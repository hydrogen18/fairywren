Fairywren = {}

Fairywren.MIN_PASSWORD_LENGTH = 12;


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
