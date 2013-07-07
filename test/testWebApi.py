

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
import MultipartPostHandler
import types
import string

def hashPassword(pw):
	h = hashlib.sha512()
	h.update(pw)
	return base64.urlsafe_b64encode(h.digest()).replace('=','')

class WebapiTest(unittest.TestCase):
	def buildFairywrenOpener(self,url,username,password):
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
		self.assertTrue ('session' in ( cookie.name for cookie in cookies))
		
		for c in cookies:
			if c.name == "session":
				self.cookie = "%s=%s" % (c.name,c.value,)
		
		self.open = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies),MultipartPostHandler.MultipartPostHandler).open

		
		
	
	def setUp(self):
		with open("test.json",'r') as fin:
			self.conf = json.load(fin)
			
		self.buildFairywrenOpener(  self.conf['url'], self.conf['username'],self.conf['password'] )

class RainyDay(WebapiTest):
	def test_addExistingUser(self):
		with open('/dev/urandom','r') as randomIn:
			username = randomIn.read(64)
		username = ''.join([c for c in username if c in string.ascii_letters])
		password = 'password'
			
		pwHash = hashlib.sha512()
		pwHash.update(password)
		pwHash = base64.urlsafe_b64encode(pwHash.digest()).replace('=','')
		qp = {'username': username, 'password' : pwHash }
		
		response  = self.open('%s/api/users' % self.conf['url'] , qp)
		body = json.load(response)
		
		self.assertTrue('resource' in body)
		
		self.assertRaisesRegexp(urllib2.HTTPError,'.*409.*',self.open,'%s/api/users' % self.conf['url'] , qp)
		

class SunnyDay(WebapiTest):
		
	def test_addUser(self):
		
		with open('/dev/urandom','r') as randomIn:
			username = randomIn.read(64)
		username = ''.join([c for c in username if c in string.ascii_letters])
		password = 'password'
			
		pwHash = hashlib.sha512()
		pwHash.update(password)
		pwHash = base64.urlsafe_b64encode(pwHash.digest()).replace('=','')
		qp = {'username': username, 'password' : pwHash }
		
		response  = self.open('%s/api/users' % self.conf['url'] , qp)
		body = json.load(response)
		
		self.assertTrue('resource' in body)
		
		pwHash = hashlib.sha512()
		pwHash.update('password1')
		pwHash = base64.urlsafe_b64encode(pwHash.digest()).replace('=','')
		query = { 'password' : pwHash }
		response = self.open('%s/%s/password' % (self.conf['url'], body['resource']),query)		
		
		response = self.open('%s/%s' % ( self.conf['url'], body['resource']))
		
		body = json.load(response)
		
		self.assertTrue(body['name'] == username)
		self.assertTrue(body['numberOfTorrents'] == 0)
		

		
		
	def test_getSession(self):
		response = self.open("%s/api/session" % self.conf['url'])
		
		body = json.load(response)
		
	
	def test_getTorrents(self):
		response = self.open("%s/api/torrents" % self.conf['url'])
		
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
