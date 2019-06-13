#!/bin/bash

if [ -e ${HOME}/src/espa-worker/run/env.sh ]
then
    source ${HOME}/src/espa-worker/run/env.sh
else
    [ -z "$AUX_ROOT_STORAGE" ] && { echo "Need to set AUX_ROOT_DIR"; exit 1; }
    [ -z "$ESPA_STORAGE" ] && { echo "Need to set ESPA_STORAGE"; exit 1; }
    [ -z "$ESPA_ORDERS" ] && { echo "Need to set ESPA_ORDERS"; exit 1; }
fi

docker run --rm -it \
--mount type=bind,source=${AUX_ROOT_STORAGE},destination=/usr/local/auxiliaries,readonly \
--mount type=bind,source=${ESPA_STORAGE},destination=/espa-storage \
--mount type=bind,source=${ESPA_ORDERS},destination=/espa-storage/orders \
usgseros/espa-worker:0.0.1
