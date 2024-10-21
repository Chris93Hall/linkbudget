"""
publishers.py
"""

class StdOutPublisher:
    def __init__(self):
        pass

    def publish_summary(self, data_list):
        print('-'*20)
        print('      LINK BUDGET SUMMARY')
        print('-'*20)
        print('| Name | Signal Power Out | Noise Power Out | Signal Gain | Noise Gain | SNR |')
        for index, data, in enumerate(data_list):
            sig_power = data['signal_power_in']
            noise_power = data['noise_power_in']
            sig_power_out = data['signal_power_out']
            noise_power_out = data['noise_power_out']
            noise_gain = convert.linear_to_db(data['noise_gain'])
            signal_gain = convert.linear_to_db(data['signal_gain'])
            snr = convert.linear_to_db(data['snr'])
            description = data['description']
            print(f' {index}. {name} | {sig_power_out} | {noise_power_out} | {signal_gain} | {noise_gain} | {snr}')
            print(f'        {description}')

    def publish_detailed((self):
        pass

    def publish(self, data_list):
        self.publish_summary(data_list)
        self.publish_detailed(data_list)


