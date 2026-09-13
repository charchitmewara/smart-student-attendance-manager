"""
pages/7_Settings.py — Account settings, profile, demo data loader.
"""

import streamlit as st

st.set_page_config(
    page_title="Settings — Smart Attendance",
    page_icon="⚙️",
    layout="wide",
)

from src.auth import require_auth, verify_password, hash_password, logout
from src.ui import inject_custom_css, render_sidebar
from src.validation import validate_name, validate_threshold
from src.sample_data import seed_demo_data, DEMO_SEMESTER_NAME
from src import models

inject_custom_css()
student = require_auth()
render_sidebar()

st.title("⚙️ Settings")

sid = student["id"]

tab_profile, tab_security, tab_demo, tab_danger = st.tabs(
    ["👤 Profile", "🔐 Security", "🎭 Demo Data", "⚠️ Danger Zone"]
)

# ===========================================================================
# TAB 1: PROFILE
# ===========================================================================
with tab_profile:
    st.markdown("### Your Profile")

    with st.form("profile_form"):
        name       = st.text_input("Full Name",          value=student.get("name") or "")
        student_id = st.text_input("Student ID / Roll No", value=student.get("student_id") or "")
        university = st.text_input("University / College", value=student.get("university") or "")
        course     = st.text_input("Course / Program",    value=student.get("course") or "")
        semester   = st.text_input("Semester",            value=student.get("semester") or "")
        threshold  = st.number_input(
            "Required Attendance % (global default)",
            min_value=1.0, max_value=100.0,
            value=float(student.get("required_percentage") or 75.0),
            step=0.5,
            help="This is the default threshold. You can override it per subject in the Subjects page.",
        )
        save_btn = st.form_submit_button("Save Profile", type="primary")

    if save_btn:
        errors = []
        if name.strip():
            ok, msg = validate_name(name, "Full Name")
            if not ok:
                errors.append(msg)
        ok2, msg2 = validate_threshold(threshold)
        if not ok2:
            errors.append(msg2)

        if errors:
            for e in errors:
                st.error(e)
        else:
            models.update_student_profile(
                sid,
                name=name.strip(),
                student_id=student_id.strip(),
                university=university.strip(),
                course=course.strip(),
                semester=semester.strip(),
                required_percentage=float(threshold),
            )
            # Refresh session state
            updated = models.get_student_by_id(sid)
            if updated:
                st.session_state["student"] = updated
                student = updated
            st.success("Profile saved.")
            st.rerun()

    # Display current info
    st.markdown("---")
    st.markdown("#### Account Info")
    st.markdown(f"- **Username:** `{student['username']}`")
    st.markdown(f"- **Member since:** {str(student.get('created_at', 'N/A'))[:10]}")


# ===========================================================================
# TAB 2: SECURITY
# ===========================================================================
with tab_security:
    st.markdown("### Change Password")

    with st.form("change_pw_form"):
        current_pw  = st.text_input("Current Password",    type="password")
        new_pw      = st.text_input("New Password",        type="password")
        confirm_pw  = st.text_input("Confirm New Password", type="password")
        change_btn  = st.form_submit_button("Change Password", type="primary")

    if change_btn:
        if not current_pw or not new_pw or not confirm_pw:
            st.error("Please fill in all fields.")
        elif not verify_password(current_pw, student["password_hash"]):
            st.error("Current password is incorrect.")
        elif new_pw != confirm_pw:
            st.error("New passwords do not match.")
        elif len(new_pw) < 6:
            st.error("New password must be at least 6 characters.")
        else:
            models.update_student_password(sid, hash_password(new_pw))
            st.success("Password changed successfully.")


# ===========================================================================
# TAB 3: DEMO DATA
# ===========================================================================
with tab_demo:
    st.markdown("### Load Demo Data")
    st.info(
        f"This will create a demo semester called **\"{DEMO_SEMESTER_NAME}\"** "
        "with 6 subjects and approximately 60 days of randomized attendance records. "
        "Use it to explore the application without entering data manually."
    )
    st.markdown(
        "**Demo subjects:** Mathematics, Physics, Chemistry, Computer Science, English, Data Structures  \n"
        "**Date range:** Past 60 weekdays  \n"
        "**Note:** Some subjects are intentionally below the attendance threshold to demonstrate all dashboard features."
    )

    # Check if demo data already exists
    semesters = models.get_semesters(sid)
    demo_exists = any(s["name"] == DEMO_SEMESTER_NAME for s in semesters)

    if demo_exists:
        st.warning(f'Demo data already loaded ("{DEMO_SEMESTER_NAME}" semester exists).')
        overwrite_check = st.checkbox("I want to reload / overwrite the demo data")
        load_btn = st.button("🔄 Reload Demo Data", type="primary", disabled=not overwrite_check)
        if load_btn and overwrite_check:
            with st.spinner("Loading demo data..."):
                result = seed_demo_data(sid, overwrite=True)
            if result["success"]:
                st.success(result["message"])
            else:
                st.error(result["message"])
    else:
        load_btn = st.button("🎭 Load Demo Data", type="primary")
        if load_btn:
            with st.spinner("Creating demo data..."):
                result = seed_demo_data(sid, overwrite=False)
            if result["success"]:
                st.success(result["message"])
                st.info("Go to the **Dashboard** and select the demo semester to explore it.")
            else:
                st.error(result["message"])


# ===========================================================================
# TAB 4: DANGER ZONE
# ===========================================================================
with tab_danger:
    st.markdown("### ⚠️ Danger Zone")
    st.error(
        "The actions in this section are **irreversible**. "
        "All data deleted here cannot be recovered."
    )

    st.markdown("#### Delete All My Data")
    st.markdown(
        "This will permanently delete **all** your semesters, subjects, and attendance records. "
        "Your account (username/password) will remain."
    )

    if "confirm_delete_all" not in st.session_state:
        st.session_state["confirm_delete_all"] = False

    if st.button("🗑️ Delete All My Attendance Data"):
        st.session_state["confirm_delete_all"] = True

    if st.session_state["confirm_delete_all"]:
        st.error("Are you absolutely sure? This deletes ALL your semesters and attendance records.")
        confirm_text = st.text_input('Type your username to confirm:', placeholder=student["username"])
        c1, c2 = st.columns(2)
        if c1.button("Yes, delete everything", type="primary"):
            if confirm_text.strip() == student["username"]:
                sems = models.get_semesters(sid)
                for s in sems:
                    models.delete_semester(s["id"], sid)
                st.session_state["confirm_delete_all"] = False
                st.success("All data deleted. Your account is still active.")
                st.rerun()
            else:
                st.error("Username does not match. Deletion cancelled.")
        if c2.button("Cancel"):
            st.session_state["confirm_delete_all"] = False
            st.rerun()

    st.markdown("---")
    st.markdown("#### Delete Account")
    st.markdown("Contact your system administrator to permanently remove your account.")
