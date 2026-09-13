"""
pages/2_Subjects.py — Semester and subject management.

Students can:
  - Create and activate semesters
  - Add subjects with optional custom thresholds
  - Archive subjects that have records
  - Delete subjects with zero records
"""

import streamlit as st

st.set_page_config(
    page_title="Subjects — Smart Attendance",
    page_icon="📚",
    layout="wide",
)

from src.auth import require_auth
from src.ui import inject_custom_css, render_sidebar
from src.validation import validate_semester_name, validate_subject_name, validate_subject_code, validate_threshold
from src import models

inject_custom_css()
student = require_auth()
render_sidebar()

st.title("📚 Subjects & Semesters")

sid = student["id"]
student_threshold = student.get("required_percentage") or 75.0

# ===========================================================================
# SEMESTERS SECTION
# ===========================================================================

st.markdown("## Semesters")

semesters = models.get_semesters(sid)
active_sem = models.get_active_semester(sid)

# ── list existing semesters ────────────────────────────────────────────────
if semesters:
    for sem in semesters:
        is_active = (active_sem and sem["id"] == active_sem["id"])
        badge = " 🟢 **Active**" if is_active else ""
        with st.container():
            col_name, col_set, col_del = st.columns([4, 2, 2])
            col_name.markdown(f"**{sem['name']}**{badge}")
            if not is_active:
                if col_set.button("Set Active", key=f"set_active_{sem['id']}"):
                    models.set_active_semester(sid, sem["id"])
                    st.success(f"'{sem['name']}' is now the active semester.")
                    st.rerun()
            # Only allow deleting if the student explicitly wants to remove it
            if col_del.button("🗑️ Delete", key=f"del_sem_{sem['id']}"):
                st.session_state[f"confirm_del_sem_{sem['id']}"] = True

            if st.session_state.get(f"confirm_del_sem_{sem['id']}"):
                st.error(
                    f"⚠️ Delete **{sem['name']}**? This will permanently remove all subjects "
                    "and attendance records in this semester. This cannot be undone."
                )
                c1, c2 = st.columns(2)
                if c1.button("Yes, delete", key=f"yes_del_sem_{sem['id']}", type="primary"):
                    models.delete_semester(sem["id"], sid)
                    st.session_state.pop(f"confirm_del_sem_{sem['id']}", None)
                    st.success("Semester deleted.")
                    st.rerun()
                if c2.button("Cancel", key=f"no_del_sem_{sem['id']}"):
                    st.session_state.pop(f"confirm_del_sem_{sem['id']}", None)
                    st.rerun()
    st.markdown("---")
else:
    st.info("No semesters yet. Create your first semester below.")

# ── create new semester ────────────────────────────────────────────────────
with st.expander("➕ Create New Semester", expanded=not bool(semesters)):
    with st.form("create_semester_form"):
        sem_name   = st.text_input("Semester Name", placeholder='e.g. "Semester 3 — 2024"')
        set_active = st.checkbox("Set as active semester immediately", value=True)
        submitted  = st.form_submit_button("Create Semester", type="primary")

    if submitted:
        ok, msg = validate_semester_name(sem_name)
        if not ok:
            st.error(msg)
        else:
            new_id = models.create_semester(sid, sem_name.strip())
            if new_id is None:
                st.error("Failed to create semester. It may already exist.")
            else:
                if set_active:
                    models.set_active_semester(sid, new_id)
                st.success(f"Semester '{sem_name.strip()}' created.")
                st.rerun()

# ===========================================================================
# SUBJECTS SECTION
# ===========================================================================

st.markdown("## Subjects")

if not active_sem:
    st.warning("No active semester. Create or activate a semester above to manage subjects.")
    st.stop()

st.markdown(f"Showing subjects for **{active_sem['name']}**")

subjects_all = models.get_subjects(active_sem["id"], include_archived=True)
active_subjs = [s for s in subjects_all if not s["is_archived"]]
archived_subjs = [s for s in subjects_all if s["is_archived"]]

