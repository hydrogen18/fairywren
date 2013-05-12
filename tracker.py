import vanilla
import urlparse
import fnmatch
import base64
import bencode
import struct
import socket
import peers
import ctypes

def sendBencodedWsgiResponse(env,start_response,responseDict):
	headers = [('Content-Type','text/plain')]
	headers.append(('Cache-Control','no-cache'))
	
	start_response('200 OK',headers)
	
	return bencode.bencode(responseDict)

def getClientAddress(environ):
    try:
        return environ['HTTP_X_FORWARDED_FOR'].split(',')[-1].strip()
    except KeyError:
        return environ['REMOTE_ADDR']

class Tracker(object):
	def __init__(self,auth,peers):
		self.auth = auth
		self.peers = peers
		#A SHA512 encoded in base64 is 88 characters
		#but the last two are always '==' so 
		#86 is used here
		self.announcePathFmt = '/' + '?' * 86 + '/announce' 
		
	
	def announce(self,env,start_response):
		if env['REQUEST_METHOD'] != 'GET':
			return vanilla.http_error(405,env,start_response)
			
		path = env['PATH_INFO'].split('/')
		#Add the omitted equals signs back in
		secretKey = path[0] + '=='
		
		try:
			secretKey = base64.urlsafe_b64decode(secretKey)
		except TyperError:
			return vanilla.http_error(404,env,start_response)
			
		if 'QUERY_STRING' not in env:
			return vanilla.http_error(400,env,start_response)
			
		query = urlparse.parse_qs(env['QUERY_STRING'])
		
		params = []
		#Parameter name, default value(if any), type conversion function
		
		def validateInfoHash(info_hash):
			if len(info_hash) != 20:
				raise ValueError("Length " + str(len(info_hash)) + ' not acceptable')
			return info_hash
			
		params.append(('info_hash',None,validateInfoHash))
		
		def validatePeerId(peer_id):
			if len(peer_id) != 20:
				raise ValueError("Improper Length")
			return peer_id
			
		params.append(('peer_id',None,validatePeerId))
		
		def validatePort(port):
			port = int(port)
			
			if port > 2 ** 16 - 1:
				raise ValueError("Port too high")
			return port
			
		params.append(('port',None,validatePort))
		params.append(('uploaded',None,int))
		params.append(('downloaded',None,int))
		params.append(('left',None,int))
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
			numwant = min(numwant,maxNumWant)
			return numwant
			
		params.append(('numwant',maxNumWant,limitNumWant))
		
		peerIp = getClientAddress(env)
		
		try:
			peerIp = socket.inet_aton(peerIp)
		except socket.error:
			return vanilla.http_error(500,env,start_response)
	
		try:
			peerIp, = struct.unpack('!I',peerIp)
		except struct.error:
			return vanilla.http_error(500,env,start_response)
		
		p = dict()
		for param,defaultValue,typeConversion in params:
			if param in query:
				p[param] = query[param][0]
				
				if typeConversion:
					try:
						p[param] = typeConversion(p[param])
					except ValueError as e:
						return vanilla.http_error(400,env,start_response,msg='bad value for ' + param)
						
			else:
				if defaultValue == None:
					return vanilla.http_error(400,env,start_response,msg='missing ' + param)
				p[param] = defaultValue
				
				
		#Make sure the secret key is valid
		if not self.auth.authenticateSecretKey(secretKey):
			response = {}
			response['failure reason'] = 'failed to authenticated secret key'
			return sendBencodedWsgiResponse(env,start_response,response)
			
			
		#Make sure the info hash is allowed
		if not self.auth.authorizeInfoHash(p['info_hash']):
			response = {}
			response['failure reason'] = 'unauthorized info hash'
			return sendBencodedWsgiResponse(env,start_response,response)
		
		
		peer = peers.Peer(peerIp,p['port'],p['left'],p['downloaded'],p['uploaded'],p['peer_id'])
		
		response = {}
		response['interval'] = 120
		response['complete'] = 0
		response['incomplete'] = 0
		response['peers'] = []
		
		if p['event'] in ['started','stopped','update']:
			response['complete'] = self.peers.getNumberOfLeeches(p['info_hash'])
			response['incomplete'] = self.peers.getNumberOfSeeds(p['info_hash'])
			
			peersForResponse = self.peers.getPeers(p['info_hash'])
			
			if p['compact'] > 0:
				peerStruct = struct.Struct('!IH')
				maxSize = p['numwant'] * peerStruct.size
				peersBuffer = ctypes.create_string_buffer(maxSize)
				
				actualSize = 0
				for peer in peersForResponse:
					peerStruct.pack_into(peersBuffer,actualSize,peer.ip,peer.port)
					actualSize += peerStruct.size
					
				response['peers'] = peersBuffer.raw[:actualSize]
			else:
				for peer in peerForResponse:
					response['peers'].append({'peer id':peer.peerId,'ip':socket.inet_ntoa(struct.pack('!I',peer.ip)),port:peer.port})
			
			self.peers.updatePeer(p['info_hash'],peer)
			
		elif p['event'] == ['stopped']:
			self.peers.removePeer(p['info_hash'],peer)
			
		return sendBencodedWsgiResponse(env,start_response,response)

		
	def __call__(self,env,start_response):
		
		if fnmatch.fnmatch(env['PATH_INFO'],self.announcePathFmt):
			return self.announce(env,start_response)
			
		return vanilla.http_error(404,env,start_response)
			
		
		

