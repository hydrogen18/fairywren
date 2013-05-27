
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
				$("#announce").text("Announce URL:"+data.announceResource);
			}
		}
	).
	fail(
		function()
		{
			$("#message").text("Server error");
		}
	);
	
	
});


function upload()
{
	$("#torrentUpload").ajaxSubmit().resetForm();
	
	return false;
}
