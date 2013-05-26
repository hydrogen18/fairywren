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
			return ('Set-Cookie','%s=%s; HttpOnly; Secure' % (SessionManager.cookieName, str(self.sessionIdentifier), ) )
			
		def getId(self):
			return self.userId
		
		def getUsername(self):
			return self.username
			
	def __init__(self):
		self.logger = logging.getLogger('fairywren.webapi.SessionManager')
		self.sessions = {}
		
	def authorizeSession(self,sessionIdentifier):
		if sessionIdentifier in self.sessions:
			session = self.sessions[sessionIdentifier]
			self.logger.info('Session authorized for user:%s',session.getUsername())
			return session
		return None
			
	def startSession(self,username,userId):
		for i, j in enumerate(self.sessions.iteritems()):
			sessionIdentifier,session = j
			if session.username == username:
				self.sessions.pop(sessionIdentifier)
				break
		
		newIdentifier = str(uuid.uuid4())
		
		self.sessions[newIdentifier] = self.Session(username,userId,newIdentifier)
		
		self.logger.info('New session started for user:%s',username)
		
		return self.sessions[newIdentifier]
		
	def getSession(self,env):
		if 'HTTP_COOKIE' not in env:
			return None

		cookie = Cookie.SimpleCookie()
		cookie.load(env['HTTP_COOKIE'])
		
		if SessionManager.cookieName not in cookie:
			return None
			
		if cookie[SessionManager.cookieName].value not in self.sessions:
			return None
		
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
		
		magic = 'boundary='
		
		try:
			offset = contentType.index(magic)
		except ValueError:
			return vanilla.http_error(400,env,start_response,'cant find boundary in Content-Type header')
			
		offset+=len(magic)
		
		boundary = '--' + contentType[offset:]
		
		upload = {}
		
		for headers, data in multipart.Parser(boundary,env['wsgi.input']):
			details = {}
			for header in headers:
				field, value = header
				
				if 'Content-Disposition' != field:
					continue
				pairs = value.split(';')	
				
				for s in pairs:
					if '=' not in s:
						continue
					key,value = s.split('=')
					value = value.replace('"','').strip()
					key = key.strip()
					details[key] = value
				break	
			else:
				#If the content disposition header is not present
				#ignore it
				continue
			
			if 'name' not in details:
				continue
			
			upload[details['name']] = data
			
		response = {}
		
		if 'torrent' and 'title' not in upload:
			return vanilla.http_error(400,env,start_response,'missing torrent or title')
		
		
		data = upload['torrent']
		newTorrent = torrents.Torrent.fromBencodedDataStream(data)
		
		if newTorrent.scrub():
			response['redownload'] = True
			
		url,infoUrl = self.torrents.addTorrent(newTorrent,''.join(upload['title']),session.getId()	)
		response['resource'] = url
		response['infoResource'] = infoUrl
			
		return sendJsonWsgiResponse(env,start_response,response)
		
	def downloadTorrent(self,env,start_response):
		session = self.sm.getSession(env)
		
		if session == None:
			return sendJsonWsgiResponse(env,start_response,Webapi.NOT_AUTHENTICATED)
			
		number = env['fairywren.pathComponents'][-1].split('.')[0]
		
		number = int(number,16)
		
		rawTorrent = self.torrents.getTorrentForDownload(number,session.getId())
		
		if rawTorrent == None:
			return vanilla.http_error(400,env,start_response)
		
		headers = [('Content-Type','text/plain')]
		headers.append(('Cache-Control','no-cache'))
	
		start_response('200 OK',headers)
		
		return [rawTorrent]
		
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
		
