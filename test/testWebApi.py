import unittest
import webapi
import fairywren
import json
import urllib
import urllib2
import cookielib
import MultipartPostHandler
from wsgi_intercept.urllib2_intercept import install_opener
import tempfile
import bencode
import torrents
import types
import datetime
import base64
import itertools
import wsgi_intercept
import users
import collections

class MockStats(object):
	def __init__(self):
		self._getCount = (0,0)
	def getCount(self,info_hash):
		return self._getCount
		
class MockUsers(unittest.TestCase):
	def __init__(self):
		self._getInfo = {'numberOfTorrents' : 0, 'name':'aTestUser', 'password' : fairywren.USER_PASSWORD_FMT % 1}
		self._addUser = None
		self._getInviteState = False
		self._createInvite = None
		self._listInvitesByUser  = []
		self._claimInvite = None
		self._getUserRoles = []
		self._setUserRoles = (0,0)
	
	def setUserRoles(self,roles,uid):
		self.assertIsInstance(roles,collections.Iterable)
		self.assertIsInstance(uid,types.IntType)
		return self._setUserRoles 
	
	def getUserRoles (self,uid):
		self.assertIsInstance(uid,types.IntType)
		return self._getUserRoles 
		
	def listInvitesByUser(self,uid):
		self.assertIsInstance(uid,types.IntType)
		return self._listInvitesByUser 	
		
	def getInfo(self,idNumber):
		self.assertIsInstance(idNumber,types.IntType)
		return self._getInfo
		
	def addUser(self,username,password):
		self.assertIsInstance(username,types.StringType)
		self.assertIsInstance(password,types.StringType)
		return self._addUser		
		
	def getInviteState(self,secret):
		self.assertIsInstance(secret,types.StringType)
		return self._getInviteState
		
	def createInvite(self,uid):
		self.assertIsInstance(uid,types.IntType)
		return self._createInvite
		
	def claimInvite(self,secret,username,password):
		self.assertIsInstance(username,types.StringType)
		self.assertIsInstance(password,types.StringType)
		return self._claimInvite

class MockAuth(object):
	def __init__(self):
		self._authenticateUser = 1
		
		self._isUserMemberOfRole = False
	
	def isUserMemberOfRole(self,userId,roles):
		return self._isUserMemberOfRole
	
	def authenticateUser(self,username,password):
		return self._authenticateUser
		
class MockTorrents(object):
	def __init__(self):
		self._getTorrents = []
		self._addTorrent = ('','')
		self._getNumTorrents = 0
		self._getTorrentForDownload = None
		self._getAnnounceUrlForUser = None
		self._searchTorrents  = []
		self._getInfo = None
		self._getExtendedInfo = None
		
	def getInfo(self,uid):
		return self._getInfo
		
	def getExtendedInfo(self,uid):
		return self._getExtendedInfo 
		
	def searchTorrents(self,tokens):
		return self._searchTorrents
	
	def addTorrent(self,torrent,title,creator,extended=None):
		return self._addTorrent
	def getTorrentForDownload(self,torrentId,uid):
		return self._getTorrentForDownload
		
	def getTorrents(self,limit,subset):
		return self._getTorrents
		
	def getNumTorrents(self):
		return self._getNumTorrents

	def getAnnounceUrlForUser(self,id):
		return self._getAnnounceUrlForUser
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

class TestGetNonExistentInvite(WebApiTest):
	def test_getNonExistentInvite(self):
		def failure(secret):
			raise ValueError()
		self.users.getInviteState = failure
		try:
			r = self.urlopen('http://webapi/invites/' + '0'*43)
		except urllib2.HTTPError as e:
			self.assertEqual(404,e.code)
			r = e.read()
			return
		self.assertTrue(False)

