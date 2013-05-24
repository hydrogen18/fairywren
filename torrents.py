import hashlib
import bencode

def computeInfoHash(rawBencodedData):
	
	torrent = bencode.bdecode(rawBencodedData)
	info_hash = hashlib.sha1()
	info_hash.update(bencode.bencode(torrent['info']))

	print info_hash.hexdigest()

class TorrentStore(object):
	
	def __init__(self):
		pass

	def setConnectionPool(self,pool):
		self.connPool = pool
		
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
			
			
				
