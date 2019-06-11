#!/bin/bash 
# set -x 

source ../common/safeguard
source main_func

(($DEV)) && echo "server cpus $SERVER_CPUS"

# create_dataset 
create_network 
start_server

while read OPERATIONS; do 
    clean_containers $CLIENT_CONTAINER
    start_client &  

    detect_stage warmup
    (($DEV)) && echo "warmup ready"
    sudo perf stat -e $PERF_EVENTS --cpu $SERVER_CPUS -p $SERVER_PIDS sleep $MEASURE_TIME 2>$PERF_LOG

    docker stop $CLIENT_CONTAINER
    log_client 
    # _summary 
    cp user.cfg $OUT/user.cfg 
    log_folder
done < $OPERATIONS_FILE
