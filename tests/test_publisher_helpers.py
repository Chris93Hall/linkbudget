"""Tests for the formatting helpers in linkbudget.publishers."""

import math

import pytest

from linkbudget import publishers
from linkbudget.publishers import (
    Publisher,
    float_to_bounded_str,
    format_number,
    label_with_units,
    pad_string,
    trunc_float,
)


class TestLabelWithUnits:
    def test_underscores_become_spaces(self):
        assert label_with_units("noise_figure_db", "W") == "noise figure db"

    def test_power_field_gets_units_appended(self):
        assert label_with_units("signal_power_out", "W") == "signal power out (W)"

    def test_units_string_is_used_verbatim(self):
        assert label_with_units("noise_power_in", "mW") == "noise power in (mW)"

    def test_non_power_field_gets_no_units(self):
        assert label_with_units("snr", "W") == "snr"

    @pytest.mark.parametrize("field", sorted(publishers.POWER_FIELDS))
    def test_every_declared_power_field_is_labelled_with_units(self, field):
        assert label_with_units(field, "W").endswith(" (W)")


class TestPadString:
    def test_pads_on_the_left_by_default(self):
        assert pad_string("ab", 5) == "   ab"

    def test_pads_on_the_right_when_requested(self):
        assert pad_string("ab", 5, side="right") == "ab   "

    def test_returns_input_unchanged_when_already_long_enough(self):
        assert pad_string("abcdef", 3) == "abcdef"

    def test_exact_length_is_unchanged(self):
        assert pad_string("abc", 3) == "abc"

    def test_coerces_non_strings(self):
        assert pad_string(123, 5) == "  123"


class TestTruncFloat:
    def test_returns_a_float(self):
        assert isinstance(trunc_float(1.5), float)

    def test_keeps_short_values_intact(self):
        assert trunc_float(1.5) == pytest.approx(1.5)

    def test_rounds_to_six_decimal_places(self):
        assert trunc_float(1.23456789) == pytest.approx(1.234568)


class TestFormatNumber:
    def test_zero_renders_as_zero_point_zero(self):
        assert format_number(0) == "0.0"
        assert format_number(0.0) == "0.0"

    def test_floating_point_noise_is_collapsed(self):
        assert format_number(2.9999999999999996) == "3"

    def test_respects_significant_figures(self):
        assert format_number(math.pi, sig_figs=3) == "3.14"

    def test_large_magnitude_uses_scientific_notation(self):
        assert format_number(1234567.0) == "1.23457e+06"

    def test_booleans_are_passed_through_as_text(self):
        assert format_number(True) == "True"

    def test_non_numbers_are_stringified(self):
        assert format_number("3 dB") == "3 dB"
        assert format_number(None) == "None"

    def test_nan_and_inf_are_stringified(self):
        assert format_number(float("nan")) == "nan"
        assert format_number(float("inf")) == "inf"
        assert format_number(float("-inf")) == "-inf"


class TestFloatToBoundedStr:
    def test_short_value_is_returned_directly(self):
        assert float_to_bounded_str(1.0) == "1"

    def test_value_within_bound_is_untouched(self):
        out = float_to_bounded_str(123.456, str_length=12)
        assert out == "123.456"
        assert len(out) <= 12

    def test_precision_is_reduced_to_fit_the_bound(self):
        out = float_to_bounded_str(-1.23456789e123, str_length=8)
        assert len(out) <= 8
        assert out.startswith("-1")

    def test_returns_best_effort_when_even_one_sig_fig_does_not_fit(self):
        out = float_to_bounded_str(-1.23456789e123, str_length=3)
        # cannot get under 3 chars; the loop exhausts and the last attempt is returned
        assert out == format_number(-1.23456789e123, 1)


class _MiniPublisher(Publisher):
    """Minimal concrete Publisher that defers to the abstract base."""

    def __init__(self):
        super().__init__()

    def publish(self, data_list, power_units="W"):
        return super().publish(data_list, power_units)


def test_publisher_is_abstract():
    with pytest.raises(TypeError):
        Publisher()  # pylint: disable=abstract-class-instantiated


def test_concrete_publisher_can_defer_to_the_base():
    pub = _MiniPublisher()
    assert pub.publish([], "W") is None
