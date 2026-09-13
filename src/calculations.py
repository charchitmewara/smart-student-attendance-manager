"""
calculations.py — Pure attendance calculation functions.

All functions are side-effect-free: they accept numeric inputs and
return computed results.  No database calls are made here.
"""

from __future__ import annotations

import math
from typing import Optional


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def effective_total(present: int, absent: int) -> int:
    """
    Return the effective total classes (Medical Leave excluded).

    Medical Leave records do not count toward or against the student.
    """
    return present + absent


def attendance_percentage(present: int, absent: int) -> Optional[float]:
    """
    Calculate attendance percentage.

    Medical leave is excluded from both numerator and denominator.

    Returns None when there are no effective classes (avoids ZeroDivisionError).

    Examples:
        >>> attendance_percentage(30, 10)
        75.0
        >>> attendance_percentage(0, 0)
        None
        >>> attendance_percentage(10, 0)
        100.0
    """
    total = effective_total(present, absent)
    if total == 0:
        return None
    return round((present / total) * 100, 2)


def status_label(percentage: Optional[float], threshold: float = 75.0) -> str:
    """
    Return a human-readable attendance status label.

    Thresholds:
        >= 85%         → "Excellent"
        >= threshold   → "Safe"
        >= threshold-10 → "Warning"
        < threshold-10  → "Critical"
        None (no data) → "No Data"

    Examples:
        >>> status_label(90.0, 75.0)
        'Excellent'
        >>> status_label(75.0, 75.0)
        'Safe'
        >>> status_label(68.0, 75.0)
        'Warning'
        >>> status_label(60.0, 75.0)
        'Critical'
        >>> status_label(None)
        'No Data'
    """
    if percentage is None:
        return "No Data"
    if percentage >= 85.0:
        return "Excellent"
    if percentage >= threshold:
        return "Safe"
    if percentage >= max(threshold - 10.0, 0.0):
        return "Warning"
    return "Critical"


def status_color(label: str) -> str:
    """Return a hex color string for a given status label."""
    colors = {
        "Excellent": "#22C55E",   # green
        "Safe":      "#4A90D9",   # blue
        "Warning":   "#F59E0B",   # amber
        "Critical":  "#EF4444",   # red
        "No Data":   "#94A3B8",   # slate
    }
    return colors.get(label, "#94A3B8")


# ---------------------------------------------------------------------------
# Advisory calculations
# ---------------------------------------------------------------------------

def classes_needed_to_recover(
    present: int,
    absent: int,
    threshold: float = 75.0,
) -> Optional[int]:
    """
    Calculate how many consecutive classes a student must attend to reach
    the required threshold.

    Returns 0 if already at or above the threshold.
    Returns None if no classes have been recorded yet.

    Formula: find the smallest non-negative integer x such that
        (present + x) / (present + absent + x) >= threshold / 100

    Derivation:
        present + x >= (threshold/100) * (total + x)
        present + x - (threshold/100)*x >= (threshold/100) * total
        x * (1 - threshold/100) >= (threshold/100) * total - present
        x >= ((threshold/100) * total - present) / (1 - threshold/100)

    Examples:
        >>> classes_needed_to_recover(30, 10, 75.0)
        0
        >>> classes_needed_to_recover(27, 13, 75.0)
        3
        >>> classes_needed_to_recover(0, 0, 75.0)
        None
    """
    total = effective_total(present, absent)
    if total == 0:
        return None

    pct = attendance_percentage(present, absent)
    if pct is not None and pct >= threshold:
        return 0

    r = threshold / 100.0
    # Edge case: threshold is 100% — any absence makes recovery impossible
    if r >= 1.0:
        return None

    numerator = r * total - present
    denominator = 1.0 - r
    x = math.ceil(numerator / denominator)
    return max(0, x)


