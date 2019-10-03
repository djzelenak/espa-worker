SYSTEM=el6
VERSION=1.0.11_beta

docker-build:
	docker build -t usgseros/espa-worker:${SYSTEM}_${VERSION} .
