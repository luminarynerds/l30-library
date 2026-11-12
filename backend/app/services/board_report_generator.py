# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
import json
from app.core.logging import get_logger
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logger = get_logger(__name__)


class BoardReportGenerator:

    # Default color scheme
    DEFAULT_COLORS = {
        "primary": (31, 78, 121),      # Dark blue
        "accent": (192, 0, 0),          # Red
        "text": (0, 0, 0),              # Black
        "light_bg": (242, 242, 242),    # Light gray
    }

    def __init__(self, template_config: Optional[Dict[str, Any]] = None):
        self.template_config = template_config or {}
        self.colors = self.template_config.get("colors", self.DEFAULT_COLORS)

    def generate_powerpoint(
        self,
        report_data: Dict[str, Any],
        title: str = "Board Report",
        organization: str = "Library System",
        logo_path: Optional[str] = None,
    ) -> bytes:
        prs = Presentation()
        prs.slide_width = Inches(10)
        prs.slide_height = Inches(7.5)

        # Define slide layouts
        blank_layout = prs.slide_layouts[6]

        try:
            # Title slide
            self._add_title_slide(prs, title, organization, report_data)

            # Executive Summary
            self._add_summary_slide(prs, blank_layout, report_data)

            # Circulation metrics
            self._add_circulation_slide(prs, blank_layout, report_data)

            # Financial metrics
            self._add_financial_slide(prs, blank_layout, report_data)

            # Patron engagement
            self._add_patron_slide(prs, blank_layout, report_data)

            # Collection status
            self._add_collection_slide(prs, blank_layout, report_data)

            # Website traffic (skip if Umami unreachable)
            if report_data.get("website"):
                self._add_website_slide(prs, blank_layout, report_data)

            # Key trends (if comparison data exists)
            if "comparison" in report_data and "trends" in report_data:
                self._add_trends_slide(prs, blank_layout, report_data)

            # Key takeaways and discussion prompts
            self._add_takeaways_slide(prs, blank_layout, report_data)

            # Save to bytes
            output = io.BytesIO()
            prs.save(output)
            output.seek(0)
            return output.getvalue()

        except Exception as e:
            logger.error(f"Error generating PowerPoint: {e}", exc_info=True)
            raise

    def generate_pdf(
        self,
        report_data: Dict[str, Any],
        title: str = "Board Report",
        organization: str = "Library System",
    ) -> bytes:
        output = io.BytesIO()

        try:
            doc = SimpleDocTemplate(
                output,
                pagesize=letter,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch,
            )

            story = []
            styles = getSampleStyleSheet()

            # Custom styles
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                textColor=colors.Color(self.colors["primary"][0]/255, self.colors["primary"][1]/255, self.colors["primary"][2]/255),
                spaceAfter=12,
                alignment=TA_CENTER,
            )

            heading_style = ParagraphStyle(
                "CustomHeading",
                parent=styles["Heading2"],
                fontSize=16,
                textColor=colors.Color(self.colors["primary"][0]/255, self.colors["primary"][1]/255, self.colors["primary"][2]/255),
                spaceAfter=10,
                spaceBefore=10,
            )

            # Title section
            story.append(Paragraph(title, title_style))
            story.append(
                Paragraph(
                    f"{organization} | "
                    f"{report_data['period']['start_date']} to "
                    f"{report_data['period']['end_date']}",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, 0.3 * inch))

            # Executive summary
            story.append(Paragraph("Executive Summary", heading_style))
            summary_data = self._format_summary_table(report_data)
            story.append(self._create_table(summary_data))
            story.append(Spacer(1, 0.2 * inch))

            # Circulation metrics
            story.append(Paragraph("Circulation Metrics", heading_style))
            circ_data = self._format_circulation_table(report_data)
            story.append(self._create_table(circ_data))
            story.append(Spacer(1, 0.2 * inch))

            # Financial metrics
            story.append(Paragraph("Financial Metrics", heading_style))
            fin_data = self._format_financial_table(report_data)
            story.append(self._create_table(fin_data))
            story.append(Spacer(1, 0.2 * inch))

            # Patron metrics
            story.append(Paragraph("Patron Engagement", heading_style))
            patron_data = self._format_patron_table(report_data)
            story.append(self._create_table(patron_data))
            story.append(Spacer(1, 0.2 * inch))

            # Collection status
            story.append(Paragraph("Collection Status", heading_style))
            coll_data = self._format_collection_table(report_data)
            story.append(self._create_table(coll_data))

            # Website traffic (skip if Umami unreachable)
            if report_data.get("website"):
                story.append(Spacer(1, 0.2 * inch))
                story.append(Paragraph("Website Traffic", heading_style))
                story.append(self._create_table(self._format_website_table(report_data)))
                top_pages = report_data["website"].get("top_pages") or []
                if top_pages:
                    story.append(Spacer(1, 0.15 * inch))
                    story.append(Paragraph("Top Pages", styles["Heading4"]))
                    rows = [["Page", "Views"]] + [
                        [str(p.get("path") or "(unknown)"), f"{int(p.get('views') or 0):,}"]
                        for p in top_pages
                    ]
                    story.append(self._create_table(rows))

            # Build PDF
            doc.build(story)
            output.seek(0)
            return output.getvalue()

        except Exception as e:
            logger.error(f"Error generating PDF: {e}", exc_info=True)
            raise

    def _add_title_slide(
        self, prs: Presentation, title: str, organization: str, report_data: Dict[str, Any]
    ) -> None:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(*self.colors["primary"])

        # Add title
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(2.5), Inches(9), Inches(1.5)
        )
        title_frame = title_box.text_frame
        title_frame.word_wrap = True
        p = title_frame.paragraphs[0]
        p.text = title
        p.font.size = Pt(54)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.alignment = PP_ALIGN.CENTER

        # Add organization
        org_box = slide.shapes.add_textbox(Inches(0.5), Inches(4), Inches(9), Inches(0.5))
        org_frame = org_box.text_frame
        p = org_frame.paragraphs[0]
        p.text = organization
        p.font.size = Pt(28)
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.alignment = PP_ALIGN.CENTER

        # Add period
        period = f"{report_data['period']['start_date']} to {report_data['period']['end_date']}"
        period_box = slide.shapes.add_textbox(Inches(0.5), Inches(4.8), Inches(9), Inches(0.4))
        period_frame = period_box.text_frame
        p = period_frame.paragraphs[0]
        p.text = period
        p.font.size = Pt(18)
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.alignment = PP_ALIGN.CENTER

    def _add_summary_slide(
        self, prs: Presentation, blank_layout, report_data: Dict[str, Any]
    ) -> None:
        slide = prs.slides.add_slide(blank_layout)
        self._add_slide_title(slide, "Executive Summary")

        # Key metrics boxes
        metrics = [
            ("Total Checkouts", str(report_data["circulation"]["total_checkouts"])),
            ("Total Revenue", f"${report_data['financial']['total_revenue']:,.0f}"),
            ("Active Patrons", str(report_data["patrons"]["active_patrons"])),
            ("Collection Size", str(report_data["collection"]["total_items"])),
        ]

        y_pos = 1.5
        for i, (label, value) in enumerate(metrics):
            x_pos = 0.5 if i < 2 else 5.25
            y_offset = 0 if i < 2 else y_pos

            self._add_metric_box(slide, label, value, x_pos, y_pos + y_offset, Inches(4), Inches(1))

            if i == 1:
                y_pos += 1.5

    def _add_circulation_slide(
        self, prs: Presentation, blank_layout, report_data: Dict[str, Any]
    ) -> None:
        slide = prs.slides.add_slide(blank_layout)
        self._add_slide_title(slide, "Circulation Metrics")

        circ = report_data["circulation"]
        holds = report_data["holds"]

        metrics = [
            f"Total Checkouts: {circ['total_checkouts']:,}",
            f"Completed Checkouts: {circ['completed_checkouts']:,}",
            f"Active Checkouts: {circ['active_checkouts']:,}",
            f"Avg. Checkout Duration: {circ['avg_checkout_duration_days']:.1f} days",
            f"Active Holds: {holds['active_holds']:,}",
            f"New Holds This Period: {holds['new_holds']:,}",
        ]

        y_pos = 1.5
        for metric in metrics:
            text_box = slide.shapes.add_textbox(Inches(1), Inches(y_pos), Inches(8), Inches(0.4))
            text_frame = text_box.text_frame
            p = text_frame.paragraphs[0]
            p.text = "• " + metric
            p.font.size = Pt(14)
            y_pos += 0.5

    def _add_financial_slide(
        self, prs: Presentation, blank_layout, report_data: Dict[str, Any]
    ) -> None:
        slide = prs.slides.add_slide(blank_layout)
        self._add_slide_title(slide, "Financial Metrics")

        fin = report_data["financial"]

        metrics = [
            f"Total Revenue: ${fin['total_revenue']:,.2f}",
            f"Outstanding Fines: {fin['outstanding_fines_count']:,} accounts",
            f"Outstanding Balance: ${fin['outstanding_balance']:,.2f}",
            f"Fine Collections This Period: {fin['daily_collection_count']} days tracked",
        ]

        y_pos = 1.5
        for metric in metrics:
            text_box = slide.shapes.add_textbox(Inches(1), Inches(y_pos), Inches(8), Inches(0.4))
            text_frame = text_box.text_frame
            p = text_frame.paragraphs[0]
            p.text = "• " + metric
            p.font.size = Pt(14)
            y_pos += 0.5

        # Revenue by type
        if fin.get("revenue_by_type"):
            y_pos += 0.3
            text_box = slide.shapes.add_textbox(Inches(1), Inches(y_pos), Inches(8), Inches(0.3))
            text_frame = text_box.text_frame
            p = text_frame.paragraphs[0]
            p.text = "Revenue by Type:"
            p.font.size = Pt(12)
            p.font.bold = True
            y_pos += 0.4

            for fine_type, data in fin.get("revenue_by_type", {}).items():
                text_box = slide.shapes.add_textbox(Inches(1.5), Inches(y_pos), Inches(7.5), Inches(0.3))
                text_frame = text_box.text_frame
                p = text_frame.paragraphs[0]
                p.text = f"  {fine_type}: ${data.get('total', 0):,.2f} ({data.get('count', 0)} items)"
                p.font.size = Pt(11)
                y_pos += 0.3

    def _add_patron_slide(
        self, prs: Presentation, blank_layout, report_data: Dict[str, Any]
    ) -> None:
        slide = prs.slides.add_slide(blank_layout)
        self._add_slide_title(slide, "Patron Engagement")

        patrons = report_data["patrons"]

        metrics = [
            f"New Patrons: {patrons['new_patrons']:,}",
            f"Active Patrons: {patrons['active_patrons']:,}",
            f"Patrons with Fines: {patrons['patrons_with_fines']:,}",
        ]

        y_pos = 1.5
        for metric in metrics:
            text_box = slide.shapes.add_textbox(Inches(1), Inches(y_pos), Inches(8), Inches(0.4))
            text_frame = text_box.text_frame
            p = text_frame.paragraphs[0]
            p.text = "• " + metric
            p.font.size = Pt(14)
            y_pos += 0.5

    def _add_collection_slide(
        self, prs: Presentation, blank_layout, report_data: Dict[str, Any]
    ) -> None:
        slide = prs.slides.add_slide(blank_layout)
        self._add_slide_title(slide, "Collection Status")

        coll = report_data["collection"]

        metrics = [
            f"Total Items: {coll['total_items']:,}",
            f"Total Titles: {coll['total_titles']:,}",
            f"Available Items: {coll['available_items']:,}",
            f"Checked Out Items: {coll['checked_out_items']:,}",
            f"Availability Rate: {coll['availability_rate']:.1f}%",
        ]

        y_pos = 1.5
        for metric in metrics:
            text_box = slide.shapes.add_textbox(Inches(1), Inches(y_pos), Inches(8), Inches(0.4))
            text_frame = text_box.text_frame
            p = text_frame.paragraphs[0]
            p.text = "• " + metric
            p.font.size = Pt(14)
            y_pos += 0.5

    def _add_website_slide(
        self, prs: Presentation, blank_layout, report_data: Dict[str, Any]
    ) -> None:
        slide = prs.slides.add_slide(blank_layout)
        self._add_slide_title(slide, "Website Traffic")

        site = report_data.get("website") or {}

        metrics = [
            f"Pageviews: {int(site.get('pageviews') or 0):,}",
            f"Visitors: {int(site.get('visitors') or 0):,}",
            f"Visits: {int(site.get('visits') or 0):,}",
            f"Bounces: {int(site.get('bounces') or 0):,}",
        ]

        y_pos = 1.5
        for metric in metrics:
            text_box = slide.shapes.add_textbox(Inches(1), Inches(y_pos), Inches(8), Inches(0.4))
            text_frame = text_box.text_frame
            p = text_frame.paragraphs[0]
            p.text = "• " + metric
            p.font.size = Pt(14)
            y_pos += 0.5

        top_pages = (site.get("top_pages") or [])[:5]
        if top_pages:
            y_pos += 0.2
            text_box = slide.shapes.add_textbox(Inches(1), Inches(y_pos), Inches(8), Inches(0.4))
            p = text_box.text_frame.paragraphs[0]
            p.text = "Top Pages:"
            p.font.size = Pt(12)
            p.font.bold = True
            y_pos += 0.4
            for page in top_pages:
                text_box = slide.shapes.add_textbox(Inches(1.5), Inches(y_pos), Inches(7.5), Inches(0.4))
                p = text_box.text_frame.paragraphs[0]
                p.text = f"{page.get('path') or '(unknown)'} — {int(page.get('views') or 0):,} views"
                p.font.size = Pt(12)
                y_pos += 0.35

    def _add_trends_slide(
        self, prs: Presentation, blank_layout, report_data: Dict[str, Any]
    ) -> None:
        slide = prs.slides.add_slide(blank_layout)
        self._add_slide_title(slide, "Period Comparison")

        trends = report_data.get("trends", {})

        y_pos = 1.5
        text_box = slide.shapes.add_textbox(Inches(1), Inches(y_pos), Inches(8), Inches(0.3))
        text_frame = text_box.text_frame
        p = text_frame.paragraphs[0]
        p.text = "vs. Previous Period:"
        p.font.size = Pt(12)
        p.font.bold = True
        y_pos += 0.5

        if "checkout_change_percent" in trends:
            change = trends["checkout_change_percent"]
            symbol = "↑" if change > 0 else "↓"
            text_box = slide.shapes.add_textbox(Inches(1.5), Inches(y_pos), Inches(7.5), Inches(0.4))
            text_frame = text_box.text_frame
            p = text_frame.paragraphs[0]
            p.text = f"{symbol} Checkouts: {change:+.1f}%"
            p.font.size = Pt(14)
            y_pos += 0.5

        if "revenue_change_percent" in trends:
            change = trends["revenue_change_percent"]
            symbol = "↑" if change > 0 else "↓"
            text_box = slide.shapes.add_textbox(Inches(1.5), Inches(y_pos), Inches(7.5), Inches(0.4))
            text_frame = text_box.text_frame
            p = text_frame.paragraphs[0]
            p.text = f"{symbol} Revenue: {change:+.1f}%"
            p.font.size = Pt(14)
            y_pos += 0.5

        if "patron_engagement_change_percent" in trends:
            change = trends["patron_engagement_change_percent"]
            symbol = "↑" if change > 0 else "↓"
            text_box = slide.shapes.add_textbox(Inches(1.5), Inches(y_pos), Inches(7.5), Inches(0.4))
            text_frame = text_box.text_frame
            p = text_frame.paragraphs[0]
            p.text = f"{symbol} Patron Engagement: {change:+.1f}%"
            p.font.size = Pt(14)
            y_pos += 0.5

    def _add_takeaways_slide(
        self, prs: Presentation, blank_layout, report_data: Dict[str, Any]
    ) -> None:
        slide = prs.slides.add_slide(blank_layout)
        self._add_slide_title(slide, "Discussion Points")

        prompts = report_data.get("narrative_prompts", {})

        y_pos = 1.5
        for category in ["circulation", "financial", "patrons"]:
            if prompts.get(category):
                text_box = slide.shapes.add_textbox(Inches(0.5), Inches(y_pos), Inches(9), Inches(0.3))
                text_frame = text_box.text_frame
                p = text_frame.paragraphs[0]
                p.text = f"{category.title()}:"
                p.font.size = Pt(12)
                p.font.bold = True
                y_pos += 0.4

                for prompt in prompts[category][:2]:  # First 2 prompts per category
                    text_box = slide.shapes.add_textbox(Inches(0.75), Inches(y_pos), Inches(8.5), Inches(0.5))
                    text_frame = text_box.text_frame
                    text_frame.word_wrap = True
                    p = text_frame.paragraphs[0]
                    p.text = "• " + prompt
                    p.font.size = Pt(11)
                    y_pos += 0.5

                y_pos += 0.1

    def _add_slide_title(self, slide, title: str) -> None:
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(9), Inches(0.6))
        title_frame = title_box.text_frame
        p = title_frame.paragraphs[0]
        p.text = title
        p.font.size = Pt(32)
        p.font.bold = True
        p.font.color.rgb = RGBColor(*self.colors["primary"])

    def _add_metric_box(
        self, slide, label: str, value: str, x: float, y: float, width: float, height: float
    ) -> None:
        shape = slide.shapes.add_shape(1, x, y, width, height)  # 1 = rectangle
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(*self.colors["light_bg"])
        shape.line.color.rgb = RGBColor(*self.colors["primary"])

        text_frame = shape.text_frame
        text_frame.margin_bottom = Inches(0.05)
        text_frame.margin_left = Inches(0.1)
        text_frame.margin_right = Inches(0.1)
        text_frame.margin_top = Inches(0.05)

        # Label
        p = text_frame.paragraphs[0]
        p.text = label
        p.font.size = Pt(11)
        p.font.color.rgb = RGBColor(*self.colors["primary"])
        p.alignment = PP_ALIGN.CENTER

        # Value
        p = text_frame.add_paragraph()
        p.text = value
        p.font.size = Pt(18)
        p.font.bold = True
        p.font.color.rgb = RGBColor(*self.colors["accent"])
        p.alignment = PP_ALIGN.CENTER

    def _format_summary_table(self, report_data: Dict[str, Any]) -> List[List[str]]:
        return [
            ["Metric", "Value"],
            ["Total Checkouts", str(report_data["circulation"]["total_checkouts"])],
            ["Revenue", f"${report_data['financial']['total_revenue']:,.0f}"],
            ["Active Patrons", str(report_data["patrons"]["active_patrons"])],
            ["Collection Size", f"{report_data['collection']['total_items']:,} items"],
        ]

    def _format_circulation_table(self, report_data: Dict[str, Any]) -> List[List[str]]:
        circ = report_data["circulation"]
        return [
            ["Metric", "Count"],
            ["Total Checkouts", str(circ["total_checkouts"])],
            ["Completed", str(circ["completed_checkouts"])],
            ["Active", str(circ["active_checkouts"])],
            ["Avg Duration (days)", f"{circ['avg_checkout_duration_days']:.1f}"],
        ]

    def _format_financial_table(self, report_data: Dict[str, Any]) -> List[List[str]]:
        fin = report_data["financial"]
        return [
            ["Metric", "Amount/Count"],
            ["Total Revenue", f"${fin['total_revenue']:,.2f}"],
            ["Outstanding Fines", f"{fin['outstanding_fines_count']} accounts"],
            ["Outstanding Balance", f"${fin['outstanding_balance']:,.2f}"],
        ]

    def _format_patron_table(self, report_data: Dict[str, Any]) -> List[List[str]]:
        patrons = report_data["patrons"]
        return [
            ["Metric", "Count"],
            ["New Patrons", str(patrons["new_patrons"])],
            ["Active Patrons", str(patrons["active_patrons"])],
            ["With Fines", str(patrons["patrons_with_fines"])],
        ]

    def _format_collection_table(self, report_data: Dict[str, Any]) -> List[List[str]]:
        coll = report_data["collection"]
        return [
            ["Metric", "Count"],
            ["Total Items", f"{coll['total_items']:,}"],
            ["Total Titles", f"{coll['total_titles']:,}"],
            ["Available", f"{coll['available_items']:,}"],
            ["Availability Rate", f"{coll['availability_rate']:.1f}%"],
        ]

    def _format_website_table(self, report_data: Dict[str, Any]) -> List[List[str]]:
        site = report_data.get("website") or {}
        return [
            ["Metric", "Count"],
            ["Pageviews", f"{int(site.get('pageviews') or 0):,}"],
            ["Visitors", f"{int(site.get('visitors') or 0):,}"],
            ["Visits", f"{int(site.get('visits') or 0):,}"],
            ["Bounces", f"{int(site.get('bounces') or 0):,}"],
        ]

    def _create_table(self, data: List[List[str]]) -> Table:
        table = Table(data, colWidths=[3 * inch, 2.25 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                ]
            )
        )
        return table
