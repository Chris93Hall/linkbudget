.PHONY: help lint-tools test-tools example-tools docs-tools lint pylint ruff test coverage examples docs docs-serve build clean

PYTHON ?= python3
PACKAGE := linkbudget
EXAMPLE_OUT := examples/example_outputs
DOCS_ADDR ?= 0.0.0.0:8000

help:
	@echo "Targets:"
	@echo "  lint-tools    Install linting/build tooling (ruff, pylint, build)"
	@echo "  test-tools    Install test tooling (pytest, pytest-cov, matplotlib)"
	@echo "  example-tools Install what the examples need (matplotlib)"
	@echo "  docs-tools    Install docs tooling (mkdocs, mkdocs-material, mkdocstrings)"
	@echo "  ruff          Run 'ruff check' on the package"
	@echo "  pylint        Run pylint on the package"
	@echo "  lint          Run both ruff and pylint"
	@echo "  test          Run the pytest suite (writes an HTML coverage report to coverage/)"
	@echo "  coverage      Run the pytest suite with a detailed terminal + HTML coverage report"
	@echo "  examples      Run every example, writing outputs to $(EXAMPLE_OUT)/"
	@echo "  docs          Build the documentation site into site/"
	@echo "  docs-serve    Serve the documentation on $(DOCS_ADDR) (override with DOCS_ADDR=)"
	@echo "  build         Build the sdist and wheel into dist/"
	@echo "  clean         Remove build, test, docs and example-output artifacts"

lint-tools:
	$(PYTHON) -m pip install ruff pylint build

test-tools:
	$(PYTHON) -m pip install pytest pytest-cov matplotlib

example-tools:
	$(PYTHON) -m pip install matplotlib

docs-tools:
	$(PYTHON) -m pip install mkdocs mkdocs-material 'mkdocstrings[python]'

ruff:
	$(PYTHON) -m ruff check $(PACKAGE)

pylint:
	$(PYTHON) -m pylint $(PACKAGE)

lint: ruff pylint

test:
	$(PYTHON) -m pytest --cov=$(PACKAGE) --cov-report=term --cov-report=html:coverage

coverage:
	$(PYTHON) -m pytest --cov=$(PACKAGE) --cov-report=term-missing --cov-report=html:coverage
	@echo "\nHTML coverage report: coverage/index.html"

examples:
	@mkdir -p $(EXAMPLE_OUT)
	@for example in examples/*.py; do \
		case "$$example" in examples/_*) continue;; esac; \
		echo "=== $$example ==="; \
		PYTHONPATH="$(CURDIR)" $(PYTHON) "$$example" || exit 1; \
	done
	@echo "\nexample outputs written to $(EXAMPLE_OUT)/"

docs:
	$(PYTHON) -m mkdocs build --strict

docs-serve:
	$(PYTHON) -m mkdocs serve --dev-addr $(DOCS_ADDR)

build: clean
	$(PYTHON) -m build

clean:
	rm -rf dist build site $(PACKAGE).egg-info .pytest_cache .ruff_cache .coverage coverage htmlcov $(EXAMPLE_OUT)
	find . -type d -name __pycache__ -exec rm -rf {} +
