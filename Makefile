.PHONY: help lint-tools test-tools example-tools lint pylint ruff test coverage examples build clean

PYTHON ?= python3
PACKAGE := linkbudget
EXAMPLE_OUT := examples/example_outputs

help:
	@echo "Targets:"
	@echo "  lint-tools    Install linting/build tooling (ruff, pylint, build)"
	@echo "  test-tools    Install test tooling (pytest, pytest-cov, matplotlib)"
	@echo "  example-tools Install what the examples need (matplotlib)"
	@echo "  ruff          Run 'ruff check' on the package"
	@echo "  pylint        Run pylint on the package"
	@echo "  lint          Run both ruff and pylint"
	@echo "  test          Run the pytest suite (writes an HTML coverage report to coverage/)"
	@echo "  coverage      Run the pytest suite with a detailed terminal + HTML coverage report"
	@echo "  examples      Run every example, writing outputs to $(EXAMPLE_OUT)/"
	@echo "  build         Build the sdist and wheel into dist/"
	@echo "  clean         Remove build, test and example-output artifacts"

lint-tools:
	$(PYTHON) -m pip install ruff pylint build

test-tools:
	$(PYTHON) -m pip install pytest pytest-cov matplotlib

example-tools:
	$(PYTHON) -m pip install matplotlib

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

build: clean
	$(PYTHON) -m build

clean:
	rm -rf dist build $(PACKAGE).egg-info .pytest_cache .coverage coverage htmlcov $(EXAMPLE_OUT)
	find . -type d -name __pycache__ -exec rm -rf {} +
