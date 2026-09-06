"""Tests for linkbudget.propagation."""

import pytest

from linkbudget import convert, propagation
from linkbudget import link_container as lc
from linkbudget.propagation import (
    AtmosphericAbsorption,
    CloudFogAttenuation,
    RainAttenuation,
    TroposphericScintillation,
    TwoRayGroundReflection,
    cloud_specific_attenuation_coefficient,
    oxygen_specific_attenuation_db_per_km,
    rain_kalpha,
    rain_specific_attenuation_db_per_km,
    water_vapor_specific_attenuation_db_per_km,
)


def _loss_db(result):
    return convert.linear_to_db(result["signal_power_in"] / result["signal_power_out"])


class TestGaseousSpecificAttenuation:
    def test_oxygen_attenuation_is_positive_and_small_at_low_band(self):
        gamma = oxygen_specific_attenuation_db_per_km(10.0)
        assert 0.0 < gamma < 0.02

    def test_oxygen_peaks_near_the_60_ghz_complex(self):
        assert (oxygen_specific_attenuation_db_per_km(57.0)
                > 20.0 * oxygen_specific_attenuation_db_per_km(30.0))

    def test_water_vapour_peaks_near_22_ghz(self):
        at_22 = water_vapor_specific_attenuation_db_per_km(22.2)
        at_15 = water_vapor_specific_attenuation_db_per_km(15.0)
        assert at_22 > at_15

    def test_water_vapour_scales_with_humidity(self):
        dry = water_vapor_specific_attenuation_db_per_km(20.0, water_vapor_density=2.0)
        humid = water_vapor_specific_attenuation_db_per_km(20.0, water_vapor_density=15.0)
        assert humid > dry


class TestAtmosphericAbsorptionComponent:
    def test_explicit_path_length(self):
        comp = AtmosphericAbsorption("atm", "", frequency=20e9, path_length_km=2.0)
        out = comp.propagate_signal(1.0, 1.0)
        gamma = (oxygen_specific_attenuation_db_per_km(20.0)
                 + water_vapor_specific_attenuation_db_per_km(20.0))
        assert _loss_db(out) == pytest.approx(gamma * 2.0)
        # gaseous loss attenuates the noise as well
        assert out["noise_power_out"] == pytest.approx(out["signal_power_out"])

    def test_slant_path_is_longer_at_low_elevation(self):
        high = AtmosphericAbsorption(
            "a", "", frequency=20e9, elevation_deg=90.0).propagate_signal(1.0, 0.0)
        low = AtmosphericAbsorption(
            "a", "", frequency=20e9, elevation_deg=10.0).propagate_signal(1.0, 0.0)
        assert _loss_db(low) > _loss_db(high)

    def test_requires_a_path_specification(self):
        with pytest.raises(ValueError):
            AtmosphericAbsorption("a", "", frequency=10e9)

    def test_is_tagged_as_propagation(self):
        assert AtmosphericAbsorption("a", "", path_length_km=1.0).is_propagation is True


class TestRainSpecificAttenuation:
    def test_p838_coefficients_are_in_range(self):
        k, alpha = rain_kalpha(20e9)
        assert 0.0 < k < 1.0
        assert 0.5 < alpha < 1.5

    def test_zero_rain_rate_gives_zero_attenuation(self):
        assert rain_specific_attenuation_db_per_km(12e9, 0.0) == 0.0

    def test_attenuation_grows_with_rain_rate(self):
        light = rain_specific_attenuation_db_per_km(12e9, 5.0)
        heavy = rain_specific_attenuation_db_per_km(12e9, 50.0)
        assert heavy > light > 0.0

    def test_attenuation_grows_with_frequency_through_ku_band(self):
        assert (rain_specific_attenuation_db_per_km(20e9, 20.0)
                > rain_specific_attenuation_db_per_km(6e9, 20.0))


