TAG=0.0.1
IMAGE=espa-worker:${TAG}

docker-build:
	docker build -t ${IMAGE} .
