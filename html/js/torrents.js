
Fairywren = {}
Fairywren.account = null;
Fairywren.MIN_PASSWORD_LENGTH = 12;

$(document).ready(function(){
	
	$("#torrentUpload").ajaxForm();

	jQuery.get("api/session").
	done(
		function(data)
		{
			if("error" in data)
			{
				$("#message").text(data.error);
			}
			else
			{
				Fairywren.my = data.my;
				jQuery.get(Fairywren.my).
				done(
					function(data)
					{
						if("error" in data)
						{
							$("#message").text(data.error);
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
	Fairywren.showTorrents();
});

Fairywren.showTorrents = function()
{

	var torrentTable = $("#torrentTable");
	torrentTable.find('tr:gt(0)').remove();
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
							var adjustment = Math.pow(SCALE,i);
							adjustedLength = lengthInBytes / adjustment;
							adjustedUnits = ADJUSTMENTS[i];
						}
						
						
						var displayLengthFixed = parseInt(adjustedLength) !== adjustedLength;
						if(displayLengthFixed)
						{
							adjustedLength = adjustedLength.toFixed(2);
						}
						
						var row = '<tr><td>' + title + 
						'&nbsp;<a href="' + downloadUrl + '">Download</a></td>\
						<td>' + adjustedLength + ' ' + adjustedUnits + '</td>\
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
	
	$("#announceUrl").text(Fairywren.account.announceResource);
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
	if(password0.val().length < Fairywren.MIN_PASSWORD_LENGTH)
	{
		errDisplay.text("Password too short, must be at least " + Fairywren.MIN_PASSWORD_LENGTH + " characters");
		return;
	}
	
	if(password0.val() !== password1.val())
	{
		errDisplay.text("Password does not match");
		return;
	}
	
	var pwSha = new jsSHA(password0.val(),"TEXT");
	var pwHash = pwSha.getHash("SHA-512","B64").replace(/=/g,"");
	
	jQuery.post(Fairywren.account.password, { "password" :pwHash }).
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
