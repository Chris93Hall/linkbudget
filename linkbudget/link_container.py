"""
link_container.py
"""

from abc import ABC, abstractmethod

import numpy as np

from . import convert
from . import publishers

class LinkContainer:
    def __init__(self):
        self.components_list = []
        self.data_list = []
        self.publisher = publishers.StdOutPublisher()

    def install_publisher(self, publisher):
        self.publisher = publisher

    def publish(self):
        self.compute()
        self.publisher.publish(self.data_list)

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
        added_noise_power = noise_power * (noise_factor + 1)
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power,
                     'noise_power_out': noise_power + added_noise_power,
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
        added_noise_power = noise_power * gain * (noise_factor + 1)
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power * gain_linear,
                     'noise_power_out': (noise_power * gain_linear) + added_noise_power,
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
                     'signal_power_out': signal_power * num_elements,
                     'noise_power_out': noise_power * num_elements,
                     'number_of_elements': num_elements,
                     'gain': f'{10.0*np.log10(num_elements)} dB'}
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
    def __init__(self, name='Integration', description='', timespan=1.0):
        self.name = name
        self.description = description
        self.timespan = timespan

    def propagate_signal(self, signal_power, noise_power):
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': (signal_power**2.0) * self.timespan,
                     'noise_power_out': noise_power,
                     'integration_time': self.timespan}
        return data_dict

