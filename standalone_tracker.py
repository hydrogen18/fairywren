import eventlet
eventlet.monkey_patch()
import eventlet.backdoor
from eventlet import wsgi
from tracker import Tracker
from auth import *
from peers import *

import vanilla
import psycopg2
import sys
import json

if __name__ == '__main__':
	with open(sys.argv[1],'r') as fin:
		conf = json.load(fin)
		authmgr = Auth(conf['salt'])
		connPool = vanilla.buildConnectionPool(psycopg2,**conf['tracker']['postgresql'])
		authmgr.setConnectionPool(connPool)
		
	eventlet.spawn(eventlet.backdoor.backdoor_server, eventlet.listen(('localhost', 3000)))
	
	wsgi.server(eventlet.listen(('192.168.12.182', 8080)), Tracker(authmgr,Peers()))
