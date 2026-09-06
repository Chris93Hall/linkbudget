"""Tests for linkbudget.convert."""

import math

import numpy as np
import pytest

from linkbudget import convert


class TestLinearToDb:
    def test_unity_is_zero_db(self):
        assert convert.linear_to_db(1.0) == pytest.approx(0.0)

    def test_factor_of_ten_is_ten_db(self):
        assert convert.linear_to_db(10.0) == pytest.approx(10.0)

    def test_factor_of_hundred_is_twenty_db(self):
        assert convert.linear_to_db(100.0) == pytest.approx(20.0)

    def test_half_is_about_minus_three_db(self):
        assert convert.linear_to_db(0.5) == pytest.approx(-3.010299957, abs=1e-6)

    def test_zero_is_negative_infinity(self):
        assert convert.linear_to_db(0.0) == -np.inf


class TestDbToLinear:
    def test_zero_db_is_unity(self):
        assert convert.db_to_linear(0.0) == pytest.approx(1.0)

    def test_ten_db_is_factor_of_ten(self):
        assert convert.db_to_linear(10.0) == pytest.approx(10.0)

    def test_minus_ten_db_is_one_tenth(self):
        assert convert.db_to_linear(-10.0) == pytest.approx(0.1)

    def test_three_db_is_about_two(self):
        assert convert.db_to_linear(3.010299957) == pytest.approx(2.0, abs=1e-6)


@pytest.mark.parametrize("value", [1e-6, 0.5, 1.0, 3.7, 42.0, 1e9])
def test_db_round_trip(value):
    assert convert.db_to_linear(convert.linear_to_db(value)) == pytest.approx(value)


class TestScaleHertz:
    def test_sub_kilohertz_stays_hz(self):
        assert convert.scale_hertz(500.0) == (500.0, "Hz")

    def test_kilohertz(self):
        assert convert.scale_hertz(5e3) == (5.0, "kHz")

    def test_megahertz(self):
        assert convert.scale_hertz(5e6) == (5.0, "MHz")

    def test_gigahertz(self):
        assert convert.scale_hertz(5e9) == (5.0, "GHz")

    def test_exactly_one_khz_is_not_scaled(self):
        # the comparison is strict ( > 1e3 ), so the boundary falls through to Hz
        assert convert.scale_hertz(1e3) == (1e3, "Hz")

    def test_exactly_one_mhz_falls_through_to_hz(self):
        # 1e6 is neither < 1e6 nor > 1e6, so no band matches
        assert convert.scale_hertz(1e6) == (1e6, "Hz")


def test_boltzmann_constant_value():
    assert convert.BOLTZMANN_CONSTANT == pytest.approx(1.380649e-23)
    # sanity: kT at room temperature is around -204 dBW/Hz
    ktb_dbw = convert.linear_to_db(convert.BOLTZMANN_CONSTANT * 290.0)
    assert ktb_dbw == pytest.approx(-203.97, abs=0.1)
    assert not math.isnan(ktb_dbw)
