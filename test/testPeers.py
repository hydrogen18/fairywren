import unittest
import peers
import time
import socket
import tracker
import subprocess
import tempfile
import os

		

class PeersTest(unittest.TestCase):
	def setUp(self):
		self.redisInstance = None
		with tempfile.NamedTemporaryFile() as fout:
			testSocket = os.tempnam() + os.urandom(4).encode('hex')
			fout.write('unixsocket ' + testSocket)
			fout.write(os.linesep)
			fout.write('loglevel warning')
			fout.write(os.linesep)
			fout.write('logfile ' + os.devnull)
			fout.write(os.linesep)
			fout.write('port 0')
			fout.write(os.linesep)
			fout.flush()
			self.redisInstance = subprocess.Popen(['redis-server',fout.name])
			
			for i in xrange(0,16):
				if os.path.exists(testSocket):
					break
				time.sleep(1)
			else:
				raise RuntimeError('redis-server did not start')
		
		self.peers = peers.Peers(testSocket,0)
		
	def tearDown(self):
		if self.redisInstance != None:
			self.redisInstance.terminate()
			self.redisInstance.wait()

class TestExpiration(PeersTest):
	def test_expireFunc(self):
		peerTracker = self.peers
		peerTracker.removeExpiredPeers()
		
		
		info_hashes = [ i*20 for i in 'abcdefghijk']
		for info_hash in info_hashes:
			for ip in xrange(0,2**9):
				p = peers.Peer(ip,1025,3)
				self.assertTrue(peerTracker.updatePeer(info_hash,p))
				
		time.sleep(2)
		peerTracker.peerExpirationPeriod = 1
		peerTracker.removeExpiredPeers()
		
		for info_hash in info_hashes:
			pList = list(peerTracker.getPeers(info_hash))
			self.assertEqual(0,len(pList))


class TestExpireNone(PeersTest):
	def test_expireFuncPartial(self):
		
		peerTracker = self.peers
		
		info_hashes = [ i*20 for i in 'abcdefghijk']
		for info_hash in info_hashes:
			for ip in xrange(0,2**9):
				p = peers.Peer(ip,1025,3)
				
				self.assertTrue(peerTracker.updatePeer(info_hash,p))
				
		peerTracker.peerExpirationPeriod = 60*60
		peerTracker.removeExpiredPeers()
		
		for info_hash in info_hashes:
			pList = list(peerTracker.getPeers(info_hash))
			self.assertEqual(len(pList),2**9)
			
class TestChange(PeersTest):		
	def test_change(self):
		peerTracker = self.peers
		info_hash = '0'*20
		ip = tracker.dottedQuadToInt('192.168.0.1')
		p = peers.Peer(ip,1025,3)
		self.assertTrue(peerTracker.updatePeer(info_hash,p))
		p = peers.Peer(ip,1025,2)
		self.assertFalse(peerTracker.updatePeer(info_hash,p))
		p = peers.Peer(ip,1025,1)
		self.assertFalse(peerTracker.updatePeer(info_hash,p))
		p = peers.Peer(ip,1025,0)
		self.assertTrue(peerTracker.updatePeer(info_hash,p))

class TestRemovePeerNoSuchInfoHash(PeersTest):		
	def test_removePeerNoSuchInfoHash(self):
		peerTracker = self.peers
		ip = tracker.dottedQuadToInt('192.168.0.1')
		p = peers.Peer(ip,1025,3)
		info_hash = '0'*20
		self.assertFalse(peerTracker.removePeer(info_hash,p))
		
class TestRemovePeerNotInInfoHash(PeersTest):		
	def test_removePeerNotExistInInfoHash(self):
		peerTracker = self.peers
		ip = tracker.dottedQuadToInt('192.168.0.1')
		p0 = peers.Peer(ip,1025,3)
		info_hash = '0'*20
		self.assertTrue(peerTracker.updatePeer(info_hash,p0))
		
		p1 = peers.Peer(ip,1026,3)
		
		self.assertFalse(peerTracker.removePeer(info_hash,p1))
		
		self.assertTrue(peerTracker.removePeer(info_hash,p0))
		
		self.assertFalse(peerTracker.removePeer(info_hash,p0))

class TestAddingPeers(PeersTest):
	def test_addingPeers(self):
		peerList = []
		for peerIp in range(1,17):
			ip = tracker.dottedQuadToInt('192.168.0.' + str(peerIp))
			
			port = peerIp%4 + 1025
			
			left = peerIp % 4
			done = 4 - left
			
			peerList.append(peers.Peer(ip,port,left))
			
		info_hashes = [chr(i)*20 for i in range(0,4)]
		
		peerTracker = self.peers
		
		for info_hash in info_hashes:
			self.assertEqual(peerTracker.getNumberOfLeeches(info_hash),0)
			self.assertEqual(peerTracker.getNumberOfSeeds(info_hash),0)
			
			self.assertEqual(len(list(peerTracker.getPeers(info_hash))),0)
			
			for i,peer in enumerate(peerList):
				self.assertTrue(peerTracker.updatePeer(info_hash,peer))
				l = peerTracker.getPeers(info_hash)
				l = list(l)
				self.assertIn(peer,l)
				self.assertEqual(i+1,len(l))
				self.assertEqual(1,sum(1 for p in peerTracker.getPeers(info_hash) if p==peer ))
		
		for info_hash in info_hashes:		
			self.assertEqual(peerTracker.getNumberOfLeeches(info_hash)+peerTracker.getNumberOfSeeds(info_hash),len(peerList))
			l = list(peerTracker.getPeers(info_hash))
			self.assertEqual(len(l),len(peerList))
			
			for peer in peerTracker.getPeers(info_hash):
				self.assertTrue(peer in peerList)
				
			for peer in peerList:
				self.assertTrue(peerTracker.removePeer(info_hash,peer))
				self.assertTrue(not peer in peerTracker.getPeers(info_hash))
			
			
				
if __name__ == '__main__':
    unittest.main()
