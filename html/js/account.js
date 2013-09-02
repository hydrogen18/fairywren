

$(document).ready(function(){
	$("body").prepend(Fairywren.makeNavbar());

	Fairywren.changePassword.alert = $("#changePassword").find("#alert");

	jQuery.get("api/session").
	done(
		function(data)
		{
			if(! Fairywren.isError(data))
			{				 
				jQuery.get(data.my.href).
				done(
					function(data)
					{
						if( ! Fairywren.isError(data) )
						{
							Fairywren.account = data;
							Fairywren.showStatistics();
							Fairywren.showInvites();
						}
					}
				).fail(Fairywren.handleServerFailure($("#account")));
			}
		}
		).fail(Fairywren.handleServerFailure($("#account")));
	

});

Fairywren.account = {};

Fairywren.showStatistics = function(){

	var list = $("#stats");
	
	data = Fairywren.account;
	list.empty();
	list.append($("<dt/>").text("Username"));
	list.append($("<dd/>").text(data.name));
	
	list.append($("<dt/>").text("Number of torrents uploaded"));
	list.append($("<dd/>").text(data.numberOfTorrents));

}
Fairywren.showInvites = function(){
	var invitesDiv = $("div#invites");
	
	var msg = invitesDiv.find(".message");
	
	var invitesTable = invitesDiv.find("table");
	invitesTable.find("tr:gt(0)").remove();
	
	jQuery.get(Fairywren.account.invites.href).done(function(data)
		{
			var invites = data.invites;
			invitesDiv.find('#numInvites').text(data.invites.length);
			for(var i = 0; i < data.invites.length;++i)
			{
				var invite = invites[i];
				var row = $("<tr />");
				var created = Fairywren.trimIsoFormatDate(invite.created);
				var link = invite.href;
				row.append($("<td>" + created + "</td>"));
				var anchor = $("<a />");
				anchor.attr('href','invite.html#' + link);
				anchor.text(anchor.prop('href'));
				row.append($('<td />').append(anchor));
				
				invitesTable.find('tr:last').after(row);
			}
		}
	).fail(function(jqXhr,textStatus,errorThrown)
		{
			Fairywren.serverErrorHandler(jqXhr,textStatus,errorThrown,msg);
		});
}

Fairywren.createInvite = function()
{
	var msg = $("div#invites").find(".message");
	jQuery.post('api/invites').done(function(data){
		if("error" in data)
		{
			Fairywren.errorHandler(data);
			return;
		}
		Fairywren.showInvites();
	}).fail(function(jqXhr,textStatus,errorThrown)
		{
			Fairywren.serverErrorHandler(jqXhr,textStatus,errorThrown,msg);
		});
}


Fairywren.changePassword = function()
{
	var passwords = $("#changePassword").find("input");
	var password0 = $(passwords[0]);
	var password1 = $(passwords[1]);

	Fairywren.changePassword.alert.find('div').remove();
	
	var validPassword = Fairywren.validatePassword(password0.val());
	if( validPassword !== null)
	{
		Fairywren.changePassword.alert.append(Fairywren.makeErrorElement(validPassword));
		return;
	}
	
	if(password0.val() !== password1.val())
	{
		Fairywren.changePassword.alert.append(Fairywren.makeErrorElement("Passwords do not match"));
		return;
	}
	
	jQuery.post(Fairywren.account.password.href, { "password" : Fairywren.hashPassword(password0.val()) }).
	done(
		function(data){
			if(! Fairywren.isError(data))
			{
				password0.val("");
				password1.val("");
				Fairywren.changePassword.alert.append(Fairywren.makeSuccessElement("Password changed!"));
			}
		}
	).
	fail(Fairywren.handleServerFailure(Fairywren.changePassword.alert));
	
	return false;
}
