"""Tests for the individual signal-chain components in linkbudget.link_container.

Every component exposes ``propagate_signal(signal_power, noise_power)`` and
returns a dict that always carries the four bookkeeping keys checked by
``assert_io_keys``.
"""

import numpy as np
import pytest

from linkbudget import convert
from linkbudget import link_container as lc

C = 2.99792458e8  # speed of light, m/s (matches the value hard-coded in the package)


def assert_io_keys(result, signal_in, noise_in):
    """Every component echoes its inputs back under the *_in keys."""
    assert result["signal_power_in"] == signal_in
    assert result["noise_power_in"] == noise_in
    assert "signal_power_out" in result
    assert "noise_power_out" in result
    assert "name" in result
    assert "description" in result


class _MiniComponent(lc.Component):
    """Minimal concrete Component that defers to the abstract base."""

    def __init__(self):
        super().__init__("mini", "a description")

    def propagate_signal(self, signal_power, noise_power):
        return super().propagate_signal(signal_power, noise_power)


class TestComponentAbstractBase:
    def test_cannot_instantiate_abstract_component(self):
        with pytest.raises(TypeError):
            lc.Component("x", "y")  # pylint: disable=abstract-class-instantiated

    def test_concrete_subclass_uses_the_base_initialiser(self):
        comp = _MiniComponent()
        assert comp.name == "mini"
        assert comp.description == "a description"

    def test_base_propagate_signal_is_a_stub(self):
        assert _MiniComponent().propagate_signal(1.0, 2.0) is None


class TestSignalSource:
    def test_adds_its_own_signal_and_noise(self):
        src = lc.SignalSource("src", "", signal_power=2.0, noise_power=0.5)
        out = src.propagate_signal(1.0, 0.25)
        assert out["signal_power_out"] == pytest.approx(3.0)
        assert out["noise_power_out"] == pytest.approx(0.75)
        assert_io_keys(out, 1.0, 0.25)

    def test_defaults_start_from_zero_input(self):
        src = lc.SignalSource("src", "", signal_power=5.0)
        out = src.propagate_signal()
        assert out["signal_power_in"] == 0.0
        assert out["noise_power_in"] == 0.0
        assert out["signal_power_out"] == pytest.approx(5.0)
        assert out["noise_power_out"] == pytest.approx(0.0)

    def test_default_signal_power_is_one(self):
        assert lc.SignalSource("s", "").signal_power == 1.0


class TestFreeSpacePathLoss:
    def test_matches_the_friis_formula(self):
        fspl = lc.FreeSpacePathLoss("path", "", distance=1000.0, frequency=5e9)
        out = fspl.propagate_signal(1.0, 1.0)
        expected = (4.0 * np.pi * 1000.0 * 5e9 / C) ** 2
        assert out["signal_power_out"] == pytest.approx(1.0 / expected)
        assert out["noise_power_out"] == pytest.approx(1.0 / expected)

    def test_doubling_distance_quadruples_the_loss(self):
        near = lc.FreeSpacePathLoss("n", "", distance=1000.0, frequency=1e9)
        far = lc.FreeSpacePathLoss("f", "", distance=2000.0, frequency=1e9)
        near_out = near.propagate_signal(1.0, 0.0)["signal_power_out"]
        far_out = far.propagate_signal(1.0, 0.0)["signal_power_out"]
        assert near_out / far_out == pytest.approx(4.0)

    def test_reports_the_speed_of_light_metadata(self):
        out = lc.FreeSpacePathLoss("p", "", distance=1.0, frequency=1.0).propagate_signal(0.0, 0.0)
        assert out["speed_of_light"] == pytest.approx(C)
        assert "formula" in out["free_space_path_loss_formula"].lower() or "Pi" in \
            out["free_space_path_loss_formula"]


