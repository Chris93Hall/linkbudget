# Figures of merit & link margin

## `budget.summary()`

[`LinkContainer.summary()`][linkbudget.link_container.LinkContainer.summary]
computes the budget and returns a
[`BudgetSummary`][linkbudget.summary.BudgetSummary] dataclass. Print it for a
readable report, or read the fields directly:

```python
summary = budget.summary()
print(summary)
print(summary.ebno_db, summary.g_over_t_db, summary.closes)
data = summary.as_dict()          # plain dict, stages included
```

### Always populated

| Field | Meaning |
|---|---|
| `signal_power_w`, `signal_power_dbw` | final signal power |
| `noise_power_w`, `noise_power_dbw` | final noise power |
| `snr`, `snr_db` | final signal-to-noise ratio |

### Populated when there is enough context

| Field | Needs | Meaning |
|---|---|---|
| `cn_db` | `noise_bandwidth` | carrier-to-noise ratio in that bandwidth |
| `cn0_dbhz` | `noise_bandwidth` | carrier-to-noise **density** (dB-Hz) |
| `ebno_db` | `noise_bandwidth` + `data_rate` | energy-per-bit to noise density |
| `esno_db` | `noise_bandwidth` + `symbol_rate` | energy-per-symbol to noise density |
| `shannon_capacity_bps` | `noise_bandwidth` | Shannon–Hartley capacity |
| `spectral_efficiency_bps_per_hz` | `noise_bandwidth` + `data_rate` | `data_rate / noise_bandwidth` |
| `eirp_dbw` | a propagation stage | signal power entering the first one |
| `total_propagation_loss_db` | a propagation stage | product of every propagation stage's loss |
| `system_noise_temp_k` | `noise_bandwidth` + a noise-floor stage | Friis sum of every stage's noise, referred to the floor plane |
| `g_over_t_db` | the above + a `role="rx"` antenna | receiver figure of merit |
| `margin_db`, `closes` | a `LinkMargin` stage | see below |

!!! note "System noise temperature and the noise model"
    `system_noise_temp_k` sums each stage's own added noise, referred to the
    noise-floor plane and divided down by the gain ahead of it. A stage only
    contributes if it reports a thermal contribution: a `ThermalNoise` floor,
    an `AntennaNoiseTemperature`, or a noise-figure stage running the
    [Friis model](noise.md) (`noise_bandwidth` set). Noise-figure stages left
    on the default multiplicative model, and quantisation noise, don't add a
    temperature — with only those present the value falls back to the
    floor-plane noise power expressed as a temperature.

## `LinkMargin`

Add a [`LinkMargin`][linkbudget.margin.LinkMargin] as the **last** stage. It
passes signal and noise through untouched and annotates the stage (and hence
the summary) with the closure verdict.

Give it exactly one requirement:

| Argument | Requirement is on | Also needs |
|---|---|---|
| `required_ebno_db` | E&#8203;b/N&#8320; | `noise_bandwidth`, `data_rate` |
| `required_esno_db` | E&#8203;s/N&#8320; | `noise_bandwidth`, `symbol_rate` |
| `required_cn_db` | C/N | `noise_bandwidth` |
| `required_snr_db` | raw SNR | — |

```python
budget.add_component(linkbudget.LinkMargin(
    "Link margin", "QPSK rate-1/2",
    required_ebno_db=1.0,
    noise_bandwidth=5e6,
    data_rate=4e6,
    implementation_loss_db=1.5,   # subtracted from the achieved metric
    coding_gain_db=0.0,           # added to the achieved metric
))
```

The margin is `achieved − required + coding_gain − implementation_loss`;
`closes` is `margin_db >= 0`.

## The `linkbudget.fom` module

The figure-of-merit maths lives in pure functions you can use on their own:

```python
from linkbudget import fom

fom.eirp_dbw(tx_power_dbw=0.0, tx_antenna_gain_dbi=36.0)          # 36.0
fom.free_space_path_loss_db(distance_m=12e3, frequency_hz=6e9)     # ~129.6
fom.g_over_t_db(rx_antenna_gain_dbi=36.0, system_noise_temp_k=290) # ~11.4
fom.cn0_from_snr(snr_db=12.0, noise_bandwidth_hz=20e6)             # ~85.0
fom.ebno_db(cn0=85.0, data_rate_bps=45e6)                          # ~8.5
```

See the [`linkbudget.fom` API reference](../api/fom.md) for the full set.
