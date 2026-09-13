"""
test_calculations.py — Unit tests for src/calculations.py

Covers:
  - attendance_percentage (normal, zero, 100%, exact 75%)
  - effective_total
  - status_label thresholds
  - classes_needed_to_recover (above, below, zero total)
  - classes_can_miss (above, below, zero total)
  - whatif_attend / whatif_miss
  - subject_summary
  - overall_summary
"""

import pytest
from src.calculations import (
    attendance_percentage,
    effective_total,
    status_label,
    status_color,
    classes_needed_to_recover,
    classes_can_miss,
    subject_summary,
    overall_summary,
    whatif_attend,
    whatif_miss,
)


# ===========================================================================
# effective_total
# ===========================================================================

class TestEffectiveTotal:
    def test_normal(self):
        assert effective_total(30, 10) == 40

    def test_zero_absent(self):
        assert effective_total(10, 0) == 10

    def test_zero_present(self):
        assert effective_total(0, 10) == 10

    def test_both_zero(self):
        assert effective_total(0, 0) == 0

    def test_medical_not_included(self):
        # Medical is handled outside this function;
        # effective_total only takes present + absent
        assert effective_total(5, 5) == 10


# ===========================================================================
# attendance_percentage
# ===========================================================================

class TestAttendancePercentage:
    def test_zero_total_returns_none(self):
        assert attendance_percentage(0, 0) is None

    def test_100_percent(self):
        assert attendance_percentage(10, 0) == 100.0

    def test_0_percent(self):
        assert attendance_percentage(0, 10) == 0.0

    def test_75_percent(self):
        assert attendance_percentage(30, 10) == 75.0

    def test_exact_75_percent_different_numbers(self):
        assert attendance_percentage(15, 5) == 75.0

    def test_below_75(self):
        pct = attendance_percentage(27, 13)
        assert pct is not None
        assert pct < 75.0

    def test_above_75(self):
        pct = attendance_percentage(80, 10)
        assert pct is not None
        assert pct > 75.0

    def test_rounding(self):
        # 1/3 ≈ 33.33
        pct = attendance_percentage(1, 2)
        assert pct == pytest.approx(33.33, abs=0.01)

    def test_large_numbers(self):
        pct = attendance_percentage(900, 100)
        assert pct == 90.0

    def test_invalid_high_absent(self):
        # 0 present, many absent
        pct = attendance_percentage(0, 100)
        assert pct == 0.0


# ===========================================================================
# status_label
# ===========================================================================

class TestStatusLabel:
    def test_none_is_no_data(self):
        assert status_label(None) == "No Data"

    def test_excellent(self):
        assert status_label(90.0, 75.0) == "Excellent"
        assert status_label(85.0, 75.0) == "Excellent"

    def test_safe_at_exactly_threshold(self):
        assert status_label(75.0, 75.0) == "Safe"

    def test_safe_above_threshold_below_85(self):
        assert status_label(80.0, 75.0) == "Safe"

    def test_warning_just_below_threshold(self):
        assert status_label(74.9, 75.0) == "Warning"

    def test_warning_at_threshold_minus_10(self):
        assert status_label(65.0, 75.0) == "Warning"

    def test_critical_below_65_with_75_threshold(self):
        assert status_label(64.9, 75.0) == "Critical"
        assert status_label(50.0, 75.0) == "Critical"

    def test_zero_is_critical(self):
        assert status_label(0.0, 75.0) == "Critical"

    def test_custom_threshold(self):
        # With 80% threshold: 79% should be Warning
        assert status_label(79.0, 80.0) == "Warning"
        assert status_label(80.0, 80.0) == "Safe"
        assert status_label(85.0, 80.0) == "Excellent"


# ===========================================================================
# classes_needed_to_recover
# ===========================================================================

class TestClassesNeededToRecover:
    def test_already_above_threshold(self):
        # 30/40 = 75% — exactly at threshold → needs 0
        assert classes_needed_to_recover(30, 10, 75.0) == 0

    def test_zero_total_returns_none(self):
        assert classes_needed_to_recover(0, 0, 75.0) is None

    def test_below_threshold(self):
        # 27/40 = 67.5%, needs N more to reach 75%
        # x = ceil((0.75*40 - 27)/(0.25)) = ceil(3/0.25) = ceil(12) = 12
        result = classes_needed_to_recover(27, 13, 75.0)
        assert result is not None
        assert result > 0
        # Verify the result is actually correct
        new_present = 27 + result
        new_total   = 40 + result
        assert new_present / new_total >= 0.75

    def test_exactly_at_threshold_returns_zero(self):
        assert classes_needed_to_recover(75, 25, 75.0) == 0

    def test_result_verifiable(self):
        """The computed N, when added, must reach or exceed the threshold."""
        present, absent, threshold = 18, 12, 75.0
        n = classes_needed_to_recover(present, absent, threshold)
        assert n is not None
        total = effective_total(present, absent)
        new_pct = (present + n) / (total + n) * 100
        assert new_pct >= threshold

    def test_high_threshold(self):
        """Test with 90% threshold."""
        n = classes_needed_to_recover(50, 10, 90.0)
        assert n is not None
        assert n > 0
        total = effective_total(50, 10)
        new_pct = (50 + n) / (total + n) * 100
        assert new_pct >= 90.0

    def test_100_percent_impossible_if_any_absent(self):
        """100% threshold with any absences is mathematically impossible."""
        result = classes_needed_to_recover(50, 5, 100.0)
        # Should return None (threshold >= 1.0)
        assert result is None


