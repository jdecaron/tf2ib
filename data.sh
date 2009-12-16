#!/bin/bash
if [ -f /tmp/tf2pb ]
then
    # Run only one instance of the script on the host.
    exit
fi
touch /tmp/tf2pb
cd /usr/local/games/steam/orangebox/tf
for i in `find -maxdepth 1 -name "*\.dem"`
do
    if test -z `fuser $i`
    then
        mv $i ./demos
    fi
done
rsync -a --bwlimit=600 --max-size=30000000 ./demos/ tf2pug@tf2pug.org:~/demos.tf2pug.org
rsync -a --bwlimit=600 --max-size=30000000 ./logs/ tf2pug@tf2pug.org:~/stats.tf2pug.org/logs
for i in `find ./demos/ -maxdepth 1 -type f -mtime +1`; do rm $i; done
for i in `find ./logs/ -maxdepth 1 -type f -mtime +1`; do rm $i; done
rm /tmp/tf2pb
