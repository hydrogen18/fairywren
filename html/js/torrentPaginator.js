
function TorrentPaginator(divEle){
	this.divEle = divEle;
	this.bar = $("<div />");

	this.pageIndicator = $("<span />");
	this.pageIndicator.addClass('badge');
	this.pageIndicator.text('999/999');
	
	var newer = $("<li />").addClass('previous').append(
			$("<a />").attr('href','#').text('\u2190Newer'));
			
	var refresh = $("<li />").append(
			$("<a />").attr('href','#').css('font-size','2em').append('\u0020\u21bb\u0020').append("<br />").append(this.pageIndicator ));
			
	var older = $("<li />").addClass('next').append(
			$("<a />").attr('href','#').text('Older\u2192'));
	
	this.bar.append($("<ul />").addClass('pager').append(newer).append(refresh).append(older));

	this.divEle.append(this.bar);

	this.table = $("<table />");
	this.table.addClass("table table-hover table-bordered");
	
	this.table.append(
	$("<thead />").append(
		$("<tr />").append(
			$("<th />").text('Title')).append(
			$("<th />").text('Size')).append(
			$("<th />").text('Upload Time')).append(
			$("<th />").text('Uploader'))));
			
	this.tableBody = $("<tbody />");
	
	this.table.append(this.tableBody);
	
	this.divEle.append(this.table);
	
	this.pageSize = 20;
	
	this.currentPage = 0;
	
	this.pages = null;
	
}

TorrentPaginator.prototype.show = function()
{
	var newBody = $("<tbody />");
	
	var pageset = this.pages[this.currentPage];
	
	for(i in pageset)
	{
		var title = pageset[i].title;
		var uploadTime = Fairywren.trimIsoFormatDate(pageset[i].creationDate);
		var uploader = pageset[i].creator.name;
		var downloadUrl = pageset[i].metainfo.href;
		var lengthInBytes = pageset[i].lengthInBytes;
		var seeds = pageset[i].seeds;
		var leeches = pageset[i].leeches;
		
		var adjustedLength = Fairywren.bytesToPrettyPrint(lengthInBytes);
		
		var titleSpan = $("<span />");
		var infoHref = pageset[i].info.href;
		titleSpan.click(infoHref,function(event){
			Fairywren.torrentTab.display(event.data);
		});
		titleSpan.attr('style','white-space:nowrap;');
		titleSpan.text(title);
		
		var row = $("<tr />");
		var titleData = $("<td />");
		titleData.append(titleSpan);
		
		var rightHandOfTitleData = $("<span />");
		rightHandOfTitleData.css('float','right');
		rightHandOfTitleData.append($('<span >'+ '&uarr;' + seeds  + '&nbsp;&darr;' + leeches + '&nbsp;</span>'));
		rightHandOfTitleData.append($('<a />').addClass('btn btn-primary').attr('href',downloadUrl).text('Download'));
		titleData.append(rightHandOfTitleData);
		
		row.append(titleData);
		
		row.append('<td>' + adjustedLength + '</td>\
		<td>' + uploadTime + "</td>\
		<td>" + uploader + "</td>");
		
		newBody.append(row);				
	}
	
	this.table.find('tbody').remove();
	this.table.append(newBody);
	
	this.pageIndicator.text( (this.currentPage + 1) + '/' + this.pages.length);
}

TorrentPaginator.prototype.flipPage = function(movement)
{
	
}

TorrentPaginator.prototype.loadTorrentsForPage = function(clearCache)
{
	if( ! (clearCache === undefined || clearCache === null) && clearCache)
	{
		this.pages = null;
	}
	var page = this.currentPage;
	
	var self = this;
	if(this.pages === null || this.pages[page] === null)
	{
		jQuery.get("api/torrents",{'resultSize':this.pageSize,'subset':page}).
		
		done(function(data)
		{
			if( ! Fairywren.isError(data) )
			{
				var numPages = data.numSubsets;
				if(self.pages === null || self.pages.length != numPages)
				{
					self.pages = [];
					for(var i= 0; i < numPages ; ++i)
					{
						self.pages.push(null);
					}
				}
				
				self.pages[page] = data.torrents;
				self.show();
			}
		}).
		fail(Fairywren.handleServerFailure(this.divEle));
	}
	else
	{
		this.show();
	}
}
