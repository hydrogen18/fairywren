import unittest
import peers
import time
import socket

class TestExpiration(unittest.TestCase):
	def test_expireFunc(self):
		peerTracker = peers.Peers(1)
		peerTracker.removeExpiredPeers()
		
		
		info_hashes = [ i*20 for i in 'abcdefghijk']
		for info_hash in info_hashes:
			for ip in xrange(0,2**9):
				p = peers.Peer(ip,1025,3,0,0,'a')
				self.assertTrue(peerTracker.updatePeer(info_hash,p))
				
		time.sleep(2)
		peerTracker.removeExpiredPeers()
		
		for info_hash in info_hashes:
			self.assertEqual(0,len(peerTracker.getPeers(info_hash)))
			
	def test_expireFuncPartial(self):
		gracePeriod = 60*60
		peerTracker = peers.Peers(gracePeriod)
		
		info_hashes = [ i*20 for i in 'abcdefghijk']
		for info_hash in info_hashes:
			for ip in xrange(0,2**9):
				p = peers.Peer(ip,1025,3,0,0,'a')
				if ip%2 == 0:
					p.created = p.created - gracePeriod - 1 
				self.assertTrue(peerTracker.updatePeer(info_hash,p))
				
		peerTracker.removeExpiredPeers()
		
		for info_hash in info_hashes:
			pList = peerTracker.getPeers(info_hash)
			self.assertEqual(len(pList),2**8)
			for peer in pList:
				self.assertTrue(peer.created%2!=0)
		
		

class PeersTest(unittest.TestCase):
	def test_creation(self):
		peers.Peers(0)
		
	def test_change(self):
		peerTracker = peers.Peers(0)
		info_hash = '0'*20
		ip = socket.inet_aton('192.168.0.1')
		p = peers.Peer(ip,1025,3,0,0,'a')
		self.assertTrue(peerTracker.updatePeer(info_hash,p))
		p = peers.Peer(ip,1025,2,0,0,'a')
		self.assertTrue(not peerTracker.updatePeer(info_hash,p))
		p = peers.Peer(ip,1025,1,0,0,'a')
		self.assertTrue(not peerTracker.updatePeer(info_hash,p))
		p = peers.Peer(ip,1025,0,0,0,'a')
		self.assertTrue(peerTracker.updatePeer(info_hash,p))
		
	def test_removePeerNoSuchInfoHash(self):
		peerTracker = peers.Peers(0)
		ip = socket.inet_aton('192.168.0.1')
		p = peers.Peer(ip,1025,3,0,0,'a')
		info_hash = '0'*20
		self.assertFalse(peerTracker.removePeer(info_hash,p))
		
	def test_removePeerNotExistInInfoHash(self):
		peerTracker = peers.Peers(0)
		ip = socket.inet_aton('192.168.0.1')
		p0 = peers.Peer(ip,1025,3,0,0,'a')
		info_hash = '0'*20
		self.assertTrue(peerTracker.updatePeer(info_hash,p0))
		
		p1 = peers.Peer(ip,1026,3,0,0,'a')
		
		self.assertFalse(peerTracker.removePeer(info_hash,p1))
		
		self.assertTrue(peerTracker.removePeer(info_hash,p0))
		
		self.assertFalse(peerTracker.removePeer(info_hash,p0))
		
	def test_addingPeers(self):
		peerList = []
		for peerIp in range(1,255):
			ip = socket.inet_aton('192.168.0.' + str(peerIp))
			
			port = peerIp%4 + 1025
			
			
			left = peerIp % 4
			done = 4 - left
			
			
			peerList.append(peers.Peer(ip,port,left,done,0,'a'))
			
		info_hashes = [chr(i)*20 for i in range(0,128)]
		
		peerTracker = peers.Peers(0)
		
		for info_hash in info_hashes:
			self.assertEqual(peerTracker.getNumberOfLeeches(info_hash),0)
			self.assertEqual(peerTracker.getNumberOfSeeds(info_hash),0)
			
			self.assertEqual(len(peerTracker.getPeers(info_hash)),0)
			
			for i,peer in enumerate(peerList):
				self.assertTrue(peerTracker.updatePeer(info_hash,peer))
				l = peerTracker.getPeers(info_hash)
				self.assertIn(peer,l)
				self.assertEqual(i+1,len(l))
				self.assertEqual(1,sum(1 for p in peerTracker.getPeers(info_hash) if p==peer ))
		
		for info_hash in info_hashes:		
			self.assertEqual(peerTracker.getNumberOfLeeches(info_hash)+peerTracker.getNumberOfSeeds(info_hash),len(peerList))
			self.assertEqual(len(peerTracker.getPeers(info_hash)),len(peerList))
			
			for peer in peerTracker.getPeers(info_hash):
				self.assertTrue(peer in peerList)
				
			for peer in peerList:
				self.assertTrue(peerTracker.removePeer(info_hash,peer))
				self.assertTrue(not peer in peerTracker.getPeers(info_hash))
			
			
				
if __name__ == '__main__':
    unittest.main()
