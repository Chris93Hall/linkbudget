# Noise modelling

## Two noise models for gain stages

`RFComponent`, `NoiseFigure` and `Mixer` support two ways of propagating
noise through a stage of available power gain `G` and noise factor
`F = 10**(NF_dB / 10)`:

| Model | Formula | Selected by |
|---|---|---|
| Multiplicative (default) | `N_out = N_in · G · F` | no `noise_bandwidth` |
| Friis added-noise | `N_out = (N_in + (F − 1)·k·T₀·B)·G` | `noise_bandwidth=B` (Hz) |

In the **multiplicative** model the SNR drops by exactly `F` at the stage
regardless of where the stage sits — a 3 dB noise figure behind 40 dB of gain
hurts as much as one at the antenna. It is scale-free (works in any linear
power unit), which is why it is the default, but it is not how a real cascade
behaves.

In the **Friis** model the excess noise `(F − 1)·k·T₀·B` is injected at the
stage *input* and then amplified with everything else, so a noisy stage after
gain is suppressed by all the preceding gain. `T₀` is the IEEE reference
temperature (`convert.REFERENCE_NOISE_TEMP_K`, 290 K); override it per stage
with `reference_temp_k`. This term is an absolute power in watts, so pair it
with a `ThermalNoise` or `AntennaNoiseTemperature` floor and keep the whole
budget in watts.

```python
B = 20e6
budget = linkbudget.LinkContainer(noise_bandwidth=B)
budget.add_component(linkbudget.SignalSource("Rx signal", "", signal_power=2e-15))
budget.add_component(linkbudget.AntennaNoiseTemperature("Antenna", "", sky_temp_k=25.0, bandwidth=B))
budget.add_component(linkbudget.RFComponent("LNA", "", gain=35.0, noise_figure=0.7, noise_bandwidth=B))
budget.add_component(linkbudget.RFComponent("IF amp", "", gain=30.0, noise_figure=6.0, noise_bandwidth=B))
```

Here the 6 dB IF-amp noise figure barely matters — it is behind 35 dB of LNA
gain. Drop the `noise_bandwidth` arguments and the same budget would report a
much worse SNR, blaming the IF amp as if it were at the front.

Each Friis stage adds `noise_bandwidth`, `reference_temp_k`,
`excess_noise_temp_k` (`= (F − 1)·T₀`), `excess_noise_power` (the excess
referred to the input) and `noise_model` to its stage dict.

`AnalogToDigitalConverter` / `DigitalToAnalogConverter` take a
`noise_bandwidth` too and forward it to their internal gain stage.

## Antenna noise temperature

`AntennaNoiseTemperature` establishes the noise floor at the receive antenna
from the sky, the ground and the antenna's ohmic loss — see
[Antenna models](antennas.md#antennanoisetemperature). Use it *instead of* a
`ThermalNoise` floor when you want the antenna contribution modelled
explicitly, and add a separate `RFComponent`/`NoiseFigure` for the receiver.

## System noise temperature

With `noise_bandwidth` set on the container, `summary().system_noise_temp_k`
is the Friis sum of every stage's own added noise, referred to the noise-floor
plane:

```
T_sys = T_floor + T_e1 + T_e2 / G1 + T_e3 / (G1 · G2) + …
```

Only stages that report a thermal contribution count: a `ThermalNoise` floor,
an `AntennaNoiseTemperature`, or a noise-figure stage on the Friis model.
`g_over_t_db` then uses this `T_sys` with the `role="rx"` antenna gain.

## The `linkbudget.fom` noise helpers

```python
from linkbudget import fom

fom.noise_figure_to_temp_k(0.7)                       # NF (dB) -> T_e (K)
fom.noise_temp_to_figure_db(50.0)                     # T_e (K) -> NF (dB)
fom.friis_total_noise_temp_k([50, 120, 300], [35, 30, 0])    # cascade T_e (K)
fom.friis_total_noise_figure_db([0.7, 2.0, 6.0], [35, 30, 0])  # cascade NF (dB)
```
