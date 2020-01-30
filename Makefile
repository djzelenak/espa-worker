.PHONY: build tests docs deploy tag login debug all

.DEFAULT_GOAL := build
VERSION    := 0.0.1
IMAGE      := $(or $(CI_REGISTRY_IMAGE), lsrd/espa-worker)
BRANCH     := $(or $(CI_COMMIT_REF_NAME),`git rev-parse --abbrev-ref HEAD`)
BRANCH     := $(shell echo $(BRANCH) | tr / -)
SHORT_HASH := `git rev-parse --short HEAD`
TAG        := $(IMAGE):$(BRANCH)-$(VERSION)-$(SHORT_HASH)
BASE_DIR   := $(PWD)/base
EXTERNAL_DIR := $(PWD)/external
SCIENCE_DIR := $(PWD)/science
BASE_6_IMAGE := $(IMAGE)/centos6
BASE_7_IMAGE := $(IMAGE)/centos7
BASE_6_TAG := $(BASE_6_IMAGE):$(VERSION)-$(SHORT_HASH)
BASE_7_TAG := $(BASE_7_IMAGE):$(VERSION)-$(SHORT_HASH)

build:
	@docker build -t $(TAG) --rm=true --compress $(PWD)

tests:

docs:

deploy: login
	docker push $(IMAGE)
	docker push $(TAG)


# Extra Makefile targets. Edit at will.


build_base: build_base_6 build_base_7

build_base_6:
	@docker build -t $(BASE_6_TAG) --rm=true --compress $(PWD) -f $(BASE_DIR)/Dockerfile.centos6

build_base_7:
	@docker build -t $(BASE_7_TAG) --rm=true --compress $(PWD) -f $(BASE_DIR)/Dockerfile.centos7

deploy_base: deploy_base_6 deploy_base_7

deploy_base_6: login
	docker push $(BASE_6_IMAGE)
	docker push $(BASE_6_TAG)

deploy_base_7: login
	docker push $(BASE_7_IMAGE)
	docker push $(BASE_7_TAG)

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
