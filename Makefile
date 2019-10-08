SYSTEM=el6
VERSION=1.2.2

docker-build:
	docker build -t usgseros/espa-worker:${SYSTEM}_${VERSION} .
