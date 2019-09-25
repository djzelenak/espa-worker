SYSTEM=el6
VERSION=1.0.1

docker-build:
	docker build -t usgseros/espa-worker:${SYSTEM}_${VERSION} .
