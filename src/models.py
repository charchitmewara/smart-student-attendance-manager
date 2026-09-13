"""
models.py — All database CRUD operations.

Every function accepts and returns plain Python dicts or lists of dicts.
UI and business logic layers never interact with the DB directly.

Parameterized queries are used throughout — no string interpolation of
user-supplied values into SQL statements.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from src.database import get_connection, placeholder

# Short alias used throughout this module
P = placeholder


# ===========================================================================
# STUDENTS
# ===========================================================================

def create_student(username: str, password_hash: str) -> int | None:
    """
    Insert a new student record.

    Returns the new student's id, or None if the username already exists.
    """
    sql = f"""
        INSERT INTO students (username, password_hash)
        VALUES ({P()}, {P()})
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (username, password_hash))
            # SQLite: lastrowid; psycopg2: use RETURNING
            if hasattr(cur, "lastrowid") and cur.lastrowid:
                return cur.lastrowid
            # PostgreSQL fallback
            cur.execute(f"SELECT id FROM students WHERE username = {P()}", (username,))
            row = cur.fetchone()
            return row[0] if row else None
    except Exception:
        return None


def get_student_by_username(username: str) -> dict | None:
    """Return the student row as a dict, or None if not found."""
    sql = f"SELECT * FROM students WHERE username = {P()}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (username,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_student_by_id(student_id: int) -> dict | None:
    """Return the student row as a dict, or None if not found."""
    sql = f"SELECT * FROM students WHERE id = {P()}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (student_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def update_student_profile(student_id: int, **fields: Any) -> bool:
    """
    Update one or more profile fields for a student.

    Accepted fields: name, student_id (as string), university,
                     course, semester, required_percentage
    """
    allowed = {"name", "student_id", "university", "course", "semester", "required_percentage"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False

    set_clause = ", ".join(f"{col} = {P()}" for col in updates)
    values = list(updates.values()) + [student_id]
    sql = f"UPDATE students SET {set_clause} WHERE id = {P()}"

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, values)
        return True


def update_student_password(student_id: int, new_hash: str) -> bool:
    """Update the password hash for a student."""
    sql = f"UPDATE students SET password_hash = {P()} WHERE id = {P()}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (new_hash, student_id))
        return True


# ===========================================================================
# SEMESTERS
# ===========================================================================

def create_semester(student_id: int, name: str) -> int | None:
    """
    Create a new semester for the student.

    Returns the new semester id, or None on failure.
    """
    sql = f"INSERT INTO semesters (student_id, name) VALUES ({P()}, {P()})"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (student_id, name))
            if hasattr(cur, "lastrowid") and cur.lastrowid:
                return cur.lastrowid
            cur.execute(
                f"SELECT id FROM semesters WHERE student_id = {P()} AND name = {P()}",
                (student_id, name),
            )
            row = cur.fetchone()
            return row[0] if row else None
    except Exception:
        return None


def get_semesters(student_id: int) -> list[dict]:
    """Return all semesters for a student, newest first."""
    sql = f"""
        SELECT * FROM semesters
        WHERE student_id = {P()}
        ORDER BY created_at DESC
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (student_id,))
        return [dict(r) for r in cur.fetchall()]


def get_active_semester(student_id: int) -> dict | None:
    """Return the active semester for a student, or None."""
    sql = f"""
        SELECT * FROM semesters
        WHERE student_id = {P()} AND is_active = 1
        ORDER BY created_at DESC
        LIMIT 1
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (student_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def set_active_semester(student_id: int, semester_id: int) -> bool:
    """Set a semester as active, deactivating all others for the student."""
    with get_connection() as conn:
        cur = conn.cursor()
        # Deactivate all
        cur.execute(
            f"UPDATE semesters SET is_active = 0 WHERE student_id = {P()}",
            (student_id,),
        )
        # Activate the chosen one
        cur.execute(
            f"UPDATE semesters SET is_active = 1 WHERE id = {P()} AND student_id = {P()}",
            (semester_id, student_id),
        )
        return True


def delete_semester(semester_id: int, student_id: int) -> bool:
    """Delete a semester and all its subjects/attendance (cascade)."""
    sql = f"DELETE FROM semesters WHERE id = {P()} AND student_id = {P()}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (semester_id, student_id))
        return True


# ===========================================================================
# SUBJECTS
# ===========================================================================

def create_subject(semester_id: int, name: str, code: str = "", threshold: float | None = None) -> int | None:
    """
    Create a subject in a semester.

    Returns the new subject id, or None if name already exists in that semester.
    """
    sql = f"""
        INSERT INTO subjects (semester_id, name, code, threshold)
        VALUES ({P()}, {P()}, {P()}, {P()})
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (semester_id, name, code, threshold))
            if hasattr(cur, "lastrowid") and cur.lastrowid:
                return cur.lastrowid
            cur.execute(
                f"SELECT id FROM subjects WHERE semester_id = {P()} AND name = {P()}",
                (semester_id, name),
            )
            row = cur.fetchone()
            return row[0] if row else None
    except Exception:
        return None


def get_subjects(semester_id: int, include_archived: bool = False) -> list[dict]:
    """
    Return subjects for a semester.

    By default excludes archived subjects.
    Pass include_archived=True to include them.
    """
    if include_archived:
        sql = f"SELECT * FROM subjects WHERE semester_id = {P()} ORDER BY name"
        params = (semester_id,)
    else:
        sql = f"SELECT * FROM subjects WHERE semester_id = {P()} AND is_archived = 0 ORDER BY name"
        params = (semester_id,)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def get_subject_by_id(subject_id: int) -> dict | None:
    """Return a single subject row."""
    sql = f"SELECT * FROM subjects WHERE id = {P()}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (subject_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def update_subject(subject_id: int, name: str, code: str, threshold: float | None) -> bool:
    """Update name, code, and threshold for a subject."""
    sql = f"""
        UPDATE subjects SET name = {P()}, code = {P()}, threshold = {P()}
        WHERE id = {P()}
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (name, code, threshold, subject_id))
        return True


