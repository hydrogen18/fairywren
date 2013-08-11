import eventlet
import fairywren
import hashlib
import psycopg2
import logging
import os
import base64

class Users(object):

	def __init__(self,salt):
		self.salt = salt
		self.connPool = None
		self.log = logging.getLogger('fairywren.users')
		self.log.info('Created')
		
	def setConnectionPool(self,pool):
		self.connPool = pool

	def _saltPwhash(self,pwHash):
		storedHash = hashlib.sha512()
		storedHash.update(self.salt)
		storedHash.update(pwHash)
		return base64.urlsafe_b64encode(storedHash.digest()).replace('=','')

	def addUser(self,username,pwHash):
		self.log.debug('Trying to add user %s',username)
		secretKey = hashlib.sha512()
		
		randomValue = os.urandom(1024)
		secretKey.update(randomValue)
		
		saltedPw = self._saltPwhash(pwHash)

		with self.connPool.item() as conn:
			cur = conn.cursor()
			
			try:
				cur.execute("INSERT into users (name,password,secretKey) VALUES(%s,%s,%s) returning users.id;",
					(username,
					saltedPw,
					base64.urlsafe_b64encode(secretKey.digest()).replace('=',''),) ) 
			except IntegrityError as e:
				self.log.error(e)
				conn.rollback()
				cur.close()
				return None
				
			conn.commit()
			
			newId, = cur.fetchone()
			cur.close()
			conn.close()
			self.log.debug('Added user, new id %.8x', newId)
			return 'api/users/%.8x'  % newId
			
		
	def createInvite(self,creatorId):
		h = hashlib.md5()
		h.update(os.urandom(1024))
		h.update(str(creatorId))
		
		secret = h.digest()
		h.update(h.digest())
		h.update(os.urandom(1024))
		secret += h.digest()
		
		with self.connPool.item() as conn:
			cur = conn.cursor()
			
			try:
				cur.execute("INSERT into invites (secret,inviter,creationdate) VALUES(%s,%s,timezone('UTC',CURRENT_TIMESTAMP));" , (base64.urlsafe_b64encode(secret).replace('=',''),creatorId,))
			except psycopg2.IntegrityError as e:
				conn.rollback()
				# 'foreign_key_violation' - violation of 'inviter' foreign key
				# i.e. user with uid doesn't exist
				if e.pgcode == '23503':
					raise ValueError('User does not exist with that uid')
				self.log.exception('Failed creating invite',exc_info=True)
				raise e
			except psycopg2.DatabaseError as e:
				conn.rollback()
				self.log.exception('Failed creating invite',exc_info=True)
				raise e
			conn.commit()
			cur.close()
		return secret
		
	def getInfo(self,idNumber):
		with self.connPool.item() as conn:
			cur = conn.cursor()
			try:
				cur.execute("Select users.name,count(torrents.creator) from users left join torrents on (torrents.creator=users.id) where users.id=%s group by users.name;",(idNumber,))
				result = cur.fetchone()
			except psycopg2.DatabaseError as e:
				self.log.exception('Failed getting info for user',exc_info=True)
				raise e
			finally:
				cur.close()
				conn.rollback()
				
			retval = {}
			if result == None:			
				return None
			else:
				name,numberOfTorrents = result
				retval =  {'numberOfTorrents' : numberOfTorrents, 'name':name, 'password' : {'href' : fairywren.USER_PASSWORD_FMT % idNumber }}
			
			return retval
			


