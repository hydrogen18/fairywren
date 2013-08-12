import base64
MSG_SCRAPE = 'x01'
IPC_PATH = 'ipc:///tmp/fairywrenStats'

API_PATH = 'api'

TORRENTS_PATH = '%s/torrents' % API_PATH
TORRENT_FMT = TORRENTS_PATH + '/%.8x.torrent'
TORRENT_INFO_FMT = TORRENTS_PATH + '/%.8x.json'

USERS_PATH = '%s/users' % API_PATH
USER_FMT = USERS_PATH + '/%.8x' 
USER_PASSWORD_FMT = USER_FMT + '/password'

USER_INVITES_FMT = USER_FMT + '/invites'

INVITES_PATH = '%s/invites' % API_PATH
def _secretToPath(self,secret):
	if len(secret)!=32:
		raise ValueError('secret must be exactly 32 characters')
		
	return '%s/%s' % (INVITES_PATH, base64.urlsafe_b64encode(secret).replace('=',''))
	
INVITE_FMT = type("",(),{'__mod__' : _secretToPath})()

UID_RE = '(?P<uid>[abcdefABCDEF0123456789]{8})'
SECRET_RE = '(?P<secret>[A-Z,a-z,0-9,_,-]{43})'


