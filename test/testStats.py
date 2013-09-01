import unittest
import stats
import fairywrenMocks

class TestStats(unittest.TestCase):
	
	def setUp(self):
		self.tracker = fairywrenMocks.Tracker()
		self.pub = stats.TrackerStatsPublisher(self.tracker)
		self.sub = stats.TrackerStatsSubscriber()
		
	
class TestEmpty(TestStats):
	def test_it(self):
		seeds,leeches = self.sub.getCount('0'*20)
		self.assertEqual(seeds,0)
		self.assertEqual(leeches,0)
		
		
class TestMessages(TestStats):
	def test_it(self):
		info_hash = '0'*20
		
		self.tracker._getScrape = { "files" : { info_hash : { "complete" : 1, "incomplete" : 1 } } }
		
		msg = self.pub.produceMessage(info_hash)
		self.sub.consumeMessage(msg)
		
		seeds,leeches = self.sub.getCount(info_hash)
		
		self.assertEqual(seeds,1)
		self.assertEqual(leeches,1)

if __name__ == '__main__':
    unittest.main()
