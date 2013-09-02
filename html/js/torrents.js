

Fairywren.account = null;

Fairywren.torrents = {}

$(document).ready(function(){
	$("body").prepend(Fairywren.makeNavbar);
	
	jQuery.ajaxSettings.traditional = true;
	var p = new TorrentPaginator($("#newestTorrents"));
	p.loadTorrentsForPage();
	
	return;
});




