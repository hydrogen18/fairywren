
$(document).ready(function(){
	jQuery.ajaxSettings.traditional = true;
	Fairywren.search.alert = $("#searchAlert");
	Fairywren.search.searchBox = $("#searchTokens");
	
	Fairywren.search.table = $("#searchTable");
	
	$("body").prepend(Fairywren.makeNavbar());
});

Fairywren.search = function(){
	Fairywren.search.alert.find('div').remove();
	var tokens = Fairywren.search.extractTokens();
	
	if (tokens.length === 0)
	{
		return;
	}
	
	Fairywren.search.table.find('tbody').remove();
	
	jQuery.get('api/torrents',{ search:1 , "token" : tokens }).done(
		function(data)
		{
			
			if(! Fairywren.isError(data))
			{
				if ( data.torrents.length === 0)
				{
					Fairywren.search.alert.append(Fairywren.makeErrorElement('Sorry, no results were found'));
					return;
				}
				
				var tmp = { pages : [data.torrents], currentPage : 0, table:Fairywren.search.table, pageIndicator: $('<p />')};
				
				TorrentPaginator.prototype.show.apply(tmp,[]);
				
			}
		
		}
		).fail( Fairywren.handleServerFailure(Fairywren.search.alert));
}

Fairywren.search.extractTokens = function()
{
	var tokens = Fairywren.search.searchBox.val().split(' ');
	
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

