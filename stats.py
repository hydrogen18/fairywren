from eventlet.green import zmq
import fairywren
import cPickle as pickle
import logging
import collections

class TrackerStatsPublisher(object):
	def __init__(self,localQueue,peerCountQueue):
		self.zmq = zmq.Context(1)
		self.pub = self.zmq.socket(zmq.PUB)
		self.pub.bind(fairywren.IPC_PATH)
		self.localQueue = localQueue
		self.peerCountQueue = peerCountQueue
		self.log = logging.getLogger('fairywren.stats.pub')
		self.log.info('Created')
		
	def produceMessage(self,msg):
		#Pickle the tuple and send it with the leading type
		#identifier
		return [fairywren.MSG_SCRAPE,pickle.dumps(msg,-1)]
		
	
	def producePeerCountMessage(self,msg):
		return [fairywren.MSG_PEERCOUNTDELTA,pickle.dumps(msg,-1)]
	
	def getThreads(self):
		return [self.statsThread,self.peerCountThread]
		
	def peerCountThread(self):
		self.log.info('Started peer count thread')
		while True:
			msg = self.peerCountQueue.get()
			
			self.pub.send_multipart(self.producePeerCountMessage(msg))
			increment, userId, _ , _ = msg
			
			self.log.debug('Sent %s msg for user %i', 'increment' if increment else 'decrement' , userId)
		
	def statsThread(self):
		self.log.info('Started stats thread')
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
		
		self.peerCountSub = self.zmq.socket(zmq.SUB)
		self.peerCountSub.connect(fairywren.IPC_PATH)
		self.peerCountSub.setsockopt(zmq.SUBSCRIBE,fairywren.MSG_PEERCOUNTDELTA)
		
		self.counts = {}
		
		self.log = logging.getLogger('fairywren.stats.sub')
		self.log.info('Created')
		
		self.userIps = {}
		
	def getUserCounts(self):
		return self.userIps
		
	def consumePeerCountMessage(self,message):
		msg = pickle.loads(message[1])
		increment, userId, ip, port = msg
		
		userCounter = self.userIps.get(userId)
		
		if userCounter == None:
			userCounter = collections.Counter()
			self.log.info('User #%i enters swarm',userId)
			self.userIps[userId] = userCounter
		
		if increment:
			action = userCounter.update
			self.log.debug('User #%i adds to %x:%i',userId,ip,port)
		else:
			action = userCounter.subtract
			self.log.debug('User #%i subtracts %x:%i',userId,ip,port)
			
		action(((ip,port,),))
		
		#Remove any entries in this users counter that 
		#have a count of zero
		toPop = []
		for entry, quantity in userCounter.iteritems():
			if quantity <= 0:
				toPop.append(entry)
				
		for entry in toPop:
			self.log.debug('User #%i loses %x:%i',userId,ip,port)
			userCounter.pop(entry)
		
		#If the user counter has no entries at all now
		#remove it from the dictionary		
		if len(userCounter) == 0:
			self.userIps.pop(userId)
			self.log.info('User #%i leaves swarm',userId)
			
		return userId
			
	
	def consumeMessage(self,message):
		#The second item in the message is a dictionary conforming
		#to the structure defined by the tracker 'scrape'
		#convention
		message = pickle.loads(message[1])
		tid, seeders, leechers = message
		
		self.counts[tid] = seeders,leechers	
		
		return  tid	
		
	def getThreads(self):
		return [self.statsThread,self.peerCountThread]	
		
	def peerCountThread(self):
		self.log.info('Started peer count thread')
		
		while True:
			recvdmsg = self.peerCountSub.recv_multipart()
			userId = self.consumePeerCountMessage(recvdmsg)
			
			self.log.debug('Received counts message for user #%i',userId)
			
		
	def statsThread(self):		
		self.log.info('Started stats thread')
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
