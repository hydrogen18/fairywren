import eventlet


class Users(object):

	def setConnectionPool(self,pool):
		self.connPool = pool
		
	def getInfo(self,idNumber):
		with self.connPool.item() as conn:
			cur = conn.cursor()
		
			cur.execute("Select users.name,count(torrents.creator) from users left join torrents on (torrents.creator=users.id) where users.id=%s group by users.name;",(idNumber,))
			result = cur.fetchone()
			conn.rollback()
			cur.close()
			
			retval = {}
			if result == None:			
				return None
			else:
				name,numberOfTorrents = result
				retval =  {'numberOfTorrents' : numberOfTorrents, 'name':name, 'password' : {'href' : fairywren.USER_PASSWORD_FMT % idNumber }}
			
			return retval
			


