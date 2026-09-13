"""
ui.py — Shared UI helper functions used across all pages.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from src.calculations import status_color
from src import models


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

def page_setup(title: str, icon: str = "📚") -> None:
    """Configure the Streamlit page (must be first Streamlit call in a page)."""
    st.set_page_config(
        page_title=f"{title} — Smart Attendance",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_custom_css() -> None:
    """Inject shared CSS for consistent card and badge styling."""
    st.markdown("""
    <style>
    /* ── metric cards ── */
    [data-testid="metric-container"] {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    /* ── status badges ── */
    .status-badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        color: #fff;
    }
    /* ── subject cards ── */
    .subject-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 10px;
    }
    .subject-card.at-risk {
        border-left: 4px solid #EF4444;
    }
    /* ── progress bar label ── */
    .progress-label {
        font-size: 0.85rem;
        color: #64748B;
        margin-bottom: 4px;
    }
    /* ── sidebar links ── */
    [data-testid="stSidebarNav"] a {
        font-size: 1rem;
        padding: 0.35rem 0;
    }
    /* ── hide default hamburger menu ── */
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Status badge helper
# ---------------------------------------------------------------------------

def status_badge(label: str) -> str:
    """Return an HTML status badge string."""
    color = status_color(label)
    return f'<span class="status-badge" style="background:{color}">{label}</span>'


def render_status_badge(label: str) -> None:
    """Render a colored status badge via st.markdown."""
    st.markdown(status_badge(label), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Semester selector
# ---------------------------------------------------------------------------

def semester_selector(student_id: int, key: str = "view_semester") -> Optional[dict]:
    """
    Render a selectbox for choosing a semester to VIEW.

    Independent of the "active semester" used for data entry.
    Returns the selected semester dict, or None if no semesters exist.
    """
    semesters = models.get_semesters(student_id)
    if not semesters:
        st.info("No semesters found. Go to **📚 Subjects** to create one.")
        return None

    sem_names = [s["name"] for s in semesters]

    # Default to the active semester if available
    active = models.get_active_semester(student_id)
    default_idx = 0
    if active:
        for i, s in enumerate(semesters):
            if s["id"] == active["id"]:
                default_idx = i
                break

    choice = st.selectbox("📅 Semester", sem_names, index=default_idx, key=key)
    return next(s for s in semesters if s["name"] == choice)


# ---------------------------------------------------------------------------
# No-data placeholder
# ---------------------------------------------------------------------------

def no_data_placeholder(message: str = "No data to display.") -> None:
    """Render a centered no-data message."""
    st.markdown(
        f'<div style="text-align:center;padding:40px;color:#94A3B8;">'
        f'<h3 style="color:#94A3B8;">📭</h3><p>{message}</p></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar() -> None:
    """Render the sidebar with student info and navigation."""
    from src.auth import logout, get_current_student

    student = get_current_student()
    if not student:
        return

    with st.sidebar:
        st.markdown("### 🎓 Smart Attendance")
        st.markdown("---")

        name = student.get("name") or student["username"]
        st.markdown(f"**{name}**")
        if student.get("university"):
            st.caption(student["university"])
        if student.get("semester"):
            st.caption(f"Semester: {student['semester']}")
        st.markdown("---")

        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()
