"""
sample_data.py — Demo data seeder.

Callable from the Settings page via "Load Demo Data".
Never runs on import.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from src import models


DEMO_SEMESTER_NAME = "Demo Semester — 2024"

DEMO_SUBJECTS = [
    {"name": "Mathematics",        "code": "MAT101", "threshold": None},
    {"name": "Physics",            "code": "PHY102", "threshold": None},
    {"name": "Chemistry",          "code": "CHE103", "threshold": None},
    {"name": "Computer Science",   "code": "CS104",  "threshold": None},
    {"name": "English",            "code": "ENG105", "threshold": 65.0},   # custom lower threshold
    {"name": "Data Structures",    "code": "CS201",  "threshold": 80.0},   # custom higher threshold
]

# Target attendance rates per subject — some above threshold, some below
_TARGET_RATES = {
    "Mathematics":      0.90,
    "Physics":          0.72,   # below default 75%
    "Chemistry":        0.88,
    "Computer Science": 0.95,
    "English":          0.68,   # above custom 65% threshold
    "Data Structures":  0.74,   # below custom 80% threshold
}


def _demo_semester_exists(student_id: int) -> bool:
    """Return True if the demo semester already exists for this student."""
    semesters = models.get_semesters(student_id)
    return any(s["name"] == DEMO_SEMESTER_NAME for s in semesters)


def _get_demo_semester_id(student_id: int) -> int | None:
    """Return the id of the demo semester if it exists."""
    semesters = models.get_semesters(student_id)
    for s in semesters:
        if s["name"] == DEMO_SEMESTER_NAME:
            return s["id"]
    return None


def seed_demo_data(student_id: int, overwrite: bool = False) -> dict:
    """
    Create a demo semester with 6 subjects and 60 days of attendance records.

    Parameters
    ----------
    student_id : int
        The student to seed data for.
    overwrite : bool
        If True and demo data already exists, delete it and recreate.
        If False and demo data already exists, return early with a message.

    Returns
    -------
    dict with keys: success (bool), message (str), semester_id (int|None),
                    subjects_created (int), records_created (int)
    """
    if _demo_semester_exists(student_id):
        if not overwrite:
            return {
                "success": False,
                "message": f'Demo data already exists ("{DEMO_SEMESTER_NAME}").',
                "semester_id": _get_demo_semester_id(student_id),
                "subjects_created": 0,
                "records_created":  0,
            }
        # Delete existing demo semester (CASCADE deletes subjects + attendance)
        existing_id = _get_demo_semester_id(student_id)
        if existing_id:
            models.delete_semester(existing_id, student_id)

    # Create semester
    semester_id = models.create_semester(student_id, DEMO_SEMESTER_NAME)
    if not semester_id:
        return {
            "success": False,
            "message": "Failed to create demo semester.",
            "semester_id": None,
            "subjects_created": 0,
            "records_created":  0,
        }

    # Create subjects
    subject_map = {}
    for subj in DEMO_SUBJECTS:
        sid = models.create_subject(
            semester_id,
            subj["name"],
            subj["code"],
            subj["threshold"],
        )
        if sid:
            subject_map[subj["name"]] = sid

    # Generate 60 days of records ending yesterday
    end_date   = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=59)

    records = []
    current = start_date
    random.seed(42)  # reproducible demo data

    while current <= end_date:
        # Skip weekends (universities rarely have classes)
        if current.weekday() < 5:  # Monday=0 … Friday=4
            for name, sid in subject_map.items():
                rate = _TARGET_RATES.get(name, 0.80)
                roll = random.random()
                if roll < rate:
                    status = "Present"
                elif roll < rate + 0.05:
                    status = "Medical"
                else:
                    status = "Absent"
                records.append({
                    "subject_id":   sid,
                    "subject_name": name,
                    "date":         current,
                    "status":       status,
                })
        current += timedelta(days=1)

    result = models.insert_attendance_batch(records)

    return {
        "success":          True,
        "message":          f'Demo data loaded: {result["saved"]} attendance records across {len(subject_map)} subjects.',
        "semester_id":      semester_id,
        "subjects_created": len(subject_map),
        "records_created":  result["saved"],
    }
