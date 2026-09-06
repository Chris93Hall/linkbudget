"""
link_container.py
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from . import convert, publishers
from ._types import StageData, StageList
from .summary import BudgetSummary, summarize


class LinkContainer:
    def __init__(self, power_units: str = 'W', carrier_frequency: float | None = None,
                 noise_bandwidth: float | None = None, data_rate: float | None = None,
                 symbol_rate: float | None = None) -> None:
        self.components_list: list[Component] = []
        self.data_list: StageList = []
        self.publishers: list[publishers.Publisher] = [publishers.StdOutPublisher()]
        self.power_units = power_units
        # optional context used by summary() to derive figures of merit
        self.carrier_frequency = carrier_frequency
        self.noise_bandwidth = noise_bandwidth
        self.data_rate = data_rate
        self.symbol_rate = symbol_rate

    @property
    def publisher(self) -> publishers.Publisher | None:
        """The first installed publisher (backwards-compatible accessor)."""
        return self.publishers[0] if self.publishers else None

    @publisher.setter
    def publisher(self, value: publishers.Publisher | None) -> None:
        self.publishers = [value] if value is not None else []

    def install_publisher(self, publisher: publishers.Publisher) -> None:
        """Replace every installed publisher with ``publisher``."""
        self.publishers = [publisher]

    def add_publisher(self, publisher: publishers.Publisher) -> None:
        """Add another publisher; ``publish()`` runs every installed one."""
        self.publishers.append(publisher)

    def publish(self) -> None:
        self.compute()
        for publisher in self.publishers:
            publisher.publish(self.data_list, power_units=self.power_units)

    def summary(self) -> BudgetSummary:
        """Compute the budget and return a :class:`~linkbudget.summary.BudgetSummary`
        with the standard figures of merit (EIRP, G/T, C/N0, Eb/N0, link
        margin, ...)."""
        self.compute()
        return summarize(self.data_list, self.components_list,
                         noise_bandwidth=self.noise_bandwidth,
                         data_rate=self.data_rate,
                         symbol_rate=self.symbol_rate,
                         carrier_frequency=self.carrier_frequency)

    def add_component(self, component: Component) -> None:
        self.components_list.append(component)

    def compute(self) -> None:
        # reset data list
        self.data_list = []
        # start with no signal or noise
        signal_power = 0.0
        noise_power = 0.0
        for component in self.components_list:
            data_dict = component.propagate_signal(signal_power, noise_power)
            signal_power = data_dict['signal_power_out']
            noise_power = data_dict['noise_power_out']
            if noise_power == 0.0:
                snr = np.inf
            else:
                snr = signal_power / noise_power
            data_dict['snr'] = snr
            if data_dict['noise_power_in'] == 0.0:
                data_dict['noise_gain'] = np.inf
            else:
                data_dict['noise_gain'] = (
                    data_dict['noise_power_out'] / data_dict['noise_power_in'])
            if data_dict['signal_power_in'] == 0.0:
                data_dict['signal_gain'] = np.inf
            else:
                data_dict['signal_gain'] = (
                    data_dict['signal_power_out'] / data_dict['signal_power_in'])
            self.data_list.append(data_dict)

class Component(ABC):
    """Abstract base class for every link-budget component.

    A component transforms an incoming ``(signal_power, noise_power)`` pair
    and returns a stage dict (see :attr:`StageData`).  The class attributes
    below are read by :meth:`LinkContainer.summary`:

    * ``is_propagation`` -- set ``True`` on path-loss stages; the signal power
      entering the first one is the budget's EIRP and their combined loss is
      the total propagation loss.
    * ``is_margin`` -- set ``True`` on a :class:`~linkbudget.margin.LinkMargin`.
    * ``role`` -- ``"tx"`` / ``"rx"`` on an antenna, so the receive antenna
      can be identified for G/T.

    Components are duck-typed -- ``LinkContainer`` only calls
    ``propagate_signal`` -- so inheriting from this class is a convention, not
    a requirement.
    """

    is_propagation: bool = False
    is_margin: bool = False
    role: str | None = None

    @abstractmethod
    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    @abstractmethod
    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Propagate signal and noise power through this component.

        Returns a dict describing this stage of the link, with keys such as
        ``name``, ``description``, ``signal_power_in``/``signal_power_out``
        and ``noise_power_in``/``noise_power_out``.
        """

class SignalSource(Component):
    def __init__(self, name: str, description: str, signal_power: float = 1.0,
                 noise_power: float = 0.0) -> None:
        self.name = name
        self.description = description
        self.signal_power = signal_power
        self.noise_power = noise_power

    def propagate_signal(self, signal_power: float = 0.0,
                         noise_power: float = 0.0) -> StageData:
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power + self.signal_power,
                     'noise_power_out': noise_power + self.noise_power}
        return data_dict

