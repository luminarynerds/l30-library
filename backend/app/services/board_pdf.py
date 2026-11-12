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
    PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
)

from ..models.board.meeting import BoardMeeting
from ..models.board.agenda import AgendaItem
from ..models.board.minutes import BoardMinutes
from ..models.board.vote import BoardVote, BoardVoteCast

import os
from ..core.branding import branding
from .board_pdf_accessible import AccessibleDocTemplate, apply_pdf_ua_metadata

_LIBRARY_NAME = branding.library_name

# Library branding colors (consistent with other PDFs)
LIBRARY_COLORS = {
    "primary": colors.HexColor("#2C1810"),      # Dark brown
    "secondary": colors.HexColor("#5C4F3D"),    # Medium brown
    "accent": colors.HexColor("#E89B44"),       # Orange
    "success": colors.HexColor("#2E7D32"),      # Green
    "danger": colors.HexColor("#C41E3A"),       # Red
    "warning": colors.HexColor("#D97706"),      # Amber
    "info": colors.HexColor("#1565C0"),         # Blue
    "light": colors.HexColor("#F0EDE8"),        # Light beige
    "text": colors.HexColor("#333333"),         # Dark gray
    "muted": colors.HexColor("#666666"),        # Medium gray
}

# Library configuration
LIBRARY_CONFIG = {
    "name": _LIBRARY_NAME,
    "short_name": branding.library_short_name,
    "address": branding.address_line1,
    "city_state_zip": branding.address_line2,
    "phone": branding.phone,
    "email": branding.contact_email,
    "website": branding.domain,
}


def get_board_styles() -> dict:
    styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "BoardTitle",
            parent=styles["Heading1"],
            fontSize=20,
            textColor=LIBRARY_COLORS["primary"],
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        ),
        "subtitle": ParagraphStyle(
            "BoardSubtitle",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=LIBRARY_COLORS["secondary"],
            spaceAfter=20,
            alignment=TA_CENTER,
        ),
        "heading": ParagraphStyle(
            "BoardHeading",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=LIBRARY_COLORS["primary"],
            spaceAfter=10,
            spaceBefore=15,
            fontName="Helvetica-Bold",
        ),
        "subheading": ParagraphStyle(
            "BoardSubheading",
            parent=styles["Heading3"],
            fontSize=12,
            textColor=LIBRARY_COLORS["secondary"],
            spaceAfter=8,
            spaceBefore=10,
            fontName="Helvetica-Bold",
        ),
        "body": ParagraphStyle(
            "BoardBody",
            parent=styles["Normal"],
            fontSize=10,
            textColor=LIBRARY_COLORS["text"],
            spaceAfter=8,
            leading=14,
        ),
        "small": ParagraphStyle(
            "BoardSmall",
            parent=styles["Normal"],
            fontSize=9,
            textColor=LIBRARY_COLORS["muted"],
            spaceAfter=4,
        ),
        "footer": ParagraphStyle(
            "BoardFooter",
            parent=styles["Normal"],
            fontSize=8,
            textColor=LIBRARY_COLORS["muted"],
            alignment=TA_CENTER,
        ),
        "agenda_item": ParagraphStyle(
            "AgendaItem",
            parent=styles["Normal"],
            fontSize=11,
            textColor=LIBRARY_COLORS["text"],
            spaceAfter=4,
            leftIndent=20,
        ),
        "agenda_number": ParagraphStyle(
            "AgendaNumber",
            parent=styles["Normal"],
            fontSize=11,
            textColor=LIBRARY_COLORS["primary"],
            fontName="Helvetica-Bold",
        ),
        "notice_title": ParagraphStyle(
            "NoticeTitle",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=LIBRARY_COLORS["primary"],
            spaceAfter=10,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        ),
        "notice_important": ParagraphStyle(
            "NoticeImportant",
            parent=styles["Normal"],
            fontSize=11,
            textColor=LIBRARY_COLORS["danger"],
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            spaceAfter=15,
        ),
        "vote_passed": ParagraphStyle(
            "VotePassed",
            parent=styles["Normal"],
            fontSize=14,
            textColor=LIBRARY_COLORS["success"],
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
        "vote_failed": ParagraphStyle(
            "VoteFailed",
            parent=styles["Normal"],
            fontSize=14,
            textColor=LIBRARY_COLORS["danger"],
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
    }


def build_library_header(elements: list, styles: dict, document_type: str):
    # Library name
    elements.append(Paragraph(LIBRARY_CONFIG["name"], styles["title"]))
    elements.append(Paragraph("Board of Trustees", styles["subtitle"]))

    # Document type banner
    banner_data = [[Paragraph(document_type.upper(), ParagraphStyle(
        "Banner",
        fontSize=12,
        textColor=colors.white,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
    ))]]
    banner = Table(banner_data, colWidths=[7.5 * inch])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIBRARY_COLORS["primary"]),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(banner)
    elements.append(Spacer(1, 0.2 * inch))


