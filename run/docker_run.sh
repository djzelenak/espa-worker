#!/bin/bash

docker run --rm -it \
--mount type=bind,source=${AUX_ROOT_DIR},destination=/usr/local/auxiliaries,readonly \
--mount type=bind,source=${ESPA_STORAGE},destination=/espa-storage \
--mount type=bind,source=${ESPA_ORDERS},destination=/espa-storage/orders \
usgseros/espa-worker:0.0.1