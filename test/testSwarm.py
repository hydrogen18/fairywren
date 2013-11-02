import testUsers
import swarm
import unittest
import psycopg2

class TestSwarm(testUsers.TestWithValidUser):
	def setUp(self):
		super(TestSwarm,self).setUp()
		
		self.swarm = swarm.Swarm()
		self.swarm.setConnectionPool(self.getConnectionPool())
		
class TestAddOne(TestSwarm):
	def test_it(self):
		self.swarm.recordPeer(self.validuid,'0'*20,'1.2.3.4',42000,'a'*20)
		
class TestAddMany(TestSwarm):
	def test_it(self):
		for i in range(0,128):
			self.swarm.recordPeer(self.validuid,'0'*20,'1.2.3.%i' % i,42000,'a'*20)		
		
class TestUpdate(TestSwarm):
	def test_it(self):
		self.swarm.recordPeer(self.validuid,'0'*20,'1.2.3.4',42000,'a'*20)
		self.swarm.recordPeer(self.validuid,'0'*20,'1.2.3.4',42000,'a'*20)
		
class TestBadUid(TestSwarm):
	def test_it(self):
		with self.assertRaises(psycopg2.IntegrityError) as cm:
			self.swarm.recordPeer(self.validuid+1,'0'*20,'1.2.3.4',42000,'a'*20)

if __name__ == '__main__':
	unittest.main()
