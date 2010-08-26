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
    # Backup the demo files that are done recording.
    if test -z `fuser $i`
    then
        mv $i ./demos
    fi
done
for i in `find ./logs -name '*.log' | grep 'L.*[0-9]\.log'`;
do
    # Verify if the file is open by the server proccess and prepend the server name to the logs
    # to guarantee that they have unique files names in the stats page.
    if test -z `fuser $i`
    then
        j=`echo $i | cut -dL -f2`;
        mv $i ./logs/'dallas3_'$j;
    fi
done
rsync -a --bwlimit=600 --max-size=30000000 ./demos/ tf2pug@tf2pug.org:~/demos.tf2pug.org
rsync -a --bwlimit=600 --max-size=30000000 ./logs/ tf2pug@tf2pug.org:~/stats.tf2pug.org/logs
for i in `find ./demos/ -maxdepth 1 -type f -mtime +1`; do rm $i; done
for i in `find ./logs/ -maxdepth 1 -type f -mtime +30`; do rm $i; done
rm /tmp/tf2pb
