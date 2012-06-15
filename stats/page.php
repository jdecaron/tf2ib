<?php

// TF2 Log Parser
// file: page.php
// author: rusty fausak
// date: dec 15 2007
// rev: v1.0 dec 15 2007
// desc: This file just contains the skeleton HTML and a single function for pushing
//       content into that skeleton.

function return_page ($contents, $nav, $rel) {
	if ($rel) {
		$path = '../../';
	}
	if (!$contents) { $contents = ''; }
	$str = <<<EOT
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">

<head>
<meta http-equiv="content-type" content="text/html; charset=iso-8859-1">
<meta name="description" content="Team Fortress 2 Log Parser for Server Logs">
<meta name="keywords" content="TF2, tf2, stats, log, logs, parse, match, parser, server">
<meta name="author" content="Rusty Fausak">
<link rel="stylesheet" type="text/css" href="{$path}global.css" media="screen">
<title>#tf2.pug.na on irc.gamesurge.net</title>
</head>

<body>
<div id='container'>
<div class='main'>
	<div class='topheader'><div style="position:absolute;right:28px;width:200px;"><a href="http://aigaming.com/" ><img style="text-decoration:none;border:0px" src="ai.gif"></a></div><form name="input" action="/" method="get"><input type="text" name="search" value="{$_REQUEST['search']}"/><input type="submit" value="Search" style="margin-left:20px;" /></form></div></a>
	<div class='content1'>
		{$contents}
	</div>
</div>
<div class='footer'>
&copy;2007-2008 Rusty 'spike' Fausak gamesurge#clanYoda
</div>
</body>

</html>
EOT;
	return $str;
}

function make_page ($contents, $nav, $rel = 0) {
	print return_page($contents, $nav, $rel);
}
