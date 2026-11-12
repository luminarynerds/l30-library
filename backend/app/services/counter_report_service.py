# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.branding import branding
from ..models.database_subscription import (
    DatabaseSubscription,
    DatabaseVendor,
)

COUNTER_RELEASE = "5"
REPORT_NAME_DR_D1 = "Database Master Report"
REPORT_ID_DR_D1 = "DR_D1"

# DR_D1 column order per COUNTER R5 Code of Practice. Aggregated over the
# whole reporting period rather than emitting one row per month -- state
# library reports typically want an annual rollup.
DR_D1_COLUMNS = [
    "Database",
    "Publisher",
    "Platform",
    "Searches_Regular",
    "Searches_Federated",
    "Searches_Automated",
    "Total_Item_Requests",
    "Unique_Item_Requests",
    "Total_Item_Investigations",
    "Unique_Item_Investigations",
    "No_License",
]

# Sum these fields when aggregating monthly stats into a yearly row.
_AGGREGATED_METRICS = (
    "searches_regular",
    "searches_federated",
    "searches_automated",
    "total_item_requests",
    "unique_item_requests",
    "total_item_investigations",
    "unique_item_investigations",
    "no_license",
)


class CounterReportService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_dr_d1(self, year: int) -> str:
        subs = await self._load_subscriptions_with_stats(year)
        header = self._build_report_header(REPORT_NAME_DR_D1, REPORT_ID_DR_D1, year)

        buf = io.StringIO()
        buf.write(header)
        writer = csv.writer(buf, dialect="excel-tab", lineterminator="\n")
        writer.writerow(DR_D1_COLUMNS)
        for row in self._build_dr_d1_rows(subs, year):
            writer.writerow(row)
        return buf.getvalue()

    async def _load_subscriptions_with_stats(
        self, year: int
    ) -> list[DatabaseSubscription]:
        result = await self.db.execute(
            select(DatabaseSubscription)
            .options(
                selectinload(DatabaseSubscription.vendor),
                selectinload(DatabaseSubscription.usage_stats),
            )
            .order_by(DatabaseSubscription.name)
        )
        subs = result.scalars().all()
        return [
            s
            for s in subs
            if any(stat.stat_year == year for stat in (s.usage_stats or []))
        ]

    def _build_dr_d1_rows(
        self, subs: Iterable[DatabaseSubscription], year: int
    ) -> list[list]:
        rows: list[list] = []
        for sub in subs:
            vendor: DatabaseVendor | None = sub.vendor
            publisher = vendor.name if vendor else ""
            platform = (
                vendor.short_name if vendor and vendor.short_name else publisher
            )

            totals = {field: 0 for field in _AGGREGATED_METRICS}
            for stat in sub.usage_stats or []:
                if stat.stat_year != year:
                    continue
                for field in _AGGREGATED_METRICS:
                    totals[field] += getattr(stat, field, 0) or 0

            rows.append(
                [
                    sub.name,
                    publisher,
                    platform,
                    totals["searches_regular"],
                    totals["searches_federated"],
                    totals["searches_automated"],
                    totals["total_item_requests"],
                    totals["unique_item_requests"],
                    totals["total_item_investigations"],
                    totals["unique_item_investigations"],
                    totals["no_license"],
                ]
            )
        return rows

    def _build_report_header(
        self, report_name: str, report_id: str, year: int
    ) -> str:
        institution = branding.library_name
        created = datetime.now(timezone.utc).date().isoformat()
        begin = date(year, 1, 1).isoformat()
        end = date(year, 12, 31).isoformat()

        lines = [
            f"Report_Name\t{report_name}",
            f"Report_ID\t{report_id}",
            f"Release\t{COUNTER_RELEASE}",
            f"Institution_Name\t{institution}",
            "Institution_ID\t",
            "Metric_Types\tSearches_Regular; Searches_Federated; Searches_Automated; "
            "Total_Item_Requests; Unique_Item_Requests; Total_Item_Investigations; "
            "Unique_Item_Investigations; No_License",
            f"Report_Filters\tBegin_Date={begin}; End_Date={end}",
            "Report_Attributes\t",
            "Exceptions\t",
            f"Reporting_Period\tBegin_Date={begin}; End_Date={end}",
            f"Created\t{created}",
            "Created_By\tL30 Library System",
            "",  # blank separator before the column header row
        ]
        return "\n".join(lines) + "\n"


def estimate_cost_per_use(
    annual_cost: Decimal | None, total_item_requests: int | None
) -> Decimal | None:
    if not annual_cost or not total_item_requests or total_item_requests <= 0:
        return None
    return (annual_cost / Decimal(total_item_requests)).quantize(Decimal("0.0001"))