class TestClaimInviteFail(WebApiTest):
	def test_claimNonExistentInvite(self):
		def failure(secret,username,pw):
			raise ValueError()
		self.users.claimInvite = failure
		try:
			r = self.urlopen('http://webapi/invites/' + '0'*43  ,data=urllib.urlencode({'password':'0'*86,'username':'foo'}))
		except urllib2.HTTPError as e:
			self.assertEqual(404,e.code)
			r = e.read()
			return
		self.assertTrue(False)
		
	def test_claimInviteUserExists(self):
		def failure(secret,username,pw):
			raise users.UserAlreadyExists()
		self.users.claimInvite = failure
		try:
			r = self.urlopen('http://webapi/invites/' + '0'*43  ,data=urllib.urlencode({'password':'0'*86,'username':'foo'}))
		except urllib2.HTTPError as e:
			self.assertEqual(409,e.code)
			r = e.read()
			return
		self.assertTrue(False)		
		
class TestClaimInvite(WebApiTest):
	def test_claimInvite(self):
		self.users._claimInvite = 'FOO'
		
		r = self.urlopen('http://webapi/invites/' + '0'*43  ,data=urllib.urlencode({'password':'0'*86,'username':'foo'}))
		
		self.assertEqual(200,r.code)
		r = json.loads(r.read())
		self.assertIn('href',r)
		self.assertNotIn('error',r)	

class TestGetInvite(WebApiTest):
	def test_getInviteClaimed(self):
		self.users._getInviteState = True
		r = self.urlopen('http://webapi/invites/' + '0'*43)
		self.assertEqual(200,r.code)
		r = json.loads(r.read())
		self.assertIn('claimed',r)
		self.assertEqual(True,r['claimed'])

	def test_getInviteUnclaimed(self):
		self.users._getInviteState = False
		r = self.urlopen('http://webapi/invites/' + '0'*43)
		self.assertEqual(200,r.code)
		r = json.loads(r.read())
		self.assertIn('claimed',r)
		self.assertEqual(False,r['claimed'])
		
	def test_wholeKeyspace(self):
		#this test is a good idea but takes too long to run
		return 
		keys = [chr(i) for i in range(0,255)]
		keyspace = []
		for _ in range(0,32):
			keyspace.append(keys)
		
		for x in itertools.product(*keyspace):
			r = self.urlopen('http://webapi/invites/' + base64.urlsafe_b64encode(''.join(x)).replace('=',''))
			self.assertEqual(200,r.code)
			r = json.loads(r.read())
			self.assertIn('claimed',r)
		
		
class TestGetListOfInvites(AuthenticatedWebApiTest):
	def test_noAuth(self):
		r = self.urlopen('http://webapi/users/000000FF/invites')	
		self.assertEqual(200,r.code)
		r = json.loads(r.read())
		self.assertIn('authorized',r)
		self.assertIn('error',r)
		self.assertEqual(False,r['authorized'])
		self.assertNotIn('invites',r)

	def test_auth(self):
		r = self.urlopen('http://webapi/users/00000001/invites')	
		self.assertEqual(200,r.code)
		r = json.loads(r.read())
		self.assertNotIn('error',r)
		self.assertIn('invites',r)
		
	def test_ok(self):
		self.users._listInvitesByUser = [{'created':datetime.datetime.now(),'href':'foo'}]
		r = self.urlopen('http://webapi/users/00000001/invites')
		self.assertEqual(200,r.code)
		r = json.loads(r.read())
		self.assertNotIn('error',r)
		self.assertIn('invites',r)		
		self.assertEqual(len(r['invites']),1)
		
class TestCreateInvite(AuthenticatedWebApiTest):
	def test_createInvite(self):
		self.users._createInvite = 'FOO'
		self.auth._isUserMemberOfRole = True
		r = self.urlopen('http://webapi/invites',data='')
		self.assertEqual(200,r.code)
		r = json.loads(r.read())
		self.assertIn('href',r)
		self.assertIsInstance(r['href'],types.UnicodeType)		

class TestTorrentInfo(AuthenticatedWebApiTest):
	def test_badTorrentId(self):
		try:
			r = self.urlopen('http://webapi/torrents/0000000G.json')
		except urllib2.HTTPError as e:
			self.assertEqual(404,e.code)
			return
		self.assertTrue(False)
	def test_missingTorrent(self):
		try:
			r = self.urlopen('http://webapi/torrents/00000000.json')
		except urllib2.HTTPError as e:
			self.assertEqual(404,e.code)
			r = e.read()
			self.assertIn('no such torrent',r)
			return
		self.assertTrue(False)
		
	def test_ok(self):
		
		self.torrents._getInfo = {'test':'foo'}
		self.torrents._getExtendedInfo = {'test': 'bar'}
		r = self.urlopen('http://webapi/torrents/00000000.json')
		self.assertEqual(r.code,200)
		r = json.loads(r.read())
		self.assertIn('test',r)
		self.assertEqual(self.torrents._getInfo['test'],r['test'])
		
		self.assertIn('extended',r)
		self.assertEqual(self.torrents._getExtendedInfo,r['extended'])

