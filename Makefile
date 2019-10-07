SYSTEM=el6
VERSION=1.2.0

docker-build:
	docker build -t usgseros/espa-worker:${SYSTEM}_${VERSION} .
