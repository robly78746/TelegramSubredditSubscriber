import json
import time
import dbactions
import fsm
from tgapi import api
from tgkeyboard import keyboard
from sys import argv

check_state = fsm.check_state

def on_update(incoming):
    try:
        commandsQ = json.loads(incoming)
    except TypeError:
        pass  #nonetype
    
    if commandsQ:
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

def start_server(port = 9696):
    from http.server import HTTPServer, BaseHTTPRequestHandler 
    
    class handler(BaseHTTPRequestHandler):
        def _set_headers(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

        def do_GET(self):
            self._set_headers()
            self.wfile.write('get response')
    
        def do_HEAD(self):
            self._set_headers()
    
        def do_POST(self):
            # Doesn't do anything with posted data
            #self._set_headers()
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            on_update(post_data)
            self._set_headers()
    
    server_address = ('', port)
    httpd = HTTPServer(server_address, handler)
    httpd.serve_forever()

if len(argv) > 1:
    if argv[1] == 'webhook':
        resp = api.set_webhook(dbactions.params['token'], argv[2], argv[3])
        print(resp.read().decode('utf-8'))
        start_server()

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
        dbactions.params['token'], 
        userid,
        'Подписки %s' % message,
        keyboard.build(kb)
    )   

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
                
                api.send_message(
                    dbactions.params['token'],
                    userid,
                    'Зарегистрированно'
                ) 
                dbactions.register(userid)
        
        api.send_message(
            dbactions.params['token'],
            userid,
            'Выберите действие',
            keyboard.build(kb)
        )  
        
        fsm.set_state('/start', userid)

@check_state
def subscribe(message):    
    userid = str(message['from']['id'])
    sublist = message['text'].split(' ')
    if len(sublist) < 1:
        api.send_message(
            dbactions.params['token'],
            userid,
            'Список подписок пуст'
        )
    else:
        current_subs = dbactions.get_subscriptions(userid)
        *not_exesting_subs, = filter(
            lambda sub: sub not in current_subs, sublist
        )
        *valid, = filter(validator, not_exesting_subs)
        if valid:
            for newSub in valid:
                current_subs[newSub] = time.time()
                
            dbactions.update(userid, current_subs)
            succ_sub_message(userid, valid, 'установлены')
            fsm.set_state('/start', userid) 
        else:
            api.send_message(
                dbactions.params['token'],
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
        api.send_message(
            dbactions.params['token'],
            userid,
            'Список отписок пуст'
        )
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
        dbactions.params['token'],
        message['from']['id'],
        'Ваши подписки',
        keyboard.build(kb)
    )


@check_unsub
def dialog(callback):
    api.delete_message(
        dbactions.params['token'],
        callback['from']['id'],
        callback['message']['message_id']
    )
    
    #sending new message with cancel bot button
    kb = keyboard.create(1, False, True, True)
    kb['keyboard'][0].append(keyboard.button(kb, '/cancel'))
    
    api.send_message(
        dbactions.params['token'],
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
        dbactions.params['token'],
        callback['from']['id'],
        callback['data'],
        keyboard.build(kb)
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
        on_update(api.get_updates(dbactions.params['token'],lastmsg + 1))

if __name__ == '__main__':
    listener(1)