def build_meeting_info_box(elements: list, meeting: BoardMeeting, styles: dict):
    meeting_date = meeting.scheduled_date.strftime("%A, %B %d, %Y") if meeting.scheduled_date else "TBD"
    start_time = meeting.start_time.strftime("%I:%M %p") if meeting.start_time else "TBD"
    end_time = meeting.end_time.strftime("%I:%M %p") if meeting.end_time else ""
    time_str = f"{start_time}" + (f" - {end_time}" if end_time else "")

    location = meeting.location or "TBD"
    if meeting.is_virtual and meeting.virtual_meeting_url:
        location = f"Virtual Meeting\n{meeting.virtual_meeting_url}"
    elif meeting.is_virtual:
        location = "Virtual Meeting (link to be provided)"

    info_data = [
        ["Date:", meeting_date],
        ["Time:", time_str],
        ["Location:", location],
    ]

    if meeting.meeting_type:
        meeting_type_display = meeting.meeting_type.replace("_", " ").title()
        info_data.insert(0, ["Meeting Type:", f"{meeting_type_display} Meeting"])

    info_table = Table(info_data, colWidths=[1.5 * inch, 5.5 * inch])
    info_table.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
        ("FONT", (1, 0), (1, -1), "Helvetica", 10),
        ("TEXTCOLOR", (0, 0), (0, -1), LIBRARY_COLORS["secondary"]),
        ("TEXTCOLOR", (1, 0), (1, -1), LIBRARY_COLORS["text"]),
        ("BACKGROUND", (0, 0), (-1, -1), LIBRARY_COLORS["light"]),
        ("BOX", (0, 0), (-1, -1), 1, LIBRARY_COLORS["secondary"]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.2 * inch))


def build_footer(elements: list, styles: dict, page_label: str = ""):
    elements.append(Spacer(1, 0.3 * inch))

    # Separator
    sep_data = [[""]]
    sep = Table(sep_data, colWidths=[7.5 * inch])
    sep.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.grey),
    ]))
    elements.append(sep)
    elements.append(Spacer(1, 0.1 * inch))

    footer_text = f"""
    {LIBRARY_CONFIG["name"]}<br/>
    {LIBRARY_CONFIG["address"]}, {LIBRARY_CONFIG["city_state_zip"]}<br/>
    Phone: {LIBRARY_CONFIG["phone"]} | Email: {LIBRARY_CONFIG["email"]}<br/>
    Website: {LIBRARY_CONFIG["website"]}
    """
    elements.append(Paragraph(footer_text, styles["footer"]))

    if page_label:
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(page_label, styles["footer"]))


