"""
test_database.py — Integration tests for database CRUD operations.

Uses a temporary in-memory SQLite database so tests are isolated
from the production database file.
"""

import os
import pytest
from datetime import date, timedelta
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Fixture: patch the DB to use an in-memory SQLite database
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def use_in_memory_db(tmp_path, monkeypatch):
    """
    Redirect all DB calls to a fresh temporary SQLite database for each test.
    """
    db_file = str(tmp_path / "test_attendance.db")

    # Patch _get_db_path so get_connection() uses the temp file
    monkeypatch.setattr("src.database._get_db_path", lambda: db_file)
    # Ensure DATABASE_URL env is not set (force SQLite path)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Re-initialize schema on the temp DB
    from src.database import init_db
    init_db()

    yield


# ---------------------------------------------------------------------------
# Helpers to avoid import loops
# ---------------------------------------------------------------------------

def _get_models():
    from src import models
    return models


# ===========================================================================
# Student CRUD
# ===========================================================================

class TestStudentCRUD:
    def test_create_and_fetch(self):
        m = _get_models()
        sid = m.create_student("testuser", "hashed_pw")
        assert sid is not None

        student = m.get_student_by_username("testuser")
        assert student is not None
        assert student["username"] == "testuser"
        assert student["password_hash"] == "hashed_pw"

    def test_duplicate_username_returns_none(self):
        m = _get_models()
        m.create_student("dup_user", "pw1")
        result = m.create_student("dup_user", "pw2")
        assert result is None

    def test_get_nonexistent_returns_none(self):
        m = _get_models()
        result = m.get_student_by_username("nobody")
        assert result is None

    def test_update_profile(self):
        m = _get_models()
        sid = m.create_student("profileuser", "pw")
        m.update_student_profile(
            sid,
            name="Alice",
            university="MIT",
            required_percentage=80.0,
        )
        student = m.get_student_by_id(sid)
        assert student["name"] == "Alice"
        assert student["university"] == "MIT"
        assert student["required_percentage"] == 80.0

    def test_update_password(self):
        m = _get_models()
        sid = m.create_student("pwuser", "old_hash")
        m.update_student_password(sid, "new_hash")
        student = m.get_student_by_id(sid)
        assert student["password_hash"] == "new_hash"


# ===========================================================================
# Semester CRUD
# ===========================================================================

class TestSemesterCRUD:
    def _student(self):
        m = _get_models()
        return m.create_student("semuser", "pw")

    def test_create_and_list(self):
        m = _get_models()
        sid = self._student()
        sem_id = m.create_semester(sid, "Sem 1")
        assert sem_id is not None

        sems = m.get_semesters(sid)
        assert len(sems) == 1
        assert sems[0]["name"] == "Sem 1"

    def test_set_active(self):
        m = _get_models()
        sid = self._student()
        s1 = m.create_semester(sid, "Sem A")
        s2 = m.create_semester(sid, "Sem B")

        m.set_active_semester(sid, s1)
        active = m.get_active_semester(sid)
        assert active["id"] == s1

        m.set_active_semester(sid, s2)
        active = m.get_active_semester(sid)
        assert active["id"] == s2

    def test_only_one_active(self):
        m = _get_models()
        sid = self._student()
        s1 = m.create_semester(sid, "Sem X")
        s2 = m.create_semester(sid, "Sem Y")
        m.set_active_semester(sid, s1)
        m.set_active_semester(sid, s2)
        sems = m.get_semesters(sid)
        active_count = sum(1 for s in sems if s["is_active"])
        assert active_count == 1

    def test_delete_semester(self):
        m = _get_models()
        sid = self._student()
        sem_id = m.create_semester(sid, "Temp Sem")
        m.delete_semester(sem_id, sid)
        sems = m.get_semesters(sid)
        assert not any(s["id"] == sem_id for s in sems)


# ===========================================================================
# Subject CRUD
# ===========================================================================

