# Validation & warnings

The library checks a budget at two points: when you **construct** a
component, and when you **compute** the budget.

## Constructor validation

Component constructors reject values that would produce a crash or nonsense
by raising `ValueError` immediately:

```python
linkbudget.FreeSpacePathLoss("p", "", distance=0.0, frequency=5e9)
# ValueError: distance must be positive (got 0.0)

linkbudget.Mixer("m", "", mode="mix")
# ValueError: mode must be one of ('downconvert', 'upconvert') (got 'mix')

linkbudget.SubBandTune(signal_lower_freq=5e6, signal_upper_freq=2e6)
# ValueError: signal band is empty: signal_upper_freq (2000000.0) must be
#             greater than signal_lower_freq (5000000.0)
```

What is checked: positive distances / frequencies / bandwidths / bit depths /
antenna diameters / integration times; physical temperatures above zero;
aperture efficiency in `(0, 1]`; elevation angle in `(0, 90]`; `role` is
`None` / `"tx"` / `"rx"`; `mixer.mode` is a known value; `SubBandTune` band
edges are non-negative and ordered; `ArrayFactor.num_elements >= 1`.

Where a band mismatch is physically meaningful rather than an error — a
`SubBandTune` whose output band does not overlap the signal band — the
signal is clamped to zero (fully filtered out) instead of going negative.

## Budget checks

After `compute()`, the budget is scanned for configurations that are
syntactically fine but physically dubious. Get the findings explicitly:

```python
for message in budget.check():
    print(message)
```

`check()` returns a list of strings (empty means nothing looked wrong). The
same messages are emitted as
[`LinkBudgetWarning`][linkbudget.checks.LinkBudgetWarning] from `compute()`
(and therefore from `publish()` and `summary()`) unless the container is
built with `warn=False`:

```python
budget = linkbudget.LinkContainer(warn=False)   # silence the warnings
```

What is flagged:

| Check | Why it matters |
|---|---|
| Final signal power is zero | no `SignalSource`, or the signal is fully attenuated |
| A stage produced negative signal or noise power | always a bug or bad input |
| More than one `ThermalNoise` stage | the thermal noise floor is being double-counted |
| A negative `total_loss_db` / `conversion_loss_db` | a "loss" that is really a gain — usually a sign error |
| A path stage's `frequency` differs from the container's `carrier_frequency` | a mismatched frequency (checks stop at the first `Mixer`, which legitimately moves the carrier) |

The scan is a helper, not a guarantee — `check_budget(data_list)` in
[`linkbudget.checks`](../api/checks.md) is a plain function you can call on
any computed `data_list`.
