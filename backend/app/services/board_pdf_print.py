# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from ..core.branding import branding
from ..models.board.meeting import BoardMeeting
from ..models.board.agenda import AgendaItem
from ..models.board.minutes import BoardMinutes
from ..models.board.vote import BoardVote
from .board_pdf_accessible import apply_pdf_ua_metadata

_LIBRARY_NAME = branding.library_name

# Print margins: 1.0" left (3-hole punch), 0.75" right, 1.0" top, 0.85" bottom
_LEFT = 1.0 * inch
_RIGHT = 0.75 * inch
_TOP = 1.0 * inch
_BOTTOM = 0.85 * inch

_PAGE_W, _PAGE_H = letter
_CONTENT_W = _PAGE_W - _LEFT - _RIGHT

_COLORS = {
    "primary": colors.HexColor("#2C1810"),
    "accent": colors.HexColor("#E89B44"),
    "muted": colors.HexColor("#666666"),
    "light_rule": colors.HexColor("#CCCCCC"),
}


def _styles():
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("PrintTitle", parent=ss["Title"], fontSize=18,
                                leading=22, textColor=_COLORS["primary"],
                                spaceAfter=6),
        "h1": ParagraphStyle("PrintH1", parent=ss["Heading1"], fontSize=14,
                             leading=17, textColor=_COLORS["primary"],
                             spaceBefore=12, spaceAfter=4),
        "h2": ParagraphStyle("PrintH2", parent=ss["Heading2"], fontSize=12,
                             leading=15, textColor=_COLORS["primary"],
                             spaceBefore=8, spaceAfter=3),
        "body": ParagraphStyle("PrintBody", parent=ss["Normal"], fontSize=10,
                               leading=13, spaceBefore=2, spaceAfter=2),
        "small": ParagraphStyle("PrintSmall", parent=ss["Normal"], fontSize=9,
                                leading=11, textColor=_COLORS["muted"]),
        "toc": ParagraphStyle("PrintTOC", parent=ss["Normal"], fontSize=11,
                              leading=18, leftIndent=12),
        "center": ParagraphStyle("PrintCenter", parent=ss["Normal"], fontSize=10,
                                 leading=13, alignment=TA_CENTER),
    }


def _header_footer(canvas, doc, meeting_date_str: str):
    canvas.saveState()
    canvas.setStrokeColor(_COLORS["light_rule"])
    canvas.setLineWidth(0.5)
    canvas.line(_LEFT, _PAGE_H - _TOP + 12, _PAGE_W - _RIGHT, _PAGE_H - _TOP + 12)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(_COLORS["muted"])
    canvas.drawString(_LEFT, _PAGE_H - _TOP + 16, f"{_LIBRARY_NAME} Board Packet")
    canvas.drawRightString(_PAGE_W - _RIGHT, _PAGE_H - _TOP + 16, meeting_date_str)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(_PAGE_W / 2, _BOTTOM - 16, f"Page {doc.page}")
    canvas.restoreState()


def _divider(elements, styles, section_title: str):
    elements.append(PageBreak())
    elements.append(Spacer(1, 2.5 * inch))
    elements.append(Paragraph(section_title, ParagraphStyle(
        "DividerTitle", parent=styles["title"], fontSize=24, alignment=TA_CENTER,
    )))
    elements.append(Spacer(1, 0.3 * inch))
    rule_data = [[""]]
    rule_table = Table(rule_data, colWidths=[2.5 * inch], rowHeights=[2])
    rule_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _COLORS["accent"]),
    ]))
    elements.append(rule_table)
    elements.append(PageBreak())


