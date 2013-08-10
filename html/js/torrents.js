

Fairywren.account = null;

Fairywren.torrents = {}

$(document).ready(function(){
	jQuery.ajaxSettings.traditional = true;
	
	Fairywren.search.init();
	Fairywren.torrents.init();
	
	$("#torrentUpload").ajaxForm();

	jQuery.get("api/session").
	done(
		function(data)
		{
			if("error" in data)
			{
				Fairywren.errorHandler(data);
			}
			else
			{
				Fairywren.my = data.my;
				jQuery.get(Fairywren.my.href).
				done(
					function(data)
					{
						if("error" in data)
						{
							Fairywren.errorHandler(data);
						}
						else
						{
							Fairywren.account = data;
							Fairywren.loadTorrentsForPage();
						}
					}
				);
			}
		}
		).fail(function(jqXhr,textStatus,errorThrown)
		{
			Fairywren.serverErrorHandler(jqXhr,textStatus,errorThrown,$("#message"));
		});
	
	
	Fairywren.torrents.tabs = $("#main");
	Fairywren.torrents.tabs.tabs();
	
	
});


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

Fairywren.torrents = {};
Fairywren.torrents.init = function()
{
	$("#torrentBrowseBar").hide();
	Fairywren.torrents.pageSize = 20;
	Fairywren.torrents.page = 0;
	Fairywren.torrents.pages = null;
	Fairywren.torrents.numPages = null;
	Fairywren.torrents.msg = $("#torrents").find("#msg");
}

Fairywren.flipPage = function(dist)
{
	
	//Move the page the requested amount
	Fairywren.torrents.page += dist;
	//Check to see if bounds have been exceeded. If so, back out the change
	//and do nothing
	if (Fairywren.torrents.page < 0 || Fairywren.torrents.page >= Fairywren.torrents.numPages)
	{
		Fairywren.torrents.page -= dist;
		return;
	}
	
	//Load the torrents for this page
	Fairywren.loadTorrentsForPage();
}

Fairywren.loadTorrentsForPage = function(clearCache)
{
	//If clearcache is specified and is true,
	//then remove any chaced pages
	if(! (clearCache===undefined || clearCache === null) && clearCache)
	{
		Fairywren.torrents.pages = null;
	}
	
	var page = Fairywren.torrents.page;
	//If the page is not loaded in the cache, then request it
	if (Fairywren.torrents.pages===null || Fairywren.torrents.pages[page] === null)
	{
		//Request the torrents list
		jQuery.get("api/torrents",{'resultSize': Fairywren.torrents.pageSize, 'subset':Fairywren.torrents.page}).
			done(
				function(data)
				{
					if("error" in data)
					{
						Fairywren.errorHandler(data);
					}
					else
					{
						Fairywren.torrents.numPages = data.numSubsets;
						
						//Create the array of torrent pages if needed
						if (Fairywren.torrents.pages === null || Fairywren.torrents.pages.length != Fairywren.torrents.numPages)
						{
							Fairywren.torrents.pages = [];
							for(var i = 0 ; i < Fairywren.torrents.numPages ; ++i)
							{
								//No pages are loaded by default
								Fairywren.torrents.pages.push(null);
							}
						}
						
						//Add this page to the list
						Fairywren.torrents.pages[page] = data.torrents;
						
						//Update the DOM
						Fairywren.showTorrents();
					}
				}).
			fail(
				function(jqXhr,textStatus,errorThrown)
				{
					Fairywren.serverErrorHandler(jqXhr,textStatus,errorThrown,Fairywren.torrents.msg);
					
				}
			);;
	}
	else
	{
		//Just update the DOM immediately
		Fairywren.showTorrents();
	}
			
}

Fairywren.trimIsoFormatDate = function(dateStr)
{
	return dateStr.substr(0,19);
}

Fairywren.bytesToPrettyPrint = function(lengthInBytes)
{
	var adjustedLength = lengthInBytes;
	var adjustedUnits = 'bytes';
	
	var ADJUSTMENTS = ['kilobytes','megabytes','gigabytes'];
	var SCALE = 1024;
	for(var i = 0;i < ADJUSTMENTS.length; ++i)
	{
		if(SCALE > adjustedLength )
		{
			break;
		}
		var adjustment = Math.pow(SCALE,i+1);
		adjustedLength = lengthInBytes / adjustment;
		adjustedUnits = ADJUSTMENTS[i];
	}
	
	var displayLengthFixed = parseInt(adjustedLength) !== adjustedLength;
	if(displayLengthFixed)
	{
		adjustedLength = adjustedLength.toFixed(2);
	}
	return adjustedLength + ' ' + adjustedUnits;
}

