"""
convert.py

Unit conversions and physical constants used throughout the package.

Powers flow through a budget as *linear* quantities (watts, or whatever
consistent unit you choose); these helpers move between that linear domain
and decibels, and scale a frequency for display.
"""

from __future__ import annotations

import numpy as np

BOLTZMANN_CONSTANT: float = 1.380649e-23  # joules per kelvin
SPEED_OF_LIGHT: float = 2.99792458e8       # meters per second
#: IEEE standard reference temperature ``T0`` for noise-figure definitions (K).
#: A noise figure ``F`` is the excess noise a stage adds referred to a source
#: at this temperature: ``T_excess = (F - 1) * T0``.
REFERENCE_NOISE_TEMP_K: float = 290.0


def linear_to_db(val: float) -> float:
    """Convert a linear power ratio to decibels (``10*log10(val)``).

    A ``val`` of exactly zero returns ``-inf`` rather than raising.
    """
    if val == 0.0:
        return -np.inf
    return 10.0 * np.log10(val)


def db_to_linear(val: float) -> float:
    """Convert a decibel value to a linear power ratio (``10**(val/10)``)."""
    return 10.0**(val / 10.0)


def scale_hertz(freq: float) -> tuple[float, str]:
    """Scale a frequency in Hz to the most readable unit for display.

    Returns ``(value, unit)`` where ``unit`` is one of ``"Hz"``, ``"kHz"``,
    ``"MHz"`` or ``"GHz"``.
    """
    if freq > 1e3 and freq < 1e6:
        return freq / 1e3, 'kHz'
    if freq > 1e6 and freq < 1e9:
        return freq / 1e6, 'MHz'
    if freq > 1e9:
        return freq / 1e9, 'GHz'
    return freq, 'Hz'
