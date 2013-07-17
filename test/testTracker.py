import unittest
import peers
import tracker
import socket
import urllib
import bencode

class MockAuth(object):
	def authenticateSecretKey(self,key):
		return True
		
	def authorizeInfoHash(self,info_hash):
		return True

class PeersTest(unittest.TestCase):
	def test_creation(self):
		tracker.Tracker(MockAuth(),peers.Peers(),0)
		
	def test_addingPeers(self):
		testTracker = tracker.Tracker(MockAuth(),peers.Peers(),0)
		def assert200(status,headers):
			self.assertTrue('200' in status)
			
		peerList = []
		for peerIp in range(1,32):
			peerList.append(('192.168.0.' + str(peerIp),peerIp%4 + 1025))
			
		info_hashes = [chr(i)*20 for i in range(0,128)]
		
		env = {}
		env['PATH_INFO'] = '/' + 86*'0' + '/announce'
		env['REQUEST_METHOD'] = 'GET'
			
		for info_hash in info_hashes:
			for cnt,peer in enumerate(peerList):
				peerIp,peerPort = peer
				env['REMOTE_ADDR'] = peerIp
				
				query = {}
				query['info_hash'] = info_hash
				query['peer_id'] = '0'*20
				query['port'] = peerPort
				query['uploaded'] = 0
				query['downloaded'] = 0 
				query['left'] = 128
				query['compact'] = 0
				query['event'] = 'started'
				
				env['QUERY_STRING'] = urllib.urlencode(query)
				
				response = testTracker(env,assert200)
				
				response = ''.join(response)
				
				response = bencode.bdecode(response)

				self.assertEqual(len(response['peers']),cnt+1)
				
	def test_compactResponse(self):
		testTracker = tracker.Tracker(MockAuth(),peers.Peers(),0)
		def assert200(status,headers):
			self.assertTrue('200' in status)
			
		peerList = []
		for peerIp in range(1,32):
			peerList.append(('192.168.0.' + str(peerIp),peerIp%4 + 1025))
			
		info_hashes = [chr(i)*20 for i in range(0,128)]
		
		env = {}
		env['PATH_INFO'] = '/' + 86*'0' + '/announce'
		env['REQUEST_METHOD'] = 'GET'
			
		for info_hash in info_hashes:
			for cnt,peer in enumerate(peerList):
				peerIp,peerPort = peer
				env['REMOTE_ADDR'] = peerIp
				
				query = {}
				query['info_hash'] = info_hash
				query['peer_id'] = '0'*20
				query['port'] = peerPort
				query['uploaded'] = 0
				if peerPort % 2 == 0:
					query['downloaded'] = 128
					query['left'] = 0
				else:
					query['left'] = 128
					query['downloaded'] = 0
				query['compact'] = 1
				query['event'] = 'started'
				
				env['QUERY_STRING'] = urllib.urlencode(query)
				
				response = testTracker(env,assert200)
				
				response = ''.join(response)
				
				response = bencode.bdecode(response)

				self.assertEqual(len(response['peers']),(cnt+1)*6)
		
		#Test Update events
		for info_hash in info_hashes:
			for peer in peerList:
				peerIp,peerPort = peer
				env['REMOTE_ADDR'] = peerIp
				
				query = {}
				query['info_hash'] = info_hash
				query['peer_id'] = '0'*20
				query['port'] = peerPort
				query['uploaded'] = 0
				if peerPort % 2 != 0:
					query['downloaded'] = 128
					query['left'] = 0
				else:
					query['left'] = 128
					query['downloaded'] = 0
				query['compact'] = 1
				
				env['QUERY_STRING'] = urllib.urlencode(query)
				
				response = testTracker(env,assert200)
				
				response = ''.join(response)
				
				response = bencode.bdecode(response)

				self.assertEqual(len(response['peers']),len(peerList)*6)
				
				
			
				
if __name__ == '__main__':
    unittest.main()
