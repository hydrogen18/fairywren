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
		
		var a = $("<a />");
		a.text(username);
		var user = Fairywren.swarm.data[username]
		a.attr('href' ,'user.html#' + user.href );
		
		div.append($("<h4 />").append(a));
		
		var table = $("<table />");
		table.addClass('table');
		var thead = $("<thead />");
		var tr = $("<tr />");
		tr.append($("<th />").text('IP'));
		tr.append($("<th />").text('Port'));
		tr.append($("<th />").text('# Torrents'));
		
		thead.append(tr);
		table.append(thead);
		
		var tbody = $("<tbody />");
		
		for(var i = 0; i != user.peers.length; ++i)
		{
			var tr = $("<tr />");
			
			var peer = user.peers[i];
			tr.append($("<td />").text(peer.ip));
			tr.append($("<td />").text(peer.port));
			tr.append($("<td />").text(peer.quantity));
			
			
			tbody.append(tr);
		}
		
		table.append(tbody);
		div.append(table);
		
		out.append(div);
	}
};	



