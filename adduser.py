import psycopg2
import sys
import json
import hashlib
import base64

if __name__ == "__main__":
	with open(sys.argv[1],'r') as fin:
		conf = json.load(fin)
		

	conn = psycopg2.connect(**conf['webapi']['postgresql'])
	
	cur = conn.cursor()
	
	sys.stdout.write('Username:')
	username = raw_input()
	
	sys.stdout.write('Password:')
	password = raw_input()
	
	pwHash = hashlib.sha512()
	pwHash.update(password)
	
	storedHash = hashlib.sha512()
	storedHash.update(conf['salt'])
	storedHash.update(pwHash.digest())
	
	secretKey = hashlib.sha512()
	with open('/dev/urandom') as randomIn:
		randomValue = randomIn.read(1024)
		secretKey.update(randomValue)
	
	cur.execute("INSERT into users (name,password,secretKey) VALUES(%s,%s,%s);",
	(username,
	base64.urlsafe_b64encode(storedHash.digest()).replace('=',''),
	base64.urlsafe_b64encode(secretKey.digest()).replace('=',''),) ) 
	conn.commit()
	cur.close()
	conn.close()
