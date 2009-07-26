#!/bin/bash
cd /usr/local/games/steam/orangebox/tf
for i in `find -maxdepth 1 -name "*\.dem"`
do
    if test -z `fuser $i`
    then
        mv $i ./demos
        rsync -a ./demos/ tf2pug@tf2pug.org:~/demos.tf2pug.org
    fi
done