class FreeSpacePathLoss(Component):
    is_propagation = True

    def __init__(self, name: str, description: str, distance: float,
                 frequency: float) -> None:
        self.name = name
        self.description = description
        self.distance = distance
        self.frequency = frequency

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        fspl = (4.0 * np.pi * self.distance * self.frequency / 2.99792458e8) ** 2
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power / fspl,
                     'noise_power_out': noise_power / fspl,
                     'speed_of_light': 2.99792458e8,
                     'speed_of_light_units': 'meters per second',
                     'free_space_path_loss_formula':
                         '(4.0 * Pi * frequency * distance / speed_of_light) ^ 2'}
        return data_dict

class Gain(Component):
    def __init__(self, name: str, description: str, gain: float, db: bool = True,
                 role: str | None = None) -> None:
        self.name = name
        self.description = description
        self.gain = gain
        self.db = db
        # optional "tx" / "rx" tag so LinkContainer.summary() can find the
        # receive antenna when computing G/T
        self.role = role

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        gain = self.gain
        if self.db:
            gain = 10.0**(gain/10.0)

        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power * gain,
                     'noise_power_out': noise_power * gain}
        return data_dict

class QuantizationNoise(Component):
    def __init__(self, name: str = 'Quantization noise', description: str = '',
                 total_bits: float = 12, headroom_db: float = 0) -> None:
        self.name = name
        self.description = description
        self.total_bits = total_bits
        self.headroom_db = headroom_db

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        total_power = signal_power + noise_power # assume uncorrelated noise
        headroom_bits = self.headroom_db / 6.0206  # 6.02 dB per bit, the standard ADC backoff rule
        effective_bits = self.total_bits - headroom_bits
        quant_noise = total_power / 4.0**effective_bits / 12.0
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power,
                     'noise_power_out': noise_power + quant_noise,
                     'quantization_noise': quant_noise,
                     'total_bits': self.total_bits,
                     'effective_bits': effective_bits,
                     'headroom_db': self.headroom_db,
                     'headroom_bits': headroom_bits}
        return data_dict


class AnalogToDigitalConverter(Component):
    """
    Analog-to-digital converter: an input buffer/driver stage (gain and
    noise figure) followed by quantization noise from the converter's
    resolution and headroom, in a single step. Internally composes
    RFComponent (gain_db, noise_figure_db) with QuantizationNoise
    (total_bits, headroom_db), so its noise behavior matches using those
    two components back-to-back.
    """
    def __init__(self, name: str = 'ADC', description: str = '', gain_db: float = 0.0,
                 noise_figure_db: float = 0.0, total_bits: float = 12.0,
                 headroom_db: float = 0.0, sample_rate: float | None = None) -> None:
        self.name = name
        self.description = description
        self.gain_db = gain_db
        self.noise_figure_db = noise_figure_db
        self.total_bits = total_bits
        self.headroom_db = headroom_db
        self.sample_rate = sample_rate
        self._input_stage = RFComponent(gain=gain_db, noise_figure=noise_figure_db)
        self._quantizer = QuantizationNoise(total_bits=total_bits, headroom_db=headroom_db)

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        stage1 = self._input_stage.propagate_signal(signal_power, noise_power)
        stage2 = self._quantizer.propagate_signal(
            stage1['signal_power_out'], stage1['noise_power_out'])
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': stage2['signal_power_out'],
                     'noise_power_out': stage2['noise_power_out'],
                     'gain_db': self.gain_db,
                     'noise_figure_db': self.noise_figure_db,
                     'total_bits': self.total_bits,
                     'effective_bits': stage2['effective_bits'],
                     'headroom_db': self.headroom_db,
                     'headroom_bits': stage2['headroom_bits'],
                     'quantization_noise': stage2['quantization_noise'],
                     'sample_rate': self.sample_rate}
        return data_dict

