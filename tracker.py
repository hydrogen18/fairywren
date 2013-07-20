import vanilla
import urlparse
import fnmatch
import base64
import bencode
import struct
import socket
import peers
import ctypes
import posixpath
from eventlet.green import zmq
import cPickle as pickle
import eventlet.queue
import fairywren
import itertools
import logging

def sendBencodedWsgiResponse(env,start_response,responseDict):
	headers = [('Content-Type','text/plain')]
	headers.append(('Cache-Control','no-cache'))
	
	start_response('200 OK',headers)
	
	yield bencode.bencode(responseDict)

def getClientAddress(environ):
    try:
        return environ['HTTP_X_FORWARDED_FOR'].split(',')[-1].strip()
    except KeyError:
        return environ['REMOTE_ADDR']

class Tracker(object):
	def __init__(self,auth,peers,pathDepth):
		self.auth = auth
		self.peers = peers
		self.pathDepth = pathDepth
		self.statsQueue = eventlet.queue.LightQueue()
		
		self.announceLog = logging.getLogger('fairywren.announce')
		self.trackerLog = logging.getLogger('fairywren.tracker')
		
		self.trackerLog.info('Created')
		
	def getQueue(self):
		"""Return the queue that this object uses to push
		events to other worker threads"""
		return self.statsQueue
		
	def getScrape(self,info_hashes):
		"""Return a dictionary object that contains a tracker scrape. 
		@param info_hashes: list on info_hashes to include in the scrape
		"""
		retval = {}
		retval['files'] = {}
		for info_hash in info_hashes:
			result = {}
			result['downloaded'] = 0
			result['complete'] = self.peers.getNumberOfSeeds(info_hash)
			result['incomplete'] = self.peers.getNumberOfLeeches(info_hash)
			retval['files'][info_hash] = result
			
		return retval
		
	def announce(self,env,start_response):
		#Extract and normalize the path
		#Posix path may not be the best approach here but 
		#no alternate has been found
		pathInfo = posixpath.normpath(env['PATH_INFO'])
		
		#Split the path into components. Drop the first
		#since it should always be the empty string
		pathComponents = pathInfo.split('/')[1+self.pathDepth:]
		
		#A SHA512 encoded in base64 is 88 characters
		#but the last two are always '==' so 
		#86 is used here
		if len(pathComponents) !=2 or len(pathComponents[0]) != 86 or pathComponents[1] != 'announce':
			return vanilla.http_error(404,env,start_response)
					
		#Only GET requests are valid
		if env['REQUEST_METHOD'] != 'GET':
			return vanilla.http_error(405,env,start_response)
		
		#Add the omitted equals signs back in
		secretKey = pathComponents[0] + '=='
		
		#base64 decode the secret key
		try:
			secretKey = base64.urlsafe_b64decode(secretKey)
		except TypeError:
			return vanilla.http_error(404,env,start_response)
		
		#Extract the IP of the peer
		peerIp = getClientAddress(env)
		peerIpAsString = peerIp
		#Chance the peer IP into an integer
		try:
			peerIp = socket.inet_aton(peerIp)
		except socket.error:
			return vanilla.http_error(500,env,start_response)
	
		#Convert from network byte order to integer
		try:
			peerIp, = struct.unpack('!I',peerIp)
		except struct.error:
			return vanilla.http_error(500,env,start_response)
						
		#Parse the query string. Absence indicates error
		if 'QUERY_STRING' not in env:
			return vanilla.http_error(400,env,start_response)
			
		query = urlparse.parse_qs(env['QUERY_STRING'])
		
		#List of tuples. Each tuple is
		#
		#Parameter name
		#default value (if any)
		#type conversion, side-effect free callable
		params = []
		
		def validateInfoHash(info_hash):
			#Info hashes are a SHA1 hash, and are always 20 bytes
			if len(info_hash) != 20:
				raise ValueError("Length " + str(len(info_hash)) + ' not acceptable')
			return info_hash
			
		params.append(('info_hash',None,validateInfoHash))
		
		def validatePeerId(peer_id):
			#Peer IDs are a string chosen by the peer to identify itself
			#and are always 20 bytes
			if len(peer_id) != 20:
				raise ValueError("Improper Length")
			return peer_id
			
		params.append(('peer_id',None,validatePeerId))
		
		def validatePort(port):
			port = int(port)
			#Ipv4 ports should not be higher than this value
			if port > 2 ** 16 - 1 or port <= 0:
				raise ValueError("Port outside of range")
			return port
			
		def validateByteCount(byteCount):
			byteCount = int(byteCount)
				
			if byteCount < 0:
				raise ValueError('byte count cannot be negative')
			return byteCount
			
		params.append(('port',None,validatePort))
		params.append(('uploaded',None,validateByteCount))
		params.append(('downloaded',None,validateByteCount))
		params.append(('left',None,validateByteCount))
		#If the client doesn't specify the compact parameter, it is
		#safe to assume that compact responses are understood. So a
		#default value of 1 is used. Additionally, any non zero
		#value provided assumes the client wants a compact response
		params.append(('compact',1,int))
		
		def validateEvent(event):
			event = event.lower()
			if event not in ['started','stopped','completed']:
				raise ValueError("Unknown event")
			return event
		
		params.append(('event','update',validateEvent))
		
		maxNumWant = 35
		def limitNumWant(numwant):
			numwant = int(numwant)
			
			if numwant < 0:
				raise ValueError('numwant cannot be negative')
			
			numwant = min(numwant,maxNumWant)
			return numwant
			
		params.append(('numwant',maxNumWant,limitNumWant))
		
		#Dictionary holding parameters to query
		p = dict()
		#Use the params to generate the parameters
		for param,defaultValue,typeConversion in params:
			#If the parameter is in the query, extract the first
			#occurence and type convert if requested
			if param in query:
				p[param] = query[param][0]
				
				if typeConversion:
					try:
						p[param] = typeConversion(p[param])
					except ValueError as e:
						return vanilla.http_error(400,env,start_response,msg='bad value for ' + param)

			#If the parameter is not in the query, then 
			#use a default value is present. Otherwise this is an error
			else:
				if defaultValue == None:
					return vanilla.http_error(400,env,start_response,msg='missing ' + param)
				p[param] = defaultValue
				
				
		#Make sure the secret key is valid
		if not self.auth.authenticateSecretKey(secretKey):
			response = {}
			response['failure reason'] = 'failed to authenticate secret key'
			return sendBencodedWsgiResponse(env,start_response,response)
			
			
		#Make sure the info hash is allowed
		if not self.auth.authorizeInfoHash(p['info_hash']):
			response = {}
			response['failure reason'] = 'unauthorized info hash'
			return sendBencodedWsgiResponse(env,start_response,response)
		
		
		#Construct the peers entry
		peer = peers.Peer(peerIp,p['port'],p['left'],p['downloaded'],p['uploaded'],p['peer_id'])
		
		#This is the basic response format
		response = {}
		response['interval'] = 5*60
		response['complete'] = 0
		response['incomplete'] = 0
		response['peers'] = []
		
		#This value is set to True if the number of seeds or leeches
		#changes in the course of processing this result
		change = False
		
		#For all 3 cases here just return peers
		if p['event'] in ['started','completed','update']:
			response['complete'] = self.peers.getNumberOfLeeches(p['info_hash'])
			response['incomplete'] = self.peers.getNumberOfSeeds(p['info_hash'])
			
			change = self.peers.updatePeer(p['info_hash'],peer)
			
			peersForResponse = self.peers.getPeers(p['info_hash'])
			
			
			#Return a compact response or a traditional response
			#based on what is requested
			if p['compact'] != 0:
				peerStruct = struct.Struct('!IH')
				maxSize = p['numwant'] * peerStruct.size
				peersBuffer = ctypes.create_string_buffer(maxSize)
				
				actualSize = 0
				for peer in peersForResponse[:p['numwant']]:
					peerStruct.pack_into(peersBuffer,actualSize,peer.ip,peer.port)
					actualSize += peerStruct.size
					
				response['peers'] = peersBuffer.raw[:actualSize]
			else:
				for peer in peersForResponse[:p['numwant']]:
					response['peers'].append({'peer id':peer.peerId,'ip':socket.inet_ntoa(struct.pack('!I',peer.ip)),'port':peer.port})
		#For stop event, just remove the peer. Don't return anything	
		elif p['event'] == 'stopped':
			self.peers.removePeer(p['info_hash'],peer)
			#Assume that the count of seeders or leechers is always 
			#decreased by one
			change = True
			
		#If the number of seeders or leechers has changed then
		#dispatch an update message
		if change:
			self.trackerLog.debug('Dispatching stats update for: %s',p['info_hash'].encode('hex').upper())
			self.statsQueue.put(p['info_hash'])
			
		#Log the successful announce
		self.announceLog.info('%s:%d %s,%s,%d',peerIpAsString,p['port'],p['info_hash'].encode('hex').upper(),p['event'],p['left'])
			
		return sendBencodedWsgiResponse(env,start_response,response)

		
	def __call__(self,env,start_response):
		return self.announce(env,start_response)
			

			
		
		