class TestRainAttenuationComponent:
    def test_explicit_horizontal_path(self):
        comp = RainAttenuation("rain", "", frequency=12e9, rain_rate=20.0, path_length_km=5.0)
        out = comp.propagate_signal(1.0, 1.0)
        assert _loss_db(out) > 0.0
        assert out["specific_attenuation_db_per_km"] > 0.0
        assert 0.0 < out["effective_path_length_km"] <= 5.0

    def test_dry_conditions_are_transparent(self):
        comp = RainAttenuation("rain", "", frequency=12e9, rain_rate=0.0, path_length_km=5.0)
        out = comp.propagate_signal(2.0, 1.0)
        assert out["signal_power_out"] == pytest.approx(2.0)
        assert out["rain_loss_db"] == pytest.approx(0.0)

    def test_slant_path_uses_p618_geometry(self):
        comp = RainAttenuation(
            "rain", "", frequency=20e9, rain_rate=30.0, elevation_deg=25.0,
            rain_height_km=3.0, station_height_km=0.1, latitude_deg=40.0,
        )
        out = comp.propagate_signal(1.0, 1.0)
        assert out["rain_loss_db"] > 0.0
        assert out["noise_power_out"] == pytest.approx(out["signal_power_out"])

    def test_lower_elevation_means_more_rain_loss(self):
        steep = RainAttenuation(
            "r", "", frequency=20e9, rain_rate=30.0, elevation_deg=50.0, rain_height_km=3.0,
        ).propagate_signal(1.0, 0.0)
        shallow = RainAttenuation(
            "r", "", frequency=20e9, rain_rate=30.0, elevation_deg=15.0, rain_height_km=3.0,
        ).propagate_signal(1.0, 0.0)
        assert shallow["rain_loss_db"] > steep["rain_loss_db"]

    def test_tropical_latitude_adjusts_the_vertical_factor(self):
        out = RainAttenuation(
            "r", "", frequency=20e9, rain_rate=30.0, elevation_deg=30.0,
            rain_height_km=4.0, latitude_deg=20.0,
        ).propagate_signal(1.0, 0.0)
        assert out["rain_loss_db"] > 0.0

    def test_light_rain_low_band_slant_path(self):
        out = RainAttenuation(
            "r", "", frequency=3e9, rain_rate=2.0, elevation_deg=40.0, rain_height_km=2.0,
        ).propagate_signal(1.0, 0.0)
        assert out["rain_loss_db"] >= 0.0
        assert out["effective_path_length_km"] > 0.0

    def test_requires_a_path_specification(self):
        with pytest.raises(ValueError):
            RainAttenuation("r", "", frequency=12e9, rain_rate=10.0)


class TestCloudFogAttenuation:
    def test_specific_attenuation_coefficient_is_positive(self):
        assert cloud_specific_attenuation_coefficient(30e9) > 0.0

    def test_coefficient_grows_with_frequency(self):
        assert (cloud_specific_attenuation_coefficient(50e9)
                > cloud_specific_attenuation_coefficient(20e9))

    def test_columnar_liquid_water_path(self):
        comp = CloudFogAttenuation(
            "cloud", "", frequency=30e9, liquid_water_path=0.5, elevation_deg=30.0)
        out = comp.propagate_signal(1.0, 1.0)
        assert out["cloud_loss_db"] > 0.0
        assert out["noise_power_out"] == pytest.approx(out["signal_power_out"])

    def test_density_and_path_length_mode(self):
        comp = CloudFogAttenuation(
            "fog", "", frequency=30e9, liquid_water_density=0.5, path_length_km=1.0)
        out = comp.propagate_signal(1.0, 0.0)
        expected = cloud_specific_attenuation_coefficient(30e9) * 0.5 * 1.0
        assert out["cloud_loss_db"] == pytest.approx(expected)

    def test_requires_a_water_specification(self):
        with pytest.raises(ValueError):
            CloudFogAttenuation("c", "", frequency=30e9)


