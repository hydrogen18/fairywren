from monotonic import monotonic_time
import logging
import eventlet
import redis
import struct

PEER_STRUCT = "=IH"

class Peer(object):
	__slots__ = ['ip','port','left']
	
	def __init__(self,ip,port,left):
		self.ip = ip
		self.port = port
		self.left = left
		
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
	PEERS_HSET = "peers"
	PEERS_ID = PEERS_HSET + ".id"
	PEER = "peer"
	
	def __init__(self,redisSocketPath):
		self.redisPool = redis.StrictRedis(unix_socket_path=redisSocketPath).connection_pool
		self.log = logging.getLogger('fairywren.peers')
		self.log.info('Created')
		
		conn = self._getRedisConn()
		if conn.ping():
			self.log.info('Redis server is alive')
		else:
			self.log.info('Redis server did not respond to ping')
			
	def _getRedisConn(self):
		return redis.StrictRedis(connection_pool=self.redisPool)
		
	def getNumberOfSeeds(self,info_hash):
		conn = self._getRedisConn()
		r = conn.hvals(info_hash)
		return sum( 1 for peer in r if peer == '1')
		
	def getNumberOfLeeches(self,info_hash):
		conn = self._getRedisConn()
		r = conn.hvals(info_hash)
		return sum( 1 for peer in r if peer == '0')
		
	def getPeers(self,info_hash):
		conn = self._getRedisConn()
		
		peers = conn.hkeys(info_hash)
		for val in peers:
			peerIp,peerPort = struct.unpack(PEER_STRUCT,val)
			yield Peer(peerIp,peerPort,0) #Use 0 here because the caller doesn't care
		
	def removePeer(self,info_hash,peer):
		conn = self._getRedisConn()
		peerNumber = self.getPeerNumber(peer)
		
		if peerNumber == None:
			return False
			
		isRemove = 1 == conn.hdel(info_hash,peerNumber)
		
		return isRemove
		
	def getPeerNumber(self,peer):
		#Pack the peer
		packedPeer = struct.pack(PEER_STRUCT,peer.ip,peer.port)
		return packedPeer
		
	def updatePeer(self,info_hash,peer):
		
		peerNumber = self.getPeerNumber(peer)
		
		conn = self._getRedisConn()
		
		wasSeed = conn.hget(info_hash, peerNumber)
						
		if wasSeed == None:	
			wasSeed = False
		else:
			wasSeed = wasSeed == '1'
			
		isSeed = peer.left == 0
		
		isAdd = 1 == conn.hset(info_hash, peerNumber,'1' if isSeed else '0')
		
		#If the peer was added or
		#If the peer changed from seed to leech, or from leech
		#to seed then the count has changed
		change = isAdd or (wasSeed!=isSeed)
			
		return change
		