def generate_meeting_agenda_pdf(
    meeting: BoardMeeting,
    agenda_items: list[AgendaItem],
    board_members: list[dict] | None = None,
) -> bytes:
    buffer = BytesIO()
    doc = AccessibleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.75 * inch,
    )

    elements = []
    styles = get_board_styles()

    # Header
    build_library_header(elements, styles, "Meeting Agenda")

    # Meeting info
    build_meeting_info_box(elements, meeting, styles)

    # Meeting title
    if meeting.title:
        elements.append(Paragraph(meeting.title, styles["heading"]))

    # Agenda items
    elements.append(Paragraph("AGENDA", styles["heading"]))

    # Standard opening items
    standard_opening = [
        ("I.", "Call to Order"),
        ("II.", "Roll Call"),
        ("III.", "Approval of Agenda"),
        ("IV.", "Approval of Minutes from Previous Meeting"),
        ("V.", "Public Comment Period"),
    ]

    for num, item in standard_opening:
        item_row = [[
            Paragraph(num, styles["agenda_number"]),
            Paragraph(item, styles["agenda_item"])
        ]]
        item_table = Table(item_row, colWidths=[0.5 * inch, 6.5 * inch])
        item_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(item_table)

    # Custom agenda items
    if agenda_items:
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph("VI. Business Items", styles["subheading"]))

        for item in agenda_items:
            item_text = f"<b>{item.item_number}.</b> {item.title}"
            if item.presenter:
                item_text += f" <i>(Presenter: {item.presenter})</i>"
            if item.estimated_duration_minutes:
                item_text += f" [{item.estimated_duration_minutes} min]"

            elements.append(Paragraph(item_text, styles["agenda_item"]))

            if item.description:
                desc_style = ParagraphStyle(
                    "AgendaDesc",
                    parent=styles["small"],
                    leftIndent=40,
                )
                elements.append(Paragraph(item.description, desc_style))

            if item.requires_action:
                action_text = f"<i>Action Required: {item.action_type or 'Vote/Decision'}</i>"
                action_style = ParagraphStyle(
                    "AgendaAction",
                    parent=styles["small"],
                    leftIndent=40,
                    textColor=LIBRARY_COLORS["accent"],
                )
                elements.append(Paragraph(action_text, action_style))

    # Standard closing items
    elements.append(Spacer(1, 0.1 * inch))
    standard_closing = [
        ("VII.", "Reports"),
        ("", "A. Director's Report"),
        ("", "B. Committee Reports"),
        ("", "C. Financial Report"),
        ("VIII.", "Old Business"),
        ("IX.", "New Business"),
        ("X.", "Announcements"),
        ("XI.", "Adjournment"),
    ]

    for num, item in standard_closing:
        if num:
            item_row = [[
                Paragraph(num, styles["agenda_number"]),
                Paragraph(item, styles["agenda_item"])
            ]]
        else:
            item_row = [[
                Paragraph("", styles["agenda_number"]),
                Paragraph(item, ParagraphStyle(
                    "SubItem",
                    parent=styles["agenda_item"],
                    leftIndent=20,
                ))
            ]]
        item_table = Table(item_row, colWidths=[0.5 * inch, 6.5 * inch])
        item_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(item_table)

    # Public comment notice
    if meeting.public_comment_enabled:
        elements.append(Spacer(1, 0.2 * inch))
        comment_box = [[Paragraph(
            "<b>PUBLIC COMMENT</b><br/>" +
            (meeting.public_comment_instructions or
             "Members of the public are welcome to address the Board during the Public Comment period. "
             "Please sign in at the meeting and limit comments to 3 minutes."),
            ParagraphStyle("CommentBox", fontSize=9, textColor=LIBRARY_COLORS["text"], leading=12)
        )]]
        comment_table = Table(comment_box, colWidths=[7 * inch])
        comment_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E3F2FD")),
            ("BOX", (0, 0), (-1, -1), 1, LIBRARY_COLORS["info"]),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(comment_table)

    # Accessibility info
    if meeting.accessibility_info:
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(
            f"<b>Accessibility:</b> {meeting.accessibility_info}",
            styles["small"]
        ))

    # Footer
    build_footer(elements, styles, f"Agenda generated {datetime.now(timezone.utc).strftime('%B %d, %Y')}")

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


