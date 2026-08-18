"""
html_publisher.py
"""

import html as html_lib

from . import convert
from .publishers import Publisher, float_to_bounded_str, label_with_units

PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; margin: 2rem; color: #1a1a1a; background: #fafafa; }}
  h1 {{ margin-bottom: 0.25rem; }}
  h2 {{ margin-top: 2.5rem; border-bottom: 2px solid #ddd; padding-bottom: 0.25rem; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; background: #fff; }}
  caption {{ caption-side: top; text-align: left; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: right; font-variant-numeric: tabular-nums; }}
  th:first-child, td:first-child {{ text-align: left; }}
  th:nth-child(2), td:nth-child(2) {{ text-align: left; }}
  thead th {{ background: #2d3748; color: #fff; position: sticky; top: 0; }}
  tbody tr:nth-child(even) {{ background: #f2f2f2; }}
  .desc {{ color: #666; font-size: 0.85em; font-weight: normal; }}
  .component {{ margin-top: 1.5rem; }}
  .component h3 {{ margin-bottom: 0.25rem; }}
  .detail-table td:first-child {{ width: 240px; color: #444; }}
</style>
</head>
<body>
<h1>{title}</h1>
<h2>Summary</h2>
<table>
<thead>
<tr><th>#</th><th>Component</th><th>Signal Power Out ({power_units})</th><th>Noise Power Out ({power_units})</th>
<th>Signal Gain (dB)</th><th>Noise Gain (dB)</th><th>SNR (dB)</th></tr>
</thead>
<tbody>
{summary_rows}
</tbody>
</table>
<h2>Detailed Report</h2>
{detail_sections}
</body>
</html>
"""


class HTMLPublisher(Publisher):
    def __init__(self, fpath, title='Link Budget Report'):
        self.fpath = fpath
        self.title = title

    def _summary_rows(self, data_list):
        rows = []
        for index, data in enumerate(data_list):
            name = html_lib.escape(str(data['name']))
            description = html_lib.escape(str(data['description']))
            sig_power_out = float_to_bounded_str(data['signal_power_out'])
            noise_power_out = float_to_bounded_str(data['noise_power_out'])
            signal_gain = float_to_bounded_str(convert.linear_to_db(data['signal_gain']))
            noise_gain = float_to_bounded_str(convert.linear_to_db(data['noise_gain']))
            snr = float_to_bounded_str(convert.linear_to_db(data['snr']))
            rows.append(
                f'<tr><td>{index + 1}</td>'
                f'<td>{name}<div class="desc">{description}</div></td>'
                f'<td>{sig_power_out}</td><td>{noise_power_out}</td>'
                f'<td>{signal_gain}</td><td>{noise_gain}</td><td>{snr}</td></tr>')
        return '\n'.join(rows)

    def _detail_sections(self, data_list, power_units):
        sections = []
        for index, data in enumerate(data_list):
            field_rows = '\n'.join(
                f'<tr><td>{html_lib.escape(label_with_units(key, power_units))}</td>'
                f'<td>{html_lib.escape(str(value))}</td></tr>'
                for key, value in data.items())
            name = html_lib.escape(str(data['name']))
            sections.append(
                f'<div class="component"><h3>{index + 1}. {name}</h3>'
                f'<table class="detail-table">{field_rows}</table></div>')
        return '\n'.join(sections)

    def publish(self, data_list, power_units='W'):
        html_doc = PAGE_TEMPLATE.format(
            title=html_lib.escape(self.title),
            power_units=html_lib.escape(power_units),
            summary_rows=self._summary_rows(data_list),
            detail_sections=self._detail_sections(data_list, power_units))
        with open(self.fpath, 'w') as f:
            f.write(html_doc)
