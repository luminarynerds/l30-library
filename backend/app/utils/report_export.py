# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
import io
from app.core.logging import get_logger
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from fastapi.responses import Response

logger = get_logger(__name__)


def _serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        # Flatten nested dicts to string for tabular formats
        return "; ".join(f"{k}: {_serialize(v)}" for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return ", ".join(str(_serialize(v)) for v in value)
    return value


def _extract_rows(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Look for common list keys
        for key in ("items", "data", "rows", "alerts", "regulatory_changes",
                     "enforcement_records", "readers", "report_types"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # No nested list found - treat as a single summary row
        return [data]
    return [{"value": str(data)}]


def export_csv(data: Any, title: str = "Report") -> bytes:
    rows = _extract_rows(data)
    buf = io.StringIO()
    writer = csv.writer(buf)

    # Title and timestamp
    writer.writerow([title])
    writer.writerow([f"Generated: {datetime.now(timezone.utc).isoformat()}"])
    writer.writerow([])

    if not rows:
        writer.writerow(["No data available"])
        return buf.getvalue().encode("utf-8")

    # Column headers from first row
    headers = list(rows[0].keys())
    writer.writerow([h.replace("_", " ").title() for h in headers])

    for row in rows:
        writer.writerow([_serialize(row.get(h, "")) for h in headers])

    return buf.getvalue().encode("utf-8")


def export_excel(data: Any, title: str = "Report") -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    rows = _extract_rows(data)
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]

    header_font = Font(bold=True, size=14)
    col_header_fill = PatternFill(
        start_color="D9E1F2", end_color="D9E1F2", fill_type="solid"
    )
    col_header_font = Font(bold=True)

    # Title
    ws.cell(row=1, column=1, value=title).font = header_font
    ws.cell(
        row=2, column=1,
        value=f"Generated: {datetime.now(timezone.utc).isoformat()}"
    )

    if not rows:
        ws.cell(row=4, column=1, value="No data available")
        out = io.BytesIO()
        wb.save(out)
        return out.getvalue()

    # Column headers
    headers = list(rows[0].keys())
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(
            row=4, column=col_idx,
            value=h.replace("_", " ").title()
        )
        cell.fill = col_header_fill
        cell.font = col_header_font

    # Data rows
    for r_idx, row in enumerate(rows, 5):
        for col_idx, h in enumerate(headers, 1):
            ws.cell(row=r_idx, column=col_idx, value=_serialize(row.get(h, "")))

    # Auto-width columns (approximate)
    for col_idx, h in enumerate(headers, 1):
        max_len = len(h) + 2
        for r_idx in range(5, min(5 + len(rows), 55)):
            cell_val = str(ws.cell(row=r_idx, column=col_idx).value or "")
            max_len = max(max_len, len(cell_val))
        ws.column_dimensions[chr(64 + col_idx) if col_idx <= 26 else "A"].width = min(max_len + 2, 50)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def export_pdf(data: Any, title: str = "Report") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    rows = _extract_rows(data)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontSize=18, spaceAfter=12,
    )
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        styles["Normal"],
    ))
    elements.append(Spacer(1, 0.3 * inch))

    if not rows:
        elements.append(Paragraph("No data available.", styles["Normal"]))
        doc.build(elements)
        return buf.getvalue()

    # Build table
    headers = list(rows[0].keys())
    table_data = [[h.replace("_", " ").title() for h in headers]]
    for row in rows[:500]:  # Cap row count for PDF size
        table_data.append([str(_serialize(row.get(h, ""))) for h in headers])

    col_width = min(7.0 * inch / max(len(headers), 1), 2.5 * inch)
    t = Table(table_data, colWidths=[col_width] * len(headers))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.85, 0.88, 0.95)),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
    ]))
    elements.append(t)

    doc.build(elements)
    return buf.getvalue()


def make_export_response(
    data: Any,
    format: str,
    title: str = "Report",
    filename_prefix: str = "report",
) -> Optional[Response]:
    fmt = format.strip().lower() if format else ""

    if fmt == "csv":
        content = export_csv(data, title=title)
        media_type = "text/csv"
        ext = "csv"
    elif fmt in ("excel", "xlsx"):
        content = export_excel(data, title=title)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    elif fmt == "pdf":
        content = export_pdf(data, title=title)
        media_type = "application/pdf"
        ext = "pdf"
    else:
        return None  # Fall through to default JSON

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.{ext}"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
