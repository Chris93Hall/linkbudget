"""Constructor input validation across the component modules."""

import pytest

from linkbudget import _validate
from linkbudget import antennas
from linkbudget import link_container as lc
from linkbudget import propagation


class TestValidateHelpers:
    def test_positive_rejects_zero_and_negative(self):
        assert _validate.positive("x", 3.0) == 3.0
        with pytest.raises(ValueError):
            _validate.positive("x", 0.0)
        with pytest.raises(ValueError):
            _validate.positive("x", -1.0)

    def test_non_negative_allows_zero(self):
        assert _validate.non_negative("x", 0.0) == 0.0
        with pytest.raises(ValueError):
            _validate.non_negative("x", -0.1)

    def test_in_range_bounds(self):
        assert _validate.in_range("x", 0.5, 0.0, 1.0) == 0.5
        with pytest.raises(ValueError):
            _validate.in_range("x", 1.5, 0.0, 1.0)
        with pytest.raises(ValueError):
            _validate.in_range("x", 0.0, 0.0, 1.0, low_open=True)

    def test_one_of(self):
        assert _validate.one_of("x", "a", ("a", "b")) == "a"
        with pytest.raises(ValueError):
            _validate.one_of("x", "c", ("a", "b"))

    def test_optional_helpers_pass_none_through(self):
        assert _validate.optional_positive("x", None) is None
        assert _validate.optional_non_negative("x", None) is None
        assert _validate.optional_in_range("x", None, 0.0, 1.0) is None
        with pytest.raises(ValueError):
            _validate.optional_positive("x", -1.0)

    def test_error_message_names_the_field(self):
        with pytest.raises(ValueError, match="frequency"):
            _validate.positive("frequency", 0.0)


class TestLinkContainerValidation:
    @pytest.mark.parametrize("kwargs", [
        {"carrier_frequency": 0.0},
        {"noise_bandwidth": -1.0},
        {"data_rate": 0.0},
        {"symbol_rate": -5.0},
    ])
    def test_rejects_non_positive_context(self, kwargs):
        with pytest.raises(ValueError):
            lc.LinkContainer(**kwargs)

    def test_accepts_none_context(self):
        lc.LinkContainer()


class TestSignalChainValidation:
    def test_signal_source_rejects_negative_power(self):
        with pytest.raises(ValueError):
            lc.SignalSource("s", "", signal_power=-1.0)
        with pytest.raises(ValueError):
            lc.SignalSource("s", "", noise_power=-1.0)

    @pytest.mark.parametrize("kwargs", [
        {"distance": 0.0, "frequency": 1e9},
        {"distance": -10.0, "frequency": 1e9},
        {"distance": 1000.0, "frequency": 0.0},
    ])
    def test_free_space_path_loss(self, kwargs):
        with pytest.raises(ValueError):
            lc.FreeSpacePathLoss("p", "", **kwargs)

    def test_gain_rejects_bad_role(self):
        with pytest.raises(ValueError):
            lc.Gain("g", "", gain=3.0, role="receiver")

    def test_quantization_noise_rejects_non_positive_bits(self):
        with pytest.raises(ValueError):
            lc.QuantizationNoise(total_bits=0)

    def test_thermal_noise(self):
        with pytest.raises(ValueError):
            lc.ThermalNoise(temperature_k=0.0)
        with pytest.raises(ValueError):
            lc.ThermalNoise(bandwidth=-1.0)

    def test_array_factor(self):
        with pytest.raises(ValueError):
            lc.ArrayFactor(num_elements=0)
        with pytest.raises(ValueError):
            lc.ArrayFactor(num_elements=4, role="bad")

    def test_mixer_rejects_bad_mode(self):
        with pytest.raises(ValueError):
            lc.Mixer("m", "", mode="mix")

    def test_mixer_rejects_non_positive_rf_frequency(self):
        with pytest.raises(ValueError):
            lc.Mixer("m", "", rf_frequency=0.0)

    def test_integrate_rejects_non_positive_timespan(self):
        with pytest.raises(ValueError):
            lc.Integrate(timespan=0.0)

    def test_radar_path_loss_needs_a_distance(self):
        with pytest.raises(ValueError):
            lc.RadarPathLoss("r", "", frequency=1e9)

    def test_radar_path_loss_one_way(self):
        with pytest.raises(ValueError):
            lc.RadarPathLossOneWay("r", "", distance=0.0)

    def test_adc_dac_reject_bad_sample_rate_and_bits(self):
        with pytest.raises(ValueError):
            lc.AnalogToDigitalConverter(sample_rate=-1.0)
        with pytest.raises(ValueError):
            lc.DigitalToAnalogConverter(total_bits=0.0)


