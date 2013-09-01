import eventlet
import eventlet.db_pool
import base64
import hashlib
import os
from psycopg2 import IntegrityError
import logging



class Auth(object):
	def __init__(self,salt):
		self.salt = salt
		self.log = logging.getLogger('fairywren.auth')
		self.log.info('Created')
		
	def setConnectionPool(self,pool):
		self.connPool = pool

	def isUserMemberOfRole(self,userId,roles):
		with self.connPool.item() as conn:
			cur = conn.cursor()
			
			cur.execute("SELECT roles.name from rolemember left join roles on roles.id=rolemember.roleid where userid=%s;",(userId,));
			
			retVal = False
			for role, in iter(cur.fetchone,None):
				if role in roles:
					retVal = True
			
			conn.rollback()
			cur.close()
			
			return retVal
	def changePassword(self,userId,pwHash):
		saltedPw = self._saltPwhash(pwHash)
		with self.connPool.item() as conn:
			cur = conn.cursor()
			try: 
				cur.execute("UPDATE users SET password=%s where id=%s;",
				(saltedPw,userId,))
			except StandardError  as e :
				self.log.error(e)
				return None
			finally:
				conn.commit()
				cur.close()
				
		return True


		
	def authenticateSecretKey(self,key):
		with self.connPool.item() as conn:
			cur = conn.cursor()
		
			cur.execute("Select 1 from users where secretKey=%s and password is not null;",
			(base64.urlsafe_b64encode(key).replace('=','') ,))
		
			allowed = cur.fetchone() != None
		
			cur.close()
			conn.rollback()
			
			return allowed
		
	def authorizeInfoHash(self,info_hash):
		with self.connPool.item() as conn:
			cur = conn.cursor()
			cur.execute("Select id from torrents where infoHash=%(infoHash)s",
			{'infoHash' : base64.urlsafe_b64encode(info_hash).replace('=','') })
			
			result = cur.fetchone()
			cur.close()
			conn.rollback()
		
			if result!= None:
				result, = result
		
			return result

	def authenticateUser(self,username,password):
		passwordHash = hashlib.sha512()
		passwordHash.update(self.salt)
		passwordHash.update(password)
		
		passwordHash = base64.urlsafe_b64encode(passwordHash.digest()).replace('=','')
		with self.connPool.item() as conn:
			cur = conn.cursor()
			cur.execute("Select id from users where name=%s and password=%s ;",
			(username,passwordHash))
			
			allowed = cur.fetchone() 
			cur.close()
			conn.rollback()
			
			if allowed == None:
				return None
			userId, = allowed
			return userId
			
			
			
			
		
