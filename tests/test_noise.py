"""Tests for the Friis per-stage noise cascade and the antenna noise model."""

import pytest

from linkbudget import antennas, convert, fom
from linkbudget import link_container as lc

K = convert.BOLTZMANN_CONSTANT
T0 = convert.REFERENCE_NOISE_TEMP_K


class TestFriisNoiseModel:
    """``noise_bandwidth`` switches the noisy stages to the Friis added-noise
    form ``N_out = (N_in + (F-1) k T0 B) G``."""

    def test_rf_component_without_bandwidth_keeps_the_multiplicative_model(self):
        rf = lc.RFComponent("rf", "", gain=10.0, noise_figure=3.0)
        out = rf.propagate_signal(1.0, 2.0)
        assert out["noise_model"] == "multiplicative"
        assert out["excess_noise_power"] == 0.0
        assert out["noise_power_out"] == pytest.approx(2.0 * 10.0 * convert.db_to_linear(3.0))

    def test_rf_component_with_bandwidth_uses_the_friis_form(self):
        b = 1e6
        rf = lc.RFComponent("rf", "", gain=10.0, noise_figure=3.0, noise_bandwidth=b)
        n_in = 5e-15
        out = rf.propagate_signal(1.0, n_in)
        noise_factor = convert.db_to_linear(3.0)
        excess = (noise_factor - 1.0) * K * T0 * b
        assert out["noise_model"] == "friis"
        assert out["excess_noise_power"] == pytest.approx(excess)
        assert out["excess_noise_temp_k"] == pytest.approx((noise_factor - 1.0) * T0)
        assert out["noise_power_out"] == pytest.approx((n_in + excess) * 10.0)
        assert out["signal_power_out"] == pytest.approx(10.0)

    def test_noise_figure_stage_adds_absolute_noise_in_the_friis_model(self):
        b = 2e6
        nf = lc.NoiseFigure("nf", "", noise_figure=6.0, noise_bandwidth=b)
        out = nf.propagate_signal(1.0, 0.0)
        excess = (convert.db_to_linear(6.0) - 1.0) * K * T0 * b
        assert out["noise_power_out"] == pytest.approx(excess)
        assert out["signal_power_out"] == 1.0

    def test_reference_temperature_is_configurable(self):
        rf = lc.RFComponent("rf", "", gain=0.0, noise_figure=3.0,
                            noise_bandwidth=1e6, reference_temp_k=120.0)
        out = rf.propagate_signal(1.0, 0.0)
        assert out["excess_noise_temp_k"] == pytest.approx(
            (convert.db_to_linear(3.0) - 1.0) * 120.0)

    def test_non_positive_noise_bandwidth_is_rejected(self):
        with pytest.raises(ValueError):
            lc.RFComponent("rf", "", noise_bandwidth=0.0)

    def _final_snr(self, noisy_first):
        b = 1e6
        budget = lc.LinkContainer(noise_bandwidth=b, warn=False)
        budget.add_component(lc.SignalSource("tx", "", signal_power=1e-9, noise_power=0.0))
        budget.add_component(lc.ThermalNoise("floor", "", temperature_k=T0, bandwidth=b))
        noisy = lc.RFComponent("mixer", "", gain=0.0, noise_figure=10.0, noise_bandwidth=b)
        gain = lc.RFComponent("lna", "", gain=30.0, noise_figure=0.0, noise_bandwidth=b)
        order = (noisy, gain) if noisy_first else (gain, noisy)
        for stage in order:
            budget.add_component(stage)
        budget.compute()
        return budget.data_list[-1]["snr"]

    def test_late_stage_noise_figure_matters_less(self):
        # a 10 dB NF stage after 30 dB of gain barely hurts; before the gain it
        # dominates -- the whole point of the Friis cascade
        assert self._final_snr(noisy_first=False) > 8.0 * self._final_snr(noisy_first=True)

    def test_multiplicative_model_ignores_stage_order(self):
        def snr(noisy_first):
            budget = lc.LinkContainer(warn=False)
            budget.add_component(lc.SignalSource("tx", "", signal_power=1e-9, noise_power=1e-18))
            noisy = lc.RFComponent("mixer", "", gain=0.0, noise_figure=10.0)
            gain = lc.RFComponent("lna", "", gain=30.0, noise_figure=0.0)
            for stage in ((noisy, gain) if noisy_first else (gain, noisy)):
                budget.add_component(stage)
            budget.compute()
            return budget.data_list[-1]["snr"]

        assert snr(True) == pytest.approx(snr(False))


class TestMixerFriisNoise:
    def test_mixer_friis_noise_and_image_noise(self):
        b = 1e6
        mix = lc.Mixer("m", "", conversion_loss_db=6.0, noise_figure_db=6.0,
                       image_reject_db=20.0, noise_bandwidth=b)
        out = mix.propagate_signal(1.0, 0.0)
        conv_gain = convert.db_to_linear(-6.0)
        noise_factor = convert.db_to_linear(6.0)
        excess = (noise_factor - 1.0) * K * T0 * b
        image = (K * T0 * b * conv_gain) / convert.db_to_linear(20.0)
        assert out["noise_power_out"] == pytest.approx(excess * conv_gain + image)
        assert out["image_noise_power"] == pytest.approx(image)


class TestAdcDacForwardNoiseBandwidth:
    def test_adc_forwards_noise_bandwidth_to_the_input_stage(self):
        b = 5e6
        adc = lc.AnalogToDigitalConverter("adc", "", gain_db=0.0, noise_figure_db=3.0,
                                          noise_bandwidth=b)
        out = adc.propagate_signal(1.0, 0.0)
        stage1 = lc.RFComponent(gain=0.0, noise_figure=3.0, noise_bandwidth=b).propagate_signal(1.0, 0.0)
        stage2 = lc.QuantizationNoise().propagate_signal(
            stage1["signal_power_out"], stage1["noise_power_out"])
        assert out["noise_power_out"] == pytest.approx(stage2["noise_power_out"])


