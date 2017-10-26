from . import dbactions
from .. import chat_sender

def launch():
    bd, opendb = dbactions.bdopen(dbactions.PATH % 'users.db')
    bd.execute('select id from subs;')
    ids = bd.fetchall()
    for _id in ids:
        subs = dbactions.get_subscriptions(_id[0])    
        ex = chat_sender.main.get_posts(subs, _id[0], True)    
        dbactions.update(_id[0], ex)