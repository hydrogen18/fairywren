

from eventlet.green import zmq
import fairywren
import cPickle as pickle

class TrackerStatsPublisher(object):
	def __init__(self,tracker):
		self.zmq = zmq.Context(1)
		self.pub = self.zmq.socket(zmq.PUB)
		self.pub.bind(fairywren.IPC_PATH)
		self.queue = tracker.getQueue()
		self.tracker = tracker
		
	def __call__(self):
		while True:
			#Only info hashes are pushed onto this queue
			info_hash = self.queue.get()
			#Get a tracker scrape for the info hash
			scrape = self.tracker.getScrape([info_hash])
			
			#Pickle the scrape and send it with the leading type
			#identifier
			self.pub.send_multipart([fairywren.MSG_SCRAPE,pickle.dumps(scrape,-1)])

class TrackerStatsSubscriber(object):
	def __init__(self):
		self.zmq = zmq.Context(1)
		self.sub = self.zmq.socket(zmq.SUB)
		self.sub.connect(fairywren.IPC_PATH)
		#Only receive messages of type scrape. These are sent
		#by the tracker whenever the peer count changes for a torrent
		self.sub.setsockopt(zmq.SUBSCRIBE,fairywren.MSG_SCRAPE)
		
		self.counts = {}
		
	def __call__(self):
		
		#Receive messages forever
		while True:
			recvdmsg = self.sub.recv_multipart()
			
			#The second item in the message is a dictionary conforming
			#to the structure defined by the tracker 'scrape'
			#convention
			recvdmsg = pickle.loads(recvdmsg[1])
			
			#For each torrent present, update the counts object
			for info_hash,stats in recvdmsg['files'].iteritems():
				self.counts[info_hash] = (stats['complete'],stats['incomplete'])
		
	def getCount(self,info_hash):
		"""Return the peer count as tuple. The first value is the number of 
			seeders, the second is the number of leechers"""
			
		#If the info hash is not present, it is not an error.
		#It just means the API has never received an update from the
		#tracker
		if not info_hash in self.counts:
			return (0,0)
			
		return self.counts[info_hash]
