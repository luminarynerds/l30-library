# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import os
from datetime import datetime
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from ..models.cash_drawer import CashDrawerSession, CashTransaction, CashDrawer


LIBRARY_NAME = os.environ.get("LIBRARY_NAME", "My Library")

COLORS = {
    "header": colors.HexColor("#3D2B1F"),
    "accent": colors.HexColor("#8B7355"),
    "light_bg": colors.HexColor("#F5F0EB"),
    "green": colors.HexColor("#2E7D32"),
    "red": colors.HexColor("#C62828"),
}


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "ReportTitle", parent=styles["Heading1"],
        fontSize=16, textColor=COLORS["header"],
    ))
    styles.add(ParagraphStyle(
        "SectionHead", parent=styles["Heading2"],
        fontSize=12, textColor=COLORS["header"], spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "SmallText", parent=styles["Normal"],
        fontSize=8, textColor=colors.gray,
    ))
    return styles


def _header_table(title: str, date_str: str, subtitle: str = ""):
    data = [
        [LIBRARY_NAME],
        [title],
        [date_str + (f"  |  {subtitle}" if subtitle else "")],
    ]
    t = Table(data, colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (0, 0), 14),
        ("FONTNAME", (0, 1), (0, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (0, 1), 12),
        ("FONTSIZE", (0, 2), (0, 2), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), COLORS["header"]),
        ("BOTTOMPADDING", (0, 0), (0, 0), 2),
        ("BOTTOMPADDING", (0, 1), (0, 1), 2),
        ("BOTTOMPADDING", (0, 2), (0, 2), 8),
        ("LINEBELOW", (0, 2), (0, 2), 1, COLORS["accent"]),
    ]))
    return t


def _fmt(val) -> str:
    if val is None:
        return "-"
    return f"${val:,.2f}"


def generate_reconciliation_pdf(
    session: CashDrawerSession,
    transactions: list,
    drawer: CashDrawer,
    opener_name: str = "",
    closer_name: str = "",
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = _styles()
    elements = []

    date_str = session.opened_at.strftime("%B %d, %Y") if session.opened_at else ""
    elements.append(_header_table("Daily Cash Reconciliation", date_str, drawer.name))
    elements.append(Spacer(1, 12))

    # Session metadata
    meta_data = [
        ["Opened by:", opener_name, "Closed by:", closer_name],
        [
            "Opened at:",
            session.opened_at.strftime("%I:%M %p") if session.opened_at else "",
            "Closed at:",
            session.closed_at.strftime("%I:%M %p") if session.closed_at else "",
        ],
    ]
    meta = Table(meta_data, colWidths=[1.2 * inch, 2 * inch, 1.2 * inch, 2 * inch])
    meta.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(meta)
    elements.append(Spacer(1, 16))

    # Financial summary
    elements.append(Paragraph("Financial Summary", styles["SectionHead"]))

    inflows = Decimal("0")
    outflows = Decimal("0")
    inflow_cats = {}
    outflow_cats = {}
    for txn in transactions:
        if txn.voided:
            continue
        if str(txn.direction) == "inflow":
            inflows += txn.amount
            cat = str(txn.category).replace("_", " ").title()
            inflow_cats[cat] = inflow_cats.get(cat, Decimal("0")) + txn.amount
        else:
            outflows += txn.amount
            cat = str(txn.category).replace("_", " ").title()
            outflow_cats[cat] = outflow_cats.get(cat, Decimal("0")) + txn.amount

    summary_rows = [["Item", "Amount"]]
    summary_rows.append(["Opening Float", _fmt(session.opening_float)])
    for cat, amt in sorted(inflow_cats.items()):
        summary_rows.append([f"  + {cat}", _fmt(amt)])
    summary_rows.append(["Total Inflows", _fmt(inflows)])
    for cat, amt in sorted(outflow_cats.items()):
        summary_rows.append([f"  - {cat}", _fmt(amt)])
    summary_rows.append(["Total Outflows", _fmt(outflows)])
    summary_rows.append(["Expected Total", _fmt(session.expected_total)])
    summary_rows.append(["Counted Total", _fmt(session.counted_total)])
    summary_rows.append(["Discrepancy", _fmt(session.discrepancy)])

    summary = Table(summary_rows, colWidths=[4 * inch, 2 * inch])
    header_style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["light_bg"]),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]
    # Bold total rows
    total_row_indices = []
    for i, row in enumerate(summary_rows):
        if row[0] in ("Total Inflows", "Total Outflows", "Expected Total", "Counted Total", "Discrepancy"):
            header_style.append(("FONTNAME", (0, i), (-1, i), "Helvetica-Bold"))
            if row[0] == "Discrepancy":
                disc = session.discrepancy or Decimal("0")
                if disc != Decimal("0"):
                    header_style.append(("TEXTCOLOR", (1, i), (1, i), COLORS["red"]))

    summary.setStyle(TableStyle(header_style))
    elements.append(summary)
    elements.append(Spacer(1, 16))

    # Denomination breakdown
    if session.denomination_breakdown:
        elements.append(Paragraph("Denomination Breakdown", styles["SectionHead"]))
        denom_labels = [
            ("hundred", "$100"), ("fifty", "$50"), ("twenty", "$20"),
            ("ten", "$10"), ("five", "$5"), ("one", "$1"),
            ("quarter", "$0.25"), ("dime", "$0.10"), ("nickel", "$0.05"), ("penny", "$0.01"),
        ]
        denom_rows = [["Denomination", "Count", "Subtotal"]]
        multipliers = {
            "hundred": 100, "fifty": 50, "twenty": 20, "ten": 10,
            "five": 5, "one": 1, "quarter": 0.25, "dime": 0.10,
            "nickel": 0.05, "penny": 0.01,
        }
        for key, label in denom_labels:
            count = session.denomination_breakdown.get(key, 0)
            if count:
                subtotal = Decimal(str(count * multipliers[key]))
                denom_rows.append([label, str(count), _fmt(subtotal)])
        denom = Table(denom_rows, colWidths=[2 * inch, 2 * inch, 2 * inch])
        denom.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), COLORS["light_bg"]),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(denom)
        elements.append(Spacer(1, 16))

    # Transaction log
    if transactions:
        elements.append(Paragraph("Transaction Log", styles["SectionHead"]))
        txn_rows = [["Time", "Category", "Direction", "Amount", "Description"]]
        for txn in transactions:
            void_prefix = "[VOID] " if txn.voided else ""
            txn_rows.append([
                txn.created_at.strftime("%I:%M %p") if txn.created_at else "",
                str(txn.category).replace("_", " ").title(),
                str(txn.direction).title(),
                _fmt(txn.amount),
                void_prefix + (txn.description or ""),
            ])
        txn_table = Table(txn_rows, colWidths=[1 * inch, 1.3 * inch, 0.8 * inch, 1 * inch, 1.6 * inch])
        txn_style = [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), COLORS["light_bg"]),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        for i, txn in enumerate(transactions, 1):
            if txn.voided:
                txn_style.append(("TEXTCOLOR", (0, i), (-1, i), colors.gray))
        txn_table.setStyle(TableStyle(txn_style))
        elements.append(txn_table)
        elements.append(Spacer(1, 20))

    # Signature lines
    sig_data = [
        ["Staff Signature: ____________________________", "Manager Signature: ____________________________"],
        ["Date: ____________________________", "Date: ____________________________"],
    ]
    sig = Table(sig_data, colWidths=[3.25 * inch, 3.25 * inch])
    sig.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    elements.append(sig)

    doc.build(elements)
    return buf.getvalue()


