"""Tests for linkbudget.checks and LinkContainer's warning behaviour."""

import warnings

import pytest

from linkbudget import link_container as lc
from linkbudget.checks import LinkBudgetWarning, check_budget


def _issues(budget):
    """Compute the budget quietly and return its check messages."""
    budget.warn = False
    return budget.check()


class TestCheckBudgetDirect:
    def test_empty_budget_has_no_issues(self):
        assert check_budget([]) == []

    def test_clean_budget_has_no_issues(self, small_data_list):
        assert check_budget(small_data_list) == []

    def test_flags_negative_power_from_a_misbehaving_stage(self):
        stages = [
            {"name": "source", "signal_power_out": 1.0, "noise_power_out": 0.1},
            {"name": "buggy", "signal_power_out": -0.5, "noise_power_out": -0.2},
        ]
        issues = check_budget(stages)
        assert any("negative signal power out" in m for m in issues)
        assert any("negative noise power out" in m for m in issues)


class TestNoSignal:
    def test_flags_a_budget_with_no_signal_source(self):
        budget = lc.LinkContainer(warn=False)
        budget.add_component(lc.ThermalNoise("noise", "", bandwidth=1e6))
        issues = budget.check()
        assert any("final signal power" in message for message in issues)

    def test_flags_a_fully_attenuated_signal(self):
        budget = lc.LinkContainer(warn=False)
        budget.add_component(lc.SignalSource("tx", "", signal_power=1.0))
        budget.add_component(lc.SubBandTune(
            input_lower_freq=0.0, input_upper_freq=10e6,
            output_lower_freq=1e6, output_upper_freq=2e6,
            signal_lower_freq=5e6, signal_upper_freq=6e6))
        assert any("final signal power" in m for m in _issues(budget))


class TestRepeatedNoiseFloor:
    def test_flags_two_thermal_noise_stages(self):
        budget = lc.LinkContainer(warn=False)
        budget.add_component(lc.SignalSource("tx", "", signal_power=1.0))
        budget.add_component(lc.ThermalNoise("floor 1", "", bandwidth=1e6))
        budget.add_component(lc.ThermalNoise("floor 2", "", bandwidth=1e6))
        issues = budget.check()
        assert any("thermal noise floor added 2 times" in m for m in issues)

    def test_one_thermal_noise_stage_is_fine(self):
        budget = lc.LinkContainer(warn=False)
        budget.add_component(lc.SignalSource("tx", "", signal_power=1.0, noise_power=1e-9))
        budget.add_component(lc.ThermalNoise("floor", "", bandwidth=1e6))
        assert not any("thermal noise floor" in m for m in budget.check())


class TestNegativeLoss:
    def test_flags_a_negative_implementation_loss(self):
        budget = lc.LinkContainer(warn=False)
        budget.add_component(lc.SignalSource("tx", "", signal_power=1.0, noise_power=1e-3))
        budget.add_component(lc.CableLoss("gain-not-loss", "", loss_db=-3.0))
        issues = budget.check()
        assert any("negative loss is a gain" in m for m in issues)

    def test_flags_a_negative_mixer_conversion_loss(self):
        budget = lc.LinkContainer(warn=False)
        budget.add_component(lc.SignalSource("tx", "", signal_power=1.0, noise_power=1e-3))
        budget.add_component(lc.Mixer("active mixer", "", conversion_loss_db=-6.0,
                                      noise_figure_db=3.0))
        assert any("conversion loss db" in m for m in budget.check())


class TestCarrierFrequency:
    def test_flags_a_path_stage_off_the_carrier(self):
        budget = lc.LinkContainer(carrier_frequency=12e9, warn=False)
        budget.add_component(lc.SignalSource("tx", "", signal_power=1.0))
        budget.add_component(lc.FreeSpacePathLoss("path", "", distance=1e3, frequency=6e9))
        issues = budget.check()
        assert any("carrier_frequency" in m for m in issues)

    def test_matching_frequency_is_fine(self):
        budget = lc.LinkContainer(carrier_frequency=12e9, warn=False)
        budget.add_component(lc.SignalSource("tx", "", signal_power=1.0))
        budget.add_component(lc.FreeSpacePathLoss("path", "", distance=1e3, frequency=12e9))
        assert not any("carrier_frequency" in m for m in budget.check())

    def test_post_mixer_frequency_change_is_not_flagged(self):
        budget = lc.LinkContainer(carrier_frequency=12e9, warn=False)
        budget.add_component(lc.SignalSource("tx", "", signal_power=1.0))
        budget.add_component(lc.FreeSpacePathLoss("path", "", distance=1e3, frequency=12e9))
        budget.add_component(lc.Mixer("dc", "", lo_frequency=11e9, rf_frequency=12e9,
                                      conversion_loss_db=6.0))
        budget.add_component(lc.FreeSpacePathLoss("if path", "", distance=1.0, frequency=1e9))
        assert not any("carrier_frequency" in m for m in budget.check())


class TestWarningEmission:
    def test_compute_emits_link_budget_warning_by_default(self):
        budget = lc.LinkContainer()
        budget.add_component(lc.ThermalNoise("noise", "", bandwidth=1e6))
        with pytest.warns(LinkBudgetWarning, match="final signal power"):
            budget.compute()

    def test_warn_false_suppresses_the_warning(self):
        budget = lc.LinkContainer(warn=False)
        budget.add_component(lc.ThermalNoise("noise", "", bandwidth=1e6))
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            budget.compute()  # must not raise

    def test_publish_also_emits_the_warning(self, capsys):
        budget = lc.LinkContainer()
        budget.add_component(lc.SignalSource("tx", "", signal_power=1.0, noise_power=1e-3))
        budget.add_component(lc.CableLoss("boost", "", loss_db=-3.0))
        with pytest.warns(LinkBudgetWarning):
            budget.publish()
        capsys.readouterr()

    def test_check_returns_the_same_messages_it_would_warn(self):
        budget = lc.LinkContainer(warn=False)
        budget.add_component(lc.SignalSource("tx", "", signal_power=1.0, noise_power=1e-3))
        budget.add_component(lc.CableLoss("boost", "", loss_db=-3.0))
        messages = budget.check()
        assert messages
        assert check_budget(budget.data_list, budget.carrier_frequency) == messages
