TAG_BASE=el7_base-alpha.3
TAG_ESPA=2.35.0-el7-beta.5

docker-build-base:
	docker build -t usgseros/espa-worker:${TAG_BASE} -f Dockerfile.el7_base .

docker-build-espa:
	docker build -t usgseros/espa-worker:${TAG_ESPA} -f Dockerfile.espa .