class DigitalToAnalogConverter(Component):
    """
    Digital-to-analog converter: quantization noise from the converter's
    output resolution and headroom, followed by an output driver stage
    (gain and noise figure), in a single step -- the reverse ordering of
    AnalogToDigitalConverter. Internally composes QuantizationNoise
    (total_bits, headroom_db) with RFComponent (gain_db, noise_figure_db).
    """
    def __init__(self, name: str = 'DAC', description: str = '', total_bits: float = 12.0,
                 headroom_db: float = 0.0, gain_db: float = 0.0,
                 noise_figure_db: float = 0.0, sample_rate: float | None = None) -> None:
        self.name = name
        self.description = description
        self.total_bits = total_bits
        self.headroom_db = headroom_db
        self.gain_db = gain_db
        self.noise_figure_db = noise_figure_db
        self.sample_rate = sample_rate
        self._quantizer = QuantizationNoise(total_bits=total_bits, headroom_db=headroom_db)
        self._output_stage = RFComponent(gain=gain_db, noise_figure=noise_figure_db)

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        stage1 = self._quantizer.propagate_signal(signal_power, noise_power)
        stage2 = self._output_stage.propagate_signal(
            stage1['signal_power_out'], stage1['noise_power_out'])
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': stage2['signal_power_out'],
                     'noise_power_out': stage2['noise_power_out'],
                     'total_bits': self.total_bits,
                     'effective_bits': stage1['effective_bits'],
                     'headroom_db': self.headroom_db,
                     'headroom_bits': stage1['headroom_bits'],
                     'quantization_noise': stage1['quantization_noise'],
                     'gain_db': self.gain_db,
                     'noise_figure_db': self.noise_figure_db,
                     'sample_rate': self.sample_rate}
        return data_dict

class SubBandTune(Component):
    def __init__(self, name: str = 'Sub-band Tuner', description: str = '',
                 input_upper_freq: float = 1e6, input_lower_freq: float = 0.0,
                 signal_upper_freq: float = 4e6, signal_lower_freq: float = 2e6,
                 output_upper_freq: float = 3e6, output_lower_freq: float = 2e6) -> None:

        self.name = name
        self.description = description
        self.input_upper_freq = input_upper_freq
        self.input_lower_freq = input_lower_freq
        self.signal_upper_freq = signal_upper_freq
        self.signal_lower_freq = signal_lower_freq
        self.output_upper_freq = output_upper_freq
        self.output_lower_freq = output_lower_freq

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        noise_reduction_ratio = (
            (self.output_upper_freq - self.output_lower_freq)
            / (self.input_upper_freq - self.input_lower_freq))
        signal_bw = self.signal_upper_freq - self.signal_lower_freq
        new_signal_bw = (
            min(self.output_upper_freq, self.signal_upper_freq)
            - max(self.output_lower_freq, self.signal_lower_freq))
        signal_reduction_ratio = new_signal_bw / signal_bw
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power * signal_reduction_ratio,
                     'noise_power_out': noise_power * noise_reduction_ratio,
                     'input_lower_frequency': self.input_lower_freq,
                     'input_upper_frequency': self.input_upper_freq,
                     'output_lower_frequency': self.output_lower_freq,
                     'output_upper_frequency': self.output_upper_freq,
                     'signal_lower_frequency_in': self.signal_lower_freq,
                     'signal_upper_frequency_in': self.signal_upper_freq}
        return data_dict

class ThermalNoise(Component):
    def __init__(self, name: str = 'Thermal noise floor', description: str = '',
                 temperature_k: float = 290.0, bandwidth: float = 1.0) -> None:
        self.name = name
        self.description = description
        self.temperature_k = temperature_k
        self.bandwidth = bandwidth

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        thermal_noise_power = convert.BOLTZMANN_CONSTANT * self.temperature_k * self.bandwidth
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power,
                     'noise_power_out': noise_power + thermal_noise_power,
                     'temperature_k': self.temperature_k,
                     'bandwidth': self.bandwidth,
                     'thermal_noise_power': thermal_noise_power,
                     'thermal_noise_power_dbw': convert.linear_to_db(thermal_noise_power)}
        return data_dict

class ImplementationLoss(Component):
    def __init__(self, name: str = 'Implementation loss', description: str = '',
                 cable_loss_db: float = 0.0, pointing_loss_db: float = 0.0,
                 polarization_loss_db: float = 0.0, other_loss_db: float = 0.0) -> None:
        self.name = name
        self.description = description
        self.cable_loss_db = cable_loss_db
        self.pointing_loss_db = pointing_loss_db
        self.polarization_loss_db = polarization_loss_db
        self.other_loss_db = other_loss_db

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        total_loss_db = (self.cable_loss_db + self.pointing_loss_db
                          + self.polarization_loss_db + self.other_loss_db)
        loss_linear = convert.db_to_linear(total_loss_db)
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power / loss_linear,
                     'noise_power_out': noise_power,
                     'cable_loss_db': self.cable_loss_db,
                     'pointing_loss_db': self.pointing_loss_db,
                     'polarization_loss_db': self.polarization_loss_db,
                     'other_loss_db': self.other_loss_db,
                     'total_loss_db': total_loss_db}
        return data_dict

