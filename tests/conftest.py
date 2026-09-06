"""Shared fixtures for the linkbudget test suite."""

import pytest

from linkbudget import link_container as lc


@pytest.fixture
def small_budget():
    """A short but representative computed budget."""
    budget = lc.LinkContainer()
    budget.add_component(lc.SignalSource(
        "Transmitter", "Peak output power", signal_power=1000.0, noise_power=0.0,
    ))
    budget.add_component(lc.FreeSpacePathLoss(
        "Path loss", "Tx to Rx", distance=50e3, frequency=9.5e9,
    ))
    budget.add_component(lc.ThermalNoise(
        "Noise floor", "Receiver noise", temperature_k=290.0, bandwidth=2e6,
    ))
    budget.add_component(lc.RFComponent(
        "LNA", "Low-noise amplifier", gain=30.0, noise_figure=1.2,
    ))
    budget.compute()
    return budget


@pytest.fixture
def small_data_list(small_budget):
    return small_budget.data_list
