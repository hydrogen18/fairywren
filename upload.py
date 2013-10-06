import sys
import json
import os
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
	stdout, stderr = proc.communicate()
	
	#Check for failure
	if 0!=proc.returncode:
		print stdout
		print stderr
		raise SystemError('mediainfo failed')
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

def listFiles(filesPath):
    
	try:
		files = os.listdir(filesPath)
	except OSError as e:
		if e.errno!=20:
			raise e
		files = [filesPath]
	        return files
	
	files = [os.path.join(filesPath,f) for f in files]	
    
	return files
	
def buildOpener(url,username,password):
	url = str(url)
    
	def hashPassword(pw):
		h = hashlib.sha512()
		h.update(pw)
		return base64.urlsafe_b64encode(h.digest()).replace('=','')
	
	qp=urllib.urlencode({"username":username,"password":hashPassword(password)})
	request = urllib2.Request('%s/api/session' % url,data=qp)
	response = urllib2.urlopen(request)
	
	body = json.load(response)
	
	if 'error' in body:
		raise Exception(body['error'])
	
	cookies = cookielib.CookieJar()
	
	cookies.extract_cookies(response,request)
	
	return urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies),MultipartPostHandler.MultipartPostHandler)


if __name__ == "__main__":
	with open(sys.argv[1],'r') as fin:
		conf = json.load(fin)

	#Login to the fairywren instance
	fairywren = buildOpener(**conf['fairywren'])

	fwurl = str(conf['fairywren']['url'])
	#Retrieve the announce url
	account = json.loads(fairywren.open('%s/api/session' % fwurl ).read())
	announceUrl = json.loads(fairywren.open('%s/%s' % ( fwurl, account['my']['href'] ) ).read())['announce']['href']
		
	#Get the current piece size as a power of 2
	pieceLength = 18
	
	filesPath = sys.argv[2]


    
	#Create a new torrent
	newTorrentPath = mktorrent(filesPath,announceUrl,pieceLength,True)
	
	files = listFiles(filesPath)

	extendedInfo = {}
	try:
		minfo = mediainfo(*files)
		extendedInfo['mediainfo'] = minfo
	except SystemError as e:
		print 'No mediainfo on upload...'

	if len(sys.argv) == 4:
		title = sys.argv[3]
	else:
		title = os.path.split(filesPath)[-1]

	
	#Upload the torrent to fairywren
	fairywren.open('%s/api/torrents' % fwurl ,data={"extended": json.dumps(extendedInfo) , "title":str(title),"torrent":open(newTorrentPath,'rb')})
	
	os.unlink(newTorrentPath)
    
	
	
