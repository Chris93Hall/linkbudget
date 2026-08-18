"""
link_container.py
"""

from abc import ABC, abstractmethod

import numpy as np

from . import convert
from . import publishers

class LinkContainer:
    def __init__(self, power_units='W'):
        self.components_list = []
        self.data_list = []
        self.publisher = publishers.StdOutPublisher()
        self.power_units = power_units

    def install_publisher(self, publisher):
        self.publisher = publisher

    def publish(self):
        self.compute()
        self.publisher.publish(self.data_list, power_units=self.power_units)

    def add_component(self, component):
        self.components_list.append(component)

    def compute(self):
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
                data_dict['noise_gain'] = data_dict['noise_power_out'] / data_dict['noise_power_in']
            if data_dict['signal_power_in'] == 0.0:
                data_dict['signal_gain'] = np.inf
            else:
                data_dict['signal_gain'] = data_dict['signal_power_out'] / data_dict['signal_power_in']
            self.data_list.append(data_dict)

class Component(ABC):
    """
    Abstract Component
    """
    @abstractmethod
    def __init__(self, name, description):
        self.name = name
        self.description = description

    @abstractmethod
    def propagate_signal(sig_power, noise_power):
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': sig_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': sig_power,
                     'noise_power_out': noise_power}
        return data_dict

class SignalSource(Component):
    def __init__(self, name, description, signal_power=1.0, noise_power=0.0):
        self.name = name
        self.description = description
        self.signal_power = signal_power
        self.noise_power = noise_power

    def propagate_signal(self, signal_power=0.0, noise_power=0.0):
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power + self.signal_power,
                     'noise_power_out': noise_power + self.noise_power}
        return data_dict

class FreeSpacePathLoss(Component):
    def __init__(self, name, description, distance, frequency):
        self.name = name
        self.description = description
        self.distance = distance
        self.frequency = frequency

    def propagate_signal(self, signal_power, noise_power):
        fspl = (4.0 * np.pi * self.distance * self.frequency / 2.99792458e8) ** 2
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power / fspl,
                     'noise_power_out': noise_power / fspl,
                     'speed_of_light': 2.99792458e8,
                     'speed_of_light_units': 'meters per second',
                     'free_space_path_loss_formula': '(4.0 * Pi * frequency * distance / speed_of_light) ^ 2'}
        return data_dict

class Gain(Component):
    def __init__(self, name, description, gain, db=True):
        self.name = name
        self.description = description
        self.gain = gain
        self.db = db

    def propagate_signal(self, signal_power, noise_power):
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

class QuantizationNoise:
    def __init__(self, name='Quantization noise', description='',  total_bits=12, headroom_db=0):
        self.name = name
        self.description = description
        self.total_bits = total_bits
        self.headroom_db = headroom_db
    
    def propagate_signal(self, signal_power, noise_power):
        total_power = signal_power + noise_power # assume uncorrelated noise
        headroom_bits = np.log2(10.0**(self.headroom_db/10.0))
        effective_bits = self.total_bits - headroom_bits
        quant_noise = total_power * (1.0 / 2.0**effective_bits) / 12.0
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
    def __init__(self, name='ADC', description='', gain_db=0.0, noise_figure_db=0.0,
                 total_bits=12.0, headroom_db=0.0, sample_rate=None):
        self.name = name
        self.description = description
        self.gain_db = gain_db
        self.noise_figure_db = noise_figure_db
        self.total_bits = total_bits
        self.headroom_db = headroom_db
        self.sample_rate = sample_rate
        self._input_stage = RFComponent(gain=gain_db, noise_figure=noise_figure_db)
        self._quantizer = QuantizationNoise(total_bits=total_bits, headroom_db=headroom_db)

    def propagate_signal(self, signal_power, noise_power):
        stage1 = self._input_stage.propagate_signal(signal_power, noise_power)
        stage2 = self._quantizer.propagate_signal(stage1['signal_power_out'], stage1['noise_power_out'])
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
    def __init__(self, name='DAC', description='', total_bits=12.0, headroom_db=0.0,
                 gain_db=0.0, noise_figure_db=0.0, sample_rate=None):
        self.name = name
        self.description = description
        self.total_bits = total_bits
        self.headroom_db = headroom_db
        self.gain_db = gain_db
        self.noise_figure_db = noise_figure_db
        self.sample_rate = sample_rate
        self._quantizer = QuantizationNoise(total_bits=total_bits, headroom_db=headroom_db)
        self._output_stage = RFComponent(gain=gain_db, noise_figure=noise_figure_db)

    def propagate_signal(self, signal_power, noise_power):
        stage1 = self._quantizer.propagate_signal(signal_power, noise_power)
        stage2 = self._output_stage.propagate_signal(stage1['signal_power_out'], stage1['noise_power_out'])
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

