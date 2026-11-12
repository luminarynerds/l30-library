# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the consolidated report builder framework.

Covers:
- ReportBuilder base class (format methods)
- All concrete builders (Circulation, Financial, PatronActivity, Collection, Compliance)
- ReportFactory (type registry, caching, async generation)
- OutputFormat enum coverage (JSON, CSV, Excel, PDF)
- ReportFilters and ReportResult data types
- Progress tracking
"""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.reports.base import (
    OutputFormat,
    ReportBuilder,
    ReportFilters,
    ReportProgress,
    ReportResult,
)
from app.services.reports.factory import (
    DEFAULT_CACHE_TTL,
    ReportFactory,
    ReportType,
    _BUILDER_REGISTRY,
)
from app.services.reports.builders import (
    CirculationReportBuilder,
    CollectionReportBuilder,
    ComplianceReportBuilder,
    FinancialReportBuilder,
    PatronActivityReportBuilder,
)


# ============================================================================
# Data types
# ============================================================================


class TestReportFilters:
    """Tests for ReportFilters dataclass."""

    def test_default_dates(self):
        """Defaults to 90-day lookback when no dates provided."""
        f = ReportFilters()
        assert f.start_date is not None
        assert f.end_date is not None
        delta = (f.end_date - f.start_date).days
        assert delta == 90

    def test_explicit_dates(self):
        s = datetime(2024, 1, 1, tzinfo=timezone.utc)
        e = datetime(2024, 6, 30, tzinfo=timezone.utc)
        f = ReportFilters(start_date=s, end_date=e)
        assert f.start_date == s
        assert f.end_date == e

    def test_fiscal_year_skips_default_date(self):
        f = ReportFilters(fiscal_year=2024)
        # Should not set start_date when fiscal_year is provided
        assert f.fiscal_year == 2024

    def test_cache_key_fragment(self):
        f = ReportFilters(
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 6, 30, tzinfo=timezone.utc),
            branch_id=5,
        )
        frag = f.cache_key_fragment
        assert "s=2024-01-01" in frag
        assert "e=2024-06-30" in frag
        assert "b=5" in frag

    def test_cache_key_deterministic(self):
        f1 = ReportFilters(
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 6, 30, tzinfo=timezone.utc),
        )
        f2 = ReportFilters(
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 6, 30, tzinfo=timezone.utc),
        )
        assert f1.cache_key_fragment == f2.cache_key_fragment


class TestReportResult:
    """Tests for ReportResult dataclass."""

    def test_to_dict_basic(self):
        r = ReportResult(title="Test Report")
        d = r.to_dict()
        assert d["title"] == "Test Report"
        assert "generated_at" in d
        assert d["sections"] == {}
        assert d["rows"] == []

    def test_to_dict_serializes_decimal(self):
        r = ReportResult(
            title="Test",
            summary={"total": Decimal("123.45")},
        )
        d = r.to_dict()
        assert d["summary"]["total"] == 123.45
        assert isinstance(d["summary"]["total"], float)

    def test_to_dict_serializes_datetime(self):
        dt = datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)
        r = ReportResult(title="Test", period_start=dt)
        d = r.to_dict()
        assert "2024-06-15" in d["period_start"]

    def test_to_dict_serializes_enum(self):
        r = ReportResult(
            title="Test",
            sections={"format": OutputFormat.PDF},
        )
        d = r.to_dict()
        assert d["sections"]["format"] == "pdf"


class TestReportProgress:
    """Tests for ReportProgress dataclass."""

    def test_initial_state(self):
        p = ReportProgress(report_id="abc-123")
        assert p.percent_complete == 0
        assert p.status == "pending"

    def test_advance(self):
        p = ReportProgress(report_id="abc-123", total_steps=4)
        p.advance("Step 1")
        assert p.completed_steps == 1
        assert p.percent_complete == 25

    def test_percent_capped_at_100(self):
        p = ReportProgress(report_id="x", total_steps=2, completed_steps=5)
        assert p.percent_complete == 100

    def test_to_dict(self):
        p = ReportProgress(report_id="id-1", total_steps=3, status="running")
        p.advance("querying")
        d = p.to_dict()
        assert d["report_id"] == "id-1"
        assert d["completed_steps"] == 1
        assert d["percent_complete"] == 33


# ============================================================================
# Output format enum
# ============================================================================


class TestOutputFormat:
    def test_values(self):
        assert OutputFormat.PDF == "pdf"
        assert OutputFormat.CSV == "csv"
        assert OutputFormat.EXCEL == "excel"
        assert OutputFormat.JSON == "json"


# ============================================================================
# ReportType enum & builder registry
# ============================================================================


class TestReportType:
    def test_all_types_registered(self):
        for rt in ReportType:
            assert rt in _BUILDER_REGISTRY

    def test_builder_classes(self):
        assert _BUILDER_REGISTRY[ReportType.CIRCULATION] is CirculationReportBuilder
        assert _BUILDER_REGISTRY[ReportType.FINANCIAL] is FinancialReportBuilder
        assert _BUILDER_REGISTRY[ReportType.PATRON_ACTIVITY] is PatronActivityReportBuilder
        assert _BUILDER_REGISTRY[ReportType.COLLECTION] is CollectionReportBuilder
        assert _BUILDER_REGISTRY[ReportType.COMPLIANCE] is ComplianceReportBuilder


# ============================================================================
# Base ReportBuilder format methods
# ============================================================================


class TestReportBuilderFormatters:
    """Test the shared format methods on the base class."""

    def _make_result(self):
        return ReportResult(
            title="Test Financial Report",
            period_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(2024, 6, 30, tzinfo=timezone.utc),
            summary={
                "total_revenue": Decimal("1234.56"),
                "total_items": 42,
            },
            sections={
                "revenue_by_type": [
                    {"type": "overdue", "count": 10, "total": Decimal("500.00")},
                    {"type": "lost_item", "count": 5, "total": Decimal("734.56")},
                ],
                "aging": {
                    "current": 100,
                    "days_31_60": 50,
                },
            },
            rows=[
                {"id": 1, "amount": Decimal("10.00"), "status": "unpaid"},
                {"id": 2, "amount": Decimal("20.00"), "status": "paid"},
            ],
        )

    def test_format_json(self):
        """JSON formatter produces valid JSON with all sections."""
        # Use a concrete subclass to test
        result = self._make_result()
        builder = FinancialReportBuilder.__new__(FinancialReportBuilder)
        out = builder._format_json(result)

        assert isinstance(out, bytes)
        data = json.loads(out.decode("utf-8"))
        assert data["title"] == "Test Financial Report"
        assert data["summary"]["total_revenue"] == 1234.56
        assert len(data["sections"]["revenue_by_type"]) == 2
        assert len(data["rows"]) == 2

    def test_format_csv(self):
        """CSV formatter includes title, summary, sections, and detail rows."""
        result = self._make_result()
        builder = FinancialReportBuilder.__new__(FinancialReportBuilder)
        out = builder._format_csv(result)

        assert isinstance(out, bytes)
        text = out.decode("utf-8")
        assert "Test Financial Report" in text
        assert "SUMMARY" in text
        assert "Total Revenue" in text
        assert "REVENUE BY TYPE" in text
        assert "DETAILS" in text

    def test_format_excel(self):
        """Excel formatter produces valid XLSX bytes."""
        result = self._make_result()
        builder = FinancialReportBuilder.__new__(FinancialReportBuilder)
        out = builder._format_excel(result)

        assert isinstance(out, bytes)
        # XLSX files start with PK (ZIP header)
        assert out[:2] == b"PK"

    def test_format_pdf(self):
        """PDF formatter produces valid PDF bytes."""
        result = self._make_result()
        builder = FinancialReportBuilder.__new__(FinancialReportBuilder)
        out = builder._format_pdf(result)

        assert isinstance(out, bytes)
        assert out[:5] == b"%PDF-"

    def test_format_dispatch(self):
        """format() dispatches to the correct formatter."""
        result = self._make_result()
        builder = FinancialReportBuilder.__new__(FinancialReportBuilder)

        json_out = builder.format(result, OutputFormat.JSON)
        assert json.loads(json_out)["title"] == "Test Financial Report"

        csv_out = builder.format(result, OutputFormat.CSV)
        assert b"Test Financial Report" in csv_out

        excel_out = builder.format(result, OutputFormat.EXCEL)
        assert excel_out[:2] == b"PK"

        pdf_out = builder.format(result, OutputFormat.PDF)
        assert pdf_out[:5] == b"%PDF-"

    def test_format_invalid_raises(self):
        result = self._make_result()
        builder = FinancialReportBuilder.__new__(FinancialReportBuilder)
        with pytest.raises(ValueError, match="Unsupported"):
            builder.format(result, "xml")


# ============================================================================
# ReportFactory
# ============================================================================


class TestReportFactory:
    """Tests for the ReportFactory."""

    def test_get_builder_returns_correct_type(self):
        db = MagicMock()
        factory = ReportFactory(db)

        builder = factory.get_builder(ReportType.FINANCIAL)
        assert isinstance(builder, FinancialReportBuilder)

        builder = factory.get_builder(ReportType.CIRCULATION)
        assert isinstance(builder, CirculationReportBuilder)

    def test_get_builder_unknown_type_raises(self):
        db = MagicMock()
        factory = ReportFactory(db)
        with pytest.raises(ValueError, match="Unknown report type"):
            factory.get_builder("nonexistent")

    def test_cache_key_varies_by_type_and_format(self):
        db = MagicMock()
        factory = ReportFactory(db)
        filters = ReportFilters(
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 6, 30, tzinfo=timezone.utc),
        )
        k1 = factory._cache_key(ReportType.FINANCIAL, filters, OutputFormat.JSON)
        k2 = factory._cache_key(ReportType.FINANCIAL, filters, OutputFormat.PDF)
        k3 = factory._cache_key(ReportType.CIRCULATION, filters, OutputFormat.JSON)

        assert k1 != k2  # different format
        assert k1 != k3  # different type
        assert "financial" in k1
        assert "circulation" in k3

    def test_default_ttls_defined_for_all_types(self):
        for rt in ReportType:
            assert rt in DEFAULT_CACHE_TTL


# ============================================================================
# Concrete builder smoke tests (with mocked DB)
# ============================================================================


class TestFinancialReportBuilder:
    """Smoke test for FinancialReportBuilder with mocked DB."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        # Mock execute to return empty result sets
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.first.return_value = (0, Decimal("0"))
        mock_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        mock_result.scalar.return_value = 0
        db.execute = AsyncMock(return_value=mock_result)
        return db

    @pytest.mark.asyncio
    async def test_query_data_returns_all_sections(self, mock_db):
        builder = FinancialReportBuilder(mock_db)
        filters = ReportFilters()
        data = await builder.query_data(filters)

        assert "revenue" in data
        assert "trends" in data
        assert "payment_methods" in data
        assert "waived" in data
        assert "outstanding" in data
        assert "budget" in data

    @pytest.mark.asyncio
    async def test_aggregate_produces_result(self, mock_db):
        builder = FinancialReportBuilder(mock_db)
        filters = ReportFilters()
        data = await builder.query_data(filters)
        result = await builder.aggregate(data, filters)

        assert isinstance(result, ReportResult)
        assert result.title == "Financial Report"
        assert "total_revenue" in result.summary

    @pytest.mark.asyncio
    async def test_generate_json(self, mock_db):
        builder = FinancialReportBuilder(mock_db)
        filters = ReportFilters()
        output = await builder.generate(filters, OutputFormat.JSON)

        data = json.loads(output)
        assert data["title"] == "Financial Report"

    @pytest.mark.asyncio
    async def test_generate_csv(self, mock_db):
        builder = FinancialReportBuilder(mock_db)
        filters = ReportFilters()
        output = await builder.generate(filters, OutputFormat.CSV)

        text = output.decode("utf-8")
        assert "Financial Report" in text

    @pytest.mark.asyncio
    async def test_generate_excel(self, mock_db):
        builder = FinancialReportBuilder(mock_db)
        filters = ReportFilters()
        output = await builder.generate(filters, OutputFormat.EXCEL)
        assert output[:2] == b"PK"

    @pytest.mark.asyncio
    async def test_generate_pdf(self, mock_db):
        builder = FinancialReportBuilder(mock_db)
        filters = ReportFilters()
        output = await builder.generate(filters, OutputFormat.PDF)
        assert output[:5] == b"%PDF-"

    @pytest.mark.asyncio
    async def test_generate_with_progress_tracking(self, mock_db):
        builder = FinancialReportBuilder(mock_db)
        filters = ReportFilters()
        progress = ReportProgress(report_id="test-1")

        await builder.generate(filters, OutputFormat.JSON, progress=progress)

        assert progress.status == "completed"
        assert progress.completed_steps == 3
        assert progress.percent_complete == 100