# ── active subjects list ───────────────────────────────────────────────────
if active_subjs:
    for subj in active_subjs:
        has_records = models.subject_has_records(subj["id"])
        thr = subj["threshold"]
        thr_display = f"{thr}%" if thr is not None else f"Default ({student_threshold}%)"

        with st.container():
            col_info, col_edit, col_action = st.columns([4, 2, 2])
            col_info.markdown(
                f"**{subj['name']}** "
                f"{'`' + subj['code'] + '`' if subj['code'] else ''}"
                f"  — Threshold: {thr_display}"
            )

            if col_edit.button("✏️ Edit", key=f"edit_{subj['id']}"):
                st.session_state[f"editing_{subj['id']}"] = True

            if has_records:
                if col_action.button("📦 Archive", key=f"arch_{subj['id']}"):
                    models.archive_subject(subj["id"])
                    st.success(f"'{subj['name']}' archived. History is preserved.")
                    st.rerun()
            else:
                if col_action.button("🗑️ Delete", key=f"del_{subj['id']}"):
                    st.session_state[f"confirm_del_{subj['id']}"] = True

            # Edit inline form
            if st.session_state.get(f"editing_{subj['id']}"):
                with st.form(f"edit_form_{subj['id']}"):
                    new_name = st.text_input("Subject Name", value=subj["name"])
                    new_code = st.text_input("Subject Code", value=subj["code"] or "")
                    new_thr  = st.number_input(
                        "Custom Threshold % (blank = use global default)",
                        min_value=0.0, max_value=100.0,
                        value=float(subj["threshold"]) if subj["threshold"] else 0.0,
                        step=0.5,
                    )
                    save_edit = st.form_submit_button("Save Changes", type="primary")
                    cancel_edit = st.form_submit_button("Cancel")

                if save_edit:
                    ok, msg = validate_subject_name(new_name)
                    if not ok:
                        st.error(msg)
                    else:
                        thr_val = float(new_thr) if new_thr > 0 else None
                        models.update_subject(subj["id"], new_name.strip(), new_code.strip(), thr_val)
                        st.session_state.pop(f"editing_{subj['id']}", None)
                        st.success("Subject updated.")
                        st.rerun()
                if cancel_edit:
                    st.session_state.pop(f"editing_{subj['id']}", None)
                    st.rerun()

            # Delete confirmation
            if st.session_state.get(f"confirm_del_{subj['id']}"):
                st.warning(f"Delete **{subj['name']}**? This cannot be undone.")
                c1, c2 = st.columns(2)
                if c1.button("Yes, delete", key=f"yes_del_{subj['id']}", type="primary"):
                    models.delete_subject(subj["id"])
                    st.session_state.pop(f"confirm_del_{subj['id']}", None)
                    st.success(f"'{subj['name']}' deleted.")
                    st.rerun()
                if c2.button("Cancel", key=f"no_del_{subj['id']}"):
                    st.session_state.pop(f"confirm_del_{subj['id']}", None)
                    st.rerun()

        st.markdown("---")
else:
    st.info("No subjects added yet for this semester. Add your first subject below.")

# ── add subject form ───────────────────────────────────────────────────────
with st.expander("➕ Add New Subject", expanded=not bool(active_subjs)):
    with st.form("add_subject_form"):
        subj_name = st.text_input("Subject Name *", placeholder="e.g. Data Structures")
        subj_code = st.text_input("Subject Code (optional)", placeholder="e.g. CS201")
        custom_thr = st.number_input(
            "Custom Threshold % (leave 0 to use your global default)",
            min_value=0.0, max_value=100.0, value=0.0, step=0.5,
            help=f"Your global default is {student_threshold}%. Enter 0 to inherit it.",
        )
        add_btn = st.form_submit_button("Add Subject", type="primary")

    if add_btn:
        ok, msg = validate_subject_name(subj_name)
        if not ok:
            st.error(msg)
        else:
            ok2, msg2 = validate_subject_code(subj_code)
            if not ok2:
                st.error(msg2)
            else:
                thr_val = float(custom_thr) if custom_thr > 0 else None
                new_id = models.create_subject(
                    active_sem["id"],
                    subj_name.strip(),
                    subj_code.strip(),
                    thr_val,
                )
                if new_id is None:
                    st.error(f"'{subj_name}' already exists in this semester.")
                else:
                    st.success(f"Subject '{subj_name.strip()}' added.")
                    st.rerun()

# ── archived subjects ──────────────────────────────────────────────────────
if archived_subjs:
    with st.expander(f"📦 Archived Subjects ({len(archived_subjs)})", expanded=False):
        for subj in archived_subjs:
            col1, col2 = st.columns([4, 2])
            col1.markdown(f"~~{subj['name']}~~ {'`' + subj['code'] + '`' if subj['code'] else ''}")
            if col2.button("♻️ Restore", key=f"restore_{subj['id']}"):
                models.unarchive_subject(subj["id"])
                st.success(f"'{subj['name']}' restored.")
                st.rerun()
