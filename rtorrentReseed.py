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
import MultipartPostHandler
import cookielib
import hashlib
import base64
import types
import xml.dom.minidom

from upload import *
	
if __name__ == "__main__":
	with open(sys.argv[1],'r') as fin:
		conf = json.load(fin)

	infoHash = sys.argv[2]
	
	#Login to the fairywren instance
	fairywren = buildOpener(**fconf['fairywren'])
	
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
		
	#Get the current piece size as a power of 2
	pieceLength = int( math.log(sourceTorrent['info']['piece length'],2) )
	
	#Change the piece size to change the infoHash
	if pieceLength > 19:
		pieceLength -= 1
	else:
		pieceLength += 1

	filesPath = rtorrentLocal.d.get_base_path(infoHash)
	#Create a new torrent
	newTorrentPath = mktorrent(filesPath,announceUrl,pieceLength,True)
	
	files = listFiles(filesPath)
	minfo = mediainfo(*files)
	
	#Upload the torrent to fairywren
	fairywren.open('%s/api/torrents' % fwurl ,data={"extended": json.dumps({ "mediainfo" : minfo }) , "title":str(sourceTorrent['info']['name']),"torrent":open(newTorrentPath,'rb')})
	
	#Disable torrent checking
	rtorrentLocal.set_check_hash(0)
	
	#Add the new torrent to the local rtorrent instance
	rtorrentLocal.load.start('',newTorrentPath)
	
	#Enable torrent checking
	rtorrentLocal.set_check_hash(1)
	
	
	
	
		
	
		
	
		
	
	
	
