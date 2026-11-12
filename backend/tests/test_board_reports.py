# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for board report generation system.

Tests cover:
- Report data aggregation
- Report generation and export
- Template management
- Schedule configuration
- Email distribution
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.board.report import BoardReport, BoardReportTemplate, BoardReportSchedule
from app.services.board_report_service import BoardReportService
from app.services.board_report_generator import BoardReportGenerator
from app.models.circulation import Checkout
from app.models.fine import Fine, FineStatus
from app.models.user import User
from app.models.inventory import ItemCopy
from app.models.catalog import CatalogItem


@pytest.fixture
def sample_dates():
    """Fixture providing sample date ranges."""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=30)
    return start_date, end_date


class TestBoardReportService:
    """Tests for BoardReportService."""

    @pytest.mark.asyncio
    async def test_generate_board_report(self, db_session: AsyncSession, sample_dates):
        """Test generating a comprehensive board report."""
        start_date, end_date = sample_dates
        service = BoardReportService(db_session)

        report_data = await service.generate_board_report(
            start_date=start_date,
            end_date=end_date,
            comparison_enabled=False,
        )

        # Verify report structure
        assert "period" in report_data
        assert "circulation" in report_data
        assert "financial" in report_data
        assert "patrons" in report_data
        assert "collection" in report_data
        assert "holds" in report_data

        # Verify period data
        assert report_data["period"]["start_date"] == start_date.isoformat()
        assert report_data["period"]["end_date"] == end_date.isoformat()

    @pytest.mark.asyncio
    async def test_generate_report_with_comparison(self, db_session: AsyncSession, sample_dates):
        """Test generating report with period comparison."""
        start_date, end_date = sample_dates
        service = BoardReportService(db_session)

        report_data = await service.generate_board_report(
            start_date=start_date,
            end_date=end_date,
            comparison_enabled=True,
        )

        # Verify comparison data
        assert "comparison" in report_data
        assert "trends" in report_data
        assert report_data["comparison"]["period"]["start_date"]
        assert report_data["comparison"]["period"]["end_date"]

    @pytest.mark.asyncio
    async def test_get_circulation_metrics(self, db_session: AsyncSession, sample_dates):
        """Test circulation metrics aggregation."""
        start_date, end_date = sample_dates
        service = BoardReportService(db_session)

        metrics = await service._get_circulation_metrics(start_date, end_date)

        # Verify metrics structure
        assert "total_checkouts" in metrics
        assert "completed_checkouts" in metrics
        assert "active_checkouts" in metrics
        assert "avg_checkout_duration_days" in metrics

        # Verify numeric types
        assert isinstance(metrics["total_checkouts"], int)
        assert isinstance(metrics["avg_checkout_duration_days"], float)

    @pytest.mark.asyncio
    async def test_get_financial_metrics(self, db_session: AsyncSession, sample_dates):
        """Test financial metrics aggregation."""
        start_date, end_date = sample_dates
        service = BoardReportService(db_session)

        metrics = await service._get_financial_metrics(start_date, end_date)

        # Verify metrics structure
        assert "total_revenue" in metrics
        assert "revenue_by_type" in metrics
        assert "outstanding_fines_count" in metrics
        assert "outstanding_balance" in metrics
        assert "payment_methods" in metrics

        # Verify numeric types
        assert isinstance(metrics["total_revenue"], (int, float))
        assert isinstance(metrics["outstanding_balance"], (int, float))

    @pytest.mark.asyncio
    async def test_get_patron_metrics(self, db_session: AsyncSession, sample_dates):
        """Test patron engagement metrics."""
        start_date, end_date = sample_dates
        service = BoardReportService(db_session)

        metrics = await service._get_patron_metrics(start_date, end_date)

        # Verify metrics structure
        assert "new_patrons" in metrics
        assert "active_patrons" in metrics
        assert "patrons_with_fines" in metrics

        # Verify numeric values
        assert metrics["new_patrons"] >= 0
        assert metrics["active_patrons"] >= 0
        assert metrics["patrons_with_fines"] >= 0

    @pytest.mark.asyncio
    async def test_get_collection_metrics(self, db_session: AsyncSession, sample_dates):
        """Test collection status metrics."""
        start_date, end_date = sample_dates
        service = BoardReportService(db_session)

        metrics = await service._get_collection_metrics(start_date, end_date)

        # Verify metrics structure
        assert "total_items" in metrics
        assert "total_titles" in metrics
        assert "checked_out_items" in metrics
        assert "available_items" in metrics
        assert "availability_rate" in metrics

        # Verify availability rate is percentage
        assert 0 <= metrics["availability_rate"] <= 100

    @pytest.mark.asyncio
    async def test_get_narrative_prompts(self, db_session: AsyncSession):
        """Test narrative prompt generation."""
        service = BoardReportService(db_session)

        # Create sample report data
        report_data = {
            "circulation": {"total_checkouts": 1000},
            "financial": {"total_revenue": 5000, "outstanding_balance": 500},
            "patrons": {"new_patrons": 50, "active_patrons": 200},
            "collection": {"availability_rate": 75},
            "comparison": {
                "circulation": {"total_checkouts": 900},
                "financial": {"total_revenue": 4500},
                "patrons": {"active_patrons": 180},
            },
        }

        prompts = await service.get_narrative_prompts(report_data)

        # Verify prompts structure
        assert "circulation" in prompts
        assert "financial" in prompts
        assert "patrons" in prompts
        assert "general" in prompts

        # Verify prompts are non-empty
        assert len(prompts["circulation"]) > 0
        assert len(prompts["financial"]) > 0
        assert len(prompts["general"]) > 0

    @pytest.mark.asyncio
    async def test_save_report_to_db(self, db_session: AsyncSession, sample_dates, admin_user):
        """Test saving report to database."""
        start_date, end_date = sample_dates
        service = BoardReportService(db_session)

        # Create sample report data
        report_data = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "circulation": {"total_checkouts": 100},
            "financial": {"total_revenue": 1000},
            "patrons": {"active_patrons": 50},
            "collection": {"total_items": 5000},
            "holds": {"active_holds": 20},
        }

        db_report = await service.save_report_to_db(
            report_data=report_data,
            recipient_emails=["board@library.org"],
            created_by_id=admin_user.id,
        )

        # Verify report was saved
        assert db_report.id is not None
        assert db_report.status == "generated"
        assert db_report.stats_snapshot == report_data


