"""
link_container.py
"""

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

class Component:
    """
    Abstract Component
    """
    def __init__(self, name, description):
        self.name = name
        self.description = description

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
    def __init__(self, name='Quantization noise', description='',  total_bits=12, utilized_bits=10):
        self.name = name
        self.description = description
        self.total_bits = total_bits
        self.utilized_bits = utilized_bits
        self.dynamic_range = 10.0
    
    def propagate_signal(self, signal_power, noise_power):
        total_power = np.sqrt(signal_power**2 + noise_power**2)
        num_levels = self.total_bits ** 2
        quant_noise = (total_power / num_levels) / np.sqrt(12.0)
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': signal_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': signal_power,
                     'noise_power_out': np.sqrt(noise_power**2 + quant_noise**2)}
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



class Integrate:
    pass


