# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable, Image, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle
)

from ..models.print_notice import PrintNotice, PrintNoticeBatch, PrintNoticeType
from ..core.config import get_settings

_settings = get_settings()


# Library branding colors
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

# Library configuration (would come from settings in production)
LIBRARY_CONFIG = {
    "name": os.environ.get("LIBRARY_NAME", "My Library"),
    "address": _settings.library_address,
    "city_state_zip": _settings.library_city_state_zip,
    "phone": _settings.library_phone,
    "email": _settings.library_email,
    "website": _settings.library_website,
    "hours": "Mon-Thu 9AM-8PM, Fri-Sat 9AM-5PM, Sun 1PM-5PM",
    "since": "1952",
    "service_area": _settings.library_service_area,
}


class AddressBlock(Flowable):

    def __init__(self, lines: list[str], width: float = 3.5 * inch, height: float = 1 * inch):
        Flowable.__init__(self)
        self.lines = lines
        self.width = width
        self.height = height

    def draw(self):
        canvas = self.canv
        y = self.height - 12  # Start from top

        canvas.setFont("Helvetica", 10)
        for line in self.lines:
            canvas.drawString(0, y, line.upper())
            y -= 14


def get_notice_styles() -> dict:
    styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "NoticeTitle",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=LIBRARY_COLORS["primary"],
            spaceAfter=20,
            alignment=TA_CENTER,
        ),
        "heading": ParagraphStyle(
            "NoticeHeading",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=LIBRARY_COLORS["secondary"],
            spaceAfter=10,
            spaceBefore=15,
        ),
        "subheading": ParagraphStyle(
            "NoticeSubheading",
            parent=styles["Heading3"],
            fontSize=12,
            textColor=LIBRARY_COLORS["secondary"],
            spaceAfter=8,
            spaceBefore=10,
        ),
        "body": ParagraphStyle(
            "NoticeBody",
            parent=styles["Normal"],
            fontSize=10,
            textColor=LIBRARY_COLORS["text"],
            spaceAfter=8,
            leading=14,
        ),
        "small": ParagraphStyle(
            "NoticeSmall",
            parent=styles["Normal"],
            fontSize=8,
            textColor=LIBRARY_COLORS["muted"],
            spaceAfter=4,
        ),
        "footer": ParagraphStyle(
            "NoticeFooter",
            parent=styles["Normal"],
            fontSize=8,
            textColor=LIBRARY_COLORS["muted"],
            alignment=TA_CENTER,
        ),
        "danger": ParagraphStyle(
            "NoticeDanger",
            parent=styles["Normal"],
            fontSize=11,
            textColor=LIBRARY_COLORS["danger"],
            fontName="Helvetica-Bold",
        ),
        "success": ParagraphStyle(
            "NoticeSuccess",
            parent=styles["Normal"],
            fontSize=11,
            textColor=LIBRARY_COLORS["success"],
            fontName="Helvetica-Bold",
        ),
        "warning": ParagraphStyle(
            "NoticeWarning",
            parent=styles["Normal"],
            fontSize=11,
            textColor=LIBRARY_COLORS["warning"],
            fontName="Helvetica-Bold",
        ),
    }


def build_library_header(elements: list, styles: dict):
    # Library name
    elements.append(Paragraph(LIBRARY_CONFIG["name"], styles["title"]))

    # Library contact info
    header_data = [
        [LIBRARY_CONFIG["address"], LIBRARY_CONFIG["phone"]],
        [LIBRARY_CONFIG["city_state_zip"], LIBRARY_CONFIG["email"]],
    ]

    header_table = Table(header_data, colWidths=[3.75 * inch, 3.75 * inch])
    header_table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), LIBRARY_COLORS["muted"]),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(header_table)

    # Separator line
    elements.append(Spacer(1, 0.1 * inch))
    separator_data = [["" * 100]]
    separator = Table(separator_data, colWidths=[7.5 * inch])
    separator.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 2, LIBRARY_COLORS["primary"]),
    ]))
    elements.append(separator)
    elements.append(Spacer(1, 0.2 * inch))