def generate_deposit_slip_pdf(
    session: CashDrawerSession,
    drawer: CashDrawer,
    prepared_by: str = "",
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = _styles()
    elements = []

    date_str = session.closed_at.strftime("%B %d, %Y") if session.closed_at else ""
    elements.append(_header_table("Bank Deposit Slip", date_str, drawer.name))
    elements.append(Spacer(1, 20))

    deposit_amount = (session.counted_total or Decimal("0")) - session.opening_float

    deposit_data = [
        ["Item", "Amount"],
        ["Counted Total", _fmt(session.counted_total)],
        ["Less Opening Float", _fmt(session.opening_float)],
        ["Deposit Amount", _fmt(deposit_amount)],
    ]
    dep = Table(deposit_data, colWidths=[4 * inch, 2 * inch])
    dep.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["light_bg"]),
        ("BACKGROUND", (0, 3), (-1, 3), COLORS["light_bg"]),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(dep)
    elements.append(Spacer(1, 16))

    if session.denomination_breakdown:
        elements.append(Paragraph("Denomination Breakdown", styles["SectionHead"]))
        denom_labels = [
            ("hundred", "$100"), ("fifty", "$50"), ("twenty", "$20"),
            ("ten", "$10"), ("five", "$5"), ("one", "$1"),
            ("quarter", "$0.25"), ("dime", "$0.10"), ("nickel", "$0.05"), ("penny", "$0.01"),
        ]
        multipliers = {
            "hundred": 100, "fifty": 50, "twenty": 20, "ten": 10,
            "five": 5, "one": 1, "quarter": 0.25, "dime": 0.10,
            "nickel": 0.05, "penny": 0.01,
        }
        denom_rows = [["Denomination", "Count", "Subtotal"]]
        for key, label in denom_labels:
            count = session.denomination_breakdown.get(key, 0)
            if count:
                subtotal = Decimal(str(count * multipliers[key]))
                denom_rows.append([label, str(count), _fmt(subtotal)])
        denom = Table(denom_rows, colWidths=[2 * inch, 2 * inch, 2 * inch])
        denom.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), COLORS["light_bg"]),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(denom)
        elements.append(Spacer(1, 20))

    sig_data = [
        ["Prepared by: ____________________________", "Verified by: ____________________________"],
        ["Date: ____________________________", "Date: ____________________________"],
    ]
    sig = Table(sig_data, colWidths=[3.25 * inch, 3.25 * inch])
    sig.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    elements.append(sig)

    doc.build(elements)
    return buf.getvalue()
