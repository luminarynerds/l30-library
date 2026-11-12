# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import date
from typing import Any, Dict

from app.services.community_metrics_service import CommunityMetricsService
from ..base import ReportBuilder, ReportFilters, ReportResult

logger = get_logger(__name__)


class CommunityOutcomesReportBuilder(ReportBuilder):
    report_name = "community_outcomes"

    async def query_data(self, filters: ReportFilters) -> Dict[str, Any]:
        service = CommunityMetricsService(self.db)
        start = filters.start_date.date() if filters.start_date else date(date.today().year, 1, 1)
        end = filters.end_date.date() if filters.end_date else date.today()
        return await service.get_dashboard(start, end, filters.branch_id)

    async def aggregate(self, data: Dict[str, Any], filters: ReportFilters) -> ReportResult:
        categories = data.get("categories", {})
        reach = categories.get("program_reach", {})
        edu = categories.get("educational", {})
        partners = categories.get("partnerships", {})
        space = categories.get("space_utilization", {})
        cost = categories.get("cost_effectiveness", {})
        collection = categories.get("collection_impact", {})

        return ReportResult(
            title="Community Outcomes Report",
            period_start=filters.start_date,
            period_end=filters.end_date,
            summary={
                "total_participants": reach.get("total_participants", 0),
                "unique_patrons": reach.get("unique_patrons", 0),
                "active_programs": edu.get("active_programs", 0),
                "active_partnerships": partners.get("active_partnerships", 0),
                "total_events": space.get("total_events", 0),
                "cost_per_attendee": cost.get("cost_per_attendee", 0),
                "total_checkouts": collection.get("total_checkouts", 0),
            },
            sections=categories,
        )
