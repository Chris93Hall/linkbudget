"""
fom.py

Standard link-budget figures of merit, as pure functions working in the
conventional decibel-domain units used in link budgets (dBW, dBi, dB/K,
dB-Hz).  These are the building blocks used by ``LinkContainer.summary()``
but are handy on their own.
"""

import math

from . import convert


def eirp_dbw(tx_power_dbw, tx_antenna_gain_dbi, tx_loss_db=0.0):
    """Effective isotropic radiated power (dBW)."""
    return tx_power_dbw + tx_antenna_gain_dbi - tx_loss_db


def g_over_t_db(rx_antenna_gain_dbi, system_noise_temp_k):
    """Receiver figure of merit G/T (dB/K)."""
    return rx_antenna_gain_dbi - convert.linear_to_db(system_noise_temp_k)


def free_space_path_loss_db(distance_m, frequency_hz):
    """Free-space path loss (dB) as a positive number."""
    wavelength = convert.SPEED_OF_LIGHT / frequency_hz
    return convert.linear_to_db((4.0 * math.pi * distance_m / wavelength) ** 2)


def cn0_dbhz(eirp, g_over_t, path_loss_db, extra_loss_db=0.0):
    """Carrier-to-noise-density ratio C/N0 (dB-Hz) from the classic link
    equation ``C/N0 = EIRP + G/T - L_path - L_extra - k`` (with k Boltzmann's
    constant in dBW/K/Hz)."""
    boltzmann_db = convert.linear_to_db(convert.BOLTZMANN_CONSTANT)
    return eirp + g_over_t - path_loss_db - extra_loss_db - boltzmann_db


def cn0_from_snr(snr_db, noise_bandwidth_hz):
    """C/N0 (dB-Hz) from a carrier-to-noise ratio measured in a given noise
    bandwidth."""
    return snr_db + convert.linear_to_db(noise_bandwidth_hz)


def cn_db(cn0, noise_bandwidth_hz):
    """Carrier-to-noise ratio C/N (dB) in a given noise bandwidth."""
    return cn0 - convert.linear_to_db(noise_bandwidth_hz)


def ebno_db(cn0, data_rate_bps):
    """Energy-per-bit to noise-density ratio Eb/N0 (dB)."""
    return cn0 - convert.linear_to_db(data_rate_bps)


def esno_db(cn0, symbol_rate_bd):
    """Energy-per-symbol to noise-density ratio Es/N0 (dB)."""
    return cn0 - convert.linear_to_db(symbol_rate_bd)


def shannon_capacity_bps(bandwidth_hz, snr_linear):
    """Shannon-Hartley channel capacity (bits/s)."""
    return bandwidth_hz * math.log2(1.0 + snr_linear)


def spectral_efficiency(data_rate_bps, bandwidth_hz):
    """Spectral efficiency (bits/s/Hz)."""
    return data_rate_bps / bandwidth_hz
