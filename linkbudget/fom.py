"""
fom.py

Standard link-budget figures of merit, as pure functions working in the
conventional decibel-domain units used in link budgets (dBW, dBi, dB/K,
dB-Hz).  These are the building blocks used by ``LinkContainer.summary()``
but are handy on their own.
"""

from __future__ import annotations

import math
from typing import Sequence

from . import convert


def eirp_dbw(tx_power_dbw: float, tx_antenna_gain_dbi: float,
             tx_loss_db: float = 0.0) -> float:
    """Effective isotropic radiated power (dBW)."""
    return tx_power_dbw + tx_antenna_gain_dbi - tx_loss_db


def g_over_t_db(rx_antenna_gain_dbi: float, system_noise_temp_k: float) -> float:
    """Receiver figure of merit G/T (dB/K)."""
    return rx_antenna_gain_dbi - convert.linear_to_db(system_noise_temp_k)


def noise_figure_to_temp_k(noise_figure_db: float,
                           reference_temp_k: float = convert.REFERENCE_NOISE_TEMP_K) -> float:
    """Equivalent noise temperature (K) of a stage with the given noise figure:
    ``T_e = (F - 1) * T0``."""
    return (convert.db_to_linear(noise_figure_db) - 1.0) * reference_temp_k


def noise_temp_to_figure_db(noise_temp_k: float,
                            reference_temp_k: float = convert.REFERENCE_NOISE_TEMP_K) -> float:
    """Noise figure (dB) equivalent to an excess noise temperature ``T_e``:
    ``F = 1 + T_e / T0``."""
    return convert.linear_to_db(1.0 + noise_temp_k / reference_temp_k)


def friis_total_noise_temp_k(stage_noise_temps_k: Sequence[float],
                             stage_gains_db: Sequence[float]) -> float:
    """Total noise temperature (K) of a cascade, referred to its input, from
    Friis: ``T = T1 + T2/G1 + T3/(G1 G2) + ...``.

    ``stage_gains_db[i]`` is the available power gain (dB) of stage ``i``; the
    last stage's gain is not used.  Both sequences must be the same length.
    """
    if len(stage_noise_temps_k) != len(stage_gains_db):
        raise ValueError("stage_noise_temps_k and stage_gains_db must match in length")
    total = 0.0
    gain_before = 1.0
    for temp_k, gain_db in zip(stage_noise_temps_k, stage_gains_db):
        total += temp_k / gain_before
        gain_before *= convert.db_to_linear(gain_db)
    return total


def friis_total_noise_figure_db(stage_noise_figures_db: Sequence[float],
                                stage_gains_db: Sequence[float]) -> float:
    """Total noise figure (dB) of a cascade from Friis:
    ``F = F1 + (F2-1)/G1 + (F3-1)/(G1 G2) + ...``."""
    temps = [noise_figure_to_temp_k(nf) for nf in stage_noise_figures_db]
    return noise_temp_to_figure_db(friis_total_noise_temp_k(temps, stage_gains_db))


def free_space_path_loss_db(distance_m: float, frequency_hz: float) -> float:
    """Free-space path loss (dB) as a positive number."""
    wavelength = convert.SPEED_OF_LIGHT / frequency_hz
    return convert.linear_to_db((4.0 * math.pi * distance_m / wavelength) ** 2)


def cn0_dbhz(eirp: float, g_over_t: float, path_loss_db: float,
             extra_loss_db: float = 0.0) -> float:
    """Carrier-to-noise-density ratio C/N0 (dB-Hz) from the classic link
    equation ``C/N0 = EIRP + G/T - L_path - L_extra - k`` (with k Boltzmann's
    constant in dBW/K/Hz)."""
    boltzmann_db = convert.linear_to_db(convert.BOLTZMANN_CONSTANT)
    return eirp + g_over_t - path_loss_db - extra_loss_db - boltzmann_db


def cn0_from_snr(snr_db: float, noise_bandwidth_hz: float) -> float:
    """C/N0 (dB-Hz) from a carrier-to-noise ratio measured in a given noise
    bandwidth."""
    return snr_db + convert.linear_to_db(noise_bandwidth_hz)


def cn_db(cn0: float, noise_bandwidth_hz: float) -> float:
    """Carrier-to-noise ratio C/N (dB) in a given noise bandwidth."""
    return cn0 - convert.linear_to_db(noise_bandwidth_hz)


def ebno_db(cn0: float, data_rate_bps: float) -> float:
    """Energy-per-bit to noise-density ratio Eb/N0 (dB)."""
    return cn0 - convert.linear_to_db(data_rate_bps)


def esno_db(cn0: float, symbol_rate_bd: float) -> float:
    """Energy-per-symbol to noise-density ratio Es/N0 (dB)."""
    return cn0 - convert.linear_to_db(symbol_rate_bd)


def shannon_capacity_bps(bandwidth_hz: float, snr_linear: float) -> float:
    """Shannon-Hartley channel capacity (bits/s)."""
    return bandwidth_hz * math.log2(1.0 + snr_linear)


def spectral_efficiency(data_rate_bps: float, bandwidth_hz: float) -> float:
    """Spectral efficiency (bits/s/Hz)."""
    return data_rate_bps / bandwidth_hz
