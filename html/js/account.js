
Fairywren.loadAccount = function()
{
	var list = $("#accountInfo");
	
	data = Fairywren.account;
	list.empty();
	list.append($("<dt/>").text("Username"));
	list.append($("<dd/>").text(data.name));
	
	list.append($("<dt/>").text("Number of torrents uploaded"));
	list.append($("<dd/>").text(data.numberOfTorrents));
	Fairywren.showInvites();
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
	
	var errDisplay = $("#changePassword").find(".warning");
	var showOnSuccess = $("#changePassword").find(".success");
	showOnSuccess.hide();
	errDisplay.text("");
	
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
	
	jQuery.post(Fairywren.account.password.href, { "password" : Fairywren.hashPassword(password0.val()) }).
	done(
		function(data){
			if("error" in data)
			{
				Fairywren.errorHandler(data);
			}
			else
			{
				showOnSuccess.show();		
				password0.val("");
				password1.val("");
			}
		}
	).
	fail(function(jqXhr,textStatus,errorThrown)
		{
			Fairywren.serverErrorHandler(jqXhr,textStatus,errorThrown,errDisplay);
		});
	
}
