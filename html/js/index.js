

function login()
{
	var username = $("#username").val();
	var password = $("#password").val();
	
	var pwSha = new jsSHA(password,"TEXT");
	var pwHash = pwSha.getHash("SHA-512","B64").replace(/=/g,"");
	
	$.ajax("api/session", {"type":"POST"})
	
	return false;
}
