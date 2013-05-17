

import json
import hashlib
import urllib
import base64
import unittest

def hashPassword(pw):
	h = hashlib.sha512()
	h.update(pw)
	return base64.urlsafe_b64encode(h.digest()).replace('=','')

class SunnyDay(unittest.TestCase):
	
	
	def setUp(self):
		with open("test.json",'r') as fin:
			self.conf = json.load(fin)
			
	def test_0login(self):
		qp = urllib.urlencode(
		{ "username" : self.conf['username'],
		  "password" : hashPassword(self.conf['password'])})
		request = urllib.urlopen("%s/session"  % self.conf['url'],data=qp)
		
		response = json.load(request)
		
		self.assertFalse('error' in response)
		


if __name__ == '__main__':
    unittest.main()