class TestTroposphericScintillation:
    def test_produces_a_positive_fade(self):
        comp = TroposphericScintillation(
            "scint", "", frequency=20e9, elevation_deg=20.0, antenna_diameter=1.2)
        out = comp.propagate_signal(1.0, 1.0)
        assert out["scintillation_fade_db"] > 0.0
        assert out["scintillation_std_db"] > 0.0
        # scintillation does not affect the noise power
        assert out["noise_power_out"] == 1.0

    def test_worse_at_low_elevation(self):
        high = TroposphericScintillation(
            "s", "", frequency=20e9, elevation_deg=45.0, antenna_diameter=1.0,
        ).propagate_signal(1.0, 0.0)
        low = TroposphericScintillation(
            "s", "", frequency=20e9, elevation_deg=10.0, antenna_diameter=1.0,
        ).propagate_signal(1.0, 0.0)
        assert low["scintillation_fade_db"] > high["scintillation_fade_db"]

    def test_explicit_n_wet_is_used(self):
        comp = TroposphericScintillation(
            "s", "", frequency=20e9, elevation_deg=30.0, antenna_diameter=1.0, n_wet=100.0)
        out = comp.propagate_signal(1.0, 0.0)
        assert out["scintillation_std_db"] > 0.0


class TestTwoRayGroundReflection:
    def test_plane_earth_slope_beyond_crossover(self):
        near = TwoRayGroundReflection(
            "tr", "", distance=1000.0, tx_height=20.0, rx_height=2.0,
        ).propagate_signal(1.0, 0.0)
        far = TwoRayGroundReflection(
            "tr", "", distance=2000.0, tx_height=20.0, rx_height=2.0,
        ).propagate_signal(1.0, 0.0)
        # 40 dB per decade -> factor of 16 in power for a doubling of range
        assert near["signal_power_out"] / far["signal_power_out"] == pytest.approx(16.0)

    def test_falls_back_to_free_space_below_crossover(self):
        comp = TwoRayGroundReflection(
            "tr", "", distance=50.0, tx_height=30.0, rx_height=10.0, frequency=900e6)
        out = comp.propagate_signal(1.0, 0.0)
        wavelength = convert.SPEED_OF_LIGHT / 900e6
        fspl = (4.0 * 3.141592653589793 * 50.0 / wavelength) ** 2
        assert out["signal_power_in"] / out["signal_power_out"] == pytest.approx(fspl)
        assert out["crossover_distance"] > 50.0

    def test_uses_plane_earth_beyond_crossover_even_with_a_frequency(self):
        comp = TwoRayGroundReflection(
            "tr", "", distance=20000.0, tx_height=30.0, rx_height=10.0, frequency=900e6)
        out = comp.propagate_signal(1.0, 0.0)
        plane_earth = (20000.0 ** 2 / (30.0 * 10.0)) ** 2
        assert out["signal_power_in"] / out["signal_power_out"] == pytest.approx(plane_earth)
        assert out["distance"] > out["crossover_distance"]

    def test_attenuates_noise_too(self):
        out = TwoRayGroundReflection(
            "tr", "", distance=5000.0, tx_height=25.0, rx_height=2.0,
        ).propagate_signal(1.0, 1.0)
        assert out["noise_power_out"] == pytest.approx(out["signal_power_out"])


def test_propagation_components_slot_into_a_container():
    budget = lc.LinkContainer()
    budget.add_component(lc.SignalSource("tx", "", signal_power=100.0))
    budget.add_component(lc.FreeSpacePathLoss("fspl", "", distance=40e3, frequency=20e9))
    budget.add_component(AtmosphericAbsorption("atm", "", frequency=20e9, elevation_deg=30.0))
    budget.add_component(RainAttenuation(
        "rain", "", frequency=20e9, rain_rate=25.0, elevation_deg=30.0, rain_height_km=3.0))
    budget.compute()
    assert len(budget.data_list) == 4
    assert budget.data_list[-1]["signal_power_out"] < budget.data_list[0]["signal_power_out"]


def test_module_exposes_helper_functions():
    assert callable(propagation.rain_kalpha)
