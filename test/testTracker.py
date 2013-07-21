import unittest
import peers
import tracker
import socket
import urllib
import bencode
import logging
import logging.handlers
import base64

from wsgi_intercept.urllib2_intercept import install_opener
import wsgi_intercept

remoteAddr = '127.0.0.1'
make_environ = wsgi_intercept.make_environ		
def make_environ_wrapper(*args,**kwargs):
	retval = make_environ(*args,**kwargs)

	retval['REMOTE_ADDR'] = remoteAddr 
	return retval

wsgi_intercept.make_environ = make_environ_wrapper
		

import urllib2

class MockAuth(object):
	def authenticateSecretKey(self,key):
		return True
		
	def authorizeInfoHash(self,info_hash):
		return True

class WSGITrackerTest(unittest.TestCase):
	def createTracker(self):
		if self.tracker == None:
			self.tracker = tracker.Tracker(MockAuth(),peers.Peers(0),0)
		return self.tracker 

		
	def setUp(self):
		self.tracker = None
		install_opener()
		
		wsgi_intercept.add_wsgi_intercept('tracker',80,self.createTracker)
		self.urlopen = urllib2.urlopen
		
class PathLopping(unittest.TestCase):
	def test_lopping(self):
		
		for i in range(0,2**7):
			def mkTracker():
				return tracker.Tracker(MockAuth(),peers.Peers(0),i)
				
			wsgi_intercept.add_wsgi_intercept('tracker',80,mkTracker)
			query = {'peer_id':'A'*20,'port':1025,'uploaded':0,'downloaded':0,'left':0,'info_hash':'C'*20}
			
			r = urllib2.urlopen('http://tracker/' + 'a/'*i + 86*'0' + '/announce?' + urllib.urlencode(query))
			r = r.read()
			r = bencode.bdecode(r)
			self.assertIn('peers',r)
			self.assertIn('interval',r)				
			self.assertRaisesRegexp(urllib2.HTTPError,'.*404.*',urllib2.urlopen,'http://tracker/' + 'a/'*(i+1) + 86*'0' + '/announce?' + urllib.urlencode(query))
		
class Unauthorized(WSGITrackerTest):
	def authenticateSecretKey(self,key):
		return key in self.keys
	
	def authorizeInfoHash(self,info_hash):
		return info_hash in self.info_hashes
	
	def createTracker(self):

		return tracker.Tracker(self,peers.Peers(0),0)
		
	def test_UnauthSecretKey(self):
		self.keys = ['0'*64]
		self.info_hashes = []
		query = {'peer_id':'A'*20,'port':1025,'uploaded':0,'downloaded':0,'left':0,'info_hash':'C'*20}
		
		r = self.urlopen('http://tracker/' + 86*'A' + '/announce?' + urllib.urlencode(query))
		r = bencode.bdecode(r.read())
		self.assertIn('failure reason',r)
		self.assertIn('secret key',r['failure reason'])
		
	def test_UnauthInfoHash(self):
		self.keys = ['0'*64]
		self.info_hashes = []
		query = {'peer_id':'A'*20,'port':1025,'uploaded':0,'downloaded':0,'left':0,'info_hash':'C'*20}
		
		r = self.urlopen('http://tracker/' + base64.urlsafe_b64encode(self.keys[0]).replace('=','') + '/announce?' + urllib.urlencode(query))
		r = bencode.bdecode(r.read())
		self.assertIn('failure reason',r)
		self.assertIn('info hash',r['failure reason'])		
		
	def test_authd(self):
		self.keys = ['0'*64]
		self.info_hashes = ['C'*20]
		query = {'peer_id':'A'*20,'port':1025,'uploaded':0,'downloaded':0,'left':0,'info_hash':'C'*20}
		
		r = self.urlopen('http://tracker/' + base64.urlsafe_b64encode(self.keys[0]).replace('=','') + '/announce?' + urllib.urlencode(query))
		r = bencode.bdecode(r.read())
		self.assertIn('peers',r)
		self.assertIn('interval',r)				
	
