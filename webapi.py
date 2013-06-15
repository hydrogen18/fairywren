import fnmatch
import vanilla
import base64
import urlparse
import json
import uuid
import itertools
import posixpath
import Cookie
import datetime
import multipart
import sys
import torrents
import logging

def sendJsonWsgiResponse(env,start_response,response,additionalHeaders=None):
	headers = [('Content-Type','text/json')]
	headers.append(('Cache-Control','no-cache'))
	
	if additionalHeaders:
		headers += additionalHeaders
	
	start_response('200 OK',headers)
	
	class DateTimeJSONEncoder(json.JSONEncoder):
		def default(self, obj):
			if isinstance(obj, datetime.datetime):
				return obj.isoformat()
			else:
				return super(DateTimeJSONEncoder, self).default(obj)
				
	yield DateTimeJSONEncoder().encode(response)

class SessionManager(object):
	cookieName = 'session'
	class Session(object):
		__slots__ = ['username','sessionIdentifier','userId']
		
		def __init__(self,username,userId,sessionIdentifier):
			self.userId = userId
			self.username = username
			self.sessionIdentifier = sessionIdentifier
			
		def getCookie(self):
			return ('Set-Cookie','%s=%s; HttpOnly' % (SessionManager.cookieName, str(self.sessionIdentifier), ) )
			
		def getId(self):
			return self.userId
		
		def getUsername(self):
			return self.username
			
	def __init__(self):
		self.logger = logging.getLogger('fairywren.webapi.SessionManager')
		self.sessions = {}
		self.usernameToSessionIdentifier = {}
		
	def authorizeSession(self,sessionIdentifier):
		if sessionIdentifier in self.sessions:
			session = self.sessions[sessionIdentifier]
			self.logger.info('Session authorized for user:%s',session.getUsername())
			return session
		return None
			
	def startSession(self,username,userId):
		#Check to see if the user has a session currently
		if username in self.usernameToSessionIdentifier:
			#Remove the existing session from both dictionaries
			oldIdentifier = self.usernameToSessionIdentifier[username]
			self.usernameToSessionIdentifier.pop(username)
			self.sessions.pop(oldIdentifier)
		
		#Create a new session identifier
		newIdentifier = str(uuid.uuid4())
		
		#Populate both dictionaries
		#The session dictionary maps the identifier to a session object
		self.sessions[newIdentifier] = self.Session(username,userId,newIdentifier)
		#The second dictionary maps the username to the identifier
		self.usernameToSessionIdentifier[username] = newIdentifier
		
		self.logger.info('New session started for user:%s',username)
		
		#Return the session object
		return self.sessions[newIdentifier]
		
	def getSession(self,env):
		#Check to see if the CGI Environmental variables
		#even contain a cookie
		if 'HTTP_COOKIE' not in env:
			return None

		#Convert the environment variable into a 
		#cookie object
		cookie = Cookie.SimpleCookie()
		cookie.load(env['HTTP_COOKIE'])
		
		#Check to see if the session cookie is in the cookies
		if SessionManager.cookieName not in cookie:
			return None
		
		#Check to see if the identifier of the session cookie is in the
		#sessions dictionary	
		if cookie[SessionManager.cookieName].value not in self.sessions:
			return None
		
		#Return the session object
		return self.sessions[cookie[SessionManager.cookieName].value]
		
