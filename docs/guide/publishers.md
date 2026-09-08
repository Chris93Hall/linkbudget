# Publishers

A publisher turns the computed `data_list` into output. With none installed,
`publish()` falls back to a `StdOutPublisher`.

## Installing publishers

```python
budget.add_publisher(pub)       # append; publish() runs every installed one
budget.publish()
```

A new container has no publisher installed. Add one (or assign the whole
`budget.publishers` list) — any installed publisher replaces the stdout
fallback:

```python
budget.publishers = [linkbudget.PDFPublisher("report.pdf")]   # replace the list
budget.publish()   # writes the PDF, no stdout
```

To skip output entirely, call `budget.compute()` instead of `budget.publish()`.

```python
budget.add_publisher(linkbudget.PDFPublisher("report.pdf", title="Downlink"))
budget.add_publisher(linkbudget.HTMLPublisher("report.html", title="Downlink"))
budget.add_publisher(linkbudget.WaterfallPublisher("cascade.png"))
budget.publish()   # one compute(), three file outputs
```

## `StdOutPublisher`

Prints a summary table and a detailed per-stage report to the console. The
default when no publisher is installed.

## `HTMLPublisher`

`HTMLPublisher(fpath, title="Link Budget Report")` — writes a single
self-contained, styled HTML file: a summary table plus a per-component field
breakdown. Content is HTML-escaped and the file is UTF-8.

## `PDFPublisher`

`PDFPublisher(fpath, title="Link Budget Report")` — the same report as a
styled, paginated PDF (via `fpdf2`), visually matching the HTML layout.

## `MarkdownPublisher`

`MarkdownPublisher(fpath, title="Link Budget Report")` — the same summary
table and per-component field breakdown as GitHub-flavoured Markdown (`.md`),
ready to drop into a README, a wiki or a PR description. Pipes and newlines
in component names / descriptions are escaped so the tables stay well-formed.

## `WaterfallPublisher`

`WaterfallPublisher(fpath, title="Link Budget Cascade", figsize=(11, 6), dpi=140)`
— renders the signal / noise / SNR **cascade** across the stages to an image.
The output format follows the file extension (`.png`, `.svg`, `.pdf`, …).

Signal and noise power are drawn as staircase traces in dBW; the shaded band
between them is the running SNR; stages with zero signal or noise power
(&minus;&infin; dBW) sit on the axis floor.

Requires `matplotlib` — `pip install linkbudget[plot]`. It is imported
lazily, so importing `linkbudget` never needs it.

## Writing your own

Subclass `linkbudget.publishers.Publisher` and implement
`publish(data_list, power_units="W")`, where `data_list` is the list of stage
dicts (each with at least `name`, `description`, `signal_power_in`/`out`,
`noise_power_in`/`out`, `signal_gain`, `noise_gain`, `snr`).
`linkbudget.publishers.label_with_units(key, power_units)` reproduces the
"append units to known power fields" behaviour the built-in publishers use.

```python
from linkbudget.publishers import Publisher

class CsvPublisher(Publisher):
    def __init__(self, fpath):
        self.fpath = fpath

    def publish(self, data_list, power_units="W"):
        import csv
        with open(self.fpath, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["stage", "signal_out", "noise_out", "snr"])
            for stage in data_list:
                writer.writerow([stage["name"], stage["signal_power_out"],
                                 stage["noise_power_out"], stage["snr"]])
```
