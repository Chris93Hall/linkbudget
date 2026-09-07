"""
link_container.py

The `LinkContainer` -- the object that holds an ordered list of
components and drives the computation -- and the whole family of signal-chain
components (`Component` and its subclasses).

A budget is built by adding components in order; ``compute()`` then threads
signal and noise power through each, recording the per-stage gain and SNR.
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod

import numpy as np

from . import _validate, convert, publishers
from ._types import StageData, StageList
from .checks import LinkBudgetWarning, check_budget
from .summary import BudgetSummary, summarize


class LinkContainer:
    """Holds the ordered chain of components and drives the computation.

    Add components with `add_component`, then `publish` (report
    it), `summary` (figures of merit) or `compute` (just fill
    `data_list`).

    ``power_units`` is a *display* label for whatever linear unit the
    ``signal_power`` / ``noise_power`` values are in -- keep it consistent
    across the whole chain (``ThermalNoise`` works in watts).
    ``carrier_frequency`` / ``noise_bandwidth`` / ``data_rate`` /
    ``symbol_rate`` are optional context `summary` uses to derive the
    figures of merit.  With ``warn=True`` (the default), `compute`
    emits a `LinkBudgetWarning` for each dubious
    configuration it finds.
    """

    def __init__(self, power_units: str = 'W', carrier_frequency: float | None = None,
                 noise_bandwidth: float | None = None, data_rate: float | None = None,
                 symbol_rate: float | None = None, warn: bool = True) -> None:
        self.components_list: list[Component] = []
        self.data_list: StageList = []
        self.publishers: list[publishers.Publisher] = [publishers.StdOutPublisher()]
        self.power_units = power_units
        # optional context used by summary() to derive figures of merit
        self.carrier_frequency = _validate.optional_positive(
            "carrier_frequency", carrier_frequency)
        self.noise_bandwidth = _validate.optional_positive("noise_bandwidth", noise_bandwidth)
        self.data_rate = _validate.optional_positive("data_rate", data_rate)
        self.symbol_rate = _validate.optional_positive("symbol_rate", symbol_rate)
        # emit LinkBudgetWarning from compute() when the budget looks dubious
        self.warn = warn

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
        """Compute the budget and hand it to every installed publisher."""
        self.compute()
        for publisher in self.publishers:
            publisher.publish(self.data_list, power_units=self.power_units)

    def summary(self) -> BudgetSummary:
        """Compute the budget and return a `BudgetSummary`
        with the standard figures of merit (EIRP, G/T, C/N0, Eb/N0, link
        margin, ...)."""
        self.compute()
        return summarize(self.data_list, self.components_list,
                         noise_bandwidth=self.noise_bandwidth,
                         data_rate=self.data_rate,
                         symbol_rate=self.symbol_rate,
                         carrier_frequency=self.carrier_frequency)

    def add_component(self, component: Component) -> None:
        """Append ``component`` to the chain (order matters)."""
        self.components_list.append(component)

    def check(self) -> list[str]:
        """Compute the budget and return a list of warnings about physically
        dubious or likely-wrong configurations (an empty list means it looks
        fine).  These are the messages ``compute()`` emits as
        `LinkBudgetWarning` unless the container was
        built with ``warn=False``."""
        self.compute()
        return check_budget(self.data_list, self.carrier_frequency)

    def compute(self) -> None:
        """Run signal and noise power through every component in order.

        Fills `data_list` with one stage dict per component, adding
        ``snr``, ``signal_gain`` and ``noise_gain`` to each.  Emits a
        `LinkBudgetWarning` per issue found unless
        ``self.warn`` is false.
        """
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

        if self.warn:
            for message in check_budget(self.data_list, self.carrier_frequency):
                warnings.warn(message, LinkBudgetWarning, stacklevel=2)

class Component(ABC):
    """Abstract base class for every link-budget component.

    A component transforms an incoming ``(signal_power, noise_power)`` pair
    and returns a stage dict (see `StageData`).  The class attributes
    below are read by ``LinkContainer.summary()``:

    * ``is_propagation`` -- set ``True`` on path-loss stages; the signal power
      entering the first one is the budget's EIRP and their combined loss is
      the total propagation loss.
    * ``is_margin`` -- set ``True`` on a `LinkMargin`.
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
    """Injects signal and/or noise power into the chain.

    Use it as a transmitter (``signal_power`` only) or as a noise source
    (``noise_power`` only); its powers are *added* to whatever is already in
    the chain.
    """

    def __init__(self, name: str, description: str, signal_power: float = 1.0,
                 noise_power: float = 0.0) -> None:
        self.name = name
        self.description = description
        self.signal_power = _validate.non_negative("signal_power", signal_power)
        self.noise_power = _validate.non_negative("noise_power", noise_power)

    def propagate_signal(self, signal_power: float = 0.0,
                         noise_power: float = 0.0) -> StageData:
        """Add this source's ``signal_power`` and ``noise_power`` to the chain."""
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power + self.signal_power,
                     'noise_power_out': noise_power + self.noise_power}
        return data_dict