class TestGain:
    def test_db_gain_is_applied_logarithmically(self):
        gain = lc.Gain("g", "", gain=3.0, db=True)
        out = gain.propagate_signal(2.0, 0.5)
        factor = 10.0 ** 0.3
        assert out["signal_power_out"] == pytest.approx(2.0 * factor)
        assert out["noise_power_out"] == pytest.approx(0.5 * factor)

    def test_linear_gain_is_applied_directly(self):
        gain = lc.Gain("g", "", gain=2.0, db=False)
        out = gain.propagate_signal(3.0, 1.0)
        assert out["signal_power_out"] == pytest.approx(6.0)
        assert out["noise_power_out"] == pytest.approx(2.0)

    def test_zero_db_gain_is_transparent(self):
        out = lc.Gain("g", "", gain=0.0, db=True).propagate_signal(7.0, 2.0)
        assert out["signal_power_out"] == pytest.approx(7.0)
        assert out["noise_power_out"] == pytest.approx(2.0)


class TestQuantizationNoise:
    def test_signal_passes_through_unchanged(self):
        qn = lc.QuantizationNoise(total_bits=12, headroom_db=0)
        out = qn.propagate_signal(3.0, 1.0)
        assert out["signal_power_out"] == 3.0

    def test_quantisation_noise_adds_to_the_noise_floor(self):
        qn = lc.QuantizationNoise(total_bits=12, headroom_db=0)
        out = qn.propagate_signal(3.0, 1.0)
        expected_qn = (3.0 + 1.0) / 4.0 ** 12 / 12.0
        assert out["quantization_noise"] == pytest.approx(expected_qn)
        assert out["noise_power_out"] == pytest.approx(1.0 + expected_qn)

    def test_headroom_reduces_the_effective_bit_count(self):
        qn = lc.QuantizationNoise(total_bits=12, headroom_db=6.0206)
        out = qn.propagate_signal(1.0, 0.0)
        assert out["effective_bits"] == pytest.approx(11.0, abs=1e-4)
        assert out["headroom_bits"] == pytest.approx(1.0, abs=1e-4)

    def test_more_bits_means_less_quantisation_noise(self):
        low = lc.QuantizationNoise(total_bits=8).propagate_signal(1.0, 0.0)
        high = lc.QuantizationNoise(total_bits=16).propagate_signal(1.0, 0.0)
        assert high["quantization_noise"] < low["quantization_noise"]


class TestThermalNoise:
    def test_adds_kt_b_to_the_noise_floor(self):
        tn = lc.ThermalNoise("t", "", temperature_k=290.0, bandwidth=1e6)
        out = tn.propagate_signal(1.0, 0.0)
        expected = convert.BOLTZMANN_CONSTANT * 290.0 * 1e6
        assert out["thermal_noise_power"] == pytest.approx(expected)
        assert out["noise_power_out"] == pytest.approx(expected)
        assert out["signal_power_out"] == 1.0

    def test_reports_noise_power_in_dbw(self):
        tn = lc.ThermalNoise("t", "", temperature_k=290.0, bandwidth=1.0)
        out = tn.propagate_signal(0.0, 0.0)
        assert out["thermal_noise_power_dbw"] == pytest.approx(
            convert.linear_to_db(out["thermal_noise_power"])
        )

    def test_default_temperature_is_290k(self):
        assert lc.ThermalNoise().temperature_k == 290.0


class TestImplementationLoss:
    def test_total_loss_is_the_sum_of_the_parts(self):
        il = lc.ImplementationLoss(
            "il", "", cable_loss_db=1.0, pointing_loss_db=0.5,
            polarization_loss_db=0.3, other_loss_db=0.2,
        )
        out = il.propagate_signal(4.0, 2.0)
        assert out["total_loss_db"] == pytest.approx(2.0)
        assert out["signal_power_out"] == pytest.approx(4.0 / convert.db_to_linear(2.0))

    def test_noise_is_untouched(self):
        il = lc.ImplementationLoss("il", "", cable_loss_db=3.0)
        out = il.propagate_signal(1.0, 2.0)
        assert out["noise_power_out"] == 2.0


class TestLossSubclasses:
    @pytest.mark.parametrize(
        "cls,attr",
        [
            (lc.CableLoss, "cable_loss_db"),
            (lc.PointingLoss, "pointing_loss_db"),
            (lc.PolarizationLoss, "polarization_loss_db"),
        ],
    )
    def test_subclass_routes_loss_to_the_right_slot(self, cls, attr):
        comp = cls("c", "", loss_db=1.5)
        out = comp.propagate_signal(10.0, 1.0)
        assert getattr(comp, attr) == 1.5
        assert out["total_loss_db"] == pytest.approx(1.5)
        assert out["signal_power_out"] == pytest.approx(10.0 / convert.db_to_linear(1.5))
        assert out["noise_power_out"] == 1.0

    def test_subclasses_are_implementation_losses(self):
        assert issubclass(lc.CableLoss, lc.ImplementationLoss)


