"""Tests for linkbudget.html_publisher.HTMLPublisher."""

from linkbudget import link_container as lc
from linkbudget.html_publisher import HTMLPublisher


def test_publish_writes_a_complete_html_document(tmp_path, small_data_list):
    out_file = tmp_path / "report.html"
    HTMLPublisher(str(out_file), title="My Report").publish(small_data_list)

    text = out_file.read_text(encoding="utf-8")
    assert text.startswith("<!doctype html>")
    assert "</html>" in text
    assert "<title>My Report</title>" in text
    assert "<h1>My Report</h1>" in text


def test_every_component_appears_in_the_summary_and_detail(tmp_path, small_data_list):
    out_file = tmp_path / "report.html"
    HTMLPublisher(str(out_file)).publish(small_data_list)
    text = out_file.read_text(encoding="utf-8")
    for data in small_data_list:
        assert data["name"] in text


def test_power_units_are_threaded_into_the_headers(tmp_path, small_data_list):
    out_file = tmp_path / "report.html"
    HTMLPublisher(str(out_file)).publish(small_data_list, power_units="dBW")
    text = out_file.read_text(encoding="utf-8")
    assert "Signal Power Out (dBW)" in text


def test_component_names_and_descriptions_are_html_escaped(tmp_path):
    budget = lc.LinkContainer()
    budget.add_component(lc.SignalSource(
        "<script>alert(1)</script>", "A & B < C", signal_power=1.0,
    ))
    budget.compute()

    out_file = tmp_path / "xss.html"
    HTMLPublisher(str(out_file)).publish(budget.data_list)
    text = out_file.read_text(encoding="utf-8")

    assert "<script>alert(1)</script>" not in text
    assert "&lt;script&gt;" in text
    assert "A &amp; B &lt; C" in text


def test_non_ascii_content_round_trips_as_utf8(tmp_path):
    budget = lc.LinkContainer()
    budget.add_component(lc.SignalSource("Antenne µ-Wellen", "λ/2 dipôle", signal_power=1.0))
    budget.compute()

    out_file = tmp_path / "unicode.html"
    HTMLPublisher(str(out_file), title="Report ±3 dB").publish(budget.data_list)
    text = out_file.read_text(encoding="utf-8")

    assert "Antenne µ-Wellen" in text
    assert "λ/2 dipôle" in text
    assert "Report ±3 dB" in text


def test_handles_an_empty_budget(tmp_path):
    out_file = tmp_path / "empty.html"
    HTMLPublisher(str(out_file)).publish([])
    assert out_file.read_text(encoding="utf-8").startswith("<!doctype html>")
