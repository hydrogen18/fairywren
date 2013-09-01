import vanilla
import base64
import json
import itertools
import datetime
import multipart
import sys
import torrents
import logging
import urlparse
import string
from restInterface import *
import fairywren
import math
import users

def decodePassword(password):
	#Password comes across as 64 bytes of base64 encoded data
	#with trailing ='s lopped off. 
	password += '=='
	
	if len(password) != 88: #64 bytes in base64 is length 88
		return None
	
	try:
		return base64.urlsafe_b64decode(password)
	except TypeError:
		return None

def validateUsername(username):
	allowedChars = string.digits + string.ascii_lowercase
	
	for c in username:
		if c not in allowedChars:
			return None
			
	return username

		
def extractUserId(*pathComponents):
	return int(pathComponents[1],16)

class Webapi(restInterface):
	
	MAX_TORRENTS_PER_RESULT = 50
	def __init__(self,torrentStats,users,authmgr,torrents,httpPathDepth,secure):
		self.torrentStats = torrentStats
		def authenticateUser(username,password):	
			#Password comes across as 64 bytes of base64 encoded data
			#with trailing ='s lopped off. 
			password += '=='
			
			if len(password) != 88: #64 bytes in base64 is length 88
				return None
				return vanilla.http_error(400,env,start_response,msg='password too short')
			
			try:
				password = base64.urlsafe_b64decode(password)
			except TypeError:
				return None
				return vanilla.http_error(400,env,start_response,msg='password poorly formed')
			
			return authmgr.authenticateUser(username,password)

		def authorizeUser(session,roles):
			return authmgr.isUserMemberOfRole(session.getId(),roles)
			

		super(Webapi,self).__init__(httpPathDepth,authenticateUser,authorizeUser,secure)
		self.authmgr = authmgr
		self.torrents = torrents
		self.users = users
		
		self.log = logging.getLogger('fairywren.webapi')
		self.log.info('Created')

	def getResponseForSession(self,session):
		return {'my' : {'href':fairywren.USER_FMT % session.getId()} }

	def getRoles(self):
		return [ res.getName() for res in self.getResources() if res.requiresAuthorization()]
		

	@resource(True,'GET','roles')
	def listRoles(self,env,start_response,session):
		return vanilla.sendJsonWsgiResponse(env,start_response,{'roles':self.getRoles()})
	
	@requireAuthorization()
	@parameter('roles',array=True)
	@resource(True,'POST','users',fairywren.UID_RE,'roles')
	def changeRolesOfUser(self,env,start_response,session,uid,roles):
		uid = int(uid,16)
		try:
			self.users.setUserRoles(roles,uid)
		except ValueError as e:
			return vanilla.http_error(400,env,start_response,msg=e.message)
		return vanilla.sendJsonWsgiResponse(env,start_response,{'roles':self.users.getUserRoles(uid)})
	
	@resource(True,'GET','users',fairywren.UID_RE,'roles')
	def listRolesOfUser(self,env,start_response,session,uid):
		uid = int(uid,16)
		#Potential pitfall in this implementation:
		#If the user for the uid does not exist, this stil returns an empty list
		return vanilla.sendJsonWsgiResponse(env,start_response,{'roles':self.users.getUserRoles(uid)})
		
	@authorizeSelf(extractUserId)
	@requireAuthorization()
	@resource(True,'GET','users',fairywren.UID_RE,'invites')
	def listInvites(self,env,start_response,session,uid):
		uid = int(uid,16)
		#Potential pitfall in this implementation:
		#If a user is authorized to perform a GET on this resource but
		#user for the uid does not exist, this stil returns an empty list
		response = { 'invites' : list(self.users.listInvitesByUser(uid)) }
		return vanilla.sendJsonWsgiResponse(env,start_response,response)

	@resource(False,'GET','invites',fairywren.SECRET_RE)
	def inviteStatus(self,env,start_response,secret):
		secret = base64.urlsafe_b64decode(secret + '=')
		try:
			claimed =self.users.getInviteState(secret)
		except ValueError as e:
			return vanilla.http_error(404,env,start_response,msg=e.message)
		
		return vanilla.sendJsonWsgiResponse(env,start_response,{'claimed':claimed})

	@parameter('password',decodePassword)
	@parameter('username')
	@resource(False,'POST','invites',fairywren.SECRET_RE)
	def claimInvite(self,env,start_response,secret,username,password):
		secret = base64.urlsafe_b64decode(secret + '=')
		
		try:
			newuser = self.users.claimInvite(secret,username,password)
		except users.UserAlreadyExists:
			return vanilla.http_error(409,env,start_response,msg='User with that name already exists')
		except ValueError as e:
			return vanilla.http_error(404,env,start_response,msg=e.message)
		
		return vanilla.sendJsonWsgiResponse(env,start_response,{'href' : newuser})
		
	@requireAuthorization()
	@resource(True,'POST','invites')
	def createInvite(self,env,start_response,session):
		pathOfNewInvite = self.users.createInvite(session.getId())
		return vanilla.sendJsonWsgiResponse(env,start_response,{'href':pathOfNewInvite})

	@authorizeSelf(extractUserId)
	@requireAuthorization('Administrator')
	@parameter('password',decodePassword)
	@resource(True,'POST','users',fairywren.UID_RE,'password')
	def changePassword(self,env,start_response,session,uid,password):
		uid = int(uid,16)
		
		if None == self.authmgr.changePassword(uid,password):
			return vanilla.http_error(400,env,start_response)
		
		return vanilla.sendJsonWsgiResponse(env,start_response,{})
		
		
	@resource(True,'GET','users',fairywren.UID_RE )
	def userInfo(self,env,start_response,session,uid):
		uid = int(uid,16)
		
		response = self.users.getInfo(uid)
		
		if response == None:
			return vanilla.http_error(404,env,start_response)
			
		if session.getId() == uid:
			response['announce'] = { 'href': self.torrents.getAnnounceUrlForUser(uid) }
				
		return vanilla.sendJsonWsgiResponse(env,start_response,response)
		
	@requireAuthorization()
	@parameter('password',decodePassword)
	@parameter('username',validateUsername)
	@resource(True,'POST','users')
	def addUser(self,env,start_response,session,password,username):
		
		try:
			resourceForNewUser,_ = self.users.addUser(username,password)
		except users.UserAlreadyExists:		
			return vanilla.http_error(409,env,start_response,'user already exists')
		
		response = { 'href' : resourceForNewUser } 
		return vanilla.sendJsonWsgiResponse(env,start_response,response)
		
	def searchTorrents(self,env,start_response,session,query):
		tokens = query.get('token')
		if tokens == None:
			return vanilla.http_error(400,env,start_response,'search must have at least one instance of token parameter')
			
		if len(tokens) > 5:
			return vanilla.http_error(400,env,start_response,'search may not have more than 5 tokens')
			
		listOfTorrents = []
		for torrent in self.torrents.searchTorrents(tokens):
			torrentId = torrent.pop('id')
			seeds, leeches = self.torrentStats.getCount(torrentId)
			torrent['seeds'] = seeds
			torrent['leeches'] = leeches
			listOfTorrents.append(torrent)
			
		return vanilla.sendJsonWsgiResponse(env,start_response,
		{'torrents': listOfTorrents})
		
	@resource(True,'GET','torrents')
	def listTorrents(self,env,start_response,session):
		
		if 'QUERY_STRING' not in env:
			query = {}
		else:
			query = urlparse.parse_qs(env['QUERY_STRING'])
			
		if 'search' in query:
			return self.searchTorrents(env,start_response,session,query)
		
		#Use the first occurence of the supplied parameter
		#With a default 
		resultSize = query.get('resultSize',[self.MAX_TORRENTS_PER_RESULT])[0]
		
		try:
			resultSize = int(resultSize)
		except ValueError:
			return vanilla.http_error(400,env,start_response,'resultSize must be integer')
		
		#Use the first occurence of the supplied parameter
		#With a default of zero	
		subset = query.get('subset',[0])[0]
		
		try:
			subset = int(subset)
		except ValueError:
			return vanilla.http_error(400,env,start_response,'subset must be integer')

		listOfTorrents = []
		
		for torrent in self.torrents.getTorrents(resultSize,subset):
			torrentId = torrent.pop('id')
			seeds, leeches = self.torrentStats.getCount(torrentId)
			torrent['seeds'] = seeds
			torrent['leeches'] = leeches
			listOfTorrents.append(torrent)

		return vanilla.sendJsonWsgiResponse(env,start_response,
		{'torrents' : listOfTorrents ,'numSubsets' : int(math.ceil(self.torrents.getNumTorrents() / float(resultSize)))} )
		
	@resource(True,'POST','torrents')
	def createTorrent(self,env,start_response,session):
		
		if not 'CONTENT_TYPE' in env:
			return vanilla.http_error(411,env,start_response,'missing Content-Type header')
		
		contentType = env['CONTENT_TYPE']
			
		if 'multipart/form-data' not in contentType:
			return vanilla.http_error(415,env,start_response,'must be form upload')
		
		forms,files = multipart.parse_form_data(env)
		
		if 'torrent' not in files or 'title' not in forms:
			return vanilla.http_error(400,env,start_response,'missing torrent or title')
		
		try:
			extended = json.loads(forms.get('extended','{}'))
		except ValueError:
			return vanilla.http_error(400,env,start_response,'bad extended info')
			
		if not isinstance(extended,dict):
			return vanilla.http_error(400,env,start_response,'extended info must be dict')
		
		data = files['torrent'].raw
		try:
			newTorrent = torrents.Torrent.fromBencodedData(data)
		except ValueError as e:
			return vanilla.http_error(400,env,start_response,str(e))
		
		response = {}
		response['redownload'] = newTorrent.scrub()
		response['redownload'] |= self.torrents.getAnnounceUrlForUser(session.getId())!=newTorrent.getAnnounceUrl()
		
		try:	
			url,infoUrl = self.torrents.addTorrent(newTorrent,forms['title'],session.getId(),extended)
		except ValueError as e: #Thrown when a torrent already exists with this info hash
			return vanilla.http_error(400,env,start_response,e.message)
			
		response['metainfo'] = { 'href' : url }
		response['info'] = { 'href' : infoUrl }
			
		return vanilla.sendJsonWsgiResponse(env,start_response,response)

	
	@resource(True,'GET','torrents',fairywren.UID_RE + '.torrent')
	def downloadTorrent(self,env,start_response,session,uid):
		uid = int(uid,16)
		
		try:
			torrent = self.torrents.getTorrentForDownload(uid,session.getId())
		except ValueError as e:
			return vanilla.http_error(404,env,start_response,msg=e.message)
		
		headers = [('Content-Type','application/x-bittorrent')]
		headers.append(('Content-Disposition','attachment; filename="%s.torrent"' % vanilla.sanitizeForContentDispositionHeaderFilename(torrent.getTitle()) ))
		headers.append(('Cache-Control','no-cache'))

		start_response('200 OK',headers)
		
		return [torrent.raw()]

	@resource(True,'GET','torrents',fairywren.UID_RE + '.json')
	def torrentInfo(self,env,start_response,session,uid):
		uid = int(uid,16)
		response = self.torrents.getInfo(uid)
		
		if response == None:
			return vanilla.http_error(404,env,start_response,msg='no such torrent')
		
		response['extended'] = self.torrents.getExtendedInfo(uid)
		return vanilla.sendJsonWsgiResponse(env,start_response,response)
		


	
		
