"""
pages/1_Dashboard.py — Main student dashboard.

Displays: KPI cards, overall status, per-subject table, charts,
          advisory messages.
"""

import streamlit as st

st.set_page_config(
    page_title="Dashboard — Smart Attendance",
    page_icon="🏠",
    layout="wide",
)

from src.auth import require_auth
from src.ui import inject_custom_css, render_sidebar, semester_selector, render_status_badge, no_data_placeholder
from src.services import get_dashboard_data
from src.analytics import subject_bar_chart, present_absent_pie, attendance_trend_chart
from src import models

inject_custom_css()
student = require_auth()
render_sidebar()

st.title("🏠 Dashboard")

# ── semester selector (view mode, independent of active semester) ──────────
sem = semester_selector(student["id"], key="dash_semester")
if not sem:
    st.stop()

threshold = student.get("required_percentage") or 75.0

# ── load data ──────────────────────────────────────────────────────────────
data = get_dashboard_data(student["id"], sem["id"], threshold)
subject_stats = data["subject_stats"]

# ── KPI cards ──────────────────────────────────────────────────────────────
st.markdown("### 📊 Overview")

col1, col2, col3, col4, col5 = st.columns(5)
pct_display = f"{data['overall_pct']:.1f}%" if data["overall_pct"] is not None else "N/A"

with col1:
    st.metric("Overall Attendance", pct_display)
with col2:
    st.metric("Total Classes", data["total_classes"])
with col3:
    st.metric("✅ Present", data["total_present"])
with col4:
    st.metric("❌ Absent", data["total_absent"])
with col5:
    st.metric("📚 Subjects", data["num_subjects"])

# ── status badge ──────────────────────────────────────────────────────────
st.markdown("**Attendance Status:**", unsafe_allow_html=False)
render_status_badge(data["overall_status"])
st.markdown("")

# ── progress bar ──────────────────────────────────────────────────────────
if data["overall_pct"] is not None:
    progress_val = min(data["overall_pct"] / 100.0, 1.0)
    st.progress(progress_val, text=f"Overall: {pct_display}  (Required: {threshold}%)")

# ── advisory message ──────────────────────────────────────────────────────
st.markdown("---")
if data["overall_pct"] is None:
    st.info("No attendance recorded yet. Go to **📝 Mark Attendance** to get started.")
elif data["overall_pct"] < threshold:
    needed = data["needs_to_attend"]
    if needed is not None and needed > 0:
        st.warning(
            f"⚠️ Your overall attendance is **{pct_display}** — below the required **{threshold}%**. "
            f"You need to attend the next **{needed}** consecutive class(es) to reach your target."
        )
    else:
        st.warning(f"⚠️ Your attendance is **{pct_display}** — below the required **{threshold}%**.")
else:
    can_miss = data["can_miss"]
    if can_miss > 0:
        st.success(
            f"✅ Your attendance is **{pct_display}** — you are on track! "
            f"You can afford to miss up to **{can_miss}** more class(es) while staying above {threshold}%."
        )
    else:
        st.info(f"✅ Attendance is **{pct_display}** — you are exactly at the threshold. Do not miss any classes.")

# ── per-subject table ──────────────────────────────────────────────────────
st.markdown("### 📋 Subject-wise Summary")

active_subjects = [s for s in subject_stats if not s["is_archived"]]
archived_subjects = [s for s in subject_stats if s["is_archived"]]

if not active_subjects:
    no_data_placeholder("No subjects found for this semester.")
else:
    import pandas as pd
    from src.calculations import status_color

    rows = []
    for s in active_subjects:
        pct = f"{s['percentage']:.1f}%" if s["percentage"] is not None else "N/A"
        rows.append({
            "Subject":    s["subject_name"],
            "Code":       s["subject_code"],
            "Total":      s["total"],
            "Present":    s["present"],
            "Absent":     s["absent"],
            "Medical":    s["medical"],
            "Attendance": pct,
            "Status":     s["status"],
            "Threshold":  f"{s['threshold']}%",
        })

    df = pd.DataFrame(rows)

    def highlight_row(row):
        """Color rows red if below threshold, green if excellent."""
        status = row["Status"]
        if status in ("Critical", "Warning"):
            return ["background-color: #FEF2F2; color: #1E293B"] * len(row)
        if status == "Excellent":
            return ["background-color: #F0FDF4; color: #1E293B"] * len(row)
        return [""] * len(row)

    styled = df.style.apply(highlight_row, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # ── per-subject advisory details ──────────────────────────────────────
    at_risk = [s for s in active_subjects if s["percentage"] is not None and s["percentage"] < s["threshold"]]
    if at_risk:
        st.markdown("#### ⚠️ Subjects Needing Attention")
        for s in at_risk:
            needed = s["needs_to_attend"]
            pct = f"{s['percentage']:.1f}%"
            msg = f"**{s['subject_name']}** — {pct} (need {s['threshold']}%)"
            if needed and needed > 0:
                msg += f" · Attend next **{needed}** class(es) consecutively to recover."
            st.warning(msg)

# ── charts ────────────────────────────────────────────────────────────────
if active_subjects:
    st.markdown("---")
    st.markdown("### 📈 Visualizations")

    col_a, col_b = st.columns(2)

    with col_a:
        fig_bar = subject_bar_chart(active_subjects, threshold)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_b:
        fig_pie = present_absent_pie(
            data["total_present"],
            data["total_absent"],
            data["total_medical"],
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # Trend chart (full width)
    trend = models.get_attendance_trend(student["id"], sem["id"])
    if trend:
        fig_trend = attendance_trend_chart(trend)
        st.plotly_chart(fig_trend, use_container_width=True)

# ── archived subjects (collapsible) ───────────────────────────────────────
if archived_subjects:
    with st.expander(f"📦 Archived Subjects ({len(archived_subjects)})", expanded=False):
        for s in archived_subjects:
            pct = f"{s['percentage']:.1f}%" if s["percentage"] is not None else "N/A"
            st.markdown(f"- **{s['subject_name']}** — {pct} (archived)")
