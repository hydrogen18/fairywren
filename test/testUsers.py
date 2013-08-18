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
		
	def test_listInvitesByUser(self):
		self.assertEqual(0,len(list(self.users.listInvitesByUser(0))))
		
class TestBootstrapRoles(TestPostgres):
	def setUp(self):
		TestPostgres.setUp(self)
		self.users = users.Users('')
		self.users.setConnectionPool(self.getConnectionPool())
		
	def test_createRoles(self):
		testRoles = ['foo','bar','qux']
		self.assertEqual(len(testRoles),self.users.createRoles(testRoles))
		
		testRoles.reverse()
		#Calling a second time should result in nothing happening
		self.assertEqual(0,self.users.createRoles(testRoles))
		
class TestWithValidUser(TestPostgres):		
	def setUp(self):
		TestPostgres.setUp(self)
		self.users = users.Users('')
		self.users.setConnectionPool(self.getConnectionPool())
		
		self.validusername = 'unittest'
		userpath,self.validuid = self.users.addUser(self.validusername,'\xFF'*64)
		self.assertIsInstance(userpath,types.StringType)
		
		return


class TestSetUserRoles(TestWithValidUser):
	def setUp(self):
		TestWithValidUser.setUp(self)

		self.testRoles = ['dungeonmaster','foo','bar','qux','troll']
		self.assertEqual(len(self.testRoles),self.users.createRoles(self.testRoles))

	def test_putUserInNonExistentRole(self):
		with self.assertRaisesRegexp(ValueError,'.*[Rr]{1}ole.*exist.*') as cm:
			self.users.setUserRoles(['fadskjhfdkjsbfdzkljsf'],self.validuid)

	def test_putNonExistentUserInRole(self):
		with self.assertRaisesRegexp(ValueError,'.*[Uu]{1}ser.*exist.*') as cm:
			self.users.setUserRoles(self.testRoles,self.validuid*999)			
	
	def test_it(self):
		
		numAdd, numRemove = self.users.setUserRoles(self.testRoles,self.validuid)
		
		self.assertEqual(len(self.testRoles),numAdd)
		self.assertEqual(0,numRemove)
		
		self.assertEqual(set(self.testRoles), set(self.users.getUserRoles(self.validuid)))
		
		numAdd, numRemove = self.users.setUserRoles([],self.validuid)
		
		self.assertEqual(len(self.testRoles),numRemove)
		self.assertEqual(0,numAdd)
		
		self.assertEqual(set(), set(self.users.getUserRoles(self.validuid)))
		
		#same code again should change nothing
		numAdd, numRemove = self.users.setUserRoles([],self.validuid)
		
		self.assertEqual(0,numRemove)
		self.assertEqual(0,numAdd)
		
		self.assertEqual(set(), set(self.users.getUserRoles(self.validuid)))
		
		
class TestUserRoles(TestWithValidUser):
	
	def setUp(self):
		TestWithValidUser.setUp(self)

		self.testRoles = ['dungeonmaster']
		self.assertEqual(len(self.testRoles),self.users.createRoles(self.testRoles))
	
	def test_addRemoveUser(self):

		self.users.addUserToRole(self.testRoles[0],self.validuid)
		
		self.assertIn(self.testRoles[0], self.users.getUserRoles(self.validuid))
		
		#Calling a second time should result in nothing happening
		self.users.addUserToRole(self.testRoles[0],self.validuid)
		
		self.assertIn(self.testRoles[0], self.users.getUserRoles(self.validuid))
		
		self.users.removeUserFromRole(self.testRoles[0],self.validuid)
		
		self.assertNotIn(self.testRoles[0], self.users.getUserRoles(self.validuid))
		
		#Calling a second time should result in nothing happening
		self.users.removeUserFromRole(self.testRoles[0],self.validuid)
		
		self.assertNotIn(self.testRoles[0], self.users.getUserRoles(self.validuid))
		
		
	def test_addUserDoesNotExist(self):

		with self.assertRaisesRegexp(ValueError,'.*[Uu]{1}ser.*exist.*') as cm:
			self.users.addUserToRole(self.testRoles[0],self.validuid*999)
			
	def test_removeUserFromRole(self):
		with self.assertRaisesRegexp(ValueError,'.*[Rr]{1}ole.*exist.*') as cm:
			self.users.removeUserFromRole('fkjd;lasnf4auwnfaw', self.validuid)
			
	def test_roleDoesNotExist(self):
		with self.assertRaisesRegexp(ValueError,'.*[Rr]{1}ole.*exist.*') as cm:
			self.users.addUserToRole('daeslnf23kijrn',self.validuid)
		
		
				
class TestUsers(TestWithValidUser):

	def test_addUserThatExists(self):	
		with self.assertRaises(users.UserAlreadyExists) as cm:
			self.users.addUser(self.validusername,'0'*64)
			
	def test_getInfo(self):
		x = self.users.getInfo(self.validuid)
		
		self.assertIsInstance(x,types.DictType)
	
	def test_createAndClaimInvite(self):
		path = self.users.createInvite(self.validuid)
		self.assertIsInstance(path,types.StringType)
		
		secret = base64.urlsafe_b64decode(path[-43:] + '=')
		
		self.assertEqual(self.users.getInviteState(secret),False)
		
		with self.assertRaises(users.UserAlreadyExists) as cm:
			self.users.claimInvite(secret,self.validusername,'\x00'*64)
		
		newUser = self.users.claimInvite(secret,'fooo','\x00'*64)
		
		self.assertEqual(self.users.getInviteState(secret),True)
		
		self.assertIsInstance(newUser,types.StringType)
				
		newUid = int(re.compile('.*/' + fairywren.UID_RE).match(newUser).groupdict()['uid'],16)
		
		self.assertIsInstance(self.users.getInfo(newUid),types.DictType)
		
	def test_doubleClaimInvite(self):
		path = self.users.createInvite(self.validuid)
		self.assertIsInstance(path,types.StringType)
		
		secret = base64.urlsafe_b64decode(path[-43:] + '=')
		
		self.users.claimInvite(secret,'fasdflkjdnasfkljnaw','\x00'*64)
		
		self.assertEqual(self.users.getInviteState(secret),True)		
		
		with self.assertRaisesRegexp(ValueError,'.*claimed.*') as cm:
			self.users.claimInvite(secret,'fasdfljdnasfkljna','\x00'*64)	
		

			
		
if __name__ == '__main__':
    unittest.main()

		
