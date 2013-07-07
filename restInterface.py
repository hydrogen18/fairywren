import posixpath
import fnmatch
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


class Authorization(object):
	SELF = 1 
	
		
class requireAuthorization(object):
	def __init__(self, *allowed):
		self.allowed = allowed
		
	def __call__(self,func):
		if not hasattr(func, 'requireAuthentication') or func.requireAuthentication != True:
			raise ValueError(func.__name__ + ' is requested to have authorization enforced, without authorization')
		func.allowed = self.allowed
		return func

					
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


		
class restInterface(object):
	NOT_AUTHENTICATED = {'error':'not authenticated'}
	
	def __init__(self,pathDepth,authenticateUser):		
		
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
		
		self.sm = SessionManager()
		
		self.authenticateUser = authenticateUser

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
			return vanilla.sendJsonWsgiResponse(env,start_response,{'error':'bad username or password'})
		
		session = self.sm.startSession(username,userId)
			
		return vanilla.sendJsonWsgiResponse(env,start_response,{},additionalHeaders=[session.getCookie()])
		

	@resource(True,'GET','session')
	def showSession(self,env,start_response,session):		
		response = {}
	
		return vanilla.sendJsonWsgiResponse(env,start_response,response,additionalHeaders=[session.getCookie()])		
		
		
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
			#If the requested path and the number of components in the 
			#path don't match, this can't be a match
			if len(resource.path) != len(pathComponents):
				continue
			
			#Compare each path component individually. If any of them
			#do not match then go to the next immediately.
			for candidate, requested in itertools.izip(resource.path,pathComponents):
				if not fnmatch.fnmatch(requested,candidate):
					break				
					
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
					if hasattr(resource,'allowed'):
						pass
						
					return resource(env,start_response,session)
				else:
					self.logger.info('%s:%s handled by %s',requestMethod,pathInfo,resource)
					return resource(env,start_response)
					
		return vanilla.http_error(errorCode,env,start_response)