class CableLoss(ImplementationLoss):
    def __init__(self, name: str = 'Cable loss', description: str = '',
                 loss_db: float = 0.0) -> None:
        super().__init__(name=name, description=description, cable_loss_db=loss_db)

class PointingLoss(ImplementationLoss):
    def __init__(self, name: str = 'Pointing loss', description: str = '',
                 loss_db: float = 0.0) -> None:
        super().__init__(name=name, description=description, pointing_loss_db=loss_db)

class PolarizationLoss(ImplementationLoss):
    def __init__(self, name: str = 'Polarization loss', description: str = '',
                 loss_db: float = 0.0) -> None:
        super().__init__(name=name, description=description, polarization_loss_db=loss_db)

class NoiseFigure(Component):
    def __init__(self, name: str = 'Noise figure', description: str = '',
                 noise_figure: float = 1.0) -> None:
        self.name = name
        self.description = description
        self.noise_figure = noise_figure

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        noise_factor = 10.0**(self.noise_figure/10.0)
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power,
                     'noise_power_out': noise_power * noise_factor,
                     'noise_figure': self.noise_figure,
                     'noise_factor': noise_factor}
        return data_dict

class RFComponent(Component):
    def __init__(self, name: str = 'RF Component', description: str = '',
                 gain: float = 1.0, noise_figure: float = 1.0) -> None:
        self.name = name
        self.description = description
        self.gain = gain
        self.noise_figure = noise_figure

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        noise_factor = 10.0**(self.noise_figure/10.0)
        gain_linear = 10.0**(self.gain/10.0)
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power * gain_linear,
                     'noise_power_out': noise_power * gain_linear * noise_factor,
                     'noise_figure': self.noise_figure,
                     'noise_factor': noise_factor,
                     'gain': self.gain}
        return data_dict

class RadarCrossSection(Component):
    def __init__(self, name: str = 'RCS', description: str = '',
                 rcs_db: float = 0.0) -> None:
        self.name = name
        self.description = description
        self.rcs_db = rcs_db

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        rcs_linear = convert.db_to_linear(self.rcs_db)
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power * rcs_linear,
                     'noise_power_out': noise_power * rcs_linear,
                     'rcs_db': self.rcs_db}
        return data_dict

class RadarPathLoss(Component):
    """
    Two-way radar path loss: transmitted signal reflected off a target with the
    given radar cross section and returned to the receiver, computed in a single
    physically-consistent step:

        Pr / Pt = (wavelength^2 * rcs) / ((4*Pi)^3 * tx_distance^2 * rx_distance^2)

    For monostatic radar (co-located transmitter/receiver), pass just
    `distance`. Unlike chaining FreeSpacePathLoss twice around
    RadarCrossSection, this applies the wavelength-dependent term exactly
    once (matching the standard radar range equation) rather than once per
    leg, which otherwise overstates the path loss by wavelength^2 / (4*Pi).
    """
    is_propagation = True

    def __init__(self, name: str = 'Radar path (two-way)', description: str = '',
                 distance: float | None = None, tx_distance: float | None = None,
                 rx_distance: float | None = None, frequency: float = 1e9,
                 rcs_db: float = 0.0) -> None:
        self.name = name
        self.description = description
        if distance is not None:
            tx_distance = distance
            rx_distance = distance
        if tx_distance is None or rx_distance is None:
            raise ValueError("give distance, or both tx_distance and rx_distance")
        self.tx_distance = tx_distance
        self.rx_distance = rx_distance
        self.frequency = frequency
        self.rcs_db = rcs_db

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        wavelength = 2.99792458e8 / self.frequency
        rcs_m2 = convert.db_to_linear(self.rcs_db)
        path_term = ((wavelength**2 * rcs_m2)
                     / ((4.0 * np.pi)**3 * self.tx_distance**2 * self.rx_distance**2))
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power * path_term,
                     'noise_power_out': noise_power * path_term,
                     'tx_distance': self.tx_distance,
                     'rx_distance': self.rx_distance,
                     'frequency': self.frequency,
                     'wavelength': wavelength,
                     'rcs_db': self.rcs_db,
                     'rcs_m2': rcs_m2,
                     'path_loss_db': convert.linear_to_db(1.0 / path_term)}
        return data_dict

