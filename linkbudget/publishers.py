"""
publishers.py
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any

from . import convert
from ._types import StageList

# fields whose values are absolute power quantities in the container's
# power_units, as opposed to ratios, dB values, frequencies, etc.
POWER_FIELDS = {'signal_power_in', 'signal_power_out', 'noise_power_in', 'noise_power_out',
                 'quantization_noise', 'thermal_noise_power', 'image_noise_power'}

def label_with_units(key: str, power_units: str) -> str:
    pretty_key = key.replace('_', ' ')
    if key in POWER_FIELDS:
        return f'{pretty_key} ({power_units})'
    return pretty_key

def pad_string(string: Any, length: int, side: str = 'left') -> str:
    string = str(string)
    str_len = len(string)
    if str_len >= length:
        return string

    rem_length = length - str_len
    if side != 'left':
        return string + (' ' * rem_length)
    return (' ' * rem_length) + string

def trunc_float(flt: float) -> float:
    return float(f'{flt:4f}')

def format_number(val: Any, sig_figs: int = 6) -> str:
    """
    Format a number to at most `sig_figs` significant figures, choosing
    between fixed-point and scientific notation based on its magnitude
    (like printf's %g) rather than the length of its default string
    representation -- this avoids both spuriously switching to scientific
    notation for floating-point noise (e.g. 2.9999999999999996 instead of
    3) and needlessly spelling out very large/small magnitudes in full.
    """
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return str(val)
    if math.isnan(val) or math.isinf(val):
        return str(val)
    if val == 0:
        return '0.0'
    return f'{float(val):.{sig_figs}g}'

def float_to_bounded_str(val: float, str_length: int = 12, sig_figs: int = 6) -> str:
    val_str = format_number(val, sig_figs)
    if len(val_str) <= str_length:
        return val_str

    # still too long (e.g. a very large exponent) -- shrink precision to fit
    for figs in range(sig_figs - 1, 0, -1):
        val_str = format_number(val, figs)
        if len(val_str) <= str_length:
            return val_str
    return val_str

class Publisher(ABC):
    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractmethod
    def publish(self, data_list: StageList, power_units: str = 'W') -> None:
        pass

class StdOutPublisher(Publisher):
    def __init__(self) -> None:
        pass

    def publish_summary(self, data_list: StageList, power_units: str = 'W') -> None:
        print('-'*120)
        print('|      LINK BUDGET SUMMARY')
        print('-'*120)
        print(f'|    Name                | Signal Power Out ({power_units}) | '
              f'Noise Power Out ({power_units}) | Signal Gain (dB) | '
              f'Noise Gain (dB) | SNR (dB)      |')
        print('-'*120)
        for index, data, in enumerate(data_list):
            name = pad_string(data['name'], 20, side='right')
            #sig_power = pad_string(trunc_float(data['signal_power_in']), 30)
            #noise_power = pad_string(data['noise_power_in'], 15)
            sig_power_out = pad_string(float_to_bounded_str(data['signal_power_out']), 20)
            noise_power_out = pad_string(float_to_bounded_str(data['noise_power_out']), 15)
            noise_gain = pad_string(
                float_to_bounded_str(convert.linear_to_db(data['noise_gain'])), 15)
            signal_gain = pad_string(
                float_to_bounded_str(convert.linear_to_db(data['signal_gain'])), 16)
            snr = pad_string(float_to_bounded_str(convert.linear_to_db(data['snr'])), 13)
            description = data['description']
            print(f' {index + 1}. {name} | {sig_power_out} | {noise_power_out} | '
                  f'{signal_gain} | {noise_gain} | {snr}')
            print(f'        {description}')

    def publish_detailed(self, data_list: StageList, power_units: str = 'W') -> None:
        print('-'*120)
        print('|      DETAILED LINK BUDGET REPORT')
        print('-'*120)
        for index, data, in enumerate(data_list):
            print('-'*120)
            print(f' {index + 1}. {data["name"]}')
            for key in data:
                pretty_key = label_with_units(key, power_units)
                print(f'      {pretty_key}: {format_number(data[key])}')

    def publish(self, data_list: StageList, power_units: str = 'W') -> None:
        self.publish_summary(data_list, power_units)
        print()
        self.publish_detailed(data_list, power_units)
