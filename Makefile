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
EXTERNAL_TAG := $(IMAGE):external-$(VERSION)-$(SHORT_HASH)
EXTERNAL_TAG_LATEST := $(IMAGE):external-latest
SCIENCE_TAG := $(IMAGE):science-$(VERSION)-$(SHORT_HASH)
SCIENCE_TAG_LATEST := $(IMAGE):science-latest

build: build_base build_external build_science

tests: test_base test_external test_science

docs:

deploy: deploy_base deploy_external deploy_science


# Extra Makefile targets. Edit at will.


build_base:
	@docker build -t $(BASE_TAG) --rm=true --compress $(PWD) -f $(BASE_DIR)/Dockerfile.base
	@docker tag $(BASE_TAG) $(BASE_TAG_LATEST)

test_base:

deploy_base: login
	docker push $(BASE_TAG)
	docker push $(BASE_TAG_LATEST)

build_external: login
	@docker build -t $(EXTERNAL_TAG) --rm=true --compress $(PWD) -f $(EXTERNAL_DIR)/Dockerfile.build
	@docker tag $(EXTERNAL_TAG) $(EXTERNAL_TAG_LATEST)

test_external:

deploy_external: login
	docker push $(EXTERNAL_TAG)
	docker push $(EXTERNAL_TAG_LATEST)

build_science: login
	@docker build -t $(SCIENCE_TAG) --rm=true --compress --build-arg SSH_PRIVATE_KEY=$(SSH_PRIVATE_KEY) $(PWD) -f $(SCIENCE_DIR)/Dockerfile.centos7
	@docker tag $(SCIENCE_TAG) $(SCIENCE_TAG_LATEST)

test_science:

deploy_science: login
	docker push $(SCIENCE_TAG)
	docker push $(SCIENCE_TAG_LATEST)

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
