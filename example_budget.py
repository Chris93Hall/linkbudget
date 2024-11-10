"""
example link budget
"""

#from linkbudget.link_container import LinkContainer
#from linkbudget.link_container import SignalSource, FreeSpacePathLoss, Gain, SubBandTune, QuantizationNoise
#from linkbudget.publishers import StdOutPublisher

import linkbudget

budget = linkbudget.LinkContainer()
budget.install_publisher(linkbudget.StdOutPublisher())
#budget.install_publisher(linkbudget.PDFPublisher('example_link_budget.pdf'))

budget.add_component(linkbudget.SignalSource(
    'Signal source',
    'Signal starting at transmit side',
    signal_power = 1.0,
    noise_power = 0.0))

budget.add_component(linkbudget.FreeSpacePathLoss(
    'Path loss',
    'Path from transmitter to receiver',
    distance = 1000,
    frequency = 5e9))

budget.add_component(linkbudget.Gain(
    'Rx antenna gain',
    'Gain of the receive antenna',
    gain = 3.0,
    db = True))

budget.add_component(linkbudget.SignalSource(
    'Noise source',
    'Noise at receive antenna',
    signal_power = 0.0,
    noise_power = 1.0))

budget.add_component(linkbudget.QuantizationNoise(
    total_bits = 12.0,
    headroom_db = 10.0))

budget.add_component(linkbudget.SubBandTune(
    input_lower_freq=10e6,
    input_upper_freq=20e6,
    output_lower_freq=15.5e6,
    output_upper_freq=16.5e6,
    signal_lower_freq=15e6,
    signal_upper_freq=17e6))

budget.publish()                                        