def generate_meeting_minutes_pdf(
    meeting: BoardMeeting,
    minutes: BoardMinutes,
    agenda_items: list[AgendaItem] | None = None,
) -> bytes:
    buffer = BytesIO()
    doc = AccessibleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.75 * inch,
    )

    elements = []
    styles = get_board_styles()

    # Header
    build_library_header(elements, styles, "Meeting Minutes")

    # Meeting info
    build_meeting_info_box(elements, meeting, styles)

    # Status badge
    status_text = minutes.status.upper() if hasattr(minutes.status, 'upper') else str(minutes.status).upper()
    if status_text in ["APPROVED", "PUBLISHED"]:
        status_color = LIBRARY_COLORS["success"]
    elif status_text == "DRAFT":
        status_color = LIBRARY_COLORS["warning"]
    else:
        status_color = LIBRARY_COLORS["muted"]

    status_badge = [[Paragraph(f"Status: {status_text}", ParagraphStyle(
        "StatusBadge",
        fontSize=10,
        textColor=colors.white,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
    ))]]
    status_table = Table(status_badge, colWidths=[2 * inch])
    status_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), status_color),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    centered = Table([[status_table]], colWidths=[7.5 * inch])
    centered.setStyle(TableStyle([("ALIGN", (0, 0), (0, 0), "RIGHT")]))
    elements.append(centered)
    elements.append(Spacer(1, 0.1 * inch))

    # Attendance
    elements.append(Paragraph("ATTENDANCE", styles["heading"]))

    if minutes.members_present:
        present_names = ", ".join([m.get("name", "Unknown") for m in minutes.members_present])
        elements.append(Paragraph(f"<b>Members Present:</b> {present_names}", styles["body"]))

    if minutes.members_absent:
        absent_names = ", ".join([m.get("name", "Unknown") for m in minutes.members_absent])
        elements.append(Paragraph(f"<b>Members Absent:</b> {absent_names}", styles["body"]))

    if minutes.members_excused:
        excused_names = ", ".join([m.get("name", "Unknown") for m in minutes.members_excused])
        elements.append(Paragraph(f"<b>Members Excused:</b> {excused_names}", styles["body"]))

    if minutes.guests_present:
        guest_names = ", ".join([g.get("name", "Unknown") for g in minutes.guests_present])
        elements.append(Paragraph(f"<b>Guests Present:</b> {guest_names}", styles["body"]))

    if minutes.quorum_count:
        elements.append(Paragraph(f"<b>Quorum:</b> {minutes.quorum_count}", styles["body"]))

    # Call to order
    if minutes.meeting_called_to_order_at:
        call_time = minutes.meeting_called_to_order_at.strftime("%I:%M %p")
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(f"The meeting was called to order at {call_time}.", styles["body"]))

    # Minutes sections
    if minutes.sections:
        for section in sorted(minutes.sections, key=lambda x: x.get("order", 0)):
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(Paragraph(section.get("title", "Section"), styles["subheading"]))
            elements.append(Paragraph(section.get("content", ""), styles["body"]))

    # Agenda items with actions
    if agenda_items:
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph("BUSINESS ITEMS", styles["heading"]))

        for item in agenda_items:
            elements.append(Paragraph(
                f"<b>{item.item_number}. {item.title}</b>",
                styles["body"]
            ))
            if item.description:
                elements.append(Paragraph(item.description, styles["small"]))
            if item.action_taken:
                elements.append(Paragraph(
                    f"<b>Action Taken:</b> {item.action_taken}",
                    ParagraphStyle("ActionTaken", parent=styles["body"], textColor=LIBRARY_COLORS["success"])
                ))
            if item.vote_result:
                elements.append(Paragraph(
                    f"<b>Vote Result:</b> {item.vote_result}",
                    styles["body"]
                ))

    # Adjournment
    if minutes.meeting_adjourned_at:
        adjourn_time = minutes.meeting_adjourned_at.strftime("%I:%M %p")
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(f"The meeting was adjourned at {adjourn_time}.", styles["body"]))

    # Approval info
    if minutes.approved and minutes.approved_at:
        elements.append(Spacer(1, 0.2 * inch))
        approval_date = minutes.approved_at.strftime("%B %d, %Y")
        approval_text = f"These minutes were approved on {approval_date}"
        if minutes.approval_vote_result:
            approval_text += f" ({minutes.approval_vote_result})"
        elements.append(Paragraph(approval_text, ParagraphStyle(
            "Approval",
            parent=styles["body"],
            fontName="Helvetica-Oblique",
        )))

    # Recording link
    if minutes.recording_url:
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(
            f"<b>Meeting Recording:</b> {minutes.recording_url}",
            styles["small"]
        ))

    # Public notes
    if minutes.notes:
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph("<b>Notes:</b>", styles["body"]))
        elements.append(Paragraph(minutes.notes, styles["small"]))

    # Footer
    prepared_text = ""
    if minutes.prepared_by:
        prepared_text = f"Prepared by: {minutes.prepared_by.first_name} {minutes.prepared_by.last_name}"
    build_footer(elements, styles, prepared_text)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


