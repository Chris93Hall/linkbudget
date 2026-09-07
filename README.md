# linkbudget

A small Python library for building RF/communications **link budgets**. You chain together a series of components (signal sources, path loss, gains, noise figures, quantization noise, etc.), and the library propagates signal and noise power through the chain, computing gain and SNR at each stage. Results can be printed to stdout, or exported to a PDF or HTML report.

📖 **Documentation: <https://chris93hall.github.io/linkbudget/>** — concepts, guides, propagation/antenna models, figures of merit and the full API reference. Build it locally with `make docs-serve`.

## Installation

The project is packaged with a standard `pyproject.toml` (setuptools backend), so it can be installed like any Python package:

```bash
git clone <this-repo>
cd linkbudget
pip install .          # regular install
# pip install -e .     # editable install, for local development
```

This pulls in `numpy` and `fpdf2` automatically. If you'd rather not install the package, `pip install -r requirements.txt` plus running scripts from the repository root also works, since `import linkbudget` then resolves to the local package directory — but the `examples/` scripts live one directory down (see below), so with this route you'd need `PYTHONPATH=. python examples/example_budget.py` from the repository root, rather than plain `python examples/example_budget.py`.

To build distributable artifacts (a wheel + sdist under `dist/`) without installing, e.g. to publish or hand off to someone else:

```bash
pip install build
python -m build
```

## Quick start

```python
import linkbudget

budget = linkbudget.LinkContainer()
budget.install_publisher(linkbudget.StdOutPublisher())

budget.add_component(linkbudget.SignalSource(
    'Signal source',
    'Signal starting at transmit side',
    signal_power=1.0,
    noise_power=0.0))

budget.add_component(linkbudget.FreeSpacePathLoss(
    'Path loss',
    'Path from transmitter to receiver',
    distance=1000,      # meters
    frequency=5e9))      # Hz

budget.add_component(linkbudget.Gain(
    'Rx antenna gain',
    'Gain of the receive antenna',
    gain=3.0,
    db=True))

budget.publish()
```

This prints a summary table (per-stage signal/noise power, gain, and SNR) followed by a detailed report with every field each component produced. See `examples/example_budget.py` for a fuller example that also includes a noise source, quantization noise, and a sub-band tuner.

## Examples

The `examples/` directory has runnable scripts (install the package first — see Installation). Run them from inside `examples/` so their output files land alongside the scripts rather than wherever you happened to invoke Python from:

```bash
cd examples
python example_budget.py         # writes example_link_budget.pdf
python example_radar_budget.py   # exercises every component, writes example_radar_link_budget.html
```

`example_radar_budget.py` models an X-band monostatic pulse-doppler surveillance radar — transmitter, feed/pointing/polarization losses, a phased-array antenna, a two-way radar path loss to a target with a given RCS, a thermal noise floor, an LNA, a downconverting mixer, an ADC digitizing the IF, a digital channelizer, and coherent pulse integration — and publishes an HTML report via `HTMLPublisher`. It's the best single reference for how every component in the library fits into a realistic chain.

## Core concepts

### `LinkContainer`

The container that holds the chain of components and drives the computation.

```python
budget = linkbudget.LinkContainer(power_units='W')  # 'W' (watts) is the default
budget.install_publisher(linkbudget.StdOutPublisher())  # optional, this is the default
budget.add_component(...)                                 # add as many as needed, in order
budget.publish()                                           # computes and publishes the result
```

- `power_units` — a display label for whatever **linear** units your `signal_power`/`noise_power` values are actually in (e.g. `'W'`, `'mW'`). Every component adds/multiplies these values directly (never in log scale), so the label must name a linear unit, not a dB-referenced one like `'dBm'`/`'dBW'` — those would be inconsistent with the actual arithmetic. It's purely cosmetic: it's passed through to the installed publisher and shown in power-related table headers and detailed-report field labels, but doesn't rescale any numbers — pick units consistently across every component you add (e.g. `ThermalNoise`'s `k·T·B` is always in watts, so if you use it, keep everything else in watts too).
- `add_component(component)` — appends a component to the chain.
- `install_publisher(publisher)` — sets how results are output (default is `StdOutPublisher`).
- `compute()` — runs signal/noise power through each component in order, computing signal gain, noise gain, and SNR at every stage. Called automatically by `publish()`.
- `publish()` — calls `compute()` then hands the resulting data, along with `power_units`, to the installed publisher.

Components are evaluated **in the order they were added**; each component's output signal/noise power becomes the next component's input.

### Components

All components implement `propagate_signal(signal_power, noise_power)` and return a dict describing that stage (input/output power, gain, and any component-specific fields). Available components, importable directly from `linkbudget`:

| Component | Purpose | Key arguments |
|---|---|---|
| `SignalSource(name, description, signal_power, noise_power)` | Injects signal and/or noise power into the chain (e.g. a transmitter, or a noise source) | `signal_power`, `noise_power` (linear, added to whatever is already in the chain) |
| `FreeSpacePathLoss(name, description, distance, frequency)` | Applies free-space path loss | `distance` (meters), `frequency` (Hz) |
| `Gain(name, description, gain, db=True)` | Applies a gain (or loss, if negative) to both signal and noise | `gain`, `db` (`True` for dB, `False` for linear) |
| `QuantizationNoise(name, description, total_bits, headroom_db)` | Adds quantization noise based on bit depth and headroom | `total_bits`, `headroom_db` |
| `AnalogToDigitalConverter(name, description, gain_db, noise_figure_db, total_bits, headroom_db, sample_rate)` | An ADC: input buffer gain/noise figure, then quantization noise, in one step. Equivalent to `RFComponent` followed by `QuantizationNoise` | `gain_db`, `noise_figure_db`, `total_bits`, `headroom_db`, optional `sample_rate` (Hz, informational) |
| `DigitalToAnalogConverter(name, description, total_bits, headroom_db, gain_db, noise_figure_db, sample_rate)` | A DAC: quantization noise, then output driver gain/noise figure, in one step (reverse order of `AnalogToDigitalConverter`). Equivalent to `QuantizationNoise` followed by `RFComponent` | `total_bits`, `headroom_db`, `gain_db`, `noise_figure_db`, optional `sample_rate` (Hz, informational) |
| `SubBandTune(name, description, input_lower_freq, input_upper_freq, signal_lower_freq, signal_upper_freq, output_lower_freq, output_upper_freq)` | Models filtering/retuning to a sub-band, reducing signal and noise bandwidth accordingly | frequency band edges (Hz) |
| `RadarCrossSection(name, description, rcs_db)` | Applies a radar cross-section scaling factor as a plain dB power multiplier | `rcs_db` |
| `RadarPathLoss(name, description, distance / tx_distance+rx_distance, frequency, rcs_db)` | Correct two-way radar path loss in one step: `λ²·σ / ((4π)³·R_tx²·R_rx²)` | `distance` or `tx_distance`+`rx_distance`, `frequency` (Hz), `rcs_db` (dB relative to 1 m²) |
| `RadarPathLossOneWay(name, description, distance, frequency)` | One leg of a two-way radar path, calibrated so `RadarPathLossOneWay -> RadarCrossSection -> RadarPathLossOneWay` reproduces `RadarPathLoss` exactly | `distance` (meters), `frequency` (Hz) |
| `ArrayFactor(name, description, num_elements)` | Applies antenna array gain from element count | `num_elements` |
| `Mixer(name, description, lo_frequency, rf_frequency, conversion_loss_db, noise_figure_db, mode, image_reject_db)` | Frequency-converts the signal (up/down-conversion against an LO), applying conversion loss/gain and noise figure | `lo_frequency`/`rf_frequency` (Hz), `conversion_loss_db`, `mode` (`'downconvert'` or `'upconvert'`), optional `noise_figure_db` and `image_reject_db` |
| `ThermalNoise(name, description, temperature_k, bandwidth)` | Adds a physically-computed thermal noise floor (`k * T * B`) to the noise power | `temperature_k` (Kelvin, default 290), `bandwidth` (Hz) |
| `ImplementationLoss(name, description, cable_loss_db, pointing_loss_db, polarization_loss_db, other_loss_db)` | Degrades signal only (noise unaffected), modeling aggregate implementation margin loss | loss terms in dB, summed into `total_loss_db` |
| `CableLoss(name, description, loss_db)` | `ImplementationLoss` specialized to a single cable loss term | `loss_db` |
| `PointingLoss(name, description, loss_db)` | `ImplementationLoss` specialized to a single pointing loss term | `loss_db` |
| `PolarizationLoss(name, description, loss_db)` | `ImplementationLoss` specialized to a single polarization loss term | `loss_db` |
| `NoiseFigure(name, description, noise_figure)` | Degrades noise power (no gain applied) by a noise figure, e.g. a lossless/unity-gain noisy stage | `noise_figure` (dB) |
| `RFComponent(name, description, gain, noise_figure)` | A generic gain block with a noise figure (e.g. an amplifier) — signal scales by `gain`, SNR degrades by `noise_figure` | `gain` (dB), `noise_figure` (dB) |
| `Integrate(name, description, timespan)` | Coherent integration (e.g. pulse integration): signal power scales by `timespan` (the processing gain), noise is unaffected | `timespan` |

`CableLoss`, `PointingLoss`, and `PolarizationLoss` are thin subclasses of `ImplementationLoss` — each just sets one of its loss terms, so you can add them individually to a chain instead of bundling all loss sources into a single `ImplementationLoss` component. They share its signal-only degradation behavior.

Every component is constructed with a `name` and `description` (used for reporting), plus its own parameters. `name`/`description` are positional in most components but keyword-only (with defaults) in a few (`QuantizationNoise`, `SubBandTune`, etc.) — check the signature if unsure.

### Publishers