class FreeSpacePathLoss(Component):
    """Free-space path loss over ``distance`` (metres) at ``frequency`` (Hz).

    Applies ``(4*pi*d*f / c)**2`` of loss to both the signal and the noise.
    For a two-way reflective (radar) path use `RadarPathLoss` instead.
    """

    is_propagation = True

    def __init__(self, name: str, description: str, distance: float,
                 frequency: float) -> None:
        self.name = name
        self.description = description
        self.distance = _validate.positive("distance", distance)
        self.frequency = _validate.positive("frequency", frequency)

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Divide the signal and noise power by the free-space path loss."""
        fspl = (4.0 * np.pi * self.distance * self.frequency / 2.99792458e8) ** 2
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power / fspl,
                     'noise_power_out': noise_power / fspl,
                     'distance': self.distance,
                     'frequency': self.frequency,
                     'speed_of_light': 2.99792458e8,
                     'speed_of_light_units': 'meters per second',
                     'free_space_path_loss_formula':
                         '(4.0 * Pi * frequency * distance / speed_of_light) ^ 2'}
        return data_dict

class Gain(Component):
    """Applies a fixed gain (or, if negative, a loss) to both the signal and
    the noise.

    ``gain`` is in dB when ``db=True`` (the default) or a linear multiplier
    when ``db=False``.  Set ``role="tx"`` / ``"rx"`` to mark an antenna so
    ``LinkContainer.summary()`` can find the receive antenna for G/T.
    """

    def __init__(self, name: str, description: str, gain: float, db: bool = True,
                 role: str | None = None) -> None:
        self.name = name
        self.description = description
        self.gain = gain
        self.db = db
        # optional "tx" / "rx" tag so LinkContainer.summary() can find the
        # receive antenna when computing G/T
        self.role = _validate.one_of("role", role, (None, "tx", "rx"))

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Multiply the signal and noise power by the (linearised) gain."""
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
    """Adds quantization noise for a converter of ``total_bits`` resolution
    driven ``headroom_db`` below full scale.

    Signal power passes through unchanged; the quantization noise
    ``(S+N) / (4**effective_bits) / 12`` is added to the noise, where
    ``effective_bits = total_bits - headroom_db / 6.0206``.
    """

    def __init__(self, name: str = 'Quantization noise', description: str = '',
                 total_bits: float = 12, headroom_db: float = 0) -> None:
        self.name = name
        self.description = description
        self.total_bits = _validate.positive("total_bits", total_bits)
        self.headroom_db = _validate.non_negative("headroom_db", headroom_db)

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Add the quantization noise to the noise power."""
        total_power = signal_power + noise_power # assume uncorrelated noise
        headroom_bits = self.headroom_db / 6.0206  # 6.02 dB per bit, the standard ADC backoff rule
        effective_bits = self.total_bits - headroom_bits
        divisor = 4.0**effective_bits
        quant_noise = float("inf") if divisor == 0.0 else total_power / divisor / 12.0
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
    """Analog-to-digital converter, in one step: an input buffer / driver
    stage (``gain_db``, ``noise_figure_db``) followed by quantization noise
    from ``total_bits`` and ``headroom_db``.

    Internally composes `RFComponent` with `QuantizationNoise`,
    so it behaves exactly like those two back to back.  ``sample_rate`` (Hz)
    is informational only.
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
        self.sample_rate = _validate.optional_positive("sample_rate", sample_rate)
        self._input_stage = RFComponent(gain=gain_db, noise_figure=noise_figure_db)
        self._quantizer = QuantizationNoise(total_bits=total_bits, headroom_db=headroom_db)

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Apply the buffer stage, then the quantization noise."""
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
    """Digital-to-analog converter, in one step: quantization noise from
    ``total_bits`` / ``headroom_db`` followed by an output driver stage
    (``gain_db``, ``noise_figure_db``) -- the reverse ordering of
    `AnalogToDigitalConverter`.

    Internally composes `QuantizationNoise` with `RFComponent`.
    ``sample_rate`` (Hz) is informational only.
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
        self.sample_rate = _validate.optional_positive("sample_rate", sample_rate)
        self._quantizer = QuantizationNoise(total_bits=total_bits, headroom_db=headroom_db)
        self._output_stage = RFComponent(gain=gain_db, noise_figure=noise_figure_db)

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Apply the quantization noise, then the output driver stage."""
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
    """Models filtering / retuning to a narrower sub-band.

    Noise scales by the ``output`` / ``input`` bandwidth ratio; the signal
    scales by the fraction of the ``signal`` band that survives inside the
    ``output`` band (zero if they do not overlap).  All six band edges are in
    Hz; each ``*_upper_freq`` must exceed its ``*_lower_freq``.
    """

    def __init__(self, name: str = 'Sub-band Tuner', description: str = '',
                 input_upper_freq: float = 1e6, input_lower_freq: float = 0.0,
                 signal_upper_freq: float = 4e6, signal_lower_freq: float = 2e6,
                 output_upper_freq: float = 3e6, output_lower_freq: float = 2e6) -> None:

        self.name = name
        self.description = description
        for edge, value in (("input_lower_freq", input_lower_freq),
                            ("input_upper_freq", input_upper_freq),
                            ("signal_lower_freq", signal_lower_freq),
                            ("signal_upper_freq", signal_upper_freq),
                            ("output_lower_freq", output_lower_freq),
                            ("output_upper_freq", output_upper_freq)):
            _validate.non_negative(edge, value)
        for band, lower, upper in (("input", input_lower_freq, input_upper_freq),
                                   ("signal", signal_lower_freq, signal_upper_freq),
                                   ("output", output_lower_freq, output_upper_freq)):
            if not upper > lower:
                raise ValueError(
                    f"{band} band is empty: {band}_upper_freq ({upper}) must be "
                    f"greater than {band}_lower_freq ({lower})")
        self.input_upper_freq = input_upper_freq
        self.input_lower_freq = input_lower_freq
        self.signal_upper_freq = signal_upper_freq
        self.signal_lower_freq = signal_lower_freq
        self.output_upper_freq = output_upper_freq
        self.output_lower_freq = output_lower_freq

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Scale signal by the surviving-band fraction and noise by the
        output/input bandwidth ratio."""
        noise_reduction_ratio = (
            (self.output_upper_freq - self.output_lower_freq)
            / (self.input_upper_freq - self.input_lower_freq))
        signal_bw = self.signal_upper_freq - self.signal_lower_freq
        # the surviving signal band is the overlap of the signal and output
        # bands -- clamp to zero when they do not overlap
        new_signal_bw = max(0.0,
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
    """Adds a physical thermal noise floor of ``k * temperature_k * bandwidth``
    watts to the noise power (signal unchanged).

    Because the floor is an absolute power in watts, every power value in the
    budget should also be in watts if you use this component.
    """

    def __init__(self, name: str = 'Thermal noise floor', description: str = '',
                 temperature_k: float = 290.0, bandwidth: float = 1.0) -> None:
        self.name = name
        self.description = description
        self.temperature_k = _validate.positive("temperature_k", temperature_k)
        self.bandwidth = _validate.positive("bandwidth", bandwidth)

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Add ``k*T*B`` to the noise power."""
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
    """Aggregate implementation-margin loss: attenuates the **signal only**
    (the noise is left untouched), matching the link-budget convention of
    "implementation loss" as an SNR penalty rather than a physical attenuator.

    The four ``*_loss_db`` terms are summed into ``total_loss_db``.  For a
    physical attenuator that reduces signal and noise together, use a
    negative-dB `Gain`.
    """

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
        """Divide the signal power by the summed loss; leave noise untouched."""
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
    """`ImplementationLoss` specialised to a single cable-loss term."""

    def __init__(self, name: str = 'Cable loss', description: str = '',
                 loss_db: float = 0.0) -> None:
        super().__init__(name=name, description=description, cable_loss_db=loss_db)

class PointingLoss(ImplementationLoss):
    """`ImplementationLoss` specialised to a single pointing-loss term."""

    def __init__(self, name: str = 'Pointing loss', description: str = '',
                 loss_db: float = 0.0) -> None:
        super().__init__(name=name, description=description, pointing_loss_db=loss_db)

class PolarizationLoss(ImplementationLoss):
    """`ImplementationLoss` specialised to a single polarization-loss term."""

    def __init__(self, name: str = 'Polarization loss', description: str = '',
                 loss_db: float = 0.0) -> None:
        super().__init__(name=name, description=description, polarization_loss_db=loss_db)

class NoiseFigure(Component):
    """A lossless / unity-gain noisy stage: degrades the noise power by
    ``noise_figure`` (dB) and leaves the signal unchanged."""

    def __init__(self, name: str = 'Noise figure', description: str = '',
                 noise_figure: float = 1.0) -> None:
        self.name = name
        self.description = description
        self.noise_figure = noise_figure

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Multiply the noise power by the noise factor."""
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
    """A generic gain block with a noise figure (e.g. an amplifier).

    The signal scales by ``gain`` (dB); the noise scales by ``gain`` times
    the ``noise_figure`` (dB) noise factor, so the SNR degrades by exactly
    the noise figure.
    """

    def __init__(self, name: str = 'RF Component', description: str = '',
                 gain: float = 1.0, noise_figure: float = 1.0) -> None:
        self.name = name
        self.description = description
        self.gain = gain
        self.noise_figure = noise_figure

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Apply the gain to the signal and gain*noise-factor to the noise."""
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
    """Scales the signal and noise by a plain (unitless) ``rcs_db`` power
    multiplier -- the target-reflection term of a two-way radar path.

    Chain it between two `RadarPathLossOneWay` legs to reproduce a
    `RadarPathLoss`.
    """

    def __init__(self, name: str = 'RCS', description: str = '',
                 rcs_db: float = 0.0) -> None:
        self.name = name
        self.description = description
        self.rcs_db = rcs_db

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Multiply the signal and noise power by ``10**(rcs_db/10)``."""
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
    """Two-way radar path loss in a single physically-consistent step:
    transmitted signal reflected off a target of the given radar cross
    section and returned to the receiver.

    ::

        Pr / Pt = (wavelength**2 * rcs) / ((4*Pi)**3 * tx_distance**2 * rx_distance**2)

    For monostatic radar (co-located transmitter/receiver) pass just
    ``distance``; for bistatic pass ``tx_distance`` and ``rx_distance``.
    Unlike chaining `FreeSpacePathLoss` twice around
    `RadarCrossSection`, this applies the wavelength-dependent term
    exactly once (matching the standard radar range equation) rather than
    once per leg -- which otherwise overstates the loss by
    ``wavelength**2 / (4*Pi)`` (~41 dB at X-band).
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
        self.tx_distance = _validate.positive("tx_distance", tx_distance)
        self.rx_distance = _validate.positive("rx_distance", rx_distance)
        self.frequency = _validate.positive("frequency", frequency)
        self.rcs_db = rcs_db

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Apply the two-way radar range-equation path term."""
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
    """One calibrated leg of a two-way radar path.

    ::

        RadarPathLossOneWay(distance=R1) -> RadarCrossSection(rcs_db)
            -> RadarPathLossOneWay(distance=R2)

    is equivalent to ``RadarPathLoss(tx_distance=R1, rx_distance=R2, rcs_db=rcs_db)``.
    Each leg implements ``Pr / Pt = wavelength / ((4*Pi)**1.5 * distance**2)``, so
    two legs plus the plain `RadarCrossSection` multiplier reproduce
    the radar range equation.

    This is **not** the same formula as `FreeSpacePathLoss` -- for a
    direct, non-reflective antenna-to-antenna link use that instead.
    """

    is_propagation = True

    def __init__(self, name: str = 'Radar path (one-way)', description: str = '',
                 distance: float = 1.0, frequency: float = 1e9) -> None:
        self.name = name
        self.description = description
        self.distance = _validate.positive("distance", distance)
        self.frequency = _validate.positive("frequency", frequency)

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Apply this leg's half of the two-way wavelength term."""
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
    """Antenna-array gain from an element count: scales both the signal and
    the noise by ``num_elements``.

    Set ``role="tx"`` / ``"rx"`` to mark the array as an antenna for
    ``LinkContainer.summary()``.
    """

    def __init__(self, name: str = 'Array Factor', description: str = '',
                 num_elements: int = 1, role: str | None = None) -> None:
        self.name = name
        self.description = description
        self.role = _validate.one_of("role", role, (None, "tx", "rx"))
        if num_elements < 1:
            raise ValueError(f"num_elements must be at least 1 (got {num_elements!r})")
        self.num_elements = num_elements

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Multiply the signal and noise power by ``num_elements``."""
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
    """Frequency-converts the signal against a local oscillator, applying
    conversion loss/gain and noise figure.

    ``noise_figure_db`` defaults to ``conversion_loss_db`` (the passive-mixer
    rule of thumb).  If ``rf_frequency`` is given the resulting
    ``if_frequency`` is reported (``rf + lo`` for ``mode="upconvert"``,
    ``|rf - lo|`` otherwise).  If ``image_reject_db`` is given, the extra
    noise folded in from the unrejected image band is added on top; omit it
    to assume an ideal, fully image-rejected mixer.
    """

    def __init__(self, name: str = 'Mixer', description: str = '',
                 lo_frequency: float = 0.0, rf_frequency: float | None = None,
                 conversion_loss_db: float = 0.0, noise_figure_db: float | None = None,
                 mode: str = 'downconvert', image_reject_db: float | None = None) -> None:
        self.name = name
        self.description = description
        self.lo_frequency = _validate.non_negative("lo_frequency", lo_frequency)
        self.rf_frequency = _validate.optional_positive("rf_frequency", rf_frequency)
        self.conversion_loss_db = conversion_loss_db
        # passive mixers have a noise figure approximately equal to conversion loss
        self.noise_figure_db = conversion_loss_db if noise_figure_db is None else noise_figure_db
        self.mode = _validate.one_of("mode", mode, ("downconvert", "upconvert"))
        self.image_reject_db = image_reject_db

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Apply conversion loss/gain, noise figure and any image noise."""
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
    """Coherent integration (e.g. pulse integration): the signal power scales
    by ``timespan`` (the coherent processing gain) while the noise power is
    left unchanged, so the SNR improves by ``timespan``."""

    def __init__(self, name: str = 'Integration', description: str = '',
                 timespan: float = 1.0) -> None:
        self.name = name
        self.description = description
        self.timespan = _validate.positive("timespan", timespan)

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Multiply the signal power by ``timespan``; leave noise unchanged."""
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power * self.timespan,
                     'noise_power_out': noise_power,
                     'integration_time': self.timespan}
        return data_dict
