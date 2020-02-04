.PHONY: build tests docs deploy build_base test_base deploy_base build_external test_external deploy_external tag login debug all

.DEFAULT_GOAL := build
VERSION    := `cat version.txt`
IMAGE      := $(or $(CI_REGISTRY_IMAGE), lsrd/espa-worker)
BRANCH     := $(or $(CI_COMMIT_REF_NAME), `git rev-parse --abbrev-ref HEAD`)
BRANCH     := $(shell echo $(BRANCH) | tr / -)
SHORT_HASH := `git rev-parse --short HEAD`
TAG        := $(IMAGE):$(BRANCH)-$(VERSION)-$(SHORT_HASH)
BASE_DIR   := $(PWD)/docker_base
EXTERNAL_DIR := $(PWD)/docker_build
WORKER_DIR := $(PWD)/docker_worker
BASE_TAG := $(IMAGE):base-$(VERSION)-$(SHORT_HASH)
BASE_TAG_LATEST := $(IMAGE):base-latest
BUILDER_TAG := $(IMAGE):builder-$(VERSION)-$(SHORT_HASH)
BUILDER_TAG_LATEST := $(IMAGE):builder-latest
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
	@docker build -t $(BUILDER_TAG) --rm=true --compress $(PWD) -f $(BUILDER_DIR)/Dockerfile.build
	@docker tag $(BUILDER_TAG) $(BUILDER_TAG_LATEST)

test_builder:

deploy_builder: login
	docker push $(BUILDER_TAG)
	docker push $(BUILDER_TAG_LATEST)

# Worker environment targets
build_worker: login
	@docker build -t $(WORKER_TAG) --rm=true --compress --build-arg SSH_PRIVATE_KEY=$(SSH_PRIVATE_KEY) $(PWD) -f $(WORKER_DIR)/Dockerfile
	@docker tag $(WORKER_TAG) $(WORKER_TAG_LATEST)

test_worker:

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
