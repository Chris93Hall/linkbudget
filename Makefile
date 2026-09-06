.PHONY: help lint-tools test-tools lint pylint ruff test coverage build clean

PYTHON ?= python3
PACKAGE := linkbudget

help:
	@echo "Targets:"
	@echo "  lint-tools  Install linting/build tooling (ruff, pylint, build)"
	@echo "  test-tools  Install test tooling (pytest, pytest-cov)"
	@echo "  ruff        Run 'ruff check' on the package"
	@echo "  pylint      Run pylint on the package"
	@echo "  lint        Run both ruff and pylint"
	@echo "  test        Run the pytest suite"
	@echo "  coverage    Run the pytest suite with a coverage report"
	@echo "  build       Build the sdist and wheel into dist/"
	@echo "  clean       Remove build and test artifacts"

lint-tools:
	$(PYTHON) -m pip install ruff pylint build

test-tools:
	$(PYTHON) -m pip install pytest pytest-cov

ruff:
	$(PYTHON) -m ruff check $(PACKAGE)

pylint:
	$(PYTHON) -m pylint $(PACKAGE)

lint: ruff pylint

test:
	$(PYTHON) -m pytest

coverage:
	$(PYTHON) -m pytest --cov=$(PACKAGE) --cov-report=term-missing

build: clean
	$(PYTHON) -m build

clean:
	rm -rf dist build $(PACKAGE).egg-info .pytest_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
