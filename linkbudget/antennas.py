"""
antennas.py

Antenna gain / beamwidth / pointing / polarization models.  The component
classes here return the same stage dict as the components in
``link_container`` and drop straight into a ``LinkContainer``.
"""

from __future__ import annotations

import math

from . import convert
from ._types import StageData
from .link_container import Component

DEFAULT_APERTURE_EFFICIENCY: float = 0.55
# rule-of-thumb constant relating -3 dB beamwidth to lambda / D for a dish
BEAMWIDTH_CONSTANT_DEG: float = 70.0


def dish_gain_dbi(diameter_m: float, frequency_hz: float,
                  efficiency: float = DEFAULT_APERTURE_EFFICIENCY) -> float:
    """Boresight gain (dBi) of a circular-aperture (parabolic) antenna."""
    wavelength = convert.SPEED_OF_LIGHT / frequency_hz
    return convert.linear_to_db(efficiency * (math.pi * diameter_m / wavelength) ** 2)


def dish_half_power_beamwidth_deg(diameter_m: float, frequency_hz: float,
                                  beamwidth_constant: float = BEAMWIDTH_CONSTANT_DEG) -> float:
    """Approximate half-power (-3 dB) beamwidth (degrees) of a parabolic dish."""
    wavelength = convert.SPEED_OF_LIGHT / frequency_hz
    return beamwidth_constant * wavelength / diameter_m


def gaussian_beam_pointing_loss_db(offset_deg: float,
                                   half_power_beamwidth_deg: float) -> float:
    """Main-lobe loss (dB) for a direction ``offset_deg`` off boresight of a
    beam with the given -3 dB beamwidth, using the standard quadratic
    (Gaussian) approximation ``L = 12 (offset / HPBW)**2``."""
    return 12.0 * (offset_deg / half_power_beamwidth_deg) ** 2


def polarization_efficiency(axial_ratio_db_1: float, axial_ratio_db_2: float,
                            tilt_angle_deg: float = 0.0) -> float:
    """Polarization matching efficiency (0..1) between two elliptically
    polarized antennas with the given axial ratios (dB) and relative tilt.

    ``AR = 0`` dB is perfectly circular; a large ``AR`` approaches linear.
    Circular-to-circular aligned gives 1.0, circular-to-linear gives 0.5
    (3 dB), crossed linears give 0.0.
    """
    ratio_1 = 10.0 ** (abs(axial_ratio_db_1) / 20.0)
    ratio_2 = 10.0 ** (abs(axial_ratio_db_2) / 20.0)
    delta = math.radians(tilt_angle_deg)
    numerator = (4.0 * ratio_1 * ratio_2
                 + (ratio_1 ** 2 - 1.0) * (ratio_2 ** 2 - 1.0) * math.cos(2.0 * delta))
    denominator = 2.0 * (ratio_1 ** 2 + 1.0) * (ratio_2 ** 2 + 1.0)
    return 0.5 + numerator / denominator


class ParabolicDish(Component):
    """Parabolic (circular-aperture) antenna.

    Gain and -3 dB beamwidth are derived from the physical diameter,
    frequency and aperture efficiency.  Like ``Gain``, the component applies
    its gain to both the signal and the noise.  Pass ``role="rx"`` (or
    ``"tx"``) so ``LinkContainer.summary()`` can pick out the receive antenna
    when computing G/T.
    """

    def __init__(self, name: str = "Parabolic dish", description: str = "",
                 diameter: float = 1.0, frequency: float = 1e9,
                 efficiency: float = DEFAULT_APERTURE_EFFICIENCY,
                 role: str | None = None) -> None:
        self.name = name
        self.description = description
        self.diameter = diameter
        self.frequency = frequency
        self.efficiency = efficiency
        self.role = role

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        gain_dbi = dish_gain_dbi(self.diameter, self.frequency, self.efficiency)
        beamwidth_deg = dish_half_power_beamwidth_deg(self.diameter, self.frequency)
        gain_linear = convert.db_to_linear(gain_dbi)
        return {"name": self.name,
                "description": self.description,
                "signal_power_in": signal_power,
                "noise_power_in": noise_power,
                "signal_power_out": signal_power * gain_linear,
                "noise_power_out": noise_power * gain_linear,
                "diameter": self.diameter,
                "frequency": self.frequency,
                "aperture_efficiency": self.efficiency,
                "gain_dbi": gain_dbi,
                "half_power_beamwidth_deg": beamwidth_deg}


class BeamPointingLoss(Component):
    """Pointing loss from a finite beamwidth and a pointing error.

    Either give ``half_power_beamwidth_deg`` directly, or give an antenna
    ``diameter`` and ``frequency`` to derive it from a parabolic-dish model.
    """

    def __init__(self, name: str = "Beam pointing loss", description: str = "",
                 pointing_error_deg: float = 0.0,
                 half_power_beamwidth_deg: float | None = None,
                 diameter: float | None = None, frequency: float | None = None) -> None:
        self.name = name
        self.description = description
        self.pointing_error_deg = pointing_error_deg
        if half_power_beamwidth_deg is None:
            if diameter is None or frequency is None:
                raise ValueError(
                    "give half_power_beamwidth_deg, or both diameter and frequency")
            half_power_beamwidth_deg = dish_half_power_beamwidth_deg(diameter, frequency)
        self.half_power_beamwidth_deg = half_power_beamwidth_deg

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        loss_db = gaussian_beam_pointing_loss_db(
            self.pointing_error_deg, self.half_power_beamwidth_deg)
        loss_linear = convert.db_to_linear(loss_db)
        return {"name": self.name,
                "description": self.description,
                "signal_power_in": signal_power,
                "noise_power_in": noise_power,
                "signal_power_out": signal_power / loss_linear,
                "noise_power_out": noise_power,
                "pointing_error_deg": self.pointing_error_deg,
                "half_power_beamwidth_deg": self.half_power_beamwidth_deg,
                "pointing_loss_db": loss_db}


class PolarizationMismatchLoss(Component):
    """Loss from a polarization mismatch between the transmit and receive
    antennas, computed from their axial ratios (dB) and relative tilt."""

    def __init__(self, name: str = "Polarization mismatch loss", description: str = "",
                 axial_ratio_db_tx: float = 0.0, axial_ratio_db_rx: float = 0.0,
                 tilt_angle_deg: float = 0.0) -> None:
        self.name = name
        self.description = description
        self.axial_ratio_db_tx = axial_ratio_db_tx
        self.axial_ratio_db_rx = axial_ratio_db_rx
        self.tilt_angle_deg = tilt_angle_deg

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        efficiency = polarization_efficiency(
            self.axial_ratio_db_tx, self.axial_ratio_db_rx, self.tilt_angle_deg)
        loss_db = -convert.linear_to_db(efficiency)
        return {"name": self.name,
                "description": self.description,
                "signal_power_in": signal_power,
                "noise_power_in": noise_power,
                "signal_power_out": signal_power * efficiency,
                "noise_power_out": noise_power,
                "axial_ratio_db_tx": self.axial_ratio_db_tx,
                "axial_ratio_db_rx": self.axial_ratio_db_rx,
                "tilt_angle_deg": self.tilt_angle_deg,
                "polarization_efficiency": efficiency,
                "polarization_loss_db": loss_db}
