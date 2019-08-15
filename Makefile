TAG=devtest

docker-build:
	docker build -t usgseros/espa-worker:${TAG} .
