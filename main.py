import fsm
import internal
import dbactions
from sys import argv

check_state = fsm.check_state
token = dbactions.params['token']

def validator(name):
    import re
    check = re.compile(r'([A-Z]|[a-z]|\d|_|-)*')
    a = re.fullmatch(check, name)
    return hasattr(a, 'group') 

def check_unsub(fn):
    def wrapper(callback):
        if callback['data'].split('=')[0] == 'delsub':
            callback['data'] = callback['data'].split('=')[1]
            callback['text'] = callback['data']  #hack for correct handling 
            unsub_handler(callback)
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
        token, 
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
        token,
        userid,
        'Выберите действие',
        keyboard.build(kb)
    )  
    
    fsm.set_state('/start', userid)
    
@internal.on_message(r'/start\s?.*')
def start(message):
    userid = str(message['from']['id'])

    if len(message['text'].split(' ')) > 1:
        
        fsm.set_state('/subscribe', userid)
        message['text'] = message['text'].split(' ')[1]
        sub_handler(message)
        
    else:        
        if not dbactions.user_exist(userid):
            dbactions.register(userid)
            api.send_message(
                token,
                userid,
                'Зарегистрированно'
            ) 
        else:
            _start(userid)

@internal.on_message('/cancel')
def cancel(message):
    userid = str(message['from']['id'])
    handlers = internal.message_handlers
    if sub_handler in handlers:
        handlers[handlers.index(sub_handler)] = subscribe
    _start(userid)

@internal.on_message(r'.*')     #regexp
@check_state('/subscribe')
def sub_handler(message):
    troll = internal.handle(message, [subscribe])[0]
    userid = message['from']['id']
    if troll != False or troll is None:
        get_subscriptions = dbactions.get_subscriptions
        current_subs = get_subscriptions(userid)
        not_exesting_subs = [
            *filter(
                lambda sub: sub not in current_subs,
                message['text'].split(' ')
            )            
        ]
        valid = [*filter(validator, not_exesting_subs)]
        if valid:
            for newSub in valid:
                current_subs[newSub] = internal.time.time()
                
            dbactions.update(userid, current_subs)
            succ_sub_message(userid, valid, 'установлены')
            handlers = internal.message_handlers
            try:
                handlers[handlers.index(sub_handler)] = subscribe
            except ValueError:
                pass        # called from start function
            message['text'] = '/cancel'
            cancel(message)     #auto cancel
        else:
            api.send_message(
                token,
                userid,
                '''Вы уже подписаны на этих пользователей
                или не найдены корректные имена для подписки'''
                )


@internal.on_message('/subscribe')
def subscribe(message):    
    return first_step(message)

@internal.on_message(r'.*')     #regexp
@check_state('/unsubscribe')
def unsub_handler(message):
    def delete(usr):
        try:
            subs.pop(usr)
        except KeyError:
            pass        #user not in subscriptions
    
    troll = internal.handle(message, [unsubscribe])[0]
    if troll != False or troll is None:
        userid = str(message['from']['id'])
        if 'text' in message:
            unsublist = message['text'].split(' ')
        else:
            unsublist = message['data']
            
        subs = dbactions.get_subscriptions(userid)
        if type(unsublist) is not str:
            for del_sub in unsublist:
                delete(del_sub)
        else:
            delete(unsublist)
        dbactions.update(userid, subs)
        succ_sub_message(userid, unsublist, 'завершены')
        handlers = internal.message_handlers
        try:
            handlers[handlers.index(unsub_handler)] = unsubscribe
        except:
            pass        #called from unsub callback
        message['text'] = '/cancel'
        cancel(message)     #auto cancel        

def first_step(message):
    userlist = message['text'].split(' ')
    userid = str(message['from']['id'])
    if len(userlist) < 1:
        api.send_message(
            token,
            userid,
            'Список %s пуст'
            % 'подписок' if message['text'] == '/subscribe'
            else 'отписок'
        )
    else:
        kb = keyboard.create(1, False, True, True)
        kb['keyboard'][0].append(keyboard.button(kb, '/cancel'))
        api.send_message(
            token, 
            userid,
            'Теперь введите имена пользователей через пробел',
            keyboard.build(kb)                
        )
        fsm.set_state('%s' % message['text'], userid)
        handlers = internal.message_handlers
        if message['text'] == '/subscribe':
            if sub_handler not in handlers:
                handlers[handlers.index(subscribe)] = sub_handler
                return True
            else:
                return False
        elif message['text'] == '/unsubscribe':
            if unsub_handler not in handlers:
                handlers[handlers.index(unsubscribe)] = unsub_handler
                return True
            else:
                return False          

@internal.on_message('/unsubscribe')
def unsubscribe(message): 
    return first_step(message)

@internal.on_message('/subscriptions')        
def subscriptions(message):
    subs = dbactions.get_subscriptions(message['from']['id'])
    values = [enumerate(subs)]
    kb = keyboard.create(len(subs) // 2, True)
    row = 0
    for x, name in enumerate(subs):
        kb['inline_keyboard'][row].append(
            keyboard.button(kb, name, callback = name)
        )
        if x % 4 == 0:
            row += 1  
    api.send_message(
        token,
        message['from']['id'],
        'Ваши подписки',
        keyboard.build(kb)
    )


@check_unsub
@internal.on_callback('.*')  #regexp
def dialog(callback):
    userid = callback['from']['id']
    api.delete_message(
        token,
        userid,
        callback['message']['message_id']
    )
    
    #sending new message with cancel bot button
    kb = keyboard.create(1, False, True, True)
    kb['keyboard'][0].append(keyboard.button(kb, '/cancel'))
    
    api.send_message(
        token,
        userid,
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
        token,
        userid,
        callback['data'],
        keyboard.build(kb)
    )
    fsm.set_state('/unsubscribe', '%s' % callback['from']['id']) 


message_handlers = [cancel, start, subscriptions, subscribe, unsubscribe]
internal.message_handlers.extend(message_handlers)
internal.callbacks_handlers.extend([dialog])

#webhook
if len(argv) > 1:
    if argv[1] == 'webhook':
        resp = api.set_webhook(dbactions.params['token'], argv[2], argv[3])
        print(resp.read().decode('utf-8'))
        internal.start_server()

#polling
while True:
    internal.on_update(
        api.get_updates(token, internal.lastmsg + 1)
    )