class TestNoiseFigure:
    def test_scales_noise_by_the_noise_factor(self):
        nf = lc.NoiseFigure("nf", "", noise_figure=3.0)
        out = nf.propagate_signal(1.0, 2.0)
        factor = 10.0 ** 0.3
        assert out["noise_factor"] == pytest.approx(factor)
        assert out["noise_power_out"] == pytest.approx(2.0 * factor)
        assert out["signal_power_out"] == 1.0


class TestRFComponent:
    def test_applies_gain_to_signal_and_gain_times_noise_factor_to_noise(self):
        rf = lc.RFComponent("rf", "", gain=10.0, noise_figure=3.0)
        out = rf.propagate_signal(1.0, 2.0)
        gain_lin = 10.0
        noise_factor = 10.0 ** 0.3
        assert out["signal_power_out"] == pytest.approx(1.0 * gain_lin)
        assert out["noise_power_out"] == pytest.approx(2.0 * gain_lin * noise_factor)

    def test_is_a_component_subclass(self):
        assert issubclass(lc.RFComponent, lc.Component)


class TestRadarCrossSection:
    def test_applies_a_unitless_linear_multiplier(self):
        rcs = lc.RadarCrossSection("rcs", "", rcs_db=10.0)
        out = rcs.propagate_signal(2.0, 0.5)
        assert out["signal_power_out"] == pytest.approx(20.0)
        assert out["noise_power_out"] == pytest.approx(5.0)


class TestRadarPathLoss:
    def test_matches_the_radar_range_equation(self):
        rpl = lc.RadarPathLoss("r", "", distance=1000.0, frequency=1e9, rcs_db=0.0)
        out = rpl.propagate_signal(1.0, 1.0)
        wavelength = C / 1e9
        path_term = (wavelength ** 2 * 1.0) / ((4.0 * np.pi) ** 3 * 1000.0 ** 2 * 1000.0 ** 2)
        assert out["signal_power_out"] == pytest.approx(path_term)
        assert out["wavelength"] == pytest.approx(wavelength)
        assert out["path_loss_db"] == pytest.approx(convert.linear_to_db(1.0 / path_term))

    def test_monostatic_distance_sets_both_legs(self):
        rpl = lc.RadarPathLoss("r", "", distance=2500.0, frequency=3e9)
        assert rpl.tx_distance == 2500.0
        assert rpl.rx_distance == 2500.0

    def test_bistatic_distances_are_kept_separate(self):
        rpl = lc.RadarPathLoss("r", "", tx_distance=1000.0, rx_distance=3000.0, frequency=1e9)
        out = rpl.propagate_signal(1.0, 0.0)
        wavelength = C / 1e9
        path_term = (wavelength ** 2) / ((4.0 * np.pi) ** 3 * 1000.0 ** 2 * 3000.0 ** 2)
        assert out["signal_power_out"] == pytest.approx(path_term)

    def test_positive_rcs_increases_returned_power(self):
        no_rcs = lc.RadarPathLoss("a", "", distance=1000.0, frequency=1e9, rcs_db=0.0)
        with_rcs = lc.RadarPathLoss("b", "", distance=1000.0, frequency=1e9, rcs_db=10.0)
        ratio = (with_rcs.propagate_signal(1.0, 0.0)["signal_power_out"]
                 / no_rcs.propagate_signal(1.0, 0.0)["signal_power_out"])
        assert ratio == pytest.approx(10.0)

    def test_requires_a_distance(self):
        with pytest.raises(ValueError):
            lc.RadarPathLoss("r", "", frequency=1e9)
        with pytest.raises(ValueError):
            lc.RadarPathLoss("r", "", tx_distance=1000.0, frequency=1e9)  # rx missing


