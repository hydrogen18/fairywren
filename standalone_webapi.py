import eventlet
eventlet.monkey_patch()
import eventlet.backdoor
from eventlet import wsgi
from webapi import Webapi
from auth import *
from peers import *

import psycopg2
import sys
import json

if __name__ == '__main__':
	with open(sys.argv[1],'r') as fin:
		conf = json.load(fin)
		authmgr = Auth(conf['salt'])
		authmgr.connect(psycopg2,**conf['tracker']['postgresql'])
		
	eventlet.spawn(eventlet.backdoor.backdoor_server, eventlet.listen(('localhost', 3001)))
	webapi = Webapi(authmgr)
	wsgi.server(eventlet.listen(('192.168.12.182', 8081)), webapi)
