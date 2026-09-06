"""
propagation.py

Atmospheric and terrain propagation-loss models: simplified engineering
implementations of the relevant ITU-R Recommendations plus a two-ray
ground-reflection model.  Each class is a drop-in ``LinkContainer``
component (it returns the same stage dict as the components in
``link_container``) and is tagged ``is_propagation = True`` so that
``LinkContainer.summary()`` folds it into the total path loss.

The models are deliberately compact approximations, not line-by-line
reference implementations:

* ``AtmosphericAbsorption``   -- ITU-R P.676 Annex 2 (gaseous, f <= 57 GHz)
* ``RainAttenuation``         -- ITU-R P.838-3 + P.618 slant path
* ``CloudFogAttenuation``     -- ITU-R P.840 double-Debye liquid water
* ``TroposphericScintillation`` -- ITU-R P.618 section 2.4.1
* ``TwoRayGroundReflection``  -- plane-earth two-ray model
"""

from __future__ import annotations

import math
from typing import Any

from . import convert
from ._types import StageData
from .link_container import Component

# --------------------------------------------------------------------------
# gaseous absorption -- ITU-R P.676 Annex 2 (simplified)
# --------------------------------------------------------------------------

def oxygen_specific_attenuation_db_per_km(frequency_ghz: float) -> float:
    """Specific attenuation from dry air / oxygen (dB/km), valid f <= 57 GHz."""
    freq = frequency_ghz
    return (7.19e-3
            + 6.09 / (freq ** 2 + 0.227)
            + 4.81 / ((freq - 57.0) ** 2 + 1.50)) * freq ** 2 * 1e-3


def water_vapor_specific_attenuation_db_per_km(frequency_ghz: float,
                                               water_vapor_density: float = 7.5) -> float:
    """Specific attenuation from water vapour (dB/km).

    ``water_vapor_density`` is the absolute humidity in g/m**3 (7.5 is the
    ITU-R reference value)."""
    freq = frequency_ghz
    rho = water_vapor_density
    return (0.050
            + 0.0021 * rho
            + 3.6 / ((freq - 22.2) ** 2 + 8.5)
            + 10.6 / ((freq - 183.3) ** 2 + 9.0)
            + 8.9 / ((freq - 325.4) ** 2 + 26.3)) * freq ** 2 * rho * 1e-4


class AtmosphericAbsorption(Component):
    """Clear-air gaseous absorption (oxygen + water vapour).

    Give a horizontal ``path_length_km`` directly, or give an
    ``elevation_deg`` for a slant path through the atmosphere (the path is
    then computed from the gas equivalent heights ``oxygen_height_km`` and
    ``water_height_km``).
    """

    is_propagation = True

    def __init__(self, name: str = "Atmospheric absorption", description: str = "",
                 frequency: float = 1e9, water_vapor_density: float = 7.5,
                 path_length_km: float | None = None, elevation_deg: float | None = None,
                 oxygen_height_km: float = 6.0, water_height_km: float = 2.1) -> None:
        self.name = name
        self.description = description
        self.frequency = frequency
        self.water_vapor_density = water_vapor_density
        if path_length_km is None and elevation_deg is None:
            raise ValueError("give path_length_km or elevation_deg")
        self.path_length_km = path_length_km
        self.elevation_deg = elevation_deg
        self.oxygen_height_km = oxygen_height_km
        self.water_height_km = water_height_km

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        freq_ghz = self.frequency / 1e9
        gamma_o = oxygen_specific_attenuation_db_per_km(freq_ghz)
        gamma_w = water_vapor_specific_attenuation_db_per_km(
            freq_ghz, self.water_vapor_density)

        if self.path_length_km is not None:
            path_km = self.path_length_km
            loss_db = (gamma_o + gamma_w) * path_km
        else:
            assert self.elevation_deg is not None  # guaranteed by __init__
            sin_elev = math.sin(math.radians(self.elevation_deg))
            loss_db = (gamma_o * self.oxygen_height_km
                       + gamma_w * self.water_height_km) / sin_elev
            path_km = (self.oxygen_height_km + self.water_height_km) / sin_elev

        loss_linear = convert.db_to_linear(loss_db)
        return {"name": self.name,
                "description": self.description,
                "signal_power_in": signal_power,
                "noise_power_in": noise_power,
                "signal_power_out": signal_power / loss_linear,
                "noise_power_out": noise_power / loss_linear,
                "frequency": self.frequency,
                "oxygen_specific_attenuation_db_per_km": gamma_o,
                "water_vapor_specific_attenuation_db_per_km": gamma_w,
                "path_length_km": path_km,
                "atmospheric_loss_db": loss_db}