class BadAnnounce(WSGITrackerTest):
	def test_badSecretKey(self):
		for i in range(1,86):
			self.assertRaisesRegexp(urllib2.HTTPError, '.*404.*', self.urlopen,'http://tracker/' + i*'0' + '/announce')
		
	def test_misingInfoHash(self):
		query = {'peer_id':'A'*20,'port':1025,'uploaded':0,'downloaded':0,'left':0}
		
		try:
			self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
		except urllib2.HTTPError, e:
			self.assertEqual(e.code, 400)
			r = e.read()
			self.assertIn('missing',r)
			self.assertIn('info_hash',r)
			return
		self.assertTrue(False)		

	def test_misingPeerId(self):
		query = {'info_hash':'A'*20,'port':1025,'uploaded':0,'downloaded':0,'left':0}
		
		try:
			self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
		except urllib2.HTTPError, e:
			self.assertEqual(e.code, 400)
			r = e.read()
			self.assertIn('missing',r)
			self.assertIn('peer_id',r)
			return
		self.assertTrue(False)		

	def test_misingPort(self):
		query = {'info_hash':'A'*20,'peer_id':'B'*20,'uploaded':0,'downloaded':0,'left':0}
		
		try:
			self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
		except urllib2.HTTPError, e:
			self.assertEqual(e.code, 400)
			r = e.read()
			self.assertIn('missing',r)
			self.assertIn('port',r)
			return
		self.assertTrue(False)		
		
	def test_misingUploaded(self):
		query = {'info_hash':'A'*20,'peer_id':'B'*20,'port':1025,'downloaded':0,'left':0}
		
		try:
			self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
		except urllib2.HTTPError, e:
			self.assertEqual(e.code, 400)
			r = e.read()
			self.assertIn('missing',r)
			self.assertIn('uploaded',r)
			return
		self.assertTrue(False)			
		
	def test_misingDownloaded(self):
		query = {'info_hash':'A'*20,'peer_id':'B'*20,'port':1025,'uploaded':0,'left':0}
		
		try:
			self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
		except urllib2.HTTPError, e:
			self.assertEqual(e.code, 400)
			r = e.read()
			self.assertIn('missing',r)
			self.assertIn('downloaded',r)
			return
		self.assertTrue(False)					

	def test_misingLeft(self):
		query = {'info_hash':'A'*20,'peer_id':'B'*20,'port':1025,'uploaded':0,'downloaded':0}
		
		try:
			self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
		except urllib2.HTTPError, e:
			self.assertEqual(e.code, 400)
			r = e.read()
			self.assertIn('missing',r)
			self.assertIn('left',r)
			return
		self.assertTrue(False)					
		
	def test_badInfoHash(self):
		for i in range(1,20):
			query = {'info_hash':i*'\0','peer_id':'A'*20,'port':1025,'uploaded':0,'downloaded':0,'left':0}
			
			try:
				self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
			except urllib2.HTTPError, e:
				self.assertEqual(e.code, 400)
				r = e.read()
				self.assertIn('bad value',r)
				self.assertIn('info_hash',r)
				continue
			self.assertTrue(False)

	def test_badPeerId(self):
		for i in range(1,20):
			query = {'info_hash':'\0'*20,'peer_id':'A'*i,'port':1025,'uploaded':0,'downloaded':0,'left':0}
			
			try:
				self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
			except urllib2.HTTPError, e:
				self.assertEqual(e.code, 400)
				r = e.read()
				self.assertIn('bad value',r)
				self.assertIn('peer_id',r)
				continue
			self.assertTrue(False)

	def test_badPort(self):
		for i in [-1,0,2**16]:
			query = {'info_hash':'\0'*20,'peer_id':'A'*20,'port':i,'uploaded':0,'downloaded':0,'left':0}
			
			try:
				self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
			except urllib2.HTTPError, e:
				self.assertEqual(e.code, 400)
				r = e.read()
				self.assertIn('bad value',r)
				self.assertIn('port',r)
				continue
			self.assertTrue(False)

	def test_badUploaded(self):
		for i in [-1,'foobar','a']:
			query = {'info_hash':'\0'*20,'peer_id':'A'*20,'port':1025,'uploaded':i,'downloaded':0,'left':0}
			
			try:
				self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
			except urllib2.HTTPError, e:
				self.assertEqual(e.code, 400)
				r = e.read()
				self.assertIn('bad value',r)
				self.assertIn('uploaded',r)
				continue
			self.assertTrue(False)

	def test_badDownloaded(self):
		for i in [-1,'foobar','a']:
			query = {'info_hash':'\0'*20,'peer_id':'A'*20,'port':1025,'uploaded':0,'downloaded':i,'left':0}
			
			try:
				self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
			except urllib2.HTTPError, e:
				self.assertEqual(e.code, 400)
				r = e.read()
				self.assertIn('bad value',r)
				self.assertIn('downloaded',r)
				continue
			self.assertTrue(False)

	def test_badLeft(self):
		for i in [-1,'foobar','a']:
			query = {'info_hash':'\0'*20,'peer_id':'A'*20,'port':1025,'uploaded':0,'downloaded':0,'left':i}
			
			try:
				self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
			except urllib2.HTTPError, e:
				self.assertEqual(e.code, 400)
				r = e.read()
				self.assertIn('bad value',r)
				self.assertIn('left',r)
				continue
			self.assertTrue(False)
			
	def test_badNumwant(self):
		for i in [-1,'foobar','a']:
			query = {'info_hash':'\0'*20,'peer_id':'A'*20,'port':1025,'uploaded':0,'downloaded':0,'left':0,'numwant':i}
			
			try:
				self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
			except urllib2.HTTPError, e:
				self.assertEqual(e.code, 400)
				r = e.read()
				self.assertIn('bad value',r)
				self.assertIn('numwant',r)
				continue
			self.assertTrue(False)			
			
	def test_badEvent(self):
		for i in ['foo','bar','qux',42]:
			query = {'info_hash':'\0'*20,'peer_id':'A'*20,'port':1025,'uploaded':0,'downloaded':0,'left':0,'event':i}
			
			try:
				self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
			except urllib2.HTTPError, e:
				self.assertEqual(e.code, 400)
				r = e.read()
				self.assertIn('bad value',r)
				self.assertIn('event',r)
				continue
			self.assertTrue(False)		
				
	def test_badCompact(self):
		for i in ['foo','bar','qux']:
			query = {'info_hash':'\0'*20,'peer_id':'A'*20,'port':1025,'uploaded':0,'downloaded':0,'left':0,'compact':i}
			
			try:
				self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
			except urllib2.HTTPError, e:
				self.assertEqual(e.code, 400)
				r = e.read()
				self.assertIn('bad value',r)
				self.assertIn('compact',r)
				continue
			self.assertTrue(False)				
		

