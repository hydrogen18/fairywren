import unittest
import torrents
import tempfile
from TestPostgres import *
class TestTorrent(TestPostgres):
	TORRENT = {'info': {'length': 65535, 'pieces': '\xc7\xbc\x832]\x80\xfc\xe0\x94\xdf\xf0%\xeds\x1c\xa5\xcb\x02&v', 'piece length': 262144, 'private': 1, 'name': 'tmpRBmSP2'}, 'announce': 'http://127.0.0.1/announce'}
	
	def setUp(self):
		TestPostgres.setUp(self)
		self.gdbmFile = tempfile.NamedTemporaryFile()
		self.torrents = torrents.TorrentStore(self.gdbmFile.name,'http://tracker/')
		self.torrents.setConnectionPool(self.connpool)
		
	def test_getNumTorrents(self):
		self.assertEqual(0,self.torrents.getNumTorrents())
		
	def test_search(self):
		searchresult = list(self.torrents.searchTorrents(['foo']))
		self.assertEqual(len(searchresult),0)
		
	def test_searchEmpty(self):
		with self.assertRaises(ValueError) as cm:
			self.torrents.searchTorrents([])
			
		
		

if __name__ == '__main__':
	unittest.main()

