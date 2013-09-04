import json
import eventlet
import eventlet.db_pool
import datetime

def sendJsonWsgiResponse(env,start_response,response,additionalHeaders=None):
	headers = [('Content-Type','text/json')]
	headers.append(('Cache-Control','no-store, no-cache, must-revalidate, max-age=0'))
	headers.append(('Pragma','no-cache'))
	
	if additionalHeaders:
		headers += additionalHeaders
	
	start_response('200 OK',headers)
	
	class DateTimeJSONEncoder(json.JSONEncoder):
		def default(self, obj):
			if isinstance(obj, datetime.datetime):
				return obj.isoformat()
			else:
				return super(DateTimeJSONEncoder, self).default(obj)
				
	return [DateTimeJSONEncoder().encode(response)]


def http_error(num,env,start_response,msg=None):
	if num < 400 or num > 599:
		raise ValueError("HTTP Error code out of range:" + str(num))
	
	start_response(str(num),[('Content-Type','text/html')])
	
	if env.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
		response = json.dumps({'msg': msg})
	else:
		errmsg = 'Error - ' +str(num)
		response = '<html><head><title>'
		response += errmsg
		response += '</title></head>'
		response += '<body><h4>' 
		response += errmsg
		response += '</h4><hr><p id="msg">'
		if msg:
			response += msg
		response += '</p></body></html>'
	
	return [response]
	
def getContentLength(env):
	if 'CONTENT_LENGTH' not in env:
		return None
		
	try:
		cl = int(env['CONTENT_LENGTH'])
	except ValueError:
		return None
		
	return cl

def buildConnectionPool(dbModule,**dbKwArgs):
	dbKwArgs['max_idle'] = 10
	dbKwArgs['max_age'] = 1200
	dbKwArgs['connect_timeout']=3
	dbKwArgs['max_size']=4

	return eventlet.db_pool.ConnectionPool(dbModule,**dbKwArgs)
	
def sanitizeForContentDispositionHeaderFilename(originalFileName):
	result = str(originalFileName).replace(' ','_')
	
	prohibited = '<>\"/:|?*!@#$%^&()[]{},'
	
	for c in prohibited:
		result = result.replace(c,'')
	
	return result
	
