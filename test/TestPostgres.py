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
		cmd.insert(2,os.devnull)
		cmd.insert(2,'-l')
	elif action == 'stop':
		cmd.insert(2,'fast')
		cmd.insert(2,'-m')
		
	if options!=None:
		cmd.append('-o')
		cmd.append(options)
		
	proc = subprocess.Popen(cmd)
	
	if proc.wait()!=0:
		raise SystemError('Failed to %s' % ' '.join(cmd))
	

#
tempdir = tempfile.mkdtemp()
initdb('trust',tempdir)

sockdir = os.path.join(tempdir,'socket')
os.mkdir(sockdir)

pg_ctl(tempdir,'start',"-k %s -h ''" % sockdir)
while 0==len(os.listdir(sockdir)):
	pass
sleep(2)

dbnum = 0	

import atexit

def cleanup():
	pg_ctl(tempdir,'stop')
	shutil.rmtree(tempdir)
atexit.register(cleanup)

#atexit.register( pg_ctl, tempdir, 'stop') #pg_ctl(self.tempdir,'stop')

#atexit.register(shutil.rmtree, tempdir) #shutil.rmtree(self.tempdir)

def loadSqlFromFile(conn,filename):
	cur = conn.cursor()
	cur.execute(open(os.path.join(os.environ['PYTHONPATH'],filename)).read())	
	cur.close()
	conn.commit()

with psycopg2.connect(host=sockdir,database='postgres',user=getpass.getuser()) as conn:
		loadSqlFromFile(conn,'roles.sql')
		

	
class TestPostgres(unittest.TestCase):
	def setUp(self):
		global dbnum
		self.dbname = 'nihitorrent%d' % dbnum
		dbnum += 1
		with psycopg2.connect(host=sockdir, database='postgres',user=getpass.getuser()) as conn:
			conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
			cur = conn.cursor()
			#Don't use the built in escaping here. It makes no sense
			#because it quotes the database name
			cur.execute('CREATE DATABASE %s;' % self.dbname)
			dbnum += 1
			cur.close()
			
		
		self.connpool = eventlet.db_pool.ConnectionPool(psycopg2,host=sockdir, database=self.dbname,user=getpass.getuser())
		with self.getConnectionPool().item() as conn:
			loadSqlFromFile(conn,'fairywren.sql')
			loadSqlFromFile(conn,'permissions.sql')	
		
	def __del__(self):

		self.getConnectionPool().clear()
		self.connpool = None
		

	
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

		
