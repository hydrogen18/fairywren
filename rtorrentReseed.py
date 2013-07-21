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

def mktorrent(target,announce,pieceLength,private):
	cmd = ['/usr/bin/mktorrent']
	cmd.append('--announce=' + announce)
	cmd.append('--piece-length=' + str(pieceLength))
	
	if private:
		cmd.append('--private')
	
	outfile = '%s.%i.torrent' % (os.tempnam(),os.getpid(),)
	
	cmd.append('--output=' + outfile)
	
	cmd.append(target)

	if 0!= subprocess.call(cmd):
		raise EnvironmentError("mktorrent failed")
		
	return outfile
	
def buildOpener(url,username,password):

	def hashPassword(pw):
		h = hashlib.sha512()
		h.update(pw)
		return base64.urlsafe_b64encode(h.digest()).replace('=','')
	
	qp=urllib.urlencode({"username":username,"password":hashPassword(password)})
	request = urllib2.Request('%s/session' % url,data=qp)
	response = urllib2.urlopen(request)
	
	body = json.load(response)
	
	if 'error' in body:
		raise Error(body['error'])
	
	cookies = cookielib.CookieJar()
	
	cookies.extract_cookies(response,request)
	
	return urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies),MultipartPostHandler.MultipartPostHandler)
	
if __name__ == "__main__":
	with open(sys.argv[1],'r') as fin:
		conf = json.load(fin)

	infoHash = sys.argv[2]
	
	fwurl = conf['fairywren']['url']
	
	#Login to the fairywren instance
	fairywren = buildOpener(fwurl,conf['fairywren']['username'],conf['fairywren']['password'])
	
	#Retrieve the announce url
	account = json.loads(fairywren.open('%/api/session' % fwurl ).read())
	announceUrl = json.loads(fairywren.open(account['my']['href']).read())['announce']['href']
	
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
	
	
	#Create a new torrent
	newTorrentPath = mktorrent(rtorrentLocal.d.get_base_path(infoHash),announceUrl,pieceLength,True)
	
	#Upload the torrent to fairywren
	
	fairywren.open('%s/api/torrents' % fwurl ,data={"title":str(sourceTorrent['info']['name']),"torrent":open(newTorrentPath,'rb')})
	
	#Add the new torrent to the local rtorrent instance
	rtorrentLocal.load.start('',newTorrentPath)
	
	
	
	
		
	
		
	
		
	
	
	
