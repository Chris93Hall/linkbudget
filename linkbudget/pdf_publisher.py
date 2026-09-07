"""
pdf_publisher.py

`PDFPublisher` -- writes the link budget as a styled, paginated PDF
(via ``fpdf2``), visually matching `HTMLPublisher`.
"""

from __future__ import annotations

from fpdf import FPDF
from fpdf.fonts import FontFace

from . import convert
from ._types import StageList
from .publishers import Publisher, float_to_bounded_str, format_number, label_with_units

HEADER_FILL = (45, 55, 72)     # matches HTMLPublisher's thead background (#2d3748)
HEADER_TEXT = 255              # white
STRIPE_FILL = (242, 242, 242)  # matches HTMLPublisher's even-row background (#f2f2f2)
BORDER_COLOR = (221, 221, 221) # matches HTMLPublisher's border color (#ddd)


class PDFPublisher(Publisher):
    """Write the budget to ``fpath`` as a styled A4 PDF: a title banner, the
    summary table, then a per-component field breakdown, with automatic
    multi-page pagination.  Requires the ``fpdf2`` package.
    """

    def __init__(self, fpath: str, title: str = 'Link Budget Report') -> None:
        self.fpath = fpath
        self.title = title
        self.pdf = FPDF(orientation="P", unit="mm", format="A4")
        self.pdf.set_auto_page_break(auto=True, margin=15)
        self.pdf.add_page()
        self.pdf.set_draw_color(*BORDER_COLOR)

    def _title_page_header(self) -> None:
        self.pdf.set_font("helvetica", "B", 20)
        self.pdf.set_text_color(*HEADER_FILL)
        self.pdf.cell(0, 12, self.title, align="L", new_x="LMARGIN", new_y="NEXT")
        self.pdf.set_draw_color(*HEADER_FILL)
        self.pdf.set_line_width(0.6)
        line_y = self.pdf.get_y()
        self.pdf.line(self.pdf.l_margin, line_y, self.pdf.w - self.pdf.r_margin, line_y)
        self.pdf.set_draw_color(*BORDER_COLOR)
        self.pdf.set_line_width(0.2)
        self.pdf.ln(4)

    def _section_heading(self, text: str) -> None:
        self.pdf.set_font("helvetica", "B", 14)
        self.pdf.set_text_color(*HEADER_FILL)
        self.pdf.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.ln(1)

    def publish_summary(self, data_list: StageList, power_units: str = 'W') -> None:
        """Render the title banner and the one-row-per-stage summary table."""
        self._title_page_header()
        self._section_heading('Summary')

        headings_style = FontFace(emphasis="BOLD", color=HEADER_TEXT, fill_color=HEADER_FILL)
        self.pdf.set_font("helvetica", '', 9)
        with self.pdf.table(
                col_widths=(9, 47, 26, 26, 24, 24, 24),
                text_align=("CENTER", "LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"),
                headings_style=headings_style,
                cell_fill_color=STRIPE_FILL,
                cell_fill_mode="ROWS",
                borders_layout="ALL",
                line_height=5.5,
                padding=1.5) as table:
            row = table.row()
            for heading in ('#', 'Component', f'Signal Power Out ({power_units})',
                             f'Noise Power Out ({power_units})', 'Signal Gain (dB)',
                             'Noise Gain (dB)', 'SNR (dB)'):
                row.cell(heading)

            for index, data in enumerate(data_list):
                row = table.row()
                row.cell(str(index + 1))
                name_cell = data['name']
                if data['description']:
                    name_cell += f"\n{data['description']}"
                row.cell(name_cell)
                row.cell(float_to_bounded_str(data['signal_power_out']))
                row.cell(float_to_bounded_str(data['noise_power_out']))
                row.cell(float_to_bounded_str(convert.linear_to_db(data['signal_gain'])))
                row.cell(float_to_bounded_str(convert.linear_to_db(data['noise_gain'])))
                row.cell(float_to_bounded_str(convert.linear_to_db(data['snr'])))

        self.pdf.add_page()

    def publish_detailed(self, data_list: StageList, power_units: str = 'W') -> None:
        """Render every field of every stage as its own table."""
        self._section_heading('Detailed Report')

        for index, data in enumerate(data_list):
            # avoid starting a component's heading right at the bottom of a
            # page, which would immediately fragment its table
            min_block_height = 8 + 3 * 5.5 * 2
            if self.pdf.will_page_break(min_block_height):
                self.pdf.add_page()

            self.pdf.set_font("helvetica", "B", 11)
            self.pdf.set_text_color(*HEADER_FILL)
            self.pdf.cell(0, 8, f'{index + 1}. {data["name"]}', new_x="LMARGIN", new_y="NEXT")
            self.pdf.set_text_color(0, 0, 0)

            self.pdf.set_font("helvetica", '', 9)
            with self.pdf.table(
                    col_widths=(1, 2),
                    text_align=("LEFT", "LEFT"),
                    first_row_as_headings=False,
                    cell_fill_color=STRIPE_FILL,
                    cell_fill_mode="ROWS",
                    borders_layout="ALL",
                    line_height=5.5,
                    padding=1.5) as table:
                for key, value in data.items():
                    row = table.row()
                    row.cell(label_with_units(key, power_units))
                    row.cell(format_number(value))

            self.pdf.ln(6)

    def publish(self, data_list: StageList, power_units: str = 'W') -> None:
        """Build the whole document and write it to ``self.fpath``."""
        self.publish_summary(data_list, power_units)
        self.publish_detailed(data_list, power_units)
        self.pdf.output(self.fpath)
