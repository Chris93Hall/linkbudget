# linkbudget — feature backlog

Status legend: `[x]` done · `[~]` partly done · `[ ]` not started

---

## 1. Results & link margin  *(the core gap: you couldn't get a number out)*

- [x] **`budget.summary()`** — returns a `BudgetSummary` with the final
  signal/noise power, SNR, and the derived figures of merit. `as_dict()` for
  serialisation, `__str__` for a readable report.
- [x] **Link margin model** — `LinkMargin` terminal component: compares the
  achieved link quality against a required threshold
  (`required_ebno_db` / `required_esno_db` / `required_cn_db` / `required_snr_db`),
  applies coding gain and implementation loss, and reports `margin_db` / `closes`.
- [x] `BudgetSummary.margin_db` / `.closes` surfaced from a `LinkMargin` stage.
- [ ] Stage lookup by name on the container (`budget["LNA"]`, `budget.stage("LNA")`).
- [ ] `to_csv()` / `to_json()` / `to_dataframe()` exporters.

## 2. Standard figures of merit

- [x] **EIRP** (dBW) — signal power entering the first propagation stage.
- [x] **G/T** (dB/K) — from a `role="rx"` antenna gain and the system noise temp.
- [x] **System noise temperature** (K) — referred to the noise-floor plane.
- [x] **C/N**, **C/N0** (dB-Hz), **Eb/N0**, **Es/N0** — from the achieved SNR,
  the noise bandwidth and the data/symbol rate.
- [x] **Shannon capacity** and **spectral efficiency**.
- [x] `linkbudget.fom` module of pure helper functions (`eirp_dbw`,
  `g_over_t_db`, `cn0_dbhz`, `cn0_from_snr`, `ebno_db`, `esno_db`, `cn_db`,
  `free_space_path_loss_db`, `shannon_capacity_bps`, `spectral_efficiency`).
- [x] Container-level `carrier_frequency`, `noise_bandwidth`, `data_rate`,
  `symbol_rate` inputs feeding the summary.
- [ ] Modulation/coding presets (required Eb/N0 tables for BPSK/QPSK/…/rate-1/2 etc.).

## 3. Propagation models

- [x] **Atmospheric gaseous absorption** — `AtmosphericAbsorption`
  (ITU-R P.676 Annex 2 simplified oxygen + water-vapour specific attenuation,
  slant path via equivalent heights or an explicit path length).
- [x] **Rain attenuation** — `RainAttenuation` (ITU-R P.838-3 specific
  attenuation with the full k/α coefficient fits, ITU-R P.618 slant-path
  geometry with the 0.01 % reduction and vertical-adjustment factors, plus a
  simple explicit-path mode).
- [x] **Cloud / fog attenuation** — `CloudFogAttenuation` (ITU-R P.840
  double-Debye liquid-water model).
- [x] **Tropospheric scintillation** — `TroposphericScintillation`
  (ITU-R P.618 §2.4.1, with the antenna aperture-averaging factor).
- [x] **Two-ray ground reflection** — `TwoRayGroundReflection` (terrestrial
  paths, with the free-space/plane-earth crossover distance).
- [ ] Terrain diffraction (knife-edge / Bullington / deygout).
- [ ] Foliage loss (ITU-R P.833 / Weissberger).
- [ ] Faraday rotation / ionospheric loss.
- [ ] Doppler shift bookkeeping.

## 4. Antenna models

- [x] **`ParabolicDish`** — boresight gain from diameter, frequency and
  aperture efficiency; also reports the −3 dB beamwidth.
- [x] **`BeamPointingLoss`** — pointing loss computed from the beamwidth and
  the pointing error (`12·(err/HPBW)²` main-lobe approximation).
- [x] **`PolarizationMismatchLoss`** — loss from two antennas' axial ratios
  and relative tilt angle.
- [x] `linkbudget.antennas` helpers (`dish_gain_dbi`,
  `dish_half_power_beamwidth_deg`, `gaussian_beam_pointing_loss_db`,
  `polarization_efficiency`).
- [x] `role="tx"|"rx"` tag on `Gain` / `ArrayFactor` / `ParabolicDish` so the
  summary can identify the receive antenna.
- [ ] Full off-boresight pattern objects (Gaussian / sinc² / measured pattern).
- [ ] Array scan loss and taper efficiency.

## 5. Noise modelling  *(known simplification)*

- [~] System noise temperature is now reported, but the per-stage cascade
  still uses `N_out = N_in · G · F` rather than the Friis added-noise form
  `N_out = N_in · G + (F−1)·k·T0·B·G`. Add proper noise-temperature tracking
  so late-stage noise figure correctly matters less.
- [ ] Antenna noise temperature model (T_sky + T_ground + T_rx composition).
- [ ] Phase-noise / reciprocal-mixing contribution.
- [ ] ADC noise from aperture jitter and SFDR/SNDR, not just quantisation.

## 6. Modelling ergonomics

- [ ] Unit-aware inputs (accept dBm / dBW / W, not just linear W + a display string).
- [ ] YAML / JSON budget definitions (`LinkContainer.from_yaml(...)`).
- [ ] Parameter sweeps (margin vs range / elevation / frequency / data rate).
- [ ] Tolerance / Monte-Carlo analysis (per-parameter 3σ, worst-case vs RSS).
- [x] Allow multiple simultaneous publishers (`add_publisher`; `publish()` runs
  all of them). `install_publisher` still replaces; `.publisher` kept as a
  backwards-compatible accessor for the first one.
- [ ] Editable component list (lookup / insert / remove / replace by name), `__repr__`.
- [ ] Bidirectional links (uplink + downlink + transponder, end-to-end C/N).
- [ ] Shared carrier frequency flowing through frequency-dependent components
  instead of each one taking its own `frequency` argument.
- [ ] Move the hard-coded `2.99792458e8` in `link_container` onto
  `convert.SPEED_OF_LIGHT` (constant added; existing call sites not yet migrated).

## 7. Validation & robustness

- [ ] Input validation (negative distances, zero frequency, `num_elements=0`,
  bad `mode` strings, non-overlapping `SubBandTune` bands → negative power).
- [ ] Warnings for physically dubious budgets (SNR improving through a passive
  loss, thermal noise added twice, gain applied before the noise floor exists).
- [ ] Consistent division-by-zero guards inside components.

## 8. Output

- [ ] CSV / JSON / dict / DataFrame export from `compute()`.
- [x] Cascade "waterfall" plot of signal & noise power vs stage
  (`WaterfallPublisher`, matplotlib, writes an image). `make examples` runs
  every example and writes `.pdf` / `.html` / `.png` to
  `examples/example_outputs/`.
- [x] Allow multiple simultaneous publishers (stdout + PDF + HTML + waterfall
  in one run) -- see [[section 6]].
- [ ] Budget-vs-budget diff.
- [ ] Scenario templates (LEO downlink, GEO, terrestrial microwave, P2P Wi-Fi).

## 9. Project

- [ ] CI configuration.
- [ ] Type hints + `py.typed`.
- [ ] Docs site / worked-example notebooks.
- [ ] Changelog.
