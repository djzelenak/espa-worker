TAG=0.0.2
IMAGE=usgseros/espa-worker:${TAG}

docker-build:
	docker build -t ${IMAGE} .