class TestAntennaNoiseTempHelper:
    def test_clear_sky_only(self):
        assert antennas.antenna_noise_temp_k(10.0) == pytest.approx(10.0)

    def test_ground_pickup_raises_the_temperature(self):
        t = antennas.antenna_noise_temp_k(10.0, ground_temp_k=290.0, ground_coupling=0.1)
        assert t == pytest.approx(0.9 * 10.0 + 0.1 * 290.0)

    def test_ohmic_loss_pulls_toward_physical_temperature(self):
        t = antennas.antenna_noise_temp_k(10.0, radiation_efficiency=0.9, physical_temp_k=290.0)
        assert t == pytest.approx(0.9 * 10.0 + 0.1 * 290.0)

    @pytest.mark.parametrize("kwargs", [
        {"sky_temp_k": -1.0},
        {"sky_temp_k": 10.0, "ground_coupling": 1.5},
        {"sky_temp_k": 10.0, "radiation_efficiency": 0.0},
    ])
    def test_rejects_out_of_range_inputs(self, kwargs):
        with pytest.raises(ValueError):
            antennas.antenna_noise_temp_k(**kwargs)


class TestAntennaNoiseTemperatureComponent:
    def test_adds_k_t_b_and_reports_the_temperature(self):
        comp = antennas.AntennaNoiseTemperature(
            "ant", "", sky_temp_k=15.0, ground_temp_k=290.0, ground_coupling=0.05,
            bandwidth=1e6)
        out = comp.propagate_signal(1.0, 0.0)
        expected_temp = 0.95 * 15.0 + 0.05 * 290.0
        assert out["antenna_noise_temp_k"] == pytest.approx(expected_temp)
        assert out["antenna_noise_power"] == pytest.approx(K * expected_temp * 1e6)
        assert out["noise_power_out"] == pytest.approx(K * expected_temp * 1e6)
        assert out["signal_power_out"] == pytest.approx(1.0)

    def test_ohmic_loss_attenuates_the_signal(self):
        comp = antennas.AntennaNoiseTemperature(
            "ant", "", sky_temp_k=10.0, radiation_efficiency=0.8, bandwidth=1.0)
        out = comp.propagate_signal(2.0, 1e-3)
        assert out["signal_power_out"] == pytest.approx(1.6)
        assert out["noise_power_out"] == pytest.approx(
            1e-3 * 0.8 + K * out["antenna_noise_temp_k"] * 1.0)

    def test_feeds_the_system_noise_temperature(self):
        b = 1e6
        budget = lc.LinkContainer(noise_bandwidth=b, warn=False)
        budget.add_component(lc.SignalSource("tx", "", signal_power=1e-12, noise_power=0.0))
        budget.add_component(lc.Gain("rx dish", "", gain=30.0, role="rx"))
        budget.add_component(antennas.AntennaNoiseTemperature(
            "antenna", "", sky_temp_k=25.0, bandwidth=b))
        budget.add_component(lc.RFComponent("lna", "", gain=40.0, noise_figure=1.0,
                                            noise_bandwidth=b))
        summary = budget.summary()
        lna_excess = fom.noise_figure_to_temp_k(1.0)
        assert summary.system_noise_temp_k == pytest.approx(25.0 + lna_excess, rel=1e-6)

    def test_later_amplifier_noise_is_suppressed_in_t_sys(self):
        b = 1e6

        def t_sys(second_lna_nf_db):
            budget = lc.LinkContainer(noise_bandwidth=b, warn=False)
            budget.add_component(lc.SignalSource("tx", "", signal_power=1e-12))
            budget.add_component(antennas.AntennaNoiseTemperature(
                "antenna", "", sky_temp_k=20.0, bandwidth=b))
            budget.add_component(lc.RFComponent("lna1", "", gain=40.0, noise_figure=0.8,
                                                noise_bandwidth=b))
            budget.add_component(lc.RFComponent("lna2", "", gain=20.0,
                                                noise_figure=second_lna_nf_db,
                                                noise_bandwidth=b))
            return budget.summary().system_noise_temp_k

        # a 10 dB swing in the second-stage NF moves T_sys by well under a kelvin
        assert abs(t_sys(3.0) - t_sys(13.0)) < 1.0


class TestFomNoiseHelpers:
    def test_noise_figure_temp_round_trip(self):
        assert fom.noise_temp_to_figure_db(fom.noise_figure_to_temp_k(2.5)) == pytest.approx(2.5)

    def test_noise_figure_to_temp_matches_the_definition(self):
        assert fom.noise_figure_to_temp_k(3.0) == pytest.approx(
            (convert.db_to_linear(3.0) - 1.0) * 290.0)

    def test_friis_total_noise_temp_is_the_cascade_sum(self):
        total = fom.friis_total_noise_temp_k([100.0, 200.0, 400.0], [10.0, 13.0, 0.0])
        assert total == pytest.approx(100.0 + 200.0 / 10.0 + 400.0 / (10.0 * convert.db_to_linear(13.0)))

    def test_friis_total_noise_figure_is_dominated_by_the_first_stage(self):
        total = fom.friis_total_noise_figure_db([1.0, 10.0], [30.0, 0.0])
        assert total == pytest.approx(1.0, abs=0.05)

    def test_friis_helpers_require_matching_lengths(self):
        with pytest.raises(ValueError):
            fom.friis_total_noise_temp_k([100.0], [10.0, 0.0])
