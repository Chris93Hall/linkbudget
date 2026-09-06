"""Tests for linkbudget.summary and LinkContainer.summary()."""

import math

import pytest

from linkbudget import convert, fom
from linkbudget import link_container as lc
from linkbudget.antennas import ParabolicDish
from linkbudget.margin import LinkMargin
from linkbudget.propagation import AtmosphericAbsorption
from linkbudget.summary import BudgetSummary, summarize


@pytest.fixture
def satcom_budget():
    budget = lc.LinkContainer(
        carrier_frequency=12e9, noise_bandwidth=20e6, data_rate=10e6, symbol_rate=5e6,
    )
    budget.add_component(lc.SignalSource("HPA", "", signal_power=20.0, noise_power=0.0))
    budget.add_component(lc.Gain("Tx antenna", "", gain=40.0, role="tx"))
    budget.add_component(lc.FreeSpacePathLoss("Downlink", "", distance=38000e3, frequency=12e9))
    budget.add_component(AtmosphericAbsorption("Atmosphere", "", frequency=12e9, elevation_deg=30.0))
    budget.add_component(lc.Gain("Rx antenna", "", gain=35.0, role="rx"))
    budget.add_component(lc.ThermalNoise("Noise floor", "", temperature_k=150.0, bandwidth=20e6))
    budget.add_component(lc.RFComponent("LNA", "", gain=40.0, noise_figure=0.8))
    return budget


class TestEmptyAndMinimal:
    def test_empty_budget_summary(self):
        summary = lc.LinkContainer().summary()
        assert isinstance(summary, BudgetSummary)
        assert summary.stages == []
        assert summary.eirp_dbw is None

    def test_single_source_reports_power_and_snr(self):
        budget = lc.LinkContainer()
        budget.add_component(lc.SignalSource("s", "", signal_power=10.0, noise_power=1.0))
        summary = budget.summary()
        assert summary.signal_power_w == pytest.approx(10.0)
        assert summary.signal_power_dbw == pytest.approx(convert.linear_to_db(10.0))
        assert summary.snr == pytest.approx(10.0)
        assert summary.snr_db == pytest.approx(10.0)


class TestFiguresOfMerit:
    def test_eirp_is_power_into_the_first_propagation_stage(self, satcom_budget):
        summary = satcom_budget.summary()
        # 20 W * 10^4 (40 dBi) = 2e5 W -> 53.01 dBW
        assert summary.eirp_dbw == pytest.approx(convert.linear_to_db(20.0) + 40.0)

    def test_total_propagation_loss_sums_the_propagation_stages(self, satcom_budget):
        summary = satcom_budget.summary()
        fspl = fom.free_space_path_loss_db(38000e3, 12e9)
        assert summary.total_propagation_loss_db > fspl  # fspl + atmosphere
        assert summary.total_propagation_loss_db == pytest.approx(fspl + 0.0, abs=5.0)

    def test_cn0_ebno_esno_from_bandwidth_and_rates(self, satcom_budget):
        summary = satcom_budget.summary()
        assert summary.cn0_dbhz == pytest.approx(
            summary.snr_db + convert.linear_to_db(20e6))
        assert summary.ebno_db == pytest.approx(
            summary.cn0_dbhz - convert.linear_to_db(10e6))
        assert summary.esno_db == pytest.approx(
            summary.cn0_dbhz - convert.linear_to_db(5e6))

    def test_spectral_efficiency_and_shannon_capacity(self, satcom_budget):
        summary = satcom_budget.summary()
        assert summary.spectral_efficiency_bps_per_hz == pytest.approx(10e6 / 20e6)
        assert summary.shannon_capacity_bps == pytest.approx(
            20e6 * math.log2(1.0 + summary.snr))

    def test_system_noise_temp_and_g_over_t(self, satcom_budget):
        summary = satcom_budget.summary()
        assert summary.system_noise_temp_k is not None
        assert summary.system_noise_temp_k > 0.0
        assert summary.g_over_t_db == pytest.approx(
            fom.g_over_t_db(35.0, summary.system_noise_temp_k), abs=1e-6)

    def test_no_g_over_t_without_a_tagged_receive_antenna(self):
        budget = lc.LinkContainer(noise_bandwidth=1e6)
        budget.add_component(lc.SignalSource("s", "", signal_power=1.0))
        budget.add_component(lc.FreeSpacePathLoss("p", "", distance=1e3, frequency=1e9))
        budget.add_component(lc.Gain("rx", "", gain=10.0))  # no role
        budget.add_component(lc.ThermalNoise("n", "", bandwidth=1e6))
        summary = budget.summary()
        assert summary.system_noise_temp_k is not None
        assert summary.g_over_t_db is None

    def test_fom_fields_absent_without_a_noise_bandwidth(self):
        budget = lc.LinkContainer()
        budget.add_component(lc.SignalSource("s", "", signal_power=1.0, noise_power=1e-3))
        summary = budget.summary()
        assert summary.cn0_dbhz is None
        assert summary.ebno_db is None
        assert summary.system_noise_temp_k is None


