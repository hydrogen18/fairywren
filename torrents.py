import hashlib
import bencode
import base64

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
		result = Torrent()
		
		b = ''
		for chunk in dataStream:
			b += chunk
			
		result.dict = bencode.bdecode(b)
		
		#TODO sanity check for required fields in bit torrent
		#file
		
		return result
		
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
		
		if 'private' in self.dict['info'] and self.dict['info']['private'] != 1:
			self.dict['info']['private'] = 1
			touched = True
			
		return touched
		
	def getAnnounceUrl(self):
		return self.dict['announce']

class TorrentStore(object):
	
	def __init__(self):
		pass

	def setConnectionPool(self,pool):
		self.connPool = pool
		
	def addTorrent(self,torrent,title,creator):
		
		with self.connPool.item() as conn:
			cur = conn.cursor()
			cur.execute(
			"Insert into torrents (title,creationdate, \
			creator, infohash) VALUES \
			(%s,NOW(),%s,%s) \
			returning torrents.id;",
			(title,creator,
			base64.urlsafe_b64encode(torrent.getInfoHash().digest()).replace('=',''),)
			)
			
			result = cur.fetchone();
			conn.commit();
			cur.close()
			
		return result
		
		
	
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
					'resource' : '%x.torrent' % torrentId,
					'infoResource' : '%x.json' % torrentId,
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
			
			
				