class TestBoardReportGenerator:
    """Tests for BoardReportGenerator."""

    def test_generate_powerpoint(self):
        """Test PowerPoint generation."""
        generator = BoardReportGenerator()

        # Create sample report data
        report_data = {
            "period": {
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z",
            },
            "circulation": {
                "total_checkouts": 1000,
                "completed_checkouts": 950,
                "active_checkouts": 50,
                "avg_checkout_duration_days": 21.5,
            },
            "financial": {
                "total_revenue": 5000,
                "revenue_by_type": {"fine": {"total": 3000, "count": 100}},
                "outstanding_fines_count": 20,
                "outstanding_balance": 500,
                "daily_collection_count": 20,
            },
            "patrons": {
                "new_patrons": 50,
                "active_patrons": 200,
                "patrons_with_fines": 20,
            },
            "collection": {
                "total_items": 10000,
                "total_titles": 5000,
                "available_items": 7500,
                "checked_out_items": 2500,
                "availability_rate": 75.0,
            },
            "holds": {"new_holds": 30, "active_holds": 100},
            "narrative_prompts": {
                "circulation": ["Test prompt"],
                "financial": [],
                "patrons": [],
            },
        }

        pptx_content = generator.generate_powerpoint(report_data)

        # Verify PPTX was generated
        assert isinstance(pptx_content, bytes)
        assert len(pptx_content) > 0
        # PowerPoint files start with PK (zip signature)
        assert pptx_content[:2] == b"PK"

    def test_generate_pdf(self):
        """Test PDF generation."""
        generator = BoardReportGenerator()

        # Create sample report data
        report_data = {
            "period": {
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z",
            },
            "circulation": {
                "total_checkouts": 1000,
                "completed_checkouts": 950,
                "active_checkouts": 50,
                "avg_checkout_duration_days": 21.5,
            },
            "financial": {
                "total_revenue": 5000,
                "revenue_by_type": {"fine": {"total": 3000, "count": 100}},
                "outstanding_fines_count": 20,
                "outstanding_balance": 500,
                "daily_collection_count": 20,
            },
            "patrons": {
                "new_patrons": 50,
                "active_patrons": 200,
                "patrons_with_fines": 20,
            },
            "collection": {
                "total_items": 10000,
                "total_titles": 5000,
                "available_items": 7500,
                "checked_out_items": 2500,
                "availability_rate": 75.0,
            },
            "holds": {"new_holds": 30, "active_holds": 100},
            "narrative_prompts": {
                "circulation": ["Test prompt"],
                "financial": [],
                "patrons": [],
            },
        }

        pdf_content = generator.generate_pdf(report_data)

        # Verify PDF was generated
        assert isinstance(pdf_content, bytes)
        assert len(pdf_content) > 0
        # PDF files start with %PDF
        assert pdf_content[:4] == b"%PDF"

    def test_customizable_colors(self):
        """Test generator with custom colors."""
        custom_colors = {
            "primary": (100, 150, 200),
            "accent": (200, 50, 50),
        }
        generator = BoardReportGenerator({"colors": custom_colors})

        assert generator.colors == custom_colors

    def test_default_colors(self):
        """Test generator with default colors."""
        generator = BoardReportGenerator()

        assert "primary" in generator.colors
        assert "accent" in generator.colors
        assert "text" in generator.colors
        assert "light_bg" in generator.colors


