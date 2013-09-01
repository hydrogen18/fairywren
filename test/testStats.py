import unittest
import stats
import fairywrenMocks

class TestStats(unittest.TestCase):
	
	def setUp(self):
		self.pub = stats.TrackerStatsPublisher(None)
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

if __name__ == '__main__':
    unittest.main()
