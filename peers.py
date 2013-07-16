
class Peer(object):
	__slots__ = ['ip','port','left','downloaded','uploaded','peerId']
	
	def __init__(self,ip,port,left,downloaded,uploaded,peerId):
		self.ip = ip
		self.port = port
		self.left = left
		self.downloaded = downloaded
		self.uploaded = uploaded
		self.peerId = peerId
		
		
	def __eq__(self,other):
		if isinstance(other,Peer):
			return self.port == other.port and self.ip == self.ip
			
		return NotImplemented

class Peers(object):
	
	def __init__(self):
		self.torrents = {}
		pass
		
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
			if extantPeer.left==0 != peer.left ==0:
				change = True
			
			self.torrents[info_hash][indexOfPeer] = peer
			
		else:
			#New peers mean the count has always changed
			change = True
			self.torrents[info_hash].append(peer)
			
		return change
		
