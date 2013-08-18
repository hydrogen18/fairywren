

Fairywren.search = {};
Fairywren.search.init = function()
{
	Fairywren.search.torrentTable = $("#torrentSearch").find("#torrentTable");
	Fairywren.search.torrentTable.hide();
	Fairywren.search.searchbox = $("#torrentSearch").find("#searchTokens");
	Fairywren.search.msg = $("#torrentSearch").find("#msg");
	
}

Fairywren.search.extractTokens = function()
{
	var tokens = Fairywren.search.searchbox.val().split(' ');
	
	for(var i = tokens.length-1; i >= 0 ; --i)
	{
		tokens[i] = jQuery.trim(tokens[i]);
		if(tokens[i] === "")
		{
			tokens.splice(i,1);
		}
	}
	
	return tokens;
}

Fairywren.search.search = function()
{
	Fairywren.search.msg.text("");
	var tokens = Fairywren.search.extractTokens();
	
	if (tokens.length === 0)
	{
		return;
	}
	jQuery.get('api/torrents',{ search:1 , "token" : tokens }).done(
		function(data)
		{
			if('error' in data)
			{
				Fairywren.errorHandler(data);
			}
			else
			{
				if(data.torrents.length == 0)
				{
					Fairywren.search.msg.text("Sorry, no results were found");
					Fairywren.search.torrentTable.hide();
					return;
				}
				Fairywren.search.torrentTable.show();
				Fairywren.clearAndRenderTorrents(Fairywren.search.torrentTable,data.torrents);
			}
		}
		).fail( function (jqXhr,textStatus,errorThrown )
		{
			Fairywren.serverErrorHandler(jqXhr,textStatus,errorThrown,Fairywren.search.msg);
		});
	
}