class TestSubBandTuneValidation:
    def test_rejects_empty_input_band(self):
        with pytest.raises(ValueError, match="input band"):
            lc.SubBandTune(input_lower_freq=10e6, input_upper_freq=10e6)

    def test_rejects_inverted_signal_band(self):
        with pytest.raises(ValueError, match="signal band"):
            lc.SubBandTune(signal_lower_freq=5e6, signal_upper_freq=2e6)

    def test_rejects_negative_frequency(self):
        with pytest.raises(ValueError):
            lc.SubBandTune(output_lower_freq=-1.0)

    def test_non_overlapping_bands_clamp_signal_to_zero(self):
        # signal band entirely outside the output band -> no signal survives,
        # not negative power
        tuner = lc.SubBandTune(
            input_lower_freq=0.0, input_upper_freq=10e6,
            output_lower_freq=1e6, output_upper_freq=2e6,
            signal_lower_freq=5e6, signal_upper_freq=6e6,
        )
        out = tuner.propagate_signal(3.0, 1.0)
        assert out["signal_power_out"] == 0.0


class TestAntennaValidation:
    def test_dish_gain_functions_reject_bad_geometry(self):
        with pytest.raises(ValueError):
            antennas.dish_gain_dbi(0.0, 10e9)
        with pytest.raises(ValueError):
            antennas.dish_gain_dbi(1.0, 10e9, efficiency=1.5)
        with pytest.raises(ValueError):
            antennas.dish_half_power_beamwidth_deg(1.0, 0.0)

    def test_parabolic_dish_component(self):
        with pytest.raises(ValueError):
            antennas.ParabolicDish("d", "", diameter=-1.0)
        with pytest.raises(ValueError):
            antennas.ParabolicDish("d", "", efficiency=0.0)
        with pytest.raises(ValueError):
            antennas.ParabolicDish("d", "", role="middle")

    def test_beam_pointing_loss(self):
        with pytest.raises(ValueError):
            antennas.BeamPointingLoss("p", "", pointing_error_deg=-1.0,
                                      half_power_beamwidth_deg=2.0)
        with pytest.raises(ValueError):
            antennas.BeamPointingLoss("p", "", half_power_beamwidth_deg=0.0)


class TestPropagationValidation:
    def test_atmospheric_absorption(self):
        with pytest.raises(ValueError):
            propagation.AtmosphericAbsorption("a", "", frequency=0.0, path_length_km=1.0)
        with pytest.raises(ValueError):
            propagation.AtmosphericAbsorption("a", "", elevation_deg=0.0)
        with pytest.raises(ValueError):
            propagation.AtmosphericAbsorption("a", "", elevation_deg=95.0)

    def test_rain_attenuation(self):
        with pytest.raises(ValueError):
            propagation.RainAttenuation("r", "", rain_rate=-1.0, path_length_km=5.0)
        with pytest.raises(ValueError):
            propagation.RainAttenuation("r", "", frequency=0.0, path_length_km=5.0)

    def test_cloud_fog_attenuation(self):
        with pytest.raises(ValueError):
            propagation.CloudFogAttenuation("c", "", temperature_k=0.0,
                                            liquid_water_path=0.5)

    def test_tropospheric_scintillation(self):
        with pytest.raises(ValueError):
            propagation.TroposphericScintillation("s", "", elevation_deg=0.0)
        with pytest.raises(ValueError):
            propagation.TroposphericScintillation("s", "", time_percent=0.0)
        with pytest.raises(ValueError):
            propagation.TroposphericScintillation("s", "", antenna_efficiency=2.0)

    def test_two_ray_ground_reflection(self):
        with pytest.raises(ValueError):
            propagation.TwoRayGroundReflection("t", "", distance=0.0)
        with pytest.raises(ValueError):
            propagation.TwoRayGroundReflection("t", "", tx_height=-1.0)

    def test_specific_attenuation_functions(self):
        with pytest.raises(ValueError):
            propagation.oxygen_specific_attenuation_db_per_km(0.0)
        with pytest.raises(ValueError):
            propagation.rain_specific_attenuation_db_per_km(12e9, -5.0)
        with pytest.raises(ValueError):
            propagation.cloud_specific_attenuation_coefficient(-1.0)
