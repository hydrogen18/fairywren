from monotonic import monotonic_time
import logging


class Peer(object):
	__slots__ = ['ip','port','left','downloaded','uploaded','peerId','created']
	
	def __init__(self,ip,port,left,downloaded,uploaded,peerId):
		self.ip = ip
		self.port = port
		self.left = left
		self.downloaded = downloaded
		self.uploaded = uploaded
		self.peerId = peerId
		self.created = monotonic_time()
		
	def ipAsDottedQuad(self):
		result = []
		for mask,shift in zip((2**i - 1 for i in range(8,40,8) ), range(0,32,8)):
			result.append( str((self.ip & mask) >> shift ))
			
		result.reverse()
		return '.'.join(result)
		
	def __eq__(self,other):
		if isinstance(other,Peer):
			return self.port == other.port and self.ip == other.ip
			
		return NotImplemented

class Peers(object):
	
	def __init__(self,peerGracePeriod):
		self.peerGracePeriod = peerGracePeriod
		self.torrents = {}
		self.log = logging.getLogger('fairywren.peers')
		self.log.info('Started')
		
	def removeExpiredPeers(self):
		currentTime = monotonic_time()
		
		self.log.info('Cleaning up expired peers')
		
		for infoHash,peerList in self.torrents.iteritems():
			self.log.debug('Checking for expired peers in: %s', infoHash.encode('hex').upper())
			expirations = []
			#Iterate over the peer list, saving the indices
			#of expired peers
			for i, peer in enumerate(peerList):
				if currentTime - peer.created >= self.peerGracePeriod:
					self.log.info('%s,peer expired: %s,%d',infoHash.encode('hex').upper(),peer.ipAsDottedQuad(),peer.port)
					expirations.append(i)
			
			#Reverse the list of indices, so the 
			#positions aren't modified as peers are removed
			expirations.reverse()
			
			#Remove each expired peer
			for expiration in expirations:
				peer = peerList.pop(expiration)
				self.log.debug('%s,peer popped: %s,%d',infoHash.encode('hex').upper(),peer.ipAsDottedQuad(),peer.port)
			
		
	def getNumberOfSeeds(self,info_hash):
		if info_hash not in self.torrents:
			return 0
			
		return sum( 1 for peer in self.torrents[info_hash] if peer.left == 0)
		
	def getNumberOfLeeches(self,info_hash):
		if info_hash not in self.torrents:
			return 0
			
		return sum( 1 for peer in self.torrents[info_hash] if peer.left != 0)
		
	def getPeers(self,info_hash):
		if info_hash not in self.torrents:
			return []
			
		return self.torrents[info_hash]
		
	def removePeer(self,info_hash,peer):
		if info_hash not in self.torrents:
			return 
		
		try:
			indexOfPeer = self.torrents[info_hash].index(peer)
		except ValueError:
			#Peer was not in torrent, no problem
			return
		
		#Remove the peer
		self.torrents[info_hash].pop(indexOfPeer)
		
	def updatePeer(self,info_hash,peer):
		if info_hash not in self.torrents:
			self.torrents[info_hash] = []
			
		exists = True
		try:
			indexOfPeer = self.torrents[info_hash].index(peer)
		except ValueError:
			exists = False
		
		#While updating the peers, determine if the number of seeders
		#or leechers has changed
		change = False
		if exists:
			extantPeer = self.torrents[info_hash][indexOfPeer]
			
			#If the peer changes from seed to leech, or from leech
			#to seed then the count has changed
			wasSeed = extantPeer.left == 0
			isSeed = peer.left == 0

			change = wasSeed!=isSeed
			
			
			self.torrents[info_hash][indexOfPeer] = peer
			
		else:
			#New peers mean the count has always changed
			change = True
			self.torrents[info_hash].append(peer)
			
		return change
		
