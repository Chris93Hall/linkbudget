.PHONY: help lint-tools lint pylint ruff build clean

PYTHON ?= python3
PACKAGE := linkbudget

help:
	@echo "Targets:"
	@echo "  lint-tools  Install linting/build tooling (ruff, pylint, build)"
	@echo "  ruff        Run 'ruff check' on the package"
	@echo "  pylint      Run pylint on the package"
	@echo "  lint        Run both ruff and pylint"
	@echo "  build       Build the sdist and wheel into dist/"
	@echo "  clean       Remove build artifacts"

lint-tools:
	$(PYTHON) -m pip install ruff pylint build

ruff:
	$(PYTHON) -m ruff check $(PACKAGE)

pylint:
	$(PYTHON) -m pylint $(PACKAGE)

lint: ruff pylint

build: clean
	$(PYTHON) -m build

clean:
	rm -rf dist build $(PACKAGE).egg-info
