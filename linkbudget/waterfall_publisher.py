"""
waterfall_publisher.py

A :class:`~linkbudget.publishers.Publisher` that renders the signal- and
noise-power cascade ("waterfall") through the budget stages to an image
file.  The output format is taken from the file extension (``.png``,
``.svg``, ``.pdf`` ...).

``matplotlib`` is imported lazily inside :meth:`WaterfallPublisher.publish`,
so it is only required when this publisher is actually used.  Install it with
``pip install linkbudget[plot]``.
"""

from __future__ import annotations

import math
from typing import Any

from . import convert
from ._types import StageList
from .publishers import Publisher

SIGNAL_COLOR = "#2b6cb0"
NOISE_COLOR = "#c53030"
FILL_COLOR = "#2b6cb0"


def _finite_db(value: float) -> float:
    """dB value as a float, or NaN when the linear input was zero / infinite."""
    result = convert.linear_to_db(value)
    return float(result) if math.isfinite(result) else float("nan")


class WaterfallPublisher(Publisher):
    """Render the per-stage signal / noise power cascade to an image.

    The shaded band between the signal and noise traces is the running SNR;
    stages carrying zero signal or noise power (``-inf`` dBW) are drawn along
    the bottom of the axes.
    """

    def __init__(self, fpath: str, title: str = "Link Budget Cascade",
                 figsize: tuple[float, float] = (11, 6), dpi: int = 140) -> None:
        self.fpath = fpath
        self.title = title
        self.figsize = figsize
        self.dpi = dpi

    def publish(self, data_list: StageList, power_units: str = "W") -> None:
        # matplotlib is an optional dependency, only needed for this publisher
        import matplotlib  # pylint: disable=import-outside-toplevel
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # pylint: disable=import-outside-toplevel

        fig, ax = plt.subplots(figsize=self.figsize)
        try:
            if data_list:
                self._draw(ax, data_list)
            else:
                ax.text(0.5, 0.5, "empty link budget", ha="center", va="center",
                        transform=ax.transAxes, color="#888888")
                ax.set_axis_off()
            ax.set_title(self.title)
            fig.tight_layout()
            fig.savefig(self.fpath, dpi=self.dpi)
        finally:
            plt.close(fig)

    def _draw(self, ax: Any, data_list: StageList) -> None:
        positions = list(range(len(data_list)))
        names = [str(stage["name"]) for stage in data_list]
        signal_raw = [_finite_db(stage["signal_power_out"]) for stage in data_list]
        noise_raw = [_finite_db(stage["noise_power_out"]) for stage in data_list]

        finite = [value for value in signal_raw + noise_raw if not math.isnan(value)]
        floor = (min(finite) - 10.0) if finite else 0.0
        signal_dbw = [floor if math.isnan(value) else value for value in signal_raw]
        noise_dbw = [floor if math.isnan(value) else value for value in noise_raw]

        final_snr = _finite_db(data_list[-1].get("snr", float("nan")))
        snr_label = "SNR" if math.isnan(final_snr) else f"SNR (final {final_snr:.1f} dB)"

        ax.fill_between(positions, signal_dbw, noise_dbw, step="mid",
                        color=FILL_COLOR, alpha=0.10, label=snr_label)
        ax.step(positions, signal_dbw, where="mid", color=SIGNAL_COLOR, marker="o",
                markersize=4, linewidth=1.8, label="Signal power out")
        ax.step(positions, noise_dbw, where="mid", color=NOISE_COLOR, marker="o",
                markersize=4, linewidth=1.8, label="Noise power out")

        ax.set_xticks(positions)
        ax.set_xticklabels(names, rotation=40, ha="right", fontsize=8)
        ax.set_ylabel("Power (dBW)")
        ax.set_ylim(bottom=floor)
        ax.grid(True, axis="y", linestyle=":", alpha=0.5)
        ax.margins(x=0.02)
        ax.legend(loc="best", fontsize=8)
