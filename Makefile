TAG=2.35.0-el7-beta.1

docker-build:
	docker build -t usgseros/espa-worker:${TAG} -f Dockerfile.espa .