Publishers control how the computed link budget is reported. Every built-in publisher labels power-valued columns/fields with the container's `power_units` (e.g. "Signal Power Out (W)"). Install one with `install_publisher()`, or add several with `add_publisher()` and `publish()` runs them all. See the [documentation](https://chris93hall.github.io/linkbudget/guide/publishers/) for the full list.

- **`StdOutPublisher`** — prints a summary table and a detailed per-stage report to the console. This is the default publisher if none is installed.
- **`PDFPublisher(fpath, title='Link Budget Report')`** — writes the same summary + detailed report to a styled PDF file at `fpath` (requires the `fpdf2` package), visually matching `HTMLPublisher`'s layout and colors (striped tables, a dark header row, a title banner), with automatic multi-page pagination.
- **`HTMLPublisher(fpath, title='Link Budget Report')`** — writes a single self-contained HTML file at `fpath` with a styled summary table and a detailed per-component breakdown.
- **`MarkdownPublisher(fpath, title='Link Budget Report')`** — writes the same tables as a GitHub-flavoured Markdown (`.md`) file.
- **`WaterfallPublisher(fpath, title='Link Budget Cascade')`** — renders the signal/noise/SNR cascade to an image (requires `matplotlib`; `pip install linkbudget[plot]`).

```python
budget = linkbudget.LinkContainer(power_units='mW')

budget.install_publisher(linkbudget.PDFPublisher('example_link_budget.pdf'))
budget.publish()

budget.install_publisher(linkbudget.HTMLPublisher('example_link_budget.html'))
budget.publish()
```

You can write your own publisher by subclassing `linkbudget.publishers.Publisher` and implementing `publish(data_list, power_units='W')`, where `data_list` is a list of per-component dicts (each containing at least `name`, `description`, `signal_power_in/out`, `noise_power_in/out`, `signal_gain`, `noise_gain`, and `snr`, plus any component-specific fields) and `power_units` is the container's display label. `linkbudget.publishers.label_with_units(key, power_units)` is available if you want the same "append units to known power fields" behavior the built-in publishers use.

### Utilities

`linkbudget.convert` provides small helpers used throughout the library:

- `linear_to_db(val)` / `db_to_linear(val)` — convert between linear power ratios and dB.
- `scale_hertz(freq)` — scales a frequency in Hz to the most readable unit (kHz/MHz/GHz) for display.

## Notes

- Power values are unitless/linear unless a component specifically documents dB (e.g. `Gain(db=True)`, `rcs_db`, `headroom_db`).
- SNR and gains are reported in dB in the summary output (converted internally via `convert.linear_to_db`).
- Divide-by-zero cases (e.g. zero noise power) are handled by treating the ratio as infinite (`np.inf`).
- `ThermalNoise` computes an absolute noise power in watts (`k * T * B`, using Boltzmann's constant). For it to be physically meaningful alongside other components, signal/noise power values throughout the chain should be in watts.
- `ImplementationLoss` only attenuates the signal (noise is left untouched), matching the conventional link-budget usage of "implementation loss" as an SNR/margin penalty rather than a physical RF attenuator. To model a physical attenuator that reduces signal and noise together, use a negative-dB `Gain` instead.
- `Mixer` attenuates/amplifies signal by `conversion_loss_db` and degrades SNR by exactly `noise_figure_db` (which defaults to `conversion_loss_db`, the standard rule of thumb for a passive mixer). If `rf_frequency` is supplied, the resulting `if_frequency` is reported (`rf ± lo` depending on `mode`). If `image_reject_db` is supplied, extra noise folded in from the unrejected image band is added on top of the noise figure; omit it (default `None`) to assume an ideal, fully image-rejected mixer.
- For a two-way (reflective) radar path, use `RadarPathLoss` rather than chaining `FreeSpacePathLoss` twice around `RadarCrossSection`. `FreeSpacePathLoss` bakes a wavelength-dependent receive-aperture term (`λ²/4π`) into its formula, which is correct for one hop between two antennas but not for a hop into a target (which has no antenna aperture — it just scatters based on RCS in m²). Chaining it twice imposes that aperture term a second time where it doesn't belong, overstating two-way path loss by `λ²/(4π)` (~41 dB at X-band) versus the standard radar range equation. `RadarPathLoss` applies the wavelength term exactly once, matching `Pr/Pt = λ²σ/((4π)³R_tx²R_rx²)`.
- `RadarPathLossOneWay` is deliberately **not** the same formula as `FreeSpacePathLoss`, even though both model "a one-way hop." It implements half of `RadarPathLoss`'s wavelength term per leg (`λ/((4π)^1.5·distance²)`) specifically so that `RadarPathLossOneWay(R1) -> RadarCrossSection(rcs_db) -> RadarPathLossOneWay(R2)` composes into the exact same result as calling `RadarPathLoss(tx_distance=R1, rx_distance=R2, rcs_db=rcs_db)` in one step. Don't use `RadarPathLossOneWay` for a genuine one-way antenna-to-antenna link with no target — use `FreeSpacePathLoss` for that.
