import posixpath
import re
import logging
import vanilla
import itertools
import urlparse
import uuid
import Cookie
import functools
import copy

'''Decorator'''
class resource(object):
	def __init__(self,requireAuth,method,*path):
		self.method = method
		self.path = path
		self.requireAuth = requireAuth
		
	def __call__(self,func):
		return Resource(func,self.requireAuth,self.method,self.path)

class Resource(object):
	def __init__(self,wrap,requireAuthentication,method,path):
		self.instance = None
		self.wrap = wrap
		
		self.method = method
		self.path = [re.compile(i) for i in path]
		
		self.requireAuthentication = requireAuthentication
		
		self.requireAuthorization = False
		self.allowedRoles = []
		self.allowSelf = False
		self.getOwnerId = None
		
		#Populated by parameter decorator
		self.parameters = []
		
	def wants(self,pathComponents):
		if len(pathComponents) != len(self.path):
			return None

		kwargs = {}	
		#Compare each path component individually. If any of them
		#do not match then go to the next immediately.
		for candidate, requested in itertools.izip(self.path,pathComponents):
			matches = candidate.match(requested)
			if matches == None:
				return None				
			kwargs.update(matches.groupdict())
			#self.logger.debug('%s matches %s', candidate, requested)
			
		return kwargs
	
	def __call__(self,env,start_response,*args,**kwargs):
		try:
			kwargs.update(self._extractParams(env))
		except ValueError as e:
			return vanilla.http_error(400,env,start_response,e.message)
		return self.wrap(self.instance,env,start_response,*args,**kwargs)
		
	def __get__(self,instance,clazz):
		c = copy.copy(self)
		c.instance = instance
		return c
		
	def _extractParams(self,env):
		
		#If the function doesn't request parameters,
		#then don't read from env['wsgi.input']. It is possible
		#the function handles what it needs on its own
		if len(self.parameters) == 0:
			return {}
			
		requestMethod = env['REQUEST_METHOD']
		retval = {}
		
		if requestMethod == 'POST':
			cl = vanilla.getContentLength(env)
			if cl == None:
				raise ValueError('Missing content length header')
		
			query = urlparse.parse_qs(env['wsgi.input'].read(cl))
			for parameter,converter in self.parameters:
				if parameter not in query:
					raise ValueError('Missing parameter %s' % parameter)
					
				retval[parameter] = query[parameter][0]
				
				if converter:
					result = converter(retval[parameter])
					if result == None:
						raise ValueError('Bad value "%s" for parameter %s' % (retval[parameter], parameter,))
						
					retval[parameter] = result
					
			return retval
		else:
			raise NotImplementedError("Cannot handle %s requests with parameters" % requestMethod)
		
	def getName(self):
		return self.wrap.__name__

class parameter(object):
	def __init__(self,name,conversionFunc=None):
		self.name = name
		self.conversionFunc = conversionFunc
		
	def __call__(self,obj):			
		obj.parameters.append((self.name,self.conversionFunc))
		return obj

class authorizeSelf(object):
	def __init__(self,getOwnerId):		
		self.getOwnerId = getOwnerId
	
	def __call__(self,func):
		if not func.requireAuthentication:
			raise ValueError( func.getName() + ' is requested to authorize self, but without authentication enforced')
		func.allowSelf = True
		func.getOwnerId = self.getOwnerId
		return func
		
class requireAuthorization(object):
	def __init__(self, *allowedRoles):
		self.allowedRoles = allowedRoles
		
	def __call__(self,func):
		if func.requireAuthentication != True:
			raise ValueError(func.getName() + ' is requested to have authorization enforced, without authentication')
		func.allowedRoles.append(func.getName())
		func.allowedRoles += list(self.allowedRoles)
		self.requireAuthorization = True
		return func

					