class TestTorrentSearch(AuthenticatedWebApiTest):
	def test_noTokens(self):
		try:
			r  = self.urlopen('http://webapi/torrents?' + urllib.urlencode({"search": 1 }))
		except urllib2.HTTPError as e:
			self.assertEqual(e.code,400)
			r = e.read()
			
			self.assertIn('one instance',r)
			return
			
		self.assertTrue(False)
		
	def test_tooManyTokens(self):
		try:
			r  = self.urlopen('http://webapi/torrents?' + urllib.urlencode({"search": 1 , "token":range(0,10)},doseq=True))
		except urllib2.HTTPError as e:
			self.assertEqual(e.code,400)
			r = e.read()
			self.assertIn('more than',r)
			self.assertIn('tokens',r)
			return
			
		self.assertTrue(False)
			
	def test_ok(self):
		NUM_TORRENTS = 100
			
		for numTokens in range(1,5):
			self.torrents._searchTorrents = [  {'infoHash':str(i).zfill(20)} for i in range(0,NUM_TORRENTS) ]
			r  = self.urlopen('http://webapi/torrents?' + urllib.urlencode({"search": 1 , "token":range(0,numTokens)},doseq=True))
			self.assertEqual(r.code,200)
			r = json.loads(r.read())
			self.assertIn('torrents',r)
			self.assertEqual(len(r['torrents']),NUM_TORRENTS)
			for torrent in r['torrents']:
				self.assertIn('leeches',torrent)
				self.assertIsInstance(torrent['leeches'],int)
				self.assertIn('seeds',torrent)
				self.assertIsInstance(torrent['seeds'],int)
				
			
			
class TestSession(AuthenticatedWebApiTest):
	def test_getSession(self):
		r = self.urlopen('http://webapi/session')
		self.assertEqual(r.code,200)
		r = json.loads(r.read())
		self.assertNotIn('error',r)
		self.assertIn('my',r)
		self.assertIn('href',r['my'])

class TestDownloadTorrent(AuthenticatedWebApiTest):
	
	def test_ok(self):
		orig = {'info': {'length': 65535, 'pieces': '\xc7\xbc\x832]\x80\xfc\xe0\x94\xdf\xf0%\xeds\x1c\xa5\xcb\x02&v', 'piece length': 262144, 'private': 1, 'name': 'tmpRBmSP2'}, 'announce': 'http://127.0.0.1/announce'}
		self.torrents._getTorrentForDownload = torrents.Torrent.fromDict(orig)
		
		r = self.urlopen('http://webapi/torrents/00000000.torrent')
		self.assertEqual(200,r.code)
		raw = r.read()
		returned = bencode.bdecode(raw)
		self.assertEqual(returned,orig)
		
		torrents.Torrent.fromBencodedData(raw)
		
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
		
		

