import fsm
import dbactions
import tgbot
import yaml

conf = yaml.load(open('conf.yml','r').read())

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
            callback['text'] = callback['data']  #hack for correct handling 
            unsub_handler(callback)
        else:
            fn(callback)
    return wrapper


def succ_sub_message(userid, subs, status):
    if type(subs) is not str:
        info_kb = tgbot.Keyboard(inline = True, rows= len(subs))
        
        for row, value in enumerate(subs):
            info_kb.add_button(
                row, value,
                link='http://reddit.com/user/%s/submitted' % value
            )            

    else:
        info_kb = tgbot.Keyboard(inline = True, rows= 1)
        info_kb.add_button(
            0, subs, link= 'http://reddit.com/user/%s/submitted' % subs
        )
    
    tgbot.send_message(userid, 'Подписки %s' % status, info_kb)   


def _start(userid):
    hello_kb = tgbot.Keyboard(
        inline = False, rows= 3, resize_keyboard= True,
        one_time_keyboard= False, selective= True
    )
    hello_kb.add_button(0, '/subscribe')
    hello_kb.add_button(1, '/unsubscribe')
    hello_kb.add_button(2, '/subscriptions')  
    tgbot.send_message(userid, 'Выберите действие', hello_kb)   
    fsm.set_state('/start', userid)

    
@tgbot.on_message(r'^/start\s?.*')
def start(message):
    userid = str(message['from']['id'])

    if len(message['text'].split(' ')) > 1:
        
        fsm.set_state('/subscribe', userid)
        message['text'] = message['text'].split(' ')[1]
        sub_handler(message)
        
    else:        
        if not dbactions.user_exist(userid):
            dbactions.register(userid)
            tgbot.send_message(userid, 'Зарегистрированно')
            _start(userid) 
        else:
            _start(userid)


@tgbot.on_message('^/cancel$')
def cancel(message):
    userid = str(message['from']['id'])
    handlers = tgbot.message_handlers
    if sub_handler in handlers:
        handlers[handlers.index(sub_handler)] = subscribe
    _start(userid)


@tgbot.on_message(r'.*')     #regexp
@check_state('/subscribe')
def sub_handler(message):
    troll = tgbot.handle(message, [subscribe])[0]
    userid = message['from']['id']
    if troll != False or troll is None:
        current_subs = dbactions.get_subscriptions(userid)
        not_exesting_subs = [
            *filter(
                lambda sub: sub not in current_subs,
                message['text'].split(' ')
            )            
        ]
        valid_names = [*filter(validator, not_exesting_subs)]
        if valid_names:
            for new_sub in valid_names:
                current_subs[new_sub] = tgbot.time.time()
                
            dbactions.update(userid, current_subs)
            succ_sub_message(userid, valid_names, 'установлены')
            handlers = tgbot.message_handlers
            try:
                handlers[handlers.index(sub_handler)] = subscribe
            except ValueError:
                pass        # called from start function
            message['text'] = '/cancel'
            cancel(message)     #auto cancel
        else:
            tgbot.send_message(
                userid,
                '''Вы уже подписаны на этих пользователей
                или не найдены корректные имена для подписки'''
                )


@tgbot.on_message('^/subscribe$')
def subscribe(message):    
    return first_step(message)

@tgbot.on_message(r'.*')     #regexp
@check_state('/unsubscribe')
def unsub_handler(message):
    def delete(usr):
        try:
            subs.pop(usr)
        except KeyError:
            pass        #user not in subscriptions
    
    troll = tgbot.handle(message, [unsubscribe])[0]
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
        handlers = tgbot.message_handlers
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
        tgbot.send_message(
            userid,
            'Список %s пуст'
            % 'подписок' if message['text'] == '/subscribe'
            else 'отписок'
        )
    else:
        cancel_kb = tgbot.Keyboard(
            inline = False, rows= 1,
            resize_keyboard= True, one_time_keyboard= True
        )
        cancel_kb.add_button(0, '/cancel')
        
        tgbot.send_message(
            userid,
            'Теперь введите имена пользователей через пробел',
            cancel_kb                
        )
        fsm.set_state('%s' % message['text'], userid)
        handlers = tgbot.message_handlers
        
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


@tgbot.on_message('^/unsubscribe$')
def unsubscribe(message): 
    return first_step(message)


@tgbot.on_message('^/subscriptions$')        
def subscriptions(message):
    subs = dbactions.get_subscriptions(message['from']['id'])
    values = [enumerate(subs)]
    subs_kb = tgbot.Keyboard(inline = True, rows= len(subs) // 2)
    row = 0
    for x, name in enumerate(subs):
        subs_kb.add_button(row, caption = name, callback= name)
        if x % 4 == 0:
            row += 1  
    tgbot.send_message(message['from']['id'], 'Ваши подписки', subs_kb)


@check_unsub
@tgbot.on_callback('.*')  #regexp
def dialog(callback):
    userid = callback['from']['id']
    tgbot.delete_message(userid, callback['message']['message_id'])
    
    #sending new message with cancel tgbot button
    cancel_kb = tgbot.Keyboard(
            inline = False, rows= 1,
            resize_keyboard= True, one_time_keyboard= True
        )
    cancel_kb.add_button(0, '/cancel')
    
    tgbot.send_message(userid, 'Selected:', cancel_kb)
    
    dialog_kb = tgbot.Keyboard(inline = True, rows= 2)
    dialog_kb.add_button(
        0,
        'Просмотр',
        link= 'http://reddit.com/user/%s/submitted' % callback['data']
    )
  
    dialog_kb.add_button(
        1,
        'Отписаться',
        callback = 'delsub=%s' % callback['data']        
    )     
    
    #adding inline buttons through new message :c
    tgbot.send_message(userid, callback['data'], dialog_kb)
    fsm.set_state('/unsubscribe', '%s' % callback['from']['id']) 


#           !!! ORDER MATTERS !!!
message_handlers = [cancel, start, subscriptions, subscribe, unsubscribe]
tgbot.message_handlers.extend(message_handlers)
tgbot.callbacks_handlers.extend([dialog])


if conf['webhook']:
    resp = tgbot.set_webhook('%s%s' % (conf['domain'],conf['token']), conf['ssl'])
    print(resp.read().decode('utf-8'))
    tgbot.start_server()
else:
    #polling
    while True:
        tgbot.on_update(
            tgbot.get_updates(tgbot.lastmsg + 1)
        )
