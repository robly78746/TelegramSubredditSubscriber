import json
import time
import dbactions
import fsm
#import main
from tgchat_sender.tgapi import api
from tgchat_sender.tgkeyboard import keyboard

check_state = fsm.check_state

def validator(name):
    import re
    check = re.compile(r'([A-Z]|[a-z]|\d|_|-)*')
    a = re.fullmatch(check, name)
    return hasattr(a, 'group') 

def check_unsub(fn):
    def wrapper(callback):
        if callback['data'].split('=')[0] == 'delsub':
            callback['data'] = callback['data'].split('=')[1]
            unsubscribe(callback, '/unsubscribe')
        else:
            fn(callback)
    return wrapper


def succ_sub_message(userid, subs, message):
    if type(subs) is not str:
        kb = keyboard.create(len(subs), inline = True)
        kbrow = kb['inline_keyboard']
        
        for row, value in enumerate(subs):
            kbrow[row].append(
                keyboard.button(kb, value, link =
                    'http://reddit.com/user/%s/submitted' % value)                
                )
    else:
        kb = keyboard.create(1, inline = True)
        kb['inline_keyboard'][0].append(
            keyboard.button(kb, subs, link =
                'http://reddit.com/user/%s/submitted' % subs)                
            )
    
    api.send_message(userid, 'Подписки %s' % message, keyboard.build(kb))   

def start(message, state, skip = False):
    userid = str(message['from']['id'])

    if len(message['text'].split(' ')) > 1:
        fsm.set_state('/subscribe', userid)
        message['text'] = message['text'].split(' ')[1]
        subscribe(message, '/subscribe')
    else:
        kb = keyboard.create(3, False, True, False, True)
        kbrow = kb['keyboard']
        kbrow[0].append(keyboard.button(kb, '/subscribe'))
        kbrow[1].append(keyboard.button(kb, '/unsubscribe'))
        kbrow[2].append(keyboard.button(kb, '/subscriptions'))
        if not skip:
            if not dbactions.user_exist(userid):
                api.send_message(userid, 'Зарегистрированно') 
                dbactions.register(userid)
        api.send_message(userid, 'Выберите действие', keyboard.build(kb))  
        fsm.set_state('/start', userid)

@check_state
def subscribe(message):
    userid = str(message['from']['id'])
    sublist = message['text'].split(' ')
    if not len(sublist) >= 1:
        api.send_message(userid, 'Список подписок пуст')  
    else:
        current_subs = dbactions.get_subscriptions(userid)
        *not_exesting_subs, = filter(
            lambda sub: sub not in current_subs, sublist
        )
        *valid, = filter(validator, not_exesting_subs)
        if valid:
            for newSub in valid:
                current_subs[newSub] = time.time() - day * 7
                
            dbactions.update(userid, current_subs)
            succ_sub_message(userid, valid, 'установлены')
            fsm.set_state('/start', userid) 
        else:
            api.send_message(
                userid,
                '''Вы уже подписаны на этих пользователей
                или не найдены корректные имена для подписки'''
            ) 

@check_state
def unsubscribe(message):
    def delete(usr):
        try:
            subs.pop(usr)
        except KeyError:
            pass        #user not in subscriptions
        
    userid = str(message['from']['id'])
    if 'text' in message:
        unsublist = message['text'].split(' ')
    else:
        unsublist = message['data']
        
    if not len(unsublist) >= 1:
        api.send_message(userid, 'Список отписок пуст')
    else:
        subs = dbactions.get_subscriptions(userid)
        if type(unsublist) is not str:
            for del_sub in unsublist:
                delete(del_sub)
        else:
            delete(unsublist)
        dbactions.update(userid, subs)
        succ_sub_message(userid, unsublist, 'завершены')
        fsm.set_state('/start', userid)
        
def subscribtions(message, state):
    subs = dbactions.get_subscriptions(message['from']['id'])
    values = list(enumerate(subs))
    kb = keyboard.create(len(subs) // 2, True)
    row = 0
    for x, name in enumerate(subs):
        kb['inline_keyboard'][row].append(
            keyboard.button(kb, name, callback = name)
        )
        if x % 4 == 0:
            row += 1  
    api.send_message(
        message['from']['id'], 'Ваши подписки', keyboard.build(kb)
    )


@check_unsub
def dialog(callback):
    api.delete_message(
        callback['from']['id'], callback['message']['message_id']
    )
    
    #sending new message with cancel bot button
    kb = keyboard.create(1, False, True, True)
    kb['keyboard'][0].append(keyboard.button(kb, '/cancel'))
    
    api.send_message(callback['from']['id'],'Selected:',
                     keyboard.build(kb)).read().decode('utf-8')
    
    kb = keyboard.create(2, True)
    kbrow = kb['inline_keyboard']
    kbrow[0].append(
        keyboard.button(
            kb, 'Просмотр',
            'http://reddit.com/user/%s/submitted' % callback['data']            
        )        
    )
    
    kbrow[1].append(
        keyboard.button(
            kb, 'Отписаться' , callback = 'delsub=%s' % callback['data']
        )
    )     
    
    #adding inline buttons through new message :c
    api.send_message(
        callback['from']['id'], callback['data'], keyboard.build(kb)
    )
    fsm.set_state('/unsubscribe', str(callback['from']['id']))

actions = {
    "/start": start,
    "/subscribe": subscribe,
    "/unsubscribe": unsubscribe,
    "/subscriptions": subscribtions,
    "/cancel": lambda msg, st: start(msg, st, skip= True),    
}

def listener(cooldown):
    lastmsg = 0

    def command_check(message):
        command = message['text'].split(' ')[0]
        try:
            actions[command](message, command)
        except KeyError:
            ustates = fsm.load_states()
            user = str(message['from']['id'])
            state = ustates[user]
            #некорректная команда
            actions[state](message, state)
    
    def callback_check(callback):
        try:
            actions[callback['data']](callback)
        except KeyError:
            dialog(callback)
            #unsubscribe(callback, '/unsubscribe')
            #pass  #unknown callback    
    
    def execution(kind):
        *execute, = map(
            lambda x: command_check(x) if kind == 'message'
            else callback_check(x),
            map(
                lambda y:y[kind], commands if kind == 'message'
                else callbacks                
            )            
        )
        execute.clear()      
                
    while True:
        try:
            commandsQ = json.loads(api.get_updates(lastmsg + 1))
        except TypeError:
            continue  #nonetype
        
        *commands, = filter(
            lambda x:'message' in x and 'text' in x['message'],
            filter(lambda y: y['update_id'] > lastmsg, commandsQ['result'])            
        )
        
        *callbacks, = filter(
            lambda x: 'callback_query' in x, commandsQ['result']
        )
        
        if commands:
            execution('message')
        elif callbacks:
            execution('callback_query')

        time.sleep(cooldown)
        lastmsg = max(
            map(lambda x: x['update_id'], commands if commands
                else callbacks), default= lastmsg            
        )

if __name__ == '__main__':
    listener(1)