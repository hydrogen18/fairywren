import eventlet
eventlet.monkey_patch()
import eventlet.backdoor
from eventlet import wsgi
from tracker import *
from auth import *
from peers import *

if __name__ == '__main__':
	eventlet.spawn(eventlet.backdoor.backdoor_server, eventlet.listen(('localhost', 3000)))
	authmgr = Auth(dbname='nihitorrent',user='tracker')
	
	wsgi.server(eventlet.listen(('192.168.12.182', 8080)), Tracker(authmgr,Peers()))
