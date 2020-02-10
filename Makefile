.PHONY: build tests docs deploy build_base test_base deploy_base build_builder test_builder deploy_builder build_worker test_worker deploy_worker tag login debug all

.DEFAULT_GOAL := build
VERSION    := $(shell cat version.txt)
IMAGE      := $(or $(CI_REGISTRY_IMAGE), lsrd/espa-worker)
BRANCH     := $(or $(CI_COMMIT_REF_NAME), $(shell git rev-parse --abbrev-ref HEAD))
BRANCH     := $(shell echo $(BRANCH) | tr / -)
SHORT_HASH := $(shell git rev-parse --short HEAD)
TAG        := $(IMAGE):$(BRANCH)-$(VERSION)-$(SHORT_HASH)
BASE_DIR   := $(PWD)/docker_base
BUILD_DIR  := $(PWD)/docker_build
WORKER_DIR := $(PWD)/docker_worker
BASE_TAG   := $(IMAGE):base-$(VERSION)-$(SHORT_HASH)
BASE_TAG_LATEST := $(IMAGE):base-latest
BUILD_TAG  := $(IMAGE):builder-$(VERSION)-$(SHORT_HASH)
BUILD_TAG_LATEST := $(IMAGE):builder-latest
WORKER_TAG := $(IMAGE):worker-$(VERSION)-$(SHORT_HASH)
WORKER_TAG_LATEST := $(IMAGE):worker-latest

build: build_base build_builder build_worker

tests: test_base test_build test_worker

docs:

deploy: deploy_base deploy_builder deploy_worker


# Base OS Targets
build_base:
	@docker build -t $(BASE_TAG) --rm=true --compress $(PWD) -f $(BASE_DIR)/Dockerfile.base
	@docker tag $(BASE_TAG) $(BASE_TAG_LATEST)

test_base:

deploy_base: login
	docker push $(BASE_TAG)
	docker push $(BASE_TAG_LATEST)

# Build environment targets
build_builder: login
	@docker build -t $(BUILD_TAG) --rm=true --compress $(PWD) -f $(BUILD_DIR)/Dockerfile.build
	@docker tag $(BUILD_TAG) $(BUILD_TAG_LATEST)

test_builder:

deploy_builder: login
	docker push $(BUILD_TAG)
	docker push $(BUILD_TAG_LATEST)

# Worker environment targets
build_worker: login
	docker build -t $(WORKER_TAG) --rm=true --compress --build-arg SSH_PRIVATE_KEY="$$SSH_PRIVATE_KEY" \
	--build-arg SSH_KNOWN_HOSTS="$$SSH_KNOWN_HOSTS" \
	$(PWD) -f $(WORKER_DIR)/Dockerfile.worker
	@docker tag $(WORKER_TAG) $(WORKER_TAG_LATEST)

test_worker: login
	@docker run --rm $(WORKER_TAG) /bin/bash -c "cd /home/espa/espa-processing && nose2 --fail-fast --with-coverage --log-level=error"

deploy_worker: login
	docker push $(WORKER_TAG)
	docker push $(WORKER_TAG_LATEST)

login:
	@$(if $(and $(CI_REGISTRY_USER), $(CI_REGISTRY_PASSWORD)), \
          docker login  -u $(CI_REGISTRY_USER) \
                        -p $(CI_REGISTRY_PASSWORD) \
                         $(CI_REGISTRY), \
          docker login)

debug:
	@echo "VERSION:   $(VERSION)"
	@echo "IMAGE:     $(IMAGE)"
	@echo "BRANCH:    $(BRANCH)"
	@echo "TAG:       $(TAG)"

all: debug build tests docs deploy
