# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
import io
from app.core.logging import get_logger
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.branch_resolver import label_to_branch_id, branch_id_to_label

from ..models.usage_statistics import (
    StatisticalReport, ReportStatus, ReportType,
)
from ..schemas.usage_statistics import (
    CirculationStatisticsSummary, CollectionStatisticsSummary,
    ComputerUsageSummary, ExportFormat, IMLSSurveyData,
    MonthOverMonthTrend, PatronStatisticsSummary, PeerComparisonResult,
    ProgramStatisticsSummary, ReferenceStatisticsSummary,
    StatisticsExportRequest, UsageStatisticsDashboard,
    VisitStatisticsSummary, YearOverYearTrend,
)
from .usage_statistics_service import UsageStatisticsService

logger = get_logger(__name__)


class StatisticsExportService:

    def __init__(self, db: AsyncSession, reports_dir: str = "/tmp/reports"):
        self.db = db
        self.stats_service = UsageStatisticsService(db)
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    async def export_statistics(
        self,
        request: StatisticsExportRequest,
        generated_by_id: Optional[int] = None,
    ) -> StatisticalReport:
        # Resolve missing branch side from the request.
        resolved_branch_id = request.branch_id
        resolved_branch_label = request.branch_location
        if resolved_branch_id is None and resolved_branch_label is not None:
            resolved_branch_id = label_to_branch_id(resolved_branch_label)
        elif resolved_branch_id is not None and resolved_branch_label is None:
            resolved_branch_label = branch_id_to_label(resolved_branch_id)

        # Create report record
        report = StatisticalReport(
            report_name=f"Statistics Export {request.period_start} to {request.period_end}",
            report_type=ReportType.CUSTOM,
            period_start=request.period_start,
            period_end=request.period_end,
            branch_id=resolved_branch_id,
            branch_location=resolved_branch_label,
            report_parameters={
                "statistics_types": request.statistics_types,
                "include_trends": request.include_trends,
                "include_peer_comparison": request.include_peer_comparison,
            },
            included_statistics=request.statistics_types,
            file_format=str(request.format),
            status=ReportStatus.GENERATING,
            generated_by_id=generated_by_id,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        try:
            # Gather requested statistics
            data = await self._gather_statistics(request)

            # Generate file based on format
            if request.format == ExportFormat.CSV:
                file_path = await self._export_csv(data, report.id)
            elif request.format == ExportFormat.XLSX:
                file_path = await self._export_xlsx(data, report.id)
            elif request.format == ExportFormat.PDF:
                file_path = await self._export_pdf(data, report.id)
            else:
                raise ValueError(f"Unsupported format: {request.format}")

            # Update report record
            file_size = os.path.getsize(file_path)
            report.file_path = str(file_path)
            report.file_size_bytes = file_size
            report.status = ReportStatus.COMPLETED
            report.generated_at = datetime.now(timezone.utc)

        except Exception as e:  # noqa: BLE001 -- export job boundary: any failure marks report as FAILED for retry, never crash route
            logger.error(f"Failed to export statistics: {e}")
            report.status = ReportStatus.FAILED
            report.error_message = str(e)

        await self.db.commit()
        await self.db.refresh(report)

        return report

    async def _gather_statistics(
        self,
        request: StatisticsExportRequest,
    ) -> Dict[str, Any]:
        data = {
            "period_start": request.period_start,
            "period_end": request.period_end,
            "branch_location": request.branch_location,
            "generated_at": datetime.now(timezone.utc),
        }

        for stat_type in request.statistics_types:
            if stat_type == "circulation":
                data["circulation"] = await self.stats_service.get_circulation_summary(
                    request.period_start, request.period_end, "monthly", request.branch_location
                )
            elif stat_type == "collection":
                data["collection"] = await self.stats_service.get_collection_summary(
                    request.period_end, request.branch_location
                )
            elif stat_type == "patron":
                data["patron"] = await self.stats_service.get_patron_summary(
                    request.period_start, request.period_end, "monthly", request.branch_location
                )
            elif stat_type == "program":
                data["program"] = await self.stats_service.get_program_summary(
                    request.period_start, request.period_end, "monthly", request.branch_location
                )
            elif stat_type == "computer":
                data["computer"] = await self.stats_service.get_computer_usage_summary(
                    request.period_start, request.period_end, "monthly", request.branch_location
                )
            elif stat_type == "reference":
                data["reference"] = await self.stats_service.get_reference_summary(
                    request.period_start, request.period_end, "monthly", request.branch_location
                )
            elif stat_type == "visit":
                data["visit"] = await self.stats_service.get_visit_summary(
                    request.period_start, request.period_end, "monthly", request.branch_location
                )

        # Add trends if requested
        if request.include_trends:
            data["trends"] = {
                "checkouts_mom": await self.stats_service.get_month_over_month_trends(
                    "checkouts", 12, request.branch_location
                ),
                "visits_mom": await self.stats_service.get_month_over_month_trends(
                    "visits", 12, request.branch_location
                ),
            }

        # Add peer comparison if requested
        if request.include_peer_comparison:
            year = request.period_end.year
            data["peer_comparison"] = await self.stats_service.get_peer_comparison(year)

        return data

    async def _export_csv(self, data: Dict[str, Any], report_id: int) -> Path:
        file_path = self.reports_dir / f"statistics_report_{report_id}.csv"

        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)

            # Header
            writer.writerow(["Usage Statistics Report"])
            writer.writerow([f"Period: {data['period_start']} to {data['period_end']}"])
            writer.writerow([f"Generated: {data['generated_at']}"])
            writer.writerow([])

            # Circulation Statistics
            if "circulation" in data:
                circ = data["circulation"]
                writer.writerow(["CIRCULATION STATISTICS"])
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Total Checkouts", circ.total_checkouts])
                writer.writerow(["Total Renewals", circ.total_renewals])
                writer.writerow(["Total Holds", circ.total_holds])
                writer.writerow(["ILL Transactions", circ.total_ill_transactions])
                if circ.turnover_rate:
                    writer.writerow(["Turnover Rate", f"{circ.turnover_rate:.2f}"])
                writer.writerow([])

                # Checkouts by item type
                writer.writerow(["Checkouts by Item Type"])
                writer.writerow(["Item Type", "Count"])
                for item_type, count in circ.checkouts_by_item_type.items():
                    writer.writerow([item_type, count])
                writer.writerow([])

            # Collection Statistics
            if "collection" in data:
                coll = data["collection"]
                writer.writerow(["COLLECTION STATISTICS"])
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Total Items", coll.total_items])
                writer.writerow(["Total Titles", coll.total_titles])
                writer.writerow(["Net Change", coll.net_change])
                if coll.collection_value:
                    writer.writerow(["Collection Value", f"${coll.collection_value:,.2f}"])
                writer.writerow([])

                # Items by format
                writer.writerow(["Items by Format"])
                writer.writerow(["Format", "Count"])
                for fmt, count in coll.items_by_format.items():
                    writer.writerow([fmt, count])
                writer.writerow([])

            # Patron Statistics
            if "patron" in data:
                patron = data["patron"]
                writer.writerow(["PATRON STATISTICS"])
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Total Registered", patron.total_registered])
                writer.writerow(["Active Borrowers", patron.active_borrowers])
                writer.writerow(["New Registrations", patron.new_registrations])
                writer.writerow(["Registration Rate", f"{patron.registration_rate:.2%}"])
                writer.writerow(["Engagement Rate", f"{patron.engagement_rate:.2%}"])
                writer.writerow([])

            # Program Statistics
            if "program" in data:
                prog = data["program"]
                writer.writerow(["PROGRAM STATISTICS"])
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Total Programs", prog.total_programs])
                writer.writerow(["Total Attendance", prog.total_attendance])
                writer.writerow(["Average Attendance", f"{prog.avg_attendance:.1f}"])
                writer.writerow([])

            # Computer Usage Statistics
            if "computer" in data:
                comp = data["computer"]
                writer.writerow(["COMPUTER USAGE STATISTICS"])
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Total Sessions", comp.total_sessions])
                writer.writerow(["Unique Users", comp.unique_users])
                writer.writerow(["Total Hours", f"{comp.total_hours:.1f}"])
                writer.writerow(["Avg Session (min)", f"{comp.avg_session_minutes:.1f}"])
                writer.writerow(["WiFi Sessions", comp.wifi_sessions])
                writer.writerow([])

            # Reference Statistics
            if "reference" in data:
                ref = data["reference"]
                writer.writerow(["REFERENCE STATISTICS"])
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Total Questions", ref.total_questions])
                if ref.avg_duration:
                    writer.writerow(["Avg Duration (min)", f"{ref.avg_duration:.1f}"])
                writer.writerow([])

            # Visit Statistics
            if "visit" in data:
                visit = data["visit"]
                writer.writerow(["VISIT STATISTICS"])
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Total Visits", visit.total_visits])
                writer.writerow(["Avg Daily Visits", f"{visit.avg_daily_visits:.1f}"])
                if visit.visits_per_capita:
                    writer.writerow(["Visits Per Capita", f"{visit.visits_per_capita:.2f}"])
                writer.writerow([])

            # Trends
            if "trends" in data:
                writer.writerow(["TREND ANALYSIS"])
                writer.writerow([])

                writer.writerow(["Checkout Trends (Month-over-Month)"])
                writer.writerow(["Month", "Value", "Previous", "Change %", "Direction"])
                for trend in data["trends"]["checkouts_mom"]:
                    writer.writerow([
                        trend.current_month.isoformat(),
                        trend.current_value,
                        trend.previous_value,
                        f"{trend.change_percent:.1f}%",
                        trend.trend_direction,
                    ])
                writer.writerow([])

            # Peer Comparison
            if "peer_comparison" in data and data["peer_comparison"]:
                writer.writerow(["PEER COMPARISON"])
                writer.writerow(["Metric", "Our Value", "Peer Avg", "Peer Median", "Percentile"])
                for comp in data["peer_comparison"]:
                    writer.writerow([
                        comp.metric_name,
                        f"{comp.our_value:.2f}" if comp.our_value else "N/A",
                        f"{comp.peer_avg:.2f}" if comp.peer_avg else "N/A",
                        f"{comp.peer_median:.2f}" if comp.peer_median else "N/A",
                        f"{comp.percentile_rank:.0f}%" if comp.percentile_rank else "N/A",
                    ])

        return file_path

    async def _export_xlsx(self, data: Dict[str, Any], report_id: int) -> Path:
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.chart import BarChart, Reference
            from openpyxl.utils.dataframe import dataframe_to_rows
        except ImportError:
            logger.warning("openpyxl not available, falling back to CSV")
            return await self._export_csv(data, report_id)

        file_path = self.reports_dir / f"statistics_report_{report_id}.xlsx"

        wb = openpyxl.Workbook()

        # Styles
        header_font = Font(bold=True, size=14)
        subheader_font = Font(bold=True, size=12)
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font_white = Font(bold=True, color="FFFFFF")

        # Summary Sheet
        ws = wb.active
        ws.title = "Summary"

        row = 1
        ws.cell(row=row, column=1, value="Usage Statistics Report").font = header_font
        row += 1
        ws.cell(row=row, column=1, value=f"Period: {data['period_start']} to {data['period_end']}")
        row += 1
        ws.cell(row=row, column=1, value=f"Generated: {data['generated_at']}")
        row += 2

        # Overview table
        overview_data = []
        if "circulation" in data:
            overview_data.append(("Total Checkouts", data["circulation"].total_checkouts))
            overview_data.append(("Total Renewals", data["circulation"].total_renewals))
        if "patron" in data:
            overview_data.append(("Active Borrowers", data["patron"].active_borrowers))
            overview_data.append(("New Registrations", data["patron"].new_registrations))
        if "program" in data:
            overview_data.append(("Total Programs", data["program"].total_programs))
            overview_data.append(("Total Attendance", data["program"].total_attendance))
        if "visit" in data:
            overview_data.append(("Total Visits", data["visit"].total_visits))
        if "reference" in data:
            overview_data.append(("Reference Questions", data["reference"].total_questions))

        # Write overview
        ws.cell(row=row, column=1, value="Overview").font = subheader_font
        row += 1
        ws.cell(row=row, column=1, value="Metric").font = header_font_white
        ws.cell(row=row, column=1).fill = header_fill
        ws.cell(row=row, column=2, value="Value").font = header_font_white
        ws.cell(row=row, column=2).fill = header_fill
        row += 1

        for metric, value in overview_data:
            ws.cell(row=row, column=1, value=metric)
            ws.cell(row=row, column=2, value=value)
            row += 1

        # Circulation Sheet
        if "circulation" in data:
            ws_circ = wb.create_sheet("Circulation")
            circ = data["circulation"]

            ws_circ.cell(row=1, column=1, value="Circulation Statistics").font = header_font

            # Main metrics
            metrics = [
                ("Total Checkouts", circ.total_checkouts),
                ("Total Renewals", circ.total_renewals),
                ("Total Holds", circ.total_holds),
                ("ILL Transactions", circ.total_ill_transactions),
                ("Turnover Rate", f"{circ.turnover_rate:.2f}" if circ.turnover_rate else "N/A"),
            ]

            row = 3
            for metric, value in metrics:
                ws_circ.cell(row=row, column=1, value=metric)
                ws_circ.cell(row=row, column=2, value=value)
                row += 1

            # Checkouts by item type
            row += 1
            ws_circ.cell(row=row, column=1, value="Checkouts by Item Type").font = subheader_font
            row += 1
            ws_circ.cell(row=row, column=1, value="Item Type").font = header_font_white
            ws_circ.cell(row=row, column=1).fill = header_fill
            ws_circ.cell(row=row, column=2, value="Count").font = header_font_white
            ws_circ.cell(row=row, column=2).fill = header_fill
            row += 1

            for item_type, count in circ.checkouts_by_item_type.items():
                ws_circ.cell(row=row, column=1, value=item_type)
                ws_circ.cell(row=row, column=2, value=count)
                row += 1

        # Collection Sheet
        if "collection" in data:
            ws_coll = wb.create_sheet("Collection")
            coll = data["collection"]

            ws_coll.cell(row=1, column=1, value="Collection Statistics").font = header_font

            metrics = [
                ("Total Items", coll.total_items),
                ("Total Titles", coll.total_titles),
                ("Net Change", coll.net_change),
            ]

            row = 3
            for metric, value in metrics:
                ws_coll.cell(row=row, column=1, value=metric)
                ws_coll.cell(row=row, column=2, value=value)
                row += 1

            # Items by format
            row += 1
            ws_coll.cell(row=row, column=1, value="Items by Format").font = subheader_font
            row += 1

            for fmt, count in coll.items_by_format.items():
                ws_coll.cell(row=row, column=1, value=fmt)
                ws_coll.cell(row=row, column=2, value=count)
                row += 1

        # Patron Sheet
        if "patron" in data:
            ws_patron = wb.create_sheet("Patrons")
            patron = data["patron"]

            ws_patron.cell(row=1, column=1, value="Patron Statistics").font = header_font

            metrics = [
                ("Total Registered", patron.total_registered),
                ("Active Borrowers", patron.active_borrowers),
                ("New Registrations", patron.new_registrations),
                ("Registration Rate", f"{patron.registration_rate:.2%}"),
                ("Engagement Rate", f"{patron.engagement_rate:.2%}"),
            ]

            row = 3
            for metric, value in metrics:
                ws_patron.cell(row=row, column=1, value=metric)
                ws_patron.cell(row=row, column=2, value=value)
                row += 1

        # Trends Sheet
        if "trends" in data:
            ws_trends = wb.create_sheet("Trends")
            ws_trends.cell(row=1, column=1, value="Trend Analysis").font = header_font

            # Checkout trends
            ws_trends.cell(row=3, column=1, value="Checkout Trends (Month-over-Month)").font = subheader_font
            row = 5
            headers = ["Month", "Value", "Previous", "Change %", "Direction"]
            for col, header in enumerate(headers, 1):
                ws_trends.cell(row=row, column=col, value=header).font = header_font_white
                ws_trends.cell(row=row, column=col).fill = header_fill
            row += 1

            chart_start_row = row
            for trend in data["trends"]["checkouts_mom"]:
                ws_trends.cell(row=row, column=1, value=trend.current_month.isoformat())
                ws_trends.cell(row=row, column=2, value=trend.current_value)
                ws_trends.cell(row=row, column=3, value=trend.previous_value)
                ws_trends.cell(row=row, column=4, value=trend.change_percent)
                ws_trends.cell(row=row, column=5, value=trend.trend_direction)
                row += 1
            chart_end_row = row - 1

            # Add chart
            if chart_end_row >= chart_start_row:
                chart = BarChart()
                chart.title = "Monthly Checkout Trends"
                chart.y_axis.title = "Checkouts"
                chart.x_axis.title = "Month"

                data_ref = Reference(ws_trends, min_col=2, min_row=chart_start_row - 1,
                                    max_col=2, max_row=chart_end_row)
                cats = Reference(ws_trends, min_col=1, min_row=chart_start_row,
                                max_row=chart_end_row)
                chart.add_data(data_ref, titles_from_data=True)
                chart.set_categories(cats)
                chart.width = 15
                chart.height = 10

                ws_trends.add_chart(chart, f"G{chart_start_row}")

        # Peer Comparison Sheet
        if "peer_comparison" in data and data["peer_comparison"]:
            ws_peer = wb.create_sheet("Peer Comparison")
            ws_peer.cell(row=1, column=1, value="Peer Comparison Analysis").font = header_font

            row = 3
            headers = ["Metric", "Our Value", "Peer Avg", "Peer Median", "Peer Min", "Peer Max", "Percentile"]
            for col, header in enumerate(headers, 1):
                ws_peer.cell(row=row, column=col, value=header).font = header_font_white
                ws_peer.cell(row=row, column=col).fill = header_fill
            row += 1

            for comp in data["peer_comparison"]:
                ws_peer.cell(row=row, column=1, value=comp.metric_name)
                ws_peer.cell(row=row, column=2, value=comp.our_value)
                ws_peer.cell(row=row, column=3, value=comp.peer_avg)
                ws_peer.cell(row=row, column=4, value=comp.peer_median)
                ws_peer.cell(row=row, column=5, value=comp.peer_min)
                ws_peer.cell(row=row, column=6, value=comp.peer_max)
                ws_peer.cell(row=row, column=7, value=f"{comp.percentile_rank:.0f}%")
                row += 1

        # Auto-adjust column widths
        for ws in wb.worksheets:
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except (ValueError, TypeError):
                        # Skip cells with non-string-convertible values
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width

        wb.save(file_path)
        return file_path

    async def _export_pdf(self, data: Dict[str, Any], report_id: int) -> Path:
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.units import inch
        except ImportError:
            logger.warning("reportlab not available, falling back to CSV")
            return await self._export_csv(data, report_id)

        file_path = self.reports_dir / f"statistics_report_{report_id}.pdf"

        doc = SimpleDocTemplate(str(file_path), pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
        )

        # Section header style
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
        )

        # Title
        elements.append(Paragraph("Usage Statistics Report", title_style))
        elements.append(Paragraph(
            f"Period: {data['period_start']} to {data['period_end']}",
            styles['Normal']
        ))
        elements.append(Paragraph(
            f"Generated: {data['generated_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}",
            styles['Normal']
        ))
        elements.append(Spacer(1, 0.3 * inch))

        # Table style
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.4, 0.6)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])

        # Circulation Statistics
        if "circulation" in data:
            elements.append(Paragraph("Circulation Statistics", section_style))
            circ = data["circulation"]

            circ_data = [
                ["Metric", "Value"],
                ["Total Checkouts", str(circ.total_checkouts)],
                ["Total Renewals", str(circ.total_renewals)],
                ["Total Holds", str(circ.total_holds)],
                ["ILL Transactions", str(circ.total_ill_transactions)],
            ]
            if circ.turnover_rate:
                circ_data.append(["Turnover Rate", f"{circ.turnover_rate:.2f}"])

            table = Table(circ_data, colWidths=[3 * inch, 2 * inch])
            table.setStyle(table_style)
            elements.append(table)
            elements.append(Spacer(1, 0.2 * inch))

        # Collection Statistics
        if "collection" in data:
            elements.append(Paragraph("Collection Statistics", section_style))
            coll = data["collection"]

            coll_data = [
                ["Metric", "Value"],
                ["Total Items", str(coll.total_items)],
                ["Total Titles", str(coll.total_titles)],
                ["Net Change", str(coll.net_change)],
            ]

            table = Table(coll_data, colWidths=[3 * inch, 2 * inch])
            table.setStyle(table_style)
            elements.append(table)
            elements.append(Spacer(1, 0.2 * inch))

        # Patron Statistics
        if "patron" in data:
            elements.append(Paragraph("Patron Statistics", section_style))
            patron = data["patron"]

            patron_data = [
                ["Metric", "Value"],
                ["Total Registered", str(patron.total_registered)],
                ["Active Borrowers", str(patron.active_borrowers)],
                ["New Registrations", str(patron.new_registrations)],
                ["Engagement Rate", f"{patron.engagement_rate:.2%}"],
            ]

            table = Table(patron_data, colWidths=[3 * inch, 2 * inch])
            table.setStyle(table_style)
            elements.append(table)
            elements.append(Spacer(1, 0.2 * inch))

        # Program Statistics
        if "program" in data:
            elements.append(Paragraph("Program Statistics", section_style))
            prog = data["program"]

            prog_data = [
                ["Metric", "Value"],
                ["Total Programs", str(prog.total_programs)],
                ["Total Attendance", str(prog.total_attendance)],
                ["Avg Attendance", f"{prog.avg_attendance:.1f}"],
            ]

            table = Table(prog_data, colWidths=[3 * inch, 2 * inch])
            table.setStyle(table_style)
            elements.append(table)
            elements.append(Spacer(1, 0.2 * inch))

        # Visit Statistics
        if "visit" in data:
            elements.append(Paragraph("Visit Statistics", section_style))
            visit = data["visit"]

            visit_data = [
                ["Metric", "Value"],
                ["Total Visits", str(visit.total_visits)],
                ["Avg Daily Visits", f"{visit.avg_daily_visits:.1f}"],
            ]
            if visit.visits_per_capita:
                visit_data.append(["Visits Per Capita", f"{visit.visits_per_capita:.2f}"])

            table = Table(visit_data, colWidths=[3 * inch, 2 * inch])
            table.setStyle(table_style)
            elements.append(table)
            elements.append(Spacer(1, 0.2 * inch))

        # Reference Statistics
        if "reference" in data:
            elements.append(Paragraph("Reference Statistics", section_style))
            ref = data["reference"]

            ref_data = [
                ["Metric", "Value"],
                ["Total Questions", str(ref.total_questions)],
            ]
            if ref.avg_duration:
                ref_data.append(["Avg Duration (min)", f"{ref.avg_duration:.1f}"])

            table = Table(ref_data, colWidths=[3 * inch, 2 * inch])
            table.setStyle(table_style)
            elements.append(table)
            elements.append(Spacer(1, 0.2 * inch))

        # Peer Comparison
        if "peer_comparison" in data and data["peer_comparison"]:
            elements.append(Paragraph("Peer Comparison Analysis", section_style))

            peer_data = [["Metric", "Our Value", "Peer Avg", "Percentile"]]
            for comp in data["peer_comparison"]:
                peer_data.append([
                    comp.metric_name,
                    f"{comp.our_value:.2f}" if comp.our_value else "N/A",
                    f"{comp.peer_avg:.2f}" if comp.peer_avg else "N/A",
                    f"{comp.percentile_rank:.0f}%" if comp.percentile_rank else "N/A",
                ])

            table = Table(peer_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
            table.setStyle(table_style)
            elements.append(table)

        # Build PDF
        doc.build(elements)
        return file_path

    async def export_imls_survey(
        self,
        fiscal_year: int,
        branch_location: Optional[str] = None,
        branch_id: Optional[int] = None,
        generated_by_id: Optional[int] = None,
    ) -> StatisticalReport:
        # Create report record
        report = StatisticalReport(
            report_name=f"IMLS Public Libraries Survey FY{fiscal_year}",
            report_type=ReportType.IMLS_SURVEY,
            fiscal_year=fiscal_year,
            branch_location=branch_location,
            file_format="xlsx",
            status=ReportStatus.GENERATING,
            generated_by_id=generated_by_id,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        try:
            # Generate IMLS data
            imls_data = await self.stats_service.generate_imls_survey_data(
                fiscal_year, resolved_branch_label, branch_id=resolved_branch_id
            )

            # Export to Excel with IMLS format
            file_path = await self._export_imls_xlsx(imls_data, report.id)

            file_size = os.path.getsize(file_path)
            report.file_path = str(file_path)
            report.file_size_bytes = file_size
            report.status = ReportStatus.COMPLETED
            report.generated_at = datetime.now(timezone.utc)

        except Exception as e:  # noqa: BLE001 -- export job boundary: any failure marks report as FAILED for retry, never crash route
            logger.error(f"Failed to export IMLS survey: {e}")
            report.status = ReportStatus.FAILED
            report.error_message = str(e)

        await self.db.commit()
        await self.db.refresh(report)

        return report

    async def _export_imls_xlsx(self, data: IMLSSurveyData, report_id: int) -> Path:
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill
        except ImportError:
            raise ImportError("openpyxl required for IMLS export") from None

        file_path = self.reports_dir / f"imls_survey_{report_id}.xlsx"

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "IMLS Survey Data"

        # Header style
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")

        # Title
        ws.cell(row=1, column=1, value=f"IMLS Public Libraries Survey Data - FY{data.fiscal_year}")
        ws.cell(row=1, column=1).font = Font(bold=True, size=14)
        ws.cell(row=2, column=1, value=f"FSCS ID: {data.library_fscs_id}")

        # Survey questions format
        survey_items = [
            ("", ""),  # Spacer
            ("SERVICE AREA", ""),
            ("Legal Service Area Population", data.service_area_population),
            ("", ""),
            ("LIBRARY COLLECTION", ""),
            ("Print Materials", data.print_collection),
            ("E-books", data.ebook_collection),
            ("Audio - Physical Units", data.audio_physical),
            ("Audio - Downloadable Units", data.audio_downloadable),
            ("Video - Physical Units", data.video_physical),
            ("Video - Downloadable Units", data.video_downloadable),
            ("", ""),
            ("CIRCULATION", ""),
            ("Physical Items Circulation", data.physical_circulation),
            ("Electronic Content Circulation", data.electronic_circulation),
            ("Total Circulation", data.total_circulation),
            ("", ""),
            ("LIBRARY PROGRAMS", ""),
            ("Children's Programs", data.childrens_programs),
            ("Children's Program Attendance", data.childrens_program_attendance),
            ("Young Adult Programs", data.young_adult_programs),
            ("Young Adult Program Attendance", data.young_adult_program_attendance),
            ("Total Programs", data.total_programs),
            ("Total Program Attendance", data.total_program_attendance),
            ("", ""),
            ("LIBRARY SERVICES", ""),
            ("Reference Transactions", data.reference_transactions),
            ("Library Visits", data.library_visits),
            ("Public Computer Uses", data.computer_uses),
            ("Registered Borrowers", data.registered_borrowers),
            ("", ""),
            ("INTERLIBRARY LOANS", ""),
            ("Items Loaned to Other Libraries", data.items_loaned),
            ("Items Borrowed from Other Libraries", data.items_borrowed),
        ]

        row = 4
        for label, value in survey_items:
            if label and not value == "":
                ws.cell(row=row, column=1, value=label)
                ws.cell(row=row, column=2, value=value if value != "" else None)
                if value == "":
                    ws.cell(row=row, column=1).font = header_font
                    ws.cell(row=row, column=1).fill = header_fill
            row += 1

        # Adjust column widths
        ws.column_dimensions['A'].width = 40
        ws.column_dimensions['B'].width = 20

        wb.save(file_path)
        return file_path
