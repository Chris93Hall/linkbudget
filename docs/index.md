# linkbudget

A small Python library for building RF / communications **link budgets**.

You chain together a series of components — signal sources, path loss, gains,
noise figures, antennas, atmospheric losses — and the library propagates
signal and noise power through the chain, computing gain and SNR at every
stage. From there it derives the standard figures of merit (EIRP, G/T,
C/N&#8320;, E&#8203;b/N&#8320;) and a link-margin verdict, and can publish the
result to the console, a PDF / HTML / Markdown report, or a waterfall plot.

```python
import linkbudget

budget = linkbudget.LinkContainer(noise_bandwidth=2e6, data_rate=1e6)

budget.add_component(linkbudget.SignalSource(
    "Transmitter", "1 W output", signal_power=1.0))
budget.add_component(linkbudget.FreeSpacePathLoss(
    "Path loss", "10 km at 2.4 GHz", distance=10e3, frequency=2.4e9))
budget.add_component(linkbudget.Gain(
    "Rx antenna", "dish gain", gain=25.0, role="rx"))
budget.add_component(linkbudget.ThermalNoise(
    "Noise floor", "290 K receiver", temperature_k=290.0, bandwidth=2e6))
budget.add_component(linkbudget.LinkMargin(
    "Margin", "required Eb/N0 = 6 dB",
    required_ebno_db=6.0, noise_bandwidth=2e6, data_rate=1e6))

print(budget.summary())
```

## What it does

- **A component chain.** [`LinkContainer`][linkbudget.link_container.LinkContainer]
  walks components in order, threading signal and noise power through each and
  recording gain and SNR at every stage.
- **Figures of merit.** [`budget.summary()`][linkbudget.link_container.LinkContainer.summary]
  returns a [`BudgetSummary`][linkbudget.summary.BudgetSummary] with EIRP, G/T,
  system noise temperature, C/N&#8320;, E&#8203;b/N&#8320;, E&#8203;s/N&#8320;,
  Shannon capacity, spectral efficiency and total propagation loss.
- **Link margin.** A [`LinkMargin`][linkbudget.margin.LinkMargin] stage compares
  the achieved link against a demodulator requirement and reports whether it
  closes.
- **Propagation models.** Free-space and radar path loss plus simplified
  ITU-R models for [gaseous absorption, rain, cloud, scintillation and two-ray
  ground reflection](guide/propagation.md).
- **Antenna models.** [Parabolic-dish gain, beam pointing loss and
  polarization mismatch](guide/antennas.md).
- **Publishers.** Console, PDF, HTML, Markdown and a matplotlib
  [waterfall / cascade plot](guide/publishers.md); run several at once.

## Where to go next

- [Installation](installation.md)
- [Concepts](concepts.md) — how the container, components and publishers fit together
- [Building a budget](guide/building-a-budget.md) — a guided walk-through
- [Figures of merit & link margin](guide/figures-of-merit.md)
- [Component reference](components.md) — every component at a glance
