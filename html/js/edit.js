
Fairywren.edit = function(){
	Fairywren.edit.title.val(Fairywren.edit.data.title);
	Fairywren.edit.extended.val(JSON.stringify(Fairywren.edit.data.extended));
};

Fairywren.edit.save = function(){
	jQuery.post(Fairywren.edit.href,{
	title : Fairywren.edit.title.val(),
	extended : Fairywren.edit.extended.val()
		}).done(
	function(data)
	{
		if(! Fairywren.isError(data))
		{
			window.location = 'torrent.html#' + Fairywren.edit.href;
		}
	}
	).fail(Fairywren.handleServerFailure(Fairywren.edit.alert) );
}

$(document).ready(function(){
	$("body").prepend(Fairywren.makeNavbar());
	var hash = window.location.hash;
	
	Fairywren.edit.alert = $("#torrent").find("#alert");
	Fairywren.edit.title = $("#torrent").find("#title");
	Fairywren.edit.extended = $("#torrent").find("#extended");
	
	if(hash.length === 0)
	{
		//User got here on accident or something. Display error message
		//and depart
		Fairywren.edit.alert.append(Fairywren.makeErrorElement("You seem to have reached this page in error",true));
		return;
	}
	
	Fairywren.edit.href = hash.slice(1);
	
	jQuery.get(Fairywren.edit.href).
	done(
		function(data)
		{
			if(! Fairywren.isError(data))
			{
				Fairywren.edit.data = data;
				Fairywren.edit();
			}
		}
		).fail(Fairywren.handleServerFailure(Fairywren.edit.alert) );
	
});


