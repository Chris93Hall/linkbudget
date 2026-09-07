"""
example_budget.py

A minimal communications link budget: a transmitter, free-space path loss, a
receive antenna, a second noise source and some digitisation stages.

Publishes to stdout, PDF, HTML and a waterfall-plot PNG at once (a demo of
``LinkContainer.add_publisher``); the files land in ``examples/example_outputs/``.
"""

import os

import linkbudget

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "example_outputs")
TITLE = "Link Budget Report"

budget = linkbudget.LinkContainer()

budget.add_component(linkbudget.SignalSource(
    'Signal source',
    'Signal starting at transmit side',
    signal_power=1.0,
    noise_power=0.0))

budget.add_component(linkbudget.FreeSpacePathLoss(
    'Path loss',
    'Path from transmitter to receiver',
    distance=1000,
    frequency=5e9))

budget.add_component(linkbudget.Gain(
    'Rx antenna gain',
    'Gain of the receive antenna',
    gain=3.0,
    db=True,
    role='rx'))

budget.add_component(linkbudget.SignalSource(
    'Noise source',
    'Noise at receive antenna',
    signal_power=0.0,
    noise_power=1.0))

budget.add_component(linkbudget.QuantizationNoise(
    total_bits=12.0,
    headroom_db=10.0))

budget.add_component(linkbudget.SubBandTune(
    input_lower_freq=10e6,
    input_upper_freq=20e6,
    output_lower_freq=15.5e6,
    output_upper_freq=16.5e6,
    signal_lower_freq=15e6,
    signal_upper_freq=17e6))

os.makedirs(OUTPUT_DIR, exist_ok=True)
stem = os.path.join(OUTPUT_DIR, 'example_link_budget')
# a new container already publishes to stdout; add the file publishers alongside it
budget.add_publisher(linkbudget.PDFPublisher(stem + '.pdf', title=TITLE))
budget.add_publisher(linkbudget.HTMLPublisher(stem + '.html', title=TITLE))
budget.add_publisher(linkbudget.MarkdownPublisher(stem + '.md', title=TITLE))
budget.add_publisher(linkbudget.WaterfallPublisher(stem + '.png', title=TITLE + ' — cascade'))
budget.publish()
print(f'\nwrote {stem}.pdf, {stem}.html, {stem}.md and {stem}.png')
