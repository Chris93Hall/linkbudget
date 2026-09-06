# Building a budget

This walk-through builds a small point-to-point microwave link from scratch.

## 1. Create the container

Give it the context the figures of merit need — a noise bandwidth and a data
rate — up front:

```python
import linkbudget

budget = linkbudget.LinkContainer(
    carrier_frequency=6e9,
    noise_bandwidth=20e6,
    data_rate=45e6,
)
```

## 2. Add the transmit side

A [`SignalSource`][linkbudget.link_container.SignalSource] injects power into
the chain; a [`Gain`][linkbudget.link_container.Gain] applies the transmit
antenna gain.

```python
budget.add_component(linkbudget.SignalSource(
    "Transmitter", "1 W (0 dBW) at the PA output", signal_power=1.0))
budget.add_component(linkbudget.Gain(
    "Tx antenna", "36 dBi dish", gain=36.0, role="tx"))
```

## 3. Add the path

`FreeSpacePathLoss` is tagged as a propagation stage, so the signal power
entering it becomes the budget's **EIRP**.

```python
budget.add_component(linkbudget.FreeSpacePathLoss(
    "Free-space path loss", "12 km hop", distance=12e3, frequency=6e9))
```

## 4. Add the receive side

Mark the receive antenna with `role="rx"` so `summary()` can compute G/T.
`ThermalNoise` establishes the noise floor (`k·T·B` in watts — so every
power value in this budget is in watts); `RFComponent` is the LNA.

```python
budget.add_component(linkbudget.Gain(
    "Rx antenna", "36 dBi dish", gain=36.0, role="rx"))
budget.add_component(linkbudget.ThermalNoise(
    "Noise floor", "290 K system temperature",
    temperature_k=290.0, bandwidth=20e6))
budget.add_component(linkbudget.RFComponent(
    "LNA", "low-noise amplifier", gain=30.0, noise_figure=1.5))
```

## 5. State the requirement

A [`LinkMargin`][linkbudget.margin.LinkMargin] stage compares the achieved
link against a demodulator threshold. It passes signal and noise through
unchanged — it only annotates the result.

```python
budget.add_component(linkbudget.LinkMargin(
    "Link margin", "64-QAM, required Eb/N0 = 15 dB",
    required_ebno_db=15.0, noise_bandwidth=20e6, data_rate=45e6,
    implementation_loss_db=2.0))
```

## 6. Read the result

```python
summary = budget.summary()
print(summary)

if summary.closes:
    print(f"link closes with {summary.margin_db:.1f} dB of margin")
```

`summary` is a [`BudgetSummary`][linkbudget.summary.BudgetSummary] — every
field is also available programmatically (`summary.eirp_dbw`,
`summary.g_over_t_db`, `summary.ebno_db`, …) and as a dict via
`summary.as_dict()`.

## 7. Publish reports

```python
budget.install_publisher(linkbudget.StdOutPublisher())
budget.add_publisher(linkbudget.HTMLPublisher("link.html", title="6 GHz hop"))
budget.add_publisher(linkbudget.PDFPublisher("link.pdf", title="6 GHz hop"))
budget.add_publisher(linkbudget.WaterfallPublisher("link.png"))
budget.publish()
```

## Inspecting individual stages

After `compute()` (or `publish()` / `summary()`), `budget.data_list` holds
one dict per stage:

```python
budget.compute()
for stage in budget.data_list:
    print(f"{stage['name']:20s}  SNR = {linkbudget.convert.linear_to_db(stage['snr']):6.1f} dB")
```