def generate_print_friendly_board_packet_pdf(
    meeting: BoardMeeting,
    agenda_items: list[AgendaItem],
    board_members: list[dict] | None = None,
    previous_minutes: BoardMinutes | None = None,
    pending_votes: list[BoardVote] | None = None,
    action_items: list[dict] | None = None,
    brief_content: str | None = None,
) -> bytes:
    styles = _styles()
    buffer = BytesIO()

    meeting_date_str = (
        meeting.scheduled_date.strftime("%B %d, %Y") if meeting.scheduled_date else "TBD"
    )
    meeting_time_str = (
        meeting.scheduled_date.strftime("%I:%M %p") if meeting.scheduled_date else ""
    )

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=_LEFT,
        rightMargin=_RIGHT,
        topMargin=_TOP,
        bottomMargin=_BOTTOM,
        title=f"Board Packet - {meeting_date_str}",
        author=_LIBRARY_NAME,
    )

    def on_page(canvas, doc):
        _header_footer(canvas, doc, meeting_date_str)

    def on_first_page(canvas, doc):
        pass  # No header/footer on cover

    elements = []

    # ---- Cover page ----
    elements.append(Spacer(1, 1.8 * inch))
    elements.append(Paragraph(_LIBRARY_NAME, ParagraphStyle(
        "CoverLib", parent=styles["title"], fontSize=22, alignment=TA_CENTER,
    )))
    elements.append(Paragraph("Board of Trustees", ParagraphStyle(
        "CoverBoard", parent=styles["h1"], fontSize=16, alignment=TA_CENTER,
        textColor=_COLORS["muted"],
    )))
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph("MEETING PACKET", ParagraphStyle(
        "CoverType", parent=styles["title"], fontSize=28, alignment=TA_CENTER,
    )))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(meeting_date_str, ParagraphStyle(
        "CoverDate", parent=styles["h1"], fontSize=16, alignment=TA_CENTER,
    )))
    if meeting_time_str:
        elements.append(Paragraph(meeting_time_str, ParagraphStyle(
            "CoverTime", parent=styles["center"], fontSize=12,
            textColor=_COLORS["muted"],
        )))
    if meeting.location:
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(meeting.location, ParagraphStyle(
            "CoverLoc", parent=styles["center"], fontSize=11,
            textColor=_COLORS["muted"],
        )))

    # ---- Table of contents ----
    elements.append(PageBreak())
    elements.append(Paragraph("Table of Contents", styles["title"]))
    elements.append(Spacer(1, 0.2 * inch))

    toc_items = ["Meeting Agenda"]
    if board_members:
        toc_items.append("Board Directory")
    if previous_minutes:
        toc_items.append("Previous Meeting Minutes")
    if pending_votes:
        toc_items.append("Pending Votes")
    if action_items:
        toc_items.append("Outstanding Action Items")
    if brief_content:
        toc_items.append("Meeting Brief")

    for i, item in enumerate(toc_items, 1):
        elements.append(Paragraph(f"{i}. {item}", styles["toc"]))

    # ---- Section 1: Agenda ----
    _divider(elements, styles, "Meeting Agenda")
    elements.append(Paragraph(f"{_LIBRARY_NAME} -- Board of Trustees", styles["small"]))
    elements.append(Paragraph(
        f"{meeting.meeting_type or Regular} Meeting -- {meeting_date_str}",
        styles["h1"],
    ))
    elements.append(Spacer(1, 0.1 * inch))

    for item in agenda_items:
        prefix = f"{item.item_number}. " if item.item_number else ""
        elements.append(Paragraph(f"<b>{prefix}{item.title}</b>", styles["body"]))
        if item.description:
            elements.append(Paragraph(item.description, styles["small"]))
        if item.estimated_duration_minutes:
            elements.append(Paragraph(
                f"Estimated: {item.estimated_duration_minutes} min", styles["small"],
            ))
        elements.append(Spacer(1, 0.05 * inch))

    # ---- Section 2: Board directory ----
    if board_members:
        _divider(elements, styles, "Board Directory")
        dir_data = [["Name", "Position", "Email", "Term Ends"]]
        for m in board_members:
            dir_data.append([
                m.get("name", ""),
                m.get("position", "").replace("_", " ").title(),
                m.get("email", "") or "",
                m.get("term_end", "") or "",
            ])
        dir_table = Table(dir_data, colWidths=[1.8*inch, 1.3*inch, 2.0*inch, 1.0*inch])
        dir_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEADING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, 0), 1, _COLORS["primary"]),
            ("LINEBELOW", (0, 1), (-1, -1), 0.5, _COLORS["light_rule"]),
        ]))
        elements.append(dir_table)

    # ---- Section 3: Previous minutes ----
    if previous_minutes:
        _divider(elements, styles, "Previous Meeting Minutes")
        if previous_minutes.body:
            for para in previous_minutes.body.split("\n\n"):
                if para.strip():
                    elements.append(Paragraph(para.strip(), styles["body"]))
        elif previous_minutes.sections:
            for section in sorted(previous_minutes.sections, key=lambda x: x.get("order", 0)):
                elements.append(Paragraph(section.get("title", ""), styles["h2"]))
                elements.append(Paragraph(section.get("content", ""), styles["body"]))
        if previous_minutes.approved:
            elements.append(Spacer(1, 0.15 * inch))
            approval_date = (
                previous_minutes.approved_at.strftime("%B %d, %Y")
                if previous_minutes.approved_at else "date unknown"
            )
            elements.append(Paragraph(f"<i>Approved {approval_date}</i>", styles["small"]))

    # ---- Section 4: Pending votes ----
    if pending_votes:
        _divider(elements, styles, "Pending Votes")
        for vote in pending_votes:
            elements.append(Paragraph(f"<b>{vote.title}</b>", styles["body"]))
            if vote.description:
                elements.append(Paragraph(vote.description, styles["small"]))
            elements.append(Paragraph(
                f"Type: {vote.vote_type or simple_majority} | Status: {vote.status}",
                styles["small"],
            ))
            elements.append(Spacer(1, 0.1 * inch))

    # ---- Section 5: Action items ----
    if action_items:
        _divider(elements, styles, "Outstanding Action Items")
        ai_data = [["Item", "Assigned To", "Due Date", "Status"]]
        for item in action_items:
            ai_data.append([
                Paragraph(item.get("title", ""), styles["small"]),
                item.get("assigned_to", ""),
                item.get("due_date", ""),
                item.get("status", "").replace("_", " ").title(),
            ])
        ai_table = Table(ai_data, colWidths=[2.5*inch, 1.3*inch, 1.0*inch, 1.0*inch])
        ai_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEADING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, 0), 1, _COLORS["primary"]),
            ("LINEBELOW", (0, 1), (-1, -1), 0.5, _COLORS["light_rule"]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(ai_table)

    # ---- Section 6: Meeting brief ----
    if brief_content:
        _divider(elements, styles, "Meeting Brief")
        for para in brief_content.split("\n\n"):
            if para.strip():
                elements.append(Paragraph(para.strip(), styles["body"]))

    doc.build(elements, onFirstPage=on_first_page, onLaterPages=on_page)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return apply_pdf_ua_metadata(
        pdf_bytes,
        title=f"Board Packet - {meeting_date_str}",
        author=_LIBRARY_NAME,
        subject="Print-Friendly Board Meeting Packet",
    )
