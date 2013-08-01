

Fairywren.account = null;


$(document).ready(function(){
	
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
						}
					}
				);
			}
		}
		);
	
	
	$("#main").tabs();
	$("#torrentBrowseBar").hide();
	Fairywren.loadTorrentsForPage();
});

Fairywren.torrents = {};
Fairywren.torrents.pageSize = 20;
Fairywren.torrents.page = 0;
Fairywren.torrents.pages = null;
Fairywren.torrents.numPages = null;

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
						$("#message").text(data.error);
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
				function()
				{
					$("#message").text("Server error");
				}
			);;
	}
	else
	{
		//Just update the DOM immediately
		Fairywren.showTorrents();
	}
			
}

Fairywren.showTorrents = function()
{
	var torrentTable = $("#torrentTable");
	torrentTable.find('tr:gt(0)').remove();
	var page = Fairywren.torrents.page;
	$("#pageNumbers").text((page +1 )+ ' / ' + Fairywren.torrents.numPages);
	
	var pageset = Fairywren.torrents.pages[page];
	for(i in pageset)
	{
		var title = pageset[i].title;
		var uploadTime = pageset[i].creationDate.substr(0,19);
		var uploader = pageset[i].creator.name;
		var downloadUrl = pageset[i].metainfo.href;
		var lengthInBytes = pageset[i].lengthInBytes;
		var seeds = pageset[i].seeds;
		var leeches = pageset[i].leeches;
		
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
		
		var row = '<tr><td>' + title + 
		'&nbsp;<a style="float:right;" class="downloadLink" href="' + downloadUrl + '">Download</a>\
		<span style="float:right;" >'+ '&uarr;' + seeds  + '&nbsp;&darr;' + leeches + '</span></td>\
		<td>' + adjustedLength + ' ' + adjustedUnits + '</td>\
		<td>' + uploadTime + "</td>\
		<td>" + uploader + "</td></tr>";
		$("#torrentTable tr:last").after(row);
	}
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
		
		error : function()
		{
			showOnFailure.show();
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
	
	jQuery.post(Fairywren.account.password, { "password" : Fairywren.hashPassword(password0.val()) }).
	done(
		function(data){
			if("error" in data)
			{
				$("#message").text(data.error);
			}
			else
			{
				showOnSuccess.show();		
				password0.val("");
				password1.val("");
			}
		}
	).
	fail(
		function()
		{
			$("#message").text("Server error");
		})
		;
	
}
