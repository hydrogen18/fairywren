

import json
import hashlib
import urllib
import urllib2
import base64
import unittest
import cookielib 
import tempfile
import random
import subprocess
import os
import multipart

def hashPassword(pw):
	h = hashlib.sha512()
	h.update(pw)
	return base64.urlsafe_b64encode(h.digest()).replace('=','')

class SunnyDay(unittest.TestCase):
	
	
	def setUp(self):
		with open("test.json",'r') as fin:
			self.conf = json.load(fin)
		self.cookie = cookielib.CookieJar()
		qp = urllib.urlencode(
		{ "username" : self.conf['username'],
		  "password" : hashPassword(self.conf['password'])})
		request = urllib2.Request("%s/session"  % self.conf['url'],data=qp)
		response = urllib2.urlopen(request)
		
		body = json.load(response)
		
		self.assertFalse('error' in body)
		
		self.cookie.extract_cookies(response,request)
		
		self.assertTrue ('session' in ( cookie.name for cookie in self.cookie))

		for c in self.cookie:
			if c.name == 'session':
				self.cookie = "%s=%s" % (c.name,c.value,)
		
	def open(self,*url):
		request = urllib2.Request(*url)
		request.add_header('Cookie',self.cookie)
		return urllib2.urlopen(request)
	
	def test_getSession(self):
		response = self.open("%s/session" % self.conf['url'])
		
		body = json.load(response)
		
		self.assertTrue('announceResource' in body)
	
	def test_getTorrents(self):
		response = self.open("%s/torrents" % self.conf['url'])
		
		body = json.load(response)
		
		self.assertTrue('torrents' in body)
		
		for t in body['torrents']:
			self.assertTrue('resource' in t)
			self.assertTrue('infoResource' in t)
			self.assertTrue('title' in t)
			self.assertTrue('creationDate' in t)
			self.assertTrue('creator' in t)
			self.assertTrue('resource' in t['creator'])
			self.assertTrue('name' in t['creator'])
			
	def test_addTorrent(self):
		#create a torrent
		with tempfile.NamedTemporaryFile(delete=True) as fout:
		
			for c in random.sample(range(0,256),128):
				fout.write(chr(c))
			
			fout.flush()
			
			torrentFileName= '%s.torrent' % fout.name 
			
			cmd = ['mktorrent','-a','http://127.0.0.1/announce','-o',torrentFileName, fout.name]
			self.assertEqual(0,subprocess.Popen(cmd).wait())
		
		try:
			with open(torrentFileName,'r') as fin:
				response = multipart.post_multipart('192.168.12.182','/nihitorrent/api/torrents', self.cookie, [('title','Test Torrent')],[('torrent','test.torrent',fin.read())])
				response = json.loads(response)
				torrentUrl = response['resource']
		except Exception:
			raise
		finally:
			os.remove(torrentFileName)
		
		print torrentUrl	
		response = self.open(torrentUrl)
		
		print response.read()
			
if __name__ == '__main__':
    unittest.main()
