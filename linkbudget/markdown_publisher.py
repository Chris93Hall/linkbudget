"""
markdown_publisher.py

`MarkdownPublisher` -- writes the link budget as a GitHub-flavoured
Markdown file, ready to drop into a README, a wiki or a PR description.
"""

from __future__ import annotations

from . import convert
from ._types import StageList
from .publishers import Publisher, float_to_bounded_str, format_number, label_with_units

_SUMMARY_HEADER = ("#", "Component", "Signal Power Out ({units})",
                   "Noise Power Out ({units})", "Signal Gain (dB)",
                   "Noise Gain (dB)", "SNR (dB)")


def _cell(value: object) -> str:
    """Escape a value for use inside a GitHub-flavoured Markdown table cell."""
    return (str(value)
            .replace("\\", "\\\\")
            .replace("|", "\\|")
            .replace("\n", " "))


class MarkdownPublisher(Publisher):
    """Write the link budget as a GitHub-flavoured Markdown file: a summary
    table followed by a per-component field breakdown (the same structure as
    `HTMLPublisher`)."""

    def __init__(self, fpath: str, title: str = "Link Budget Report") -> None:
        self.fpath = fpath
        self.title = title

    def _summary_table(self, data_list: StageList, power_units: str) -> list[str]:
        header = [text.format(units=power_units) for text in _SUMMARY_HEADER]
        lines = ["| " + " | ".join(header) + " |",
                 "|" + "|".join(["---"] * len(header)) + "|"]
        for index, data in enumerate(data_list):
            name = _cell(data["name"])
            if data["description"]:
                name += f"<br>{_cell(data['description'])}"
            lines.append("| " + " | ".join((
                str(index + 1),
                name,
                float_to_bounded_str(data["signal_power_out"]),
                float_to_bounded_str(data["noise_power_out"]),
                float_to_bounded_str(convert.linear_to_db(data["signal_gain"])),
                float_to_bounded_str(convert.linear_to_db(data["noise_gain"])),
                float_to_bounded_str(convert.linear_to_db(data["snr"])),
            )) + " |")
        return lines

    def _detail_sections(self, data_list: StageList, power_units: str) -> list[str]:
        lines: list[str] = []
        for index, data in enumerate(data_list):
            lines += ["", f"### {index + 1}. {_cell(data['name'])}", "",
                      "| Field | Value |", "|---|---|"]
            for key, value in data.items():
                lines.append(
                    f"| {_cell(label_with_units(key, power_units))} "
                    f"| {_cell(format_number(value))} |")
        return lines

    def publish(self, data_list: StageList, power_units: str = "W") -> None:
        """Render the report and write it to ``self.fpath`` as UTF-8."""
        lines = [f"# {self.title}", "", "## Summary", ""]
        lines += self._summary_table(data_list, power_units)
        lines += ["", "## Detailed Report"]
        lines += self._detail_sections(data_list, power_units)
        with open(self.fpath, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
