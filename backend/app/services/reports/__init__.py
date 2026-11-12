# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Consolidated Report Generation Framework.

Provides a unified interface for generating, formatting, caching, and exporting
reports across all library domains (circulation, financial, patron activity,
collection, compliance).

Usage:
    from app.services.reports import ReportFactory, OutputFormat, ReportType

    factory = ReportFactory(db, redis_client)
    report = await factory.generate(
        ReportType.FINANCIAL,
        filters=ReportFilters(start_date=..., end_date=...),
        output=OutputFormat.PDF,
    )
"""

from .base import OutputFormat, ReportBuilder, ReportFilters, ReportResult
from .builders import (
    CirculationReportBuilder,
    CollectionReportBuilder,
    ComplianceReportBuilder,
    FinancialReportBuilder,
    PatronActivityReportBuilder,
)
from .factory import ReportFactory, ReportType
from .cache_invalidator import invalidate_report_cache

__all__ = [
    "OutputFormat",
    "ReportBuilder",
    "ReportFilters",
    "ReportResult",
    "ReportType",
    "ReportFactory",
    "CirculationReportBuilder",
    "CollectionReportBuilder",
    "ComplianceReportBuilder",
    "FinancialReportBuilder",
    "PatronActivityReportBuilder",
    "invalidate_report_cache",
]
