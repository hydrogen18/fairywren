$(document).ready(function(){
	$("body").prepend(Fairywren.makeNavbar());
	
	Fairywren.swarm.alert = $("#swarm").find("#alert");
	
	jQuery.get('api/swarm').
	done(
		function(data)
		{
			if(! Fairywren.isError(data))
			{
				Fairywren.swarm.data = data;
				Fairywren.swarm();
			}
		}
		).fail(Fairywren.handleServerFailure(Fairywren.swarm.alert) );
	
});

Fairywren.swarm = function()
{
	var out = $("#swarm");
	for(username in Fairywren.swarm.data)
	{
		var div = $("<div />");
		
		var a = $("<span />");
		a.text(username);
		var user = Fairywren.swarm.data[username]
		//a.attr('href' ,'user.html#' + user.href );
		
		div.append($("<h4 />").append(a));
		
		var table = $("<table />");
		table.addClass('table');
		var thead = $("<thead />");
		var tr = $("<tr />");
		tr.append($("<th />").text('IP'));
		tr.append($("<th />").text('Port'));
		tr.append($("<th />").text('Last Seen'));
		tr.append($("<th />").text('First Seen'));
		
		thead.append(tr);
		table.append(thead);
		
		var tbody = $("<tbody />");
		
		for(var i = 0; i != user.length; ++i)
		{
			var tr = $("<tr />");
			
			var peer = user[i];
			tr.append($("<td />").text(peer.ip));
			tr.append($("<td />").text(peer.port));
			tr.append($("<td />").text(Fairywren.trimIsoFormatDate(peer.lastSeen)));
			tr.append($("<td />").text(Fairywren.trimIsoFormatDate(peer.firstSeen)));
			
			tbody.append(tr);
		}
		
		table.append(tbody);
		div.append(table);
		
		out.append(div);
	}
};	



