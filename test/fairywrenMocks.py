

class Tracker(object):
	def __init__(self):
		self._getQueue = None
		self._getScrape = {"files" : {} }
		
	def getQueue(self):
		return self._getQueue

	def getScrape(self,info_hashes):
		return self._getScrape
		
class Peers(object):
	def __init__(self):
		self._getNumberOfPeers = (0,0)
		
	def getNumberOfPeers(self,info_hash):
		return self._getNumberOfPeers
		
