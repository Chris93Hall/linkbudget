"""
convert.py
"""

from __future__ import annotations

import numpy as np

BOLTZMANN_CONSTANT: float = 1.380649e-23  # joules per kelvin
SPEED_OF_LIGHT: float = 2.99792458e8       # meters per second

def linear_to_db(val: float) -> float:
    if val == 0.0:
        return -np.inf
    return 10.0 * np.log10(val)

def db_to_linear(val: float) -> float:
    return 10.0**(val / 10.0)

def scale_hertz(freq: float) -> tuple[float, str]:
    if freq > 1e3 and freq < 1e6:
        return freq / 1e3, 'kHz'
    if freq > 1e6 and freq < 1e9:
        return freq / 1e6, 'MHz'
    if freq > 1e9:
        return freq / 1e9, 'GHz'
    return freq, 'Hz'