# --------------------------------------------------------------------------
# rain attenuation -- ITU-R P.838-3 (specific attenuation) + P.618 (slant path)
# --------------------------------------------------------------------------

_P838: dict[str, dict[str, Any]] = {
    "kh": {
        "a": [-5.33980, -0.35351, -0.23789, -0.94158],
        "b": [-0.10008, 1.26970, 0.86036, 0.64552],
        "c": [1.13098, 0.45400, 0.15354, 0.16817],
        "m": -0.18961, "const": 0.71147,
    },
    "kv": {
        "a": [-3.80595, -3.44965, -0.39902, 0.50167],
        "b": [0.56934, -0.22911, 0.73042, 1.07319],
        "c": [0.81061, 0.51059, 0.11899, 0.27195],
        "m": -0.16398, "const": 0.63297,
    },
    "ah": {
        "a": [-0.14318, 0.29591, 0.32177, -5.37610, 16.1721],
        "b": [1.82442, 0.77564, 0.63773, -0.96230, -3.29980],
        "c": [-0.55187, 0.19822, 0.13164, 1.47828, 3.43990],
        "m": 0.67849, "const": -1.95537,
    },
    "av": {
        "a": [-0.07771, 0.56727, -0.20238, -48.2991, 48.5833],
        "b": [2.33840, 0.95545, 1.14520, 0.791669, 0.791459],
        "c": [-0.76284, 0.54039, 0.26809, 0.116226, 0.116479],
        "m": -0.053739, "const": 0.83433,
    },
}


def _p838_fit(coef: dict[str, Any], log_freq: float) -> float:
    total = sum(a * math.exp(-((log_freq - b) / c) ** 2)
                for a, b, c in zip(coef["a"], coef["b"], coef["c"]))
    return total + coef["m"] * log_freq + coef["const"]


def rain_kalpha(frequency_hz: float, polarization_tilt_deg: float = 45.0,
                elevation_deg: float = 90.0) -> tuple[float, float]:
    """ITU-R P.838-3 ``k`` and ``alpha`` for the given frequency, polarization
    tilt (45 deg = circular) and path elevation."""
    log_freq = math.log10(frequency_hz / 1e9)
    k_h = 10.0 ** _p838_fit(_P838["kh"], log_freq)
    k_v = 10.0 ** _p838_fit(_P838["kv"], log_freq)
    a_h = _p838_fit(_P838["ah"], log_freq)
    a_v = _p838_fit(_P838["av"], log_freq)

    tau = math.radians(polarization_tilt_deg)
    theta = math.radians(elevation_deg)
    cos2 = math.cos(theta) ** 2 * math.cos(2.0 * tau)
    k = (k_h + k_v + (k_h - k_v) * cos2) / 2.0
    alpha = (k_h * a_h + k_v * a_v + (k_h * a_h - k_v * a_v) * cos2) / (2.0 * k)
    return k, alpha


def rain_specific_attenuation_db_per_km(frequency_hz: float, rain_rate_mm_h: float,
                                        polarization_tilt_deg: float = 45.0,
                                        elevation_deg: float = 90.0) -> float:
    """ITU-R P.838-3 specific rain attenuation ``gamma_R = k R**alpha`` (dB/km)."""
    if rain_rate_mm_h <= 0.0:
        return 0.0
    k, alpha = rain_kalpha(frequency_hz, polarization_tilt_deg, elevation_deg)
    return k * rain_rate_mm_h ** alpha