class SubBandTune:
    def __init__(self, name='Sub-band Tuner', description='', input_upper_freq=1e6,
                 input_lower_freq=0.0, signal_upper_freq=4e6, signal_lower_freq=2e6,
                 output_upper_freq=3e6, output_lower_freq=2e6):

        self.name = name
        self.description = description
        self.input_upper_freq = input_upper_freq
        self.input_lower_freq = input_lower_freq
        self.signal_upper_freq = signal_upper_freq
        self.signal_lower_freq = signal_lower_freq
        self.output_upper_freq = output_upper_freq
        self.output_lower_freq = output_lower_freq

    def propagate_signal(self, signal_power, noise_power):
        noise_reduction_ratio = (self.output_upper_freq - self.output_lower_freq) / (self.input_upper_freq - self.input_lower_freq)
        signal_bw = self.signal_upper_freq - self.signal_lower_freq
        new_signal_bw = min(self.output_upper_freq, self.signal_upper_freq) - max(self.output_lower_freq, self.signal_lower_freq)
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
    def __init__(self, name='Thermal noise floor', description='', temperature_k=290.0, bandwidth=1.0):
        self.name = name
        self.description = description
        self.temperature_k = temperature_k
        self.bandwidth = bandwidth

    def propagate_signal(self, signal_power, noise_power):
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
    def __init__(self, name='Implementation loss', description='', cable_loss_db=0.0,
                 pointing_loss_db=0.0, polarization_loss_db=0.0, other_loss_db=0.0):
        self.name = name
        self.description = description
        self.cable_loss_db = cable_loss_db
        self.pointing_loss_db = pointing_loss_db
        self.polarization_loss_db = polarization_loss_db
        self.other_loss_db = other_loss_db

    def propagate_signal(self, signal_power, noise_power):
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
    def __init__(self, name='Cable loss', description='', loss_db=0.0):
        super().__init__(name=name, description=description, cable_loss_db=loss_db)

class PointingLoss(ImplementationLoss):
    def __init__(self, name='Pointing loss', description='', loss_db=0.0):
        super().__init__(name=name, description=description, pointing_loss_db=loss_db)

class PolarizationLoss(ImplementationLoss):
    def __init__(self, name='Polarization loss', description='', loss_db=0.0):
        super().__init__(name=name, description=description, polarization_loss_db=loss_db)

class NoiseFigure:
    def __init__(self, name='Noise figure', description='', noise_figure=1.0):
        self.name = name
        self.description = description
        self.noise_figure = noise_figure

    def propagate_signal(self, signal_power, noise_power):
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

class RFComponent:
    def __init__(self, name='RF Component', description='', gain=1.0, noise_figure=1.0):
        self.name = name
        self.description = description
        self.gain = gain
        self.noise_figure = noise_figure

    def propagate_signal(self, signal_power, noise_power):
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

class RadarCrossSection:
    def __init__(self, name='RCS', description='', rcs_db=0.0):
        self.name = name
        self.description = description
        self.rcs_db = rcs_db
    
    def propagate_signal(self, signal_power, noise_power):
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
    def __init__(self, name='Radar path (two-way)', description='', distance=None,
                 tx_distance=None, rx_distance=None, frequency=1e9, rcs_db=0.0):
        self.name = name
        self.description = description
        if distance is not None:
            tx_distance = distance
            rx_distance = distance
        self.tx_distance = tx_distance
        self.rx_distance = rx_distance
        self.frequency = frequency
        self.rcs_db = rcs_db

    def propagate_signal(self, signal_power, noise_power):
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

        RadarPathLossOneWay(distance=R1) -> RadarCrossSection(rcs_db) -> RadarPathLossOneWay(distance=R2)

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
    def __init__(self, name='Radar path (one-way)', description='', distance=1.0, frequency=1e9):
        self.name = name
        self.description = description
        self.distance = distance
        self.frequency = frequency

    def propagate_signal(self, signal_power, noise_power):
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

class ArrayFactor:
    def __init__(self, name='Array Factor', description='', num_elements=1):
        self.name = name
        self.description = description
        self.num_elements = num_elements

    def propagate_signal(self, signal_power, noise_power):
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
    def __init__(self, name='Mixer', description='', lo_frequency=0.0, rf_frequency=None,
                 conversion_loss_db=0.0, noise_figure_db=None, mode='downconvert',
                 image_reject_db=None):
        self.name = name
        self.description = description
        self.lo_frequency = lo_frequency
        self.rf_frequency = rf_frequency
        self.conversion_loss_db = conversion_loss_db
        # passive mixers have a noise figure approximately equal to conversion loss
        self.noise_figure_db = conversion_loss_db if noise_figure_db is None else noise_figure_db
        self.mode = mode
        self.image_reject_db = image_reject_db

    def propagate_signal(self, signal_power, noise_power):
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

class Integrate:
    """
    Coherent integration (e.g. pulse integration): builds up SNR by summing
    `timespan` samples/pulses coherently. Signal power scales by `timespan`
    (the coherent processing gain); noise power is unaffected.
    """
    def __init__(self, name='Integration', description='', timespan=1.0):
        self.name = name
        self.description = description
        self.timespan = timespan

    def propagate_signal(self, signal_power, noise_power):
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power * self.timespan,
                     'noise_power_out': noise_power,
                     'integration_time': self.timespan}
        return data_dict

