"""
checks.py

Post-computation sanity checks for a link budget.

``check_budget`` inspects a computed ``data_list`` and returns a list of
human-readable warnings about physically dubious or likely-wrong budgets.
``LinkContainer`` emits them via ``warnings.warn`` after ``compute()``
(unless it was constructed with ``check=False``), and
``LinkContainer.check()`` returns the list directly.
"""

from __future__ import annotations

from ._types import StageList

# keys whose value is a loss in dB and so should not be negative -- a negative
# "loss" is really a gain and usually a sign error
_LOSS_KEYS = ("total_loss_db", "conversion_loss_db")


class LinkBudgetWarning(UserWarning):
    """Category for warnings about a dubious link budget."""


def _number(value: object) -> float | None:
    """``value`` as a float when it is a real number, else ``None``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def check_budget(data_list: StageList,
                 carrier_frequency: float | None = None) -> list[str]:
    """Return a list of warning messages about ``data_list`` (a computed
    budget).  An empty list means nothing suspicious was found."""
    issues: list[str] = []
    if not data_list:
        return issues

    _check_negative_power(data_list, issues)
    _check_no_signal(data_list, issues)
    _check_repeated_noise_floor(data_list, issues)
    _check_negative_loss(data_list, issues)
    _check_carrier_frequency(data_list, carrier_frequency, issues)
    return issues


def _check_negative_power(data_list: StageList, issues: list[str]) -> None:
    for stage in data_list:
        for key in ("signal_power_out", "noise_power_out"):
            value = _number(stage.get(key))
            if value is not None and value < 0.0:
                issues.append(
                    f"stage {stage['name']!r} produced negative "
                    f"{key.replace('_', ' ')} ({value:.3g})")


def _check_no_signal(data_list: StageList, issues: list[str]) -> None:
    final_signal = _number(data_list[-1].get("signal_power_out"))
    if final_signal is not None and final_signal <= 0.0:
        issues.append(
            f"final signal power is {final_signal:.3g}; the budget has no signal "
            "source, or the signal is fully attenuated")


def _check_repeated_noise_floor(data_list: StageList, issues: list[str]) -> None:
    thermal = [stage["name"] for stage in data_list if "thermal_noise_power" in stage]
    if len(thermal) > 1:
        names = ", ".join(repr(name) for name in thermal)
        issues.append(
            f"thermal noise floor added {len(thermal)} times ({names}); "
            "noise is being double-counted")


def _check_negative_loss(data_list: StageList, issues: list[str]) -> None:
    for stage in data_list:
        for key in _LOSS_KEYS:
            value = _number(stage.get(key))
            if value is not None and value < 0.0:
                issues.append(
                    f"stage {stage['name']!r} has {key.replace('_', ' ')} = "
                    f"{value:.3g} (a negative loss is a gain)")


def _check_carrier_frequency(data_list: StageList, carrier_frequency: float | None,
                             issues: list[str]) -> None:
    if not carrier_frequency:
        return
    mixed = False
    for stage in data_list:
        if stage.get("if_frequency") is not None:
            mixed = True  # a mixer has moved the carrier; later stages differ by design
        freq = _number(stage.get("frequency"))
        if (not mixed and freq is not None and freq > 0.0
                and abs(freq - carrier_frequency) / carrier_frequency > 0.01):
            issues.append(
                f"stage {stage['name']!r} uses frequency {freq:.4g} Hz but the "
                f"budget's carrier_frequency is {carrier_frequency:.4g} Hz")
