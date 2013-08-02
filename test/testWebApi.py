import unittest
import webapi
import fairywren
import json
import urllib
import urllib2
import cookielib
import MultipartPostHandler
from wsgi_intercept.urllib2_intercept import install_opener

import wsgi_intercept

class MockStats(object):
	def getCount(self,info_hash):
		return (0,0)
		
class MockUsers(object):
	def getInfo(self,idNumber):
		return {'numberOfTorrents' : 0, 'name':'aTestUser', 'password' : fairywren.USER_PASSWORD_FMT % 1}

class MockAuth(object):
	def __init__(self):
		self._authenticateUser = 1
	
	def authenticateUser(self,username,password):
		return self._authenticateUser

class MockTorrents(object):
	def __init__(self):
		self._getTorrents = []
		self._getNumTorrents = 0
		self._getTorrentForDownload = None
		
	def getTorrentForDownload(self,torrentId,uid):
		return self._getTorrentForDownload
		
	def getTorrents(self,limit,subset):
		return self._getTorrents
		
	def getNumTorrents(self):
		return self._getNumTorrents

class WebApiTest(unittest.TestCase):
	def getWebapi(self):
		if self.webapi == None:
			self.webapi = webapi.Webapi(self.stats,self.users,self.auth,self.torrents,0,False)
		return self.webapi

		
	def setUp(self):
		self.webapi = None
		self.auth = MockAuth()
		self.stats = MockStats() 
		self.users = MockUsers()
		self.torrents = MockTorrents()
		
		install_opener()
		
		wsgi_intercept.add_wsgi_intercept('webapi',80,self.getWebapi)
		self.urlopen = urllib2.urlopen

class AuthenticatedWebApiTest(WebApiTest):
	def setUp(self):
		
		WebApiTest.setUp(self)
		request = urllib2.Request('http://webapi/session',data=urllib.urlencode({'username':'auser','password':'0'*86}))
		response = self.urlopen(request)
		cookies = cookielib.CookieJar()
	
		cookies.extract_cookies(response,request)
	
		self.urlopen = urllib2.build_opener(wsgi_intercept.urllib2_intercept.wsgi_urllib2.WSGI_HTTPHandler(),urllib2.HTTPCookieProcessor(cookies),MultipartPostHandler.MultipartPostHandler).open		

class TestDownloadTorrent(AuthenticatedWebApiTest):
	def test_truncatedPath(self):
		
		try:
			r = self.urlopen('http://webapi/torrents/0000000.torrent')
		except urllib2.HTTPError, e:
			self.assertEqual(404,e.code)
			r = e.read()
			self.assertNotIn('Torrent not found',r)
			return
		self.assertTrue(False)	
		
	def test_badPath(self):
		try:
			r = self.urlopen('http://webapi/torrents/FFFFFFFG.torrent')
		except urllib2.HTTPError, e:
			self.assertEqual(404,e.code)
			r = e.read()
			self.assertNotIn('Torrent not found',r)
			return
		self.assertTrue(False)			
		
	def test_unknownTorrent(self):
		
		try:
			r = self.urlopen('http://webapi/torrents/00000000.torrent')
		except urllib2.HTTPError, e:
			self.assertEqual(404,e.code)
			r = e.read()
			self.assertIn('Torrent not found',r)
			return
		self.assertTrue(False)

class TestGetTorrents(AuthenticatedWebApiTest):
	def test_ok(self):
		self.torrents._getTorrents = [{'infoHash':'0'*20}]
		r = self.urlopen('http://webapi/torrents')
		self.assertEqual(200,r.code)
		r = json.loads(r.read())
		self.assertIn('numSubsets',r)
		self.assertIn('torrents',r)
		self.assertGreaterEqual(len(r['torrents']),1)
		self.assertIn('seeds',r['torrents'][0])
		self.assertIn('leeches',r['torrents'][0])
		
	def test_badResultSize(self):
		try:
			self.urlopen('http://webapi/torrents?' + urllib.urlencode({'resultSize': 'meow','subset':1}))
		except urllib2.HTTPError,e:
			self.assertEqual(e.code,400)
			r = e.read()
			self.assertIn('resultSize',r)
			return
		self.assertTrue(False)

	def test_badSubset(self):
		try:
			self.urlopen('http://webapi/torrents?' + urllib.urlencode({'resultSize': 5,'subset':'meow'}))
		except urllib2.HTTPError,e:
			self.assertEqual(e.code,400)
			r = e.read()
			self.assertIn('subset',r)
			return
		self.assertTrue(False)

		
class TestSession(WebApiTest):
	def test_notLoggedIn(self):
		r = self.urlopen('http://webapi/session')
		self.assertEqual(r.code,200)
		r = json.loads(r.read())
		self.assertIn('authenticated',r)
		self.assertTrue ( not r['authenticated'])
		
	def test_login(self):
		r = self.urlopen('http://webapi/session',data=urllib.urlencode({'username':'auser','password':'0'*86}))
		self.assertEqual(r.code,200)
		r = json.loads(r.read())
		self.assertIn('authenticated',r)
		self.assertNotIn('error',r)
		self.assertTrue(r['authenticated'])
		
	def test_failedLogin(self):
		self.auth._authenticateUser = None
		r = self.urlopen('http://webapi/session',data=urllib.urlencode({'username':'auser','password':'0'*86}))
		self.assertEqual(r.code,200)
		r = json.loads(r.read())
		self.assertIn('error',r)
		
class TestAuthentication(WebApiTest):
	def test_downloadTorrent(self):
		r = self.urlopen('http://webapi/torrents')
		self.assertEqual(r.code,200)
		r = json.loads(r.read())
		self.assertIn('authenticated',r)
		self.assertTrue ( not r['authenticated'])
		
if __name__ == '__main__':
    unittest.main()

