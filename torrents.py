import hashlib
import bencode
import base64
import cPickle as pickle
import psycopg2
import os
import os.path
import fairywren
import gdbm

class Torrent(object):
	def __init__(self):
		self.infoHash = None
		self.dict = None
	
	
	@staticmethod	
	def fromBencodedData(data):
		"""Build a Torrent object from bencoded data"""
		
		try:
			decoded = bencode.bdecode(data)
		except bencode.BTFailure:
			raise ValueError('not bencoded data')
		
		return Torrent.fromDict(decoded)
		
	
	@staticmethod 
	def fromDict(torrentDict):
		"""Build a torrent from a dictionary. The dictionary
		should follow the metainfo file structure definition
		of a bit torrent file"""
		result = Torrent()
		
		result.dict = torrentDict
		
		if 'info' not in result.dict:
			raise ValueError('missing info')
			
		if type(result.dict['info'])!=dict:
			raise ValueError('info not dict')
				
		if not ( 'announce'  in result.dict  or 'announce-list'  in result.dict):
			raise ValueError('missing announce')
			
		if 'piece length' not in result.dict['info']:
			raise ValueError('missing piece length')
			
		if type(result.dict['info']['piece length'])!=int:
			raise ValueError('piece length not integer')
			
		if 'pieces' not in result.dict['info']:
			raise ValueError('missing pieces')
			
		if type(result.dict['info']['pieces'])!=str:
			raise ValueError('pieces not string')
			
		if 'name' not in result.dict['info']:
			raise ValueError('missing name')
			
		if type(result.dict['info']['name'])!=str:
			raise ValueError('name not string')
			
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
			if k in d.keys():
				d.pop(k)
				return True
				
			return False
		
		touched |= removeIfPresent(self.dict,'announce-list')
		
		if touched and 'announce' not in self.dict :
			self.dict['announce'] = ''
		
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
	EXTENDED_SUFFIX = 'ext'
	def __init__(self,torrentDbPath,trackerUrl):
		self.backingStore = gdbm.open(torrentDbPath,'cf',0600)
		self.trackerUrl = str(trackerUrl)
		
		
	def setConnectionPool(self,pool):
		self.connPool = pool
		
	def addTorrent(self,torrent,title,creator,extended=None):
		"""Add a torrent.
		
		torrent -- the Torrent object to add
		title -- the title of the torrent
		creator -- the id of the user creating the torrent
		extended -- dictionary of extended information to store with the torrent. Must be picklable
		
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
			
		self._storeTorrent(torrent,result,extended)
		return self.getResourceForTorrent(result),self.getInfoResourceForTorrent(result)


	def _buildKeys(self,torrentId):
		if torrentId < 0 or torrentId > (2**32 -1):
			return ValueError("torrentId out of range")
			
		metainfoKey = '%.8x' % torrentId
		infoKey = metainfoKey  + TorrentStore.EXTENDED_SUFFIX
		return metainfoKey, infoKey
	
	def getInfo(self,uid):
		with self.connPool.item() as conn:
			cur = conn.cursor();
			
			cur.execute("Select torrents.infoHash,torrents.id,torrents.title, torrents.creationdate,\
			users.id, users.name, torrents.lengthInBytes \
			from torrents \
			left join users on torrents.creator = users.id \
			where torrents.id = %s",(uid,));
			
			result = cur.fetchone()
			cur.close()
			conn.rollback()
			
		if result == None:
			return None
		infoHash,torrentId,torrentTitle,torrentsCreationDate,userId,userName,lengthInBytes = result
		infoHash = base64.urlsafe_b64decode(infoHash + '==')
		return {
			#'infoHash' : str(infoHash) ,
			'metainfo' : { 'href' : self.getResourceForTorrent(torrentId) },
			'title' : torrentTitle,
			'creationDate' : torrentsCreationDate,
			'lengthInBytes' : lengthInBytes,
			'creator': {
				'href' : fairywren.USER_FMT % userId,
				'name' : userName
				}
			}
			
	def getExtendedInfo(self,torrentId):
		_, metainfoK = self._buildKeys(torrentId)
		try:
			d = self.backingStore[metainfoK]
		except KeyError:
			return None
		return pickle.loads(d)
	
	def _storeTorrent(self,torrent,torrentId,extended=None):
		metainfoK, infoK = self._buildKeys(torrentId)
		self.backingStore[metainfoK] = pickle.dumps(torrent.dict,-1)
		
		if extended == None:
			extended = {}
		
		self.backingStore[infoK] = pickle.dumps(extended,-1)
		self.backingStore.sync()
		
	def _retrieveTorrent(self,torrentId):		
		infoK, _ = self._buildKeys(torrentId)
		try:
			torrentDict = pickle.loads(self.backingStore[infoK])
		except KeyError:
			return None
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
			conn.rollback()
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
		return fairywren.TORRENT_FMT % torrentId
		
	def getInfoResourceForTorrent(self,torrentId):
		"""
		Return the info url of a torrent
		
		torrentId -- the id of the torrent
		"""
		return fairywren.TORRENT_INFO_FMT % torrentId
	
	def getNumTorrents(self):
		with self.connPool.item() as conn:
			cur = conn.cursor()
			
			cur.execute('Select count(1) from torrents;')
			numTorrents, = cur.fetchone()
			cur.close()
			conn.rollback()
		return numTorrents
		
	def searchTorrents(self,tokens):
		
		sql = "Select torrents.infoHash,torrents.id,torrents.title, torrents.creationdate,\
		users.id, users.name, torrents.lengthInBytes \
		from torrents \
		left join users on torrents.creator = users.id \
		where lower(title) like '%%'||lower(%s)||'%%'"
		
		sql+= " and lower(title) like '%%'||lower(%s)||'%%'"*(len(tokens)-1)
		sql+= " order by creationdate desc"
		sql+= ';'
		
		with self.connPool.item() as conn:
			cur = conn.cursor()
			cur.execute(sql,tokens)
			
			for record in cur:
				infoHash,torrentId,torrentTitle,torrentsCreationDate,userId,userName,lengthInBytes = record
				infoHash = base64.urlsafe_b64decode(infoHash + '==')
				yield {
					'infoHash' : infoHash ,
					'metainfo' : { 'href' : self.getResourceForTorrent(torrentId) },
					'info' : {'href' : self.getInfoResourceForTorrent(torrentId) },
					'title' : torrentTitle,
					'creationDate' : torrentsCreationDate,
					'lengthInBytes' : lengthInBytes,
					'creator': {
						'href' : fairywren.USER_FMT % userId,
						'name' : userName
						}
					}
			cur.close()
			conn.rollback()
	
	def getTorrents(self,limit,subset):
		"""
		Return a list of information about torrents
		
		limit -- the maximum number of torrents to return
		offset -- the starting point of torrents to be returned. This
		is expressed as a factor of limit
		
		"""
		with self.connPool.item() as conn:
			cur = conn.cursor()
			cur.execute(
			"Select torrents.infoHash,torrents.id,torrents.title,torrents.creationdate, \
			users.id,users.name,torrents.lengthInBytes \
			from torrents \
			left join users on torrents.creator = users.id \
			order by creationdate desc limit %s offset %s;",
			(limit,subset*limit, ))
			
			while True:
				r = cur.fetchone()
				if r!=None:
					infoHash,torrentId,torrentTitle,torrentsCreationDate,userId,userName,lengthInBytes = r
					infoHash = base64.urlsafe_b64decode(infoHash + '==')
					yield {
					'infoHash' : infoHash ,
					'metainfo' : { 'href' : self.getResourceForTorrent(torrentId) },
					'info' : {'href' : self.getInfoResourceForTorrent(torrentId) },
					'title' : torrentTitle,
					'creationDate' : torrentsCreationDate,
					'lengthInBytes' : lengthInBytes,
					'creator': {
						'href' : fairywren.USER_FMT % userId,
						'name' : userName
						}
					}
				else:
					conn.rollback()
					cur.close()
					break
			
			
				