def archive_subject(subject_id: int) -> bool:
    """Archive a subject (hide from entry; preserve history)."""
    sql = f"UPDATE subjects SET is_archived = 1 WHERE id = {P()}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (subject_id,))
        return True


def unarchive_subject(subject_id: int) -> bool:
    """Restore an archived subject to active status."""
    sql = f"UPDATE subjects SET is_archived = 0 WHERE id = {P()}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (subject_id,))
        return True


def delete_subject(subject_id: int) -> bool:
    """
    Permanently delete a subject and all its attendance records.

    Only call this after confirming the subject has no records, or
    when the user has explicitly confirmed irreversible deletion.
    """
    sql = f"DELETE FROM subjects WHERE id = {P()}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (subject_id,))
        return True


def subject_has_records(subject_id: int) -> bool:
    """Return True if any attendance records exist for this subject."""
    sql = f"SELECT COUNT(*) FROM attendance WHERE subject_id = {P()}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (subject_id,))
        count = cur.fetchone()[0]
        return count > 0


# ===========================================================================
# ATTENDANCE
# ===========================================================================

def attendance_exists(subject_id: int, record_date: date | str) -> bool:
    """Return True if a record already exists for subject + date."""
    sql = f"SELECT COUNT(*) FROM attendance WHERE subject_id = {P()} AND date = {P()}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (subject_id, str(record_date)))
        return cur.fetchone()[0] > 0