def build_patron_address_block(
    elements: list,
    patron_name: str,
    address_line1: str,
    address_line2: Optional[str],
    city: str,
    state: str,
    zip_code: str,
):
    # Create address block positioned for #10 window envelope
    address_lines = [patron_name, address_line1]
    if address_line2:
        address_lines.append(address_line2)
    address_lines.append(f"{city}, {state}  {zip_code}")

    # Left-aligned address block
    address_data = [[AddressBlock(address_lines)]]
    address_table = Table(address_data, colWidths=[4 * inch])
    address_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
    ]))

    elements.append(Spacer(1, 0.3 * inch))
    elements.append(address_table)
    elements.append(Spacer(1, 0.3 * inch))


def build_notice_date(elements: list, styles: dict, date: datetime):
    date_str = date.strftime("%B %d, %Y")
    date_para = Paragraph(f"Notice Date: {date_str}", styles["small"])

    date_table = Table([[date_para]], colWidths=[7.5 * inch])
    date_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, 0), "RIGHT"),
    ]))
    elements.append(date_table)
    elements.append(Spacer(1, 0.1 * inch))


def build_items_table(
    elements: list,
    headers: list[str],
    rows: list[list[str]],
    col_widths: list[float],
    totals_row: Optional[list[str]] = None,
):
    data = [headers] + rows
    if totals_row:
        data.append(totals_row)

    table = Table(data, colWidths=col_widths)

    style_commands = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), LIBRARY_COLORS["secondary"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        # Data rows
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1 if not totals_row else -2), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]

    if totals_row:
        style_commands.extend([
            ("LINEABOVE", (0, -1), (-1, -1), 1.5, colors.black),
            ("FONT", (-2, -1), (-1, -1), "Helvetica-Bold", 10),
            ("BACKGROUND", (-2, -1), (-1, -1), LIBRARY_COLORS["light"]),
        ])

    table.setStyle(TableStyle(style_commands))
    elements.append(table)
    elements.append(Spacer(1, 0.2 * inch))


def build_action_box(elements: list, styles: dict, title: str, content: str, box_type: str = "warning"):
    color_map = {
        "warning": (colors.HexColor("#FFF9E6"), LIBRARY_COLORS["warning"]),
        "danger": (colors.HexColor("#FFF5F5"), LIBRARY_COLORS["danger"]),
        "success": (colors.HexColor("#E8F5E9"), LIBRARY_COLORS["success"]),
        "info": (colors.HexColor("#E3F2FD"), LIBRARY_COLORS["info"]),
    }

    bg_color, text_color = color_map.get(box_type, color_map["warning"])

    title_style = ParagraphStyle(
        "ActionTitle",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=text_color,
        spaceAfter=6,
    )

    content_style = ParagraphStyle(
        "ActionContent",
        fontName="Helvetica",
        fontSize=10,
        textColor=LIBRARY_COLORS["text"],
        leading=14,
    )

    box_content = [[Paragraph(title, title_style)], [Paragraph(content, content_style)]]
    box_table = Table(box_content, colWidths=[7 * inch])
    box_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("BOX", (0, 0), (-1, -1), 1, text_color),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (0, 0), 10),
        ("BOTTOMPADDING", (0, -1), (0, -1), 10),
    ]))

    elements.append(box_table)
    elements.append(Spacer(1, 0.2 * inch))


def build_contact_info(elements: list, styles: dict):
    elements.append(Spacer(1, 0.2 * inch))

    # Separator
    separator_data = [[""]]
    separator = Table(separator_data, colWidths=[7.5 * inch])
    separator.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.grey),
    ]))
    elements.append(separator)
    elements.append(Spacer(1, 0.1 * inch))

    contact_text = f"""
    <b>Questions?</b><br/>
    Visit us at {LIBRARY_CONFIG["address"]}, {LIBRARY_CONFIG["city_state_zip"]}<br/>
    Call us at {LIBRARY_CONFIG["phone"]} | Email us at {LIBRARY_CONFIG["email"]}<br/>
    Website: {LIBRARY_CONFIG["website"]}<br/>
    Library Hours: {LIBRARY_CONFIG["hours"]}
    """

    elements.append(Paragraph(contact_text, styles["small"]))


