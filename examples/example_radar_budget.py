"""
example_radar_budget.py

A more complete example:
Radar link budget, from transmitter output through the receive chain to a
coherently-integrated detection SNR. Exercises most components in the
linkbudget package and publishes to stdout, PDF, HTML and a waterfall-plot
PNG at once; the files land in ``examples/example_outputs/``.
"""

import os

import linkbudget

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "example_outputs")
TITLE = "Radar Link Budget"

RADAR_FREQUENCY = 9.5e9   # X-band, Hz
TARGET_RANGE = 50e3       # 50 km slant range, meters
IF_BANDWIDTH = 2e6        # receiver IF bandwidth, Hz

budget = linkbudget.LinkContainer(
    carrier_frequency=RADAR_FREQUENCY, noise_bandwidth=IF_BANDWIDTH)

# --- Transmit chain ---

budget.add_component(linkbudget.SignalSource(
    'Radar transmitter',
    'Peak output power from the final HPA stage',
    signal_power=1000.0,   # 1 kW peak
    noise_power=0.0))

budget.add_component(linkbudget.CableLoss(
    'Tx waveguide loss',
    'Loss between the HPA output and the antenna feed',
    loss_db=0.6))

budget.add_component(linkbudget.ArrayFactor(
    'Tx phased array antenna',
    'Transmit gain from a 256-element phased array',
    num_elements=256))

budget.add_component(linkbudget.PointingLoss(
    'Tx beam pointing loss',
    'Residual beam-steering error loss',
    loss_db=0.3))

# --- Propagation and target ---

budget.add_component(linkbudget.RadarPathLoss(
    'Radar path loss (two-way)',
    'Transmitter to target and back, reflecting off a ~5 sq. meter target',
    distance=TARGET_RANGE,
    frequency=RADAR_FREQUENCY,
    rcs_db=7.0))

# --- Receive front end ---

budget.add_component(linkbudget.PolarizationLoss(
    'Polarization mismatch loss',
    'Loss from target-induced polarization mismatch',
    loss_db=0.2))

budget.add_component(linkbudget.Gain(
    'Rx antenna gain',
    'Receive antenna gain',
    gain=34.0,
    db=True,
    role='rx'))

budget.add_component(linkbudget.CableLoss(
    'Rx cable loss',
    'Loss from the antenna feed to the LNA input',
    loss_db=0.5))

budget.add_component(linkbudget.ThermalNoise(
    'Receiver thermal noise floor',
    'System noise referenced to the LNA input',
    temperature_k=290.0,
    bandwidth=IF_BANDWIDTH))

budget.add_component(linkbudget.RFComponent(
    'LNA',
    'Low-noise amplifier',
    gain=30.0,
    noise_figure=1.2))

# --- Downconversion and digitization ---

budget.add_component(linkbudget.Mixer(
    'Downconverter',
    'Downconvert RF to IF against a fixed LO',
    lo_frequency=8.7e9,
    rf_frequency=RADAR_FREQUENCY,
    conversion_loss_db=6.0,
    noise_figure_db=6.0,
    image_reject_db=30.0,
    mode='downconvert'))

budget.add_component(linkbudget.AnalogToDigitalConverter(
    'ADC',
    'Near-unity-gain IF buffer feeding a 14-bit digitizer sampling the IF',
    gain_db=0.0,
    noise_figure_db=2.0,
    total_bits=14.0,
    headroom_db=12.0,
    sample_rate=50e6))

budget.add_component(linkbudget.SubBandTune(
    'Digital channelizer',
    'Selects the Doppler processing sub-band from the digitized IF',
    input_lower_freq=0.0,
    input_upper_freq=50e6,
    output_lower_freq=20e6,
    output_upper_freq=22e6,
    signal_lower_freq=20.2e6,
    signal_upper_freq=21.8e6))

# --- Pulse processing ---

budget.add_component(linkbudget.Integrate(
    'Coherent pulse integration',
    'Coherent integration over a 64-pulse CPI',
    timespan=64.0))

os.makedirs(OUTPUT_DIR, exist_ok=True)
stem = os.path.join(OUTPUT_DIR, 'example_radar_link_budget')
# a new container already publishes to stdout; add the file publishers alongside it
budget.add_publisher(linkbudget.PDFPublisher(stem + '.pdf', title=TITLE))
budget.add_publisher(linkbudget.HTMLPublisher(stem + '.html', title=TITLE))
budget.add_publisher(linkbudget.MarkdownPublisher(stem + '.md', title=TITLE))
budget.add_publisher(linkbudget.WaterfallPublisher(stem + '.png', title=TITLE + ' — cascade'))
budget.publish()
print(f'\nwrote {stem}.pdf, {stem}.html, {stem}.md and {stem}.png\n')
print(budget.summary())
