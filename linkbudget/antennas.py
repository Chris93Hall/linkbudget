"""
antennas.py

Antenna gain / beamwidth / pointing / polarization models.  The component
classes here return the same stage dict as the components in
``link_container`` and drop straight into a ``LinkContainer``.
"""

from __future__ import annotations

import math

from . import _validate, convert
from ._types import StageData
from .link_container import Component

DEFAULT_APERTURE_EFFICIENCY: float = 0.55
# rule-of-thumb constant relating -3 dB beamwidth to lambda / D for a dish
BEAMWIDTH_CONSTANT_DEG: float = 70.0


def dish_gain_dbi(diameter_m: float, frequency_hz: float,
                  efficiency: float = DEFAULT_APERTURE_EFFICIENCY) -> float:
    """Boresight gain (dBi) of a circular-aperture (parabolic) antenna."""
    _validate.positive("diameter_m", diameter_m)
    _validate.positive("frequency_hz", frequency_hz)
    _validate.in_range("efficiency", efficiency, 0.0, 1.0, low_open=True)
    wavelength = convert.SPEED_OF_LIGHT / frequency_hz
    return convert.linear_to_db(efficiency * (math.pi * diameter_m / wavelength) ** 2)


def dish_half_power_beamwidth_deg(diameter_m: float, frequency_hz: float,
                                  beamwidth_constant: float = BEAMWIDTH_CONSTANT_DEG) -> float:
    """Approximate half-power (-3 dB) beamwidth (degrees) of a parabolic dish."""
    _validate.positive("diameter_m", diameter_m)
    _validate.positive("frequency_hz", frequency_hz)
    wavelength = convert.SPEED_OF_LIGHT / frequency_hz
    return beamwidth_constant * wavelength / diameter_m


def gaussian_beam_pointing_loss_db(offset_deg: float,
                                   half_power_beamwidth_deg: float) -> float:
    """Main-lobe loss (dB) for a direction ``offset_deg`` off boresight of a
    beam with the given -3 dB beamwidth, using the standard quadratic
    (Gaussian) approximation ``L = 12 (offset / HPBW)**2``."""
    _validate.non_negative("offset_deg", offset_deg)
    _validate.positive("half_power_beamwidth_deg", half_power_beamwidth_deg)
    return 12.0 * (offset_deg / half_power_beamwidth_deg) ** 2


def antenna_noise_temp_k(sky_temp_k: float, ground_temp_k: float = 290.0,
                         ground_coupling: float = 0.0,
                         radiation_efficiency: float = 1.0,
                         physical_temp_k: float = 290.0) -> float:
    """Antenna noise temperature (K) at the feed port.

    The beam sees a scene that is a fraction ``ground_coupling`` warm ground
    (``ground_temp_k``) and the rest cold sky (``sky_temp_k`` -- the
    atmospheric-emission brightness temperature seen along the path, which
    already includes the ~2.7 K cosmic background)::

        T_scene = (1 - ground_coupling) * sky_temp_k + ground_coupling * ground_temp_k

    Ohmic / feed loss with radiation efficiency ``radiation_efficiency`` (0..1)
    then attenuates that scene and adds its own physical-temperature noise::

        T_a = radiation_efficiency * T_scene + (1 - radiation_efficiency) * physical_temp_k
    """
    _validate.non_negative("sky_temp_k", sky_temp_k)
    _validate.non_negative("ground_temp_k", ground_temp_k)
    _validate.in_range("ground_coupling", ground_coupling, 0.0, 1.0)
    _validate.in_range("radiation_efficiency", radiation_efficiency, 0.0, 1.0, low_open=True)
    _validate.non_negative("physical_temp_k", physical_temp_k)
    scene_temp_k = ((1.0 - ground_coupling) * sky_temp_k
                    + ground_coupling * ground_temp_k)
    return (radiation_efficiency * scene_temp_k
            + (1.0 - radiation_efficiency) * physical_temp_k)


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
        self.diameter = _validate.positive("diameter", diameter)
        self.frequency = _validate.positive("frequency", frequency)
        self.efficiency = _validate.in_range("efficiency", efficiency, 0.0, 1.0, low_open=True)
        self.role = _validate.one_of("role", role, (None, "tx", "rx"))

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Apply the dish boresight gain to the signal and the noise."""
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
        self.pointing_error_deg = _validate.non_negative(
            "pointing_error_deg", pointing_error_deg)
        if half_power_beamwidth_deg is None:
            if diameter is None or frequency is None:
                raise ValueError(
                    "give half_power_beamwidth_deg, or both diameter and frequency")
            half_power_beamwidth_deg = dish_half_power_beamwidth_deg(diameter, frequency)
        self.half_power_beamwidth_deg = _validate.positive(
            "half_power_beamwidth_deg", half_power_beamwidth_deg)

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Attenuate the signal by the pointing loss (noise unchanged)."""
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
        """Scale the signal by the polarization efficiency (noise unchanged)."""
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