class TrackerTest(WSGITrackerTest):
	def test_addingPeers(self):
		peerList = []
		for peerIp in range(1,32):
			peerList.append(('192.168.0.' + str(peerIp),peerIp%4 + 1025))
			
		info_hashes = (chr(i)*20 for i in range(0,128))
			
		for info_hash in info_hashes:
			for cnt,peer in enumerate(peerList):
				peerIp,peerPort = peer
				global remoteAddr
				remoteAddr = peerIp
				
				query = {}
				query['info_hash'] = info_hash
				query['peer_id'] = '0'*20
				query['port'] = peerPort
				query['uploaded'] = 0
				query['downloaded'] = 0 
				query['left'] = 128
				query['compact'] = 0
				query['event'] = 'started'
				r = self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
				self.assertEqual(200,r.code)
				
				response = bencode.bdecode(r.read())
				self.assertIn('peers',response)
				self.assertEqual(len(response['peers']),cnt+1)
				
	def test_compactResponse(self):
		global remoteAddr
		peerList = []
		for peerIp in range(1,32):
			peerList.append(('192.168.0.' + str(peerIp),peerIp%4 + 1025))
			
		info_hashes = [chr(i)*20 for i in range(0,128)]
			
		for info_hash in info_hashes:
			for cnt,peer in enumerate(peerList):
				peerIp,peerPort = peer
				remoteAddr = peerIp
				
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
				
				r = self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
				self.assertEqual(200,r.code)
				
				response = bencode.bdecode(r.read())
				self.assertIn('peers',response)
				self.assertEqual(len(response['peers']),(cnt+1)*6)
		
		#Test Update events
		for info_hash in info_hashes:
			for peer in peerList:
				peerIp,peerPort = peer

				remoteAddr = peerIp
				
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
				
				r = self.urlopen('http://tracker/' + 86*'0' + '/announce?' + urllib.urlencode(query))
				self.assertEqual(200,r.code)
				response = bencode.bdecode(r.read())
				self.assertIn('peers',response)

				self.assertEqual(len(response['peers']),len(peerList)*6)
				
if __name__ == '__main__':
    unittest.main()
