import unittest
import torrents
import tempfile
from TestPostgres import TestPostgres
import psycopg2
class TestTorrent(TestPostgres):
	TORRENT = {'info': {'length': 65535, 'pieces': '\xc7\xbc\x832]\x80\xfc\xe0\x94\xdf\xf0%\xeds\x1c\xa5\xcb\x02&v', 'piece length': 262144, 'private': 1, 'name': 'tmpRBmSP2'}, 'announce': 'http://127.0.0.1/announce'}
	
	def setUp(self):
		TestPostgres.setUp(self)
		self.gdbmFile = tempfile.NamedTemporaryFile()
		self.torrents = torrents.TorrentStore(self.gdbmFile.name,'http://tracker/')
		self.torrents.setConnectionPool(self.getConnectionPool())
		
	def __del__(self):
		self.gdbmFile.close()
		
	def test_getNumTorrents(self):
		self.assertEqual(0,self.torrents.getNumTorrents())
	
	def test_search(self):
		searchresult = list(self.torrents.searchTorrents(['foo']))
		self.assertEqual(len(searchresult),0)
	
	def test_searchEmpty(self):
		with self.assertRaises(ValueError) as cm:
			list(self.torrents.searchTorrents([]))
			
	def test_getInfo(self):
		with self.assertRaisesRegexp(ValueError,'Torrent.*uid.*') as cm:
			self.torrents.getInfo(0)
			
	def  test_addTorrent(self):
		#should raise this exception since torrent is valid but 
		#user does not exist
		with self.assertRaisesRegexp(ValueError,'User.*uid.*') as cm:
			self.torrents.addTorrent(torrents.Torrent.fromDict(TestTorrent.TORRENT),'foobar',0)
			
	def test_getExtendedInfo(self):
		with self.assertRaisesRegexp(ValueError,'.*torrent.*') as cm:
			self.torrents.getExtendedInfo(0)
			
	def test_getAnnounceUrlForUser(self):
		with self.assertRaisesRegexp(ValueError,'.*user id.*') as cm:
			self.torrents.getAnnounceUrlForUser(0)
			
	def test_getTorrentForDownload(self):
		#raises because specified torrent doesn't exist
		with self.assertRaisesRegexp(ValueError,'.*torrent.*') as cm:
			self.torrents.getTorrentForDownload(0,0)
			
	def test_getTorrents(self):
		self.assertEqual(0,len(list(self.torrents.getTorrents(50,0))))
		
		

if __name__ == '__main__':
	unittest.main()

