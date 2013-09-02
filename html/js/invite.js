$(document).ready(function(){
	var hash = window.location.hash;
	
	var registerButton = $("input#register");
	
	Fairywren.register.alert = $("#register").find("#alert");
	
	if(hash.length === 0)
	{
		//User got here on accident or something. Display error message
		//and depart
		Fairywren.register.alert.append(Fairywren.makeErrorElement("You seem to have reached this page in error",true));
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
				Fairywren.register.alert.append(Fairywren.makeErrorElement("This invite has already been claimed.",true));
				return;
			}
			registerButton.removeAttr('disabled');
		}
		).fail(Fairywren.handleServerFailure(Fairywren.register.alert) );

});
	
	
Fairywren.register = function()
{
	Fairywren.register.alert.find('div').remove();
	
	var username = $("input#username");
	
	var validUsername = Fairywren.validateUsername(username.val());
	
	if(validUsername !== null)
	{
		Fairywren.register.alert.append(Fairywren.makeErrorElement(validUsername));
		return;
	}
	
	var password0 = $("input#password0");
	var password1 = $("input#password1");
	
	var validPassword = Fairywren.validatePassword(password0.val());
	if( validPassword !== null)
	{
		Fairywren.register.alert.append(Fairywren.makeErrorElement(validPassword));
		return;
	}
	
	if(password0.val() !== password1.val())
	{
		Fairywren.register.alert.append(Fairywren.makeErrorElement("Passwords does not match",true));
		return;
	}
	username = username.val();
	password = Fairywren.hashPassword(password0.val());
	
	jQuery.post(Fairywren.register.href,{username:username,password:password}).
	done(
		function(data)
		{
			Fairywren.register.showSuccess();
		}
		).fail(Fairywren.handleServerFailure(Fairywren.register.alert) );
}


Fairywren.register.showSuccess = function()
{
	$("div#register").hide();
	$("div#success").show();
};
