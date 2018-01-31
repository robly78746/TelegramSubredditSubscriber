import time
import json
import re

lastmsg = 0
message_handlers = []
callbacks_handlers = []

def on_message(text):
    def wrapper(fn):
        def inner(message):
            if re.findall(text, message['text']):
                return(fn(message))
        return inner
    return wrapper

def on_callback(data):
    def wrapper(fn):
        def inner(callback):
            if re.findall(data, callback['data']):
                return(fn(callback))
        return inner
    return wrapper

def handle(recieved, handlers = message_handlers):
    if len(recieved) > 1:
        if type(recieved) is not dict:      #we got few messages at once
            messages = [msg['message'] for msg in recieved]  #throwing useless
        else:
            messages = [recieved]
    else:
        messages = None
    for handler in handlers:
        if messages is not None:     #this also means we have multiple messages
            done = [*map(handler, messages)]
            return done
        else:           #thats why if not we transfer single msg directly
            if 'message' in recieved[0]:
                handler(recieved[0]['message'])
            elif 'callback_query' in recieved[0]:
                handler(recieved[0]['callback_query'])

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
            handle(callbacks, callbacks_handlers)
    
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