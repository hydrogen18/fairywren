import hashlib
import bencode
import base64
import cPickle as pickle
import psycopg2
import os
import os.path


def computeInfoHash(rawBencodedData):
	
	torrent = bencode.bdecode(rawBencodedData)
	info_hash = hashlib.sha1()
	info_hash.update(bencode.bencode(torrent['info']))

	print info_hash.hexdigest()
	
class Torrent(object):
	def __init__(self):
		self.infoHash = None
		self.dict = None
	
	@staticmethod	
	def fromBencodedDataStream(dataStream):
		
		b = ''
		for chunk in dataStream:
			b += chunk
			
		return Torrent.fromDict(bencode.bdecode(b))
		
	@staticmethod 
	def fromDict(torrentDict):
		result = Torrent()
		
		result.dict = torrentDict
		#TODO sanity check for required fields in bit torrent
		#file
		
		return result
		
	def raw(self):
		return bencode.bencode(self.dict)
	
	def _computeInfoHash(self):
		self.infoHash = hashlib.sha1()
		self.infoHash.update(bencode.bencode(self.dict['info']))
		
	def getInfoHash(self):
		if self.infoHash == None:
			self._computeInfoHash()
			
		return self.infoHash
	
	def scrub(self):
		touched = False
		def removeIfPresent(d,k):
			if k in d:
				d.pop(k)
				return True
				
			return False
		
		touched |= removeIfPresent(self.dict,'announce-list')
		removeIfPresent(self.dict,'creation date')
		removeIfPresent(self.dict,'comment')
		removeIfPresent(self.dict,'created by')
		
		if 'private' not in self.dict['info'] or self.dict['info']['private'] != 1:
			self.dict['info']['private'] = 1
			self.infoHash == None
			touched = True
			
		return touched
		
	def getAnnounceUrl(self):
		return self.dict['announce']
		
	def setAnnounce(self,url):
		self.dict['announce'] = url

class TorrentStore(object):
	
	def __init__(self,torrentPath,trackerUrl,apiUrl):
		self.torrentPath = torrentPath
		self.trackerUrl = trackerUrl
		self.apiUrl = apiUrl
		

	def setConnectionPool(self,pool):
		self.connPool = pool
		
	def addTorrent(self,torrent,title,creator):
		
		with self.connPool.item() as conn:
			cur = conn.cursor()
			try:
				cur.execute(
				"Insert into torrents (title,creationdate, \
				creator, infohash) VALUES \
				(%s,NOW(),%s,%s) \
				returning torrents.id;",
				(title,creator,
				base64.urlsafe_b64encode(torrent.getInfoHash().digest()).replace('=',''),)
				)
				
				result = cur.fetchone();
				result, = result
				conn.commit();
			except psycopg2.DatabaseError:
				return None
			finally:
				cur.close()
			
		self._storeTorrent(torrent,result)
		return self.getResourceForTorrent(result),self.getInfoResourceForTorrent(result)
		
	
	def _buildPathFromId(self,torrentId):
		if torrentId < 0 or torrentId > (2**32 -1):
			return ValueError("torrentId out of range")
			
		subpath = '%.8x' % torrentId
		subpath =  [subpath[i:i+2] for i in xrange(0,8,2)]
		path = os.path.join(self.torrentPath,*subpath)
		
		containingFolder = os.path.join(self.torrentPath,*subpath[:3])
		
		return containingFolder, path
	
	def _storeTorrent(self,torrent,torrentId):
		containingFolder, path = self._buildPathFromId(torrentId)
		
		if not os.path.exists(containingFolder):
			os.makedirs(containingFolder)
			
		with open(path,'w') as fout:
			pickle.dump(torrent.dict,fout)
		
	def _retrieveTorrent(self,torrentId):		
		_, path = self._buildPathFromId(torrentId)
		
		if not os.path.exists(path):
			return None
			
		with open(path,'r') as fin:
			torrentDict = pickle.load(fin)
			
		return Torrent.fromDict(torrentDict)
	
	def getAnnounceUrlForUser(self,user):
		with self.connPool.item() as conn:
			cur = conn.cursor()
			cur.execute(
			"Select secretkey from users where id=%s;",
			(user,))
			
			result = cur.fetchone()
			
			cur.close()
			
		if None == result:
			return None
		result, = result
		return '%s/%s/announce' % (self.trackerUrl,result,)
			
	
	def getTorrentForDownload(self,torrentId,forUser):
		torrent = self._retrieveTorrent(torrentId)
		
		if torrent == None:
			return None
		
		announceUrl = self.getAnnounceUrlForUser(forUser)
		
		if None == announceUrl:
			return None
		
		torrent.setAnnounce(announceUrl)
		
		return torrent.raw()
	
	def getResourceForTorrent(self,torrentId):
		return '%s/torrents/%.8x.torrent' % (self.apiUrl, torrentId,)
		
	def getInfoResourceForTorrent(self,torrentId):
		return '%s/torrents/%.8x.json'  % (self.apiUrl,torrentId,)
	
	def getTorrents(self,limit,subset):
		with self.connPool.item() as conn:
			cur = conn.cursor()
			cur.execute(
			"Select torrents.id,torrents.title,torrents.creationdate, \
			users.id,users.name \
			from torrents \
			left join users on torrents.creator = users.id \
			order by creationdate desc limit %s offset %s;",
			(limit,subset*limit, ))
			
			while True:
				r = cur.fetchone()
				if r!=None:
					torrentId,torrentTitle,torrentsCreationDate,userId,userName =r
					
					yield {
					'resource' : self.getResourceForTorrent(torrentId),
					'infoResource' : self.getInfoResourceForTorrent(torrentId),
					'title' : torrentTitle,
					'creationDate' : torrentsCreationDate,
					'creator': {
						'resource' : '%x.json' % userId,
						'name' : userName
						}
					}
				else:
					cur.close()
					break
			
			
				
