"""Tests for linkbudget.fom."""

import math

import pytest

from linkbudget import convert, fom


class TestEirp:
    def test_sums_power_and_gain_minus_loss(self):
        assert fom.eirp_dbw(20.0, 30.0, tx_loss_db=1.0) == pytest.approx(49.0)

    def test_loss_defaults_to_zero(self):
        assert fom.eirp_dbw(10.0, 15.0) == pytest.approx(25.0)


class TestGOverT:
    def test_gain_minus_ten_log_t(self):
        assert fom.g_over_t_db(30.0, 100.0) == pytest.approx(30.0 - 20.0)

    def test_290k_reference(self):
        assert fom.g_over_t_db(0.0, 290.0) == pytest.approx(-convert.linear_to_db(290.0))


class TestFreeSpacePathLoss:
    def test_matches_component_form(self):
        loss = fom.free_space_path_loss_db(1000.0, 5e9)
        wavelength = convert.SPEED_OF_LIGHT / 5e9
        expected = convert.linear_to_db((4.0 * math.pi * 1000.0 / wavelength) ** 2)
        assert loss == pytest.approx(expected)

    def test_doubling_distance_adds_six_db(self):
        near = fom.free_space_path_loss_db(1000.0, 2e9)
        far = fom.free_space_path_loss_db(2000.0, 2e9)
        assert far - near == pytest.approx(6.0206, abs=1e-3)


class TestCarrierToNoise:
    def test_link_equation_round_trips_with_snr_form(self):
        eirp, g_t, path_loss = 50.0, 5.0, 160.0
        cn0 = fom.cn0_dbhz(eirp, g_t, path_loss)
        # C/N in a 1 MHz bandwidth, then back to C/N0
        cn = fom.cn_db(cn0, 1e6)
        assert fom.cn0_from_snr(cn, 1e6) == pytest.approx(cn0)

    def test_cn0_uses_boltzmann(self):
        cn0 = fom.cn0_dbhz(0.0, 0.0, 0.0)
        assert cn0 == pytest.approx(-convert.linear_to_db(convert.BOLTZMANN_CONSTANT))

    def test_ebno_is_cn0_minus_rate(self):
        assert fom.ebno_db(80.0, 1e6) == pytest.approx(80.0 - 60.0)

    def test_esno_is_cn0_minus_symbol_rate(self):
        assert fom.esno_db(80.0, 5e5) == pytest.approx(80.0 - convert.linear_to_db(5e5))

    def test_ebno_equals_esno_for_one_bit_per_symbol(self):
        cn0 = 75.0
        assert fom.ebno_db(cn0, 1e6) == pytest.approx(fom.esno_db(cn0, 1e6))


class TestCapacityAndEfficiency:
    def test_shannon_capacity_at_unity_snr(self):
        assert fom.shannon_capacity_bps(1e6, 1.0) == pytest.approx(1e6)

    def test_shannon_capacity_scales_with_bandwidth(self):
        assert fom.shannon_capacity_bps(2e6, 7.0) == pytest.approx(
            2.0 * fom.shannon_capacity_bps(1e6, 7.0))

    def test_spectral_efficiency(self):
        assert fom.spectral_efficiency(1.5e6, 1e6) == pytest.approx(1.5)
