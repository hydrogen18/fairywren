import fnmatch
import vanilla
import base64
import urlparse
import json
import uuid

def sendJsonWsgiResponse(env,start_response,response,additionalHeaders=None):
	headers = [('Content-Type','text/json')]
	headers.append(('Cache-Control','no-cache'))
	
	if additionalHeaders:
		headers += additionalHeaders
	
	start_response('200 OK',headers)
	
	yield json.dumps(response)

class SessionManager(object):
	class Session(object):
		__slots__ = ['username','sessionIdentifier']
		
		def __init__(self,username,sessionIdentifier):
			self.username = username
			self.sessionIdentifier = sessionIdentifier
			
		def getCookie(self):
			return ('Set-Cookie','session=%s HttpOnly; Secure' % str(self.sessionIdentifier))
			
	def __init__(self):
		self.sessions = {}
		
	def authorizeSession(self,sessionIdentifier):
		if sessionIdentifier in self.sessions:
			return self.sessions[sessionIdentifier]
		return None
			
	def startSession(self,username):
		for i, j in enumerate(self.sessions.iteritems()):
			sessionIdentifier,session = j
			if session.username == username:
				self.sessions.pop(sessionIdentifier)
				break
		
		newIdentifier = uuid.uuid4()
		
		self.sessions[newIdentififer] = Session(username,newIdentifier)
		return self.sessions[newIdentifier]
		
class Webapi(object):
	
	def login(self,env,start_response):
		if 'QUERY_STRING' not in env:
			return vanilla.http_error(400,env,start_response)
		
		query = urlparse.parse_qs(env['QUERY_STRING'])
		
		if 'username' not in query:
			return vanilla.http_error(400,env,start_response,msg='missing username')
		#Use first occurence from query string
		username = query['username'][0]
		
		if 'password' not in query:
			return vanilla.http_error(400,env,start_response,msg='missing password')
		#Use first occurence from query string
		password = query['password'][0]
		
		#Password comes across as 64 bytes of base64 encoded data
		#with trailing ='s lopped off. 
		
		password += '=='
		
		if len(password) != 88: #64 bytes in base64 is length 88
			return vanilla.http_error(400,env,start_response,msg='password too short')
		
		try:
			password = base64.urlsafe_b64decode(password)
		except TypeError:
			return vanilla.http_error(400,env,start_response,msg='password poorly formed')
		
		if not self.auth.authenticateUser(username,password):
			return sendJsonWsgiResponse(env,start_response,{'error':'bad username or password'})
		
		session = self.sm.startSession(username)
			
		return sendJsonWsgiResponse(env,start_response,{},additionalHeaders=
		[session.getCookie()])
		
	def listTorrents(self,env,start_response):
		return vanilla.http_error(501,env,start_response)
	
	def createTorrent(self,env,start_response):
		return vanilla.http_error(501,env,start_response)
		
	def downloadTorrent(self,env,start_response):
		return vanilla.http_error(501,env,start_response)
		
	def torrentInfo(self,env,start_response):
		return vanilla.http_error(501,env,start_response)
	
	def __init__(self,auth):
		self.auth = auth
		self.sm = SessionManager()
		self.resources = []
		self.resources.append(('/session','PUT',self.login))
		self.resources.append(('/torrents','GET',self.listTorrents))
		self.resources.append(('/torrents','PUT',self.createTorrent))
		self.resources.append(('/torrents/*.json','GET',self.torrentInfo))
		self.resources.append(('/torrents/*.torrent','GET',self.downloadTorrent))
		
	def __call__(self,env,start_response):
		
		pathInfo = env['PATH_INFO']
		requestMethod = env['REQUEST_METHOD']
		
		errorCode = 404
		
		for pattern,method,function in self.resources:
			
			if fnmatch.fnmatch(pathInfo,pattern):
				errorCode = 405
				if requestMethod == method:
					return function(env,start_response)
				
		return vanilla.http_error(errorCode,env,start_response)
		
