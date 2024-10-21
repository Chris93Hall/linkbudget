"""
example link budget
"""

from linkbudget.link_container import LinkContainer
from linkbudget.link_container import SignalSource, FreeSpacePathLoss, Gain
from linkbudget.publishers import StdOutPublisher

budget = LinkContainer()
budget.install_publisher(StdOutPublisher())

budget.add_component(SignalSource('Signal source',
                                  'Signal starting at transmit side',
                                  signal_power = 1.0,
                                  noise_power = 0.0))

budget.add_component(FreeSpacePathLoss('Path loss',
                                       'Path from transmitter to receiver',
                                       distance = 1000,
                                       frequency = 5e9))

budget.add_component(Gain('Rx antenna gain',
                          'Gain of the receive antenna',
                          gain=3.0,
                          db = True))

budget.add_component(SignalSource('Noise source',
                                  'Noise at receive antenna',
                                  signal_power = 0.0,
                                  noise_power = 1.0))

budget.compute()
budget.publish()                                        
