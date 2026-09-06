# Installation

`linkbudget` is packaged with a standard `pyproject.toml` (setuptools
backend).

```bash
git clone https://github.com/Chris93Hall/linkbudget
cd linkbudget
pip install .          # regular install
pip install -e .       # editable install, for local development
```

This pulls in `numpy` and `fpdf2`.

## Optional extras

| Extra | Adds | Needed for |
|---|---|---|
| `linkbudget[plot]` | `matplotlib` | [`WaterfallPublisher`](guide/publishers.md#waterfallpublisher) |
| `linkbudget[test]` | `pytest`, `pytest-cov`, `matplotlib` | running the test suite |
| `linkbudget[docs]` | `mkdocs`, `mkdocs-material`, `mkdocstrings` | building this site |

```bash
pip install -e '.[plot]'
```

## Requirements

- Python 3.8 or newer
- `numpy >= 1.21.5`
- `fpdf2 >= 2.8.1` (for [`PDFPublisher`](guide/publishers.md#pdfpublisher))

## Building distributable artifacts

```bash
pip install build
python -m build          # writes a wheel + sdist to dist/
```

## Developer tasks

The `Makefile` wraps the common workflows:

```bash
make test        # pytest + an HTML coverage report in coverage/
make lint        # ruff + pylint
make examples    # run every example, outputs to examples/example_outputs/
make docs        # build this site into site/
make docs-serve  # serve it locally with live reload
```
