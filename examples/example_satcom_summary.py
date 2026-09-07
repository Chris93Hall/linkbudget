"""
example_satcom_summary.py

A Ku-band satellite downlink that exercises the figures-of-merit and
link-margin features: the container is given a carrier frequency, a noise
bandwidth and a data rate, an antenna is tagged role="rx" so G/T can be
found, propagation losses are stacked up, and a LinkMargin stage states the
demodulator requirement.  ``budget.summary()`` then reports EIRP, path loss,
G/T, C/N0, Eb/N0 and whether the link closes.  Publishes to stdout, PDF, HTML
and a waterfall-plot PNG in ``examples/example_outputs/``.
"""

import os

import linkbudget as lb

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "example_outputs")
TITLE = "Ku-band Satellite Downlink"

CARRIER = 11.7e9        # Ku-band downlink, Hz
SYMBOL_RATE = 27.5e6    # baud
DATA_RATE = 2 * SYMBOL_RATE * 0.8   # QPSK, rate-4/5 FEC
NOISE_BW = 30e6         # receiver noise bandwidth, Hz
ELEVATION = 25.0        # ground-station look angle, degrees

budget = lb.LinkContainer(
    carrier_frequency=CARRIER,
    noise_bandwidth=NOISE_BW,
    data_rate=DATA_RATE,
    symbol_rate=SYMBOL_RATE,
)

# --- Satellite transmit ---
budget.add_component(lb.SignalSource(
    "Transponder HPA", "Saturated output power at the feed", signal_power=120.0))
budget.add_component(lb.Gain(
    "Satellite antenna", "Shaped downlink beam, on-boresight", gain=33.0, role="tx"))

# --- Downlink path ---
budget.add_component(lb.FreeSpacePathLoss(
    "Free-space path loss", "GEO slant range at 25 deg elevation",
    distance=39_500e3, frequency=CARRIER))
budget.add_component(lb.AtmosphericAbsorption(
    "Gaseous absorption", "Clear-air oxygen + water vapour",
    frequency=CARRIER, elevation_deg=ELEVATION))
budget.add_component(lb.RainAttenuation(
    "Rain fade", "Exceeded 0.01% of an average year",
    frequency=CARRIER, rain_rate=32.0, elevation_deg=ELEVATION,
    rain_height_km=3.2, station_height_km=0.1, latitude_deg=41.0))
budget.add_component(lb.TroposphericScintillation(
    "Scintillation", "0.01% tropospheric scintillation fade",
    frequency=CARRIER, elevation_deg=ELEVATION, antenna_diameter=1.2))

# --- Ground station receive ---
budget.add_component(lb.ParabolicDish(
    "Ground station dish", "1.2 m offset reflector",
    diameter=1.2, frequency=CARRIER, efficiency=0.65, role="rx"))
budget.add_component(lb.PolarizationMismatchLoss(
    "Polarization mismatch", "Circular feed against a slightly elliptical signal",
    axial_ratio_db_tx=0.8, axial_ratio_db_rx=1.0, tilt_angle_deg=15.0))
budget.add_component(lb.ThermalNoise(
    "System noise floor", "Antenna + LNA noise referenced to the feed",
    temperature_k=120.0, bandwidth=NOISE_BW))
budget.add_component(lb.RFComponent(
    "LNB", "Low-noise block downconverter", gain=55.0, noise_figure=0.7))

# --- Demodulator requirement ---
budget.add_component(lb.LinkMargin(
    "Link margin", "QPSK rate-4/5, required Eb/N0 with 1 dB implementation loss",
    required_ebno_db=3.6, noise_bandwidth=NOISE_BW, data_rate=DATA_RATE,
    implementation_loss_db=1.0, coding_gain_db=0.0))

os.makedirs(OUTPUT_DIR, exist_ok=True)
stem = os.path.join(OUTPUT_DIR, "example_satcom_downlink")
budget.install_publisher(lb.StdOutPublisher())
budget.add_publisher(lb.PDFPublisher(stem + ".pdf", title=TITLE))
budget.add_publisher(lb.HTMLPublisher(stem + ".html", title=TITLE))
budget.add_publisher(lb.MarkdownPublisher(stem + ".md", title=TITLE))
budget.add_publisher(lb.WaterfallPublisher(stem + ".png", title=TITLE + " — cascade"))
budget.publish()
print(f"\nwrote {stem}.pdf, {stem}.html, {stem}.md and {stem}.png\n")
print(budget.summary())