class TestRadarPathLossOneWay:
    def test_matches_the_calibrated_half_leg_formula(self):
        leg = lc.RadarPathLossOneWay("leg", "", distance=1000.0, frequency=1e9)
        out = leg.propagate_signal(1.0, 1.0)
        wavelength = C / 1e9
        path_term = wavelength / ((4.0 * np.pi) ** 1.5 * 1000.0 ** 2)
        assert out["signal_power_out"] == pytest.approx(path_term)
        assert out["noise_power_out"] == pytest.approx(path_term)


class TestArrayFactor:
    def test_scales_both_signal_and_noise_by_element_count(self):
        af = lc.ArrayFactor("af", "", num_elements=256)
        out = af.propagate_signal(1.0, 0.5)
        assert out["signal_power_out"] == pytest.approx(256.0)
        assert out["noise_power_out"] == pytest.approx(128.0)
        assert out["number_of_elements"] == 256

    def test_gain_metadata_is_a_db_string(self):
        out = lc.ArrayFactor("af", "", num_elements=100).propagate_signal(1.0, 0.0)
        assert out["gain"] == f"{10.0 * np.log10(100)} dB"


class TestMixer:
    def test_conversion_loss_attenuates_the_signal(self):
        mix = lc.Mixer("m", "", conversion_loss_db=6.0)
        out = mix.propagate_signal(1.0, 1.0)
        conv_gain = convert.db_to_linear(-6.0)
        noise_factor = convert.db_to_linear(6.0)
        assert out["signal_power_out"] == pytest.approx(conv_gain)
        assert out["noise_power_out"] == pytest.approx(conv_gain * noise_factor)

    def test_noise_figure_defaults_to_conversion_loss(self):
        assert lc.Mixer("m", "", conversion_loss_db=5.0).noise_figure_db == 5.0

    def test_explicit_noise_figure_overrides_the_default(self):
        assert lc.Mixer("m", "", conversion_loss_db=5.0, noise_figure_db=2.0).noise_figure_db == 2.0

    def test_downconvert_if_frequency(self):
        out = lc.Mixer(
            "m", "", lo_frequency=30.0, rf_frequency=100.0, mode="downconvert"
        ).propagate_signal(1.0, 0.0)
        assert out["if_frequency"] == pytest.approx(70.0)

    def test_upconvert_if_frequency(self):
        out = lc.Mixer(
            "m", "", lo_frequency=30.0, rf_frequency=100.0, mode="upconvert"
        ).propagate_signal(1.0, 0.0)
        assert out["if_frequency"] == pytest.approx(130.0)

    def test_if_frequency_is_none_without_an_rf_frequency(self):
        out = lc.Mixer("m", "", lo_frequency=30.0).propagate_signal(1.0, 0.0)
        assert out["if_frequency"] is None

    def test_image_rejection_adds_a_bounded_amount_of_image_noise(self):
        mix = lc.Mixer("m", "", conversion_loss_db=0.0, noise_figure_db=0.0, image_reject_db=20.0)
        out = mix.propagate_signal(1.0, 1.0)
        # conversion gain and noise factor are both unity here
        expected_image = 1.0 / convert.db_to_linear(20.0)
        assert out["image_noise_power"] == pytest.approx(expected_image)
        assert out["noise_power_out"] == pytest.approx(1.0 + expected_image)

    def test_no_image_noise_when_rejection_is_unset(self):
        out = lc.Mixer("m", "", conversion_loss_db=0.0).propagate_signal(1.0, 1.0)
        assert out["image_noise_power"] == 0.0


class TestIntegrate:
    def test_signal_gets_the_coherent_processing_gain(self):
        out = lc.Integrate("i", "", timespan=64.0).propagate_signal(2.0, 0.5)
        assert out["signal_power_out"] == pytest.approx(128.0)

    def test_noise_is_unaffected(self):
        out = lc.Integrate("i", "", timespan=64.0).propagate_signal(2.0, 0.5)
        assert out["noise_power_out"] == pytest.approx(0.5)
        assert out["integration_time"] == 64.0


