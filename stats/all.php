<?php

// TF2 Log Parser
// file: upload.php
// author: rusty fausak
// date: dec 18 2007
// rev: v1.0 dec 18 2007
// desc: This file has a form for users to upload a .log file. This page checks
//       the uploaded file to confim it's properties. Then it uploads the file
//       to its own directory and runs the tf2 log parser on it.

if ($_SERVER['SERVER_ADDR'] !=  $_SERVER['REMOTE_ADDR']){
        echo 'Exit!';
        exit();
}

include 'database.php';
include 'parser.php';

$database = new Database();

exec('ls -t ~/stats.tf2pug.org/logs/ | grep -v \'L.*[0-9]\.log\' | head -n100', $latestFiles);
foreach($latestFiles as $fileName){
    $explodedFileName = explode(".", $fileName);
    $explodedFileName = $database->sqlEscapeString($explodedFileName);
    if(count($explodedFileName) == 2 && $explodedFileName[1] == log && filesize('./logs/' . $fileName) > 20000){
        exec('grep \' tv_record \' ~/stats.tf2pug.org/logs/' . $fileName, $mapName);
        $mapName = explode(" ", $mapName[0]);
        $mapName = explode("_", $mapName[count($mapName) - 1]);
        $logDate = $mapName[0];
        $mapName = $mapName[4];
        if($mapName){
            $logDate = str_replace('h', ':', $logDate);
            $logDate = str_replace('m', '', $logDate);
            $logDate = strtotime($logDate);
            $server = explode("_", $explodedFileName[0]);
            $server = $server[0];
            $newFileName = $server . '_' . $logDate . '_' . $mapName;
            if( !$database->queryAssoc("SELECT * FROM files WHERE fileName = '$newFileName'")){
                $directory = './log/' . $newFileName;
                $newFileName = $newFileName . '.log';
                mkdir($directory);
                copy('./logs/' . $fileName, $directory . '/' . $newFileName);
                if(!parse($directory, 'ready')){
                    unlink($directory . '/' . $newFileName);
                    rmdir($directory);
                }
            }
            unset($logDate);
        }
    }
}
?>
