

def http_error(num,env,start_response,msg=None):
	if num < 400 or num > 499:
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
	
	
