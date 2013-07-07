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

from restInterface import *

class Webapi(restInterface):
	def __init__(self,users,authmgr,torrents,httpPathDepth):
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

		super(Webapi,self).__init__(httpPathDepth,authenticateUser)
		self.authmgr = authmgr
		self.torrents = torrents
		self.users = users

	@resource(True,'GET','users','*')
	def userInfo(self,env,start_response,session):
		number = env['fairywren.pathComponents'][-1]
		number = int(number,16)
		
		response = self.users.getInfo(number)
		
		if response == None:
			return vanilla.http_error(404,env,start_response)
				
		return vanilla.sendJsonWsgiResponse(env,start_response,response)
		
	@resource(True,'POST','users')
	def addUser(self,env,start_response,session):
		
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
			return None
			return vanilla.http_error(400,env,start_response,msg='password too short')
		
		try:
			password = base64.urlsafe_b64decode(password)
		except TypeError:
			return None
			return vanilla.http_error(400,env,start_response,msg='password poorly formed')		
		
		resourceForNewUser = self.authmgr.addUser(username,password)
		
		response = { 'resource' : resourceForNewUser } 
		return vanilla.sendJsonWsgiResponse(env,start_response,response)
		
	@resource(True,'GET','torrents')
	def listTorrents(self,env,start_response,session):
		
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
		

		return vanilla.sendJsonWsgiResponse(env,start_response,
		{'torrents' : [i for i in self.torrents.getTorrents(resultSize,subset)] } )
		
	@resource(True,'POST','torrents')
	def createTorrent(self,env,start_response,session):
		
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
			
		return vanilla.sendJsonWsgiResponse(env,start_response,response)

	@resource(True,'GET','torrents','*.torrent')
	def downloadTorrent(self,env,start_response,session):
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

	@resource(True,'GET','torrents','*.json')
	def torrentInfo(self,env,start_response):
		return vanilla.http_error(501,env,start_response)
		


	
		