def generate_public_notice_pdf(
    meeting: BoardMeeting,
    agenda_items: list[AgendaItem] | None = None,
    posting_date: datetime | None = None,
) -> bytes:
    buffer = BytesIO()
    doc = AccessibleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    elements = []
    styles = get_board_styles()

    # Large title for posting
    elements.append(Paragraph("PUBLIC NOTICE", styles["notice_title"]))
    elements.append(Paragraph("BOARD OF TRUSTEES MEETING", styles["notice_title"]))
    elements.append(Spacer(1, 0.2 * inch))

    # Library name
    elements.append(Paragraph(LIBRARY_CONFIG["name"], styles["subtitle"]))
    elements.append(Spacer(1, 0.3 * inch))

    # Meeting type badge
    meeting_type = meeting.meeting_type.replace("_", " ").upper() if meeting.meeting_type else "REGULAR"
    if meeting_type in ["SPECIAL", "EMERGENCY"]:
        elements.append(Paragraph(f"*** {meeting_type} MEETING ***", styles["notice_important"]))

    # Meeting details in large format
    meeting_date = meeting.scheduled_date.strftime("%A, %B %d, %Y") if meeting.scheduled_date else "TBD"
    start_time = meeting.start_time.strftime("%I:%M %p") if meeting.start_time else "TBD"

    details_data = [
        [Paragraph("<b>DATE:</b>", styles["body"]), Paragraph(meeting_date, ParagraphStyle(
            "DetailValue", fontSize=14, fontName="Helvetica-Bold", textColor=LIBRARY_COLORS["primary"]
        ))],
        [Paragraph("<b>TIME:</b>", styles["body"]), Paragraph(start_time, ParagraphStyle(
            "DetailValue", fontSize=14, fontName="Helvetica-Bold", textColor=LIBRARY_COLORS["primary"]
        ))],
        [Paragraph("<b>LOCATION:</b>", styles["body"]), Paragraph(
            meeting.location or "TBD",
            ParagraphStyle("DetailValue", fontSize=12, fontName="Helvetica-Bold", textColor=LIBRARY_COLORS["primary"])
        )],
    ]

    if meeting.is_virtual:
        details_data.append([
            Paragraph("<b>VIRTUAL ACCESS:</b>", styles["body"]),
            Paragraph(meeting.virtual_meeting_url or "Link to be provided", styles["body"])
        ])

    details_table = Table(details_data, colWidths=[1.5 * inch, 5 * inch])
    details_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, -1), LIBRARY_COLORS["light"]),
        ("BOX", (0, 0), (-1, -1), 2, LIBRARY_COLORS["primary"]),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Purpose/Title
    if meeting.title:
        elements.append(Paragraph(f"<b>Purpose:</b> {meeting.title}", styles["body"]))
        elements.append(Spacer(1, 0.1 * inch))

    # Tentative agenda
    if agenda_items:
        elements.append(Paragraph("<b>TENTATIVE AGENDA</b>", styles["subheading"]))
        for item in agenda_items:
            elements.append(Paragraph(f"• {item.title}", styles["body"]))
        elements.append(Spacer(1, 0.1 * inch))

    # Executive session notice
    if meeting.has_executive_session:
        exec_box = [[Paragraph(
            "<b>EXECUTIVE SESSION NOTICE</b><br/>" +
            "The Board may convene in executive session as permitted by law." +
            (f"<br/>Reason: {meeting.executive_session_reason}" if meeting.executive_session_reason else ""),
            ParagraphStyle("ExecBox", fontSize=10, textColor=LIBRARY_COLORS["text"], leading=14)
        )]]
        exec_table = Table(exec_box, colWidths=[6 * inch])
        exec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF9E6")),
            ("BOX", (0, 0), (-1, -1), 1, LIBRARY_COLORS["warning"]),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(exec_table)
        elements.append(Spacer(1, 0.2 * inch))

    # Public participation
    elements.append(Spacer(1, 0.1 * inch))
    public_text = """
    <b>PUBLIC PARTICIPATION</b><br/><br/>
    The public is welcome to attend this meeting. A public comment period will be provided
    for members of the community to address the Board. Sign-in is available at the meeting.
    """
    if meeting.public_comment_instructions:
        public_text += f"<br/><br/>{meeting.public_comment_instructions}"

    elements.append(Paragraph(public_text, styles["body"]))

    # Accessibility
    if meeting.accessibility_info:
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(
            f"<b>Accessibility:</b> {meeting.accessibility_info}",
            styles["body"]
        ))
    else:
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(
            "<b>Accessibility:</b> Persons with disabilities who need assistance to participate "
            "should contact the library at least 48 hours in advance.",
            styles["body"]
        ))

    # Contact info
    elements.append(Spacer(1, 0.2 * inch))
    contact_box = [[Paragraph(
        f"<b>For more information contact:</b><br/>"
        f"{LIBRARY_CONFIG['name']}<br/>"
        f"Phone: {LIBRARY_CONFIG['phone']}<br/>"
        f"Email: {LIBRARY_CONFIG['email']}",
        styles["body"]
    )]]
    contact_table = Table(contact_box, colWidths=[6 * inch])
    contact_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIBRARY_COLORS["light"]),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(contact_table)

    # Posting info
    elements.append(Spacer(1, 0.3 * inch))
    post_date = posting_date or datetime.now(timezone.utc)
    elements.append(Paragraph(
        f"<i>Posted: {post_date.strftime('%B %d, %Y at %I:%M %p')}</i>",
        styles["footer"]
    ))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


