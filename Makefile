PYTHON ?= python3
UV ?= uv
SITE_CONFIG := build/mkdocs.yml
SYNC_CONFIG := external-content.toml
SYNC_MANIFEST := build/.external-content-manifest.json

.PHONY: all prepare sync build-site serve clean

all: build-site

prepare:
	$(PYTHON) scripts/prepare_build.py

sync: prepare
	$(PYTHON) scripts/sync_external_content.py $(SYNC_CONFIG) --target-root build --manifest-path $(SYNC_MANIFEST)

build-site: sync
	$(UV) run zensical build -f $(SITE_CONFIG)

serve: sync
	$(UV) run zensical serve -f $(SITE_CONFIG)

clean:
	rm -rf build .cache