class RainAttenuation(Component):
    """Rain attenuation.

    Two ways to specify the path:

    * ``path_length_km`` -- a horizontal path; an ITU-R style effective-length
      reduction factor is applied.
    * ``elevation_deg`` + ``rain_height_km`` + ``station_height_km`` -- a
      slant path, using the ITU-R P.618 0.01 % reduction and vertical
      adjustment factors.  ``latitude_deg`` refines the vertical factor.
    """

    is_propagation = True

    def __init__(self, name: str = "Rain attenuation", description: str = "",
                 frequency: float = 1e9, rain_rate: float = 0.0,
                 polarization_tilt_deg: float = 45.0, path_length_km: float | None = None,
                 elevation_deg: float | None = None, rain_height_km: float = 3.0,
                 station_height_km: float = 0.0, latitude_deg: float | None = None) -> None:
        self.name = name
        self.description = description
        self.frequency = frequency
        self.rain_rate = rain_rate
        self.polarization_tilt_deg = polarization_tilt_deg
        if path_length_km is None and elevation_deg is None:
            raise ValueError("give path_length_km or elevation_deg")
        self.path_length_km = path_length_km
        self.elevation_deg = elevation_deg
        self.rain_height_km = rain_height_km
        self.station_height_km = station_height_km
        self.latitude_deg = latitude_deg

    def _effective_path_km(self, gamma_r: float) -> float:
        freq_ghz = self.frequency / 1e9
        if self.path_length_km is not None:
            length = self.path_length_km
            reduction = 1.0 / (1.0 + 0.78 * math.sqrt(length * gamma_r / freq_ghz)
                               - 0.38 * (1.0 - math.exp(-2.0 * length)))
            return length * max(min(reduction, 2.5), 0.0)

        assert self.elevation_deg is not None  # guaranteed by __init__
        theta = math.radians(self.elevation_deg)
        delta_h = max(self.rain_height_km - self.station_height_km, 1e-6)
        slant = delta_h / math.sin(theta)
        horiz = slant * math.cos(theta)
        reduction = 1.0 / (1.0 + 0.78 * math.sqrt(horiz * gamma_r / freq_ghz)
                           - 0.38 * (1.0 - math.exp(-2.0 * horiz)))
        zeta = math.degrees(math.atan2(delta_h, horiz * reduction))
        if zeta > self.elevation_deg:
            length_r = horiz * reduction / math.cos(theta)
        else:
            length_r = delta_h / math.sin(theta)
        chi = 0.0
        if self.latitude_deg is not None and abs(self.latitude_deg) < 36.0:
            chi = 36.0 - abs(self.latitude_deg)
        vertical = 1.0 / (1.0 + math.sqrt(math.sin(theta))
                          * (31.0 * (1.0 - math.exp(-self.elevation_deg / (1.0 + chi)))
                             * math.sqrt(length_r * gamma_r) / freq_ghz ** 2 - 0.45))
        return length_r * vertical

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        elevation = self.elevation_deg if self.elevation_deg is not None else 90.0
        gamma_r = rain_specific_attenuation_db_per_km(
            self.frequency, self.rain_rate, self.polarization_tilt_deg, elevation)
        effective_km = self._effective_path_km(gamma_r) if gamma_r > 0.0 else 0.0
        loss_db = gamma_r * effective_km
        loss_linear = convert.db_to_linear(loss_db)
        return {"name": self.name,
                "description": self.description,
                "signal_power_in": signal_power,
                "noise_power_in": noise_power,
                "signal_power_out": signal_power / loss_linear,
                "noise_power_out": noise_power / loss_linear,
                "frequency": self.frequency,
                "rain_rate_mm_h": self.rain_rate,
                "specific_attenuation_db_per_km": gamma_r,
                "effective_path_length_km": effective_km,
                "rain_loss_db": loss_db}


# --------------------------------------------------------------------------
# cloud / fog attenuation -- ITU-R P.840 double-Debye
# --------------------------------------------------------------------------

def cloud_specific_attenuation_coefficient(frequency_hz: float,
                                           temperature_k: float = 273.15) -> float:
    """ITU-R P.840 cloud liquid-water specific attenuation coefficient
    ``K_l`` in (dB/km) per (g/m**3)."""
    freq_ghz = frequency_hz / 1e9
    theta = 300.0 / temperature_k
    eps0 = 77.66 + 103.3 * (theta - 1.0)
    eps1 = 0.0671 * eps0
    eps2 = 3.52
    fp = 20.20 - 146.0 * (theta - 1.0) + 316.0 * (theta - 1.0) ** 2
    fs = 39.8 * fp
    eps_pp = (freq_ghz * (eps0 - eps1) / (fp * (1.0 + (freq_ghz / fp) ** 2))
              + freq_ghz * (eps1 - eps2) / (fs * (1.0 + (freq_ghz / fs) ** 2)))
    eps_p = ((eps0 - eps1) / (1.0 + (freq_ghz / fp) ** 2)
             + (eps1 - eps2) / (1.0 + (freq_ghz / fs) ** 2) + eps2)
    eta = (2.0 + eps_p) / eps_pp
    return 0.819 * freq_ghz / (eps_pp * (1.0 + eta ** 2))