class RadarPathLossOneWay(Component):
    """
    One leg of a two-way radar path (transmitter-to-target, or
    target-to-receiver), calibrated so that chaining two of these around a
    RadarCrossSection component reproduces the exact RadarPathLoss result:

        RadarPathLossOneWay(distance=R1) -> RadarCrossSection(rcs_db)
            -> RadarPathLossOneWay(distance=R2)

    is equivalent to:

        RadarPathLoss(tx_distance=R1, rx_distance=R2, rcs_db=rcs_db)

    Implements:

        Pr / Pt = wavelength / ((4*Pi)^1.5 * distance^2)

    so that two legs multiplied together contribute
    wavelength^2 / ((4*Pi)^3 * R1^2 * R2^2), and RadarCrossSection's plain
    (unitless) multiplier supplies the rcs term, together matching the
    standard radar range equation.

    This is NOT the same formula as FreeSpacePathLoss / a genuine one-way
    antenna-to-antenna link (each leg only carries half of the total
    wavelength-dependent term) -- for a direct, non-reflective path, use
    FreeSpacePathLoss instead.
    """
    is_propagation = True

    def __init__(self, name: str = 'Radar path (one-way)', description: str = '',
                 distance: float = 1.0, frequency: float = 1e9) -> None:
        self.name = name
        self.description = description
        self.distance = distance
        self.frequency = frequency

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        wavelength = 2.99792458e8 / self.frequency
        path_term = wavelength / ((4.0 * np.pi)**1.5 * self.distance**2)
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power * path_term,
                     'noise_power_out': noise_power * path_term,
                     'distance': self.distance,
                     'frequency': self.frequency,
                     'wavelength': wavelength,
                     'path_loss_db': convert.linear_to_db(1.0 / path_term)}
        return data_dict

class ArrayFactor(Component):
    def __init__(self, name: str = 'Array Factor', description: str = '',
                 num_elements: int = 1, role: str | None = None) -> None:
        self.name = name
        self.description = description
        self.role = role
        self.num_elements = num_elements

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power * self.num_elements,
                     'noise_power_out': noise_power * self.num_elements,
                     'number_of_elements': self.num_elements,
                     'gain': f'{10.0*np.log10(self.num_elements)} dB'}
        return data_dict

class Mixer(Component):
    """
    Frequency-converts the signal (up- or down-conversion against a local
    oscillator), applying conversion loss/gain and noise figure.
    """
    def __init__(self, name: str = 'Mixer', description: str = '',
                 lo_frequency: float = 0.0, rf_frequency: float | None = None,
                 conversion_loss_db: float = 0.0, noise_figure_db: float | None = None,
                 mode: str = 'downconvert', image_reject_db: float | None = None) -> None:
        self.name = name
        self.description = description
        self.lo_frequency = lo_frequency
        self.rf_frequency = rf_frequency
        self.conversion_loss_db = conversion_loss_db
        # passive mixers have a noise figure approximately equal to conversion loss
        self.noise_figure_db = conversion_loss_db if noise_figure_db is None else noise_figure_db
        self.mode = mode
        self.image_reject_db = image_reject_db

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        conversion_gain_linear = convert.db_to_linear(-self.conversion_loss_db)
        noise_factor = convert.db_to_linear(self.noise_figure_db)

        signal_power_out = signal_power * conversion_gain_linear
        noise_power_out = noise_power * conversion_gain_linear * noise_factor

        image_noise_power = 0.0
        if self.image_reject_db is not None:
            image_reject_linear = convert.db_to_linear(self.image_reject_db)
            image_noise_power = (noise_power * conversion_gain_linear) / image_reject_linear
            noise_power_out += image_noise_power

        if self.rf_frequency is not None:
            if self.mode == 'upconvert':
                if_frequency = self.rf_frequency + self.lo_frequency
            else:
                if_frequency = abs(self.rf_frequency - self.lo_frequency)
        else:
            if_frequency = None

        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power_out,
                     'noise_power_out': noise_power_out,
                     'lo_frequency': self.lo_frequency,
                     'rf_frequency': self.rf_frequency,
                     'if_frequency': if_frequency,
                     'mode': self.mode,
                     'conversion_loss_db': self.conversion_loss_db,
                     'noise_figure_db': self.noise_figure_db,
                     'image_reject_db': self.image_reject_db,
                     'image_noise_power': image_noise_power}
        return data_dict

class Integrate(Component):
    """
    Coherent integration (e.g. pulse integration): builds up SNR by summing
    `timespan` samples/pulses coherently. Signal power scales by `timespan`
    (the coherent processing gain); noise power is unaffected.
    """
    def __init__(self, name: str = 'Integration', description: str = '',
                 timespan: float = 1.0) -> None:
        self.name = name
        self.description = description
        self.timespan = timespan

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power * self.timespan,
                     'noise_power_out': noise_power,
                     'integration_time': self.timespan}
        return data_dict
