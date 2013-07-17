import unittest
import peers
import socket

class PeersTest(unittest.TestCase):
	def test_creation(self):
		peers.Peers()
		
	def test_addingPeers(self):
		
		peerList = []
		for peerIp in range(1,255):
			ip = socket.inet_aton('192.168.0.' + str(peerIp))
			
			port = peerIp%4 + 1025
			
			
			left = peerIp % 4
			done = 4 - left
			
			
			peerList.append(peers.Peer(ip,port,left,done,0,'a'))
			
		info_hashes = [chr(i)*20 for i in range(0,128)]
		
		peerTracker = peers.Peers()
		
		for info_hash in info_hashes:
			self.assertEqual(peerTracker.getNumberOfLeeches(info_hash),0)
			self.assertEqual(peerTracker.getNumberOfSeeds(info_hash),0)
			
			self.assertEqual(len(peerTracker.getPeers(info_hash)),0)
			
			for peer in peerList:
				self.assertTrue(peerTracker.updatePeer(info_hash,peer))
				self.assertTrue(peer in peerTracker.getPeers(info_hash))
				self.assertEqual(1,sum(1 for p in peerTracker.getPeers(info_hash) if p==peer ))
		
		for info_hash in info_hashes:		
			self.assertEqual(peerTracker.getNumberOfLeeches(info_hash)+peerTracker.getNumberOfSeeds(info_hash),len(peerList))
			self.assertEqual(len(peerTracker.getPeers(info_hash)),len(peerList))
			
			for peer in peerTracker.getPeers(info_hash):
				self.assertTrue(peer in peerList)
				
			for peer in peerList:
				peerTracker.removePeer(info_hash,peer)
				self.assertTrue(not peer in peerTracker.getPeers(info_hash))
			
			
				
if __name__ == '__main__':
    unittest.main()