class TestMarginInSummary:
    def test_margin_and_closes_surface_from_a_link_margin_stage(self, satcom_budget):
        satcom_budget.add_component(LinkMargin(
            "Margin", "", required_ebno_db=5.0, noise_bandwidth=20e6, data_rate=10e6,
            implementation_loss_db=1.5,
        ))
        summary = satcom_budget.summary()
        assert summary.margin_db is not None
        assert summary.closes in (True, False)
        assert summary.margin_db == pytest.approx(satcom_budget.data_list[-1]["margin_db"])

    def test_no_margin_without_the_stage(self, satcom_budget):
        assert satcom_budget.summary().margin_db is None
        assert satcom_budget.summary().closes is None


class TestSummaryRendering:
    def test_as_dict_round_trips_the_fields(self, satcom_budget):
        data = satcom_budget.summary().as_dict()
        assert data["eirp_dbw"] == pytest.approx(satcom_budget.summary().eirp_dbw)
        assert "stages" in data and len(data["stages"]) == 7

    def test_str_is_a_readable_report(self, satcom_budget):
        text = str(satcom_budget.summary())
        assert "Link budget summary" in text
        assert "EIRP" in text
        assert "G/T" in text

    def test_str_shows_closure_when_a_margin_is_present(self, satcom_budget):
        satcom_budget.add_component(LinkMargin("M", "", required_snr_db=3.0))
        text = str(satcom_budget.summary())
        assert "Link closes" in text


class TestSummaryEdgeCases:
    def test_propagation_stage_before_any_signal(self):
        # first stage is propagation, so the EIRP reference power is zero
        budget = lc.LinkContainer(noise_bandwidth=1e6)
        budget.add_component(lc.FreeSpacePathLoss("p", "", distance=1e3, frequency=1e9))
        budget.add_component(lc.SignalSource("s", "", signal_power=1.0, noise_power=1e-6))
        summary = budget.summary()
        assert summary.eirp_dbw is None
        assert summary.total_propagation_loss_db is not None

    def test_noise_bandwidth_but_no_noise_floor_stage(self):
        # no stage injects noise into a noiseless input, so there is no
        # reference plane for the system noise temperature
        budget = lc.LinkContainer(noise_bandwidth=1e6)
        budget.add_component(lc.SignalSource("s", "", signal_power=1.0, noise_power=0.0))
        budget.add_component(lc.Gain("g", "", gain=10.0, role="rx"))
        summary = budget.summary()
        assert summary.cn0_dbhz is not None
        assert summary.system_noise_temp_k is None
        assert summary.g_over_t_db is None

    def test_rx_antenna_with_no_signal_yields_no_g_over_t(self):
        # no signal source: the receive antenna sees zero signal power in,
        # so its gain cannot be recovered for G/T
        budget = lc.LinkContainer(noise_bandwidth=1e6)
        budget.add_component(lc.Gain("Rx antenna", "", gain=30.0, role="rx"))
        budget.add_component(lc.ThermalNoise("noise", "", bandwidth=1e6))
        summary = budget.summary()
        assert summary.system_noise_temp_k is not None
        assert summary.g_over_t_db is None

    def test_infinite_snr_leaves_shannon_capacity_unset(self):
        budget = lc.LinkContainer(noise_bandwidth=1e6, data_rate=1e5)
        budget.add_component(lc.SignalSource("s", "", signal_power=1.0, noise_power=0.0))
        summary = budget.summary()
        assert summary.snr == float("inf")
        assert summary.shannon_capacity_bps is None
        assert summary.spectral_efficiency_bps_per_hz == pytest.approx(0.1)


def test_summarize_is_usable_standalone():
    budget = lc.LinkContainer()
    budget.add_component(lc.SignalSource("s", "", signal_power=2.0, noise_power=0.5))
    budget.compute()
    summary = summarize(budget.data_list, budget.components_list, noise_bandwidth=1e3)
    assert summary.snr == pytest.approx(4.0)
    assert summary.cn0_dbhz == pytest.approx(
        convert.linear_to_db(4.0) + convert.linear_to_db(1e3))
