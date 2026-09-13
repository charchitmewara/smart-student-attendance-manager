"""
app.py — Application entry point.

Serves as the login/register gate.
Authenticated users are directed to the Dashboard via Streamlit's
multi-page navigation in the pages/ directory.
"""

import streamlit as st

# ── page config must be the very first Streamlit call ──────────────────────
st.set_page_config(
    page_title="Smart Student Attendance Manager",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── ensure DB schema is ready before anything else ─────────────────────────
from src.database import init_db  # noqa: E402 (import after page_config)
try:
    init_db()
except Exception as e:
    st.error(f"Database initialization error: {e}")
    st.stop()

from src.auth import login_student, register_student, get_current_student, logout
from src.ui import inject_custom_css, render_sidebar

inject_custom_css()


# ── already logged in: show welcome and redirect hint ──────────────────────
student = get_current_student()
if student:
    render_sidebar()
    name = student.get("name") or student["username"]
    st.title(f"Welcome back, {name}! 👋")
    st.success("You are logged in. Use the sidebar to navigate.")
    st.page_link("pages/1_Dashboard.py", label="Go to Dashboard →", icon="🏠")
    st.stop()


# ── not logged in: show login / register UI ────────────────────────────────
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown(
        '<div style="text-align:center;padding:30px 0 10px;">'
        '<h1 style="font-size:2rem;">🎓 Smart Attendance</h1>'
        '<p style="color:#64748B;">University Student Attendance Manager</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])

    with tab_login:
        st.markdown("#### Sign in to your account")
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                ok, msg = login_student(username, password)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with tab_register:
        st.markdown("#### Create a new account")
        with st.form("register_form", clear_on_submit=True):
            new_username  = st.text_input("Username", placeholder="3–30 chars, letters/digits/_")
            new_password  = st.text_input("Password", type="password", placeholder="At least 6 characters")
            confirm_pw    = st.text_input("Confirm Password", type="password")
            submitted_reg = st.form_submit_button("Create Account", use_container_width=True, type="primary")

        if submitted_reg:
            if new_password != confirm_pw:
                st.error("Passwords do not match.")
            else:
                ok, msg = register_student(new_username, new_password)
                if ok:
                    st.success(f"{msg} You can now sign in.")
                else:
                    st.error(msg)

    st.markdown(
        '<div style="text-align:center;margin-top:30px;color:#94A3B8;font-size:0.8rem;">'
        'Smart Student Attendance Manager &mdash; University Project'
        '</div>',
        unsafe_allow_html=True,
    )