class Webapi(object):
	NOT_AUTHENTICATED = {'error':'not authenticated'}
	def login(self,env,start_response):
		
		cl = vanilla.getContentLength(env)
		if cl == None:
			return vanilla.http_error(411,env,start_response,'missing Content-Length header')
		
		query = urlparse.parse_qs(env['wsgi.input'].read(cl))
		
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
		
		userId = self.auth.authenticateUser(username,password)
		if userId == None:
			return sendJsonWsgiResponse(env,start_response,{'error':'bad username or password'})
		
		session = self.sm.startSession(username,userId)
			
		return sendJsonWsgiResponse(env,start_response,{},additionalHeaders=
		[session.getCookie()])
		
	def showSession(self,env,start_response):
		session = self.sm.getSession(env)
		
		if session == None:
			return sendJsonWsgiResponse(env,start_response,Webapi.NOT_AUTHENTICATED)
			
		response = {}
		
		response['announceResource'] = self.torrents.getAnnounceUrlForUser(session.getId())
		
		return sendJsonWsgiResponse(env,start_response,response,additionalHeaders=[session.getCookie()])
	
	def listTorrents(self,env,start_response):
		session = self.sm.getSession(env)
		
		if session == None:
			return sendJsonWsgiResponse(env,start_response,Webapi.NOT_AUTHENTICATED)
		
		if 'QUERY_STRING' not in env:
			query = {}
		else:
			query = urlparse.parse_qs(env['QUERY_STRING'])
		
		resultSize = query.get('resultSize',50)
		
		try:
			resultSize = int(resultSize)
		except ValueError:
			return vanilla.http_error(400,env,start_response,'resultSize must be integer')
			
		subset = query.get('subset',0)
		
		try:
			subset = int(subset)
		except ValueError:
			return vanilla.http_error(400,env,start_response,'subset must be integer')
		

		return sendJsonWsgiResponse(env,start_response,
		{'torrents' : [i for i in self.torrents.getTorrents(resultSize,subset)] } )
		
	
	def createTorrent(self,env,start_response):
		session = self.sm.getSession(env)
		
		if False and session == None:
			return sendJsonWsgiResponse(env,start_response,Webapi.NOT_AUTHENTICATED)
		
		if not 'CONTENT_TYPE' in env:
			return vanilla.http_error(411,env,start_response,'missing Content-Type header')
		
		contentType = env['CONTENT_TYPE']
			
		if 'multipart/form-data' not in contentType:
			return vanilla.http_error(415,env,start_response,'must be form upload')
		
		forms,files = multipart.parse_form_data(env)
		
		response = {}
		
		if 'torrent' not in files or 'title' not in forms:
			return vanilla.http_error(400,env,start_response,'missing torrent or title')
		
		data = files['torrent'].raw
		newTorrent = torrents.Torrent.fromBencodedData(data)
		
		if newTorrent.scrub():
			response['redownload'] = True
			
		url,infoUrl = self.torrents.addTorrent(newTorrent,forms['title'],session.getId())
		response['resource'] = url
		response['infoResource'] = infoUrl
			
		return sendJsonWsgiResponse(env,start_response,response)
		
	def downloadTorrent(self,env,start_response):
		session = self.sm.getSession(env)
		
		if session == None:
			return sendJsonWsgiResponse(env,start_response,Webapi.NOT_AUTHENTICATED)
			
		number = env['fairywren.pathComponents'][-1].split('.')[0]
		
		number = int(number,16)
		
		torrent = self.torrents.getTorrentForDownload(number,session.getId())
		
		if torrent == None:
			return vanilla.http_error(404,env,start_response)
		
		headers = [('Content-Type','application/x-bittorrent')]
		headers.append(('Content-Disposition','attachment; filename="%s.torrent"' % vanilla.sanitizeForContentDispositionHeaderFilename(torrent.getTitle()) ))
		headers.append(('Cache-Control','no-cache'))
	
		start_response('200 OK',headers)
		
		return [torrent.raw()]
		
	def torrentInfo(self,env,start_response):
		return vanilla.http_error(501,env,start_response)
	
	
	
	def __init__(self,auth,torrents,pathDepth):
		
		self.logger = logging.getLogger('fairywren.webapi')
		self.pathDepth = pathDepth
		self.auth = auth
		self.torrents = torrents
		self.sm = SessionManager()
		self.resources = []
		self.resources.append((['session'],'POST',self.login))
		self.resources.append((['session'],'GET',self.showSession))
		self.resources.append((['torrents'],'GET',self.listTorrents))
		self.resources.append((['torrents'],'POST',self.createTorrent))
		self.resources.append((['torrents','*.json'],'GET',self.torrentInfo))
		self.resources.append((['torrents','*.torrent'],'GET',self.downloadTorrent))
		
	def __call__(self,env,start_response):
		
		#Extract and normalize the path
		#Posix path may not be the best approach here but 
		#no alternate has been found
		pathInfo = posixpath.normpath(env['PATH_INFO'])
		
		#Split the path into components. Drop the first
		#since it should always be the empty string
		pathComponents = pathInfo.split('/')[1+self.pathDepth:]
		
		env['fairywren.pathComponents'] = pathComponents
		
		requestMethod = env['REQUEST_METHOD']
		
		#The default is request not found
		errorCode = 404
		
		
		for path,method,function in self.resources:
			#If the requested path and the number of components in the 
			#path don't match, this can't be a match
			if len(path) != len(pathComponents):
				continue
			
			for actual, candidate in itertools.izip(path,pathComponents):
				if not fnmatch.fnmatch(candidate,actual):
					break				
					
				self.logger.debug('%s matches %s', candidate, actual)
			#Loop ran to exhaustion, this is a match
			else:
				#If the method does not agree with the resource, the
				#code is method not supported
				if requestMethod != method:
					errorCode = 405
				else:
					self.logger.info('%s:%s handled by %s',requestMethod,pathInfo,function.__name__)
					return function(env,start_response)
					
		self.logger.info('%s:%s not handled',requestMethod,pathInfo)		
		return vanilla.http_error(errorCode,env,start_response)
		
