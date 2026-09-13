"""
pages/6_What_If_Calculator.py — Attendance calculator.

Answers:
  1. "How many consecutive classes do I need to attend to reach X%?"
  2. "How many classes can I still miss while staying above X%?"
  3. What-If simulation: project attendance if I attend or miss N more classes.
"""

import streamlit as st

st.set_page_config(
    page_title="What-If Calculator — Smart Attendance",
    page_icon="🧮",
    layout="wide",
)

from src.auth import require_auth
from src.ui import inject_custom_css, render_sidebar, semester_selector, render_status_badge
from src.calculations import (
    attendance_percentage, status_label,
    classes_needed_to_recover, classes_can_miss,
    whatif_attend, whatif_miss,
)
from src.services import get_subject_stats
from src import models

inject_custom_css()
student = require_auth()
render_sidebar()

st.title("🧮 What-If Calculator")
st.markdown(
    "Understand exactly where you stand and what it takes to hit your attendance target."
)

sid = student["id"]
default_threshold = student.get("required_percentage") or 75.0

tab_calc, tab_whatif = st.tabs(["📐 Attendance Calculator", "🔮 What-If Projector"])

# ===========================================================================
# TAB 1: ATTENDANCE CALCULATOR
# ===========================================================================
with tab_calc:
    st.markdown("### Calculate Classes Needed / Can Miss")

    col_in, col_out = st.columns([1, 1])

    with col_in:
        st.markdown("#### Enter your current figures")
        present_in = st.number_input("Classes Attended (Present)", min_value=0, value=0, step=1)
        absent_in  = st.number_input("Classes Absent",            min_value=0, value=0, step=1)
        threshold_in = st.number_input(
            "Required Attendance %",
            min_value=1.0, max_value=100.0,
            value=float(default_threshold),
            step=0.5,
        )
        calc_btn = st.button("Calculate", type="primary")

    with col_out:
        st.markdown("#### Results")
        if calc_btn or (present_in + absent_in > 0):
            pct = attendance_percentage(int(present_in), int(absent_in))
            label = status_label(pct, float(threshold_in))
            total = int(present_in) + int(absent_in)

            if pct is None:
                st.info("No classes recorded yet.")
            else:
                st.markdown(f"**Current Attendance:** {pct:.2f}%")
                render_status_badge(label)
                st.markdown(f"**Total effective classes:** {total}")
                st.progress(min(pct / 100.0, 1.0))
                st.markdown("---")

                if pct >= float(threshold_in):
                    can = classes_can_miss(int(present_in), int(absent_in), float(threshold_in))
                    st.success(
                        f"✅ You are above the required **{threshold_in}%**.\n\n"
                        f"You can afford to miss up to **{can}** more class(es) "
                        f"while staying at or above {threshold_in}%."
                    )
                else:
                    needed = classes_needed_to_recover(int(present_in), int(absent_in), float(threshold_in))
                    if needed is None:
                        st.error("Unable to calculate. Please check your inputs.")
                    elif needed == 0:
                        st.info("You are exactly at the required threshold.")
                    else:
                        st.warning(
                            f"⚠️ Your attendance is **{pct:.2f}%** — below the required **{threshold_in}%**.\n\n"
                            f"You need to attend the next **{needed}** consecutive class(es) "
                            f"to reach **{threshold_in}%**."
                        )
                        st.info("You currently cannot afford to miss any class until you recover.")

    # ── Formula explanation ────────────────────────────────────────────────
    with st.expander("📐 How is this calculated?"):
        st.markdown("""
**Attendance Percentage:**
```
percentage = (present / (present + absent)) × 100
```
Medical Leave is excluded from both numerator and denominator.

**Classes needed to recover (when below threshold):**
```
Find the smallest x ≥ 0 such that:
    (present + x) / (present + absent + x) ≥ required / 100

Solving:
    x ≥ (required% × total − present) / (1 − required%)
    x = ceil of the above
```

**Classes you can still miss (when above threshold):**
```
Find the largest y ≥ 0 such that:
    present / (present + absent + y) ≥ required / 100

Solving:
    y ≤ present / (required%) − total
    y = floor of the above
```
        """)

# ===========================================================================
# TAB 2: WHAT-IF PROJECTOR
# ===========================================================================
with tab_whatif:
    st.markdown("### Project future attendance scenarios")

    # Subject-level what-if
    sem = semester_selector(sid, key="whatif_semester")
    if sem:
        subject_stats = get_subject_stats(sem["id"], default_threshold)
        active = [s for s in subject_stats if not s["is_archived"] and s["total"] > 0]

        if not active:
            st.info("No attendance data yet. Mark some attendance first.")
        else:
            subj_names = [s["subject_name"] for s in active]
            chosen = st.selectbox("Select Subject", options=subj_names)
            subj_data = next(s for s in active if s["subject_name"] == chosen)

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Current: {subj_data['percentage']:.1f}%**")
                st.markdown(
                    f"Present: {subj_data['present']}  |  "
                    f"Absent: {subj_data['absent']}  |  "
                    f"Threshold: {subj_data['threshold']}%"
                )

            extra = st.slider("Simulate attending N more classes:", 0, 50, 5)
            miss  = st.slider("Simulate missing N more classes:", 0, 50, 0)

            proj_attend = whatif_attend(
                subj_data["present"], subj_data["absent"], extra, subj_data["threshold"]
            )
            proj_miss = whatif_miss(
                subj_data["present"], subj_data["absent"], miss, subj_data["threshold"]
            )

            col_sim1, col_sim2 = st.columns(2)
            with col_sim1:
                st.markdown(f"**If you attend {extra} more classes:**")
                pct_proj = proj_attend["new_percentage"]
                st.metric(
                    "Projected Attendance",
                    f"{pct_proj:.1f}%" if pct_proj else "N/A",
                    delta=f"+{(pct_proj or 0) - (subj_data['percentage'] or 0):.1f}%" if pct_proj else None,
                )
                render_status_badge(proj_attend["new_status"])

            with col_sim2:
                st.markdown(f"**If you miss {miss} more classes:**")
                pct_miss = proj_miss["new_percentage"]
                delta_val = ((pct_miss or 0) - (subj_data["percentage"] or 0))
                st.metric(
                    "Projected Attendance",
                    f"{pct_miss:.1f}%" if pct_miss else "N/A",
                    delta=f"{delta_val:.1f}%" if pct_miss else None,
                    delta_color="inverse",
                )
                render_status_badge(proj_miss["new_status"])
