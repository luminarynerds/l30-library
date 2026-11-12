# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
import io
import json
from app.core.logging import get_logger
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum, StrEnum
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class OutputFormat(StrEnum):
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"


# ---------------------------------------------------------------------------
# Shared data types
# ---------------------------------------------------------------------------

@dataclass
class ReportFilters:
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    branch_id: Optional[int] = None
    fiscal_year: Optional[int] = None
    state_code: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.start_date is None and self.fiscal_year is not None:
            # Not every builder reads filters.fiscal_year directly (only
            # compliance/financial do) -- most just filter on
            # start_date/end_date. Derive a concrete range so those builders
            # don't compare a column to None. Default FY start month (July)
            # matches UsageStatisticsSettings.fiscal_year_start_month's
            # fallback in app/services/usage_statistics_service.py when no
            # per-branch settings row overrides it.
            from datetime import timedelta
            fy_start_month = 7
            self.start_date = datetime(self.fiscal_year - 1, fy_start_month, 1, tzinfo=timezone.utc)
            self.end_date = datetime(self.fiscal_year, fy_start_month, 1, tzinfo=timezone.utc) - timedelta(days=1)
        if self.start_date is None and self.fiscal_year is None:
            from datetime import timedelta
            self.end_date = self.end_date or datetime.now(timezone.utc)
            self.start_date = self.end_date - timedelta(days=90)
        if self.end_date is None and self.start_date is not None:
            self.end_date = datetime.now(timezone.utc)

    @property
    def cache_key_fragment(self) -> str:
        parts = []
        if self.start_date:
            parts.append(f"s={self.start_date.date()}")
        if self.end_date:
            parts.append(f"e={self.end_date.date()}")
        if self.branch_id:
            parts.append(f"b={self.branch_id}")
        if self.fiscal_year:
            parts.append(f"fy={self.fiscal_year}")
        if self.state_code:
            parts.append(f"st={self.state_code}")
        for k, v in sorted(self.extra.items()):
            parts.append(f"{k}={v}")
        return "|".join(parts)


@dataclass
class ReportResult:
    title: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    sections: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    rows: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        def _serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, date):
                return obj.isoformat()
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, Enum):
                return obj.value
            return obj

        def _walk(data):
            if isinstance(data, dict):
                return {k: _walk(v) for k, v in data.items()}
            if isinstance(data, (list, tuple)):
                return [_walk(v) for v in data]
            return _serialize(data)

        return _walk({
            "title": self.title,
            "generated_at": self.generated_at,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "sections": self.sections,
            "summary": self.summary,
            "rows": self.rows,
            "metadata": self.metadata,
        })


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------

