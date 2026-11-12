# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from ..models.acquisition import PurchaseOrder

_LIBRARY_NAME = os.environ.get("LIBRARY_NAME", "My Library")


def generate_barcode() -> str:
    return f"L30-{uuid.uuid4().hex[:12].upper()}"


def generate_po_pdf(po: PurchaseOrder) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    # Container for PDF elements
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "POTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#2C1810"),
        spaceAfter=20,
        alignment=TA_CENTER,
    )

    heading_style = ParagraphStyle(
        "POHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#5C4F3D"),
        spaceAfter=10,
        spaceBefore=15,
    )

    # Title
    title = Paragraph("PURCHASE ORDER", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    # Header Information Table
    header_data = [
        [_LIBRARY_NAME, "", "PO Number:", po.po_number],
        ["123 Library Lane", "", "Date:", datetime.now().strftime("%B %d, %Y")],
        ["Library 2030, NS", "", "Status:", str(po.status).replace("_", " ").title()],
        ["Phone: (555) 123-4567", "", "Fund:", po.fund.name if po.fund else "N/A"],
    ]

    header_table = Table(
        header_data, colWidths=[2.5 * inch, 0.5 * inch, 1.2 * inch, 2.3 * inch]
    )
    header_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
                ("FONT", (2, 0), (2, -1), "Helvetica-Bold", 9),
                ("FONT", (3, 0), (3, -1), "Helvetica", 9),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (2, 0), (3, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    elements.append(header_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Vendor Information
    vendor_heading = Paragraph("VENDOR INFORMATION", heading_style)
    elements.append(vendor_heading)

    vendor_data = [
        ["Vendor:", po.vendor.name if po.vendor else "N/A"],
        [
            "Contact:",
            po.vendor.contact_name if po.vendor and po.vendor.contact_name else "N/A",
        ],
        ["Email:", po.vendor.email if po.vendor and po.vendor.email else "N/A"],
        ["Phone:", po.vendor.phone if po.vendor and po.vendor.phone else "N/A"],
    ]

    vendor_table = Table(vendor_data, colWidths=[1.5 * inch, 5 * inch])
    vendor_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
                ("FONT", (1, 0), (1, -1), "Helvetica", 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    elements.append(vendor_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Line Items
    items_heading = Paragraph("LINE ITEMS", heading_style)
    elements.append(items_heading)

    # Line items table header
    items_data = [["#", "Title", "Author", "ISBN", "Qty", "Unit Price", "Total"]]

    # Add line items
    for idx, item in enumerate(po.items, 1):
        line_total = Decimal(str(item.quantity)) * item.unit_price
        items_data.append(
            [
                str(idx),
                item.title or "N/A",
                item.author or "N/A",
                item.isbn or "N/A",
                str(item.quantity),
                f"${item.unit_price:.2f}",
                f"${line_total:.2f}",
            ]
        )

    # Add totals row
    items_data.append(["", "", "", "", "", "TOTAL:", f"${po.total_amount:.2f}"])

    items_table = Table(
        items_data,
        colWidths=[
            0.3 * inch,
            2 * inch,
            1.3 * inch,
            1 * inch,
            0.5 * inch,
            0.9 * inch,
            0.9 * inch,
        ],
    )

    items_table.setStyle(
        TableStyle(
            [
                # Header row
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5C4F3D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                # Data rows
                ("FONT", (0, 1), (-1, -2), "Helvetica", 8),
                ("ALIGN", (0, 1), (0, -1), "CENTER"),  # Row numbers
                ("ALIGN", (4, 1), (4, -1), "CENTER"),  # Quantity
                ("ALIGN", (5, 1), (-1, -1), "RIGHT"),  # Prices
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                # Grid
                ("GRID", (0, 0), (-1, -2), 0.5, colors.grey),
                ("LINEABOVE", (0, -1), (-1, -1), 1.5, colors.black),
                # Totals row
                ("FONT", (5, -1), (-1, -1), "Helvetica-Bold", 10),
                ("BACKGROUND", (5, -1), (-1, -1), colors.HexColor("#F0EDE8")),
                # Padding
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    elements.append(items_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Notes section if exists
    if po.notes:
        notes_heading = Paragraph("NOTES", heading_style)
        elements.append(notes_heading)
        notes_text = Paragraph(po.notes, styles["Normal"])
        elements.append(notes_text)
        elements.append(Spacer(1, 0.2 * inch))

    # Footer
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )

    footer_text = Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br/>"
        f"{_LIBRARY_NAME} - Acquisitions Department",
        footer_style,
    )
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(footer_text)

    # Build PDF
    doc.build(elements)

    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
