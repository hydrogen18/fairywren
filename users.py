import eventlet


class Users(object):

	def setConnectionPool(self,pool):
		self.connPool = pool
		
	def getInfo(self,idNumber):
		with self.connPool.item() as conn:
			cur = conn.cursor()
		
			cur.execute("Select name from users where id=%s;",(idNumber,))
		
			result = cur.fetchone()
			retval = {}
			if result == None:
				return None
			else:
				name, = result
				retval =  {'id': idNumber, 'name':name}
				
			cur.execute("Select count(1) from torrents where creator=%s",
			(idNumber,))
						
			numberOfTorrents, = cur.fetchone()
			
			retval['numberOfTorrents'] = numberOfTorrents
			
			return retval
			


