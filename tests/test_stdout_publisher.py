"""Tests for linkbudget.publishers.StdOutPublisher."""

import pytest

from linkbudget import link_container as lc
from linkbudget.publishers import StdOutPublisher


def test_publish_prints_summary_and_detailed_sections(capsys, small_data_list):
    StdOutPublisher().publish(small_data_list)
    out = capsys.readouterr().out
    assert "LINK BUDGET SUMMARY" in out
    assert "DETAILED LINK BUDGET REPORT" in out


def test_summary_lists_every_component_by_name(capsys, small_data_list):
    StdOutPublisher().publish_summary(small_data_list)
    out = capsys.readouterr().out
    for data in small_data_list:
        assert data["name"] in out


def test_detailed_report_labels_power_fields_with_units(capsys, small_data_list):
    StdOutPublisher().publish_detailed(small_data_list, power_units="mW")
    out = capsys.readouterr().out
    assert "signal power out (mW)" in out


def test_publish_handles_an_empty_budget(capsys):
    StdOutPublisher().publish([])
    out = capsys.readouterr().out
    assert "LINK BUDGET SUMMARY" in out


def test_publish_is_the_default_container_publisher(capsys):
    budget = lc.LinkContainer()
    budget.add_component(lc.SignalSource("src", "desc-text", signal_power=1.0))
    budget.publish()
    out = capsys.readouterr().out
    assert "src" in out
    assert "desc-text" in out


def test_stdout_publisher_can_be_constructed():
    assert isinstance(StdOutPublisher(), StdOutPublisher)
