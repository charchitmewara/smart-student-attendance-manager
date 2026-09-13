"""
pages/5_Analytics.py — Attendance analytics, monthly reports, and charts.
"""

import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(
    page_title="Analytics — Smart Attendance",
    page_icon="📊",
    layout="wide",
)

from src.auth import require_auth
from src.ui import inject_custom_css, render_sidebar, semester_selector, no_data_placeholder
from src.analytics import (
    subject_bar_chart, present_absent_pie,
    attendance_trend_chart, daily_attendance_bar, monthly_bar_chart,
)
from src.services import get_subject_stats, get_dashboard_data
from src.calculations import attendance_percentage
from src.export import subject_stats_to_csv, export_filename
from src.pdf_report import generate_attendance_pdf
from src import models

inject_custom_css()
student = require_auth()
render_sidebar()

st.title("📊 Analytics")

sid = student["id"]
threshold = student.get("required_percentage") or 75.0

# ── semester selector ──────────────────────────────────────────────────────
sem = semester_selector(sid, key="analytics_semester")
if not sem:
    st.stop()

tab_overview, tab_monthly, tab_trend = st.tabs(["📈 Overview", "📅 Monthly Report", "📉 Trend"])

# ===========================================================================
# TAB 1: OVERVIEW
# ===========================================================================
with tab_overview:
    subject_stats = get_subject_stats(sem["id"], threshold)
    active_subjects = [s for s in subject_stats if not s["is_archived"]]

    if not active_subjects:
        no_data_placeholder("No attendance data for this semester yet.")
    else:
        total_present = sum(s["present"] for s in active_subjects)
        total_absent  = sum(s["absent"]  for s in active_subjects)
        total_medical = sum(s["medical"] for s in active_subjects)
        overall_pct   = attendance_percentage(total_present, total_absent)

        # ── summary metrics ────────────────────────────────────────────────
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Overall Attendance", f"{overall_pct:.1f}%" if overall_pct else "N/A")
        col2.metric("Total Present",  total_present)
        col3.metric("Total Absent",   total_absent)
        col4.metric("Medical Leave",  total_medical)

        # ── charts ────────────────────────────────────────────────────────
        col_a, col_b = st.columns(2)
        with col_a:
            fig_bar = subject_bar_chart(active_subjects, threshold)
            st.plotly_chart(fig_bar, use_container_width=True)
        with col_b:
            fig_pie = present_absent_pie(total_present, total_absent, total_medical)
            st.plotly_chart(fig_pie, use_container_width=True)

        # ── daily bar ─────────────────────────────────────────────────────
        trend_data = models.get_attendance_trend(sid, sem["id"])
        if trend_data:
            fig_daily = daily_attendance_bar(trend_data)
            st.plotly_chart(fig_daily, use_container_width=True)

        # ── subject stats table ───────────────────────────────────────────
        st.markdown("### Subject Statistics")
        rows = []
        for s in active_subjects:
            pct = s["percentage"]
            rows.append({
                "Subject":   s["subject_name"],
                "Code":      s["subject_code"],
                "Total":     s["total"],
                "Present":   s["present"],
                "Absent":    s["absent"],
                "Medical":   s["medical"],
                "% Attended": f"{pct:.1f}%" if pct is not None else "N/A",
                "Status":    s["status"],
                "Threshold": f"{s['threshold']}%",
                "Can Miss":  s["can_miss"],
                "Need":      s["needs_to_attend"] if s["needs_to_attend"] else "—",
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # ── Export buttons ────────────────────────────────────────────────
        col_csv, col_pdf = st.columns(2)

        csv = subject_stats_to_csv(active_subjects)
        col_csv.download_button(
            "📥 Export Subject Stats (CSV)",
            data=csv,
            file_name=export_filename("subject_stats"),
            mime="text/csv",
        )

        # PDF report
        if col_pdf.button("📄 Download PDF Report"):
            with st.spinner("Generating PDF..."):
                try:
                    dash_data = get_dashboard_data(student["id"], sem["id"],
                                                   student.get("required_percentage") or 75.0)
                    pdf_bytes = generate_attendance_pdf(
                        student       = student,
                        semester_name = sem["name"],
                        subject_stats = active_subjects,
                        dashboard_data= dash_data,
                    )
                    st.download_button(
                        label     = "⬇️ Click here to save the PDF",
                        data      = pdf_bytes,
                        file_name = export_filename("smart_attendance"),
                        mime      = "application/pdf",
                        key       = "pdf_download_btn",
                    )
                except Exception as e:
                    st.error(f"PDF generation failed: {e}")


# ===========================================================================
# TAB 2: MONTHLY REPORT
# ===========================================================================
with tab_monthly:
    col_yr, col_mo = st.columns(2)
    with col_yr:
        selected_year = st.selectbox("Year", options=list(range(date.today().year, date.today().year - 5, -1)))
    with col_mo:
        selected_month = st.selectbox(
            "Month",
            options=list(range(1, 13)),
            format_func=lambda m: date(2000, m, 1).strftime("%B"),
            index=date.today().month - 1,
        )

    monthly_data = models.get_monthly_summary(sid, selected_year, selected_month)

    if not monthly_data:
        no_data_placeholder(f"No attendance records for {date(selected_year, selected_month, 1).strftime('%B %Y')}.")
    else:
        month_label = date(selected_year, selected_month, 1).strftime("%B %Y")
        st.markdown(f"### {month_label} Summary")

        total_p = sum(r["present"] for r in monthly_data)
        total_a = sum(r["absent"]  for r in monthly_data)
        total_m = sum(r["medical"] for r in monthly_data)
        pct     = attendance_percentage(total_p, total_a)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Attendance %", f"{pct:.1f}%" if pct else "N/A")
        col2.metric("Present",  total_p)
        col3.metric("Absent",   total_a)
        col4.metric("Medical",  total_m)

        # Monthly bar chart
        fig_month = monthly_bar_chart(monthly_data)
        st.plotly_chart(fig_month, use_container_width=True)

        # Per-subject table
        rows = []
        for r in monthly_data:
            p = r["present"] or 0
            a = r["absent"]  or 0
            pct_sub = attendance_percentage(p, a)
            rows.append({
                "Subject":   r["subject_name"],
                "Code":      r.get("subject_code", ""),
                "Present":   p,
                "Absent":    a,
                "Medical":   r.get("medical", 0),
                "Total":     p + a,
                "% Attended": f"{pct_sub:.1f}%" if pct_sub is not None else "N/A",
            })
        df_m = pd.DataFrame(rows)
        st.dataframe(df_m, use_container_width=True, hide_index=True)

        # PDF report including monthly breakdown
        if st.button("📄 Download Monthly PDF Report", key="monthly_pdf_btn"):
            with st.spinner("Generating PDF..."):
                try:
                    sem_monthly = semester_selector(sid, key="monthly_sem_for_pdf")
                    if sem_monthly:
                        dash_data   = get_dashboard_data(sid, sem_monthly["id"],
                                                         student.get("required_percentage") or 75.0)
                        subj_stats  = get_subject_stats(sem_monthly["id"],
                                                        student.get("required_percentage") or 75.0)
                        pdf_bytes   = generate_attendance_pdf(
                            student        = student,
                            semester_name  = sem_monthly["name"],
                            subject_stats  = subj_stats,
                            dashboard_data = dash_data,
                            monthly_data   = monthly_data,
                            monthly_year   = selected_year,
                            monthly_month  = selected_month,
                        )
                        from src.export import export_filename
                        st.download_button(
                            label     = "⬇️ Save Monthly PDF",
                            data      = pdf_bytes,
                            file_name = export_filename(f"smart_attendance_{month_label.replace(' ', '_')}"),
                            mime      = "application/pdf",
                            key       = "monthly_pdf_dl",
                        )
                except Exception as e:
                    st.error(f"PDF generation failed: {e}")


# ===========================================================================
# TAB 3: TREND
# ===========================================================================
with tab_trend:
    trend_data = models.get_attendance_trend(sid, sem["id"])
    if not trend_data:
        no_data_placeholder("No trend data available for this semester.")
    else:
        fig_trend = attendance_trend_chart(trend_data)
        st.plotly_chart(fig_trend, use_container_width=True)

        fig_daily = daily_attendance_bar(trend_data)
        st.plotly_chart(fig_daily, use_container_width=True)
