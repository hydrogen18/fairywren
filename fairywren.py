import sys
MSG_SCRAPE = 'x01'
IPC_PATH = 'ipc:///tmp/fairywrenStats'

API_PATH = 'api'

TORRENTS_PATH = '%s/torrents' % API_PATH
TORRENT_FMT = TORRENTS_PATH + '/%.8x.torrent'
TORRENT_INFO_FMT = TORRENTS_PATH + '/%.8x.json'

USERS_PATH = '%s/users' % API_PATH
USER_FMT = USERS_PATH + '/%.8x' 
USER_PASSWORD_FMT = USER_FMT + '/password'

def import_psycopg2():
	RUNNING_ON_PYPY = hasattr(sys, "pypy_translation_info")
	
	if RUNNING_ON_PYPY:
		import psycopg2cffi as psycopg2
	else:
		import psycopg2
		
	return psycopg2


