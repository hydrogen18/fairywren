

Fairywren.torrentTab.extension.mediainfo = {
	displayName : 'Media Info',
	attach : function(data,div)
	{
		var files = $("<ul />");
		
		for(filename in data.files)
		{
			var trackList = $("<ul />");
			var file = data.files[filename];
			var tracks = file.tracks;
			for(var i = 0; i != tracks.length; ++i)
			{
				var track = tracks[i];
				var trackKvs = $("<ul />");
				for( k in track )
				{
					var v = $("<span />").text(track[k]);
					var k = $("<span />").text(k);
					trackKvs.append($("<li />").append(k,$("<span />").text(': '),v));
				}
				trackList.append($("<li />").append($("<span />").text(track.type),trackKvs));
			}
			
			var fileItem = $("<li />");
			fileItem.append($("<span />").text(filename));
			fileItem.append(trackList);
			files.append(fileItem);
		}
		div.append(files);
	}
};
