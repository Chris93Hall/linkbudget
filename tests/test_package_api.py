"""The public surface re-exported from the linkbudget package."""

import importlib

import pytest

import linkbudget

EXPECTED_EXPORTS = [
    "LinkContainer",
    "SignalSource",
    "FreeSpacePathLoss",
    "Gain",
    "SubBandTune",
    "QuantizationNoise",
    "RadarCrossSection",
    "ArrayFactor",
    "ThermalNoise",
    "ImplementationLoss",
    "CableLoss",
    "PointingLoss",
    "PolarizationLoss",
    "Mixer",
    "NoiseFigure",
    "RFComponent",
    "Integrate",
    "RadarPathLoss",
    "RadarPathLossOneWay",
    "AnalogToDigitalConverter",
    "DigitalToAnalogConverter",
    "ParabolicDish",
    "BeamPointingLoss",
    "PolarizationMismatchLoss",
    "AntennaNoiseTemperature",
    "AtmosphericAbsorption",
    "RainAttenuation",
    "CloudFogAttenuation",
    "TroposphericScintillation",
    "TwoRayGroundReflection",
    "LinkMargin",
    "Component",
    "BudgetSummary",
    "LinkBudgetWarning",
    "check_budget",
    "StdOutPublisher",
    "PDFPublisher",
    "HTMLPublisher",
    "MarkdownPublisher",
    "WaterfallPublisher",
]

# every public component class, across all the component modules
COMPONENT_NAMES = [
    "SignalSource", "FreeSpacePathLoss", "Gain", "SubBandTune", "QuantizationNoise",
    "RadarCrossSection", "ArrayFactor", "ThermalNoise", "ImplementationLoss",
    "CableLoss", "PointingLoss", "PolarizationLoss", "Mixer", "NoiseFigure",
    "RFComponent", "Integrate", "RadarPathLoss", "RadarPathLossOneWay",
    "AnalogToDigitalConverter", "DigitalToAnalogConverter",
    "ParabolicDish", "BeamPointingLoss", "PolarizationMismatchLoss",
    "AntennaNoiseTemperature",
    "AtmosphericAbsorption", "RainAttenuation", "CloudFogAttenuation",
    "TroposphericScintillation", "TwoRayGroundReflection", "LinkMargin",
]


@pytest.mark.parametrize("name", EXPECTED_EXPORTS)
def test_symbol_is_exported(name):
    assert hasattr(linkbudget, name)


@pytest.mark.parametrize("name", COMPONENT_NAMES)
def test_every_component_inherits_the_base_class(name):
    assert issubclass(getattr(linkbudget, name), linkbudget.Component)


def test_package_exposes_a_version_string():
    assert isinstance(linkbudget.__version__, str)
    assert linkbudget.__version__


def test_package_reimports_cleanly():
    importlib.reload(linkbudget)


def test_end_to_end_smoke(capsys):
    budget = linkbudget.LinkContainer()
    budget.add_component(linkbudget.SignalSource("tx", "", signal_power=10.0, noise_power=1e-6))
    budget.add_component(linkbudget.FreeSpacePathLoss("path", "", distance=1000.0, frequency=2.4e9))
    budget.add_component(linkbudget.Gain("rx gain", "", gain=20.0))
    budget.add_component(linkbudget.ThermalNoise("noise", "", bandwidth=1e6))
    budget.publish()

    out = capsys.readouterr().out
    assert "tx" in out
    assert len(budget.data_list) == 4
