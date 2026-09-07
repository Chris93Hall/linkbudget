"""
_validate.py

Small input-validation helpers shared by the component constructors.  Each
returns the value unchanged on success and raises ``ValueError`` otherwise,
so they can be used inline:

    self.distance = _validate.positive("distance", distance)
"""

from __future__ import annotations

from typing import Any, Iterable


def positive(name: str, value: float) -> float:
    """Require ``value > 0``."""
    if not value > 0.0:
        raise ValueError(f"{name} must be positive (got {value!r})")
    return value


def non_negative(name: str, value: float) -> float:
    """Require ``value >= 0``."""
    if not value >= 0.0:
        raise ValueError(f"{name} must be non-negative (got {value!r})")
    return value


def in_range(name: str, value: float, low: float, high: float,
             *, low_open: bool = False) -> float:
    """Require ``low <= value <= high`` (``low < value`` if ``low_open``)."""
    low_ok = value > low if low_open else value >= low
    if not (low_ok and value <= high):
        bound = f"({low}, {high}]" if low_open else f"[{low}, {high}]"
        raise ValueError(f"{name} must be in {bound} (got {value!r})")
    return value


def one_of(name: str, value: Any, choices: Iterable[Any]) -> Any:
    """Require ``value`` to be one of ``choices``."""
    choices = tuple(choices)
    if value not in choices:
        raise ValueError(f"{name} must be one of {choices} (got {value!r})")
    return value


def optional_positive(name: str, value: float | None) -> float | None:
    """Require ``value`` to be ``None`` or ``> 0``."""
    return None if value is None else positive(name, value)


def optional_non_negative(name: str, value: float | None) -> float | None:
    """Require ``value`` to be ``None`` or ``>= 0``."""
    return None if value is None else non_negative(name, value)


def optional_in_range(name: str, value: float | None, low: float, high: float,
                      *, low_open: bool = False) -> float | None:
    """Require ``value`` to be ``None`` or within ``[low, high]``."""
    if value is None:
        return None
    return in_range(name, value, low, high, low_open=low_open)