# ===========================================================================
# classes_can_miss
# ===========================================================================

class TestClassesCanMiss:
    def test_zero_total_returns_zero(self):
        assert classes_can_miss(0, 0, 75.0) == 0

    def test_100_attendance_can_miss_some(self):
        # 30 present, 0 absent → can miss 10 before hitting 75%
        # y = floor(30/0.75 - 30) = floor(40 - 30) = 10
        assert classes_can_miss(30, 0, 75.0) == 10

    def test_exactly_at_threshold_can_miss_zero(self):
        # 30/40 = 75% exactly → cannot miss any
        assert classes_can_miss(30, 10, 75.0) == 0

    def test_below_threshold_returns_zero(self):
        # Already below — cannot miss anything
        assert classes_can_miss(27, 13, 75.0) == 0

    def test_result_stays_above_threshold(self):
        """Verify: after missing the computed N, attendance >= threshold."""
        present, absent, threshold = 90, 10, 75.0
        can_miss = classes_can_miss(present, absent, threshold)
        total = effective_total(present, absent)
        if can_miss > 0:
            new_pct = present / (total + can_miss) * 100
            assert new_pct >= threshold

    def test_missing_one_more_would_drop_below(self):
        """Verify: missing can_miss+1 drops below threshold."""
        present, absent, threshold = 90, 10, 75.0
        can_miss = classes_can_miss(present, absent, threshold)
        total = effective_total(present, absent)
        if can_miss >= 0:
            over_limit = present / (total + can_miss + 1) * 100
            assert over_limit < threshold


# ===========================================================================
# whatif functions
# ===========================================================================

class TestWhatIf:
    def test_attend_more_increases_percentage(self):
        result = whatif_attend(50, 10, 10, 75.0)
        original = attendance_percentage(50, 10)
        assert result["new_percentage"] >= original

    def test_miss_more_decreases_percentage(self):
        result = whatif_miss(50, 10, 5, 75.0)
        original = attendance_percentage(50, 10)
        assert result["new_percentage"] <= original

    def test_attend_zero_extra_unchanged(self):
        result = whatif_attend(50, 10, 0, 75.0)
        assert result["new_percentage"] == attendance_percentage(50, 10)

    def test_miss_zero_extra_unchanged(self):
        result = whatif_miss(50, 10, 0, 75.0)
        assert result["new_percentage"] == attendance_percentage(50, 10)

    def test_status_updates_correctly(self):
        # Start at 50% (Critical), attend enough to reach 75%
        needed = classes_needed_to_recover(5, 5, 75.0)
        result = whatif_attend(5, 5, needed, 75.0)
        assert result["new_status"] in ("Safe", "Excellent")


# ===========================================================================
# subject_summary
# ===========================================================================

class TestSubjectSummary:
    def test_empty_records(self):
        result = subject_summary([], 75.0)
        assert result["present"] == 0
        assert result["absent"]  == 0
        assert result["total"]   == 0
        assert result["percentage"] is None

    def test_all_present(self):
        records = [{"status": "Present"}] * 10
        result = subject_summary(records, 75.0)
        assert result["present"] == 10
        assert result["percentage"] == 100.0
        assert result["status"] == "Excellent"

    def test_all_absent(self):
        records = [{"status": "Absent"}] * 10
        result = subject_summary(records, 75.0)
        assert result["absent"] == 10
        assert result["percentage"] == 0.0
        assert result["status"] == "Critical"

    def test_medical_excluded(self):
        records = [
            {"status": "Present"}, {"status": "Present"}, {"status": "Present"},
            {"status": "Medical"}, {"status": "Medical"},
        ]
        result = subject_summary(records, 75.0)
        # Medical is excluded: total = 3 present + 0 absent = 3
        assert result["present"] == 3
        assert result["medical"] == 2
        assert result["total"]   == 3
        assert result["percentage"] == 100.0

    def test_75_percent_exactly(self):
        records = (
            [{"status": "Present"}] * 15 +
            [{"status": "Absent"}]  * 5
        )
        result = subject_summary(records, 75.0)
        assert result["percentage"] == 75.0
        assert result["status"] == "Safe"


# ===========================================================================
# overall_summary
# ===========================================================================

class TestOverallSummary:
    def test_aggregates_correctly(self):
        summaries = [
            {"present": 20, "absent": 5, "medical": 1},
            {"present": 30, "absent": 10, "medical": 0},
        ]
        result = overall_summary(summaries)
        assert result["present"] == 50
        assert result["absent"]  == 15
        assert result["medical"] == 1
        assert result["total"]   == 65
        assert result["num_subjects"] == 2

    def test_empty_list(self):
        result = overall_summary([])
        assert result["present"] == 0
        assert result["total"]   == 0
        assert result["percentage"] is None
