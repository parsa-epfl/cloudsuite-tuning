#!/bin/bash

set -e

source $1

OUTPUT_FILE=$EXPERIMENT_ID.txt
CLIENT_NAME=dc-client-$EXPERIMENT_ID
SERVER_NAME=dc-server-$EXPERIMENT_ID
SERVER_THREADS=$((`echo $SERVER_CPU_SET | tr -cd , | wc -c` + 1))
CLIENT_THREADS=$((`echo $CLIENT_CPU_SET | tr -cd , | wc -c` + 1))

echo cpu_set: $SERVER_CPU_SET > $OUTPUT_FILE
echo memory_size: $SERVER_MEMORY >> $OUTPUT_FILE
echo server_cpu_count: $SERVER_THREADS >> $OUTPUT_FILE
echo client_cpu_count: $CLIENT_THREADS >> $OUTPUT_FILE

ssh $SERVER_ADDRESS docker stop $SERVER_NAME || true
ssh $SERVER_ADDRESS docker rm $SERVER_NAME || true
ssh $SERVER_ADDRESS docker run -d --cpuset-cpus $SERVER_CPU_SET  --name $SERVER_NAME -p $SERVER_PORT:$SERVER_PORT -d $SERVER_IMAGE -t $SERVER_THREADS -m $SERVER_MEMORY -n $KEY_LENGTH

docker stop $CLIENT_NAME || true
docker rm $CLIENT_NAME || true
docker run --cpuset-cpus $CLIENT_CPU_SET -d --network=host --name $CLIENT_NAME $CLIENT_IMAGE bash -c 'cd /usr/src/memcached/memcached_client/; \
    echo '$SERVER_ADDRESS', 11211 > docker_servers.txt; \
    ./loader -a ../twitter_dataset/twitter_dataset_unscaled -o ../twitter_dataset/twitter_dataset_30x -s docker_servers.txt -w '$CLIENT_THREADS' -S '$SCALE_FACTOR' -D '$SERVER_MEMORY' -j -T 1; \
    while true; do sleep 100; done;'

while ! docker logs $CLIENT_NAME 2>&1 | grep -q 'warmed up' &>/dev/null; do sleep 5; echo Waiting to be warmed up!; done;
echo Warmed up!

for i in `seq $START_LOAD $LOAD_STEP $END_LOAD | shuf`; do
	echo rps: $i >> $OUTPUT_FILE;
	docker exec -i $CLIENT_NAME bash -c "cd /usr/src/memcached/memcached_client/; \
		./loader -a ../twitter_dataset/twitter_dataset_30x -s docker_servers.txt -g 0.8 -T 1 -c 200 -w $CLIENT_THREADS -e -r $i" &>> $OUTPUT_FILE &
    EXEC_TO_KILL=$!
	sleep $SLEEP_TIME;
	docker exec $CLIENT_NAME bash -c "pkill loader"
	kill -9 $EXEC_TO_KILL
    ssh $SERVER_ADDRESS $MPSTAT_COMMAND >> $OUTPUT_FILE
done;