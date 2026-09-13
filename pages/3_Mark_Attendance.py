"""
pages/3_Mark_Attendance.py — Daily attendance entry.

Student selects a date, number of classes, and for each class:
assigns a subject and marks Present / Absent / Medical Leave.
"""

import streamlit as st
from datetime import date

st.set_page_config(
    page_title="Mark Attendance — Smart Attendance",
    page_icon="📝",
    layout="wide",
)

from src.auth import require_auth
from src.ui import inject_custom_css, render_sidebar
from src.validation import validate_attendance_date, validate_class_count, validate_attendance_row
from src import models

inject_custom_css()
student = require_auth()
render_sidebar()

st.title("📝 Mark Attendance")

sid = student["id"]

# ── active semester guard ──────────────────────────────────────────────────
active_sem = models.get_active_semester(sid)
if not active_sem:
    st.warning("No active semester found. Please go to **📚 Subjects** to create and activate a semester first.")
    st.stop()

# ── non-archived subjects for this semester ────────────────────────────────
subjects = models.get_subjects(active_sem["id"], include_archived=False)
if not subjects:
    st.warning(
        f"No subjects found in **{active_sem['name']}**. "
        "Please go to **📚 Subjects** to add subjects first."
    )
    st.stop()

subject_map = {s["name"]: s["id"] for s in subjects}
subject_names = list(subject_map.keys())

st.markdown(f"Active semester: **{active_sem['name']}**")

# ── date and class count ───────────────────────────────────────────────────
col_date, col_count = st.columns([2, 1])
with col_date:
    chosen_date = st.date_input(
        "Attendance Date",
        value=date.today(),
        max_value=date.today(),
        help="You cannot mark attendance for a future date.",
    )
with col_count:
    class_count = st.number_input(
        "Number of Classes Today",
        min_value=1, max_value=20, value=1, step=1,
    )

# ── validate date ──────────────────────────────────────────────────────────
ok_date, msg_date = validate_attendance_date(chosen_date)
if not ok_date:
    st.error(msg_date)
    st.stop()

st.markdown("---")
st.markdown("### Mark each class")
st.caption(
    "Select the subject for each class slot and mark the attendance status. "
    "If a subject already has a record for this date it will be skipped automatically."
)

STATUS_OPTIONS = ["Present", "Absent", "Medical Leave"]

# ── build dynamic rows using session state ─────────────────────────────────
# Store selections in session state so changing class_count doesn't reset them
if "mark_rows" not in st.session_state or len(st.session_state.mark_rows) != class_count:
    st.session_state.mark_rows = [
        {"subject": subject_names[0], "status": "Present"}
        for _ in range(int(class_count))
    ]

# Keep length in sync
while len(st.session_state.mark_rows) < class_count:
    st.session_state.mark_rows.append({"subject": subject_names[0], "status": "Present"})
while len(st.session_state.mark_rows) > class_count:
    st.session_state.mark_rows.pop()

for i in range(int(class_count)):
    col_cls, col_subj, col_status = st.columns([1, 3, 2])
    col_cls.markdown(f"**Class {i+1}**")

    chosen_subj = col_subj.selectbox(
        "Subject",
        options=subject_names,
        index=subject_names.index(st.session_state.mark_rows[i]["subject"])
               if st.session_state.mark_rows[i]["subject"] in subject_names else 0,
        key=f"subj_{i}",
        label_visibility="collapsed",
    )
    chosen_status = col_status.radio(
        "Status",
        options=STATUS_OPTIONS,
        index=STATUS_OPTIONS.index(st.session_state.mark_rows[i]["status"])
               if st.session_state.mark_rows[i]["status"] in STATUS_OPTIONS else 0,
        key=f"status_{i}",
        horizontal=True,
        label_visibility="collapsed",
    )

    st.session_state.mark_rows[i]["subject"] = chosen_subj
    st.session_state.mark_rows[i]["status"]  = chosen_status

# ── submit ─────────────────────────────────────────────────────────────────
st.markdown("---")
if st.button("💾 Save Attendance", type="primary", use_container_width=False):
    # Build records list (normalize "Medical Leave" → "Medical")
    records_to_insert = []
    validation_errors = []

    for i, row in enumerate(st.session_state.mark_rows):
        subj_name = row["subject"]
        raw_status = row["status"]
        db_status = "Medical" if raw_status == "Medical Leave" else raw_status

        subj_id = subject_map.get(subj_name)
        ok, msg = validate_attendance_row(subj_id, chosen_date, db_status)
        if not ok:
            validation_errors.append(f"Class {i+1}: {msg}")
            continue

        records_to_insert.append({
            "subject_id":   subj_id,
            "subject_name": subj_name,
            "date":         chosen_date,
            "status":       db_status,
            "session_num":  i + 1,
        })

    if validation_errors:
        for err in validation_errors:
            st.error(err)
    else:
        result = models.insert_attendance_batch(records_to_insert)
        saved   = result["saved"]
        skipped = result["skipped"]

        if saved:
            st.success(f"✅ Saved {saved} attendance record(s) for {chosen_date}.")

        if skipped:
            for skip_msg in skipped:
                st.warning(f"⏭️ Skipped: {skip_msg}")

        if saved:
            # Reset rows after successful save
            st.session_state.mark_rows = [
                {"subject": subject_names[0], "status": "Present"}
                for _ in range(int(class_count))
            ]
            st.rerun()
