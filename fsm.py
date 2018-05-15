import yaml

STATES = 'states.yml'

def load_states():
    return yaml.load(open(STATES , 'r').read())

def save_states(new_states):
    f = open(STATES, 'w')
    f.write(yaml.dump(new_states))
    f.close()

def set_state(state, user):
    states = load_states()
    states[user] = state
    save_states(states)

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
