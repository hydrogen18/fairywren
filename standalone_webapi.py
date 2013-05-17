import eventlet
eventlet.monkey_patch()
import eventlet.backdoor
from eventlet import wsgi

from webapi import Webapi
from auth import *
from torrents import TorrentStore

import vanilla
import psycopg2
import sys
import json

if __name__ == '__main__':
	with open(sys.argv[1],'r') as fin:
		conf = json.load(fin)
		
		connPool = vanilla.buildConnectionPool(psycopg2,**conf['tracker']['postgresql'])
		
		authmgr = Auth(conf['salt'])
		authmgr.setConnectionPool(connPool)
		
		torrents = TorrentStore()
		torrents.setConnectionPool(connPool)
		
	eventlet.spawn(eventlet.backdoor.backdoor_server, eventlet.listen(('localhost', 3001)))
	webapi = Webapi(authmgr,torrents)
	wsgi.server(eventlet.listen(('0.0.0.0', 8081)), webapi)
