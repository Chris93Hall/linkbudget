"""
margin.py

Link-margin / closure analysis.
"""

from __future__ import annotations

from . import convert, fom
from ._types import StageData
from .link_container import Component


class LinkMargin(Component):
    """Terminal analysis stage: compares the achieved link quality against a
    required threshold and reports the margin.

    Signal and noise pass through unchanged; the stage is annotated with
    ``achieved_snr_db``, ``achieved_ebno_db`` / ``achieved_esno_db``,
    ``required_db``, ``margin_db`` and ``closes``.

    Provide the requirement as exactly one of ``required_ebno_db``,
    ``required_esno_db``, ``required_cn_db`` or ``required_snr_db``.  When the
    requirement is Eb/N0 or Es/N0, ``noise_bandwidth`` and ``data_rate``
    (or ``symbol_rate``) are needed to convert the achieved C/N.

    ``coding_gain_db`` is added to the achieved metric and
    ``implementation_loss_db`` is subtracted from it before the margin is
    taken.
    """

    is_margin = True

    def __init__(self, name: str = "Link margin", description: str = "",
                 required_ebno_db: float | None = None,
                 required_esno_db: float | None = None,
                 required_cn_db: float | None = None,
                 required_snr_db: float | None = None,
                 noise_bandwidth: float | None = None, data_rate: float | None = None,
                 symbol_rate: float | None = None, implementation_loss_db: float = 0.0,
                 coding_gain_db: float = 0.0) -> None:
        requirements = {
            "required_ebno_db": required_ebno_db,
            "required_esno_db": required_esno_db,
            "required_cn_db": required_cn_db,
            "required_snr_db": required_snr_db,
        }
        given = [key for key, value in requirements.items() if value is not None]
        if len(given) != 1:
            raise ValueError(
                "give exactly one of " + ", ".join(requirements) + f" (got {given})")

        self.name = name
        self.description = description
        self.required_ebno_db = required_ebno_db
        self.required_esno_db = required_esno_db
        self.required_cn_db = required_cn_db
        self.required_snr_db = required_snr_db
        self.noise_bandwidth = noise_bandwidth
        self.data_rate = data_rate
        self.symbol_rate = symbol_rate
        self.implementation_loss_db = implementation_loss_db
        self.coding_gain_db = coding_gain_db

    def _achieved_and_required(
            self, achieved_snr_db: float,
            cn0: float | None) -> tuple[str, float | None, float]:
        """Return (metric_name, achieved_db, required_db).

        Exactly one ``required_*`` is set (enforced in ``__init__``), so
        ``required_db`` is always a real number.
        """
        if self.required_ebno_db is not None:
            achieved = fom.ebno_db(cn0, self.data_rate) if (
                cn0 is not None and self.data_rate) else None
            return "Eb/N0", achieved, self.required_ebno_db
        if self.required_esno_db is not None:
            achieved = fom.esno_db(cn0, self.symbol_rate) if (
                cn0 is not None and self.symbol_rate) else None
            return "Es/N0", achieved, self.required_esno_db
        if self.required_cn_db is not None:
            achieved = fom.cn_db(cn0, self.noise_bandwidth) if (
                cn0 is not None and self.noise_bandwidth) else achieved_snr_db
            return "C/N", achieved, self.required_cn_db
        assert self.required_snr_db is not None  # the one requirement that was set
        return "SNR", achieved_snr_db, self.required_snr_db

    def propagate_signal(self, signal_power: float, noise_power: float) -> StageData:
        """Pass the power through unchanged; annotate the stage with the
        achieved metric, the requirement and the resulting margin."""
        if noise_power > 0.0:
            achieved_snr = signal_power / noise_power
        else:
            achieved_snr = float("inf")
        achieved_snr_db = convert.linear_to_db(achieved_snr)

        cn0 = None
        if self.noise_bandwidth:
            cn0 = fom.cn0_from_snr(achieved_snr_db, self.noise_bandwidth)
        achieved_ebno_db = fom.ebno_db(cn0, self.data_rate) if (
            cn0 is not None and self.data_rate) else None
        achieved_esno_db = fom.esno_db(cn0, self.symbol_rate) if (
            cn0 is not None and self.symbol_rate) else None

        metric, achieved_db, required_db = self._achieved_and_required(
            achieved_snr_db, cn0)

        margin_db = None
        if achieved_db is not None:
            margin_db = (achieved_db - required_db
                         + self.coding_gain_db - self.implementation_loss_db)

        return {"name": self.name,
                "description": self.description,
                "signal_power_in": signal_power,
                "noise_power_in": noise_power,
                "signal_power_out": signal_power,
                "noise_power_out": noise_power,
                "metric": metric,
                "achieved_snr_db": achieved_snr_db,
                "achieved_ebno_db": achieved_ebno_db,
                "achieved_esno_db": achieved_esno_db,
                "achieved_db": achieved_db,
                "required_db": required_db,
                "coding_gain_db": self.coding_gain_db,
                "implementation_loss_db": self.implementation_loss_db,
                "margin_db": margin_db,
                "closes": bool(margin_db is not None and margin_db >= 0.0)}