class TestCreateTorrent(AuthenticatedWebApiTest):
	def test_wrongPostContentType(self):
		try:
			self.urlopen('http://webapi/torrents',data=urllib.urlencode({'foo':5}))
		except urllib2.HTTPError,e:
			self.assertEqual(415,e.code)
			return
		self.assertTrue(False)
		
	def test_postNoTorrent(self):
		with tempfile.TemporaryFile() as tmpfile:
			try:
				self.urlopen('http://webapi/torrents',data={'title':'42','nottorrent':tmpfile})
			except urllib2.HTTPError,e:
				self.assertEqual(400,e.code)
				r = e.read()
				self.assertIn('missing',r)
				return
		self.assertTrue(False)
		
	def test_postNoTitle(self):
		with tempfile.TemporaryFile() as tmpfile:
			try:
				self.urlopen('http://webapi/torrents',data={'nottitle':'42','torrent':tmpfile})
			except urllib2.HTTPError,e:
				self.assertEqual(400,e.code)
				r = e.read()
				self.assertIn('missing',r)
				return
		self.assertTrue(False)		
		
	def test_postInvalidTorrent(self):
		with tempfile.TemporaryFile() as tmpfile:
			tmpfile.write('afjdasklfjdaskjf')
			tmpfile.flush()
			try:
				self.urlopen('http://webapi/torrents',data={'title':'42','torrent':tmpfile})
			except urllib2.HTTPError,e:
				self.assertEqual(400,e.code)
				r = e.read()
				self.assertIn('not bencoded data',r)
				return
		self.assertTrue(False)				
		
	def test_ok(self):
		self.torrents._getAnnounceUrlForUser = 'http://foobar'
		with tempfile.TemporaryFile() as tmpfile:
			torrent = {'info': {'length': 65535, 'pieces': '\xc7\xbc\x832]\x80\xfc\xe0\x94\xdf\xf0%\xeds\x1c\xa5\xcb\x02&v', 'piece length': 262144, 'private': 1, 'name': 'tmpRBmSP2'}, 'announce': self.torrents._getAnnounceUrlForUser}

			tmpfile.write(bencode.bencode(torrent))
			tmpfile.flush()
			r = self.urlopen('http://webapi/torrents',data={'title':'42','torrent':tmpfile})
			self.assertEqual(200,r.code)
			r = json.loads(r.read())
			self.assertIn('redownload',r)
			self.assertEqual(False,r['redownload'])
			self.assertIn('metainfo',r)
			self.assertIn('href',r['metainfo'])
			self.assertIn('info',r)
			self.assertIn('href',r['info'])
			
	def test_okWithExtendedData(self):
		self.torrents._getAnnounceUrlForUser = 'http://foobar'
		with tempfile.TemporaryFile() as tmpfile:
			torrent = {'info': {'length': 65535, 'pieces': '\xc7\xbc\x832]\x80\xfc\xe0\x94\xdf\xf0%\xeds\x1c\xa5\xcb\x02&v', 'piece length': 262144, 'private': 1, 'name': 'tmpRBmSP2'}, 'announce': self.torrents._getAnnounceUrlForUser}

			tmpfile.write(bencode.bencode(torrent))
			tmpfile.flush()
			r = self.urlopen('http://webapi/torrents',data={'title':'42','torrent':tmpfile , 'extended':json.dumps({'foo':'bar'})})
			self.assertEqual(200,r.code)
			r = json.loads(r.read())
			self.assertIn('redownload',r)
			self.assertEqual(False,r['redownload'])
			self.assertIn('metainfo',r)
			self.assertIn('href',r['metainfo'])
			self.assertIn('info',r)
			self.assertIn('href',r['info'])		
			
	def test_badExtendedData(self):
		self.torrents._getAnnounceUrlForUser = 'http://foobar'
		with tempfile.TemporaryFile() as tmpfile:
			torrent = {'info': {'length': 65535, 'pieces': '\xc7\xbc\x832]\x80\xfc\xe0\x94\xdf\xf0%\xeds\x1c\xa5\xcb\x02&v', 'piece length': 262144, 'private': 1, 'name': 'tmpRBmSP2'}, 'announce': self.torrents._getAnnounceUrlForUser}

			tmpfile.write(bencode.bencode(torrent))
			tmpfile.flush()
			try:
				r = self.urlopen('http://webapi/torrents',data={'title':'42','torrent':tmpfile , 'extended':'sadfasdfdsf'})
			except urllib2.HTTPError as e:
				self.assertEqual(400,e.code)
				r = e.read()
				self.assertIn('bad extended',r)
				return
			self.assertTrue(False)

	def test_extendedDataNotDict(self):
		self.torrents._getAnnounceUrlForUser = 'http://foobar'
		with tempfile.TemporaryFile() as tmpfile:
			torrent = {'info': {'length': 65535, 'pieces': '\xc7\xbc\x832]\x80\xfc\xe0\x94\xdf\xf0%\xeds\x1c\xa5\xcb\x02&v', 'piece length': 262144, 'private': 1, 'name': 'tmpRBmSP2'}, 'announce': self.torrents._getAnnounceUrlForUser}

			tmpfile.write(bencode.bencode(torrent))
			tmpfile.flush()
			try:
				r = self.urlopen('http://webapi/torrents',data={'title':'42','torrent':tmpfile , 'extended':'5'})
			except urllib2.HTTPError as e:
				self.assertEqual(400,e.code)
				r = e.read()
				self.assertIn('must be dict',r)
				return
			self.assertTrue(False)

			
	def test_bencodedTorrentButMissing(self):
		with tempfile.TemporaryFile() as tmpfile:
			torrent = {'info': {'length': 65535, 'pieces': '\xc7\xbc\x832]\x80\xfc\xe0\x94\xdf\xf0%\xeds\x1c\xa5\xcb\x02&v', 'piece length': 262144, 'private': 1, 'name': 'tmpRBmSP2'}}

			tmpfile.write(bencode.bencode(torrent))
			tmpfile.flush()
			try:
				 self.urlopen('http://webapi/torrents',data={'title':'42','torrent':tmpfile})
			except urllib2.HTTPError,e:
				self.assertEqual(400,e.code)
				r = e.read()
				self.assertIn('missing',r)
				return
			self.assertTrue(False)
			
	def test_needsRedownload(self):
		self.torrents._getAnnounceUrlForUser = 'http://foobar'
		
		with tempfile.TemporaryFile() as tmpfile:
			torrent = {'info': {'length': 65535, 'pieces': '\xc7\xbc\x832]\x80\xfc\xe0\x94\xdf\xf0%\xeds\x1c\xa5\xcb\x02&v', 'piece length': 262144,  'name': 'tmpRBmSP2','private': 1}, 'announce': 'http://localhost'}

			tmpfile.write(bencode.bencode(torrent))
			tmpfile.flush()
			r = self.urlopen('http://webapi/torrents',data={'title':'42','torrent':tmpfile})
			self.assertEqual(200,r.code)
			r = json.loads(r.read())
			self.assertIn('redownload',r)
			self.assertEqual(True,r['redownload'])
			self.assertIn('metainfo',r)
			self.assertIn('href',r['metainfo'])
			self.assertIn('info',r)
			self.assertIn('href',r['info'])		
		
		with tempfile.TemporaryFile() as tmpfile:
			torrent = {'info': {'length': 65535, 'pieces': '\xc7\xbc\x832]\x80\xfc\xe0\x94\xdf\xf0%\xeds\x1c\xa5\xcb\x02&v', 'piece length': 262144,  'name': 'tmpRBmSP2'}, 'announce': self.torrents._getAnnounceUrlForUser}

			tmpfile.write(bencode.bencode(torrent))
			tmpfile.flush()
			r = self.urlopen('http://webapi/torrents',data={'title':'42','torrent':tmpfile})
			self.assertEqual(200,r.code)
			r = json.loads(r.read())
			self.assertIn('redownload',r)
			self.assertEqual(True,r['redownload'])
			self.assertIn('metainfo',r)
			self.assertIn('href',r['metainfo'])
			self.assertIn('info',r)
			self.assertIn('href',r['info'])		
			
		with tempfile.TemporaryFile() as tmpfile:
			torrent = {'info': {'length': 65535, 'pieces': '\xc7\xbc\x832]\x80\xfc\xe0\x94\xdf\xf0%\xeds\x1c\xa5\xcb\x02&v', 'piece length': 262144, 'private': 1, 'name': 'tmpRBmSP2'}, 'announce-list': [['http://127.0.0.1/announce']]}

			tmpfile.write(bencode.bencode(torrent))
			tmpfile.flush()
			r = self.urlopen('http://webapi/torrents',data={'title':'42','torrent':tmpfile})
			self.assertEqual(200,r.code)
			r = json.loads(r.read())
			self.assertIn('redownload',r)
			self.assertEqual(True,r['redownload'])
			self.assertIn('metainfo',r)
			self.assertIn('href',r['metainfo'])
			self.assertIn('info',r)
			self.assertIn('href',r['info'])				