def build_footer(elements: list, styles: dict):
    elements.append(Spacer(1, 0.3 * inch))

    footer_text = f"""
    This notice was generated on {datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p")}.<br/>
    {LIBRARY_CONFIG["name"]} - Serving our community since {LIBRARY_CONFIG["since"]}.
    """

    elements.append(Paragraph(footer_text, styles["footer"]))


def generate_overdue_notice_pdf(
    notice: PrintNotice,
    items: list[dict],
    total_fine: Decimal = Decimal("0.00"),
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    elements = []
    styles = get_notice_styles()

    # Header
    build_library_header(elements, styles)

    # Date
    build_notice_date(elements, styles, datetime.now(timezone.utc))

    # Address block
    build_patron_address_block(
        elements,
        notice.recipient_name,
        notice.address_line1,
        notice.address_line2,
        notice.city,
        notice.state,
        notice.zip_code,
    )

    # Notice title
    title_style = ParagraphStyle(
        "OverdueTitle",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=LIBRARY_COLORS["danger"],
        spaceAfter=15,
    )
    elements.append(Paragraph("OVERDUE NOTICE", title_style))

    # Greeting
    patron_first = notice.recipient_name.split()[0] if notice.recipient_name else "Patron"
    elements.append(Paragraph(f"Dear {patron_first},", styles["body"]))
    elements.append(Paragraph(
        "The following item(s) from your library account are now overdue. "
        "Please return them as soon as possible to avoid additional fines.",
        styles["body"]
    ))

    # Items table
    headers = ["Title", "Author", "Due Date", "Days Overdue", "Fine"]
    rows = []
    for item in items:
        rows.append([
            item.get("title", "N/A"),
            item.get("author", "N/A"),
            item.get("due_date", "N/A"),
            str(item.get("days_overdue", 0)),
            f"${item.get('fine_amount', '0.00')}",
        ])

    col_widths = [2.5 * inch, 1.5 * inch, 1 * inch, 1 * inch, 0.75 * inch]

    if total_fine > 0:
        totals_row = ["", "", "", "Total:", f"${total_fine:.2f}"]
        build_items_table(elements, headers, rows, col_widths, totals_row)
    else:
        build_items_table(elements, headers, rows, col_widths)

    # Action box
    build_action_box(
        elements, styles,
        "Action Required",
        "Please return the overdue item(s) to any library branch or book drop. "
        "You may also renew eligible items online or by calling us. "
        "If you believe you have already returned these items, please contact us immediately.",
        "warning"
    )

    # Contact info and footer
    build_contact_info(elements, styles)
    build_footer(elements, styles)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


def generate_fine_notice_pdf(
    notice: PrintNotice,
    fines: list[dict],
    total_balance: Decimal,
    account_blocked: bool = False,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    elements = []
    styles = get_notice_styles()

    # Header
    build_library_header(elements, styles)
    build_notice_date(elements, styles, datetime.now(timezone.utc))
    build_patron_address_block(
        elements,
        notice.recipient_name,
        notice.address_line1,
        notice.address_line2,
        notice.city,
        notice.state,
        notice.zip_code,
    )

    # Notice title
    title_style = ParagraphStyle(
        "FineTitle",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=LIBRARY_COLORS["danger"],
        spaceAfter=15,
    )
    elements.append(Paragraph("FINE NOTICE", title_style))

    # Greeting
    patron_first = notice.recipient_name.split()[0] if notice.recipient_name else "Patron"
    elements.append(Paragraph(f"Dear {patron_first},", styles["body"]))
    elements.append(Paragraph(
        "Your library account has outstanding fines. Please review the details below "
        "and arrange for payment at your earliest convenience.",
        styles["body"]
    ))

    # Total due box
    total_box_data = [
        [Paragraph("Total Amount Due", ParagraphStyle("", fontSize=12, textColor=colors.white))],
        [Paragraph(f"${total_balance:.2f}", ParagraphStyle("", fontSize=24, fontName="Helvetica-Bold", textColor=colors.white))],
    ]
    total_box = Table(total_box_data, colWidths=[3 * inch])
    total_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIBRARY_COLORS["danger"]),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))

    # Center the box
    centered_table = Table([[total_box]], colWidths=[7.5 * inch])
    centered_table.setStyle(TableStyle([("ALIGN", (0, 0), (0, 0), "CENTER")]))
    elements.append(centered_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Fines table
    elements.append(Paragraph("Fine Details", styles["subheading"]))
    headers = ["Description", "Date", "Item", "Amount"]
    rows = []
    for fine in fines:
        rows.append([
            fine.get("description", "N/A"),
            fine.get("date", "N/A"),
            fine.get("item_title", "N/A")[:30],
            f"${fine.get('amount', '0.00')}",
        ])

    col_widths = [2 * inch, 1 * inch, 2.5 * inch, 1 * inch]
    totals_row = ["", "", "Total:", f"${total_balance:.2f}"]
    build_items_table(elements, headers, rows, col_widths, totals_row)

    # Payment options
    build_action_box(
        elements, styles,
        "Payment Options",
        "<b>In Person:</b> Visit any library branch during open hours<br/>"
        f"<b>Online:</b> Pay securely at {LIBRARY_CONFIG['website']}<br/>"
        f"<b>By Phone:</b> Call {LIBRARY_CONFIG['phone']}<br/>"
        "<b>By Mail:</b> Send check or money order to the address above<br/><br/>"
        "<i>We accept cash, check, credit/debit cards, and money orders.</i>",
        "success"
    )

    # Account blocked warning
    if account_blocked:
        build_action_box(
            elements, styles,
            "Account Status: Blocked",
            "Due to outstanding fines, your borrowing privileges have been suspended. "
            "Please pay your balance to restore full access to library services.",
            "danger"
        )

    build_contact_info(elements, styles)
    build_footer(elements, styles)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


def generate_hold_ready_notice_pdf(
    notice: PrintNotice,
    items: list[dict],
    pickup_location: str,
    pickup_address: str,
    pickup_hours: str,
    final_pickup_date: str,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    elements = []
    styles = get_notice_styles()

    # Header
    build_library_header(elements, styles)
    build_notice_date(elements, styles, datetime.now(timezone.utc))
    build_patron_address_block(
        elements,
        notice.recipient_name,
        notice.address_line1,
        notice.address_line2,
        notice.city,
        notice.state,
        notice.zip_code,
    )

    # Notice title
    title_style = ParagraphStyle(
        "HoldTitle",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=LIBRARY_COLORS["success"],
        spaceAfter=15,
    )
    elements.append(Paragraph("HOLD READY FOR PICKUP", title_style))

    # Success box
    success_box_data = [
        [Paragraph("Your Hold is Ready!", ParagraphStyle("", fontSize=14, fontName="Helvetica-Bold", textColor=LIBRARY_COLORS["success"]))],
        [Paragraph("The item(s) you requested are now available for pickup.", styles["body"])],
    ]
    success_box = Table(success_box_data, colWidths=[6 * inch])
    success_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E8F5E9")),
        ("BOX", (0, 0), (-1, -1), 2, LIBRARY_COLORS["success"]),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 15),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 15),
    ]))
    centered_table = Table([[success_box]], colWidths=[7.5 * inch])
    centered_table.setStyle(TableStyle([("ALIGN", (0, 0), (0, 0), "CENTER")]))
    elements.append(centered_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Greeting
    patron_first = notice.recipient_name.split()[0] if notice.recipient_name else "Patron"
    elements.append(Paragraph(f"Dear {patron_first},", styles["body"]))
    elements.append(Paragraph(
        "Great news! The following item(s) you placed on hold are now ready for pickup:",
        styles["body"]
    ))

    # Items table
    headers = ["Title", "Author", "Format", "Pickup By"]
    rows = []
    for item in items:
        rows.append([
            item.get("title", "N/A"),
            item.get("author", "N/A"),
            item.get("format", "N/A"),
            item.get("pickup_by", final_pickup_date),
        ])

    col_widths = [2.75 * inch, 1.75 * inch, 1 * inch, 1 * inch]
    build_items_table(elements, headers, rows, col_widths)

    # Pickup location
    build_action_box(
        elements, styles,
        "Pickup Location",
        f"<b>{pickup_location}</b><br/>"
        f"{pickup_address}<br/>"
        f"Hours: {pickup_hours}",
        "info"
    )

    # Important notice
    build_action_box(
        elements, styles,
        "Important",
        f"Please pick up your item(s) by <b>{final_pickup_date}</b>.<br/><br/>"
        "Items not picked up by this date will be returned to the shelf or "
        "sent to the next person on the waiting list.<br/><br/>"
        "<b>What to bring:</b> Your library card or valid photo ID",
        "warning"
    )

    build_contact_info(elements, styles)
    build_footer(elements, styles)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


def generate_account_expiring_notice_pdf(
    notice: PrintNotice,
    expiration_date: str,
    days_until_expiry: int,
    member_since: str,
    card_type: str,
    items_checked_out: int = 0,
    holds_count: int = 0,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    elements = []
    styles = get_notice_styles()

    # Header
    build_library_header(elements, styles)
    build_notice_date(elements, styles, datetime.now(timezone.utc))
    build_patron_address_block(
        elements,
        notice.recipient_name,
        notice.address_line1,
        notice.address_line2,
        notice.city,
        notice.state,
        notice.zip_code,
    )

    # Notice title
    title_style = ParagraphStyle(
        "ExpiringTitle",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=LIBRARY_COLORS["warning"],
        spaceAfter=15,
    )
    elements.append(Paragraph("LIBRARY CARD RENEWAL NOTICE", title_style))

    # Greeting
    patron_first = notice.recipient_name.split()[0] if notice.recipient_name else "Patron"
    elements.append(Paragraph(f"Dear {patron_first},", styles["body"]))
    elements.append(Paragraph(
        "Your library card is expiring soon. To continue enjoying all the benefits "
        "of your library membership, please renew your card before the expiration date.",
        styles["body"]
    ))

    # Expiry box
    expiry_box_data = [
        [Paragraph("Your library card expires on", styles["small"])],
        [Paragraph(expiration_date, ParagraphStyle("", fontSize=20, fontName="Helvetica-Bold", textColor=LIBRARY_COLORS["warning"]))],
        [Paragraph(f"{days_until_expiry} days remaining", styles["body"])],
    ]
    expiry_box = Table(expiry_box_data, colWidths=[4 * inch])
    expiry_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF9E6")),
        ("BOX", (0, 0), (-1, -1), 2, LIBRARY_COLORS["warning"]),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    centered_table = Table([[expiry_box]], colWidths=[7.5 * inch])
    centered_table.setStyle(TableStyle([("ALIGN", (0, 0), (0, 0), "CENTER")]))
    elements.append(centered_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Account details
    elements.append(Paragraph("Your Account Information", styles["subheading"]))
    account_data = [
        ["Card Number:", notice.context_data.get("library_card", "N/A") if notice.context_data else "N/A"],
        ["Member Since:", member_since],
        ["Card Type:", card_type],
    ]
    if items_checked_out > 0:
        account_data.append(["Items Currently Checked Out:", str(items_checked_out)])
    if holds_count > 0:
        account_data.append(["Active Holds:", str(holds_count)])

    account_table = Table(account_data, colWidths=[2.5 * inch, 4 * inch])
    account_table.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
        ("FONT", (1, 0), (1, -1), "Helvetica", 10),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9f9f9")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(account_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Renewal options
    build_action_box(
        elements, styles,
        "How to Renew",
        "<b>In Person:</b> Visit any library branch with valid ID and proof of address<br/>"
        f"<b>Online:</b> Renew at {LIBRARY_CONFIG['website']} (if address unchanged)<br/>"
        f"<b>By Phone:</b> Call {LIBRARY_CONFIG['phone']}<br/><br/>"
        f"Renewal is <b>FREE</b> for residents of {LIBRARY_CONFIG['service_area']}.",
        "success"
    )

    # Requirements
    build_action_box(
        elements, styles,
        "What You'll Need",
        "- Valid photo ID (driver's license, state ID, passport)<br/>"
        "- Proof of current address (utility bill, lease agreement, bank statement)<br/>"
        "- For children: Parent/guardian must be present with their ID",
        "info"
    )

    build_contact_info(elements, styles)
    build_footer(elements, styles)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


def generate_merged_notices_pdf(
    notices: list[PrintNotice],
    patron_name: str,
    address_line1: str,
    address_line2: Optional[str],
    city: str,
    state: str,
    zip_code: str,
    library_card: str,
    notice_contents: list[dict],
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    elements = []
    styles = get_notice_styles()

    # Header
    build_library_header(elements, styles)
    build_notice_date(elements, styles, datetime.now(timezone.utc))
    build_patron_address_block(
        elements, patron_name, address_line1, address_line2, city, state, zip_code
    )

    # Greeting
    patron_first = patron_name.split()[0] if patron_name else "Patron"
    elements.append(Paragraph(f"Dear {patron_first},", styles["body"]))
    elements.append(Paragraph(
        "This letter contains important notices regarding your library account. "
        "Please review each section carefully.",
        styles["body"]
    ))

    # Summary box
    notice_types = [nc["title"] for nc in notice_contents]
    summary_items = "<br/>".join([f"- {nt}" for nt in notice_types])
    build_action_box(
        elements, styles,
        "This Letter Contains:",
        summary_items,
        "info"
    )

    # Add each notice section
    for nc in notice_contents:
        # Section divider
        elements.append(Spacer(1, 0.2 * inch))

        # Section title with appropriate color
        color_map = {
            "overdue": LIBRARY_COLORS["danger"],
            "fine": LIBRARY_COLORS["danger"],
            "hold_ready": LIBRARY_COLORS["success"],
            "account_expiring": LIBRARY_COLORS["warning"],
        }
        title_color = color_map.get(nc["type"], LIBRARY_COLORS["secondary"])

        section_title_style = ParagraphStyle(
            "SectionTitle",
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=title_color,
            spaceAfter=10,
        )
        elements.append(Paragraph(nc["title"], section_title_style))

        # Separator line
        sep_data = [[""]]
        sep = Table(sep_data, colWidths=[7.5 * inch])
        sep.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 2, title_color),
        ]))
        elements.append(sep)
        elements.append(Spacer(1, 0.1 * inch))

        # Section content
        elements.append(Paragraph(nc["content"], styles["body"]))

    build_contact_info(elements, styles)
    build_footer(elements, styles)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


