"""Tests for linkbudget.markdown_publisher.MarkdownPublisher."""

from linkbudget import link_container as lc
from linkbudget.markdown_publisher import MarkdownPublisher


def test_publish_writes_a_markdown_document(tmp_path, small_data_list):
    out_file = tmp_path / "report.md"
    MarkdownPublisher(str(out_file), title="My Report").publish(small_data_list)

    text = out_file.read_text(encoding="utf-8")
    assert text.startswith("# My Report\n")
    assert "## Summary" in text
    assert "## Detailed Report" in text
    assert text.endswith("\n")


def test_summary_is_a_valid_gfm_table(tmp_path, small_data_list):
    out_file = tmp_path / "report.md"
    MarkdownPublisher(str(out_file)).publish(small_data_list)
    lines = out_file.read_text(encoding="utf-8").splitlines()

    header = next(line for line in lines if line.startswith("| # |"))
    separator = lines[lines.index(header) + 1]
    assert set(separator) <= set("|- ")
    # one data row per stage, each with the same column count as the header
    columns = header.count("|")
    rows = [line for line in lines
            if line.startswith("| ") and line[2].isdigit()]
    assert len(rows) == len(small_data_list)
    assert all(row.count("|") == columns for row in rows)


def test_every_component_appears_with_a_detail_section(tmp_path, small_data_list):
    out_file = tmp_path / "report.md"
    MarkdownPublisher(str(out_file)).publish(small_data_list)
    text = out_file.read_text(encoding="utf-8")
    for index, data in enumerate(small_data_list):
        assert f"### {index + 1}. {data['name']}" in text


def test_power_units_are_threaded_into_the_headers(tmp_path, small_data_list):
    out_file = tmp_path / "report.md"
    MarkdownPublisher(str(out_file)).publish(small_data_list, power_units="dBW")
    text = out_file.read_text(encoding="utf-8")
    assert "Signal Power Out (dBW)" in text
    assert "signal power out (dBW)" in text  # detail rows


def test_pipes_and_newlines_in_content_are_escaped(tmp_path):
    budget = lc.LinkContainer(warn=False)
    budget.add_component(lc.SignalSource("A | B", "line one\nline two", signal_power=1.0))
    budget.compute()

    out_file = tmp_path / "escaped.md"
    MarkdownPublisher(str(out_file)).publish(budget.data_list)
    text = out_file.read_text(encoding="utf-8")

    assert r"A \| B" in text
    assert "line one line two" in text
    # a raw pipe would break the table -- every table line has a balanced count
    for line in text.splitlines():
        if line.startswith("|"):
            assert line.count("|") - line.count(r"\|") >= 2


def test_non_ascii_content_round_trips_as_utf8(tmp_path):
    budget = lc.LinkContainer(warn=False)
    budget.add_component(lc.SignalSource("Antenne µ-Wellen", "λ/2 dipôle", signal_power=1.0))
    budget.compute()

    out_file = tmp_path / "unicode.md"
    MarkdownPublisher(str(out_file), title="Report ±3 dB").publish(budget.data_list)
    text = out_file.read_text(encoding="utf-8")

    assert "Antenne µ-Wellen" in text
    assert "λ/2 dipôle" in text
    assert "Report ±3 dB" in text


def test_handles_an_empty_budget(tmp_path):
    out_file = tmp_path / "empty.md"
    MarkdownPublisher(str(out_file)).publish([])
    text = out_file.read_text(encoding="utf-8")
    assert text.startswith("# Link Budget Report")
    assert "## Summary" in text


def test_works_as_one_of_several_publishers(tmp_path):
    budget = lc.LinkContainer(warn=False)
    budget.add_component(lc.SignalSource("s", "", signal_power=1.0, noise_power=1e-3))
    md = tmp_path / "multi.md"
    budget.add_publisher(MarkdownPublisher(str(md)))
    budget.publish()
    assert md.read_text(encoding="utf-8").startswith("# Link Budget Report")
