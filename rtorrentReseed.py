#!/usr/bin/python
import sys
import json
import xmlrpclib
import os
import bencode
import math
import subprocess
import urllib
import urllib2
import urlparse
import MultipartPostHandler
import cookielib
import hashlib
import base64
import types
import xml.dom.minidom
import tempfile

from upload import *
	
if __name__ == "__main__":
	with open(sys.argv[1],'r') as fin:
		conf = json.load(fin)

	infoHash = sys.argv[2]
	
	#Login to the fairywren instance
	fairywren = buildOpener(**conf['fairywren'])
	fwurl = str(conf['fairywren']['url'])
	#Retrieve the announce url
	account = json.loads(fairywren.open('%s/api/session' % fwurl ).read())
	announceUrl = json.loads(fairywren.open('%s/%s' % ( fwurl, account['my']['href'] ) ).read())['announce']['href']
	
	#Open an RPC session to the local rtorrent instance
	rtorrentLocal = xmlrpclib.ServerProxy(conf['rtorrentLocal']['url'])
	
	#Open the torrent file from rtorrent's session directory
	with open(os.path.join(rtorrentLocal.get_session(),'%s.torrent' % infoHash),'rb') as fin:
		sourceTorrent = bencode.bdecode(fin.read())
	
	#Check to see if this torrent is from the fairywren tracker already
	if announceUrl == sourceTorrent['announce'] or ('announce-list' in sourceTorrent and announceUrl in sourceTorrent['announce-list']):
		sys.exit(0)
	
	oldAnnounce = urlparse.urlparse(sourceTorrent['announce'])
	h = hashlib.sha1()
	h.update(oldAnnounce.scheme)
	h.update(oldAnnounce.netloc)
	sourceTorrent['info']['x_cross_seed'] = h.digest()
	sourceTorrent['announce'] = str(announceUrl)
	sourceTorrent.pop('announce-list',None)
	sourceTorrent.pop('creation date',None)
	sourceTorrent.pop('comment',None)
	sourceTorrent.pop('created by',None)
	sourceTorrent.pop('encoding',None)

	filesPath = rtorrentLocal.d.get_base_path(infoHash)	
	files = listFiles(filesPath)
	minfo = mediainfo(*files)
	
	#Create a new torrent
	with tempfile.NamedTemporaryFile(suffix='.torrent') as fout:
		fout.write(bencode.bencode(sourceTorrent))
		fout.flush()

		with open(fout.name,'rb') as fin:
			#Upload the torrent to fairywren
			fairywren.open('%s/api/torrents' % fwurl ,data={"extended": json.dumps({ "mediainfo" : minfo }) , "title":str(sourceTorrent['info']['name']),"torrent":fin})	            
		os.chmod(fout.name,0444)
		#Add the new torrent to the local rtorrent instance
		rtorrentLocal.load.start('',fout.name)
	
	
	
	
	
		
	
		
	
		
	
	
	
