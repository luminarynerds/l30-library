# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
import io
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import BinaryIO

from jinja2 import Template
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.multi_branch import ConsortiumBilling, ConsortiumMember, Consortium
from app.schemas.multi_branch import ConsortiumBillingResponse


class ConsortiumInvoiceExportService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_pdf_invoice(
        self,
        billing_record: ConsortiumBilling,
        output_stream: BinaryIO | None = None,
    ) -> bytes:
        # Create PDF in memory
        if output_stream is None:
            output_stream = io.BytesIO()

        # Create document
        doc = SimpleDocTemplate(
            output_stream,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        # Story of elements to add
        story = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#1f4788"),
            spaceAfter=12,
            alignment=1,  # Center
        )
        story.append(Paragraph("INVOICE", title_style))

        # Spacing
        story.append(Spacer(1, 0.3 * inch))

        # Header info table
        header_data = [
            ["Invoice Number:", billing_record.invoice_number or "N/A"],
            ["Date:", datetime.now(timezone.utc).strftime("%B %d, %Y")],
            ["Due Date:", billing_record.due_date.strftime("%B %d, %Y") if billing_record.due_date else "N/A"],
            ["Status:", str(billing_record.status).upper()],
        ]
        header_table = Table(header_data, colWidths=[2 * inch, 4 * inch])
        header_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1f4788")),
                ]
            )
        )
        story.append(header_table)
        story.append(Spacer(1, 0.3 * inch))

        # Billing parties info
        parties_data = [
            ["BILLED BY (Creditor):", "BILLED TO (Debtor):"],
            [
                f"{billing_record.billing_member.library_system.name if billing_record.billing_member else 'N/A'}\n"
                f"Member ID: {billing_record.billing_member_id}",
                f"{billing_record.billed_member.library_system.name if billing_record.billed_member else 'N/A'}\n"
                f"Member ID: {billing_record.billed_member_id}",
            ],
        ]
        parties_table = Table(parties_data, colWidths=[3.25 * inch, 3.25 * inch])
        parties_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("ALIGN", (0, 1), (-1, 1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4788")),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(parties_table)
        story.append(Spacer(1, 0.3 * inch))

        # Line items table
        line_items_data = [
            ["Item Type", "Quantity", "Unit Amount", "Total Amount", "Period"],
            [
                str(billing_record.item_type).replace("_", " ").title(),
                str(billing_record.quantity),
                f"${billing_record.unit_amount:.2f}",
                f"${billing_record.total_amount:.2f}",
                f"{billing_record.billing_period_start} to {billing_record.billing_period_end}",
            ],
        ]
        line_items_table = Table(line_items_data, colWidths=[1.5 * inch, 1 * inch, 1.3 * inch, 1.3 * inch, 1.4 * inch])
        line_items_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("ALIGN", (1, 1), (-1, 1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4788")),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 8),
                    ("ROWBACKGROUNDS", (0, 1), (-1, 1), [colors.HexColor("#f0f0f0")]),
                ]
            )
        )
        story.append(line_items_table)
        story.append(Spacer(1, 0.3 * inch))

        # Total amount
        total_style = ParagraphStyle(
            "TotalAmount",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#1f4788"),
            alignment=2,  # Right
        )
        story.append(Paragraph(f"<b>Total Due: ${billing_record.total_amount:.2f}</b>", total_style))
        story.append(Spacer(1, 0.2 * inch))

        # Payment info
        if billing_record.payment_reference:
            payment_info = f"<b>Payment Reference:</b> {billing_record.payment_reference}"
            story.append(Paragraph(payment_info, styles["Normal"]))

        if billing_record.due_date:
            story.append(
                Paragraph(
                    f"<b>Please remit payment by:</b> {billing_record.due_date.strftime('%B %d, %Y')}",
                    styles["Normal"],
                )
            )

        story.append(Spacer(1, 0.3 * inch))

        # Footer
        footer_style = ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.grey,
            alignment=1,
        )
        story.append(
            Paragraph(
                "This is an automated invoice generated by the library consortium billing system.",
                footer_style,
            )
        )

        # Build PDF
        doc.build(story)

        # Get bytes if using BytesIO
        if isinstance(output_stream, io.BytesIO):
            return output_stream.getvalue()
        return b""

    def generate_csv_invoice(
        self,
        billing_records: list[ConsortiumBilling],
        output_stream: io.StringIO | None = None,
    ) -> str:
        if output_stream is None:
            output_stream = io.StringIO()

        fieldnames = [
            "Invoice Number",
            "Billing Member",
            "Billed Member",
            "Item Type",
            "Quantity",
            "Unit Amount",
            "Total Amount",
            "Period Start",
            "Period End",
            "Status",
            "Due Date",
            "Invoice Date",
            "Payment Reference",
            "Description",
        ]

        writer = csv.DictWriter(output_stream, fieldnames=fieldnames)
        writer.writeheader()

        for record in billing_records:
            writer.writerow(
                {
                    "Invoice Number": record.invoice_number or "",
                    "Billing Member": record.billing_member.library_system.name
                    if record.billing_member
                    else "",
                    "Billed Member": record.billed_member.library_system.name
                    if record.billed_member
                    else "",
                    "Item Type": str(record.item_type),
                    "Quantity": record.quantity,
                    "Unit Amount": f"{record.unit_amount:.2f}",
                    "Total Amount": f"{record.total_amount:.2f}",
                    "Period Start": record.billing_period_start.isoformat(),
                    "Period End": record.billing_period_end.isoformat(),
                    "Status": str(record.status),
                    "Due Date": record.due_date.isoformat() if record.due_date else "",
                    "Invoice Date": record.invoiced_at.isoformat() if record.invoiced_at else "",
                    "Payment Reference": record.payment_reference or "",
                    "Description": record.description or "",
                }
            )

        return output_stream.getvalue()

    async def generate_member_invoice_summary_csv(
        self,
        consortium_id: int,
        member_id: int,
        invoice_number: str | None = None,
        output_stream: io.StringIO | None = None,
    ) -> str:
        if output_stream is None:
            output_stream = io.StringIO()

        fieldnames = [
            "Invoice Number",
            "Date",
            "Member",
            "Amount",
            "Status",
            "Due Date",
        ]

        writer = csv.DictWriter(output_stream, fieldnames=fieldnames)
        writer.writeheader()

        # This would be populated from database query
        # Implementation would fetch records based on filters

        return output_stream.getvalue()
