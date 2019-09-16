TAG_BASE=el7_base-alpha.1
TAG_ESPA=2.35.0-el7-beta.3

docker-build-base:
    docker build -t usgseros/espa-worker:${TAG_BASE} -f Dockerfile.el7 .

docker-build-espa:
	docker build -t usgseros/espa-worker:${TAG_ESPA} -f Dockerfile.espa .
