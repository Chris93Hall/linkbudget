# Component reference

Every component implements `propagate_signal(signal_power, noise_power)` and
is importable directly from `linkbudget`. `name` and `description` come
first (positional in most, keyword-with-default in a few — check the
signature).

## Sources and gains

| Component | Purpose | Key arguments |
|---|---|---|
| `SignalSource` | Inject signal and/or noise power (a transmitter, or a noise source) | `signal_power`, `noise_power` (linear, added to the chain) |
| `Gain` | Apply a gain/loss to both signal and noise | `gain`, `db=True`, `role=None` (`"tx"`/`"rx"`) |
| `RFComponent` | Generic gain block with a noise figure (an amplifier) | `gain` (dB), `noise_figure` (dB) |
| `NoiseFigure` | Degrade noise only, by a noise figure | `noise_figure` (dB) |
| `ArrayFactor` | Array gain from element count | `num_elements`, `role=None` |
| `Integrate` | Coherent integration: signal ×`timespan`, noise unchanged | `timespan` |

## Path loss (tagged `is_propagation`)

| Component | Purpose | Key arguments |
|---|---|---|
| `FreeSpacePathLoss` | Free-space path loss | `distance` (m), `frequency` (Hz) |
| `RadarPathLoss` | Two-way radar path loss in one step | `distance` or `tx_distance`+`rx_distance`, `frequency`, `rcs_db` |
| `RadarPathLossOneWay` | One calibrated leg of a two-way radar path | `distance` (m), `frequency` (Hz) |
| `RadarCrossSection` | RCS scaling as a plain dB multiplier | `rcs_db` (dB rel. 1 m²) |
| `AtmosphericAbsorption` | ITU-R P.676 gaseous absorption | `frequency`, `path_length_km` or `elevation_deg` |
| `RainAttenuation` | ITU-R P.838 / P.618 rain | `frequency`, `rain_rate`, `path_length_km` or slant-path args |
| `CloudFogAttenuation` | ITU-R P.840 cloud / fog | `frequency`, `liquid_water_path` or `liquid_water_density`+`path_length_km` |
| `TroposphericScintillation` | ITU-R P.618 §2.4.1 scintillation | `frequency`, `elevation_deg`, `antenna_diameter` |
| `TwoRayGroundReflection` | Plane-earth two-ray (terrestrial) | `distance`, `tx_height`, `rx_height`, `frequency` |

See [Propagation models](guide/propagation.md) for details and validity ranges.

## Antennas

| Component | Purpose | Key arguments |
|---|---|---|
| `ParabolicDish` | Dish gain + beamwidth from geometry | `diameter`, `frequency`, `efficiency`, `role=None` |
| `BeamPointingLoss` | Pointing loss from beamwidth + error | `pointing_error_deg`, `half_power_beamwidth_deg` or `diameter`+`frequency` |
| `PolarizationMismatchLoss` | Loss from axial ratios + tilt | `axial_ratio_db_tx`, `axial_ratio_db_rx`, `tilt_angle_deg` |

See [Antenna models](guide/antennas.md).

## Losses

| Component | Purpose | Key arguments |
|---|---|---|
| `ImplementationLoss` | Aggregate implementation margin loss (signal only) | `cable_loss_db`, `pointing_loss_db`, `polarization_loss_db`, `other_loss_db` |
| `CableLoss` | `ImplementationLoss` with just a cable term | `loss_db` |
| `PointingLoss` | `ImplementationLoss` with just a pointing term | `loss_db` |
| `PolarizationLoss` | `ImplementationLoss` with just a polarization term | `loss_db` |

`ImplementationLoss` attenuates the **signal only**. For a physical
attenuator that reduces signal and noise together, use a negative-dB `Gain`.

## Frequency conversion and digitisation

| Component | Purpose | Key arguments |
|---|---|---|
| `Mixer` | Up/down-conversion, conversion loss, noise figure, image noise | `lo_frequency`, `rf_frequency`, `conversion_loss_db`, `mode`, `noise_figure_db`, `image_reject_db` |
| `SubBandTune` | Filter/retune to a sub-band, reducing signal and noise bandwidth | band-edge frequencies (Hz) |
| `QuantizationNoise` | Add quantization noise from bit depth + headroom | `total_bits`, `headroom_db` |
| `AnalogToDigitalConverter` | Buffer gain/NF then quantization noise, in one step | `gain_db`, `noise_figure_db`, `total_bits`, `headroom_db`, `sample_rate` |
| `DigitalToAnalogConverter` | Quantization noise then output driver gain/NF | `total_bits`, `headroom_db`, `gain_db`, `noise_figure_db`, `sample_rate` |

## Noise floor and analysis

| Component | Purpose | Key arguments |
|---|---|---|
| `ThermalNoise` | Physical thermal noise floor `k·T·B` (watts) | `temperature_k` (default 290), `bandwidth` (Hz) |
| `LinkMargin` | Compare achieved link vs a requirement; report closure | one of `required_ebno_db` / `required_esno_db` / `required_cn_db` / `required_snr_db` |

See [Figures of merit & link margin](guide/figures-of-merit.md).
