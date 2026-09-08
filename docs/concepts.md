# Concepts

A link budget in this library is three things: a **container**, an ordered
list of **components**, and one or more **publishers**.

## `LinkContainer`

The container holds the chain and drives the computation.

```python
budget = linkbudget.LinkContainer(
    power_units="W",          # display label for the linear power units you use
    carrier_frequency=None,   # Hz  — optional context for summary()
    noise_bandwidth=None,     # Hz  — enables C/N0, Eb/N0, system noise temp, G/T
    data_rate=None,           # bit/s — enables Eb/N0 and spectral efficiency
    symbol_rate=None,         # baud  — enables Es/N0
)
```

- **`add_component(component)`** — append a component; order matters, each
  stage's output power is the next stage's input.
- **`compute()`** — run signal and noise power through every component,
  recording `signal_gain`, `noise_gain` and `snr` per stage into
  `budget.data_list`. Called automatically by `publish()` and `summary()`.
- **`publish()`** — `compute()`, then hand `data_list` to every installed
  publisher (or a `StdOutPublisher` fallback if none is installed).
- **`summary()`** — `compute()`, then return a
  [`BudgetSummary`](guide/figures-of-merit.md) with the figures of merit.

`power_units` is a **cosmetic label** for whatever linear unit your
`signal_power` / `noise_power` values are in. Components add and multiply
these values directly (never in dB), so keep the unit consistent across the
whole chain. `ThermalNoise`, `AntennaNoiseTemperature` and the Friis noise
model (see [Noise modelling](guide/noise.md)) all compute `k·T·B` in watts, so
if you use any of them, work in watts everywhere.

## Components

Every component implements:

```python
def propagate_signal(self, signal_power, noise_power) -> dict: ...
```

and returns a **stage dict** carrying at least:

| Key | Meaning |
|---|---|
| `name`, `description` | identification, for reports |
| `signal_power_in`, `noise_power_in` | what the stage received |
| `signal_power_out`, `noise_power_out` | what it produced |

plus any component-specific fields (a `Mixer` adds `if_frequency`, a
`ThermalNoise` adds `thermal_noise_power`, and so on). After `compute()` the
container adds `snr`, `signal_gain` and `noise_gain` to each dict.

Every built-in component inherits
[`linkbudget.Component`][linkbudget.link_container.Component] — an `ABC` that
declares the `propagate_signal` contract and carries the tag defaults
(`is_propagation`, `is_margin`, `role`).  The container itself is duck-typed,
though: it only calls `propagate_signal`, so a plain object with that method
also works.

A few components carry class-level tags the container's `summary()` looks
for:

- **`is_propagation = True`** — path-loss stages
  (`FreeSpacePathLoss`, `RadarPathLoss`, everything in
  [`linkbudget.propagation`](guide/propagation.md)). EIRP is the signal power
  entering the first of these; total propagation loss is their product.
- **`role="rx"`** — set on `Gain`, `ArrayFactor` or `ParabolicDish` to mark
  the receive antenna, so G/T can be computed.
- **`is_margin = True`** — the [`LinkMargin`](guide/figures-of-merit.md#linkmargin)
  stage.

See the [component reference](components.md) for the full list, and
[Validation & warnings](guide/validation.md) for what the constructors reject
and what `budget.check()` flags.

## Publishers

A publisher turns the computed `data_list` into output. Add one, or
[several at once](guide/publishers.md):

```python
budget.add_publisher(linkbudget.HTMLPublisher("out.html"))
budget.add_publisher(linkbudget.WaterfallPublisher("out.png"))
budget.publish()   # runs the two you added
```

With no publisher installed, `publish()` falls back to a `StdOutPublisher`;
`add_publisher()` (or assigning `budget.publishers`) replaces that fallback.
Write your own by subclassing `linkbudget.publishers.Publisher` and implementing
`publish(data_list, power_units="W")`.
