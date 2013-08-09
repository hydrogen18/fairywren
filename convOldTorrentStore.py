import sys
import gdbm
import torrents
import os
import os.path
import cPickle as pickle

if __name__ == "__main__":
	torrentsDir = sys.argv[1]
	
	db = gdbm.open(sys.argv[2],'cf',0600)
	
	for root,dirs,files in os.walk(torrentsDir):
		for f in files:
			fpath = os.path.join(root,f)
			with open(fpath) as fin:
				torrentdict = pickle.load(fin)
			path = fpath.split(os.sep)
			torrentId = int(path[-4] + path[-3] + path[-2] + path[-1],16)
			print '%.8x' % torrentId 
			db['%.8x' % torrentId ] = pickle.dumps(torrentdict,-1)
			db[('%.8x' % torrentId) + torrents.TorrentStore.EXTENDED_SUFFIX ] = pickle.dumps({},-1)
			
	
	db.sync()
