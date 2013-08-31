import sys
import json
import gdbm
import torrents
import psycopg2

if __name__ == '__main__':
	with open(sys.argv[1],'r') as fin:
		conf = json.load(fin)

		
	conn = psycopg2.connect(**conf['webapi']['postgresql'])
	olddb = gdbm.open(conf['webapi']['torrentPath'],'r')
	
	curkey = olddb.firstkey()
	cur = conn.cursor()
	try:
		while curkey!= None:
			torrentId = int(curkey[0:8],16)
			insertColumn = 'metainfo'
			if 'ext' in curkey:
				insertColumn = 'extendedInfo'
				
			cur.execute("update torrents set(" + insertColumn + ") = (%s) where id=%s",(psycopg2.Binary(olddb[curkey]),torrentId,))
			
			curkey = olddb.nextkey(curkey)
	except Exception as e:
		print e
		cur.close()
		conn.rollback()
		sys.exit(1)
		
	cur.close()
	conn.commit()
	sys.exit(0)
		
