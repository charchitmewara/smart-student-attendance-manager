"""
services.py — Higher-level service functions that combine DB queries
with business logic calculations.

UI pages call services; services call models and calculations.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from src import calculations as calc
from src import models


def get_subject_stats(semester_id: int, student_threshold: float = 75.0) -> list[dict]:
    """
    Return enriched per-subject stats for a semester.

    Combines raw DB counts with calculated percentage, status,
    advisory messages, and the effective threshold for each subject.
    """
    raw = models.get_subject_summary(semester_id)
    result = []

    for row in raw:
        threshold = row["threshold"] if row["threshold"] is not None else student_threshold
        present   = row["present"]  or 0
        absent    = row["absent"]   or 0
        medical   = row["medical"]  or 0

        pct   = calc.attendance_percentage(present, absent)
        label = calc.status_label(pct, threshold)

        result.append({
            "subject_id":       row["subject_id"],
            "subject_name":     row["subject_name"],
            "subject_code":     row["subject_code"] or "",
            "threshold":        threshold,
            "is_archived":      row["is_archived"],
            "present":          present,
            "absent":           absent,
            "medical":          medical,
            "total":            calc.effective_total(present, absent),
            "percentage":       pct,
            "status":           label,
            "color":            calc.status_color(label),
            "can_miss":         calc.classes_can_miss(present, absent, threshold),
            "needs_to_attend":  calc.classes_needed_to_recover(present, absent, threshold),
        })

    return result


def get_dashboard_data(student_id: int, semester_id: int, student_threshold: float = 75.0) -> dict:
    """
    Return all data needed to render the dashboard for one semester.
    """
    subject_stats = get_subject_stats(semester_id, student_threshold)

    # Overall figures (Medical excluded from totals)
    total_present = sum(s["present"] for s in subject_stats)
    total_absent  = sum(s["absent"]  for s in subject_stats)
    total_medical = sum(s["medical"] for s in subject_stats)
    overall_pct   = calc.attendance_percentage(total_present, total_absent)
    overall_label = calc.status_label(overall_pct, student_threshold)

    return {
        "subject_stats":    subject_stats,
        "total_present":    total_present,
        "total_absent":     total_absent,
        "total_medical":    total_medical,
        "total_classes":    calc.effective_total(total_present, total_absent),
        "overall_pct":      overall_pct,
        "overall_status":   overall_label,
        "overall_color":    calc.status_color(overall_label),
        "num_subjects":     len(subject_stats),
        "can_miss":         calc.classes_can_miss(total_present, total_absent, student_threshold),
        "needs_to_attend":  calc.classes_needed_to_recover(total_present, total_absent, student_threshold),
    }
