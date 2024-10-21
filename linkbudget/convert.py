"""
convert.py
"""

import numpy as np

def linear_to_db(val):
    return 10.0 * np.log10(val)

def db_to_linear(val):
    return 10.0**(val / 10.0)