class TestCirculationReportBuilder:
    """Smoke test for CirculationReportBuilder with mocked DB."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.first.return_value = (0,)
        mock_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        mock_result.scalar.return_value = 0
        db.execute = AsyncMock(return_value=mock_result)
        return db

    @pytest.mark.asyncio
    async def test_query_data_structure(self, mock_db):
        builder = CirculationReportBuilder(mock_db)
        filters = ReportFilters()
        data = await builder.query_data(filters)

        assert "checkouts" in data
        assert "returns" in data
        assert "overdue" in data
        assert "holds" in data
        assert "popular_items" in data

    @pytest.mark.asyncio
    async def test_generate_all_formats(self, mock_db):
        builder = CirculationReportBuilder(mock_db)
        filters = ReportFilters()

        for fmt in OutputFormat:
            output = await builder.generate(filters, fmt)
            assert isinstance(output, bytes)
            assert len(output) > 0


class TestPatronActivityReportBuilder:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.first.return_value = (0,)
        mock_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        mock_result.scalar.return_value = 0
        db.execute = AsyncMock(return_value=mock_result)
        return db

    @pytest.mark.asyncio
    async def test_query_data_structure(self, mock_db):
        builder = PatronActivityReportBuilder(mock_db)
        filters = ReportFilters()
        data = await builder.query_data(filters)

        assert "new_patrons" in data
        assert "active_patrons" in data
        assert "top_borrowers" in data
        assert "fine_stats" in data
        assert "demographics" in data


class TestCollectionReportBuilder:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.first.return_value = (0, 0)
        mock_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        mock_result.scalar.return_value = 0
        db.execute = AsyncMock(return_value=mock_result)
        return db

    @pytest.mark.asyncio
    async def test_query_data_structure(self, mock_db):
        builder = CollectionReportBuilder(mock_db)
        filters = ReportFilters()
        data = await builder.query_data(filters)

        assert "totals" in data
        assert "by_format" in data
        assert "additions" in data
        assert "lost_damaged" in data
        assert "turnover" in data


class TestComplianceReportBuilder:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.first.return_value = (0,)
        mock_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        mock_result.scalar.return_value = 0
        db.execute = AsyncMock(return_value=mock_result)
        return db

    @pytest.mark.asyncio
    async def test_query_data_structure(self, mock_db):
        builder = ComplianceReportBuilder(mock_db)
        filters = ReportFilters(fiscal_year=2024)
        data = await builder.query_data(filters)

        assert "fiscal_year" in data
        assert "circulation" in data
        assert "patrons" in data
        assert "collection" in data
        assert "programs" in data
        assert "financial" in data
        assert "prior_year" in data

    @pytest.mark.asyncio
    async def test_aggregate_includes_yoy(self, mock_db):
        builder = ComplianceReportBuilder(mock_db)
        filters = ReportFilters(fiscal_year=2024)
        data = await builder.query_data(filters)
        result = await builder.aggregate(data, filters)

        assert "year_over_year" in result.sections
        assert result.title.startswith("Annual Compliance Report")


# ============================================================================
# Factory generate (with mocked builder)
# ============================================================================


class TestReportFactoryGenerate:
    """Test factory.generate orchestration."""

    @pytest.mark.asyncio
    async def test_generate_without_cache(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.first.return_value = (0, Decimal("0"))
        mock_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        mock_result.scalar.return_value = 0
        db.execute = AsyncMock(return_value=mock_result)

        factory = ReportFactory(db, redis=None)
        filters = ReportFilters()
        result = await factory.generate(
            ReportType.FINANCIAL, filters, OutputFormat.JSON, use_cache=False,
        )

        data = json.loads(result)
        assert data["title"] == "Financial Report"

    @pytest.mark.asyncio
    async def test_generate_all_types_json(self):
        """Ensure every registered type can produce JSON output."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.first.return_value = (0, Decimal("0"), 0)
        mock_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        mock_result.scalar.return_value = 0
        db.execute = AsyncMock(return_value=mock_result)

        factory = ReportFactory(db, redis=None)
        filters = ReportFilters(fiscal_year=2024)

        for rt in ReportType:
            result = await factory.generate(
                rt, filters, OutputFormat.JSON, use_cache=False,
            )
            data = json.loads(result)
            assert "title" in data
            assert "summary" in data
