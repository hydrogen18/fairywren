$(document).ready(function(){
	var hash = window.location.hash;
	
	var registerButton = $("input#register");
	
	if(hash.length === 0)
	{
		//User got here on accident or something. Display error message
		//and depart
	}
	
	var inviteHref = hash.slice(1);
	
	//Retrieve the invite, check to see if it is valid
	jQuery.get(inviteHref).
	done(
		function(data)
		{
			//Check to see if it has been claimed
			
			
		}
		).fail(function(jqXhr,textStatus,errorThrown)
		{
			Fairywren.serverErrorHandler(jqXhr,textStatus,errorThrown,$("#message"));
			
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

}


