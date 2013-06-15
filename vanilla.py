
import eventlet

def http_error(num,env,start_response,msg=None):
	if num < 400 or num > 599:
		raise ValueError("HTTP Error code out of range:" + str(num))
	
	start_response(str(num),[('Content-Type','text/html')])
	
	errmsg = 'Error - ' +str(num)
	response = '<html><head><title>'
	response += errmsg
	response += '</title></head>'
	response += '<body><h4>' 
	response += errmsg
	response += '</h4><hr><p>'
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
	
	prohibited = '<>\"/:|?*!@#$%^&()[]{}.,'
	
	for c in prohibited:
		result = result.replace(c,'')
	
	return result
	
