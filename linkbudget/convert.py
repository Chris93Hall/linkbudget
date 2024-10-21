"""
convert.py
"""

import numpy as np

def linear_to_db(val):
    if val == 0.0:
        return -np.inf
    return 10.0 * np.log10(val)

def db_to_linear(val):
    return 10.0**(val / 10.0)