class CloudFogAttenuation(Component):
    """Attenuation from cloud / fog liquid water (ITU-R P.840).

    Give either a columnar ``liquid_water_path`` (kg/m**2, i.e. the integrated
    content) with an ``elevation_deg``, or a ``liquid_water_density``
    (g/m**3) with a ``path_length_km``.
    """

    is_propagation = True

    def __init__(self, name: str = "Cloud / fog attenuation", description: str = "",
                 frequency: float = 1e9, temperature_k: float = 273.15,
                 liquid_water_path: float | None = None, elevation_deg: float = 90.0,
                 liquid_water_density: float | None = None,
                 path_length_km: float | None = None) -> None:
        self.name = name
        self.description = description
        self.frequency = frequency
        self.temperature_k = temperature_k
        if liquid_water_path is None and (liquid_water_density is None
                                          or path_length_km is None):
            raise ValueError(
                "give liquid_water_path, or liquid_water_density and path_length_km")
        self.liquid_water_path = liquid_water_path
        self.elevation_deg = elevation_deg
        self.liquid_water_density = liquid_water_density
        self.path_length_km = path_length_km

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        k_l = cloud_specific_attenuation_coefficient(self.frequency, self.temperature_k)
        if self.liquid_water_path is not None:
            loss_db = k_l * self.liquid_water_path / math.sin(math.radians(self.elevation_deg))
        else:
            # guaranteed non-None by __init__
            assert self.liquid_water_density is not None and self.path_length_km is not None
            loss_db = k_l * self.liquid_water_density * self.path_length_km
        loss_linear = convert.db_to_linear(loss_db)
        return {"name": self.name,
                "description": self.description,
                "signal_power_in": signal_power,
                "noise_power_in": noise_power,
                "signal_power_out": signal_power / loss_linear,
                "noise_power_out": noise_power / loss_linear,
                "frequency": self.frequency,
                "specific_attenuation_coefficient_db_km_per_g_m3": k_l,
                "cloud_loss_db": loss_db}


# --------------------------------------------------------------------------
# tropospheric scintillation -- ITU-R P.618 section 2.4.1
# --------------------------------------------------------------------------

def _wet_refractivity(temperature_c: float, relative_humidity_percent: float) -> float:
    saturation = 6.1121 * math.exp(17.502 * temperature_c / (temperature_c + 240.97))
    vapor_pressure = relative_humidity_percent / 100.0 * saturation
    temp_k = temperature_c + 273.15
    return 3.732e5 * vapor_pressure / temp_k ** 2


def _scintillation_time_factor(percent: float) -> float:
    log_p = math.log10(percent)
    return -0.061 * log_p ** 3 + 0.072 * log_p ** 2 - 1.71 * log_p + 3.0


def scintillation_std_db(frequency_hz: float, elevation_deg: float,
                         antenna_diameter_m: float, antenna_efficiency: float = 0.5,
                         n_wet: float | None = None, temperature_c: float = 15.0,
                         relative_humidity_percent: float = 50.0) -> float:
    """Standard deviation (dB) of the tropospheric scintillation fade
    (ITU-R P.618 section 2.4.1)."""
    freq_ghz = frequency_hz / 1e9
    if n_wet is None:
        n_wet = _wet_refractivity(temperature_c, relative_humidity_percent)
    sigma_ref = 3.6e-3 + 1e-4 * n_wet

    theta = math.radians(elevation_deg)
    height_l = 1000.0
    path_l = 2.0 * height_l / (math.sqrt(math.sin(theta) ** 2 + 2.35e-4) + math.sin(theta))

    eff_diameter = math.sqrt(antenna_efficiency) * antenna_diameter_m
    x_arg = 1.22 * eff_diameter ** 2 * (freq_ghz / path_l)
    averaging = 3.86 * (x_arg ** 2 + 1.0) ** (11.0 / 12.0) \
        * math.sin(11.0 / 6.0 * math.atan2(1.0, x_arg)) - 7.08 * x_arg ** (5.0 / 6.0)
    averaging_factor = math.sqrt(averaging) if averaging > 0.0 else 0.0

    return sigma_ref * freq_ghz ** (7.0 / 12.0) * averaging_factor / math.sin(theta) ** 1.2


