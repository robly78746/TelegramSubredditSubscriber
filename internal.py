import time
import json
import re
from sys import argv
import dbactions

lastmsg = 0
token = dbactions.params['token']
handlers = []

def on_message(text):
    def wrapper(fn):
        def inner(message):
            if re.findall(text, message['text']):
                return(fn(message))
        return inner
    return wrapper

def handle(message, handlers = handlers):
    if len(message) > 1:
        if type(message) is not dict:
            _filter = [m['message'] for m in message]
        else:
            _filter = [message]
    else:
        _filter = False
    for h in handlers:
        if _filter:     #this also means we have multiple messages
            *done, = map(h, _filter)
            return done
        else:           #thats why if not we transfer single msg directly
            h(message[0]['message'])

def on_update(incoming, webhook = False, cooldown = 1):
    global lastmsg
    try:
        commandsQ = json.loads(incoming)
    except TypeError:
        pass  #nonetype
    
    if commandsQ:

        *commands, = filter(
            lambda x:'message' in x and 'text' in x['message'],
            filter(
                lambda y: y['update_id'] > lastmsg, commandsQ['result']
            ) if not webhook else [commandsQ]
        )
            
        *callbacks, = filter(
            lambda x: 'callback_query' in x,
            commandsQ if webhook else commandsQ['result']
        )
    
        if commands:
            handle(commands)
        elif callbacks:
            execution('callback_query', callbacks)
    
    if not webhook:
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
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            on_update(post_data, True)
            self._set_headers()
    
    server_address = ('', port)
    httpd = HTTPServer(server_address, handler)
    httpd.serve_forever()

if len(argv) > 1:
    if argv[1] == 'webhook':
        resp = api.set_webhook(dbactions.params['token'], argv[2], argv[3])
        print(resp.read().decode('utf-8'))
        start_server()