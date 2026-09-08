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

## 5. Noise modelling

- [x] Friis per-stage noise cascade. `RFComponent` / `NoiseFigure` / `Mixer`
  (and the ADC/DAC input stages) take an opt-in `noise_bandwidth` (Hz) that
  switches them from the scale-free `N_out = N_in · G · F` to the Friis
  added-noise form `N_out = (N_in + (F−1)·k·T0·B)·G`, referring the excess to
  the stage input so late-stage noise figure correctly matters less.
  `reference_temp_k` (default `convert.REFERENCE_NOISE_TEMP_K` = 290 K) is
  configurable per stage. `summary().system_noise_temp_k` now sums the
  per-stage contributions (Friis, referred to the floor plane) instead of just
  reporting the floor temperature. `linkbudget.fom` gained
  `noise_figure_to_temp_k` / `noise_temp_to_figure_db` /
  `friis_total_noise_temp_k` / `friis_total_noise_figure_db`.
- [x] Antenna noise temperature model. `antennas.AntennaNoiseTemperature`
  injects `k·T_a·B` from a `T_sky` / `T_ground` / ohmic-loss composition;
  `antennas.antenna_noise_temp_k` is the scalar helper. Receiver temperature
  stays a separate `ThermalNoise` / noise-figure stage.
- [ ] Phase-noise / reciprocal-mixing contribution.
- [ ] ADC noise from aperture jitter and SFDR/SNDR, not just quantisation.

## 6. Modelling ergonomics

- [ ] Unit-aware inputs (accept dBm / dBW / W, not just linear W + a display string).
- [ ] YAML / JSON budget definitions (`LinkContainer.from_yaml(...)`).
- [ ] Parameter sweeps (margin vs range / elevation / frequency / data rate).
- [ ] Tolerance / Monte-Carlo analysis (per-parameter 3σ, worst-case vs RSS).
- [x] Allow multiple simultaneous publishers (`add_publisher`; `publish()` runs
  all of them, or falls back to a `StdOutPublisher` when none are installed).
  `.publishers` is the list; assign it to replace or clear.
- [ ] Editable component list (lookup / insert / remove / replace by name), `__repr__`.
- [ ] Bidirectional links (uplink + downlink + transponder, end-to-end C/N).
- [ ] Shared carrier frequency flowing through frequency-dependent components
  instead of each one taking its own `frequency` argument.
- [x] Move the hard-coded `2.99792458e8` in `link_container` onto
  `convert.SPEED_OF_LIGHT`.

## 7. Validation & robustness

- [x] Input validation -- component constructors raise `ValueError` for
  non-positive distances/frequencies/bandwidths/bit-depths/etc., bad `role`
  and `mixer.mode` strings, out-of-range elevation/efficiency, and unordered
  `SubBandTune` band edges (`linkbudget/_validate.py`). Non-overlapping
  `SubBandTune` bands now clamp the signal to zero instead of going negative.
- [x] Warnings for physically dubious budgets -- `budget.check()` /
  `LinkBudgetWarning` from `compute()` flag: no signal / fully attenuated
  signal, negative stage power, a repeated `ThermalNoise` floor, a negative
  `total_loss_db` / `conversion_loss_db`, and a path stage off the declared
  `carrier_frequency` (`linkbudget/checks.py`). `LinkContainer(warn=False)`
  silences them.
- [x] Division-by-zero guards -- covered by the input validation above plus a
  `4.0**effective_bits` underflow guard in `QuantizationNoise`.
- [ ] "SNR improves through a passive stage" was dropped as a check: with the
  built-in components it only happens via a negative loss value, which the
  negative-loss check already catches. Revisit if user-written components
  become common.

## 8. Output

- [ ] CSV / JSON / dict / DataFrame export from `compute()`.
- [x] Markdown report -- `MarkdownPublisher` writes the summary + per-component
  tables as GitHub-flavoured Markdown (`.md`).
- [x] Cascade "waterfall" plot of signal & noise power vs stage
  (`WaterfallPublisher`, matplotlib, writes an image). `make examples` runs
  every example and writes `.pdf` / `.html` / `.md` / `.png` to
  `examples/example_outputs/`.
- [x] Allow multiple simultaneous publishers (stdout + PDF + HTML + Markdown +
  waterfall in one run) -- see [[section 6]].
- [ ] Budget-vs-budget diff.
- [ ] Scenario templates (LEO downlink, GEO, terrestrial microwave, P2P Wi-Fi).

## 9. Project

- [~] CI configuration. Docs deploy workflow exists
  (`.github/workflows/docs.yml`); still need a test/lint CI workflow.
- [x] Type hints + `py.typed`. Every function/method in the package is
  annotated; ``linkbudget/py.typed`` ships the marker; ``mypy linkbudget``
  is clean. Every component now inherits ``Component`` (which carries the
  ``is_propagation`` / ``is_margin`` / ``role`` tag defaults).
- [ ] Add mypy to CI / the Makefile.
- [x] Docs site -- MkDocs + Material + mkdocstrings, published to GitHub Pages
  from CI (`make docs` / `make docs-serve`, `pip install linkbudget[docs]`).
- [ ] Worked-example notebooks (deferred).
- [x] Class / function docstrings written for the whole package; the
  `missing-module-docstring` / `missing-class-docstring` /
  `missing-function-docstring` pylint checks are re-enabled (pylint 10/10).
- [ ] Changelog.