class TestGetUserInfo(AuthenticatedWebApiTest):
	def test_badUserId(self):
		try:
			self.urlopen('http://webapi/users/000000FG')
		except urllib2.HTTPError,e:
			self.assertEqual(404,e.code)
			return
		self.assertTrue(False)

	def test_userDoesntExist(self):
		self.users._getInfo = None 
		try:
			self.urlopen('http://webapi/users/000000FF')
		except urllib2.HTTPError,e:
			self.assertEqual(404,e.code)
			return
		self.assertTrue(False)


	def test_ok(self):
		self.users._getInfo = {'numberOfTorrents' : 23, 'name':'aTestUser', 'password' : {'href' : fairywren.USER_PASSWORD_FMT % 1 }}
		
		r = self.urlopen('http://webapi/users/000000FF')
		self.assertEqual(200,r.code)
		r = json.loads(r.read())
		self.assertIn('numberOfTorrents',r)
		self.assertIn('name',r)
		self.assertIn('password',r)
		self.assertIn('href',r['password'])
		self.assertNotIn('announce',r)
		self.assertEqual(r['numberOfTorrents'],self.users._getInfo['numberOfTorrents'])
		
	def test_getself(self):
		self.users._getInfo = {'numberOfTorrents' : 23, 'name':'aTestUser', 'password' : {'href' : fairywren.USER_PASSWORD_FMT % 1 }}
		self.torrents._getAnnounceUrlForUser = 'http://foobar'
		r = self.urlopen('http://webapi/users/%.8x' % self.auth._authenticateUser)
		self.assertEqual(200,r.code)
		r = json.loads(r.read())
		self.assertIn('numberOfTorrents',r)
		self.assertIn('name',r)
		self.assertIn('password',r)
		self.assertIn('href',r['password'])
		self.assertIn('announce',r)
		self.assertIn('href',r['announce'])
		self.assertEqual(self.torrents._getAnnounceUrlForUser,r['announce']['href'])
		self.assertEqual(r['numberOfTorrents'],self.users._getInfo['numberOfTorrents'])		

