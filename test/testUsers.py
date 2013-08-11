from time import sleep
import eventlet
import eventlet.db_pool
import psycopg2
import unittest
import subprocess
import tempfile
import os
import os.path
import shutil
import getpass
import signal
import types
import re
import fairywren
import base64

from TestPostgres import TestPostgres
import users

class TestUsersEmptyDatabase(TestPostgres):
	def setUp(self):
		TestPostgres.setUp(self)
		self.users = users.Users('')
		self.users.setConnectionPool(self.getConnectionPool())
		
	def test_createInvite(self):
		with self.assertRaisesRegexp(ValueError,'.*uid.*') as cm:
			self.users.createInvite(0)
			
	def test_getInviteState(self):
		with self.assertRaisesRegexp(ValueError,'.*nvite.*exist.*secret.*') as cm:
			self.users.getInviteState('0'*32)

	def test_claimInvite(self):
		with self.assertRaisesRegexp(ValueError,'.*nvite.*exist.*claim.*') as cm:
			self.users.claimInvite('\x00'*32,'foo','f'*64)
			
		with self.getConnectionPool().item() as conn:
			cur = conn.cursor()
			cur.execute('Select count(1)  from users')
			numberOfUsers, = cur.fetchone()
		self.assertEqual(0,numberOfUsers)

	def test_getInfo(self):
		self.assertEqual(None,self.users.getInfo(0))
		
class TestUsers(TestPostgres):
	def setUp(self):
		TestPostgres.setUp(self)
		self.users = users.Users('')
		self.users.setConnectionPool(self.getConnectionPool())
		
		self.validusername = 'unittest'
		userpath = self.users.addUser(self.validusername,'\xFF'*64)
		self.assertIsInstance(userpath,types.StringType)
		
		self.validuid = int(re.compile('.*/' + fairywren.UID_RE).match(userpath).groupdict()['uid'],16)
		return

	def test_addUserThatExists(self):	
		with self.assertRaisesRegexp(ValueError,'.*username.*exists.*') as cm:
			self.users.addUser(self.validusername,'0'*64)
			
	def test_getInfo(self):
		x = self.users.getInfo(self.validuid)
		
		self.assertIsInstance(x,types.DictType)
	
	def test_createAndClaimInvite(self):
		path = self.users.createInvite(self.validuid)
		self.assertIsInstance(path,types.StringType)
		
		secret = base64.urlsafe_b64decode(path[-43:] + '=')
		
		self.assertEqual(self.users.getInviteState(secret),False)
		
		with self.assertRaisesRegexp(ValueError,'.*[uU]{1}ser.*exists.*') as cm:
			self.users.claimInvite(secret,self.validusername,'\x00'*64)
		
		newUser = self.users.claimInvite(secret,'fooo','\x00'*64)
		
		self.assertEqual(self.users.getInviteState(secret),True)
		
		self.assertIsInstance(newUser,types.StringType)
		
		
		newUid = self.validuid = int(re.compile('.*/' + fairywren.UID_RE).match(newUser).groupdict()['uid'],16)
		
		
		self.assertIsInstance(self.users.getInfo(newUid),types.DictType)
		
	def test_doubleClaimInvite(self):
		path = self.users.createInvite(self.validuid)
		self.assertIsInstance(path,types.StringType)
		
		secret = base64.urlsafe_b64decode(path[-43:] + '=')
		
		self.users.claimInvite(secret,'fasdflkjdnasfkljnaw','\x00'*64)
		
		self.assertEqual(self.users.getInviteState(secret),True)		
		
		with self.assertRaisesRegexp(ValueError,'.*claimed.*') as cm:
			self.users.claimInvite(secret,'fasdflkjdnasfkljna','\x00'*64)	
		
	def test_getInviteStateNotExist(self):
		with self.assertRaisesRegexp(ValueError,'.*secret.*') as cm:
			#technically this could fail, because test_createInvite could have
			#ran and somehow this was the result of the random value hashing,
			#but that is extremely unlikely
			self.users.getInviteState('\x00'*32)
			
		
if __name__ == '__main__':
    unittest.main()

		
