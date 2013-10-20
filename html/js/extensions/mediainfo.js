

Fairywren.torrent.extensions.mediainfo =  function(data)
	{
		var retval = $("<div />");
		retval.addClass('span12');
		var files = $("<ul />");
		var hidden = [];
		for(filename in data.files)
		{
			var trackList = $("<ul />");
			var file = data.files[filename];
			var tracks = file.tracks;
			for(var i = 0; i != tracks.length; ++i)
			{
				var track = tracks[i];
				
				var showTrack = track.type in Fairywren.torrent.extensions.mediainfo.allowedTracks;
				
				var trackKvs = $("<ul />");
				for( k in track )
				{
					var v = $("<span />").text(track[k]);
					
					var kText = k;
					
					var showKey = false;
					if(showTrack)
					{
						showKey = k in Fairywren.torrent.extensions.mediainfo.allowedTracks[track.type];
					}
					
					if(showKey)
					{
						kText = Fairywren.torrent.extensions.mediainfo.allowedTracks[track.type][k]||kText;
					}
					
					var k = $("<span />").text(kText);
					
					var kvElement = $("<li />").append(k,$("<span />").text(': '),v);
					
					if(!showKey)
					{
						kvElement.hide();
						hidden.push(kvElement);
					}
					
					trackKvs.append(kvElement);
				}
				
				var trackElements = $("<li />").append($("<span />").text(track.type),trackKvs);

				if(!showTrack)
				{
					trackElements.hide();
					hidden.push(trackElements);
				}

				trackList.append(trackElements);
				
			}
			
			var fileItem = $("<li />");
			var span = $("<span />").text(filename)
			span.data('trackListing',trackList);
			span.addClass('btn btn-link');
			span.click(Fairywren.torrent.extensions.mediainfo.toggleTrackListingVisibility);
			fileItem.append(span);
			$(trackList).hide();
			hidden.push(trackList);
			fileItem.append(trackList);
			files.append(fileItem);
		}
		
		var showAllButton = $("<button />");
		showAllButton.addClass('btn');
		showAllButton.text('Show All');
		showAllButton.click(function()
		{
			for(var i = 0 ; i != hidden.length; ++i)
			{
				hidden[i].show();
			}
			$(this).remove();
			hidden = null;
		})
		retval.append($("<p />").append($("<h3 />").text('Media Info')));
		retval.append($("<p />").append(showAllButton));
		retval.append(files);
		
		return retval;
	};
	
Fairywren.torrent.extensions.mediainfo.toggleTrackListingVisibility = 	function(){
				$(this).data('trackListing').toggle();
			};

Fairywren.torrent.extensions.mediainfo.allowedTracks = {
	'General' : {
		'Format' : null,
		'Duration' : null,
		'File_size' : 'File Size',
		'Stream_size' : 'Stream Size'
	},
	
	'Video' : {
		'Width':null,
		'Height':null,
		'Frame_rate' : 'Frame Rate',
		'Bit_rate' : 'Bit Rate',
		'Stream_size' : 'Stream Size'
		},
	
	'Audio' : {
		'Compression_mode' : 'Compression Mode',
		'Language' : null,
		'Bit_rate' : 'Bit Rate',
		'Channel_s_' : 'Channels',
		'Format' : null,
		'Stream_size' : 'Stream Size',
		'Duration' : null,
		'Sampling_rate' : 'Sampling rate'
	},
	
	'Text': {
		'Language' : null
		}
	
};
