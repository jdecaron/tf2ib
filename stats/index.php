<h1></h1>
<?php
error_reporting(E_ERROR);

// TF2 Log Parser
// file: list.php
// author: rusty fausak
// date: dec 15 2007
// rev: v1.1 dec 18 2007
// desc: This file scans $_GET['dir'] or the current directory and prints a
//       formatted list that has all folders containing a 'log.log' file in
//       them. It does not recurse to subdirectories.
//       v1.1: Added paging through $_GET['sel'] to signify the selection.

include 'database.php';
include 'page.php';

$database = new Database();
$search = $_REQUEST['search'];
if($search == ''){
    $search = date('m\/Y');
}
$search = $database->sqlEscapeString($search);

foreach(explode(" ", $search) as $searchString){
    if($searchString == ''){
        continue;
    }
    $escapedSearchString = $database->sqlEscapeString($searchString);
    //echo "<pre>";
    $results = $database->queryAssoc("SELECT * FROM statsIndex WHERE id like '%$escapedSearchString%'");
    //echo "SELECT * FROM statsIndex WHERE id like '%$escapedSearchString%'";
    foreach($results as $result){
        foreach($files = explode(":", $result['files']) as $file){
            $fileIndex[$file]++;
            $keywordsMatched[$file][] = $escapedSearchString;
        }
    }
    //print_r($results);
    //echo "</pre>";
}
arsort($fileIndex);
//echo "<pre>";
foreach($fileIndex as $file => $group){
    $explodedFile = explode("_", $file);
    $indexGroup[$group][$file] = (int)$explodedFile[1];
}
unset($fileIndex);
$sortedIndexGroup = array();
foreach($indexGroup as $matchedKeywords => $group){
    $groupCount[] = array($matchedKeywords, count($group));
    arsort($group);
    $sortedIndexGroup = array_merge($sortedIndexGroup, $group);
}
//var_dump($sortedIndexGroup);
//echo "</pre>";

// Global variables
$html = '';
$dir = '.';
if ($_GET['dir']) { $dir = $_GET['dir']; }
$sel = date("ny",time());
if ($_GET['sel']) { $sel = $_GET['sel']; }
$files = scandir($dir);
$char = 'a';
$list = array();

//var_dump($indexGroup);
// HTML Output

$html = <<<EOT
<div class='contentheader'>List</div>
<table class='maintable'>
<tr>
	<th align=left width=250px>Date</th>
	<th align=left>Stats (map_server)</th>
	<th align=left>Keywords matched</th>
</tr>
EOT;

$counter = 0;
$groupCountIndex = 0;
foreach ($sortedIndexGroup as $key => $val){
    $date = date('j\/m\/Y H:i:s', $val);
    $explodedFileName = explode('_', $key);
    $mapName = $explodedFileName[2] . '_' . $explodedFileName[0];
    if($groupCount[$groupCountIndex][1] - 1 < $counter){
        $groupCountIndex++;
        $counter = 0;
    }
    $matchedKeywords = implode(', ', $keywordsMatched[$key]);
    $counter++;
	$html .= <<<EOT
<tr class='tr{$tmp}'>
	<td>{$date}</td>
	<td><a href='./log/{$key}'>{$mapName}</a></td>
	<td>{$matchedKeywords}</td>
</tr>
EOT;
}

$html .= <<<EOT
</table><br>
<center>
EOT;

// Output month/year choices
foreach ((is_array($pos)?$pos:array()) as $key => $val) {
	$html .= "<a href='?sel={$key}'>{$val}</a> - ";
}
$html = substr($html, 0, -3);

$html .= <<<EOT
</center>
EOT;

// Create the page through page.php
make_page($html,$nav);

?>
