"""
pages/4_Attendance_History.py — Read-only attendance history with filters,
edit, delete, and CSV export.
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta

st.set_page_config(
    page_title="History — Smart Attendance",
    page_icon="📅",
    layout="wide",
)

from src.auth import require_auth
from src.ui import inject_custom_css, render_sidebar, semester_selector, no_data_placeholder
from src.export import attendance_to_csv, export_filename
from src import models

inject_custom_css()
student = require_auth()
render_sidebar()

st.title("📅 Attendance History")

sid = student["id"]

# ── semester selector ──────────────────────────────────────────────────────
sem = semester_selector(sid, key="hist_semester")
if not sem:
    st.stop()

# ── filters ───────────────────────────────────────────────────────────────
with st.expander("🔍 Filters", expanded=True):
    col1, col2, col3 = st.columns([2, 2, 2])

    # Subject multi-select
    subjects = models.get_subjects(sem["id"], include_archived=True)
    subject_map = {s["name"]: s["id"] for s in subjects}
    with col1:
        selected_subjects = st.multiselect(
            "Filter by Subject",
            options=list(subject_map.keys()),
            default=[],
            placeholder="All subjects",
        )

    # Date range
    with col2:
        start_date = st.date_input(
            "From Date",
            value=date.today() - timedelta(days=30),
            max_value=date.today(),
        )
    with col3:
        end_date = st.date_input(
            "To Date",
            value=date.today(),
            max_value=date.today(),
        )

    status_filter = st.radio(
        "Status Filter",
        options=["All", "Present", "Absent", "Medical"],
        horizontal=True,
    )

# ── fetch records ──────────────────────────────────────────────────────────
subject_ids = [subject_map[n] for n in selected_subjects] if selected_subjects else None

records = models.get_attendance(
    student_id=sid,
    semester_id=sem["id"],
    subject_ids=subject_ids,
    start_date=start_date,
    end_date=end_date,
    status_filter=status_filter if status_filter != "All" else None,
)

st.markdown(f"**{len(records)}** record(s) found")

# ── export button ──────────────────────────────────────────────────────────
if records:
    csv_bytes = attendance_to_csv(records)
    st.download_button(
        label="📥 Export CSV",
        data=csv_bytes,
        file_name=export_filename("attendance_history"),
        mime="text/csv",
    )

# ── records table ──────────────────────────────────────────────────────────
if not records:
    no_data_placeholder("No records match the selected filters.")
else:
    df = pd.DataFrame(records)
    display_cols = {
        "date":         "Date",
        "subject_name": "Subject",
        "subject_code": "Code",
        "semester_name":"Semester",
        "status":       "Status",
        "session_num":  "Session",
    }
    df_display = df[[c for c in display_cols if c in df.columns]].rename(columns=display_cols)

    def color_status(val):
        colors = {"Present": "#22C55E", "Absent": "#EF4444", "Medical": "#F59E0B"}
        color = colors.get(val, "#94A3B8")
        return f"color: {color}; font-weight: 600"

    styled = df_display.style.map(color_status, subset=["Status"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # ── edit / delete section ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### ✏️ Edit or Delete a Record")
    st.caption(
        "Select a record to edit its status or delete it. "
        "Deleting is permanent and will update all calculations."
    )

    record_options = {
        f"{r['date']} — {r['subject_name']} — {r['status']}": r["id"]
        for r in records
    }

    chosen_label = st.selectbox(
        "Select a record",
        options=list(record_options.keys()),
        index=0,
    )
    chosen_id = record_options[chosen_label]

    col_edit, col_del = st.columns(2)

    with col_edit:
        st.markdown("**Edit Status**")
        new_status = st.radio(
            "New Status",
            options=["Present", "Absent", "Medical"],
            key="edit_status_radio",
            horizontal=True,
        )
        if st.button("💾 Update", type="primary"):
            models.update_attendance_record(chosen_id, new_status)
            st.success("Record updated.")
            st.rerun()

    with col_del:
        st.markdown("**Delete Record**")
        st.warning("⚠️ Deletion is permanent and cannot be undone.")
        if st.button("🗑️ Delete This Record", type="secondary"):
            st.session_state["confirm_del_record"] = chosen_id

    if st.session_state.get("confirm_del_record") == chosen_id:
        st.error(f"Confirm: permanently delete **{chosen_label}**?")
        c1, c2 = st.columns(2)
        if c1.button("Yes, delete", type="primary"):
            models.delete_attendance_record(chosen_id)
            st.session_state.pop("confirm_del_record", None)
            st.success("Record deleted.")
            st.rerun()
        if c2.button("Cancel"):
            st.session_state.pop("confirm_del_record", None)
            st.rerun()
