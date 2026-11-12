# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict

from sqlalchemy import and_, func, select

from ....models.catalog import CatalogItem
from ....models.circulation import Checkout
from ....models.inventory import ItemCopy
from ....models.lost_damaged import DamagedItemRecord, LostItemRecord
from ..base import ReportBuilder, ReportFilters, ReportResult

logger = get_logger(__name__)


class CollectionReportBuilder(ReportBuilder):

    report_name = "collection"

    async def query_data(self, filters: ReportFilters) -> Dict[str, Any]:
        start = filters.start_date
        end = filters.end_date

        # Run sequentially — shared DB session cannot handle concurrent ops
        totals = await self._get_totals()
        by_format = await self._get_by_format()
        additions = await self._get_additions(start, end)
        lost_damaged = await self._get_lost_damaged(start, end)
        turnover = await self._get_turnover(start, end)

        return {
            "totals": totals,
            "by_format": by_format,
            "additions": additions,
            "lost_damaged": lost_damaged,
            "turnover": turnover,
        }

    async def aggregate(self, data: Dict[str, Any], filters: ReportFilters) -> ReportResult:
        totals = data["totals"]
        ld = data["lost_damaged"]

        availability_rate = 0.0
        if totals["total_items"] > 0:
            availability_rate = round(
                totals["available_items"] / totals["total_items"] * 100, 1
            )

        return ReportResult(
            title="Collection Report",
            period_start=filters.start_date,
            period_end=filters.end_date,
            summary={
                "total_items": totals["total_items"],
                "total_titles": totals["total_titles"],
                "available_items": totals["available_items"],
                "checked_out_items": totals["checked_out_items"],
                "availability_rate": f"{availability_rate}%",
                "items_added": data["additions"]["count"],
                "items_lost": ld["lost_count"],
                "items_damaged": ld["damaged_count"],
                "turnover_rate": data["turnover"]["rate"],
            },
            sections={
                "items_by_format": data["by_format"],
                "lost_damaged_summary": {
                    "lost_count": ld["lost_count"],
                    "lost_value": ld["lost_value"],
                    "damaged_count": ld["damaged_count"],
                    "damaged_value": ld["damaged_value"],
                },
            },
        )

    # -- queries -----------------------------------------------------------

    async def _get_totals(self) -> Dict[str, int]:
        total_q = select(func.count(ItemCopy.id))
        total = (await self.db.execute(total_q)).scalar() or 0

        titles_q = select(func.count(func.distinct(CatalogItem.id)))
        titles = (await self.db.execute(titles_q)).scalar() or 0

        # Derive checked-out count from active checkouts
        checked_out_q = select(func.count(func.distinct(Checkout.item_copy_id))).where(
            Checkout.returned_at.is_(None)
        )
        checked_out = (await self.db.execute(checked_out_q)).scalar() or 0
        available = max(total - checked_out, 0)

        return {
            "total_items": total,
            "total_titles": titles,
            "available_items": available,
            "checked_out_items": checked_out,
        }

    async def _get_by_format(self):
        q = select(
            CatalogItem.item_type,
            func.count(ItemCopy.id).label("count"),
        ).join(
            ItemCopy, CatalogItem.id == ItemCopy.catalog_item_id
        ).group_by(CatalogItem.item_type).order_by(func.count(ItemCopy.id).desc())

        rows = (await self.db.execute(q)).all()
        return [
            {
                "format": (itype.value if hasattr(itype, "value") else str(itype)),
                "count": cnt,
            }
            for itype, cnt in rows
            if itype is not None
        ]

    async def _get_additions(self, start, end) -> Dict[str, int]:
        q = select(func.count(ItemCopy.id)).where(and_(
            ItemCopy.created_at >= start,
            ItemCopy.created_at <= end,
        ))
        count = (await self.db.execute(q)).scalar() or 0
        return {"count": count}

    async def _get_lost_damaged(self, start, end) -> Dict[str, Any]:
        lost_q = select(
            func.count(LostItemRecord.id),
            func.coalesce(func.sum(LostItemRecord.replacement_cost), 0),
        ).where(and_(
            LostItemRecord.reported_at >= start,
            LostItemRecord.reported_at <= end,
        ))
        lost_row = (await self.db.execute(lost_q)).first()

        damaged_q = select(
            func.count(DamagedItemRecord.id),
            func.coalesce(func.sum(DamagedItemRecord.charge_amount), 0),
        ).where(and_(
            DamagedItemRecord.reported_at >= start,
            DamagedItemRecord.reported_at <= end,
        ))
        damaged_row = (await self.db.execute(damaged_q)).first()

        return {
            "lost_count": lost_row[0] if lost_row else 0,
            "lost_value": float(lost_row[1]) if lost_row else 0.0,
            "damaged_count": damaged_row[0] if damaged_row else 0,
            "damaged_value": float(damaged_row[1]) if damaged_row else 0.0,
        }

    async def _get_turnover(self, start, end) -> Dict[str, Any]:
        checkouts_q = select(func.count(Checkout.id)).where(and_(
            Checkout.checked_out_at >= start,
            Checkout.checked_out_at <= end,
        ))
        checkouts = (await self.db.execute(checkouts_q)).scalar() or 0

        total_q = select(func.count(ItemCopy.id))
        total = (await self.db.execute(total_q)).scalar() or 1

        rate = round(checkouts / total, 2)
        return {"checkouts": checkouts, "total_items": total, "rate": rate}
