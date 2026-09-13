"""
analytics.py — Analytics and chart-building helpers.

All chart functions return Plotly figure objects ready for st.plotly_chart().
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.calculations import status_color


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

def subject_bar_chart(subject_stats: list[dict], threshold: float = 75.0) -> go.Figure:
    """
    Horizontal bar chart of per-subject attendance percentages.

    Bars are colored by status. A vertical threshold line is drawn.
    """
    if not subject_stats:
        return go.Figure()

    df = pd.DataFrame(subject_stats)
    df = df[df["is_archived"] == 0]  # exclude archived subjects
    if df.empty:
        return go.Figure()

    df = df.sort_values("percentage", ascending=True)

    colors = [status_color(s) for s in df["status"]]

    fig = go.Figure(go.Bar(
        x=df["percentage"],
        y=df["subject_name"],
        orientation="h",
        marker_color=colors,
        text=[f"{p:.1f}%" if p is not None else "N/A" for p in df["percentage"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Attendance: %{x:.1f}%<extra></extra>",
    ))

    fig.add_vline(
        x=threshold,
        line_dash="dash",
        line_color="orange",
        annotation_text=f"Required: {threshold}%",
        annotation_position="top right",
    )

    fig.update_layout(
        title="Subject-wise Attendance",
        xaxis_title="Attendance %",
        yaxis_title="",
        xaxis=dict(range=[0, 115]),
        height=max(300, len(df) * 50 + 100),
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def present_absent_pie(total_present: int, total_absent: int, total_medical: int = 0) -> go.Figure:
    """Pie chart showing present / absent / medical breakdown."""
    labels = []
    values = []
    colors_list = []

    if total_present > 0:
        labels.append("Present")
        values.append(total_present)
        colors_list.append("#22C55E")
    if total_absent > 0:
        labels.append("Absent")
        values.append(total_absent)
        colors_list.append("#EF4444")
    if total_medical > 0:
        labels.append("Medical Leave")
        values.append(total_medical)
        colors_list.append("#F59E0B")

    if not values:
        return go.Figure()

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        marker_colors=colors_list,
        hole=0.45,
        hovertemplate="%{label}: %{value} classes (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        title="Overall Attendance Breakdown",
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=True,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def attendance_trend_chart(trend_data: list[dict]) -> go.Figure:
    """
    Line chart showing cumulative attendance percentage over time.
    """
    if not trend_data:
        return go.Figure()

    df = pd.DataFrame(trend_data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    df["cumulative_present"] = df["present"].cumsum()
    df["cumulative_absent"]  = df["absent"].cumsum()
    df["cumulative_total"]   = df["cumulative_present"] + df["cumulative_absent"]
    df["cumulative_pct"] = (
        df["cumulative_present"] / df["cumulative_total"].replace(0, float("nan"))
    ) * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["cumulative_pct"],
        mode="lines+markers",
        name="Cumulative %",
        line=dict(color="#4A90D9", width=2),
        hovertemplate="%{x|%d %b}: %{y:.1f}%<extra></extra>",
    ))

    fig.update_layout(
        title="Attendance Trend Over Time",
        xaxis_title="Date",
        yaxis_title="Cumulative Attendance %",
        yaxis=dict(range=[0, 105]),
        margin=dict(l=20, r=20, t=50, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def daily_attendance_bar(trend_data: list[dict]) -> go.Figure:
    """Grouped bar chart of daily present vs absent count."""
    if not trend_data:
        return go.Figure()

    df = pd.DataFrame(trend_data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["date"], y=df["present"],
        name="Present", marker_color="#22C55E",
    ))
    fig.add_trace(go.Bar(
        x=df["date"], y=df["absent"],
        name="Absent", marker_color="#EF4444",
    ))
    if "medical" in df.columns and df["medical"].sum() > 0:
        fig.add_trace(go.Bar(
            x=df["date"], y=df["medical"],
            name="Medical", marker_color="#F59E0B",
        ))

    fig.update_layout(
        title="Daily Attendance",
        barmode="stack",
        xaxis_title="Date",
        yaxis_title="Classes",
        margin=dict(l=20, r=20, t=50, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def monthly_bar_chart(monthly_data: list[dict]) -> go.Figure:
    """Grouped bar chart: per-subject present/absent for a month."""
    if not monthly_data:
        return go.Figure()

    df = pd.DataFrame(monthly_data)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["subject_name"], y=df["present"],
        name="Present", marker_color="#22C55E",
    ))
    fig.add_trace(go.Bar(
        x=df["subject_name"], y=df["absent"],
        name="Absent", marker_color="#EF4444",
    ))

    fig.update_layout(
        title="Monthly Subject-wise Attendance",
        barmode="group",
        xaxis_title="Subject",
        yaxis_title="Classes",
        margin=dict(l=20, r=20, t=50, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
