"""Tests for linkbudget.margin.LinkMargin."""

import pytest

from linkbudget import convert
from linkbudget import link_container as lc
from linkbudget.margin import LinkMargin


class TestConstruction:
    def test_requires_exactly_one_requirement(self):
        with pytest.raises(ValueError):
            LinkMargin("m", "")
        with pytest.raises(ValueError):
            LinkMargin("m", "", required_snr_db=10.0, required_ebno_db=6.0)

    def test_is_tagged_as_a_margin_stage(self):
        comp = LinkMargin("m", "", required_snr_db=10.0)
        assert comp.is_margin is True
        assert comp.is_propagation is False


class TestSnrRequirement:
    def test_passes_signal_and_noise_through_unchanged(self):
        out = LinkMargin("m", "", required_snr_db=10.0).propagate_signal(4.0, 1.0)
        assert out["signal_power_out"] == 4.0
        assert out["noise_power_out"] == 1.0

    def test_margin_is_achieved_minus_required(self):
        out = LinkMargin("m", "", required_snr_db=3.0).propagate_signal(4.0, 1.0)
        assert out["achieved_snr_db"] == pytest.approx(convert.linear_to_db(4.0))
        assert out["margin_db"] == pytest.approx(convert.linear_to_db(4.0) - 3.0)
        assert out["closes"] is True

    def test_negative_margin_does_not_close(self):
        out = LinkMargin("m", "", required_snr_db=20.0).propagate_signal(4.0, 1.0)
        assert out["margin_db"] < 0.0
        assert out["closes"] is False

    def test_noiseless_input_gives_infinite_snr(self):
        out = LinkMargin("m", "", required_snr_db=10.0).propagate_signal(4.0, 0.0)
        assert out["achieved_snr_db"] == float("inf")
        assert out["margin_db"] == float("inf")
        assert out["closes"] is True

    def test_coding_gain_and_implementation_loss_shift_the_margin(self):
        base = LinkMargin("m", "", required_snr_db=3.0).propagate_signal(4.0, 1.0)
        adjusted = LinkMargin(
            "m", "", required_snr_db=3.0, coding_gain_db=5.0, implementation_loss_db=2.0,
        ).propagate_signal(4.0, 1.0)
        assert adjusted["margin_db"] == pytest.approx(base["margin_db"] + 3.0)


class TestEbNoRequirement:
    def test_converts_achieved_cn_to_ebno(self):
        # SNR = 10 dB in a 1 MHz noise bandwidth, data rate 500 kb/s
        out = LinkMargin(
            "m", "", required_ebno_db=4.0, noise_bandwidth=1e6, data_rate=5e5,
        ).propagate_signal(10.0, 1.0)
        expected_ebno = 10.0 + convert.linear_to_db(1e6) - convert.linear_to_db(5e5)
        assert out["achieved_ebno_db"] == pytest.approx(expected_ebno)
        assert out["margin_db"] == pytest.approx(expected_ebno - 4.0)
        assert out["metric"] == "Eb/N0"

    def test_margin_is_none_without_the_bandwidth_and_rate(self):
        out = LinkMargin("m", "", required_ebno_db=4.0).propagate_signal(10.0, 1.0)
        assert out["margin_db"] is None
        assert out["closes"] is False

    def test_esno_requirement_is_none_without_bandwidth(self):
        out = LinkMargin("m", "", required_esno_db=6.0).propagate_signal(10.0, 1.0)
        assert out["achieved_esno_db"] is None
        assert out["margin_db"] is None
        assert out["metric"] == "Es/N0"


class TestEsNoRequirement:
    def test_uses_the_symbol_rate(self):
        out = LinkMargin(
            "m", "", required_esno_db=6.0, noise_bandwidth=1e6, symbol_rate=1e6,
        ).propagate_signal(20.0, 1.0)
        expected = convert.linear_to_db(20.0)  # C/N0 - Rs, with B == Rs
        assert out["achieved_esno_db"] == pytest.approx(expected)
        assert out["metric"] == "Es/N0"


class TestCnRequirement:
    def test_falls_back_to_snr_without_a_bandwidth(self):
        out = LinkMargin("m", "", required_cn_db=8.0).propagate_signal(10.0, 1.0)
        assert out["metric"] == "C/N"
        assert out["margin_db"] == pytest.approx(convert.linear_to_db(10.0) - 8.0)


def test_link_margin_as_the_final_stage_of_a_budget():
    budget = lc.LinkContainer()
    budget.add_component(lc.SignalSource("src", "", signal_power=1.0, noise_power=1e-2))
    budget.add_component(LinkMargin("margin", "", required_snr_db=15.0))
    budget.compute()
    margin_stage = budget.data_list[-1]
    assert margin_stage["margin_db"] == pytest.approx(convert.linear_to_db(100.0) - 15.0)
