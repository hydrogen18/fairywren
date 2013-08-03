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

PG_DIR = '/usr/lib/postgresql/9.1'
def initdb(authmethod,directory):
	PATH = PG_DIR + '/bin/initdb'
	
	cmd = [PATH,'--auth='+authmethod,'--pgdata=' + directory]
	proc = subprocess.Popen(cmd)
	
	if proc.wait()!=0:
		raise SystemError('Failed to initdb')
		
def pg_ctl(directory,action,options=None):
	PATH = os.path.join(PG_DIR,'bin','pg_ctl')
	
	cmd = [PATH,action,'-D',directory,]
	
	if action == 'start':
		cmd.insert(2,'-w')
		
	if options!=None:
		cmd.append('-o')
		cmd.append(options)
		
	proc = subprocess.Popen(cmd)
	
	if proc.wait()!=0:
		raise SystemError('Failed to initdb')
	
class TestPostgres(unittest.TestCase):
	def setUp(self):
		self.tempdir = tempfile.mkdtemp()
		initdb('trust',self.tempdir)
		
		self.sockdir = os.path.join(self.tempdir,'socket')
		os.mkdir(self.sockdir)
		
		pg_ctl(self.tempdir,'start',"-k %s -h ''" % self.sockdir)
		while 0==len(os.listdir(self.sockdir)):
			pass
		sleep(2)
		
		with psycopg2.connect(host=self.sockdir, database='postgres',user=getpass.getuser()) as conn:
			conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
			cur = conn.cursor()
			cur.execute('CREATE DATABASE nihitorrent;')
			cur.close()
			
		
		self.connpool = eventlet.db_pool.ConnectionPool(psycopg2,host=self.sockdir, database='nihitorrent',user=getpass.getuser())
		self.loadSqlFromFile('roles.sql')
		self.loadSqlFromFile('fairywren.sql')
		self.loadSqlFromFile('permissions.sql')	
		
	def loadSqlFromFile(self,filename):
		with self.getConnectionPool().item() as conn:
			cur = conn.cursor()
			cur.execute(open(os.path.join(os.environ['PYTHONPATH'],filename)).read())	
			cur.close()
			conn.commit()
		
	def __del__(self):

		self.getConnectionPool().clear()
		self.connpool = None
		
		pg_ctl(self.tempdir,'stop')

		shutil.rmtree(self.tempdir)
	
	def getConnectionPool(self):
		return self.connpool
		
	def test_ok(self):
		with self.getConnectionPool().item() as conn:
			cur = conn.cursor()
			cur.execute('Select 1;')
			
			result, = cur.fetchone()
			self.assertEqual(1,result)
			
			cur.close()
			
			conn.rollback()
			
		
if __name__ == '__main__':
    unittest.main()

		