class TroposphericScintillation(Component):
    """Tropospheric scintillation fade (ITU-R P.618 section 2.4.1).

    Reports the fade depth exceeded ``time_percent`` percent of an average
    year.  The wet refractivity ``n_wet`` is derived from
    ``temperature_c`` / ``relative_humidity_percent`` if not given directly.
    """

    is_propagation = True

    def __init__(self, name: str = "Tropospheric scintillation", description: str = "",
                 frequency: float = 1e9, elevation_deg: float = 30.0,
                 antenna_diameter: float = 1.0, antenna_efficiency: float = 0.5,
                 n_wet: float | None = None, temperature_c: float = 15.0,
                 relative_humidity_percent: float = 50.0,
                 time_percent: float = 0.01) -> None:
        self.name = name
        self.description = description
        self.frequency = frequency
        self.elevation_deg = elevation_deg
        self.antenna_diameter = antenna_diameter
        self.antenna_efficiency = antenna_efficiency
        self.n_wet = n_wet
        self.temperature_c = temperature_c
        self.relative_humidity_percent = relative_humidity_percent
        self.time_percent = time_percent

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        sigma = scintillation_std_db(
            self.frequency, self.elevation_deg, self.antenna_diameter,
            self.antenna_efficiency, self.n_wet,
            self.temperature_c, self.relative_humidity_percent)
        fade_db = _scintillation_time_factor(self.time_percent) * sigma
        loss_linear = convert.db_to_linear(fade_db)
        return {"name": self.name,
                "description": self.description,
                "signal_power_in": signal_power,
                "noise_power_in": noise_power,
                "signal_power_out": signal_power / loss_linear,
                "noise_power_out": noise_power,
                "frequency": self.frequency,
                "elevation_deg": self.elevation_deg,
                "scintillation_std_db": sigma,
                "time_percent": self.time_percent,
                "scintillation_fade_db": fade_db}


# --------------------------------------------------------------------------
# two-ray ground reflection (terrestrial)
# --------------------------------------------------------------------------

class TwoRayGroundReflection(Component):
    """Plane-earth two-ray propagation model for a terrestrial path.

    Beyond the free-space / plane-earth crossover distance the received power
    falls as ``(h_tx h_rx / d**2)**2`` (a 40 dB/decade slope).  Below the
    crossover it falls back to free-space loss (``frequency`` required for
    that and for reporting the crossover distance).
    """

    is_propagation = True

    def __init__(self, name: str = "Two-ray ground reflection", description: str = "",
                 distance: float = 1000.0, tx_height: float = 10.0,
                 rx_height: float = 2.0, frequency: float | None = None) -> None:
        self.name = name
        self.description = description
        self.distance = distance
        self.tx_height = tx_height
        self.rx_height = rx_height
        self.frequency = frequency

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        plane_earth_loss = (self.distance ** 2 / (self.tx_height * self.rx_height)) ** 2

        crossover = None
        loss = plane_earth_loss
        if self.frequency is not None:
            wavelength = convert.SPEED_OF_LIGHT / self.frequency
            crossover = 4.0 * math.pi * self.tx_height * self.rx_height / wavelength
            free_space_loss = (4.0 * math.pi * self.distance / wavelength) ** 2
            if self.distance < crossover:
                loss = free_space_loss

        loss_linear = loss
        return {"name": self.name,
                "description": self.description,
                "signal_power_in": signal_power,
                "noise_power_in": noise_power,
                "signal_power_out": signal_power / loss_linear,
                "noise_power_out": noise_power / loss_linear,
                "distance": self.distance,
                "tx_height": self.tx_height,
                "rx_height": self.rx_height,
                "crossover_distance": crossover,
                "path_loss_db": convert.linear_to_db(loss_linear)}
