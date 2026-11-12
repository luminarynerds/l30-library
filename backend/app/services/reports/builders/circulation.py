# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict

from sqlalchemy import and_, func, select

from ....models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ....models.catalog import CatalogItem
from ....models.inventory import ItemCopy
from ....models.user import User
from ..base import ReportBuilder, ReportFilters, ReportResult

logger = get_logger(__name__)


class CirculationReportBuilder(ReportBuilder):

    report_name = "circulation"

    async def query_data(self, filters: ReportFilters) -> Dict[str, Any]:
        start = filters.start_date
        end = filters.end_date

        # Run sequentially — shared DB session cannot handle concurrent ops
        checkouts_q = await self._count_checkouts(start, end)
        returns_q = await self._count_returns(start, end)
        active_q = await self._count_active()
        overdue_q = await self._get_overdue_items()
        holds_q = await self._get_hold_metrics(start, end)
        popular_q = await self._get_popular_items(start, end)

        return {
            "checkouts": checkouts_q,
            "returns": returns_q,
            "active": active_q,
            "overdue": overdue_q,
            "holds": holds_q,
            "popular_items": popular_q,
        }

    async def aggregate(self, data: Dict[str, Any], filters: ReportFilters) -> ReportResult:
        holds = data["holds"]
        fill_rate = 0.0
        if holds["placed"] > 0:
            fill_rate = round(holds["filled"] / holds["placed"] * 100, 1)

        result = ReportResult(
            title="Circulation Report",
            period_start=filters.start_date,
            period_end=filters.end_date,
            summary={
                "total_checkouts": data["checkouts"]["total"],
                "total_returns": data["returns"]["total"],
                "active_checkouts": data["active"]["count"],
                "overdue_items": len(data["overdue"]),
                "holds_placed": holds["placed"],
                "holds_filled": holds["filled"],
                "hold_fill_rate": f"{fill_rate}%",
            },
            sections={
                "checkout_breakdown": data["checkouts"].get("by_type", {}),
                "overdue_items": data["overdue"][:100],
                "popular_items": data["popular_items"],
                "holds": {
                    "placed": holds["placed"],
                    "filled": holds["filled"],
                    "active": holds["active"],
                    "fill_rate": fill_rate,
                },
            },
            rows=data["overdue"],
        )
        return result

    # -- query helpers -----------------------------------------------------

    async def _count_checkouts(self, start, end) -> Dict[str, Any]:
        q = select(
            func.count(Checkout.id).label("total"),
        ).where(and_(
            Checkout.checked_out_at >= start,
            Checkout.checked_out_at <= end,
        ))
        row = (await self.db.execute(q)).first()
        total = row[0] if row else 0

        # By item type
        type_q = select(
            CatalogItem.item_type,
            func.count(Checkout.id),
        ).join(
            ItemCopy, Checkout.item_copy_id == ItemCopy.id
        ).join(
            CatalogItem, ItemCopy.catalog_item_id == CatalogItem.id
        ).where(and_(
            Checkout.checked_out_at >= start,
            Checkout.checked_out_at <= end,
        )).group_by(CatalogItem.item_type)

        type_rows = (await self.db.execute(type_q)).all()
        by_type = {
            (str(itype.value) if hasattr(itype, "value") else str(itype)): count
            for itype, count in type_rows
            if itype is not None
        }

        return {"total": total, "by_type": by_type}

    async def _count_returns(self, start, end) -> Dict[str, Any]:
        q = select(func.count(Checkout.id)).where(and_(
            Checkout.returned_at.isnot(None),
            Checkout.returned_at >= start,
            Checkout.returned_at <= end,
        ))
        total = (await self.db.execute(q)).scalar() or 0
        return {"total": total}

    async def _count_active(self) -> Dict[str, int]:
        q = select(func.count(Checkout.id)).where(
            Checkout.status == CheckoutStatus.active
        )
        count = (await self.db.execute(q)).scalar() or 0
        return {"count": count}

    async def _get_overdue_items(self):
        now = datetime.now(timezone.utc)
        q = select(Checkout).where(and_(
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
            Checkout.due_date < now,
        )).order_by(Checkout.due_date).limit(500)

        rows = (await self.db.execute(q)).scalars().all()
        items = []
        for co in rows:
            days_overdue = (now - co.due_date).days
            items.append({
                "checkout_id": co.id,
                "patron_id": co.user_id,
                "item_copy_id": co.item_copy_id,
                "due_date": co.due_date.isoformat(),
                "days_overdue": days_overdue,
            })
        return items

    async def _get_hold_metrics(self, start, end) -> Dict[str, int]:
        placed_q = select(func.count(Hold.id)).where(and_(
            Hold.created_at >= start,
            Hold.created_at <= end,
        ))
        placed = (await self.db.execute(placed_q)).scalar() or 0

        filled_q = select(func.count(Hold.id)).where(and_(
            Hold.status == HoldStatus.fulfilled,
            Hold.created_at >= start,
            Hold.created_at <= end,
        ))
        filled = (await self.db.execute(filled_q)).scalar() or 0

        active_q = select(func.count(Hold.id)).where(
            Hold.status == HoldStatus.pending,
        )
        active = (await self.db.execute(active_q)).scalar() or 0

        return {"placed": placed, "filled": filled, "active": active}

    async def _get_popular_items(self, start, end, limit=20):
        q = select(
            CatalogItem.id,
            CatalogItem.title,
            func.count(Checkout.id).label("checkout_count"),
        ).join(
            ItemCopy, Checkout.item_copy_id == ItemCopy.id,
        ).join(
            CatalogItem, ItemCopy.catalog_item_id == CatalogItem.id,
        ).where(and_(
            Checkout.checked_out_at >= start,
            Checkout.checked_out_at <= end,
        )).group_by(CatalogItem.id, CatalogItem.title).order_by(
            func.count(Checkout.id).desc()
        ).limit(limit)

        rows = (await self.db.execute(q)).all()
        return [
            {"catalog_item_id": cid, "title": title, "checkouts": cnt}
            for cid, title, cnt in rows
        ]
