"""
export.py — Data export utilities (CSV, future: PDF).
"""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd


def attendance_to_csv(records: list[dict]) -> bytes:
    """
    Convert a list of attendance record dicts to CSV bytes.

    Suitable for Streamlit's st.download_button(data=...).
    """
    if not records:
        df = pd.DataFrame(columns=["Date", "Subject", "Code", "Semester", "Status"])
    else:
        df = pd.DataFrame(records)
        rename_map = {
            "date":          "Date",
            "subject_name":  "Subject",
            "subject_code":  "Code",
            "semester_name": "Semester",
            "status":        "Status",
            "session_num":   "Session",
        }
        df = df.rename(columns=rename_map)
        keep_cols = [c for c in rename_map.values() if c in df.columns]
        df = df[keep_cols]
        df = df.sort_values(["Date", "Subject"], ascending=[False, True])

    return df.to_csv(index=False).encode("utf-8")


def subject_stats_to_csv(subject_stats: list[dict]) -> bytes:
    """Export per-subject summary stats to CSV bytes."""
    if not subject_stats:
        df = pd.DataFrame(columns=["Subject", "Code", "Total", "Present", "Absent", "Medical", "Percentage", "Status"])
    else:
        rows = []
        for s in subject_stats:
            rows.append({
                "Subject":    s["subject_name"],
                "Code":       s.get("subject_code", ""),
                "Total":      s["total"],
                "Present":    s["present"],
                "Absent":     s["absent"],
                "Medical":    s.get("medical", 0),
                "Percentage": f"{s['percentage']:.2f}%" if s["percentage"] is not None else "N/A",
                "Status":     s["status"],
                "Threshold":  f"{s['threshold']}%",
            })
        df = pd.DataFrame(rows)

    return df.to_csv(index=False).encode("utf-8")


def export_filename(prefix: str = "attendance") -> str:
    """Generate a timestamped export filename."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.csv"