class SessionManager(object):
	cookieName = 'session'
	class Session(object):
		__slots__ = ['username','sessionIdentifier','userId','secure']
		
		def __init__(self,username,userId,sessionIdentifier,secure):
			self.userId = userId
			self.username = username
			self.sessionIdentifier = sessionIdentifier
			self.secure = secure
			
		def getCookie(self):
			return ('Set-Cookie','%s=%s; HttpOnly%s' % (SessionManager.cookieName, str(self.sessionIdentifier), '; Secure' if self.secure else '') )
			
		def getId(self):
			return self.userId
		
		def getUsername(self):
			return self.username
			
	def __init__(self,secure):
		self.secure = secure
		self.logger = logging.getLogger('fairywren.restInterface.SessionManager')
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
		self.sessions[newIdentifier] = self.Session(username,userId,newIdentifier,self.secure)
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



		
class restInterface(object):
	NOT_AUTHENTICATED = {'error':'not authenticated', 'authenticated': False,'authorized':False}
	NOT_AUTHORIZED = {'error':'not authorized' , 'authenticated':True, 'authorized':False}
	
	def __init__(self,pathDepth,authenticateUser, authorizeUser,secure):		
		
		#Inspect each member of this object. If it is an instance of
		#resource then add it to the list
		self.resources = []
		for attr in (i for i in dir(self)):
			member = getattr(self,attr)

			if isinstance(member,Resource): 
				self.resources.append(member)

				
		self.logger = logging.getLogger('fairywren.restInterface')
		
		self.pathDepth = pathDepth
		
		self.sm = SessionManager(secure)
		
		self.authenticateUser = authenticateUser
		self.authorizeUser = authorizeUser

	def getResponseForSession(self,session):
		return {}
		
	@resource(True,'GET','session')
	def showSession(self,env,start_response,session):		
		response = self.getResponseForSession(session)
	
		return vanilla.sendJsonWsgiResponse(env,start_response,response,additionalHeaders=[session.getCookie()])	

	@resource(False,'POST','session')
	def login(self,env,start_response):
		
		cl = vanilla.getContentLength(env)
		if cl == None:
			return vanilla.http_error(411,env,start_response,'missing Content-Length header')
		
		content = env['wsgi.input'].read(cl)
		query = urlparse.parse_qs(content)
		
		if 'username' not in query:
			return vanilla.http_error(400,env,start_response,msg='missing username')
		#Use first occurence from query string
		username = query['username'][0]
		
		if 'password' not in query:
			return vanilla.http_error(400,env,start_response,msg='missing password')
		#Use first occurence from query string
		password = query['password'][0]
		
		userId = self.authenticateUser(username,password)
		if userId == None:
			self.logger.info('Failed authorization for user:%s' , username)
			return vanilla.sendJsonWsgiResponse(env,start_response,{'error':'bad username or password'})
		
		session = self.sm.startSession(username,userId)
			
		return vanilla.sendJsonWsgiResponse(env,start_response,self.getResponseForSession(session),additionalHeaders=[session.getCookie()])
		
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
		
		#Find a resource with a patch matching the requested one
		for resource in self.resources:	
			kwargs = resource.wants(pathComponents)

			if kwargs == None:
				continue

			#If the method does not agree with the resource, the
			#code is method not supported
			if requestMethod != resource.method:
				errorCode = 405	
				continue							
			
			self.logger.debug('%s:%s handled by %s',requestMethod,pathInfo,resource.getName())
			if resource.requireAuthentication:
				session = self.sm.getSession(env)

				if session == None:
					return vanilla.sendJsonWsgiResponse(env,start_response,restInterface.NOT_AUTHENTICATED)
					
				#Check to see if the resource requires authorization
				if resource.requireAuthorization:
					authorized = resource.allowSelf and resource.getOwnerId(*pathComponents)==session.getId()
					authorized |= self.authorizeUser(session,resource.allowedRoles)
					if not authorized:
						self.logger.debug('%s:%s not authorized for %s',requestMethod,pathInfo,session.getUsername())
						return vanilla.sendJsonWsgiResponse(env,start_response,restInterface.NOT_AUTHORIZED)

				return resource(env,start_response,session,**kwargs)
			else:
				return resource(env,start_response,**kwargs)
				
		self.logger.info('%s:%s not handled, %d', requestMethod,pathInfo,errorCode)
		return vanilla.http_error(errorCode,env,start_response)
