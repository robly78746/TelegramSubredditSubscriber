import ast
from sqlite3 import *
import json


def bdopen(dbname = 'users.db'):
    opendb = connect(dbname)
    opendb.row_factory = Row
    bd = opendb.cursor()
    return bd, opendb

def get_subscriptions(uid):
    bd, opendb = bdopen()
    bd.execute('select subs from subs where id=%s' % uid)
    subscriptions = ast.literal_eval(bd.fetchall()[0][0])
    return subscriptions

def register(uid):
    bd, opendb = bdopen()
    bd.execute("insert into subs values(%s,'{}')" % uid)
    opendb.commit()

def user_exist(uid):
    bd, opendb = bdopen()
    bd.execute("select id from subs where id=%s" % uid)
    try:
        int(bd.fetchall()[0][0])
    except:
        return False
    else:
        return True

def update(subscriber, seq):
    bd, opendb = bdopen()
    sublist = {}
    if not hasattr(seq, 'keys'):
        for user in seq:
            sublist.update(user)
    else:
        sublist = seq        
    bd.execute(
        '''update subs set subs=? where id=?''' ,
        (json.dumps(sublist), subscriber)        
    )
    opendb.commit()