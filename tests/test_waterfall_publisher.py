"""Tests for linkbudget.waterfall_publisher.WaterfallPublisher."""

import pytest

pytest.importorskip("matplotlib")

from linkbudget import link_container as lc  # noqa: E402
from linkbudget.waterfall_publisher import WaterfallPublisher, _finite_db  # noqa: E402

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class TestFiniteDb:
    def test_converts_linear_power_to_db(self):
        assert _finite_db(1.0) == pytest.approx(0.0)
        assert _finite_db(10.0) == pytest.approx(10.0)

    def test_zero_power_becomes_nan(self):
        assert _finite_db(0.0) != _finite_db(0.0)  # NaN

    def test_infinite_snr_becomes_nan(self):
        assert _finite_db(float("inf")) != _finite_db(float("inf"))


def test_publish_writes_a_png(tmp_path, small_data_list):
    out = tmp_path / "cascade.png"
    WaterfallPublisher(str(out), title="Cascade").publish(small_data_list)
    data = out.read_bytes()
    assert data.startswith(PNG_MAGIC)
    assert len(data) > 2000


def test_publish_writes_svg_when_the_extension_says_so(tmp_path, small_data_list):
    out = tmp_path / "cascade.svg"
    WaterfallPublisher(str(out)).publish(small_data_list)
    assert out.read_text(encoding="utf-8").lstrip().startswith("<?xml")


def test_handles_an_empty_budget(tmp_path):
    out = tmp_path / "empty.png"
    WaterfallPublisher(str(out)).publish([])
    assert out.read_bytes().startswith(PNG_MAGIC)


def test_handles_stages_with_zero_signal_and_noise(tmp_path):
    # a budget where noise is zero until a ThermalNoise stage and the leading
    # signal power passes through a total loss -- exercises the NaN -> floor path
    budget = lc.LinkContainer()
    budget.add_component(lc.SignalSource("tx", "", signal_power=1.0, noise_power=0.0))
    budget.add_component(lc.FreeSpacePathLoss("path", "", distance=1e5, frequency=10e9))
    budget.add_component(lc.ThermalNoise("noise", "", bandwidth=1e6))
    budget.compute()

    out = tmp_path / "zeros.png"
    WaterfallPublisher(str(out)).publish(budget.data_list)
    assert out.read_bytes().startswith(PNG_MAGIC)


def test_works_as_one_of_several_publishers(tmp_path):
    budget = lc.LinkContainer()
    budget.add_component(lc.SignalSource("s", "", signal_power=1.0, noise_power=1e-3))
    png = tmp_path / "multi.png"
    budget.add_publisher(WaterfallPublisher(str(png)))
    budget.publish()
    assert png.read_bytes().startswith(PNG_MAGIC)


def test_does_not_leak_figures(tmp_path, small_data_list):
    import matplotlib.pyplot as plt

    before = len(plt.get_fignums())
    for i in range(3):
        WaterfallPublisher(str(tmp_path / f"c{i}.png")).publish(small_data_list)
    assert len(plt.get_fignums()) == before
