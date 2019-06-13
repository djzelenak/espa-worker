TAG=0.0.1
IMAGE=usgseros/espa-worker:${TAG}

docker-build:
	docker build -t ${IMAGE} .
