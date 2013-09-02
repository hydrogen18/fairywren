Fairywren = {};

Fairywren.MIN_PASSWORD_LENGTH = 12;
Fairywren.MIN_USERNAME_LENGTH = 4;

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
				if(data.msg === undefined || data.msg === null)
				{
					element.text(statusCode);
				}
				else
				{
					element.text(data.msg);
				}
			}
		}
	}
	else if ( textStatus === "timeout" )
	{
		element.text("Requested timed out");
	}
	
}

Fairywren.makeErrorElement = function(msg)
{
	var r = $("<div />");
	r.addClass('alert');
	
	r.append($("<button />").attr('type','button').addClass('close').attr('data-dismiss','alert').text('\u2A2F'));
	
	r.append(msg);
	
	r.alert();
	
	return r;
}

Fairywren.handleServerFailure = function(errorHolder)
{
	var f = function(jqXhr,textStatus,errorThrown)
	{
		var data = jqXhr.responseText;
		
		if(textStatus === "error")
		{
			var statusCode = jqXhr.statusCode().status;
			if(statusCode > 499)
			{
				errorHolder.prepend(Fairywren.makeErrorElement("Server error"));
			}
			
			else
			{
				data = jQuery.parseJSON(data);
				if ( 'msg' in data )
				{
					if(data.msg === undefined || data.msg === null)
					{
						errorHolder.prepend(Fairywren.makeErrorElement(statusCode));
					}
					else
					{
						errorHolder.prepend(Fairywren.makeErrorElement(data.msg));
					}
				}
			}
		}
		else if ( textStatus === "timeout" )
		{
			errorHolder.prepend(Fairywren.makeErrorElement('Request to server timed out'));
		}
	}
	
	return f;
}
	

Fairywren.isError = function(data,errorHolder)
{
	if ( ! ('error' in data))
	{
		return false;
	}
	
	if ( false === data.authenticated )
	{
		window.location = 'index.html';
		return true;
	}
	
	if ( false === data.authorized )
	{
		if(errorHolder !== undefined && errorHolder !== null )
		{
			errorHolder.prepend(Fairywren.makeErrorElement("Not authorized"));
		}
		else
		{
			alert('You are not authorized to perform this function');
		}
		return true;
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
			if(rejected.indexOf(username[i])===-1)
			{
				rejected.push(username[i]);
			}
		}
	}
	
	if(rejected.length !==0)
	{
		return 'The following characters are not allowed in usernames: "' + rejected.join('') + '"';
	}
	
	if(username.length < Fairywren.MIN_USERNAME_LENGTH)
	{
		return 'Username too short';
	}
	
	return null;
}