class AntennaNoiseTemperature(Component):
    """Antenna noise-temperature floor: injects ``k * T_a * bandwidth`` watts
    of noise, where ``T_a`` is composed from the sky brightness temperature,
    ground pickup and the antenna's own ohmic loss (see `antenna_noise_temp_k`).

    This is the receive-side counterpart to a `ThermalNoise` receiver floor:
    put it right after the receive antenna to establish the noise entering the
    front end.  ``sky_temp_k`` is the atmospheric-emission brightness
    temperature along the path (roughly ``T_phys * (1 - 10**(-A_atm_db/10))``
    plus the 2.7 K cosmic background, so a few K at high elevation in clear
    air, tens of K through rain).  With ``radiation_efficiency < 1`` the ohmic
    loss also attenuates the signal, exactly like a matched lossy stage.
    """

    def __init__(self, name: str = "Antenna noise", description: str = "",
                 sky_temp_k: float = 10.0, ground_temp_k: float = 290.0,
                 ground_coupling: float = 0.0, radiation_efficiency: float = 1.0,
                 physical_temp_k: float = 290.0, bandwidth: float = 1.0) -> None:
        self.name = name
        self.description = description
        self.sky_temp_k = _validate.non_negative("sky_temp_k", sky_temp_k)
        self.ground_temp_k = _validate.non_negative("ground_temp_k", ground_temp_k)
        self.ground_coupling = _validate.in_range(
            "ground_coupling", ground_coupling, 0.0, 1.0)
        self.radiation_efficiency = _validate.in_range(
            "radiation_efficiency", radiation_efficiency, 0.0, 1.0, low_open=True)
        self.physical_temp_k = _validate.non_negative("physical_temp_k", physical_temp_k)
        self.bandwidth = _validate.positive("bandwidth", bandwidth)

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Attenuate by the ohmic loss and add ``k * T_a * bandwidth``."""
        antenna_temp_k = antenna_noise_temp_k(
            self.sky_temp_k, self.ground_temp_k, self.ground_coupling,
            self.radiation_efficiency, self.physical_temp_k)
        antenna_noise_power = (convert.BOLTZMANN_CONSTANT * antenna_temp_k
                               * self.bandwidth)
        efficiency = self.radiation_efficiency
        scene_temp_k = ((1.0 - self.ground_coupling) * self.sky_temp_k
                        + self.ground_coupling * self.ground_temp_k)
        return {"name": self.name,
                "description": self.description,
                "signal_power_in": signal_power,
                "noise_power_in": noise_power,
                "signal_power_out": signal_power * efficiency,
                "noise_power_out": noise_power * efficiency + antenna_noise_power,
                "sky_temp_k": self.sky_temp_k,
                "ground_temp_k": self.ground_temp_k,
                "ground_coupling": self.ground_coupling,
                "radiation_efficiency": efficiency,
                "physical_temp_k": self.physical_temp_k,
                "bandwidth": self.bandwidth,
                "scene_noise_temp_k": scene_temp_k,
                "antenna_noise_temp_k": antenna_temp_k,
                "antenna_noise_power": antenna_noise_power}
