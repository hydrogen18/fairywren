import posixpath
import re
import logging
import vanilla
import itertools
import urlparse
import uuid
import Cookie

class resource(object):
	def __init__(self,requireAuth,method,*path):
		self.method = method
		self.path = path
		self.requireAuth = requireAuth
		
	def __call__(self,func):
		func.method = self.method
		func.path = self.path
		func.requireAuthentication = self.requireAuth
		return func

class parameter(object):
	def __init__(self,name,conversionFunc=None):
		self.name = name
		self.conversionFunc = conversionFunc
		
	def __call__(self,func):
		if not hasattr(func,'parameters'):
			func.parameters = []
			
		func.parameters.append((self.name,self.conversionFunc))
		return func

class authorizeSelf(object):
	def __init__(self,getOwnerId):		
		self.getOwnerId = getOwnerId
	
	def __call__(self,func):
		if not hasattr(func,'allowedRoles'):
			raise ValueError( func.__name__ + ' is requested to authorize self, but without authentication enforced')
		func.allowSelf = True
		func.getOwnerId = self.getOwnerId
		return func
		
class requireAuthorization(object):
	def __init__(self, *allowedRoles):
		self.allowedRoles = allowedRoles
		
	def __call__(self,func):
		if not hasattr(func, 'requireAuthentication') or func.requireAuthentication != True:
			raise ValueError(func.__name__ + ' is requested to have authorization enforced, without authentication')
		func.allowedRoles = [func.__name__]
		func.allowedRoles += list(self.allowedRoles)
		func.allowSelf = False
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


def extractParams(func,env):
	if not hasattr(func,'parameters'):
		return {}
		
	requestMethod = env['REQUEST_METHOD']
	
	retval = {}
	
	if requestMethod == 'POST':
		cl = vanilla.getContentLength(env)
		if cl == None:
			return None
			return vanilla.http_error(411,env,start_response,'missing Content-Length header')
	
		query = urlparse.parse_qs(env['wsgi.input'].read(cl))
		for parameter,converter in func.parameters:
			if parameter not in query:
				return None
				
			retval[parameter] = query[parameter][0]
			if converter:
				retval[parameter] = converter(retval[parameter])
				if retval[parameter] == None:
					return None
				
		return retval
	elif requestMethod == 'GET':
		raise NotImplementedError
	else:
		return None

		
class restInterface(object):
	NOT_AUTHENTICATED = {'error':'not authenticated', 'authenticated': False,'authorized':False}
	NOT_AUTHORIZED = {'error':'not authorized' , 'authenticated':True, 'authorized':False}
	
	def __init__(self,pathDepth,authenticateUser, authorizeUser,secure):		
		
		#Inspect each member of this object. If it has a member 
		#and path it has been decorated by the resource decorator
		#and should be added to the list of resources
		self.resources = []
		for attr in (i for i in dir(self) if not i.startswith('__')):
			member = getattr(self,attr)
			
			if hasattr(member,'path') and hasattr(member,'method'):
				self.resources.append(member)

				
		self.logger = logging.getLogger('fairywren.restInterface')
		
		self.pathDepth = pathDepth
		
		self.sm = SessionManager(secure)
		
		self.authenticateUser = authenticateUser
		self.authorizeUser = authorizeUser

	@resource(False,'POST','session')
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
		
		userId = self.authenticateUser(username,password)
		if userId == None:
			self.logger.info('Failed authorization for user:%s' , username)
			return vanilla.sendJsonWsgiResponse(env,start_response,{'error':'bad username or password'})
		
		session = self.sm.startSession(username,userId)
			
		return vanilla.sendJsonWsgiResponse(env,start_response,{},additionalHeaders=[session.getCookie()])
		
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
		
		kwargs = {}
		
		#Find a resource with a patch matching the requested one
		for resource in self.resources:
			#If the requested path and the number of components in the 
			#path don't match, this can't be a match
			if len(resource.path) != len(pathComponents):
				continue
			
			#Compare each path component individually. If any of them
			#do not match then go to the next immediately.
			for candidate, requested in itertools.izip(resource.path,pathComponents):
				matches = re.compile(candidate).match(requested)
				if matches == None:
					break				
				kwargs.update(matches.groupdict())
				self.logger.debug('%s matches %s', candidate, requested)
			#Loop ran to exhaustion, this is a match
			else:
				#If the method does not agree with the resource, the
				#code is method not supported
				if requestMethod != resource.method:
					errorCode = 405					
				elif resource.requireAuthentication:
					session = self.sm.getSession(env)

					if session == None:
						return vanilla.sendJsonWsgiResponse(env,start_response,restInterface.NOT_AUTHENTICATED)
						
					#Check to see if the resource requires authorization
					if hasattr(resource,'allowedRoles'):	
						authorized = resource.allowSelf and resource.getOwnerId(*pathComponents)==session.getId()
						authorized |= self.authorizeUser(session,resource.allowedRoles)
						if not authorized:
							return vanilla.sendJsonWsgiResponse(env,start_response,restInterface.NOT_AUTHORIZED)
						
					extractedParams = extractParams(resource,env)
					
					if extractedParams == None:
						return vanilla.http_error(400,env,start_response,'missing one or more parameters')
					
					kwargs.update(extractedParams)
					
					self.logger.debug('%s:%s handled by %s',requestMethod,pathInfo,resource)
					
					return resource(env,start_response,session,**kwargs)
				else:
					self.logger.debug('%s:%s handled by %s',requestMethod,pathInfo,resource)
					kwargs = extractParams(resource,env)

					if kwargs == None:
						return vanilla.http_error(400,env,start_response,'missing one or more parameters')

					return resource(env,start_response,**kwargs)
		self.logger.info('%s:%s not handled, %d', requestMethod,pathInfo,errorCode)
		return vanilla.http_error(errorCode,env,start_response)
