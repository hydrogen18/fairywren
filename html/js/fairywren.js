Fairywren = {};

Fairywren.MIN_PASSWORD_LENGTH = 12;
Fairywren.MIN_USERNAME_LENGTH = 4;

Fairywren.trimIsoFormatDate = function(dateStr)
{
	return dateStr.substr(0,19);
}

Fairywren.bytesToPrettyPrint = function(lengthInBytes)
{
	var adjustedLength = lengthInBytes;
	var adjustedUnits = 'bytes';
	
	var ADJUSTMENTS = ['kilobytes','megabytes','gigabytes'];
	var SCALE = 1024;
	for(var i = 0;i < ADJUSTMENTS.length; ++i)
	{
		if(SCALE > adjustedLength )
		{
			break;
		}
		var adjustment = Math.pow(SCALE,i+1);
		adjustedLength = lengthInBytes / adjustment;
		adjustedUnits = ADJUSTMENTS[i];
	}
	
	var displayLengthFixed = parseInt(adjustedLength) !== adjustedLength;
	if(displayLengthFixed)
	{
		adjustedLength = adjustedLength.toFixed(2);
	}
	return adjustedLength + ' ' + adjustedUnits;
}

Fairywren.makeNavbar = function()
{
	var navbar = $("<div />");
	navbar.addClass('navbar');
	
	var navbarInner = $("<div />");
	navbarInner.addClass('navbar-inner');
	
	navbar.append(navbarInner);
	
	var nav = $("<ul />");
	nav.addClass('nav');
	
	navbarInner.append(nav);
	
	var makeNavItem = function(name,href)
	{
		if(href === null || href === undefined)
		{
			href = '#';
		}
		
		var li =$("<li />")
		li.append($("<a />").attr('href',href).text(name));
		
		
		if(href != '#' && window.location.href.indexOf(href) != -1)
		{
			li.addClass('active');
		}
		
		return li;
	};
	
	
	nav.append(makeNavItem('Newest','torrents.html'));
	nav.append(makeNavItem('Search','search.html'));
	nav.append(makeNavItem('Upload','upload.html'));
	nav.append(makeNavItem('Account','account.html'));
	
	return navbar;
}

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

Fairywren.makeSuccessElement = function(msg)
{
	var r = $("<div />");
	r.addClass('alert');
	
	r.addClass('alert-success');
	
	r.append($("<button />").attr('type','button').addClass('close').attr('data-dismiss','alert').text('\u2A2F'));
	
	r.append(msg);
	
	r.alert();
	
	return r;
}

Fairywren.makeErrorElement = function(msg,fatal)
{
	var r = $("<div />");
	r.addClass('alert');
	
	if(fatal === true)
	{
		r.addClass('alert-error');
	}
	
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
				errorHolder.prepend(Fairywren.makeErrorElement("Server error",true));
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
			errorHolder.prepend(Fairywren.makeErrorElement('Request to server timed out',true));
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
	if(password.length < Fairywren.MIN_PASSWORD_LENGTH)
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
