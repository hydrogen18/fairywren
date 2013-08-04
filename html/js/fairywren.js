Fairywren = {};

Fairywren.MIN_PASSWORD_LENGTH = 12;

Fairywren.serverErrorHandler = function(jqXhr,textStatus,errorThrown,element)
{
	var data = jqXhr.responseText;
	
	if(textStatus === "error")
	{
		var statusCode = jqXhr.statusCode().status;
		if(statusCode > 499)
		{
			element.text("Server error");
		}
		
		else
		{
			data = jQuery.parseJSON(data);
			if ( 'msg' in data )
			{
				element.text(data.msg);
			}
		}
	}
	else if ( textStatus === "timeout" )
	{
		element.text("Requested timed out");
	}
	
}

Fairywren.errorHandler = function(data)
{
	if ( ! 'error' in data )
	{
		console.log("Error handler called with object without 'error' attr");
		return;
	}
	
	if ( ! data.authenticated )
	{
		window.location = 'index.html';
		return;
	}
	
	if  ( ! data.authorized ) 
	{
		alert('You are not authorized to perform this function');
	}
}


Fairywren.hashPassword = function(password)
{
	var pwSha = new jsSHA(password,"TEXT");
	var pwHash = pwSha.getHash("SHA-512","B64").replace(/=/g,"");
	
	return pwHash;
}

Fairywren.validatePassword = function(password)
{
	if(password < Fairywren.MIN_PASSWORD_LENGTH)
	{
		return "Password too short, must be at least " + Fairywren.MIN_PASSWORD_LENGTH + " characters";
	}
	
	return null;
}

Fairywren.validateUsername = function(username)
{
	var ACCEPTED = 'abcdefghijklmnopqrstuvwxyz0123456789';
	
	var rejected = [];
	for(var i = 0 ; i < username.length;++i){
		if ( -1 === ACCEPTED.indexOf(username[i]))
		{
			rejected.push(username[i]);
		}
	}
	
	if(rejected.length !==0)
	{
		return 'The following characters are not allowed in usernames: ' + rejected.join('');
	}
	
	return null;
}
