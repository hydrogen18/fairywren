import unittest
import stats
import fairywrenMocks

class TestStats(unittest.TestCase):
	
	def setUp(self):
		self.pub = stats.TrackerStatsPublisher(None,None)
		self.sub = stats.TrackerStatsSubscriber()
		
class TestEmpty(TestStats):
	def test_it(self):
		seeds,leeches = self.sub.getCount(1)
		self.assertEqual(seeds,0)
		self.assertEqual(leeches,0)
		
class TestMessages(TestStats):
	def test_it(self):
		tid = 1
		numSeeds = 5
		numLeeches = 6
		
		msg = self.pub.produceMessage((tid,numSeeds,numLeeches))
		self.sub.consumeMessage(msg)
		
		seeds,leeches = self.sub.getCount(tid)
		
		self.assertEqual(seeds,numSeeds)
		self.assertEqual(leeches,numLeeches)
		
		
	def test_peerCountDecrement(self):
		userId = 1
		ip = 0x10200304
		port = 2
		
		
		msg = self.pub.producePeerCountMessage((True,userId,ip,port+1))
		self.sub.consumePeerCountMessage(msg)
		
		for i in xrange(1,100):
			msg = self.pub.producePeerCountMessage((False,userId,ip,port))
			
			self.sub.consumePeerCountMessage(msg)
			
			counts = self.sub.getUserCounts()
			
			self.assertEqual(1,len(counts))
			
			self.assertIn(userId,counts)
			
			self.assertNotIn((ip,port,),counts[userId])
			
			self.assertEqual(1,counts[userId][(ip,port+1,)])
			
		msg = self.pub.producePeerCountMessage((False,userId,ip,port+1))
		self.sub.consumePeerCountMessage(msg)
		
		counts = self.sub.getUserCounts()
		
		self.assertEqual(0,len(counts))
		
		self.assertNotIn(userId,counts)
		
	def test_peerCountIncrement(self):
		
		userId = 1
		ip = 0x10200304
		port = 2
		
		for i in xrange(1,100):
			msg = self.pub.producePeerCountMessage((True,userId,ip,port))
			
			self.sub.consumePeerCountMessage(msg)
			
			counts = self.sub.getUserCounts()
			
			self.assertEqual(1,len(counts))
			
			self.assertEqual(1,len(counts[userId]))
			
			self.assertEqual(i,counts[userId][(ip,port)])

if __name__ == '__main__':
    unittest.main()
