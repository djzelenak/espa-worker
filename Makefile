TAG=dev_v0.0.1

docker-build:
	docker build -t usgseros/espa-worker:${TAG} .
