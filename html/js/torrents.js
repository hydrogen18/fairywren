


$(document).ready(function(){
	
	jQuery.get("api/torrents").
	done(
		function(data)
		{
			if("error" in data)
			{
				$("#message").text(data.error);
			}
			else
			{
				for(i in data.torrents)
				{
					var title = data.torrents[i].title;
					var uploadTime = data.torrents[i].creationDate;
					var uploader = data.torrents[i].creator.name;
					var downloadUrl = data.torrents[i].resource;
					var lengthInBytes = data.torrents[i].lengthInBytes;
					
					var row = '<tr><td>' + title + 
					'&nbsp;<a href="' + downloadUrl + '">Download</a></td>\
					<td>' + lengthInBytes +' bytes</td>\
					<td>' + uploadTime + "</td>\
					<td>" + uploader + "</td></tr>";
					$("#torrentTable tr:last").after(row);
				}
			}
		}
	).
	fail(
		function()
		{
			$("#message").text("Server error");
		}
	);
	
	
});
