import eventlet
import logging
import psycopg2
import psycopg2.extras

class Swarm(object):
	def __init__(self):
		self.connPool = None
		self.queue = eventlet.queue.LightQueue()
		self.log = logging.getLogger('fairywren.Swarm')
		psycopg2.extras.register_inet()
		
		self.log.info('Created')
		
	def setConnectionPool(self,pool):
		self.connPool = pool		
		
	def __call__(self):
		self.log.info('Started')
		while True:
			args = self.queue.get()
			self.recordPeer(*args)
		
	def pushPeer(self,*args):
		self.queue.put(args)
	
	def getPeers(self):
		result = {}
		with self.connPool.item() as conn:
			with conn.cursor() as cur:
				cur.execute("Select users.name,peers.peerId,peers.ip,peers.port,peers.firstseen,peers.lastseen from peers left join users on peers.userId = users.id");
				
				for row in cur:
					username,peerId,ip,port,firstSeen,lastSeen = row
					if username not in result:
						result[username] = []
					result[username].append({
						'peerId': str(peerId),
						'ip': str(ip),
						'port': port,
						'firstSeen':firstSeen,
						'lastSeen':lastSeen
					})
					
			conn.rollback()
		return result
		
	def recordPeer(self,userId,infoHash,peerIp,port,peerId):
		peerIp = psycopg2.extras.Inet(peerIp)
		peerId = psycopg2.Binary(peerId)
		with self.connPool.item() as conn:
			with conn.cursor() as cur:
					try:
						cur.execute("Update peers set peerId = %s , lastSeen = timezone('UTC',CURRENT_TIMESTAMP) where userid = %s and port = %s and ip = %s returning userid",
						(peerId,userId,port,peerIp,))
					except psycopg2.DatabaseError as e:
						self.log.exception('Error updating peer',exc_info=True)
						conn.rollback()
						raise e
					
					r = cur.fetchone()
					
					if r == None:
						try:
							cur.execute("Insert into peers (userId,ip,port,peerId,lastSeen,firstSeen) VALUES(%s,%s,%s,%s,timezone('UTC',CURRENT_TIMESTAMP),timezone('UTC',CURRENT_TIMESTAMP))",
							(userId,peerIp,port,peerId));
						except psycopg2.IntegrityError as e:
							conn.rollback()
							#This string is specified in the postgre documentation appendix
							# 'PostgreSQL Error Codes' as 'unique_violation' and corresponds
							#to primary key violations. This occurs here because conceivably
							#the record was created after the update and before this insert 
							#and can be ignored
							if e.pgcode == '23505':
								return
							# 'foreign_key_violation' - violation of 'creator' foreign key
							# i.e. user with uid doesn't exist. This should never happen
							elif e.pgcode == '23503':
								self.log.exception('Tried to insert peer with non existent user id %x',userId,exc_info=True)
								raise e
							else:
								raise e
						except psycopg2.DatabaseError as e:
							self.log.exception('Error inserting peer',exc_info=True)
							conn.rollback()
							raise e
					conn.commit()
					self.log.debug('Updated peer for user id %x',userId)
						
						
