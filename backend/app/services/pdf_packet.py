# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
from app.core.logging import get_logger
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = get_logger(__name__)


def generate_packet_cover_pdf(
    topic_name: str,
    forms: list[dict],
    library_name: str = "My Library",
    library_phone: str = "(555) 123-4567",
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PacketTitle", parent=styles["Title"], fontSize=18, spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "PacketSubtitle", parent=styles["Normal"], fontSize=11,
        textColor=colors.grey, spaceAfter=18,
    )
    heading_style = ParagraphStyle(
        "PacketHeading", parent=styles["Heading2"], fontSize=14,
        spaceBefore=12, spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "PacketBody", parent=styles["Normal"], fontSize=11, spaceAfter=4,
    )
    small_style = ParagraphStyle(
        "PacketSmall", parent=styles["Normal"], fontSize=9, textColor=colors.grey,
    )

    elements = []

    # Header
    elements.append(Paragraph(f"{topic_name} Forms Packet", title_style))
    elements.append(Paragraph(
        f"Prepared by {library_name} | {library_phone} | Generated {date.today().strftime('%B %d, %Y')}",
        subtitle_style,
    ))

    # Disclaimer
    elements.append(Paragraph(
        "<b>Disclaimer:</b> These forms are provided for informational purposes. "
        "They do not constitute legal advice. Consult a qualified attorney for your specific situation.",
        small_style,
    ))
    elements.append(Spacer(1, 12))

    # Forms table
    elements.append(Paragraph("Included Forms", heading_style))

    table_data: list[list] = [["#", "Form", "Description"]]
    online_only = []
    row_num = 0

    for form in forms:
        url = form.get("form_url", "")
        is_pdf = url and url.lower().endswith(".pdf")

        if url and not is_pdf:
            online_only.append(form)
            continue

        row_num += 1
        title = form.get("title", "Untitled")
        number = form.get("form_number", "")
        desc = form.get("when_to_use") or form.get("description") or ""
        label = f"{title}"
        if number:
            label += f" ({number})"

        table_data.append([str(row_num), Paragraph(label, body_style), Paragraph(desc[:200], body_style)])

    if len(table_data) > 1:
        table = Table(table_data, colWidths=[0.4 * inch, 2.5 * inch, 4.0 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f0eb")),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 1), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d4c9b8")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(table)

    # Online-only forms
    if online_only:
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Available Online Only", heading_style))
        for form in online_only:
            title = form.get("title", "Untitled")
            url = form.get("form_url", "")
            elements.append(Paragraph(f"- {title}: {url}", body_style))

    # Footer
    elements.append(Spacer(1, 24))
    elements.append(Paragraph(
        "Need help? Visit the library's legal resource desk or call us. "
        "Free legal clinics are available -- ask at the front desk for the schedule.",
        small_style,
    ))

    doc.build(elements)
    return buffer.getvalue()