class TestUserAlreadyExists(AuthenticatedWebApiTest):
	def test_test(self):
		def mock(username,password):
			raise users.UserAlreadyExists()
		self.users.addUser = mock
		self.auth._isUserMemberOfRole = True
		try:
			self.urlopen('http://webapi/users', data= urllib.urlencode({'username':'foo','password':86*'0'}))
		except urllib2.HTTPError,e:
			self.assertEqual(409,e.code)
			r = e.read()
			self.assertIn('user already exists',r)
			return
		self.assertTrue(False)

class TestAddUser(AuthenticatedWebApiTest):
	def test_ok(self):
		self.users._addUser = 'FOO',0
		self.auth._isUserMemberOfRole = True
		
		r = self.urlopen('http://webapi/users', data= urllib.urlencode({'username':'foo','password':86*'0'}))
		self.assertEqual(200,r.code)
		r = json.loads(r.read())
		self.assertIn('href',r)
		self.assertEqual(r['href'],'FOO')
		
	def test_badPassword(self):
		self.users._addUser = 'meow',0
		self.auth._isUserMemberOfRole = True
		try:
			self.urlopen('http://webapi/users', data= urllib.urlencode({'username':'foo','password':85*'0'}))
		except urllib2.HTTPError,e:
			self.assertEqual(400,e.code)
			r = e.read()
			self.assertIn('password',r)
			self.assertIn('Bad value',r)
			return
		self.assertTrue(False)	
		
	def test_missingPassword(self):
		self.users._addUser = 'meow',0
		self.auth._isUserMemberOfRole = True
		try:
			self.urlopen('http://webapi/users', data= urllib.urlencode({'username':'foo'}))
		except urllib2.HTTPError,e:
			self.assertEqual(400,e.code)
			r = e.read()
			self.assertIn('password',r)
			self.assertIn('Missing',r)
			return
		self.assertTrue(False)							

