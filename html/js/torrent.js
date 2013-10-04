$(document).ready(function(){
	$("body").prepend(Fairywren.makeNavbar());
	var hash = window.location.hash;
	
	Fairywren.torrent.alert = $("#torrent").find("#alert");
	Fairywren.torrent.title = $("#torrent").find("a#title");
	Fairywren.torrent.info = $("#torrent").find("#info");
	Fairywren.torrent.edit = $("#torrent").find("#edit");
	
	if(hash.length === 0)
	{
		//User got here on accident or something. Display error message
		//and depart
		Fairywren.torrent.alert.append(Fairywren.makeErrorElement("You seem to have reached this page in error",true));
		return;
	}
	
	Fairywren.torrent.href = hash.slice(1);
	
	jQuery.get(Fairywren.torrent.href).
	done(
		function(data)
		{
			if(! Fairywren.isError(data))
			{
				Fairywren.torrent.data = data;
				Fairywren.torrent();
			}
		}
		).fail(Fairywren.handleServerFailure(Fairywren.torrent.alert) );
	
});

Fairywren.torrent = function()
{
	Fairywren.torrent.title.attr('href',Fairywren.torrent.data.metainfo.href);
	Fairywren.torrent.edit.attr('href','edit.html#' + Fairywren.torrent.href);
	Fairywren.torrent.title.text(Fairywren.torrent.data.title);
	
	Fairywren.torrent.info.append($("<dt />").text("Uploaded"));
	Fairywren.torrent.info.append($("<dd />").text(Fairywren.trimIsoFormatDate(Fairywren.torrent.data.creationDate)));
	
	Fairywren.torrent.info.append($("<dt />").text("Uploader"));
	Fairywren.torrent.info.append($("<dd />").text(Fairywren.torrent.data.creator.name));
	
	Fairywren.torrent.info.append($("<dt />").text("Size"));
	Fairywren.torrent.info.append($("<dd />").text(Fairywren.bytesToPrettyPrint(Fairywren.torrent.data.lengthInBytes)));
	
	if(('extended' in Fairywren.torrent.data) && Fairywren.torrent.data.extended !== null)
	{
		for(extension in Fairywren.torrent.data.extended)
		{
			if( ! (extension in Fairywren.torrent.extensions))
			{
				return;
			}
			
			var row = $("<div />");
			row.addClass('row');
			
			var data = Fairywren.torrent.data.extended[extension];
			
			row.append(Fairywren.torrent.extensions[extension](data));
			
			$("body").append(row);
			
		}		
	}
};	

Fairywren.torrent.extensions = {};