class TestSubBandTune:
    def test_noise_scales_with_the_output_over_input_bandwidth_ratio(self):
        sbt = lc.SubBandTune(
            input_lower_freq=0.0, input_upper_freq=50e6,
            output_lower_freq=20e6, output_upper_freq=22e6,
            signal_lower_freq=20.2e6, signal_upper_freq=21.8e6,
        )
        out = sbt.propagate_signal(1.0, 1.0)
        assert out["noise_power_out"] == pytest.approx(2e6 / 50e6)

    def test_signal_fully_inside_the_output_band_is_preserved(self):
        sbt = lc.SubBandTune(
            input_lower_freq=0.0, input_upper_freq=50e6,
            output_lower_freq=20e6, output_upper_freq=22e6,
            signal_lower_freq=20.2e6, signal_upper_freq=21.8e6,
        )
        out = sbt.propagate_signal(3.0, 1.0)
        assert out["signal_power_out"] == pytest.approx(3.0)

    def test_signal_partly_outside_the_output_band_is_clipped(self):
        sbt = lc.SubBandTune(
            input_lower_freq=0.0, input_upper_freq=10e6,
            output_lower_freq=2e6, output_upper_freq=4e6,
            signal_lower_freq=3e6, signal_upper_freq=6e6,
        )
        out = sbt.propagate_signal(3.0, 0.0)
        # kept band is 3e6..4e6 out of a 3e6-wide signal -> 1/3 survives
        assert out["signal_power_out"] == pytest.approx(1.0)


class TestAnalogToDigitalConverter:
    def test_equivalent_to_rf_component_then_quantisation_noise(self):
        adc = lc.AnalogToDigitalConverter(
            "adc", "", gain_db=3.0, noise_figure_db=2.0, total_bits=14.0, headroom_db=12.0,
        )
        out = adc.propagate_signal(1e-9, 1e-12)

        stage1 = lc.RFComponent(gain=3.0, noise_figure=2.0).propagate_signal(1e-9, 1e-12)
        stage2 = lc.QuantizationNoise(total_bits=14.0, headroom_db=12.0).propagate_signal(
            stage1["signal_power_out"], stage1["noise_power_out"]
        )
        assert out["signal_power_out"] == pytest.approx(stage2["signal_power_out"])
        assert out["noise_power_out"] == pytest.approx(stage2["noise_power_out"])
        assert out["quantization_noise"] == pytest.approx(stage2["quantization_noise"])
        assert out["sample_rate"] is None


class TestDigitalToAnalogConverter:
    def test_equivalent_to_quantisation_noise_then_rf_component(self):
        dac = lc.DigitalToAnalogConverter(
            "dac", "", total_bits=12.0, headroom_db=6.0, gain_db=2.0, noise_figure_db=1.0,
        )
        out = dac.propagate_signal(1e-6, 1e-9)

        stage1 = lc.QuantizationNoise(total_bits=12.0, headroom_db=6.0).propagate_signal(
            1e-6, 1e-9
        )
        stage2 = lc.RFComponent(gain=2.0, noise_figure=1.0).propagate_signal(
            stage1["signal_power_out"], stage1["noise_power_out"]
        )
        assert out["signal_power_out"] == pytest.approx(stage2["signal_power_out"])
        assert out["noise_power_out"] == pytest.approx(stage2["noise_power_out"])


class TestRadarPathConsistency:
    """The one-way legs are calibrated to reproduce the two-way result."""

    def test_two_one_way_legs_around_rcs_equal_the_two_way_path(self):
        r1, r2, freq, rcs_db = 1000.0, 3000.0, 2e9, 7.0

        leg1 = lc.RadarPathLossOneWay("l1", "", distance=r1, frequency=freq)
        rcs = lc.RadarCrossSection("rcs", "", rcs_db=rcs_db)
        leg2 = lc.RadarPathLossOneWay("l2", "", distance=r2, frequency=freq)

        s = leg1.propagate_signal(1.0, 0.0)["signal_power_out"]
        s = rcs.propagate_signal(s, 0.0)["signal_power_out"]
        s = leg2.propagate_signal(s, 0.0)["signal_power_out"]

        two_way = lc.RadarPathLoss(
            "tw", "", tx_distance=r1, rx_distance=r2, frequency=freq, rcs_db=rcs_db
        )
        expected = two_way.propagate_signal(1.0, 0.0)["signal_power_out"]

        assert s == pytest.approx(expected)