Fairywren.clearAndRenderTorrents = function(torrentTable,pageset)
{
	torrentTable.find('tr:gt(0)').remove();
	
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
		titleSpan.attr('class','torrentLink');
		var infoHref = pageset[i].info.href;
		titleSpan.click(infoHref,function(event){
			Fairywren.torrentTab.display(event.data);
		});
		titleSpan.text(title);
		
		var row = $("<tr />");
		var titleData = $("<td />");
		titleData.append(titleSpan);
		
		titleData.append('&nbsp;<a style="float:right;" class="downloadLink" href="' + downloadUrl + '">Download</a>\
		<span style="float:right;" >'+ '&uarr;' + seeds  + '&nbsp;&darr;' + leeches + '</span>');
		
		row.append(titleData);
		
		row.append('<td>' + adjustedLength + '</td>\
		<td>' + uploadTime + "</td>\
		<td>" + uploader + "</td>");
		
		torrentTable.find("tr:last").after(row);
		
		
	}
	

}

Fairywren.showTorrents = function()
{
	
	var torrentTable = $("#torrents").find("#torrentTable");
	
	var page = Fairywren.torrents.page;
	$("#pageNumbers").text((page +1 )+ ' / ' + Fairywren.torrents.numPages);
	
	var pageset = Fairywren.torrents.pages[page];
	Fairywren.clearAndRenderTorrents(torrentTable,pageset);
	
	$("#torrentBrowseBar").show();

}


Fairywren.uploadTorrent = function()
{
	
	var showOnSuccess = $("#torrentUpload").find(".success");
	var showOnFailure = $("#torrentUpload").find(".failure");
	
	showOnSuccess.hide();
	showOnFailure.hide();
	
	var options ={
		
		success : function(responseText,statusText,xhr,$form)
		{
			showOnSuccess.show();
		},
		
		error : 
		function(jqXhr,textStatus,errorThrown)
		{
			showOnFailure.show();
			Fairywren.serverErrorHandler(jqXhr,textStatus,errorThrown,$("#upload").find("#msg"));
		},
		clearForm : true,
		
	};
		
	$("#torrentUpload").ajaxSubmit(options);
	
	return false;
}

Fairywren.loadAccount = function()
{
	var list = $("#accountInfo");
	
	data = Fairywren.account;
	list.empty();
	list.append($("<dt/>").text("Username"));
	list.append($("<dd/>").text(data.name));
	
	list.append($("<dt/>").text("Number of torrents uploaded"));
	list.append($("<dd/>").text(data.numberOfTorrents));
}

Fairywren.loadUpload = function()
{
	
	$("#announceUrl").text(Fairywren.account.announce.href);
}

Fairywren.changePassword = function()
{
	var passwords = $("#changePassword").find("input");
	var password0 = $(passwords[0]);
	var password1 = $(passwords[1]);
	
	var errDisplay = $("#changePassword").find(".warning");
	var showOnSuccess = $("#changePassword").find(".success");
	showOnSuccess.hide();
	errDisplay.text("");
	
	var validPassword = Fairywren.validatePassword(password0.val());
	if( validPassword !== null)
	{
		errDisplay.text(validPassword);
		return;
	}
	
	if(password0.val() !== password1.val())
	{
		errDisplay.text("Password does not match");
		return;
	}
	
	jQuery.post(Fairywren.account.password.href, { "password" : Fairywren.hashPassword(password0.val()) }).
	done(
		function(data){
			if("error" in data)
			{
				Fairywren.errorHandler(data);
			}
			else
			{
				showOnSuccess.show();		
				password0.val("");
				password1.val("");
			}
		}
	).
	fail(function(jqXhr,textStatus,errorThrown)
		{
			Fairywren.serverErrorHandler(jqXhr,textStatus,errorThrown,errDisplay);
		});
	
}
