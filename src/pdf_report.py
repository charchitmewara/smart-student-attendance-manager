"""
pdf_report.py — PDF attendance report generator using ReportLab.

Generates a professional single-student attendance report including:
  - Student profile header
  - Overall KPI summary
  - Per-subject attendance table
  - Status badges with colour coding
  - Advisory messages
  - Monthly breakdown table (if provided)
  - Footer with generation timestamp

Returns bytes suitable for Streamlit's st.download_button().
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


# ---------------------------------------------------------------------------
# Colour palette (matches the Streamlit theme)
# ---------------------------------------------------------------------------

C_PRIMARY   = colors.HexColor("#4A90D9")   # blue
C_EXCELLENT = colors.HexColor("#22C55E")   # green
C_SAFE      = colors.HexColor("#4A90D9")   # blue
C_WARNING   = colors.HexColor("#F59E0B")   # amber
C_CRITICAL  = colors.HexColor("#EF4444")   # red
C_MEDICAL   = colors.HexColor("#F59E0B")   # amber
C_LIGHT_BG  = colors.HexColor("#F8F9FA")   # page bg
C_TABLE_HDR = colors.HexColor("#1E293B")   # dark header
C_ROW_ALT   = colors.HexColor("#F1F5F9")   # alternate row
C_ROW_RISK  = colors.HexColor("#FEF2F2")   # at-risk row (light red)
C_ROW_OK    = colors.HexColor("#F0FDF4")   # excellent row (light green)
C_TEXT      = colors.HexColor("#1E293B")
C_MUTED     = colors.HexColor("#64748B")
C_WHITE     = colors.white
C_BORDER    = colors.HexColor("#E2E8F0")


def _status_colour(status: str) -> colors.HexColor:
    mapping = {
        "Excellent": C_EXCELLENT,
        "Safe":      C_SAFE,
        "Warning":   C_WARNING,
        "Critical":  C_CRITICAL,
        "No Data":   C_MUTED,
    }
    return mapping.get(status, C_MUTED)


def _row_bg(status: str) -> colors.HexColor | None:
    if status in ("Critical", "Warning"):
        return C_ROW_RISK
    if status == "Excellent":
        return C_ROW_OK
    return None


# ---------------------------------------------------------------------------
# Page template with header/footer
# ---------------------------------------------------------------------------

def _make_page_template(doc, student_name: str, semester_name: str) -> PageTemplate:
    """Return a PageTemplate with a branded header and footer on every page."""

    def on_page(canvas, doc):
        canvas.saveState()
        w, h = A4

        # ── Header bar ─────────────────────────────────────────────────────
        canvas.setFillColor(C_PRIMARY)
        canvas.rect(0, h - 2.2 * cm, w, 2.2 * cm, fill=True, stroke=False)

        canvas.setFillColor(C_WHITE)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(1.5 * cm, h - 1.3 * cm, "🎓  Smart Student Attendance Manager")

        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(w - 1.5 * cm, h - 1.3 * cm, f"Attendance Report")

        # ── Footer ─────────────────────────────────────────────────────────
        canvas.setFillColor(C_MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(1.5 * cm, 0.8 * cm, f"Generated: {datetime.now().strftime('%d %b %Y  %H:%M')}")
        canvas.drawCentredString(w / 2, 0.8 * cm, f"{student_name}  —  {semester_name}")
        canvas.drawRightString(w - 1.5 * cm, 0.8 * cm, f"Page {doc.page}")

        # ── Footer rule ────────────────────────────────────────────────────
        canvas.setStrokeColor(C_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(1.5 * cm, 1.2 * cm, w - 1.5 * cm, 1.2 * cm)

        canvas.restoreState()

    page_width = A4[0]
    frame = Frame(
        1.5 * cm,                  # x
        1.8 * cm,                  # y (above footer)
        page_width - 3.0 * cm,    # width
        A4[1] - 4.2 * cm,         # height (below header, above footer)
        leftPadding=0,
        rightPadding=0,
        topPadding=0.3 * cm,
        bottomPadding=0,
    )
    return PageTemplate(id="main", frames=[frame], onPage=on_page)


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Heading1"],
            fontSize=18,
            textColor=C_TEXT,
            spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontSize=11,
            textColor=C_MUTED,
            spaceAfter=4,
        ),
        "section": ParagraphStyle(
            "section",
            parent=base["Heading2"],
            fontSize=13,
            textColor=C_PRIMARY,
            spaceBefore=14,
            spaceAfter=6,
            borderPad=2,
        ),
        "body": ParagraphStyle(
            "body",
            fontSize=10,
            textColor=C_TEXT,
            leading=14,
            spaceAfter=4,
        ),
        "muted": ParagraphStyle(
            "muted",
            fontSize=9,
            textColor=C_MUTED,
            leading=13,
            spaceAfter=3,
        ),
        "advisory": ParagraphStyle(
            "advisory",
            fontSize=9,
            textColor=C_TEXT,
            backColor=colors.HexColor("#FFFBEB"),
            borderColor=C_WARNING,
            borderWidth=0.5,
            borderPad=6,
            leading=13,
            spaceAfter=6,
        ),
        "good": ParagraphStyle(
            "good",
            fontSize=9,
            textColor=C_TEXT,
            backColor=colors.HexColor("#F0FDF4"),
            borderColor=C_EXCELLENT,
            borderWidth=0.5,
            borderPad=6,
            leading=13,
            spaceAfter=6,
        ),
        "cell": ParagraphStyle("cell", fontSize=9, textColor=C_TEXT, leading=12),
        "cell_center": ParagraphStyle(
            "cell_center", fontSize=9, textColor=C_TEXT, alignment=TA_CENTER, leading=12
        ),
    }


# ---------------------------------------------------------------------------
# KPI summary table
# ---------------------------------------------------------------------------

def _kpi_table(
    overall_pct: Optional[float],
    total_classes: int,
    present: int,
    absent: int,
    medical: int,
    num_subjects: int,
    threshold: float,
    status: str,
) -> Table:
    pct_str = f"{overall_pct:.1f}%" if overall_pct is not None else "N/A"
    status_c = _status_colour(status)

    data = [
        ["Overall Attendance", "Total Classes", "Present", "Absent", "Medical", "Subjects"],
        [
            Paragraph(f'<font color="{status_c.hexval()}" size="16"><b>{pct_str}</b></font>',
                      ParagraphStyle("kpi", alignment=TA_CENTER, leading=20)),
            Paragraph(f'<font size="16"><b>{total_classes}</b></font>',
                      ParagraphStyle("kpi", alignment=TA_CENTER, leading=20)),
            Paragraph(f'<font color="#22C55E" size="16"><b>{present}</b></font>',
                      ParagraphStyle("kpi", alignment=TA_CENTER, leading=20)),
            Paragraph(f'<font color="#EF4444" size="16"><b>{absent}</b></font>',
                      ParagraphStyle("kpi", alignment=TA_CENTER, leading=20)),
            Paragraph(f'<font color="#F59E0B" size="16"><b>{medical}</b></font>',
                      ParagraphStyle("kpi", alignment=TA_CENTER, leading=20)),
            Paragraph(f'<font size="16"><b>{num_subjects}</b></font>',
                      ParagraphStyle("kpi", alignment=TA_CENTER, leading=20)),
        ],
        [
            Paragraph(
                f'<font color="{status_c.hexval()}"><b>Status: {status}</b></font>  '
                f'<font color="#64748B">(Required: {threshold}%)</font>',
                ParagraphStyle("kpi_sub", alignment=TA_CENTER, fontSize=8, leading=11),
            ),
            "", "", "", "", "",
        ],
    ]

    col_w = (A4[0] - 3.0 * cm) / 6

    t = Table(data, colWidths=[col_w] * 6, repeatRows=1)
    t.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",    (0, 0), (-1, 0), C_TABLE_HDR),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("VALIGN",        (0, 0), (-1, 0), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        # Value row
        ("ALIGN",         (0, 1), (-1, 1), "CENTER"),
        ("VALIGN",        (0, 1), (-1, 2), "MIDDLE"),
        ("TOPPADDING",    (0, 1), (-1, 1), 10),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
        # Subtitle row (span all columns)
        ("SPAN",          (0, 2), (-1, 2)),
        ("ALIGN",         (0, 2), (-1, 2), "CENTER"),
        ("TOPPADDING",    (0, 2), (-1, 2), 2),
        ("BOTTOMPADDING", (0, 2), (-1, 2), 8),
        # All
        ("GRID",          (0, 0), (-1, -1), 0.5, C_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT_BG]),
    ]))
    return t


# ---------------------------------------------------------------------------
# Subject table
# ---------------------------------------------------------------------------

def _subject_table(subject_stats: list[dict]) -> Table:
    s = _styles()
    headers = ["Subject", "Code", "Total", "Present", "Absent", "Medical", "Attendance %", "Status", "Threshold"]
    rows = [headers]

    for subj in subject_stats:
        if subj.get("is_archived"):
            continue
        pct = subj.get("percentage")
        pct_str = f"{pct:.1f}%" if pct is not None else "N/A"
        status = subj.get("status", "No Data")
        status_c = _status_colour(status)

        rows.append([
            Paragraph(subj["subject_name"], s["cell"]),
            Paragraph(subj.get("subject_code") or "", s["cell_center"]),
            Paragraph(str(subj.get("total", 0)), s["cell_center"]),
            Paragraph(str(subj.get("present", 0)), s["cell_center"]),
            Paragraph(str(subj.get("absent", 0)), s["cell_center"]),
            Paragraph(str(subj.get("medical", 0)), s["cell_center"]),
            Paragraph(
                f'<font color="{status_c.hexval()}"><b>{pct_str}</b></font>',
                ParagraphStyle("pct", alignment=TA_CENTER, fontSize=9),
            ),
            Paragraph(
                f'<font color="{status_c.hexval()}"><b>{status}</b></font>',
                ParagraphStyle("stat", alignment=TA_CENTER, fontSize=9),
            ),
            Paragraph(f"{subj.get('threshold', 75)}%", s["cell_center"]),
        ])

    avail_w = A4[0] - 3.0 * cm
    col_widths = [
        avail_w * 0.22,  # Subject name
        avail_w * 0.08,  # Code
        avail_w * 0.07,  # Total
        avail_w * 0.07,  # Present
        avail_w * 0.07,  # Absent
        avail_w * 0.07,  # Medical
        avail_w * 0.12,  # %
        avail_w * 0.14,  # Status
        avail_w * 0.10,  # Threshold
    ]

    t = Table(rows, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        # Header
        ("BACKGROUND",    (0, 0), (-1, 0), C_TABLE_HDR),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("VALIGN",        (0, 0), (-1, 0), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        # Body
        ("FONTSIZE",      (0, 1), (-1, -1), 9),
        ("VALIGN",        (0, 1), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("GRID",          (0, 0), (-1, -1), 0.4, C_BORDER),
    ]

    # Colour individual data rows
    for i, row_data in enumerate(rows[1:], start=1):
        status_cell = row_data[7]  # Status Paragraph
        # Extract status text from Paragraph text
        raw = subject_stats[i - 1].get("status", "") if not subject_stats[i-1].get("is_archived") else ""
        bg = _row_bg(raw)
        if bg:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
        else:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i),
                                C_WHITE if i % 2 == 1 else C_ROW_ALT))

    t.setStyle(TableStyle(style_cmds))
    return t


# ---------------------------------------------------------------------------
# Monthly breakdown table
# ---------------------------------------------------------------------------

def _monthly_table(monthly_data: list[dict], year: int, month: int) -> Table:
    from src.calculations import attendance_percentage

    month_name = datetime(year, month, 1).strftime("%B %Y")
    s = _styles()
    headers = ["Subject", "Present", "Absent", "Medical", "Total", "Attendance %"]
    rows = [headers]

    for r in monthly_data:
        p = r.get("present", 0) or 0
        a = r.get("absent",  0) or 0
        m = r.get("medical", 0) or 0
        pct = attendance_percentage(p, a)
        rows.append([
            Paragraph(r["subject_name"], s["cell"]),
            Paragraph(str(p), s["cell_center"]),
            Paragraph(str(a), s["cell_center"]),
            Paragraph(str(m), s["cell_center"]),
            Paragraph(str(p + a), s["cell_center"]),
            Paragraph(f"{pct:.1f}%" if pct is not None else "N/A", s["cell_center"]),
        ])

    avail_w = A4[0] - 3.0 * cm
    col_widths = [avail_w * 0.35, avail_w * 0.13, avail_w * 0.13,
                  avail_w * 0.13, avail_w * 0.13, avail_w * 0.13]

    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_TABLE_HDR),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("VALIGN",        (0, 0), (-1, 0), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("FONTSIZE",      (0, 1), (-1, -1), 9),
        ("VALIGN",        (0, 1), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_ROW_ALT]),
        ("GRID",          (0, 0), (-1, -1), 0.4, C_BORDER),
    ]))
    return t


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def generate_attendance_pdf(
    student: dict,
    semester_name: str,
    subject_stats: list[dict],
    dashboard_data: dict,
    monthly_data: Optional[list[dict]] = None,
    monthly_year:  Optional[int] = None,
    monthly_month: Optional[int] = None,
) -> bytes:
    """
    Generate a complete PDF attendance report.

    Parameters
    ----------
    student        : student profile dict (name, student_id, university, etc.)
    semester_name  : display name of the selected semester
    subject_stats  : list from services.get_subject_stats()
    dashboard_data : dict from services.get_dashboard_data()
    monthly_data   : optional list from models.get_monthly_summary()
    monthly_year   : year for the monthly section
    monthly_month  : month for the monthly section

    Returns
    -------
    bytes — PDF content ready for st.download_button()
    """
    buf = io.BytesIO()
    s = _styles()

    student_name = student.get("name") or student.get("username", "Student")
    threshold    = float(student.get("required_percentage") or 75.0)

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.0 * cm,
        title="Smart Attendance Report",
        author=student_name,
    )
    doc.addPageTemplates([_make_page_template(doc, student_name, semester_name)])

    story = []

    # ── Report title ──────────────────────────────────────────────────────
    story.append(Paragraph("Attendance Report", s["title"]))
    story.append(Paragraph(f"Semester: {semester_name}", s["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_PRIMARY, spaceAfter=10))

    # ── Student profile ───────────────────────────────────────────────────
    story.append(Paragraph("Student Profile", s["section"]))

    profile_rows = [
        ["Full Name",         student_name,
         "Student ID",        student.get("student_id") or "—"],
        ["University",        student.get("university") or "—",
         "Course",            student.get("course") or "—"],
        ["Semester",          student.get("semester") or "—",
         "Required Attendance", f"{threshold}%"],
        ["Username",          student.get("username", "—"),
         "Report Date",       datetime.now().strftime("%d %B %Y")],
    ]

    avail_w = A4[0] - 3.0 * cm
    profile_t = Table(
        profile_rows,
        colWidths=[avail_w * 0.2, avail_w * 0.3, avail_w * 0.2, avail_w * 0.3],
    )
    profile_t.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",      (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",     (0, 0), (0, -1), C_MUTED),
        ("TEXTCOLOR",     (2, 0), (2, -1), C_MUTED),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [C_WHITE, C_LIGHT_BG]),
        ("GRID",          (0, 0), (-1, -1), 0.4, C_BORDER),
    ]))
    story.append(profile_t)
    story.append(Spacer(1, 10))

    # ── KPI summary ───────────────────────────────────────────────────────
    story.append(Paragraph("Overall Summary", s["section"]))
    story.append(_kpi_table(
        overall_pct   = dashboard_data.get("overall_pct"),
        total_classes = dashboard_data.get("total_classes", 0),
        present       = dashboard_data.get("total_present", 0),
        absent        = dashboard_data.get("total_absent", 0),
        medical       = dashboard_data.get("total_medical", 0),
        num_subjects  = dashboard_data.get("num_subjects", 0),
        threshold     = threshold,
        status        = dashboard_data.get("overall_status", "No Data"),
    ))
    story.append(Spacer(1, 6))

    # ── Advisory message ──────────────────────────────────────────────────
    overall_pct = dashboard_data.get("overall_pct")
    if overall_pct is not None:
        if overall_pct < threshold:
            needed = dashboard_data.get("needs_to_attend")
            if needed and needed > 0:
                story.append(Paragraph(
                    f"⚠  Your overall attendance is {overall_pct:.1f}% — below the required {threshold}%. "
                    f"You need to attend the next {needed} consecutive class(es) to reach your target.",
                    s["advisory"],
                ))
        else:
            can_miss = dashboard_data.get("can_miss", 0)
            story.append(Paragraph(
                f"✓  Your attendance is {overall_pct:.1f}% — you are on track! "
                f"You can afford to miss up to {can_miss} more class(es) while staying above {threshold}%.",
                s["good"],
            ))

    # ── Subject-wise table ────────────────────────────────────────────────
    active = [s2 for s2 in subject_stats if not s2.get("is_archived")]
    if active:
        story.append(Paragraph("Subject-wise Attendance", s["section"]))
        story.append(_subject_table(active))
        story.append(Spacer(1, 6))

        # Per-subject advisories
        at_risk = [
            s2 for s2 in active
            if s2.get("percentage") is not None and s2["percentage"] < s2.get("threshold", threshold)
        ]
        if at_risk:
            story.append(Paragraph("Subjects Needing Attention", s["section"]))
            for sub in at_risk:
                pct_s = f"{sub['percentage']:.1f}%"
                needed = sub.get("needs_to_attend")
                msg = (
                    f"<b>{sub['subject_name']}</b> — Current: {pct_s} "
                    f"(Required: {sub.get('threshold', threshold)}%). "
                )
                if needed and needed > 0:
                    msg += f"Attend the next <b>{needed}</b> consecutive class(es) to recover."
                story.append(Paragraph(msg, s["advisory"]))

    # ── Monthly breakdown ─────────────────────────────────────────────────
    if monthly_data and monthly_year and monthly_month:
        month_label = datetime(monthly_year, monthly_month, 1).strftime("%B %Y")
        story.append(Paragraph(f"Monthly Breakdown — {month_label}", s["section"]))
        story.append(_monthly_table(monthly_data, monthly_year, monthly_month))
        story.append(Spacer(1, 6))

    # ── Calculation notes ─────────────────────────────────────────────────
    story.append(Paragraph("How Attendance Is Calculated", s["section"]))
    story.append(Paragraph(
        "Attendance % = (Present ÷ (Present + Absent)) × 100  "
        "— Medical Leave is excluded from both numerator and denominator.",
        s["muted"],
    ))
    story.append(Paragraph(
        "Classes needed to recover = ⌈(threshold% × total − present) ÷ (1 − threshold%)⌉  "
        "— smallest integer x such that (present + x) ÷ (total + x) ≥ required threshold.",
        s["muted"],
    ))
    story.append(Paragraph(
        "Classes you can miss = ⌊present ÷ threshold% − total⌋  "
        "— largest integer y such that present ÷ (total + y) ≥ required threshold.",
        s["muted"],
    ))

    doc.build(story)
    return buf.getvalue()
