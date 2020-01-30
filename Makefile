.PHONY: build tests docs deploy build_base test_base deploy_base build_external test_external deploy_external tag login debug all

.DEFAULT_GOAL := build
VERSION    := 0.0.1
IMAGE      := $(or $(CI_REGISTRY_IMAGE), lsrd/espa-worker)
BRANCH     := $(or $(CI_COMMIT_REF_NAME), `git rev-parse --abbrev-ref HEAD`)
BRANCH     := $(shell echo $(BRANCH) | tr / -)
SHORT_HASH := `git rev-parse --short HEAD`
TAG        := $(IMAGE):$(BRANCH)-$(VERSION)-$(SHORT_HASH)
BASE_DIR   := $(PWD)/base
EXTERNAL_DIR := $(PWD)/external
SCIENCE_DIR := $(PWD)/science
BASE_TAG := $(IMAGE):base-$(VERSION)-$(SHORT_HASH)
BASE_TAG_LATEST := $(IMAGE):espa-base
EXTERNAL_TAG := $(IMAGE):external-$(VERSION)-$(SHORT_HASH)
EXTERNAL_TAG_LATEST := $(IMAGE):espa-external

build: build_base build_external

tests: test_base test_external

docs:

deploy: deploy_base deploy_external


# Extra Makefile targets. Edit at will.


build_base:
	@docker build -t $(BASE_TAG) --rm=true --compress $(PWD) -f $(BASE_DIR)/Dockerfile.centos7
	@docker tag $(BASE_TAG) $(BASE_TAG_LATEST)

test_base:

deploy_base: login
	docker push $(BASE_TAG)
	docker push $(BASE_TAG_LATEST)

build_external:
	@docker build -t $(EXTERNAL_TAG) --rm=true --compress $(PWD) --build-arg image=$(BASE_TAG_LATEST) -f $(EXTERNAL_DIR)/Dockerfile.centos7
	@docker tag $(EXTERNAL_TAG) $(EXTERNAL_TAG_LATEST)

test_external:

deploy_external: login
	docker push $(EXTERNAL_TAG)
	docker push $(EXTERNAL_TAG_LATEST)



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
