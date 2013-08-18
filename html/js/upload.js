

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



Fairywren.loadUpload = function()
{
	
	$("#announceUrl").text(Fairywren.account.announce.href);
}
