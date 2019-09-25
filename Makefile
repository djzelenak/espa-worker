SYSTEM=el6
VERSION=0.1.0

docker-build:
	docker build -t usgseros/espa-worker:${SYSTEM}_${VERSION} .
