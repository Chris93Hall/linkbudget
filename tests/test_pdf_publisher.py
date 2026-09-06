"""Tests for linkbudget.pdf_publisher.PDFPublisher."""

from linkbudget import link_container as lc
from linkbudget.pdf_publisher import PDFPublisher


def test_publish_writes_a_valid_pdf_file(tmp_path, small_data_list):
    out_file = tmp_path / "report.pdf"
    PDFPublisher(str(out_file), title="Budget").publish(small_data_list)

    data = out_file.read_bytes()
    assert data.startswith(b"%PDF")
    assert data.rstrip().endswith(b"%%EOF")
    assert len(data) > 1000


def test_publish_handles_components_without_a_description(tmp_path):
    budget = lc.LinkContainer()
    budget.add_component(lc.SignalSource("src", "", signal_power=1.0))
    budget.add_component(lc.Gain("amp", "with description", gain=10.0))
    budget.compute()

    out_file = tmp_path / "nodesc.pdf"
    PDFPublisher(str(out_file)).publish(budget.data_list)
    assert out_file.read_bytes().startswith(b"%PDF")


def test_default_title_is_used_when_none_is_given(tmp_path, small_data_list):
    pub = PDFPublisher(str(tmp_path / "r.pdf"))
    assert pub.title == "Link Budget Report"
    pub.publish(small_data_list)
    assert (tmp_path / "r.pdf").exists()


def test_publish_paginates_a_long_detailed_report(tmp_path):
    budget = lc.LinkContainer()
    budget.add_component(lc.SignalSource("src", "", signal_power=1.0, noise_power=1.0))
    # Mixer emits a tall detail table (~15 fields), so a couple of dozen of them
    # forces the detailed report to spill across several pages.
    for i in range(25):
        budget.add_component(lc.Mixer(
            f"mixer {i}", f"downconversion stage {i}",
            lo_frequency=1e9, rf_frequency=2e9, conversion_loss_db=6.0, image_reject_db=30.0,
        ))
    budget.compute()

    out_file = tmp_path / "long.pdf"
    PDFPublisher(str(out_file)).publish(budget.data_list)
    data = out_file.read_bytes()
    assert data.startswith(b"%PDF")
    # the detailed report alone must have spilled onto several pages
    assert data.count(b"/Type /Page") + data.count(b"/Type/Page") >= 3
