import eventlet
eventlet.monkey_patch()
import eventlet.backdoor
from eventlet import wsgi
from tracker import Tracker, TrackerStats
from auth import *
from peers import *

import vanilla
import psycopg2
import sys
import json

DEFAULT_LISTEN_IP ='127.0.0.1'
DEFAULT_LISTEN_PORT = 8080
DEFAULT_PATH_DEPTH = 1

if __name__ == '__main__':
	with open(sys.argv[1],'r') as fin:
		conf = json.load(fin)
	authmgr = Auth(conf['salt'])
	connPool = vanilla.buildConnectionPool(psycopg2,**conf['tracker']['postgresql'])
	authmgr.setConnectionPool(connPool)
	
	httpListenIp = conf['tracker'].get('ip',DEFAULT_LISTEN_IP)
	httpListenPort = conf['tracker'].get('port',DEFAULT_LISTEN_PORT)
	httpPathDepth = conf.get('pathDepth',DEFAULT_PATH_DEPTH)
	
	tracker = Tracker(authmgr,Peers(),httpPathDepth)
	trackerStats = TrackerStats(tracker)
	
	eventlet.spawn_n(trackerStats)
	
	wsgi.server(eventlet.listen((httpListenIp, httpListenPort)), tracker)
