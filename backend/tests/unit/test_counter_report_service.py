# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for CounterReportService and helpers."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.counter_report_service import (
    COUNTER_RELEASE,
    DR_D1_COLUMNS,
    REPORT_ID_DR_D1,
    CounterReportService,
    estimate_cost_per_use,
)


class TestEstimateCostPerUse:
    """Pure helper for cost-per-use calculation."""

    def test_returns_none_when_cost_missing(self):
        assert estimate_cost_per_use(None, 100) is None

    def test_returns_none_when_requests_zero(self):
        assert estimate_cost_per_use(Decimal("1200.00"), 0) is None

    def test_returns_none_when_requests_negative(self):
        assert estimate_cost_per_use(Decimal("1200.00"), -1) is None

    def test_returns_none_when_requests_none(self):
        assert estimate_cost_per_use(Decimal("1200.00"), None) is None

    def test_divides_cost_by_requests(self):
        result = estimate_cost_per_use(Decimal("1200.00"), 100)
        assert result == Decimal("12.0000")

    def test_quantizes_to_four_decimal_places(self):
        result = estimate_cost_per_use(Decimal("1000.00"), 333)
        assert result == Decimal("3.0030")


class _StubStat:
    def __init__(self, year, month, **fields):
        self.stat_year = year
        self.stat_month = month
        for k, v in fields.items():
            setattr(self, k, v)


class _StubVendor:
    def __init__(self, name, short_name=None):
        self.name = name
        self.short_name = short_name


class _StubSubscription:
    def __init__(self, name, vendor=None, stats=None):
        self.name = name
        self.vendor = vendor
        self.usage_stats = stats or []


class TestDR_D1Generation:
    """Unit tests for the DR_D1 TSV output."""

    @pytest.fixture
    def service(self):
        db = MagicMock()
        return CounterReportService(db)

    def _stats(self, year, **overrides):
        defaults = dict(
            searches_regular=10,
            searches_federated=2,
            searches_automated=1,
            total_item_requests=100,
            unique_item_requests=80,
            total_item_investigations=150,
            unique_item_investigations=120,
            no_license=3,
        )
        defaults.update(overrides)
        return _StubStat(year=year, month=1, **defaults)

    def test_report_header_includes_required_fields(self, service):
        header = service._build_report_header("Database Master Report", "DR_D1", 2026)
        assert "Report_Name\tDatabase Master Report" in header
        assert "Report_ID\tDR_D1" in header
        assert f"Release\t{COUNTER_RELEASE}" in header
        assert "Begin_Date=2026-01-01" in header
        assert "End_Date=2026-12-31" in header
        # trailing blank line before column header
        assert header.endswith("\n")

    def test_dr_d1_rows_aggregate_monthly_into_yearly_totals(self, service):
        sub = _StubSubscription(
            "Academic Search",
            vendor=_StubVendor("EBSCO", "EBSCOhost"),
            stats=[
                self._stats(2026, total_item_requests=100, searches_regular=10),
                self._stats(2026, total_item_requests=200, searches_regular=20),
                self._stats(2025, total_item_requests=999),  # different year, ignored
            ],
        )
        rows = service._build_dr_d1_rows([sub], 2026)
        assert len(rows) == 1
        row = rows[0]
        assert row[0] == "Academic Search"
        assert row[1] == "EBSCO"
        assert row[2] == "EBSCOhost"
        # searches_regular = 10 + 20
        assert row[3] == 30
        # total_item_requests = 100 + 200
        assert row[6] == 300

    def test_dr_d1_handles_missing_vendor(self, service):
        sub = _StubSubscription(
            "No-Vendor DB", vendor=None, stats=[self._stats(2026)]
        )
        rows = service._build_dr_d1_rows([sub], 2026)
        assert rows[0][1] == ""  # publisher blank
        assert rows[0][2] == ""  # platform blank

    def test_dr_d1_platform_falls_back_to_publisher(self, service):
        sub = _StubSubscription(
            "DB", vendor=_StubVendor("Gale", short_name=None), stats=[self._stats(2026)]
        )
        rows = service._build_dr_d1_rows([sub], 2026)
        assert rows[0][1] == "Gale"
        assert rows[0][2] == "Gale"

    def test_dr_d1_columns_match_counter_r5_spec(self):
        """DR_D1 columns must include all required COUNTER R5 metric names."""
        assert DR_D1_COLUMNS[0] == "Database"
        assert "Publisher" in DR_D1_COLUMNS
        assert "Platform" in DR_D1_COLUMNS
        assert "Searches_Regular" in DR_D1_COLUMNS
        assert "Total_Item_Requests" in DR_D1_COLUMNS
        assert "No_License" in DR_D1_COLUMNS
        assert REPORT_ID_DR_D1 == "DR_D1"

    @pytest.mark.asyncio
    async def test_generate_dr_d1_full_output_shape(self, service):
        """Smoke test: header + columns + a body row form a complete TSV."""
        service._load_subscriptions_with_stats = AsyncMock(
            return_value=[
                _StubSubscription(
                    "JSTOR",
                    vendor=_StubVendor("ITHAKA", "JSTOR"),
                    stats=[self._stats(2026, total_item_requests=42)],
                )
            ]
        )
        out = await service.generate_dr_d1(2026)
        lines = out.splitlines()
        # Header block then blank then column header then one body row
        assert any(line.startswith("Report_ID\tDR_D1") for line in lines)
        col_header_idx = next(i for i, l in enumerate(lines) if l.startswith("Database\t"))
        body = lines[col_header_idx + 1 :]
        assert any(line.startswith("JSTOR\t") for line in body)
        # The TIR for our row should be 42
        jstor_line = next(line for line in body if line.startswith("JSTOR\t"))
        cells = jstor_line.split("\t")
        # Index 6 is Total_Item_Requests
        assert cells[6] == "42"
