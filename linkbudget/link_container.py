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
        self.publisher.publish(self.data_list)

    def add_component(self, component):
        self.components_list.append(componen)

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
            snr = convert.linear_to_db(sig_power / noise_power)
            data_dict['snr'] = snr
            data_dict['noise_gain'] = data_dict['noise_power_out'] / data_dict['noise_power_in']
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
                     'signal_power_in': sig_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': sig_power,
                     'noise_power_out': noise_power}
        return data_dict

class FreeSpacePathLoss(Component):
    def __init__(self, name, description, distance, frequency):
        self.name = name
        self.description = description
        self.distance = distance
        self.frequency = frequency

    def propagate_signal(self, signal_power, noise_power):
        data_dict = {'name': self.name,
                     'description': self.description,
                     'signal_power_in': sig_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': sig_power,
                     'noise_power_out': noise_power}
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
                     'signal_power_in': sig_power,
                     'noise_power_in': noise_power,
                     'signal_power_out': sig_power * gain,
                     'noise_power_out': noise_power * gain}
        return data_dict

class QuantizationNoise:
    pass

class SubBandTune:
    pass

class Integrate:
    pass


