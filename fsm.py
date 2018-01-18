from tgapi import api
from tgkeyboard import keyboard
import json
from internal import token

STATES = 'states.json'

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

def check_state(state):
    def wrapper(fn):
        def inner(message):
            userid = str(message['from']['id'])
            ustates = load_states()
            if ustates[userid] == state:
                fn(message)
            else:
                return  #unknown state
        return inner
    return wrapper