def generate_batch_manifest_pdf(
    batch: PrintNoticeBatch,
    notices: list[PrintNotice],
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    elements = []
    styles = get_notice_styles()

    # Title
    elements.append(Paragraph("PRINT NOTICE BATCH MANIFEST", styles["title"]))
    elements.append(Spacer(1, 0.1 * inch))

    # Batch info
    batch_data = [
        ["Batch Number:", batch.batch_number],
        ["Generated:", datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p")],
        ["Total Notices:", str(len(notices))],
        ["Total Pages:", str(batch.page_count)],
        ["Estimated Print Cost:", f"${batch.total_print_cost:.2f}"],
        ["Estimated Postage:", f"${batch.total_postage_cost:.2f}"],
        ["Total Estimated Cost:", f"${batch.total_cost:.2f}"],
    ]

    batch_table = Table(batch_data, colWidths=[2 * inch, 4 * inch])
    batch_table.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
        ("FONT", (1, 0), (1, -1), "Helvetica", 10),
        ("BACKGROUND", (0, 0), (-1, -1), LIBRARY_COLORS["light"]),
        ("BOX", (0, 0), (-1, -1), 1, LIBRARY_COLORS["secondary"]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(batch_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Notice list
    elements.append(Paragraph("Notice List", styles["heading"]))

    headers = ["#", "Patron", "Type", "Address", "Pages"]
    rows = []
    for i, notice in enumerate(notices, 1):
        address_short = f"{notice.city}, {notice.state} {notice.zip_code}"
        rows.append([
            str(i),
            notice.recipient_name[:25],
            str(notice.notice_type).replace("_", " ").title(),
            address_short,
            str(notice.pages),
        ])

    col_widths = [0.4 * inch, 1.8 * inch, 1.2 * inch, 2.1 * inch, 0.5 * inch]
    build_items_table(elements, headers, rows, col_widths)

    # Footer
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(
        f"Generated by {LIBRARY_CONFIG['name']} Print Notice System",
        styles["footer"]
    ))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
