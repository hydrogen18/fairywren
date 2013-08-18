import vanilla
import psycopg2
import sys
import json
import hashlib
import base64
import users
import getpass

if __name__ == "__main__":
	with open(sys.argv[1],'r') as fin:
		conf = json.load(fin)

	connPool = vanilla.buildConnectionPool(psycopg2,**conf['webapi']['postgresql'])
	u = users.Users(conf['salt'])
	u.setConnectionPool(connPool)
	
	sys.stdout.write('Username:')
	username = raw_input()
	
	password = getpass.getpass('Password:')
	
	h = hashlib.sha512()
	h.update(password)
	
	u.addUser(username,h.digest())
	
	with connPool.item() as conn:
		cur = conn.cursor()
	
	sys.exit(0)