def classes_can_miss(
    present: int,
    absent: int,
    threshold: float = 75.0,
) -> int:
    """
    Calculate how many future classes a student can miss while keeping
    attendance at or above the threshold.

    Returns 0 if already below or exactly at the threshold.
    Returns 0 if no classes recorded.

    Formula: find the largest non-negative integer y such that
        present / (present + absent + y) >= threshold / 100

    Derivation:
        present >= (threshold/100) * (total + y)
        present / (threshold/100) - total >= y
        y <= present / (threshold/100) - total

    Examples:
        >>> classes_can_miss(30, 0, 75.0)
        10
        >>> classes_can_miss(30, 10, 75.0)
        0
        >>> classes_can_miss(0, 0, 75.0)
        0
    """
    total = effective_total(present, absent)
    if total == 0:
        return 0

    pct = attendance_percentage(present, absent)
    if pct is None or pct < threshold:
        return 0

    r = threshold / 100.0
    if r <= 0:
        return 0

    max_miss = (present / r) - total
    return max(0, math.floor(max_miss))


# ---------------------------------------------------------------------------
# Summary aggregation
# ---------------------------------------------------------------------------

def subject_summary(records: list[dict], threshold: float = 75.0) -> dict:
    """
    Aggregate a list of attendance record dicts into summary statistics.

    Each record must have a 'status' key with value 'Present', 'Absent', or 'Medical'.

    Returns a dict:
        present, absent, medical, total, percentage, status, can_miss, needs_to_attend
    """
    present = sum(1 for r in records if r.get("status") == "Present")
    absent  = sum(1 for r in records if r.get("status") == "Absent")
    medical = sum(1 for r in records if r.get("status") == "Medical")
    total   = effective_total(present, absent)
    pct     = attendance_percentage(present, absent)
    label   = status_label(pct, threshold)

    return {
        "present":          present,
        "absent":           absent,
        "medical":          medical,
        "total":            total,
        "percentage":       pct,
        "status":           label,
        "can_miss":         classes_can_miss(present, absent, threshold),
        "needs_to_attend":  classes_needed_to_recover(present, absent, threshold),
    }


def overall_summary(subject_summaries: list[dict]) -> dict:
    """
    Compute overall (cross-subject) attendance statistics from a list
    of per-subject summary dicts.

    Returns a dict with the same keys as subject_summary(), plus 'num_subjects'.
    """
    total_present = sum(s.get("present", 0) for s in subject_summaries)
    total_absent  = sum(s.get("absent",  0) for s in subject_summaries)
    total_medical = sum(s.get("medical", 0) for s in subject_summaries)

    return {
        "present":      total_present,
        "absent":       total_absent,
        "medical":      total_medical,
        "total":        effective_total(total_present, total_absent),
        "percentage":   attendance_percentage(total_present, total_absent),
        "num_subjects": len(subject_summaries),
    }


# ---------------------------------------------------------------------------
# What-If calculator
# ---------------------------------------------------------------------------

def whatif_attend(present: int, absent: int, extra_classes: int, threshold: float = 75.0) -> dict:
    """
    Project attendance percentage if the student attends the next N classes.

    Returns a dict: new_present, new_total, new_percentage, new_status
    """
    new_present = present + extra_classes
    new_total   = effective_total(present, absent) + extra_classes
    new_pct     = attendance_percentage(new_present, new_total - new_present)
    return {
        "new_present":    new_present,
        "new_total":      new_total,
        "new_percentage": new_pct,
        "new_status":     status_label(new_pct, threshold),
    }


def whatif_miss(present: int, absent: int, extra_misses: int, threshold: float = 75.0) -> dict:
    """
    Project attendance percentage if the student misses the next N classes.

    Returns a dict: new_absent, new_total, new_percentage, new_status
    """
    new_absent  = absent + extra_misses
    new_total   = effective_total(present, absent) + extra_misses
    new_pct     = attendance_percentage(present, new_absent)
    return {
        "new_absent":     new_absent,
        "new_total":      new_total,
        "new_percentage": new_pct,
        "new_status":     status_label(new_pct, threshold),
    }
