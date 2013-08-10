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
	
def mediainfo(*files):
	cmd = ['/usr/bin/mediainfo','--output=XML']
	cmd += files
	
	proc = subprocess.Popen(cmd,stdout=subprocess.PIPE)
	#Read all the output
	stdout, _ = proc.communicate()
	
	#Check for failure
	if 0!=proc.returncode:
		raise EnvironmentError('mediainfo failed')
	retval = {}
	
	#Parse the output
	doc = xml.dom.minidom.parseString(stdout)
	#Ignore anything not in the first Mediainfo tag
	doc = doc.getElementsByTagName('Mediainfo')[0]
	#Extract the mediainfo version
	retval['version'] = doc.getAttribute('version').strip()
	retval['files'] = {}
	#For each file, extract the information about the tracks
	for f in doc.getElementsByTagName('File'):
		f_ = {}
		f_['tracks'] = []
		name = None
		for track in f.getElementsByTagName('track'):
			t = {}
			t['type'] = str(track.getAttribute('type'))
			for tag in track.childNodes:
				if len(tag.childNodes)==1 and 'text' in tag.childNodes[0].nodeName:
					key = tag.tagName.strip()
					value = tag.childNodes[0].nodeValue.strip()
					#Mediainfo shows the name of the file in the
					#General track
					if t['type'] == 'General' and 'Complete_name' == key:
						name = value
					else:
						t[key] = value
			f_['tracks'].append(t)


		name = name.strip().split(os.sep)[-1]			
		retval['files'][name] = f_
		
	return retval
		
	
def buildOpener(url,username,password):

	def hashPassword(pw):
		h = hashlib.sha512()
		h.update(pw)
		return base64.urlsafe_b64encode(h.digest()).replace('=','')
	
	qp=urllib.urlencode({"username":username,"password":hashPassword(password)})
	request = urllib2.Request('%s/api/session' % url,data=qp)
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
	
	fwurl = str(conf['fairywren']['url'])
	
	#Login to the fairywren instance
	fairywren = buildOpener(fwurl,conf['fairywren']['username'],conf['fairywren']['password'])
	
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
	
	try:
		files = os.listdir(filesPath)
	except OSError as e:
		if e.errno!=20:
			raise e
			
		files = [filesPath]
	
	files = [os.path.join(filesPath,f) for f in files]
	
	minfo = mediainfo(*files)
	
	#Upload the torrent to fairywren
	fairywren.open('%s/api/torrents' % fwurl ,data={"extended": json.dumps({ "mediainfo" : minfo }) , "title":str(sourceTorrent['info']['name']),"torrent":open(newTorrentPath,'rb')})
	
	#Add the new torrent to the local rtorrent instance
	rtorrentLocal.load.start('',newTorrentPath)
	
	
	
	
		
	
		
	
		
	
	
	
