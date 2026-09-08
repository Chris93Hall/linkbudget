# Antenna models

`linkbudget.antennas` has three components and the scalar helpers behind
them. They return the standard stage dict, so they drop straight into a
chain.

## `ParabolicDish`

Boresight gain and &minus;3 dB beamwidth from the physical diameter,
frequency and aperture efficiency. Like `Gain`, it scales both signal and
noise. Tag it `role="rx"` (or `"tx"`) so
[`summary()`](figures-of-merit.md) can identify the receive antenna for G/T.

```python
linkbudget.ParabolicDish(
    "Ground station dish", "1.2 m offset reflector",
    diameter=1.2, frequency=11.7e9, efficiency=0.65, role="rx")
```

The stage dict adds `gain_dbi` and `half_power_beamwidth_deg`.

Gain is `η·(π·D/λ)²`; the beamwidth is the `70·λ/D` rule of thumb.

## `BeamPointingLoss`

Pointing loss from a finite beamwidth and a pointing error, using the
quadratic main-lobe approximation `L = 12·(error / HPBW)²` dB (so the loss is
3 dB at half the beamwidth, 12 dB at the full beamwidth).

```python
# give the beamwidth directly...
linkbudget.BeamPointingLoss(
    "Pointing", "", pointing_error_deg=0.3, half_power_beamwidth_deg=1.6)

# ...or derive it from a dish
linkbudget.BeamPointingLoss(
    "Pointing", "", pointing_error_deg=0.3, diameter=1.2, frequency=11.7e9)
```

Attenuates the signal only.

## `PolarizationMismatchLoss`

Loss from a polarization mismatch between the transmit and receive antennas,
computed from their axial ratios (dB) and relative tilt.

```python
linkbudget.PolarizationMismatchLoss(
    "Polarization", "",
    axial_ratio_db_tx=0.8,   # 0 dB = perfectly circular
    axial_ratio_db_rx=1.0,   # large -> approaches linear
    tilt_angle_deg=15.0)
```

Matched circular gives no loss; circular against linear gives 3 dB; crossed
linears give a null. Attenuates the signal only.

## `AntennaNoiseTemperature`

The antenna-side noise floor: injects `k·T_a·B` watts, where the antenna
noise temperature `T_a` is composed from the sky brightness temperature, warm
ground picked up through the sidelobes/spillover, and the antenna's own ohmic
loss. It is the receive-side counterpart to a `ThermalNoise` receiver floor —
put it right after the receive antenna.

```python
linkbudget.AntennaNoiseTemperature(
    "Antenna noise", "clear-sky Ku-band, 30 deg elevation",
    sky_temp_k=12.0,          # atmospheric emission along the path (incl. ~2.7 K CMB)
    ground_temp_k=290.0,
    ground_coupling=0.05,     # fraction of the pattern seeing warm ground
    radiation_efficiency=0.98,  # ohmic efficiency; < 1 also attenuates the signal
    physical_temp_k=290.0,
    bandwidth=20e6)
```

`T_a = η·[(1 − c)·T_sky + c·T_ground] + (1 − η)·T_phys` with `c` the ground
coupling and `η` the radiation efficiency. The stage dict adds
`scene_noise_temp_k`, `antenna_noise_temp_k` and `antenna_noise_power`, and
`summary()` folds `antenna_noise_temp_k` into the
[system noise temperature](noise.md).

## Scalar helpers

```python
from linkbudget import antennas

antennas.dish_gain_dbi(1.2, 11.7e9, efficiency=0.65)              # dBi
antennas.dish_half_power_beamwidth_deg(1.2, 11.7e9)               # degrees
antennas.gaussian_beam_pointing_loss_db(0.3, 1.6)                 # dB
antennas.polarization_efficiency(0.8, 1.0, tilt_angle_deg=15.0)   # 0..1
antennas.antenna_noise_temp_k(12.0, ground_coupling=0.05)         # K
```
