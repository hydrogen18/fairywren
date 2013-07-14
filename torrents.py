import hashlib
import bencode
import base64
import cPickle as pickle
import psycopg2
import os
import os.path

	
class Torrent(object):
	def __init__(self):
		self.infoHash = None
		self.dict = None
	
	
	@staticmethod	
	def fromBencodedData(data):
		"""Build a Torrent object from bencoded data"""
		
		return Torrent.fromDict(bencode.bdecode(data))
		
	
	@staticmethod 
	def fromDict(torrentDict):
		"""Build a torrent from a dictionary. The dictionary
		should follow the metainfo file structure definition
		of a bit torrent file"""
		result = Torrent()
		
		result.dict = torrentDict
		#TODO sanity check for required fields in bit torrent
		#file
		
		return result
	
	def getTotalSizeInBytes(self):
		if 'length' in self.dict['info']:
			return self.dict['info']['length']
		
		if 'files' in self.dict['info']:
			return sum((i['length'] for i in self.dict['info']['files']))
	
	def raw(self):
		"""Return this torrent as a bencoded string"""
		return bencode.bencode(self.dict)
		
	def _computeInfoHash(self):
		self.infoHash = hashlib.sha1()
		self.infoHash.update(bencode.bencode(self.dict['info']))
		
	
	def getInfoHash(self):
		"""Return the info hash of this torrent as a hashlib object"""
		if self.infoHash == None:
			self._computeInfoHash()
			
		return self.infoHash

	def scrub(self):
		"""Remove any commonly present identifying information in the 
		torrent. In addition, set the torrent to private if not already
		so. This function returns True if the torrent is altered
		in such a way that changes the info hash or announce url, both
		of which require the user to redownload it."""
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
		"""Get the announce url of the torrent"""
		return self.dict['announce']
		
	def setAnnounce(self,url):
		"""Set the announce url of the torrent"""
		self.dict['announce'] = url
		
	def getTitle(self):
		return self.dict['info']['name']

class TorrentStore(object):
	
	def __init__(self,torrentPath,trackerUrl):
		self.torrentPath = torrentPath
		self.trackerUrl = str(trackerUrl)
		
		
	def setConnectionPool(self,pool):
		self.connPool = pool
		
	def addTorrent(self,torrent,title,creator):
		"""Add a torrent.
		
		torrent -- the Torrent object to add
		title -- the title of the torrent
		creator -- the id of the user creating the torrent
		
		"""
		with self.connPool.item() as conn:
			cur = conn.cursor()
			try:
				cur.execute(
				"Insert into torrents (title,creationdate, \
				creator, infohash,lengthInBytes) VALUES \
				(%s,NOW(),%s,%s,%s) \
				returning torrents.id;",
				(title,creator,
				base64.urlsafe_b64encode(torrent.getInfoHash().digest()).replace('=',''),
				torrent.getTotalSizeInBytes())
				)
				
				result = cur.fetchone();
				result, = result
				conn.commit();
			except psycopg2.DatabaseError:
				#TODO Log error
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
		"""
		Return the announce url for the user
		
		user -- id of the user
		
		"""
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
		"""
		Return a bencoded string of a torrent
		
		torrentId -- the id number of the torrent being downloaded
		forUser -- the id number of the user downloading the torrent
		"""
		
		torrent = self._retrieveTorrent(torrentId)
		
		if torrent == None:
			return None
		
		announceUrl = self.getAnnounceUrlForUser(forUser)
		
		if None == announceUrl:
			return None
			
		torrent.setAnnounce(announceUrl)
		
		return torrent
	
	def getResourceForTorrent(self,torrentId):
		"""
		Return the download url of a torrent
		
		torrentId -- the id of the torrent 
		"""
		return 'api/torrents/%.8x.torrent' % torrentId
		
	def getInfoResourceForTorrent(self,torrentId):
		"""
		Return the info url of a torrent
		
		torrentId -- the id of the torrent
		"""
		return 'api/torrents/%.8x.json'  % torrentId
	
	def getTorrents(self,limit,subset):
		"""
		Return a list of information about torrents
		
		limits -- the maximum number of torrents to return
		offset -- the starting point of torrents to be returned. This
		is expressed as a factor of limits
		
		"""
		with self.connPool.item() as conn:
			cur = conn.cursor()
			cur.execute(
			"Select torrents.id,torrents.title,torrents.creationdate, \
			users.id,users.name,torrents.lengthInBytes \
			from torrents \
			left join users on torrents.creator = users.id \
			order by creationdate desc limit %s offset %s;",
			(limit,subset*limit, ))
			
			while True:
				r = cur.fetchone()
				if r!=None:
					torrentId,torrentTitle,torrentsCreationDate,userId,userName,lengthInBytes =r
					
					yield {
					'resource' : self.getResourceForTorrent(torrentId),
					'infoResource' : self.getInfoResourceForTorrent(torrentId),
					'title' : torrentTitle,
					'creationDate' : torrentsCreationDate,
					'lengthInBytes' : lengthInBytes,
					'creator': {
						'resource' : 'api/users/%.8x' % userId,
						'name' : userName
						}
					}
				else:
					cur.close()
					break
			
			
				