def generate_vote_record_pdf(
    vote: BoardVote,
    votes_cast: list[BoardVoteCast],
) -> bytes:
    buffer = BytesIO()
    doc = AccessibleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.75 * inch,
    )

    elements = []
    styles = get_board_styles()

    # Header
    build_library_header(elements, styles, "Official Vote Record")

    # Vote title
    elements.append(Paragraph(vote.title, styles["heading"]))

    # Vote info
    vote_type_display = vote.vote_type.replace("_", " ").title() if vote.vote_type else "Simple Majority"
    opens_at = vote.opens_at.strftime("%B %d, %Y at %I:%M %p") if vote.opens_at else "N/A"
    closes_at = vote.closes_at.strftime("%B %d, %Y at %I:%M %p") if vote.closes_at else "N/A"

    info_data = [
        ["Vote Type:", vote_type_display],
        ["Voting Opened:", opens_at],
        ["Voting Closed:", closes_at],
        ["Quorum Required:", str(vote.quorum_required)],
    ]

    if vote.meeting:
        meeting_date = vote.meeting.scheduled_date.strftime("%B %d, %Y") if vote.meeting.scheduled_date else "N/A"
        info_data.insert(0, ["Meeting:", meeting_date])

    info_table = Table(info_data, colWidths=[1.75 * inch, 5.25 * inch])
    info_table.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
        ("FONT", (1, 0), (1, -1), "Helvetica", 10),
        ("BACKGROUND", (0, 0), (-1, -1), LIBRARY_COLORS["light"]),
        ("BOX", (0, 0), (-1, -1), 1, LIBRARY_COLORS["secondary"]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Description
    if vote.description:
        elements.append(Paragraph("<b>Motion/Resolution:</b>", styles["body"]))
        elements.append(Paragraph(vote.description, styles["body"]))
        elements.append(Spacer(1, 0.2 * inch))

    # Results box
    if vote.passed is not None:
        result_text = "MOTION PASSED" if vote.passed else "MOTION FAILED"
        result_style = styles["vote_passed"] if vote.passed else styles["vote_failed"]
        result_color = LIBRARY_COLORS["success"] if vote.passed else LIBRARY_COLORS["danger"]

        result_box = [[Paragraph(result_text, result_style)]]
        result_table = Table(result_box, colWidths=[4 * inch])
        result_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E8F5E9") if vote.passed else colors.HexColor("#FFEBEE")),
            ("BOX", (0, 0), (-1, -1), 2, result_color),
            ("TOPPADDING", (0, 0), (-1, -1), 15),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 15),
        ]))
        centered = Table([[result_table]], colWidths=[7.5 * inch])
        centered.setStyle(TableStyle([("ALIGN", (0, 0), (0, 0), "CENTER")]))
        elements.append(centered)
        elements.append(Spacer(1, 0.2 * inch))

    # Tally
    elements.append(Paragraph("VOTE TALLY", styles["subheading"]))

    tally_data = [
        ["Yes", str(vote.final_tally_yes or 0)],
        ["No", str(vote.final_tally_no or 0)],
        ["Abstain", str(vote.final_tally_abstain or 0)],
        ["Total Votes Cast", str((vote.final_tally_yes or 0) + (vote.final_tally_no or 0) + (vote.final_tally_abstain or 0))],
    ]

    tally_table = Table(tally_data, colWidths=[2 * inch, 1 * inch])
    tally_table.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 11),
        ("FONT", (1, 0), (1, -1), "Helvetica-Bold", 11),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#E8F5E9")),  # Yes - green
        ("BACKGROUND", (0, 1), (0, 1), colors.HexColor("#FFEBEE")),  # No - red
        ("BACKGROUND", (0, 2), (0, 2), colors.HexColor("#FFF9E6")),  # Abstain - yellow
        ("BACKGROUND", (0, 3), (-1, 3), LIBRARY_COLORS["light"]),   # Total
        ("BOX", (0, 0), (-1, -1), 1, colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    centered = Table([[tally_table]], colWidths=[7.5 * inch])
    centered.setStyle(TableStyle([("ALIGN", (0, 0), (0, 0), "CENTER")]))
    elements.append(centered)
    elements.append(Spacer(1, 0.2 * inch))

    # Individual votes
    if votes_cast:
        elements.append(Paragraph("INDIVIDUAL VOTES", styles["subheading"]))

        vote_rows = [["Board Member", "Vote", "Comment"]]
        for vc in votes_cast:
            member_name = f"{vc.board_member.first_name} {vc.board_member.last_name}" if vc.board_member else "Unknown"
            choice = vc.choice.upper() if vc.choice else "N/A"
            comment = vc.comment[:50] + "..." if vc.comment and len(vc.comment) > 50 else (vc.comment or "")
            vote_rows.append([member_name, choice, comment])

        vote_table = Table(vote_rows, colWidths=[2.5 * inch, 1 * inch, 3 * inch])
        vote_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIBRARY_COLORS["secondary"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 10),
            ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 1, colors.grey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(vote_table)

    # Footer
    closed_text = ""
    if vote.closed_at_actual:
        closed_text = f"Vote closed: {vote.closed_at_actual.strftime('%B %d, %Y at %I:%M %p')}"
    build_footer(elements, styles, closed_text)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


def generate_board_packet_pdf(
    meeting: BoardMeeting,
    agenda_items: list[AgendaItem],
    board_members: list[dict] | None = None,
    previous_minutes: BoardMinutes | None = None,
    pending_votes: list[BoardVote] | None = None,
    action_items: list[dict] | None = None,
    brief_content: str | None = None,
) -> bytes:
    buffer = BytesIO()
    doc = AccessibleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.75 * inch,
    )

    elements = []
    styles = get_board_styles()

    # === COVER PAGE ===
    elements.append(Spacer(1, 1.5 * inch))
    elements.append(Paragraph(LIBRARY_CONFIG["name"], styles["title"]))
    elements.append(Paragraph("Board of Trustees", styles["subtitle"]))
    elements.append(Spacer(1, 0.5 * inch))

    # Large title
    elements.append(Paragraph("BOARD PACKET", ParagraphStyle(
        "PacketTitle",
        fontSize=28,
        fontName="Helvetica-Bold",
        textColor=LIBRARY_COLORS["primary"],
        alignment=TA_CENTER,
        spaceAfter=30,
    )))

    # Meeting date large
    meeting_date = meeting.scheduled_date.strftime("%B %d, %Y") if meeting.scheduled_date else "TBD"
    elements.append(Paragraph(meeting_date, ParagraphStyle(
        "PacketDate",
        fontSize=18,
        textColor=LIBRARY_COLORS["secondary"],
        alignment=TA_CENTER,
        spaceAfter=20,
    )))

    # Meeting type
    meeting_type = meeting.meeting_type.replace("_", " ").title() if meeting.meeting_type else "Regular"
    elements.append(Paragraph(f"{meeting_type} Meeting", styles["subtitle"]))

    elements.append(Spacer(1, 1 * inch))

    # Table of contents
    elements.append(Paragraph("CONTENTS", styles["heading"]))
    toc_items = [
        "1. Meeting Agenda",
        "2. Board Member Directory",
    ]
    if previous_minutes:
        toc_items.append("3. Previous Meeting Minutes (for approval)")
    if pending_votes:
        toc_items.append(f"{'4' if previous_minutes else '3'}. Pending Motions/Votes")
    if action_items:
        toc_items.append(f"{'5' if previous_minutes else '4'}. Outstanding Action Items")
    if brief_content:
        toc_items.append("Meeting Preparation Brief")

    for item in toc_items:
        elements.append(Paragraph(item, styles["body"]))

    elements.append(PageBreak())

    # === AGENDA SECTION ===
    build_library_header(elements, styles, "Meeting Agenda")
    build_meeting_info_box(elements, meeting, styles)

    if meeting.title:
        elements.append(Paragraph(meeting.title, styles["heading"]))

    elements.append(Paragraph("AGENDA", styles["heading"]))

    # Standard items + custom items (abbreviated version)
    all_items = [
        ("I.", "Call to Order"),
        ("II.", "Roll Call"),
        ("III.", "Approval of Agenda"),
        ("IV.", "Approval of Previous Minutes"),
        ("V.", "Public Comment"),
    ]

    for num, item in all_items:
        elements.append(Paragraph(f"<b>{num}</b> {item}", styles["agenda_item"]))

    if agenda_items:
        elements.append(Paragraph("<b>VI. Business Items</b>", styles["agenda_item"]))
        for item in agenda_items:
            elements.append(Paragraph(
                f"    {item.item_number}. {item.title}",
                styles["body"]
            ))

    elements.append(Paragraph("<b>VII.</b> Reports", styles["agenda_item"]))
    elements.append(Paragraph("<b>VIII.</b> Old Business", styles["agenda_item"]))
    elements.append(Paragraph("<b>IX.</b> New Business", styles["agenda_item"]))
    elements.append(Paragraph("<b>X.</b> Adjournment", styles["agenda_item"]))

    elements.append(PageBreak())

    # === BOARD MEMBERS ===
    build_library_header(elements, styles, "Board of Trustees Directory")

    if board_members:
        for member in board_members:
            member_text = f"<b>{member.get('name', 'Unknown')}</b>"
            if member.get('position'):
                member_text += f" - {member['position'].replace('_', ' ').title()}"
            elements.append(Paragraph(member_text, styles["body"]))
            if member.get('email'):
                elements.append(Paragraph(f"    Email: {member['email']}", styles["small"]))
            if member.get('term_end'):
                elements.append(Paragraph(f"    Term Ends: {member['term_end']}", styles["small"]))
    else:
        elements.append(Paragraph("Board member directory not available.", styles["body"]))

    # === PREVIOUS MINUTES ===
    if previous_minutes:
        elements.append(PageBreak())
        build_library_header(elements, styles, "Previous Meeting Minutes")
        elements.append(Paragraph(
            "<i>These minutes are presented for approval at the upcoming meeting.</i>",
            styles["small"]
        ))
        elements.append(Spacer(1, 0.2 * inch))

        if previous_minutes.sections:
            for section in sorted(previous_minutes.sections, key=lambda x: x.get("order", 0)):
                elements.append(Paragraph(section.get("title", ""), styles["subheading"]))
                elements.append(Paragraph(section.get("content", ""), styles["body"]))

    # === PENDING VOTES ===
    if pending_votes:
        elements.append(PageBreak())
        build_library_header(elements, styles, "Pending Motions/Votes")

        for vote in pending_votes:
            elements.append(Paragraph(f"<b>{vote.title}</b>", styles["subheading"]))
            if vote.description:
                elements.append(Paragraph(vote.description, styles["body"]))
            vote_type = vote.vote_type.replace("_", " ").title() if vote.vote_type else "Simple Majority"
            elements.append(Paragraph(f"<i>Vote Type: {vote_type}</i>", styles["small"]))
            elements.append(Spacer(1, 0.1 * inch))

    # === ACTION ITEMS ===
    if action_items:
        elements.append(PageBreak())
        build_library_header(elements, styles, "Outstanding Action Items")

        headers = ["Item", "Assigned To", "Due Date", "Status"]
        rows = []
        for item in action_items:
            rows.append([
                item.get("title", "N/A")[:40],
                item.get("assigned_to", "N/A"),
                item.get("due_date", "N/A"),
                item.get("status", "N/A").replace("_", " ").title(),
            ])

        if rows:
            action_table = Table([headers] + rows, colWidths=[2.5 * inch, 1.5 * inch, 1.25 * inch, 1.25 * inch])
            action_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), LIBRARY_COLORS["secondary"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
                ("BOX", (0, 0), (-1, -1), 1, colors.grey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            elements.append(action_table)

    # === MEETING BRIEF ===
    if brief_content:
        elements.append(PageBreak())
        build_library_header(elements, styles, "Meeting Preparation Brief")
        elements.append(Paragraph(
            "<i>AI-generated summary to assist with meeting preparation</i>",
            styles["small"]
        ))
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph(brief_content, styles["body"]))

    # Final footer
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(
        f"Board Packet generated {datetime.now(timezone.utc).strftime('%B %d, %Y at %I:%M %p')}",
        styles["footer"]
    ))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
