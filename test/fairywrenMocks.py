

class Tracker(object):
	def __init__(self):
		self._getQueue = None
		self._getScrape = {"files" : {} }
		
	def getQueue(self):
		return self._getQueue

	def getScrape(self,info_hashes):
		return self._getScrape
