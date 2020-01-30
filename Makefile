.PHONY: build tests docs deploy tag login debug all

.DEFAULT_GOAL := build
VERSION    := 0.0.1
IMAGE      := ***REMOVED***/$(CI_PROJECT_PATH)
BRANCH     := $(or $(CI_COMMIT_REF_NAME),`git rev-parse --abbrev-ref HEAD`)
BRANCH     := $(shell echo $(BRANCH) | tr / -)
SHORT_HASH := `git rev-parse --short HEAD`
TAG        := $(IMAGE):$(BRANCH)-$(VERSION)-$(SHORT_HASH)

# ESPA Standard Makefile targets.  Do not remove.

build:
	@docker build -t $(TAG) --rm=true --compress $(PWD)

tests:

docs:

deploy: login
	docker push $(IMAGE)
	docker push $(TAG)


# Extra Makefile targets. Edit at will.


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
