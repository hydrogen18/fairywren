import bencode

import sys

import hashlib

with open(sys.argv[1],'r') as fin:
	torrent = bencode.bdecode(fin.read())

info_hash = hashlib.sha1()

info_hash.update(bencode.bencode(torrent['info']))

print info_hash.hexdigest()





