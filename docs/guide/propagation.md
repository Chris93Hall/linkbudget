# Propagation models

`linkbudget.propagation` provides simplified engineering implementations of
the relevant ITU-R Recommendations, plus a two-ray ground-reflection model.
Every class is a drop-in component tagged `is_propagation = True`, so
[`summary()`](figures-of-merit.md) folds it into the total path loss.

!!! warning "These are approximations"
    The models are compact curve-fits and single-parameter formulas, not
    line-by-line reference implementations. They are fine for trade studies
    and first-order budgets; they are **not** a substitute for a full ITU-R
    prediction where an availability figure has to be defended. Each model's
    validity range is noted below.

## `AtmosphericAbsorption`

Clear-air gaseous absorption (oxygen + water vapour), ITU-R P.676 Annex 2.

Specify the path one of two ways:

```python
# explicit horizontal path
linkbudget.AtmosphericAbsorption(
    "Gases", "", frequency=20e9, path_length_km=3.0, water_vapor_density=7.5)

# slant path from the gas equivalent heights
linkbudget.AtmosphericAbsorption(
    "Gases", "", frequency=20e9, elevation_deg=30.0)
```

- `water_vapor_density` is absolute humidity in g/m&#179; (7.5 is the ITU-R
  reference).
- **Validity:** the oxygen term is the P.676 fit for **f &#8804; 57 GHz**;
  the water-vapour term is usable to ~350 GHz. Both assume a standard
  sea-level atmosphere.

## `RainAttenuation`

ITU-R P.838-3 specific attenuation (`γ_R = k·R^α`, with the full frequency
and polarization coefficient fits) and ITU-R P.618 slant-path geometry.

```python
# explicit horizontal path, with an effective-length reduction factor
linkbudget.RainAttenuation(
    "Rain", "", frequency=12e9, rain_rate=22.0, path_length_km=6.0)

# slant path: P.618 0.01% reduction + vertical-adjustment factors
linkbudget.RainAttenuation(
    "Rain", "", frequency=20e9, rain_rate=32.0,
    elevation_deg=25.0, rain_height_km=3.2, station_height_km=0.1,
    latitude_deg=41.0, polarization_tilt_deg=45.0)  # 45° tilt = circular
```

- `rain_rate` is the point rain rate in mm/h (a rate of 0 is transparent).
- `latitude_deg` refines the vertical-adjustment factor; omit it to use the
  worst case.
- **Validity:** P.838-3 coefficients cover **1–1000 GHz**; the slant-path
  procedure is the P.618 method for the attenuation exceeded 0.01% of an
  average year and expects `elevation_deg` &#8805; ~5°.

## `CloudFogAttenuation`

ITU-R P.840 double-Debye model of liquid-water permittivity.

```python
# columnar (integrated) liquid water, kg/m²
linkbudget.CloudFogAttenuation(
    "Cloud", "", frequency=30e9, liquid_water_path=0.6, elevation_deg=30.0)

# in-cloud density × path length
linkbudget.CloudFogAttenuation(
    "Fog", "", frequency=30e9, liquid_water_density=0.5, path_length_km=1.0)
```

- **Validity:** the double-Debye fit is good across the microwave/millimetre
  band; the model covers cloud/fog liquid water only (rain is handled
  separately by `RainAttenuation`).

## `TroposphericScintillation`

ITU-R P.618 §2.4.1 — the fast amplitude fading on a low-elevation slant path,
with the antenna aperture-averaging factor.

```python
linkbudget.TroposphericScintillation(
    "Scintillation", "", frequency=20e9, elevation_deg=20.0,
    antenna_diameter=1.2, antenna_efficiency=0.5,
    time_percent=0.01)   # fade depth exceeded this % of an average year
```

- The wet refractivity `n_wet` is derived from `temperature_c` and
  `relative_humidity_percent` unless you pass it directly.
- **Validity:** P.618 gives this method for **f &gt; 4 GHz** and
  **elevation &#8805; 5°**.

## `TwoRayGroundReflection`

A plane-earth two-ray model for a **terrestrial** path.

```python
linkbudget.TwoRayGroundReflection(
    "Two-ray", "", distance=8000.0, tx_height=25.0, rx_height=2.0,
    frequency=900e6)
```

Beyond the free-space / plane-earth crossover distance the received power
falls as `(h_tx·h_rx / d²)²` (40 dB/decade); below it, the model falls back
to free-space loss (`frequency` is needed for that and to report the
crossover distance).

## Scalar helpers

The specific-attenuation maths is also exposed as pure functions:

```python
from linkbudget import propagation

propagation.oxygen_specific_attenuation_db_per_km(20.0)        # GHz -> dB/km
propagation.rain_specific_attenuation_db_per_km(12e9, 22.0)    # Hz, mm/h -> dB/km
propagation.rain_kalpha(20e9, polarization_tilt_deg=45.0)      # (k, alpha)
propagation.cloud_specific_attenuation_coefficient(30e9)       # (dB/km)/(g/m^3)
```