def insert_attendance_record(
    subject_id: int,
    record_date: date | str,
    status: str,
    session_num: int = 1,
) -> bool:
    """
    Insert a single attendance record.

    Returns True on success, False if a duplicate exists.
    """
    if attendance_exists(subject_id, record_date):
        return False

    sql = f"""
        INSERT INTO attendance (subject_id, date, status, session_num)
        VALUES ({P()}, {P()}, {P()}, {P()})
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (subject_id, str(record_date), status, session_num))
        return True


def insert_attendance_batch(records: list[dict]) -> dict:
    """
    Insert multiple attendance records in a single transaction.

    Each record dict must have keys: subject_id, date, status, session_num (optional).
    Returns a dict: {saved: int, skipped: list[str]}
    """
    saved = 0
    skipped = []

    with get_connection() as conn:
        cur = conn.cursor()
        for rec in records:
            subj_id = rec["subject_id"]
            rec_date = str(rec["date"])
            status = rec["status"]
            session_num = rec.get("session_num", 1)
            subj_name = rec.get("subject_name", f"Subject {subj_id}")

            # Check duplicate
            cur.execute(
                f"SELECT COUNT(*) FROM attendance WHERE subject_id = {P()} AND date = {P()}",
                (subj_id, rec_date),
            )
            if cur.fetchone()[0] > 0:
                skipped.append(f"{subj_name} (already recorded for {rec_date})")
                continue

            cur.execute(
                f"""
                INSERT INTO attendance (subject_id, date, status, session_num)
                VALUES ({P()}, {P()}, {P()}, {P()})
                """,
                (subj_id, rec_date, status, session_num),
            )
            saved += 1

    return {"saved": saved, "skipped": skipped}


def update_attendance_record(record_id: int, status: str) -> bool:
    """Update the status of an existing attendance record."""
    sql = f"UPDATE attendance SET status = {P()} WHERE id = {P()}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (status, record_id))
        return True


def delete_attendance_record(record_id: int) -> bool:
    """Permanently delete an attendance record."""
    sql = f"DELETE FROM attendance WHERE id = {P()}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (record_id,))
        return True


def get_attendance(
    student_id: int,
    semester_id: int | None = None,
    subject_ids: list[int] | None = None,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    status_filter: str | None = None,
) -> list[dict]:
    """
    Retrieve attendance records with optional filters.

    Returns a list of dicts with keys:
        id, subject_id, subject_name, semester_name, date, status, session_num, created_at
    """
    conditions = ["se.student_id = " + P()]
    params: list[Any] = [student_id]

    if semester_id:
        conditions.append("se.id = " + P())
        params.append(semester_id)

    if subject_ids:
        placeholders = ", ".join(P() for _ in subject_ids)
        conditions.append(f"su.id IN ({placeholders})")
        params.extend(subject_ids)

    if start_date:
        conditions.append("a.date >= " + P())
        params.append(str(start_date))

    if end_date:
        conditions.append("a.date <= " + P())
        params.append(str(end_date))

    if status_filter and status_filter != "All":
        conditions.append("a.status = " + P())
        params.append(status_filter)

    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT
            a.id,
            a.subject_id,
            su.name  AS subject_name,
            su.code  AS subject_code,
            se.name  AS semester_name,
            a.date,
            a.status,
            a.session_num,
            a.created_at
        FROM attendance a
        JOIN subjects  su ON a.subject_id = su.id
        JOIN semesters se ON su.semester_id = se.id
        WHERE {where_clause}
        ORDER BY a.date DESC, su.name
    """

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def get_subject_summary(semester_id: int) -> list[dict]:
    """
    Return per-subject attendance summary for a semester.

    Each dict contains:
        subject_id, subject_name, subject_code, threshold,
        total, present, absent, medical
    """
    sql = f"""
        SELECT
            su.id          AS subject_id,
            su.name        AS subject_name,
            su.code        AS subject_code,
            su.threshold   AS threshold,
            su.is_archived AS is_archived,
            COUNT(a.id)                                      AS total,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END)  AS present,
            SUM(CASE WHEN a.status = 'Absent'  THEN 1 ELSE 0 END)  AS absent,
            SUM(CASE WHEN a.status = 'Medical' THEN 1 ELSE 0 END)  AS medical
        FROM subjects su
        LEFT JOIN attendance a ON su.id = a.subject_id
        WHERE su.semester_id = {P()}
        GROUP BY su.id, su.name, su.code, su.threshold, su.is_archived
        ORDER BY su.name
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (semester_id,))
        return [dict(r) for r in cur.fetchall()]


def get_monthly_summary(student_id: int, year: int, month: int) -> list[dict]:
    """
    Return per-subject attendance summary for a specific month.
    """
    month_str = f"{year:04d}-{month:02d}"
    sql = f"""
        SELECT
            su.name AS subject_name,
            su.code AS subject_code,
            COUNT(a.id) AS total,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present,
            SUM(CASE WHEN a.status = 'Absent'  THEN 1 ELSE 0 END) AS absent,
            SUM(CASE WHEN a.status = 'Medical' THEN 1 ELSE 0 END) AS medical
        FROM attendance a
        JOIN subjects  su ON a.subject_id = su.id
        JOIN semesters se ON su.semester_id = se.id
        WHERE se.student_id = {P()}
          AND strftime('%Y-%m', a.date) = {P()}
        GROUP BY su.id, su.name, su.code
        ORDER BY su.name
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (student_id, month_str))
        return [dict(r) for r in cur.fetchall()]


def get_attendance_trend(student_id: int, semester_id: int | None = None) -> list[dict]:
    """
    Return daily attendance counts (present/absent/medical) for trend charts.
    """
    conditions = ["se.student_id = " + P()]
    params: list[Any] = [student_id]

    if semester_id:
        conditions.append("se.id = " + P())
        params.append(semester_id)

    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT
            a.date,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present,
            SUM(CASE WHEN a.status = 'Absent'  THEN 1 ELSE 0 END) AS absent,
            SUM(CASE WHEN a.status = 'Medical' THEN 1 ELSE 0 END) AS medical
        FROM attendance a
        JOIN subjects  su ON a.subject_id = su.id
        JOIN semesters se ON su.semester_id = se.id
        WHERE {where_clause}
        GROUP BY a.date
        ORDER BY a.date
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
