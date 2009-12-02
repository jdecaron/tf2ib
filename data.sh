#!/bin/bash
cd /usr/local/games/steam/orangebox/tf
for i in `find -maxdepth 1 -name "*\.dem"`
do
    if test -z `fuser $i`
    then
        mv $i ./demos
    fi
done
rsync -a --bwlimit=600 ./demos/ tf2pug@tf2pug.org:~/demos.tf2pug.org
rsync -a --bwlimit=600 ./logs/ tf2pug@tf2pug.org:~/stats.tf2pug.org/logs
