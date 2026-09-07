"""
summary.py

Structured link-budget results plus the standard figures of merit, produced
by ``LinkContainer.summary()``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Sequence

from . import convert, fom
from ._types import StageList

if TYPE_CHECKING:
    from .link_container import Component


@dataclass
class BudgetSummary:
    """The computed result of a link budget.

    The power / SNR fields are always populated.  The figure-of-merit fields
    are populated only when the container was given enough information
    (``noise_bandwidth``, ``data_rate`` / ``symbol_rate``), when a
    propagation stage is present (``eirp_dbw``, ``total_propagation_loss_db``),
    when a ``role="rx"`` antenna is present (``g_over_t_db``) or when a
    ``LinkMargin`` stage is present (``margin_db`` / ``closes``).
    """

    stages: StageList = field(default_factory=list)

    signal_power_w: float = 0.0
    signal_power_dbw: float = float("-inf")
    noise_power_w: float = 0.0
    noise_power_dbw: float = float("-inf")
    snr: float = float("inf")
    snr_db: float = float("inf")

    noise_bandwidth_hz: float | None = None
    data_rate_bps: float | None = None
    symbol_rate_bd: float | None = None
    carrier_frequency_hz: float | None = None

    cn_db: float | None = None
    cn0_dbhz: float | None = None
    ebno_db: float | None = None
    esno_db: float | None = None

    eirp_dbw: float | None = None
    total_propagation_loss_db: float | None = None
    system_noise_temp_k: float | None = None
    g_over_t_db: float | None = None

    shannon_capacity_bps: float | None = None
    spectral_efficiency_bps_per_hz: float | None = None

    margin_db: float | None = None
    closes: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        """The summary as a plain dict (stages included)."""
        return asdict(self)

    def __str__(self) -> str:
        rows = [
            ("Signal power", _fmt(self.signal_power_dbw, "dBW")),
            ("Noise power", _fmt(self.noise_power_dbw, "dBW")),
            ("SNR", _fmt(self.snr_db, "dB")),
            ("C/N0", _fmt(self.cn0_dbhz, "dB-Hz")),
            ("Eb/N0", _fmt(self.ebno_db, "dB")),
            ("Es/N0", _fmt(self.esno_db, "dB")),
            ("EIRP", _fmt(self.eirp_dbw, "dBW")),
            ("Path loss (propagation)", _fmt(self.total_propagation_loss_db, "dB")),
            ("System noise temp", _fmt(self.system_noise_temp_k, "K")),
            ("G/T", _fmt(self.g_over_t_db, "dB/K")),
            ("Shannon capacity", _fmt(self.shannon_capacity_bps, "bit/s")),
            ("Spectral efficiency", _fmt(self.spectral_efficiency_bps_per_hz, "bit/s/Hz")),
            ("Link margin", _fmt(self.margin_db, "dB")),
        ]
        width = max(len(label) for label, _ in rows)
        lines = ["Link budget summary", "-" * (width + 16)]
        lines += [f"{label:<{width}}  {value}" for label, value in rows if value is not None]
        if self.closes is not None:
            lines.append("-" * (width + 16))
            lines.append(f"{'Link closes':<{width}}  {'YES' if self.closes else 'NO'}")
        return "\n".join(lines)


def _fmt(value: float | None, units: str) -> str | None:
    if value is None:
        return None
    return f"{value:.3g} {units}"


def _propagation_metrics(summary: BudgetSummary, data_list: StageList,
                         components: Sequence[Component]) -> None:
    prop_idxs = [i for i, comp in enumerate(components)
                 if getattr(comp, "is_propagation", False)]
    if not prop_idxs:
        return
    eirp_w = data_list[prop_idxs[0]]["signal_power_in"]
    if eirp_w > 0.0:
        summary.eirp_dbw = convert.linear_to_db(eirp_w)
    total_gain = 1.0
    for i in prop_idxs:
        stage = data_list[i]
        if stage["signal_power_in"] > 0.0:
            total_gain *= stage["signal_power_out"] / stage["signal_power_in"]
    summary.total_propagation_loss_db = -convert.linear_to_db(total_gain)


def _noise_metrics(summary: BudgetSummary, data_list: StageList,
                   components: Sequence[Component],
                   noise_bandwidth: float | None) -> None:
    if not noise_bandwidth:
        return
    floor_idx = next((i for i, stage in enumerate(data_list)
                      if stage["noise_power_in"] == 0.0 and stage["noise_power_out"] > 0.0),
                     None)
    if floor_idx is None:
        return
    gain_after = 1.0
    for stage in data_list[floor_idx + 1:]:
        # noise is non-zero at every stage past the floor, so this is always
        # a real ratio; the guard is only belt-and-braces against div-by-zero
        if stage["noise_power_in"] > 0.0:  # pragma: no branch
            gain_after *= stage["noise_power_out"] / stage["noise_power_in"]
    final_noise = data_list[-1]["noise_power_out"]
    t_sys = final_noise / (convert.BOLTZMANN_CONSTANT * noise_bandwidth * gain_after)
    summary.system_noise_temp_k = t_sys

    rx_idx = next((i for i, comp in enumerate(components)
                   if getattr(comp, "role", None) == "rx"), None)
    if rx_idx is not None:
        stage = data_list[rx_idx]
        if stage["signal_power_in"] > 0.0:
            rx_gain_db = convert.linear_to_db(
                stage["signal_power_out"] / stage["signal_power_in"])
            summary.g_over_t_db = fom.g_over_t_db(rx_gain_db, t_sys)


def summarize(data_list: StageList, components: Sequence[Component] | None = None,
              noise_bandwidth: float | None = None, data_rate: float | None = None,
              symbol_rate: float | None = None,
              carrier_frequency: float | None = None) -> BudgetSummary:
    """Build a `BudgetSummary` from a computed ``data_list`` and the
    component list that produced it."""
    components = list(components or [])
    summary = BudgetSummary(stages=list(data_list),
                            noise_bandwidth_hz=noise_bandwidth,
                            data_rate_bps=data_rate,
                            symbol_rate_bd=symbol_rate,
                            carrier_frequency_hz=carrier_frequency)
    if not data_list:
        return summary

    last = data_list[-1]
    summary.signal_power_w = last["signal_power_out"]
    summary.signal_power_dbw = convert.linear_to_db(last["signal_power_out"])
    summary.noise_power_w = last["noise_power_out"]
    summary.noise_power_dbw = convert.linear_to_db(last["noise_power_out"])
    summary.snr = last["snr"]
    summary.snr_db = convert.linear_to_db(last["snr"])

    if noise_bandwidth:
        summary.cn_db = summary.snr_db
        summary.cn0_dbhz = fom.cn0_from_snr(summary.snr_db, noise_bandwidth)
        if summary.snr not in (float("inf"), float("-inf")):
            summary.shannon_capacity_bps = fom.shannon_capacity_bps(
                noise_bandwidth, summary.snr)
        if data_rate:
            summary.ebno_db = fom.ebno_db(summary.cn0_dbhz, data_rate)
            summary.spectral_efficiency_bps_per_hz = fom.spectral_efficiency(
                data_rate, noise_bandwidth)
        if symbol_rate:
            summary.esno_db = fom.esno_db(summary.cn0_dbhz, symbol_rate)

    _propagation_metrics(summary, data_list, components)
    _noise_metrics(summary, data_list, components, noise_bandwidth)

    margin_stage = next((stage for stage in data_list if "margin_db" in stage), None)
    if margin_stage is not None:
        summary.margin_db = margin_stage["margin_db"]
        summary.closes = margin_stage["closes"]

    return summary