class TestGetTorrents(AuthenticatedWebApiTest):
	def test_noparams(self):
		NUM_TORRENTS = 5
		self.torrents._getNumTorrents = NUM_TORRENTS
		self.torrents._getTorrents = [  {'infoHash':str(i).zfill(20)} for i in range(0,NUM_TORRENTS) ]
		self.stats._getCount = (2,3)
		r = self.urlopen('http://webapi/torrents')
		self.assertEqual(200,r.code)
		r = json.loads(r.read())
		self.assertIn('numSubsets',r)
		self.assertIn('torrents',r)
		self.assertEqual(r['numSubsets'],1)
		self.assertGreaterEqual(len(r['torrents']),1)
		self.assertIn('seeds',r['torrents'][0])
		self.assertEqual(2,r['torrents'][0]['seeds'])
		self.assertIn('leeches',r['torrents'][0])
		self.assertEqual(3,r['torrents'][0]['leeches'])
	
	def test_ok(self):
		NUM_TORRENTS = 100
		RESULT_SIZE = 20
		self.torrents._getNumTorrents = NUM_TORRENTS
		self.torrents._getTorrents = [  {'infoHash':str(i).zfill(20)} for i in range(0,NUM_TORRENTS) ]
		self.stats._getCount = (2,3)
		r = self.urlopen('http://webapi/torrents?' + urllib.urlencode({'resultSize':RESULT_SIZE}))
		self.assertEqual(200,r.code)
		r = json.loads(r.read())
		self.assertIn('numSubsets',r)
		self.assertIn('torrents',r)
		self.assertEqual(r['numSubsets'],NUM_TORRENTS/RESULT_SIZE)
		self.assertGreaterEqual(len(r['torrents']),RESULT_SIZE)
		
		for torrent in r['torrents']:
			self.assertIn('seeds',torrent)
			self.assertIn('leeches',torrent)
			
			self.assertIsInstance(torrent['leeches'],int)
			self.assertIsInstance(torrent['seeds'],int)
			
			self.assertEqual(2,torrent['seeds'])
			self.assertEqual(3,torrent['leeches'])
			
			
			
		
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

class TestGetSession(AuthenticatedWebApiTest):
	def test_it(self):
		r = self.urlopen('http://webapi/session')
		self.assertEqual(r.code,200)
		r = json.loads(r.read())
		self.assertNotIn('error',r)
		self.assertIn('my',r)
		self.assertIn('href',r['my'])
		
class TestRoles(AuthenticatedWebApiTest):
	def test_listRoles(self):
		r = self.urlopen('http://webapi/roles')
		self.assertEqual(r.code,200)
		r = json.loads(r.read())
		self.assertNotIn('error',r)
		self.assertIn('roles',r)
		self.assertNotEqual(0,len(r['roles']))
		
	def test_listUserRoles(self):
		self.users._getUserRoles = ['foo','bar','qux']
		r = self.urlopen('http://webapi/users/%.8x/roles' % self.auth._authenticateUser)
		self.assertEqual(r.code,200)
		r = json.loads(r.read())
		self.assertNotIn('error',r)
		self.assertIn('roles',r)
		self.assertEqual(self.users._getUserRoles,r['roles'])
		
		
	def test_changeRoles(self):
		def mock(self,*args,**kwargs):
			return True
		self.auth.isUserMemberOfRole = mock
		
		self.users._getUserRoles = ['foo','bar','qux']
		r = self.urlopen('http://webapi/users/%.8x/roles' % self.auth._authenticateUser, data= urllib.urlencode({'roles':self.users._getUserRoles}))
		self.assertEqual(r.code,200)
		r = json.loads(r.read())
		self.assertNotIn('error',r)
		self.assertIn('roles',r)
		self.assertEqual(self.users._getUserRoles,r['roles'])
		
		
		
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
		self.assertNotIn('error',r)
		self.assertIn('my',r)
		self.assertIn('href',r['my'])
		
		
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
		
	def test_changePassword(self):
		r = self.urlopen('http://webapi/users/00000000/password',data=urllib.urlencode({'password':'0'*86}))
		self.assertEqual(r.code,200)
		r = json.loads(r.read())
		self.assertIn('authenticated',r)
		self.assertTrue ( not r['authenticated'])
		

		
	
		
if __name__ == '__main__':
    unittest.main()

