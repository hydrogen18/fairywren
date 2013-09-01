from eventlet.green import zmq
import fairywren
import cPickle as pickle
import logging

class TrackerStatsPublisher(object):
	def __init__(self,tracker):
		self.zmq = zmq.Context(1)
		self.pub = self.zmq.socket(zmq.PUB)
		self.pub.bind(fairywren.IPC_PATH)
		self.queue = tracker.getQueue()
		self.tracker = tracker
		self.log = logging.getLogger('fairywren.stats.pub')
		self.log.info('Created')
		
	def produceMessage(self,info_hash):
		#Get a tracker scrape for the info hash
		scrape = self.tracker.getScrape([info_hash])
		
		#Pickle the scrape and send it with the leading type
		#identifier
		return [fairywren.MSG_SCRAPE,pickle.dumps(scrape,-1)]
		
		
	def __call__(self):
		self.log.info('Started')
		while True:
			#Only info hashes are pushed onto this queue
			info_hash = self.queue.get()
			
			#Pickle the scrape and send it with the leading type
			#identifier
			self.pub.send_multipart(self.produceMessage(info_hash))
			
			self.log.info('Sent scrape for:%s',info_hash.encode('hex').upper())

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
		#For each torrent present, update the counts object
		for info_hash,stats in message['files'].iteritems():
			self.counts[info_hash] = (stats['complete'],stats['incomplete'])
			self.log.info('Recvd scrape for:%s;%d;%d',info_hash.encode('hex').upper(),stats['complete'],stats['incomplete'])
		
	def __call__(self):		
		self.log.info('Started')
		#Receive messages forever
		while True:
			recvdmsg = self.sub.recv_multipart()
			

			self.consumeMessage(recvdmsg)
		
	def getCount(self,info_hash):
		"""Return the peer count as tuple. The first value is the number of 
			seeders, the second is the number of leechers"""
			
		#If the info hash is not present, it is not an error.
		#It just means the API has never received an update from the
		#tracker
		if not info_hash in self.counts:
			return (0,0)
			
		return self.counts[info_hash]
