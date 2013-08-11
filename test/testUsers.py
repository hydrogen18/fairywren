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

from TestPostgres import TestPostgres
import users

class TestUsersEmptyDatabase(TestPostgres):
	def setUp(self):
		TestPostgres.setUp(self)
		self.users = users.Users()
		self.users.setConnectionPool(self.getConnectionPool())
		
	def test_createInvite(self):
		with self.assertRaisesRegexp(ValueError,'.*uid.*') as cm:
			self.users.createInvite(0)
			
			
	def test_getInfo(self):
		self.assertEqual(None,self.users.getInfo(0))
			
		
if __name__ == '__main__':
    unittest.main()

		
