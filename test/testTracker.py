import unittest
import peers
import tracker
import socket
import urllib
import bencode
import logging
import logging.handlers

from wsgi_intercept.urllib2_intercept import install_opener
import wsgi_intercept

import urllib2

class MockAuth(object):
	def authenticateSecretKey(self,key):
		return True
		
	def authorizeInfoHash(self,info_hash):
		return True

class WSGITrackerTest(unittest.TestCase):
	def setUp(self):
		install_opener()
		
		def createTracker():
			return tracker.Tracker(MockAuth(),peers.Peers(),0)
		
		wsgi_intercept.add_wsgi_intercept('tracker',80,createTracker)
		self.urlopen = urllib2.urlopen
	
class BadAnnounce(WSGITrackerTest):
	def test_badSecretKey(self):
		for i in range(1,86):
			self.assertRaisesRegexp(urllib2.HTTPError, '.*404.*', self.urlopen,'http://tracker/' + i*'0' + '/announce')
		
	def test_badInfoHash(self):
		for i in range(0,20):
			query = {'info_hash':i*'\0','peer_id':'A'*20,'port':1025,'uploaded':0,'downloaded':0,'left':0}
			
			try:
				self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
			except urllib2.HTTPError, e:
				self.assertEqual(e.code, 400)
				self.assertIn('info_hash',e.read())
				continue
			self.assertTrue(False)

	def test_badPeerId(self):
		for i in range(0,20):
			query = {'info_hash':'\0'*20,'peer_id':'A'*i,'port':1025,'uploaded':0,'downloaded':0,'left':0}
			
			try:
				self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
			except urllib2.HTTPError, e:
				self.assertEqual(e.code, 400)
				self.assertIn('peer_id',e.read())
				continue
			self.assertTrue(False)

	def test_badPort(self):
		for i in [-1,0,2**16]:
			query = {'info_hash':'\0'*20,'peer_id':'A'*20,'port':i,'uploaded':0,'downloaded':0,'left':0}
			
			try:
				self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
			except urllib2.HTTPError, e:
				self.assertEqual(e.code, 400)
				self.assertIn('port',e.read())
				continue
			self.assertTrue(False)

	def test_badUploaded(self):
		for i in [-1,'foobar','a']:
			query = {'info_hash':'\0'*20,'peer_id':'A'*20,'port':1025,'uploaded':i,'downloaded':0,'left':0}
			
			try:
				self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
			except urllib2.HTTPError, e:
				self.assertEqual(e.code, 400)
				self.assertIn('uploaded',e.read())
				continue
			self.assertTrue(False)

	def test_badDownloaded(self):
		for i in [-1,'foobar','a']:
			query = {'info_hash':'\0'*20,'peer_id':'A'*20,'port':1025,'uploaded':0,'downloaded':i,'left':0}
			
			try:
				self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
			except urllib2.HTTPError, e:
				self.assertEqual(e.code, 400)
				self.assertIn('downloaded',e.read())
				continue
			self.assertTrue(False)

	def test_badLeft(self):
		for i in [-1,'foobar','a']:
			query = {'info_hash':'\0'*20,'peer_id':'A'*20,'port':1025,'uploaded':0,'downloaded':0,'left':i}
			
			try:
				self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
			except urllib2.HTTPError, e:
				self.assertEqual(e.code, 400)
				self.assertIn('left',e.read())
				continue
			self.assertTrue(False)
		

class TrackerTest(unittest.TestCase):
	def setUp(self):
		logger = logging.getLogger('fairywren')
		logger.setLevel(logging.DEBUG)
		#logger.addHandler(logging.StreamHandler())
		
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
