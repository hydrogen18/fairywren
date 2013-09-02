

$(document).ready(function(){
	Fairywren.upload.alert = $("#uploadAlert");
	Fairywren.upload.announceUrl = $("#announceUrl");
	$("body").prepend(Fairywren.makeNavbar());
	$("#torrentUpload").ajaxForm();
	
	jQuery.get("api/session").
	done(
		function(data)
		{
			if(! Fairywren.isError(data))
			{				 
				jQuery.get(data.my.href).
				done(
					function(data)
					{
						if( ! Fairywren.isError(data) )
						{
							Fairywren.upload.announceUrl.text(data.announce.href);
						}
					}
				).fail(Fairywren.handleServerFailure($("#uploadInfo")));
			}
		}
		).fail(Fairywren.handleServerFailure($("#uploadInfo")));
});

Fairywren.upload = function()
{
	Fairywren.upload.alert.find('div').remove();
	var options ={
		
		success : function(responseText,statusText,xhr,$form)
		{
			Fairywren.upload.alert.append(Fairywren.makeSuccessElement('Upload successful!'));
			
		},
		
		error : Fairywren.handleServerFailure(Fairywren.upload.alert),
		clearForm : true,
		
	};
		
	$("#torrentUpload").ajaxSubmit(options);
	
	return false;
}


