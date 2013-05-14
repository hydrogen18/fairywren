import eventlet
import eventlet.db_pool
import base64
import hashlib

class Auth(object):
	def __init__(self,salt):
		self.salt = salt
		
	def setConnectionPool(self,pool):
		self.connPool = pool
		
	def authenticateSecretKey(self,key):
		with self.connPool.item() as conn:
			cur = conn.cursor()
		
			cur.execute("Select 1 from users where secretKey=%s and password is not null;",
			(base64.urlsafe_b64encode(key).replace('=','') ,))
		
			allowed = cur.fetchone() != None
			cur.close()
			
			return allowed
		
	def authorizeInfoHash(self,info_hash):
		with self.connPool.item() as conn:
			cur = conn.cursor()
			cur.execute("Select 1 from torrents where infoHash=%(infoHash)s",
			{'infoHash' : base64.urlsafe_b64encode(info_hash).replace('=','') })
			
			allowed = cur.fetchone() != None
			cur.close()
		
			return allowed

	def authenticateUser(self,username,password):
		passwordHash = hashlib.sha512()
		passwordHash.update(self.salt)
		passwordHash.update(password)
		
		passwordHash = base64.urlsafe_b64encode(passwordHash.digest()).replace('=','')
		with self.connPool.item() as conn:
			cur = conn.cursor()
			cur.execute("Select 1 from users where name=%s and password=%s ;",
			(username,passwordHash))
			
			allowed = cur.fetchone() != None
			cur.close()
			
			return allowed
			
			
		
