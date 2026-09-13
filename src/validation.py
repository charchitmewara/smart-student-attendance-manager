"""
validation.py — Input validation functions.

All functions return (is_valid: bool, message: str).
An empty message means validation passed.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Tuple

ValidationResult = Tuple[bool, str]


# ---------------------------------------------------------------------------
# String validators
# ---------------------------------------------------------------------------

def validate_username(username: str) -> ValidationResult:
    """
    Validate a username.
    Rules: 3–30 characters, alphanumeric and underscores only.
    """
    if not username or not username.strip():
        return False, "Username cannot be empty."
    username = username.strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(username) > 30:
        return False, "Username must be at most 30 characters."
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username may only contain letters, digits, and underscores."
    return True, ""


def validate_password(password: str) -> ValidationResult:
    """Password must be at least 6 characters."""
    if not password:
        return False, "Password cannot be empty."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    return True, ""


def validate_name(name: str, field_label: str = "Name") -> ValidationResult:
    """General text field: 1–100 chars, not blank."""
    if not name or not name.strip():
        return False, f"{field_label} cannot be empty."
    if len(name.strip()) > 100:
        return False, f"{field_label} must be at most 100 characters."
    return True, ""


def validate_subject_name(name: str) -> ValidationResult:
    """Subject name: 1–80 chars, not blank."""
    if not name or not name.strip():
        return False, "Subject name cannot be empty."
    if len(name.strip()) > 80:
        return False, "Subject name must be at most 80 characters."
    return True, ""


def validate_subject_code(code: str) -> ValidationResult:
    """Subject code: optional, at most 20 chars."""
    if code and len(code.strip()) > 20:
        return False, "Subject code must be at most 20 characters."
    return True, ""


def validate_semester_name(name: str) -> ValidationResult:
    """Semester name: 1–60 chars, not blank."""
    if not name or not name.strip():
        return False, "Semester name cannot be empty."
    if len(name.strip()) > 60:
        return False, "Semester name must be at most 60 characters."
    return True, ""


# ---------------------------------------------------------------------------
# Numeric validators
# ---------------------------------------------------------------------------

def validate_threshold(value: float | int | str) -> ValidationResult:
    """Attendance threshold must be between 1.0 and 100.0."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False, "Attendance threshold must be a number."
    if v < 1.0 or v > 100.0:
        return False, "Attendance threshold must be between 1% and 100%."
    return True, ""


def validate_class_count(value: int | str) -> ValidationResult:
    """Number of classes per day: integer between 1 and 20."""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return False, "Number of classes must be a whole number."
    if v < 1:
        return False, "Number of classes must be at least 1."
    if v > 20:
        return False, "Number of classes per day cannot exceed 20."
    return True, ""


# ---------------------------------------------------------------------------
# Date validators
# ---------------------------------------------------------------------------

def validate_attendance_date(record_date: date | str) -> ValidationResult:
    """
    Attendance date must not be in the future.
    Accepts a date object or an ISO string (YYYY-MM-DD).
    """
    if isinstance(record_date, str):
        try:
            record_date = datetime.strptime(record_date, "%Y-%m-%d").date()
        except ValueError:
            return False, "Invalid date format. Use YYYY-MM-DD."

    if record_date > date.today():
        return False, "Attendance date cannot be in the future."
    return True, ""


# ---------------------------------------------------------------------------
# Status validator
# ---------------------------------------------------------------------------

VALID_STATUSES = {"Present", "Absent", "Medical"}


def validate_status(status: str) -> ValidationResult:
    """Status must be one of: Present, Absent, Medical."""
    if status not in VALID_STATUSES:
        return False, f"Status must be one of: {', '.join(sorted(VALID_STATUSES))}."
    return True, ""


# ---------------------------------------------------------------------------
# Composite validators
# ---------------------------------------------------------------------------

def validate_attendance_row(
    subject_id: int | None,
    record_date: date | str | None,
    status: str | None,
) -> ValidationResult:
    """Validate a single attendance row from the entry form."""
    if not subject_id:
        return False, "Please select a subject."

    if record_date is None:
        return False, "Please select a date."
    ok, msg = validate_attendance_date(record_date)
    if not ok:
        return False, msg

    if not status:
        return False, "Please select an attendance status."
    ok, msg = validate_status(status)
    if not ok:
        return False, msg

    return True, ""
