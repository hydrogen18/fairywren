import hashlib
import bencode
import base64
import cPickle as pickle
import cStringIO as StringIO
import psycopg2
import os
import os.path
import fairywren
import logging

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
		
		result.dict = dict(torrentDict)
		
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
	def __init__(self,trackerUrl):
		self.log = logging.getLogger('fairywren.torrentstore')

		self.trackerUrl = str(trackerUrl)
		self.log.info('Created')
		
	def setConnectionPool(self,pool):
		self.connPool = pool
		
	def addTorrent(self,torrent,title,creator,extended=None):
		"""Add a torrent.
		
		torrent -- the Torrent object to add
		title -- the title of the torrent
		creator -- the id of the user creating the torrent
		extended -- dictionary of extended information to store with the torrent. Must be picklable
		
		"""
		
		if extended == None:
			extended = {}
			
		with self.connPool.item() as conn:
			cur = conn.cursor()
			try:
				cur.execute(
				"Insert into torrents (title,creationdate, \
				creator, infohash,lengthInBytes,metainfo,extendedinfo) VALUES \
				(%s,timezone('UTC',CURRENT_TIMESTAMP),%s,%s,%s,%s,%s) \
				returning torrents.id;",
				(title,creator,
				base64.urlsafe_b64encode(torrent.getInfoHash().digest()).replace('=',''),
				torrent.getTotalSizeInBytes(),
				psycopg2.Binary(pickle.dumps(torrent.dict,-1)),
				psycopg2.Binary(pickle.dumps(extended,-1)),)
				)
				
				result = cur.fetchone();
				result, = result
				conn.commit();
			except psycopg2.IntegrityError as e:
				conn.rollback()
				#This string is specified in the postgre documentation appendix
				# 'PostgreSQL Error Codes' as 'unique_violation' and corresponds
				#to primary key violations
				if e.pgcode == '23505':
					raise ValueError('Torrent already exists with that infohash')
				# 'foreign_key_violation' - violation of 'creator' foreign key
				# i.e. user with uid doesn't exist
				elif e.pgcode == '23503':
					raise ValueError('User does not exist with that uid')
				raise e
			except psycopg2.DatabaseError as e:
				self.log.exception('Error adding torrent',exc_info=True)
				conn.rollback()
				raise e
			finally:
				cur.close()
			
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
			try:
				cur.execute("Select torrents.infoHash,torrents.id,torrents.title, torrents.creationdate,\
				users.id, users.name, torrents.lengthInBytes \
				from torrents \
				left join users on torrents.creator = users.id \
				where torrents.id = %s",(uid,));
			except psycopg2.DatabaseError as e:
				self.log.exception('Error retrieving info for torrent',exc_info=True)
				conn.rollback()
				raise e
			
			result = cur.fetchone()
			cur.close()
			conn.rollback()
			
		if result == None:
			raise ValueError('Torrent does not exist for specified uid')
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

		with self.connPool.item() as conn:
			cur = conn.cursor()
			try:
				cur.execute('Select extendedinfo from torrents where id=%s',(torrentId,))
			except psycopg2.DatabaseError as e:
				self.log.exception('Error retrieving extendedinfo for torrent %.8x', torrentId,exc_info=True)
				cur.close()
				conn.rollback()
				raise e
			
			result = cur.fetchone()
			cur.close()
			conn.rollback()
		if result == None:
			self.log.debug('Request for extended info on non existent torrent %.8x',torrentId)
			raise ValueError('Specified torrent does not exist')

		result, = result
		result = StringIO.StringIO(result)
		edict = pickle.load(result)		
		
		return edict
	
	def getAnnounceUrlForUser(self,user):
		"""
		Return the announce url for the user
		
		user -- id of the user
		
		"""
		with self.connPool.item() as conn:
			cur = conn.cursor()
			try:
				cur.execute(
				"Select secretkey from users where id=%s;",
				(user,))
			except psycopg2.DatabaseError as e:
				self.log.exception('Error retrieving announce url for user',exc_info=True)
				conn.rollback()
				raise e
			
			result = cur.fetchone()
			conn.rollback()
			cur.close()
			
		if None == result:
			raise ValueError('Specified user id does not exist')
		result, = result
		return '%s/%s/announce' % (self.trackerUrl,result,)
			
	
	def getTorrentForDownload(self,torrentId,forUser):
		"""
		Return a torrent object
		
		torrentId -- the id number of the torrent being downloaded
		forUser -- the id number of the user downloading the torrent
		"""

		with self.connPool.item() as conn:
			cur = conn.cursor()
			try:
				cur.execute('Select metainfo from torrents where id=%s',(torrentId,))
			except psycopg2.DatabaseError as e:
				self.log.exception('Error retrieving metainfo for torrent %.8x', torrentId,exc_info=True)
				cur.close()
				conn.rollback()
				raise e
			
			result = cur.fetchone()
			cur.close()
			conn.rollback()
		if result == None:
			self.log.debug('Request for metainfo on non existent torrent %.8x',torrentId)
			raise ValueError('Torrent does not exist')

		result, = result
		result = StringIO.StringIO(result)
		tdict = pickle.load(result)

		torrent = Torrent.fromDict(tdict)
		
		announceUrl = self.getAnnounceUrlForUser(forUser)	
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

		if len(tokens) == 0:
			raise ValueError('search token list length must be > 0')
		
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
			
			try:
				cur.execute(sql,tokens)
			except psycopg2.DatabaseError as e:
				self.log.exception('Error searching for torrents',exc_info=True)
				conn.rollback()
				raise e
			
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
			try:
				cur.execute(
				"Select torrents.infoHash,torrents.id,torrents.title,torrents.creationdate, \
				users.id,users.name,torrents.lengthInBytes \
				from torrents \
				left join users on torrents.creator = users.id \
				order by creationdate desc limit %s offset %s;",
				(limit,subset*limit, ))
			except psycopg2.DatabaseError as e:
				self.log.exception('Error retrieving torrent listing',exc_info=True)
				conn.rollback()
				raise e	
			
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
			
			
				
