#!/bin/bash 

# dataset scale: $1
# worker number: $1 

echo "args are $1 $2"

/usr/src/memcached/memcached_client/loader \
    -a /usr/src/memcached/twitter_dataset/twitter_dataset_unscaled \
    -o /usr/src/memcached/twitter_dataset/twitter_dataset_{$1}x \
    -s /usr/src/memcached/memcached_client/servers.txt \
    -w $2 -S $2 -D 2048 -j

/usr/src/memcached/memcached_client/loader \
    -a /usr/src/memcached/twitter_dataset/twitter_dataset_{$1}x \
    -s /usr/src/memcached/memcached_client/servers.txt \
    -g 0.8 -c 200 -w $2 -e -r 1800 -T 1
