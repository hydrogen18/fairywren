Fairywren.torrentTab = {};
Fairywren.torrentTab.init = function()
{
	
}
Fairywren.torrentTab.tabs = {};
Fairywren.torrentTab.nextIndex = 4;
Fairywren.torrentTab.extension = {};
Fairywren.torrentTab.display = function(href)
{
	if(href in Fairywren.torrentTab.tabs)
	{
		Fairywren.torrents.tabs.tabs({'active':Fairywren.torrentTab.tabs[href]});
		return;
	}
	
	jQuery.get(href).
	done(function(data)
		{
			if('error' in data)
			{
				Fairywren.errorHandler(data);
			}
			else
			{
				var newLi = $("<li />");
				var anchor = $("<a />");
				anchor.attr('href','#' + href);
				anchor.text(data.title);
				newLi.append(anchor);
				
				var closeButton = $("<a />")
				closeButton.text('\u2a2f');
				closeButton.addClass('tabCloseButton');

				newLi.append(closeButton);
				
				
				$("#tabs").append(newLi)
				var newDiv = $("<div />");
				newDiv.attr('id',href);
				
				var contentDiv = $("<div />");
				contentDiv.attr('class','contentBox ui-corner-all');
				
				var header = $("<div />");
				header.attr('class','contentBoxHeader ui-corner-all');
				header.text(data.title);
				
				contentDiv.append(header);
				
				contentDiv.append( '<a href="' + data.metainfo.href + '">Download</a>');
				contentDiv.append($("<br />"));
				
				contentDiv.append($("<span />").text("Created on: " + Fairywren.trimIsoFormatDate(data.creationDate)));
				contentDiv.append($("<br />"));
				
				
				contentDiv.append($("<span />").text("Uploaded by: " + data.creator.name));
				contentDiv.append($("<br />"));
				
				contentDiv.append($("<span />").text("Size: " + Fairywren.bytesToPrettyPrint(data.lengthInBytes) ));
				contentDiv.append($("<br />"));
				
				newDiv.append(contentDiv);
				
				Fairywren.torrentTab.tabs[href] = Fairywren.torrentTab.nextIndex;
				
				if('extended' in data && data.extended !== null)
				{
					for(extension in data.extended)
					{
						if(extension in Fairywren.torrentTab.extension)
						{
							var ext = Fairywren.torrentTab.extension[extension];
							var dat = data.extended[extension];
							var contentDiv = $("<div />");
							contentDiv.addClass('contentBox');
							contentDiv.addClass('ui-corner-all');
							var header = $("<div />");
							header.addClass('contentBoxHeader');
							header.addClass('ui-corner-all');
							header.text(ext.displayName);
							contentDiv.append(header);
							ext.attach(dat,contentDiv);
							newDiv.append(contentDiv);
						}
					}
				}
				Fairywren.torrents.tabs.append(newDiv);
				
				closeButton.click(function()
				{
					newDiv.remove();
					newLi.remove();
					var index = Fairywren.torrentTab.tabs[href];
					delete Fairywren.torrentTab.tabs[href];
					for( t in Fairywren.torrentTab.tabs)
					{
						if(Fairywren.torrentTab.tabs[t] > index)
						{
							Fairywren.torrentTab.tabs[t]--;
						}
					}
					Fairywren.torrentTab.nextIndex--;
					Fairywren.torrents.tabs.tabs('refresh');
					Fairywren.torrents.tabs.tabs({active:0});
				})
				
				Fairywren.torrents.tabs.tabs('refresh');
				Fairywren.torrents.tabs.tabs({'active': Fairywren.torrentTab.nextIndex++ } );
				
			}
		}
	);
};