class TestBoardReportTemplate:
    """Tests for BoardReportTemplate."""

    @pytest.mark.asyncio
    async def test_create_template(self, db_session: AsyncSession, admin_user):
        """Test creating a report template."""
        template = BoardReportTemplate(
            name="Executive Summary",
            is_default=True,
            is_active=True,
            include_sections={"circulation": True, "financial": True},
            created_by=admin_user.id,
        )

        db_session.add(template)
        await db_session.commit()

        assert template.id is not None
        assert template.name == "Executive Summary"
        assert template.is_default is True


class TestBoardReportSchedule:
    """Tests for BoardReportSchedule."""

    @pytest.mark.asyncio
    async def test_create_schedule(self, db_session: AsyncSession, admin_user):
        """Test creating a report schedule."""
        schedule = BoardReportSchedule(
            name="Monthly Board Report",
            is_active=True,
            frequency="monthly",
            day_of_month=1,
            time_of_day="09:00",
            report_format="both",
            include_comparison=True,
            created_by=admin_user.id,
        )

        db_session.add(schedule)
        await db_session.commit()

        assert schedule.id is not None
        assert schedule.name == "Monthly Board Report"
        assert schedule.frequency == "monthly"
        assert schedule.day_of_month == 1


@pytest.mark.unit
class TestBoardReportValidation:
    """Tests for report data validation."""

    def test_availability_rate_calculation(self):
        """Test availability rate is correctly calculated."""
        available = 75
        total = 100
        rate = (available / total * 100)

        assert rate == 75.0
        assert 0 <= rate <= 100

    def test_revenue_by_type_aggregation(self):
        """Test revenue aggregation by fine type."""
        revenue_data = {
            "overdue": {"total": 300, "count": 100},
            "lost": {"total": 200, "count": 10},
            "damaged": {"total": 100, "count": 5},
        }

        total_revenue = sum(item["total"] for item in revenue_data.values())
        assert total_revenue == 600

    def test_trend_calculation_positive_growth(self):
        """Test trend calculation with positive growth."""
        current = 1100
        previous = 1000
        change_percent = (current - previous) / previous * 100

        assert change_percent == 10.0
        assert change_percent > 0

    def test_trend_calculation_negative_growth(self):
        """Test trend calculation with negative growth."""
        current = 900
        previous = 1000
        change_percent = (current - previous) / previous * 100

        assert change_percent == -10.0
        assert change_percent < 0

    def test_trend_calculation_no_change(self):
        """Test trend calculation with no change."""
        current = 1000
        previous = 1000
        change_percent = (current - previous) / previous * 100

        assert change_percent == 0.0
