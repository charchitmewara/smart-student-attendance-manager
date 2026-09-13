"""
auth.py — Authentication helpers.

Passwords are hashed with bcrypt before storage.
Session state is managed via st.session_state["student"].
"""

from __future__ import annotations

from typing import Optional

import bcrypt
import streamlit as st

from src.models import create_student, get_student_by_username


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Hash a plain-text password with bcrypt. Returns a str."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Registration / login
# ---------------------------------------------------------------------------

def register_student(username: str, password: str) -> tuple[bool, str]:
    """
    Register a new student account.

    Returns (success: bool, message: str).
    """
    from src.validation import validate_username, validate_password

    ok, msg = validate_username(username)
    if not ok:
        return False, msg

    ok, msg = validate_password(password)
    if not ok:
        return False, msg

    # Check uniqueness
    if get_student_by_username(username.strip()):
        return False, "That username is already taken. Please choose another."

    pw_hash = hash_password(password)
    student_id = create_student(username.strip(), pw_hash)
    if student_id is None:
        return False, "Registration failed. Please try again."

    return True, "Account created successfully!"


def login_student(username: str, password: str) -> tuple[bool, str]:
    """
    Authenticate a student.

    On success, stores the student dict in st.session_state["student"].
    Returns (success: bool, message: str).
    """
    if not username or not password:
        return False, "Please enter both username and password."

    student = get_student_by_username(username.strip())
    if not student:
        return False, "Invalid username or password."

    if not verify_password(password, student["password_hash"]):
        return False, "Invalid username or password."

    st.session_state["student"] = student
    return True, "Login successful!"


def logout() -> None:
    """Clear the session state to log out the current student."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]


# ---------------------------------------------------------------------------
# Session guard
# ---------------------------------------------------------------------------

def require_auth() -> Optional[dict]:
    """
    Ensure a student is logged in.

    If not, display a message and stop execution of the current page.
    Returns the student dict if authenticated.
    """
    if "student" not in st.session_state:
        st.warning("Please log in to access this page.")
        st.stop()
    return st.session_state["student"]


def get_current_student() -> Optional[dict]:
    """Return the logged-in student dict, or None."""
    return st.session_state.get("student", None)
