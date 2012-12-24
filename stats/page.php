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
<script>
function sort(e, p){
    a0 = new Array();
    a1 = new Array();
    b = '';
    c = 0;
    r = e.parentNode.parentNode;
    n = e.innerHTML;
    s0 = new Array();
    s1 = new Array();
    t = ''
    while(r != null){
        if(r.nodeName == "TR"){
            if(c == 0){
                t = '<tr>' + r.innerHTML + '</tr>';
            }else{
                a0.push({'p':p, 'r':r.innerHTML, 'v':r.childNodes[p].innerHTML.replace(',', '')});
                a1.push(r.childNodes[p].innerHTML.replace(',', ''));
            }
        }
        r = r.nextSibling;
        c++;
    }
    b = a0.pop().r;
    a1.pop();
    a1.sort(function(x,y){return y-x});
    content = '';
    for(i = 0; i < a1.length; i++){
        if(i % 2 == 0){
            c1 = ' class=tr0';
        }else{
            c1 = ' class=tr1';
        }
        for(j = 0; j < a0.length; j++){
            if(a1[i] == a0[j].v){
                content += '<tr' + c1 + '>' + a0[j].r + '</tr>';
                a0.splice(j, 1);
                break;
            }
        }
    }
    e.parentNode.parentNode.parentNode.innerHTML = t + content + b;
}
</script>
<body>
<div id='container'>
<div class='main'>
	<div class='topheader'><form name="input" action="/" method="get"><input type="text" name="search" value="{$_REQUEST['search']}"/><input type="submit" value="Search" style="margin-left:20px;" /></form></div></a>
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
