SYSTEM=el6
VERSION=1.2.1

docker-build:
	docker build -t usgseros/espa-worker:${SYSTEM}_${VERSION} .
