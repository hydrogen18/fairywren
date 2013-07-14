import eventlet
eventlet.monkey_patch()
import eventlet.backdoor
from eventlet import wsgi

from webapi import Webapi
from auth import *
from torrents import TorrentStore
from users import Users
import vanilla
import psycopg2
import sys
import json


DEFAULT_LISTEN_IP ='127.0.0.1'
DEFAULT_LISTEN_PORT = 8081
DEFAULT_PATH_DEPTH = 1

if __name__ == '__main__':
	with open(sys.argv[1],'r') as fin:
		conf = json.load(fin)
		
	connPool = vanilla.buildConnectionPool(psycopg2,**conf['webapi']['postgresql'])
	
	authmgr = Auth(conf['salt'])
	authmgr.setConnectionPool(connPool)
	
	torrents = TorrentStore(conf['webapi']['torrentPath'],conf['trackerUrl'])
	torrents.setConnectionPool(connPool)
		
	httpListenIp = conf['webapi'].get('ip',DEFAULT_LISTEN_IP)
	httpListenPort = conf['webapi'].get('port',DEFAULT_LISTEN_PORT)
	httpPathDepth = conf.get('pathDepth',DEFAULT_PATH_DEPTH)

	users = Users()
	users.setConnectionPool(connPool)
	
	webapi = Webapi(users,authmgr,torrents,httpPathDepth)
	wsgi.server(eventlet.listen((httpListenIp, httpListenPort)), webapi)
