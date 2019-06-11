#!/bin/bash

docker run --rm -it \
--mount type=bind,source=/usr/local/auxiliaries,destination=/usr/local/auxiliaries,readonly \
--mount type=bind,source=/data2/dzelenak/espa-storage,destination=/espa-storage \
--mount type=bind,source=/data2/dzelenak/espa-storage/orders,destination=/espa-storage/orders \
usgseros/espa-worker:0.0.1