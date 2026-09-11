# Installation

```bash
pip install linkbudget-rf
```

The PyPI distribution is named **`linkbudget-rf`** (the bare `linkbudget` name
was already taken); the import name is still `linkbudget`. It pulls in `numpy`
and `fpdf2`.

## From source

```bash
git clone https://github.com/Chris93Hall/linkbudget
cd linkbudget
pip install .          # regular install
pip install -e .       # editable install, for local development
```

## Optional extras

| Extra | Adds | Needed for |
|---|---|---|
| `linkbudget-rf[plot]` | `matplotlib` | [`WaterfallPublisher`](guide/publishers.md#waterfallpublisher) |
| `linkbudget-rf[test]` | `pytest`, `pytest-cov`, `matplotlib` | running the test suite |
| `linkbudget-rf[docs]` | `mkdocs`, `mkdocs-material`, `mkdocstrings` | building this site |

```bash
pip install 'linkbudget-rf[plot]'
# or, from a source checkout:
pip install -e '.[plot]'
```

## Requirements

- Python 3.8 or newer
- `numpy >= 1.21.5`
- `fpdf2 >= 2.8.1` (for [`PDFPublisher`](guide/publishers.md#pdfpublisher))

## Building distributable artifacts

```bash
pip install build twine
python -m build          # writes a wheel + sdist to dist/
twine check dist/*       # or: make dist-check
```

## Publishing a release

Releases go to PyPI as **`linkbudget-rf`** through GitHub Actions
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) — no API
tokens. One-time setup: on PyPI, add a *pending publisher* for the project
(`Chris93Hall` / `linkbudget` / workflow `release.yml` / environment `pypi`).

To cut a release:

1. Bump `version` in `pyproject.toml` and commit.
2. Tag it and push — the tag must be the version prefixed with `v`:

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

The `release.yml` workflow then runs the test suite, builds the artifacts,
checks the tag matches the package version, publishes to PyPI, and opens a
GitHub Release with the artifacts attached. `workflow_dispatch` runs
everything except the publish step, for a dry run.

## Developer tasks

The `Makefile` wraps the common workflows:

```bash
make test        # pytest + an HTML coverage report in coverage/
make lint        # ruff + pylint
make examples    # run every example, outputs to examples/example_outputs/
make docs        # build this site into site/
make docs-serve  # serve it locally with live reload
```
