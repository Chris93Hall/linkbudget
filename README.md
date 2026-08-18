# linkbudget

A small Python library for building RF/communications **link budgets**. You chain together a series of components (signal sources, path loss, gains, noise figures, quantization noise, etc.), and the library propagates signal and noise power through the chain, computing gain and SNR at each stage. Results can be printed to stdout or exported to a PDF report.

## Installation

There is no packaged distribution yet — use the library directly from a clone of this repository.

```bash
git clone <this-repo>
cd linkbudget
pip install numpy fpdf2
```

Run scripts from the repository root so `import linkbudget` resolves to the local package.

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

This prints a summary table (per-stage signal/noise power, gain, and SNR) followed by a detailed report with every field each component produced. See `example_budget.py` for a fuller example that also includes a noise source, quantization noise, and a sub-band tuner.

Run the example directly:

```bash
python example_budget.py
```

## Core concepts

### `LinkContainer`

The container that holds the chain of components and drives the computation.

```python
budget = linkbudget.LinkContainer()
budget.install_publisher(linkbudget.StdOutPublisher())  # optional, this is the default
budget.add_component(...)                                 # add as many as needed, in order
budget.publish()                                           # computes and publishes the result
```

- `add_component(component)` — appends a component to the chain.
- `install_publisher(publisher)` — sets how results are output (default is `StdOutPublisher`).
- `compute()` — runs signal/noise power through each component in order, computing signal gain, noise gain, and SNR at every stage. Called automatically by `publish()`.
- `publish()` — calls `compute()` then hands the resulting data to the installed publisher.

Components are evaluated **in the order they were added**; each component's output signal/noise power becomes the next component's input.

### Components

All components implement `propagate_signal(signal_power, noise_power)` and return a dict describing that stage (input/output power, gain, and any component-specific fields). Available components, importable directly from `linkbudget`:

| Component | Purpose | Key arguments |
|---|---|---|
| `SignalSource(name, description, signal_power, noise_power)` | Injects signal and/or noise power into the chain (e.g. a transmitter, or a noise source) | `signal_power`, `noise_power` (linear, added to whatever is already in the chain) |
| `FreeSpacePathLoss(name, description, distance, frequency)` | Applies free-space path loss | `distance` (meters), `frequency` (Hz) |
| `Gain(name, description, gain, db=True)` | Applies a gain (or loss, if negative) to both signal and noise | `gain`, `db` (`True` for dB, `False` for linear) |
| `QuantizationNoise(name, description, total_bits, headroom_db)` | Adds ADC quantization noise based on bit depth and headroom | `total_bits`, `headroom_db` |
| `SubBandTune(name, description, input_lower_freq, input_upper_freq, signal_lower_freq, signal_upper_freq, output_lower_freq, output_upper_freq)` | Models filtering/retuning to a sub-band, reducing signal and noise bandwidth accordingly | frequency band edges (Hz) |
| `RadarCrossSection(name, description, rcs_db)` | Applies a radar cross-section scaling factor (e.g. for radar link budgets) | `rcs_db` |
| `ArrayFactor(name, description, num_elements)` | Applies antenna array gain from element count | `num_elements` |
| `Mixer(name, description, lo_frequency, rf_frequency, conversion_loss_db, noise_figure_db, mode, image_reject_db)` | Frequency-converts the signal (up/down-conversion against an LO), applying conversion loss/gain and noise figure | `lo_frequency`/`rf_frequency` (Hz), `conversion_loss_db`, `mode` (`'downconvert'` or `'upconvert'`), optional `noise_figure_db` and `image_reject_db` |
| `ThermalNoise(name, description, temperature_k, bandwidth)` | Adds a physically-computed thermal noise floor (`k * T * B`) to the noise power | `temperature_k` (Kelvin, default 290), `bandwidth` (Hz) |
| `ImplementationLoss(name, description, cable_loss_db, pointing_loss_db, polarization_loss_db, other_loss_db)` | Degrades signal only (noise unaffected), modeling aggregate implementation margin loss | loss terms in dB, summed into `total_loss_db` |
| `CableLoss(name, description, loss_db)` | `ImplementationLoss` specialized to a single cable loss term | `loss_db` |
| `PointingLoss(name, description, loss_db)` | `ImplementationLoss` specialized to a single pointing loss term | `loss_db` |
| `PolarizationLoss(name, description, loss_db)` | `ImplementationLoss` specialized to a single polarization loss term | `loss_db` |

`CableLoss`, `PointingLoss`, and `PolarizationLoss` are thin subclasses of `ImplementationLoss` — each just sets one of its loss terms, so you can add them individually to a chain instead of bundling all loss sources into a single `ImplementationLoss` component. They share its signal-only degradation behavior.

Additional components (`NoiseFigure`, `RFComponent`, `Integrate`) are defined in `linkbudget.link_container` but are not yet exposed from the top-level `linkbudget` package; import them directly, e.g. `from linkbudget.link_container import NoiseFigure`.

Every component is constructed with a `name` and `description` (used for reporting), plus its own parameters. `name`/`description` are positional in most components but keyword-only (with defaults) in a few (`QuantizationNoise`, `SubBandTune`, etc.) — check the signature if unsure.

### Publishers

Publishers control how the computed link budget is reported.

- **`StdOutPublisher`** — prints a summary table and a detailed per-stage report to the console. This is the default publisher if none is installed.
- **`PDFPublisher(fpath)`** — writes the same summary + detailed report to a PDF file at `fpath` (requires the `fpdf2` package).

```python
budget.install_publisher(linkbudget.PDFPublisher('example_link_budget.pdf'))
budget.publish()
```

You can write your own publisher by subclassing `linkbudget.publishers.Publisher` and implementing `publish(data_list)`, where `data_list` is a list of per-component dicts (each containing at least `name`, `description`, `signal_power_in/out`, `noise_power_in/out`, `signal_gain`, `noise_gain`, and `snr`, plus any component-specific fields).

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
