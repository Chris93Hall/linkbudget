"""Tests for linkbudget.antennas."""

import math

import pytest

from linkbudget import antennas, convert
from linkbudget.antennas import (
    BeamPointingLoss,
    ParabolicDish,
    PolarizationMismatchLoss,
    dish_gain_dbi,
    dish_half_power_beamwidth_deg,
    gaussian_beam_pointing_loss_db,
    polarization_efficiency,
)


class TestDishGain:
    def test_matches_the_aperture_formula(self):
        gain = dish_gain_dbi(1.2, 12e9, efficiency=0.6)
        wavelength = convert.SPEED_OF_LIGHT / 12e9
        expected = convert.linear_to_db(0.6 * (math.pi * 1.2 / wavelength) ** 2)
        assert gain == pytest.approx(expected)

    def test_doubling_diameter_adds_six_db(self):
        assert dish_gain_dbi(2.0, 10e9) - dish_gain_dbi(1.0, 10e9) == pytest.approx(
            6.0206, abs=1e-3)

    def test_known_ballpark_gain(self):
        # a 1 m dish at 10 GHz, 55% efficient, is ~38 dBi
        assert dish_gain_dbi(1.0, 10e9) == pytest.approx(37.8, abs=0.5)


class TestDishBeamwidth:
    def test_inversely_proportional_to_diameter(self):
        assert dish_half_power_beamwidth_deg(2.0, 10e9) == pytest.approx(
            0.5 * dish_half_power_beamwidth_deg(1.0, 10e9))

    def test_uses_the_seventy_lambda_over_d_rule(self):
        wavelength = convert.SPEED_OF_LIGHT / 10e9
        assert dish_half_power_beamwidth_deg(1.5, 10e9) == pytest.approx(
            70.0 * wavelength / 1.5)


class TestPointingLoss:
    def test_zero_offset_is_no_loss(self):
        assert gaussian_beam_pointing_loss_db(0.0, 2.0) == 0.0

    def test_three_db_at_half_the_beamwidth(self):
        assert gaussian_beam_pointing_loss_db(1.0, 2.0) == pytest.approx(3.0)

    def test_twelve_db_at_the_full_beamwidth(self):
        assert gaussian_beam_pointing_loss_db(2.0, 2.0) == pytest.approx(12.0)


class TestPolarizationEfficiency:
    def test_matched_circular_is_lossless(self):
        assert polarization_efficiency(0.0, 0.0) == pytest.approx(1.0)

    def test_circular_to_linear_is_three_db(self):
        assert polarization_efficiency(0.0, 60.0) == pytest.approx(0.5, abs=5e-3)
        assert -convert.linear_to_db(polarization_efficiency(0.0, 60.0)) == pytest.approx(
            3.0, abs=0.05)

    def test_aligned_linears_are_lossless(self):
        assert polarization_efficiency(40.0, 40.0, tilt_angle_deg=0.0) == pytest.approx(
            1.0, abs=1e-3)

    def test_crossed_linears_are_a_null(self):
        assert polarization_efficiency(40.0, 40.0, tilt_angle_deg=90.0) == pytest.approx(
            0.0, abs=1e-3)


class TestParabolicDishComponent:
    def test_applies_its_gain_to_signal_and_noise(self):
        dish = ParabolicDish("rx", "", diameter=1.0, frequency=10e9, efficiency=0.6)
        out = dish.propagate_signal(1.0, 0.5)
        gain_linear = convert.db_to_linear(dish_gain_dbi(1.0, 10e9, 0.6))
        assert out["signal_power_out"] == pytest.approx(gain_linear)
        assert out["noise_power_out"] == pytest.approx(0.5 * gain_linear)
        assert out["gain_dbi"] == pytest.approx(dish_gain_dbi(1.0, 10e9, 0.6))
        assert out["half_power_beamwidth_deg"] > 0.0

    def test_role_is_stored_for_the_summary(self):
        assert ParabolicDish("rx", "", role="rx").role == "rx"

    def test_is_not_flagged_as_propagation(self):
        assert ParabolicDish("d", "").is_propagation is False


class TestBeamPointingLossComponent:
    def test_derives_beamwidth_from_diameter_and_frequency(self):
        comp = BeamPointingLoss("pl", "", pointing_error_deg=0.5, diameter=1.0, frequency=10e9)
        assert comp.half_power_beamwidth_deg == pytest.approx(
            dish_half_power_beamwidth_deg(1.0, 10e9))

    def test_requires_beamwidth_or_dish_geometry(self):
        with pytest.raises(ValueError):
            BeamPointingLoss("pl", "", pointing_error_deg=0.5)

    def test_attenuates_signal_only(self):
        comp = BeamPointingLoss("pl", "", pointing_error_deg=1.0, half_power_beamwidth_deg=2.0)
        out = comp.propagate_signal(4.0, 2.0)
        assert out["pointing_loss_db"] == pytest.approx(3.0)
        assert out["signal_power_out"] == pytest.approx(4.0 / convert.db_to_linear(3.0))
        assert out["noise_power_out"] == 2.0


class TestPolarizationMismatchLossComponent:
    def test_matched_circular_passes_through(self):
        comp = PolarizationMismatchLoss("pm", "", axial_ratio_db_tx=0.0, axial_ratio_db_rx=0.0)
        out = comp.propagate_signal(3.0, 1.0)
        assert out["signal_power_out"] == pytest.approx(3.0)
        assert out["polarization_loss_db"] == pytest.approx(0.0)

    def test_circular_to_linear_costs_about_three_db(self):
        comp = PolarizationMismatchLoss(
            "pm", "", axial_ratio_db_tx=0.0, axial_ratio_db_rx=60.0)
        out = comp.propagate_signal(1.0, 0.0)
        assert out["polarization_loss_db"] == pytest.approx(3.0, abs=0.05)
        assert out["noise_power_out"] == 0.0


def test_module_default_efficiency_is_reasonable():
    assert 0.4 < antennas.DEFAULT_APERTURE_EFFICIENCY < 0.8
