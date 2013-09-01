from eventlet.green import zmq
import fairywren
import cPickle as pickle
import logging

class TrackerStatsPublisher(object):
	def __init__(self,localQueue):
		self.zmq = zmq.Context(1)
		self.pub = self.zmq.socket(zmq.PUB)
		self.pub.bind(fairywren.IPC_PATH)
		self.localQueue = localQueue
		self.log = logging.getLogger('fairywren.stats.pub')
		self.log.info('Created')
		
	def produceMessage(self,msg):
		#Pickle the tuple and send it with the leading type
		#identifier
		return [fairywren.MSG_SCRAPE,pickle.dumps(msg,-1)]
		
	def __call__(self):
		self.log.info('Started')
		while True:
			#Tuples consisting of 
			#
			# Torrent Id
			# Seed count
			# Leech count
			#
			# are pushed into this queue
			
			#Only info hashes are pushed onto this queue
			msg = self.localQueue.get()
			
			#Pickle the scrape and send it with the leading type
			#identifier
			self.pub.send_multipart(self.produceMessage(msg))
			
			tid, _ , _ = msg
			
			self.log.info('Sent counts for torrent #%i', tid)

class TrackerStatsSubscriber(object):
	def __init__(self):
		self.zmq = zmq.Context(1)
		self.sub = self.zmq.socket(zmq.SUB)
		self.sub.connect(fairywren.IPC_PATH)
		#Only receive messages of type scrape. These are sent
		#by the tracker whenever the peer count changes for a torrent
		self.sub.setsockopt(zmq.SUBSCRIBE,fairywren.MSG_SCRAPE)
		
		self.counts = {}
		
		self.log = logging.getLogger('fairywren.stats.sub')
		self.log.info('Created')
		
	def consumeMessage(self,message):
		#The second item in the message is a dictionary conforming
		#to the structure defined by the tracker 'scrape'
		#convention
		message = pickle.loads(message[1])
		tid, seeders, leechers = message
		
		self.counts[tid] = seeders,leechers	
		
		return  tid	
		
	def __call__(self):		
		self.log.info('Started')
		#Receive messages forever
		while True:
			recvdmsg = self.sub.recv_multipart()
			tid = self.consumeMessage(recvdmsg)
			
			self.log.info('Received counts for torrent #%i', tid)
		
	def getCount(self,torrentId):
		"""Return the peer count as tuple. The first value is the number of 
			seeders, the second is the number of leechers"""
		#If the torrentId is not present, it is not an error.
		#It just means the API has never received an update from the
		#tracker
		if not torrentId in self.counts:
			return (0,0)
			
		return self.counts[torrentId]
