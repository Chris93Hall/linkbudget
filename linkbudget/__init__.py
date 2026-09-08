"""RF / communications link-budget modelling."""

from . import convert, fom
from .antennas import (
    AntennaNoiseTemperature,
    BeamPointingLoss,
    ParabolicDish,
    PolarizationMismatchLoss,
    antenna_noise_temp_k,
    dish_gain_dbi,
    dish_half_power_beamwidth_deg,
    gaussian_beam_pointing_loss_db,
    polarization_efficiency,
)
from .checks import LinkBudgetWarning, check_budget
from .html_publisher import HTMLPublisher
from .link_container import (
    AnalogToDigitalConverter,
    ArrayFactor,
    CableLoss,
    Component,
    DigitalToAnalogConverter,
    FreeSpacePathLoss,
    Gain,
    ImplementationLoss,
    Integrate,
    LinkContainer,
    Mixer,
    NoiseFigure,
    PointingLoss,
    PolarizationLoss,
    QuantizationNoise,
    RadarCrossSection,
    RadarPathLoss,
    RadarPathLossOneWay,
    RFComponent,
    SignalSource,
    SubBandTune,
    ThermalNoise,
)
from .margin import LinkMargin
from .markdown_publisher import MarkdownPublisher
from .pdf_publisher import PDFPublisher
from .propagation import (
    AtmosphericAbsorption,
    CloudFogAttenuation,
    RainAttenuation,
    TroposphericScintillation,
    TwoRayGroundReflection,
)
from .publishers import StdOutPublisher
from .summary import BudgetSummary
from .waterfall_publisher import WaterfallPublisher

__all__ = [  # noqa: RUF022  -- grouped by role, not alphabetised
    "convert",
    "fom",
    # container + results
    "LinkContainer",
    "BudgetSummary",
    "Component",
    # signal-chain components
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
    # antennas
    "ParabolicDish",
    "BeamPointingLoss",
    "PolarizationMismatchLoss",
    "AntennaNoiseTemperature",
    "dish_gain_dbi",
    "dish_half_power_beamwidth_deg",
    "gaussian_beam_pointing_loss_db",
    "polarization_efficiency",
    "antenna_noise_temp_k",
    # propagation
    "AtmosphericAbsorption",
    "RainAttenuation",
    "CloudFogAttenuation",
    "TroposphericScintillation",
    "TwoRayGroundReflection",
    # margin
    "LinkMargin",
    # validation
    "LinkBudgetWarning",
    "check_budget",
    # publishers
    "StdOutPublisher",
    "PDFPublisher",
    "HTMLPublisher",
    "MarkdownPublisher",
    "WaterfallPublisher",
]