class TestSubjectCRUD:
    def _setup(self):
        m = _get_models()
        sid = m.create_student("subjuser", "pw")
        sem_id = m.create_semester(sid, "Test Sem")
        return m, sid, sem_id

    def test_create_and_list(self):
        m, _, sem_id = self._setup()
        subj_id = m.create_subject(sem_id, "Maths", "MAT101")
        assert subj_id is not None

        subjects = m.get_subjects(sem_id)
        assert len(subjects) == 1
        assert subjects[0]["name"] == "Maths"

    def test_duplicate_name_returns_none(self):
        m, _, sem_id = self._setup()
        m.create_subject(sem_id, "Physics", "PHY")
        result = m.create_subject(sem_id, "Physics", "PHY2")
        assert result is None

    def test_archive_subject(self):
        m, _, sem_id = self._setup()
        subj_id = m.create_subject(sem_id, "Chemistry")
        m.archive_subject(subj_id)

        # Should not appear in default listing (include_archived=False)
        active = m.get_subjects(sem_id, include_archived=False)
        assert not any(s["id"] == subj_id for s in active)

        # Should appear when include_archived=True
        all_s = m.get_subjects(sem_id, include_archived=True)
        assert any(s["id"] == subj_id for s in all_s)

    def test_unarchive_subject(self):
        m, _, sem_id = self._setup()
        subj_id = m.create_subject(sem_id, "History")
        m.archive_subject(subj_id)
        m.unarchive_subject(subj_id)
        active = m.get_subjects(sem_id)
        assert any(s["id"] == subj_id for s in active)

    def test_delete_subject(self):
        m, _, sem_id = self._setup()
        subj_id = m.create_subject(sem_id, "Geography")
        m.delete_subject(subj_id)
        subjects = m.get_subjects(sem_id)
        assert not any(s["id"] == subj_id for s in subjects)

    def test_subject_has_records_false_initially(self):
        m, _, sem_id = self._setup()
        subj_id = m.create_subject(sem_id, "English")
        assert not m.subject_has_records(subj_id)


# ===========================================================================
# Attendance CRUD
# ===========================================================================

class TestAttendanceCRUD:
    def _setup(self):
        m = _get_models()
        sid = m.create_student("attuser", "pw")
        sem_id = m.create_semester(sid, "Test Sem")
        subj_id = m.create_subject(sem_id, "CS", "CS101")
        return m, sid, sem_id, subj_id

    def test_insert_and_exists(self):
        m, _, _, subj_id = self._setup()
        today = date.today()
        ok = m.insert_attendance_record(subj_id, today, "Present")
        assert ok
        assert m.attendance_exists(subj_id, today)

    def test_duplicate_insert_returns_false(self):
        m, _, _, subj_id = self._setup()
        today = date.today()
        m.insert_attendance_record(subj_id, today, "Present")
        result = m.insert_attendance_record(subj_id, today, "Absent")
        assert not result

    def test_batch_insert(self):
        m, sid, sem_id, subj_id = self._setup()
        subj_id2 = m.create_subject(sem_id, "Math")
        today = date.today()
        records = [
            {"subject_id": subj_id,  "subject_name": "CS",   "date": today, "status": "Present"},
            {"subject_id": subj_id2, "subject_name": "Math", "date": today, "status": "Absent"},
        ]
        result = m.insert_attendance_batch(records)
        assert result["saved"] == 2
        assert len(result["skipped"]) == 0

    def test_batch_skips_duplicates(self):
        m, sid, sem_id, subj_id = self._setup()
        today = date.today()
        m.insert_attendance_record(subj_id, today, "Present")
        records = [
            {"subject_id": subj_id, "subject_name": "CS", "date": today, "status": "Absent"},
        ]
        result = m.insert_attendance_batch(records)
        assert result["saved"] == 0
        assert len(result["skipped"]) == 1

    def test_update_record(self):
        m, _, _, subj_id = self._setup()
        today = date.today()
        m.insert_attendance_record(subj_id, today, "Present")
        records = m.get_attendance(1, status_filter=None)
        rec_id = records[0]["id"]
        m.update_attendance_record(rec_id, "Absent")
        updated = m.get_attendance(1)
        assert updated[0]["status"] == "Absent"

    def test_delete_record(self):
        m, sid, sem_id, subj_id = self._setup()
        today = date.today()
        m.insert_attendance_record(subj_id, today, "Present")
        records = m.get_attendance(sid)
        rec_id = records[0]["id"]
        m.delete_attendance_record(rec_id)
        records_after = m.get_attendance(sid)
        assert len(records_after) == 0

    def test_subject_summary(self):
        m, sid, sem_id, subj_id = self._setup()
        today = date.today()
        yesterday = today - timedelta(days=1)
        m.insert_attendance_record(subj_id, today, "Present")
        m.insert_attendance_record(subj_id, yesterday, "Absent")
        summary = m.get_subject_summary(sem_id)
        assert len(summary) == 1
        assert summary[0]["present"] == 1
        assert summary[0]["absent"]  == 1

    def test_subject_has_records_true_after_insert(self):
        m, _, _, subj_id = self._setup()
        m.insert_attendance_record(subj_id, date.today(), "Present")
        assert m.subject_has_records(subj_id)

    def test_get_attendance_filters_by_status(self):
        m, sid, sem_id, subj_id = self._setup()
        today = date.today()
        yesterday = today - timedelta(days=1)
        m.insert_attendance_record(subj_id, today, "Present")
        m.insert_attendance_record(subj_id, yesterday, "Absent")

        present_only = m.get_attendance(sid, status_filter="Present")
        assert all(r["status"] == "Present" for r in present_only)
        assert len(present_only) == 1
