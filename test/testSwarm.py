import testUsers
import swarm
import unittest
import psycopg2
import time

class TestSwarm(testUsers.TestWithValidUser):
	def setUp(self):
		super(TestSwarm,self).setUp()
		
		self.swarm = swarm.Swarm()
		self.swarm.setConnectionPool(self.getConnectionPool())
		
class TestAddOne(TestSwarm):
	def test_it(self):
		self.swarm.recordPeer(self.validuid,'0'*20,'1.2.3.4',42000,'a'*20)
		r = self.swarm.getPeers()
		self.assertIn(self.validusername,r)
		
class TestAddMany(TestSwarm):
	def test_it(self):
		for lastOctet in range(1,128):
			self.swarm.recordPeer(self.validuid,'0'*20,'1.2.3.%i' % lastOctet,42000,'a'*20)		
			r = self.swarm.getPeers()
			self.assertIn(self.validusername,r)
			self.assertEqual(lastOctet,len(r[self.validusername]))
			
class TestAddManyDifferentPort(TestSwarm):
	def test_it(self):
		for lastOctet in range(1,128):
			self.swarm.recordPeer(self.validuid,'0'*20,'1.2.3.5',4000 + lastOctet,'a'*20)		
			r = self.swarm.getPeers()
			self.assertIn(self.validusername,r)
			self.assertEqual(lastOctet,len(r[self.validusername]))	
		
class TestUpdate(TestSwarm):
	def test_it(self):
		ip = '1.2.3.4'
		port = 42000
		self.swarm.recordPeer(self.validuid,'0'*20,ip,port,'a'*20)
		r = self.swarm.getPeers()
		self.assertIn(self.validusername,r)
		self.assertEqual(1,len(r[self.validusername]))
		self.assertEqual(1,len(r))
		self.assertEqual(r[self.validusername][0]['peerId'],'a'*20)
		self.assertEqual(r[self.validusername][0]['ip'],ip)
		self.assertEqual(r[self.validusername][0]['port'],port)
		
		
		time.sleep(1)
		self.swarm.recordPeer(self.validuid,'0'*20,ip,port,'b'*20)
		r = self.swarm.getPeers()
		self.assertIn(self.validusername,r)
		self.assertEqual(1,len(r[self.validusername]))
		self.assertEqual(1,len(r))
		self.assertEqual(r[self.validusername][0]['peerId'],'b'*20)
		self.assertGreater(r[self.validusername][0]['lastSeen'],r[self.validusername][0]['firstSeen'])
		self.assertEqual(r[self.validusername][0]['ip'],ip)
		self.assertEqual(r[self.validusername][0]['port'],port)
		
		
class TestBadUid(TestSwarm):
	def test_it(self):
		with self.assertRaises(psycopg2.IntegrityError) as cm:
			self.swarm.recordPeer(self.validuid+1,'0'*20,'1.2.3.4',42000,'a'*20)

if __name__ == '__main__':
	unittest.main()
