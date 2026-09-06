"""Tests for linkbudget.link_container.LinkContainer."""

import numpy as np
import pytest

from linkbudget import link_container as lc
from linkbudget.publishers import StdOutPublisher


class RecordingPublisher:
    """A stand-in publisher that just captures what it was handed."""

    def __init__(self):
        self.calls = []

    def publish(self, data_list, power_units="W"):
        self.calls.append((list(data_list), power_units))


class TestConstruction:
    def test_starts_empty_with_a_stdout_publisher(self):
        budget = lc.LinkContainer()
        assert budget.components_list == []
        assert budget.data_list == []
        assert isinstance(budget.publisher, StdOutPublisher)
        assert budget.power_units == "W"

    def test_power_units_are_configurable(self):
        assert lc.LinkContainer(power_units="mW").power_units == "mW"

    def test_install_publisher_replaces_the_default(self):
        budget = lc.LinkContainer()
        rec = RecordingPublisher()
        budget.install_publisher(rec)
        assert budget.publisher is rec


class TestCompute:
    def test_empty_budget_computes_an_empty_data_list(self):
        budget = lc.LinkContainer()
        budget.compute()
        assert budget.data_list == []

    def test_single_source_derives_snr_and_gains(self):
        budget = lc.LinkContainer()
        budget.add_component(lc.SignalSource("src", "", signal_power=4.0, noise_power=1.0))
        budget.compute()

        (stage,) = budget.data_list
        assert stage["signal_power_out"] == pytest.approx(4.0)
        assert stage["noise_power_out"] == pytest.approx(1.0)
        assert stage["snr"] == pytest.approx(4.0)
        # both inputs were zero -> gains are infinite
        assert stage["signal_gain"] == np.inf
        assert stage["noise_gain"] == np.inf

    def test_snr_is_infinite_with_no_noise(self):
        budget = lc.LinkContainer()
        budget.add_component(lc.SignalSource("src", "", signal_power=1.0, noise_power=0.0))
        budget.compute()
        assert budget.data_list[0]["snr"] == np.inf

    def test_two_stage_chain_tracks_running_power_and_gain(self):
        budget = lc.LinkContainer()
        budget.add_component(lc.SignalSource("src", "", signal_power=4.0, noise_power=1.0))
        budget.add_component(lc.Gain("amp", "", gain=3.0, db=False))
        budget.compute()

        source, amp = budget.data_list
        assert source["snr"] == pytest.approx(4.0)

        assert amp["signal_power_in"] == pytest.approx(4.0)
        assert amp["noise_power_in"] == pytest.approx(1.0)
        assert amp["signal_power_out"] == pytest.approx(12.0)
        assert amp["noise_power_out"] == pytest.approx(3.0)
        assert amp["signal_gain"] == pytest.approx(3.0)
        assert amp["noise_gain"] == pytest.approx(3.0)
        assert amp["snr"] == pytest.approx(4.0)

    def test_compute_is_idempotent_and_resets_the_data_list(self):
        budget = lc.LinkContainer()
        budget.add_component(lc.SignalSource("src", "", signal_power=1.0))
        budget.compute()
        budget.compute()
        assert len(budget.data_list) == 1

    def test_snr_degrades_through_a_lossy_noisy_chain(self):
        budget = lc.LinkContainer()
        budget.add_component(lc.SignalSource("src", "", signal_power=1.0, noise_power=1e-3))
        budget.add_component(lc.NoiseFigure("nf", "", noise_figure=3.0))
        budget.compute()
        source, after_nf = budget.data_list
        assert after_nf["snr"] < source["snr"]


class TestPublish:
    def test_publish_computes_then_delegates_to_the_publisher(self):
        budget = lc.LinkContainer(power_units="mW")
        rec = RecordingPublisher()
        budget.install_publisher(rec)
        budget.add_component(lc.SignalSource("src", "", signal_power=2.0, noise_power=1.0))

        budget.publish()

        assert len(rec.calls) == 1
        data_list, power_units = rec.calls[0]
        assert power_units == "mW"
        assert data_list[0]["signal_power_out"] == pytest.approx(2.0)
        assert data_list is not budget.data_list or len(data_list) == 1