@dataclass
class ReportProgress:
    report_id: str
    total_steps: int = 0
    completed_steps: int = 0
    status: str = "pending"  # pending | running | completed | failed
    message: str = ""
    error: Optional[str] = None

    @property
    def percent_complete(self) -> int:
        if self.total_steps == 0:
            return 0
        return min(100, int(self.completed_steps / self.total_steps * 100))

    def advance(self, message: str = ""):
        self.completed_steps += 1
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "percent_complete": self.percent_complete,
            "status": self.status,
            "message": self.message,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class ReportBuilder(ABC):

    report_name: str = "report"

    def __init__(self, db: AsyncSession):
        self.db = db

    # -- abstract methods --------------------------------------------------

    @abstractmethod
    async def query_data(self, filters: ReportFilters) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def aggregate(self, data: Dict[str, Any], filters: ReportFilters) -> ReportResult:
        pass

    # -- formatting (shared implementation) --------------------------------

    def format(self, result: ReportResult, output: OutputFormat) -> bytes:
        if output == OutputFormat.JSON:
            return self._format_json(result)
        if output == OutputFormat.CSV:
            return self._format_csv(result)
        if output == OutputFormat.EXCEL:
            return self._format_excel(result)
        if output == OutputFormat.PDF:
            return self._format_pdf(result)
        raise ValueError(f"Unsupported output format: {output}")

    # -- orchestrator ------------------------------------------------------

    async def generate(
        self,
        filters: ReportFilters,
        output: OutputFormat = OutputFormat.JSON,
        progress: Optional[ReportProgress] = None,
    ) -> bytes:
        if progress:
            progress.status = "running"
            progress.total_steps = 3
            progress.advance("Querying data")

        raw = await self.query_data(filters)

        if progress:
            progress.advance("Aggregating results")

        result = await self.aggregate(raw, filters)

        if progress:
            progress.advance("Formatting output")

        formatted = self.format(result, output)

        if progress:
            progress.status = "completed"

        return formatted

    # -- shared formatters -------------------------------------------------

    def _format_json(self, result: ReportResult) -> bytes:
        return json.dumps(result.to_dict(), indent=2, default=str).encode("utf-8")

    def _format_csv(self, result: ReportResult) -> bytes:
        buf = io.StringIO()
        writer = csv.writer(buf)

        # Header row
        writer.writerow([result.title])
        if result.period_start and result.period_end:
            writer.writerow([
                f"Period: {result.period_start.date()} to {result.period_end.date()}"
            ])
        writer.writerow([f"Generated: {result.generated_at.isoformat()}"])
        writer.writerow([])

        # Summary section
        if result.summary:
            writer.writerow(["SUMMARY"])
            for key, value in result.summary.items():
                writer.writerow([key.replace("_", " ").title(), _fmt(value)])
            writer.writerow([])

        # Sections
        for section_name, section_data in result.sections.items():
            writer.writerow([section_name.upper().replace("_", " ")])
            if isinstance(section_data, list) and section_data:
                headers = list(section_data[0].keys())
                writer.writerow(headers)
                for row in section_data:
                    writer.writerow([_fmt(row.get(h, "")) for h in headers])
            elif isinstance(section_data, dict):
                for k, v in section_data.items():
                    writer.writerow([k.replace("_", " ").title(), _fmt(v)])
            writer.writerow([])

        # Detail rows
        if result.rows:
            writer.writerow(["DETAILS"])
            if result.rows:
                headers = list(result.rows[0].keys())
                writer.writerow(headers)
                for row in result.rows:
                    writer.writerow([_fmt(row.get(h, "")) for h in headers])

        return buf.getvalue().encode("utf-8")

    def _format_excel(self, result: ReportResult) -> bytes:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill

        wb = Workbook()
        ws = wb.active
        ws.title = result.title[:31]  # Excel limit

        header_font = Font(bold=True, size=14)
        section_font = Font(bold=True, size=12)
        col_header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

        row_num = 1
        ws.cell(row=row_num, column=1, value=result.title).font = header_font
        row_num += 1
        if result.period_start and result.period_end:
            ws.cell(
                row=row_num, column=1,
                value=f"Period: {result.period_start.date()} to {result.period_end.date()}"
            )
            row_num += 1
        ws.cell(row=row_num, column=1, value=f"Generated: {result.generated_at.isoformat()}")
        row_num += 2

        # Summary
        if result.summary:
            ws.cell(row=row_num, column=1, value="Summary").font = section_font
            row_num += 1
            for key, value in result.summary.items():
                ws.cell(row=row_num, column=1, value=key.replace("_", " ").title())
                ws.cell(row=row_num, column=2, value=_fmt(value))
                row_num += 1
            row_num += 1

        # Sections
        for section_name, section_data in result.sections.items():
            ws.cell(
                row=row_num, column=1,
                value=section_name.replace("_", " ").title()
            ).font = section_font
            row_num += 1

            if isinstance(section_data, list) and section_data:
                headers = list(section_data[0].keys())
                for col_idx, h in enumerate(headers, 1):
                    cell = ws.cell(row=row_num, column=col_idx, value=h.replace("_", " ").title())
                    cell.fill = col_header_fill
                    cell.font = Font(bold=True)
                row_num += 1
                for data_row in section_data:
                    for col_idx, h in enumerate(headers, 1):
                        ws.cell(row=row_num, column=col_idx, value=_fmt(data_row.get(h, "")))
                    row_num += 1
            elif isinstance(section_data, dict):
                for k, v in section_data.items():
                    ws.cell(row=row_num, column=1, value=k.replace("_", " ").title())
                    ws.cell(row=row_num, column=2, value=_fmt(v))
                    row_num += 1
            row_num += 1

        # Detail rows sheet
        if result.rows:
            detail_ws = wb.create_sheet("Details")
            headers = list(result.rows[0].keys())
            for col_idx, h in enumerate(headers, 1):
                cell = detail_ws.cell(row=1, column=col_idx, value=h.replace("_", " ").title())
                cell.fill = col_header_fill
                cell.font = Font(bold=True)
            for r_idx, data_row in enumerate(result.rows, 2):
                for col_idx, h in enumerate(headers, 1):
                    detail_ws.cell(row=r_idx, column=col_idx, value=_fmt(data_row.get(h, "")))

        out = io.BytesIO()
        wb.save(out)
        return out.getvalue()

    def _format_pdf(self, result: ReportResult) -> bytes:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        title_style = ParagraphStyle(
            "ReportTitle", parent=styles["Title"], fontSize=18, spaceAfter=12,
        )
        elements.append(Paragraph(result.title, title_style))

        if result.period_start and result.period_end:
            elements.append(Paragraph(
                f"Period: {result.period_start.date()} to {result.period_end.date()}",
                styles["Normal"],
            ))
        elements.append(Paragraph(
            f"Generated: {result.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            styles["Normal"],
        ))
        elements.append(Spacer(1, 0.3 * inch))

        # Summary table
        if result.summary:
            elements.append(Paragraph("Summary", styles["Heading2"]))
            summary_data = [
                [k.replace("_", " ").title(), str(_fmt(v))]
                for k, v in result.summary.items()
            ]
            t = Table(summary_data, colWidths=[3 * inch, 3 * inch])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.85, 0.88, 0.95)),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.2 * inch))

        # Section tables
        for section_name, section_data in result.sections.items():
            elements.append(Paragraph(
                section_name.replace("_", " ").title(),
                styles["Heading2"],
            ))

            if isinstance(section_data, list) and section_data:
                headers = list(section_data[0].keys())
                table_data = [
                    [h.replace("_", " ").title() for h in headers]
                ]
                for row in section_data[:200]:  # cap for PDF size
                    table_data.append([str(_fmt(row.get(h, ""))) for h in headers])

                col_width = min(6.5 * inch / max(len(headers), 1), 2 * inch)
                t = Table(table_data, colWidths=[col_width] * len(headers))
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.85, 0.88, 0.95)),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]))
                elements.append(t)
            elif isinstance(section_data, dict) and section_data:
                kv_data = [
                    [k.replace("_", " ").title(), str(_fmt(v))]
                    for k, v in section_data.items()
                ]
                t = Table(kv_data, colWidths=[3 * inch, 3 * inch])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.85, 0.88, 0.95)),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                ]))
                elements.append(t)

            elements.append(Spacer(1, 0.2 * inch))

        doc.build(elements)
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return "; ".join(f"{k}: {_fmt(v)}" for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return ", ".join(str(_fmt(v)) for v in value)
    return value
