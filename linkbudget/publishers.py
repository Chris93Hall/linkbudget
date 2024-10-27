"""
publishers.py
"""

from . import convert

def pad_string(string, length, side='left'):
    string = str(string)
    str_len = len(string)
    if str_len >= length:
        return string

    rem_length = length - str_len
    if side != 'left':
        return string + (' ' * rem_length) 
    return (' ' * rem_length) + string

def trunc_float(flt):
    flt = f'{flt:4f}'
    return float(flt)

def float_to_bounded_str(val, str_length=12):
    val_str = str(val)
    if len(val_str) <= str_length:
        return val_str

    val_str = f'{val:e}' # force scientific notarion
    if len(val_str) <= str_length:
        return val_str

    frac, exp = val_str.split('e')
    exp_length = len(exp)
    frac_length = str_length - exp_length - 1
    if frac[0] == '-':
        frac_length -= 1

    # if frac_length is 0 or -1, we can just use the whole number
    if frac_length in [0, -1]:
        return frac.split('.')[0] + 'e' + exp

    frac = frac[:frac_length]
    return frac + 'e' + exp
    
class StdOutPublisher:
    def __init__(self):
        pass

    def publish_summary(self, data_list):
        print('-'*120)
        print('|      LINK BUDGET SUMMARY')
        print('-'*120)
        print('|    Name                | Signal Power Out     | Noise Power Out | Signal Gain (dB) | Noise Gain (dB) | SNR (dB)      |')
        print('-'*120)
        for index, data, in enumerate(data_list):
            name = pad_string(data['name'], 20, side='right')
            #sig_power = pad_string(trunc_float(data['signal_power_in']), 30)
            #noise_power = pad_string(data['noise_power_in'], 15)
            sig_power_out = pad_string(float_to_bounded_str(data['signal_power_out']), 20)
            noise_power_out = pad_string(float_to_bounded_str(data['noise_power_out']), 15)
            noise_gain = pad_string(float_to_bounded_str(convert.linear_to_db(data['noise_gain'])), 15)
            signal_gain = pad_string(float_to_bounded_str(convert.linear_to_db(data['signal_gain'])), 16)
            snr = pad_string(float_to_bounded_str(convert.linear_to_db(data['snr'])), 13)
            description = data['description']
            print(f' {index + 1}. {name} | {sig_power_out} | {noise_power_out} | {signal_gain} | {noise_gain} | {snr}')
            print(f'        {description}')

    def publish_detailed(self, data_list):
        print('-'*120)
        print('|      DETAILED LINK BUDGET REPORT')
        print('-'*120)
        for index, data, in enumerate(data_list):
            print('-'*120)
            print(f' {index + 1}. {data["name"]}')
            for key in data.keys():
                pretty_key = key.replace('_', ' ')
                print(f'      {pretty_key}: {data[key]}')

    def publish(self, data_list):
        self.publish_summary(data_list)
        print('')
        self.publish_detailed(data_list)


