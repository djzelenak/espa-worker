#!/bin/bash

if [ -e ${HOME}/src/espa-worker/run/env.sh ]
then
    source ${HOME}/src/espa-worker/run/env.sh
else
    [ -z "$AUX_ROOT_STORAGE" ] && { echo "Need to set AUX_ROOT_DIR"; exit 1; }
    [ -z "$DATA_DIR" ] && { echo "Need to set DATA_DIR"; exit 1; }
fi

docker run --rm -it \
--mount type=bind,source=${AUX_ROOT_STORAGE},destination=/usr/local/auxiliaries,readonly \
--mount type=bind,source=${ESPA_STORAGE},destination=/espa-storage/orders \
--user espa \
usgseros/espa-worker:0.0.2
