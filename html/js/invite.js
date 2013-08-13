$(document).ready(function(){
	var hash = window.location.hash;
	
	var registerButton = $("input#register");
	
	Fairywren.register.err = $("#message");
	
	if(hash.length === 0)
	{
		//User got here on accident or something. Display error message
		//and depart
		Fairywren.register.err.text("You seem to have reached this page in error");
		return;
	}
	
	Fairywren.register.href = hash.slice(1);

	//Retrieve the invite, check to see if it is valid
	jQuery.get(Fairywren.register.href).
	done(
		function(data)
		{
			//Check to see if it has been claimed
			if(data.claimed)
			{
				Fairywren.register.err.text("This invite has already been claimed.");
				return;
			}
			
			registerButton.removeAttr('disabled');
			
		}
		).fail(function(jqXhr,textStatus,errorThrown)
		{
			Fairywren.serverErrorHandler(jqXhr,textStatus,errorThrown,Fairywren.register.err);
			
		});

	});
	
Fairywren.register = function()
{
	var errDisplay = $("#message");
	errDisplay.text('');
	var username = $("input#username");
	
	var validUsername = Fairywren.validateUsername(username.val());
	
	if(validUsername !== null)
	{
		errDisplay.text(validUsername);
		return;
	}
	
	var password0 = $("input#password0");
	var password1 = $("input#password1");
	

	var validPassword = Fairywren.validatePassword(password0.val());
	if( validPassword !== null)
	{
		errDisplay.text(validPassword);
		return;
	}
	
	if(password0.val() !== password1.val())
	{
		errDisplay.text("Password does not match");
		return;
	}
	username = username.val();
	password = Fairywren.hashPassword(password0.val());
	
	jQuery.post(Fairywren.register.href,{username:username,password:password}).
	done(
		function(data)
		{
			window.location = 'index.html';
		}
		).fail(function(jqXhr,textStatus,errorThrown)
		{
			Fairywren.serverErrorHandler(jqXhr,textStatus,errorThrown,Fairywren.register.err);
			
		});

}


