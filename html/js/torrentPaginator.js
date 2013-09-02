
function TorrentPaginator(divEle){
	this.divEle = divEle;
	this.bar = $("<div />");

	this.pageIndicator = $("<span />");
	this.pageIndicator.addClass('badge');
	this.pageIndicator.text('999/999');
	
	var self = this;
	var newer = $("<li />").addClass('previous').append(
			$("<a />").attr('href','#').text('\u2190Newer').click(function()
			{
				self.flipPage(-1);
				
				}));
			
	var refresh = $("<li />").append(
			$("<a />").attr('href','#').css('font-size','2em').append('\u0020\u21bb\u0020').click(function(){
				self.loadTorrentsForPage(true);
				}).append("<br />").append(this.pageIndicator ));
			
	var older = $("<li />").addClass('next').append(
			$("<a />").attr('href','#').text('Older\u2192').click(function()
			{
				self.flipPage(1);
				
				}));
	
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
		
		var titleAnchor = $("<a />");
		var infoHref = 'torrent.html#' + pageset[i].info.href;
		titleAnchor.attr('href',infoHref);
		titleAnchor.attr('style','white-space:nowrap;');
		titleAnchor.text(title);
		
		var row = $("<tr />");
		var titleData = $("<td />");
		titleData.append(titleAnchor);
		
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
	this.currentPage += movement;
	
	if(this.currentPage < 0 )
	{
		this.currentPage = 0;
	}
	
	if(this.currentPage >= this.pages.length)
	{
		this.currentPage = this.pages.length - 1;
	}
	
	this.loadTorrentsForPage(false);
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
