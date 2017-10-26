from .. import api
from .. import json
from .. import keyboard
from os.path import join
from sys import platform

STATES = join('WebAndBots', 'TG', 'bots', 'subscriber', 'states.json')

def load_states():
    return json.loads(open(STATES , 'r').read())

def save_states(new_states):
    f = open(STATES, 'w')
    f.write(json.dumps(new_states))
    f.close()

def set_state(state, user):
    old = load_states()
    old[user] = state
    save_states(old)

def check_state(fn):
    def wrapper(message, req_state):
        userid = str(message['from']['id'])
        ustates = load_states()
        if ustates[userid] == '/start':
            kb = keyboard.create(1, False, True, True)
            kb['keyboard'][0].append(keyboard.button(kb, '/cancel'))
            api.send_message(
                userid,
                'Теперь введите имена пользователей через пробел',
                keyboard.build(kb)                
            )
            set_state(req_state, userid)
        elif ustates[userid] == req_state:
            fn(message)
        else:
            return  #unknown state
    return wrapper