"""
test_validation.py — Unit tests for src/validation.py
"""

import pytest
from datetime import date, timedelta
from src.validation import (
    validate_username,
    validate_password,
    validate_name,
    validate_subject_name,
    validate_subject_code,
    validate_semester_name,
    validate_threshold,
    validate_class_count,
    validate_attendance_date,
    validate_status,
    validate_attendance_row,
)


class TestValidateUsername:
    def test_valid(self):
        ok, _ = validate_username("student123")
        assert ok

    def test_valid_with_underscore(self):
        ok, _ = validate_username("john_doe")
        assert ok

    def test_too_short(self):
        ok, msg = validate_username("ab")
        assert not ok
        assert "3" in msg

    def test_too_long(self):
        ok, msg = validate_username("a" * 31)
        assert not ok

    def test_empty(self):
        ok, msg = validate_username("")
        assert not ok

    def test_special_chars(self):
        ok, msg = validate_username("user@name")
        assert not ok

    def test_spaces_only(self):
        ok, msg = validate_username("   ")
        assert not ok


class TestValidatePassword:
    def test_valid(self):
        ok, _ = validate_password("secure123")
        assert ok

    def test_too_short(self):
        ok, msg = validate_password("12345")
        assert not ok

    def test_empty(self):
        ok, msg = validate_password("")
        assert not ok

    def test_exactly_6(self):
        ok, _ = validate_password("abc123")
        assert ok


class TestValidateName:
    def test_valid(self):
        ok, _ = validate_name("Alice Johnson")
        assert ok

    def test_empty(self):
        ok, msg = validate_name("")
        assert not ok

    def test_whitespace_only(self):
        ok, msg = validate_name("   ")
        assert not ok

    def test_too_long(self):
        ok, msg = validate_name("A" * 101)
        assert not ok


class TestValidateSubjectName:
    def test_valid(self):
        ok, _ = validate_subject_name("Data Structures")
        assert ok

    def test_empty(self):
        ok, _ = validate_subject_name("")
        assert not ok

    def test_too_long(self):
        ok, _ = validate_subject_name("S" * 81)
        assert not ok


class TestValidateSubjectCode:
    def test_valid(self):
        ok, _ = validate_subject_code("CS201")
        assert ok

    def test_empty_is_valid(self):
        ok, _ = validate_subject_code("")
        assert ok

    def test_too_long(self):
        ok, _ = validate_subject_code("X" * 21)
        assert not ok


class TestValidateSemesterName:
    def test_valid(self):
        ok, _ = validate_semester_name("Semester 3 — 2024")
        assert ok

    def test_empty(self):
        ok, _ = validate_semester_name("")
        assert not ok

    def test_too_long(self):
        ok, _ = validate_semester_name("S" * 61)
        assert not ok


class TestValidateThreshold:
    def test_valid_75(self):
        ok, _ = validate_threshold(75.0)
        assert ok

    def test_valid_100(self):
        ok, _ = validate_threshold(100.0)
        assert ok

    def test_valid_1(self):
        ok, _ = validate_threshold(1.0)
        assert ok

    def test_zero_invalid(self):
        ok, _ = validate_threshold(0.0)
        assert not ok

    def test_above_100_invalid(self):
        ok, _ = validate_threshold(100.1)
        assert not ok

    def test_negative_invalid(self):
        ok, _ = validate_threshold(-5)
        assert not ok

    def test_string_input(self):
        ok, _ = validate_threshold("not_a_number")
        assert not ok


class TestValidateClassCount:
    def test_valid(self):
        ok, _ = validate_class_count(5)
        assert ok

    def test_one(self):
        ok, _ = validate_class_count(1)
        assert ok

    def test_zero_invalid(self):
        ok, _ = validate_class_count(0)
        assert not ok

    def test_above_max_invalid(self):
        ok, _ = validate_class_count(21)
        assert not ok

    def test_string_number(self):
        ok, _ = validate_class_count("5")
        assert ok

    def test_non_numeric(self):
        ok, _ = validate_class_count("abc")
        assert not ok


class TestValidateAttendanceDate:
    def test_today_valid(self):
        ok, _ = validate_attendance_date(date.today())
        assert ok

    def test_yesterday_valid(self):
        ok, _ = validate_attendance_date(date.today() - timedelta(days=1))
        assert ok

    def test_tomorrow_invalid(self):
        ok, msg = validate_attendance_date(date.today() + timedelta(days=1))
        assert not ok
        assert "future" in msg.lower()

    def test_string_date_valid(self):
        ok, _ = validate_attendance_date("2024-01-15")
        assert ok

    def test_invalid_string(self):
        ok, msg = validate_attendance_date("not-a-date")
        assert not ok


class TestValidateStatus:
    def test_present(self):
        ok, _ = validate_status("Present")
        assert ok

    def test_absent(self):
        ok, _ = validate_status("Absent")
        assert ok

    def test_medical(self):
        ok, _ = validate_status("Medical")
        assert ok

    def test_invalid(self):
        ok, _ = validate_status("Late")
        assert not ok

    def test_lowercase_invalid(self):
        ok, _ = validate_status("present")
        assert not ok


class TestValidateAttendanceRow:
    def test_valid_row(self):
        ok, _ = validate_attendance_row(1, date.today(), "Present")
        assert ok

    def test_none_subject(self):
        ok, msg = validate_attendance_row(None, date.today(), "Present")
        assert not ok

    def test_none_date(self):
        ok, msg = validate_attendance_row(1, None, "Present")
        assert not ok

    def test_future_date(self):
        ok, msg = validate_attendance_row(1, date.today() + timedelta(days=1), "Present")
        assert not ok

    def test_invalid_status(self):
        ok, msg = validate_attendance_row(1, date.today(), "OnLeave")
        assert not ok
