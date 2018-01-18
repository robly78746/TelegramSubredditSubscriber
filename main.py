import fsm
import internal
from tgapi import api
from tgkeyboard import keyboard

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
    
    api.send_message(
        internal.token, 
        userid,
        'Подписки %s' % message,
        keyboard.build(kb)
    )   

def _start(userid):
    kb = keyboard.create(3, False, True, False, True)
    kbrow = kb['keyboard']
    kbrow[0].append(keyboard.button(kb, '/subscribe'))
    kbrow[1].append(keyboard.button(kb, '/unsubscribe'))
    kbrow[2].append(keyboard.button(kb, '/subscriptions'))    
    api.send_message(
        internal.token,
        userid,
        'Выберите действие',
        keyboard.build(kb)
    )  
    
    fsm.set_state('/start', userid)
    
@internal.on_message('/start')
def start(message):
    userid = str(message['from']['id'])

    if len(message['text'].split(' ')) > 1:
        
        fsm.set_state('/subscribe', userid)
        message['text'] = message['text'].split(' ')[1]
        subscribe(message)
        
    else:        
        if not internal.dbactions.user_exist(userid):
            api.send_message(
                internal.token,
                userid,
                'Зарегистрированно'
            ) 
            internal.dbactions.register(userid)
        else:
            _start(userid)

@internal.on_message('/cancel')
def cancel(message):
    userid = str(message['from']['id'])
    _start(userid)

@internal.on_message(r'.*')     #regexp
@check_state('/subscribe')
def _subscribe(message):
    current_subs = internal.dbactions.get_subscriptions(message['from']['id'])
    *not_exesting_subs, = filter(
        lambda sub: sub not in current_subs, message['text'].split(' ')
    )
    *valid, = filter(validator, not_exesting_subs)
    if valid:
        for newSub in valid:
            current_subs[newSub] = internal.time.time()
            
        internal.dbactions.update(message['from']['id'], current_subs)
        succ_sub_message(message['from']['id'], valid, 'установлены')
        fsm.set_state('/start', message['from']['id']) 
    else:
        api.send_message(
            internal.token,
            message['from']['id'],
            '''Вы уже подписаны на этих пользователей
            или не найдены корректные имена для подписки'''
            )

@internal.on_message('/subscribe')
#@check_state('/subscribe')
def subscribe(message):    
    userid = str(message['from']['id'])
    sublist = message['text'].split(' ')
    if len(sublist) < 1:
        api.send_message(
            internal.token,
            userid,
            'Список подписок пуст'
        )
    else:
        kb = keyboard.create(1, False, True, True)
        kb['keyboard'][0].append(keyboard.button(kb, '/cancel'))
        api.send_message(
            internal.token, 
            userid,
            'Теперь введите имена пользователей через пробел',
            keyboard.build(kb)                
        )
        fsm.set_state('/subscribe', userid)

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
        api.send_message(
            internal.token,
            userid,
            'Список отписок пуст'
        )
    else:
        subs = internal.dbactions.get_subscriptions(userid)
        if type(unsublist) is not str:
            for del_sub in unsublist:
                delete(del_sub)
        else:
            delete(unsublist)
        internal.dbactions.update(userid, subs)
        succ_sub_message(userid, unsublist, 'завершены')
        fsm.set_state('/start', userid)

@internal.on_message('/subscriptions')        
def subscriptions(message):
    subs = internal.dbactions.get_subscriptions(message['from']['id'])
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
        internal.token,
        message['from']['id'],
        'Ваши подписки',
        keyboard.build(kb)
    )


@check_unsub
def dialog(callback):
    api.delete_message(
        internal.token,
        callback['from']['id'],
        callback['message']['message_id']
    )
    
    #sending new message with cancel bot button
    kb = keyboard.create(1, False, True, True)
    kb['keyboard'][0].append(keyboard.button(kb, '/cancel'))
    
    api.send_message(
        internal.token,
        callback['from']['id'],
        'Selected:',
        keyboard.build(kb)        
    )
    #.read().decode('utf-8')
    
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
        internal.token,
        callback['from']['id'],
        callback['data'],
        keyboard.build(kb)
    )
    fsm.set_state('/unsubscribe', str(callback['from']['id'])) 


message_handlers = [
    start, subscriptions, subscribe, cancel, _subscribe
]  #, unsubscribe]
internal.handlers.extend(message_handlers)
while True:
    internal.on_update(
        api.get_updates(internal.token, internal.lastmsg + 1)
    )