"""
convert.py
"""

import numpy as np

BOLTZMANN_CONSTANT = 1.380649e-23  # joules per kelvin

def linear_to_db(val):
    if val == 0.0:
        return -np.inf
    return 10.0 * np.log10(val)

def db_to_linear(val):
    return 10.0**(val / 10.0)

def scale_hertz(freq):
    if freq > 1e3 and freq < 1e6:
        return freq / 1e3, 'kHz'
    if freq > 1e6 and freq < 1e9:
        return freq / 1e6, 'MHz'
    if freq > 1e9:
        return freq / 1e9, 'GHz'
    return freq, 'Hz'
