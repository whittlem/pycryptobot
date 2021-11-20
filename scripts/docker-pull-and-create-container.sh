#!/bin/bash

# full path of file
full=`realpath $0`
# remove the file name e.g. file.sh
directory=`dirname $full`
# just the file name
filename=`basename $0`
# now remove the extension
filenameminussh=${filename%.*}
# convert to upper case
# this is our docker name
dockername=${filenameminussh^^}

docker pull ghcr.io/whittlem/pycryptobot/pycryptobot:latest
docker stop $dockername
docker rm $dockername

docker create \
  --name=$dockername \
  -v $directory/config.json:/app/config.json \
  -v $directory/coinbase.key:/app/coinbase.key \
  --restart unless-stopped \
  ghcr.io/whittlem/pycryptobot/pycryptobot:latest \
  --market $dockername --buymaxsize 10

docker start $dockername