# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict

from sqlalchemy import and_, func, select

from ....models.circulation import Checkout
from ....models.fine import Fine, FineStatus
from ....models.user import User, UserRole
from ..base import ReportBuilder, ReportFilters, ReportResult

logger = get_logger(__name__)


class PatronActivityReportBuilder(ReportBuilder):

    report_name = "patron_activity"

    async def query_data(self, filters: ReportFilters) -> Dict[str, Any]:
        start = filters.start_date
        end = filters.end_date

        # Run sequentially — shared DB session cannot handle concurrent ops
        new_patrons = await self._count_new_patrons(start, end)
        active_patrons = await self._count_active_patrons(start, end)
        top_borrowers = await self._get_top_borrowers(start, end)
        fine_stats = await self._get_patron_fine_stats(start, end)
        demographics = await self._get_demographics()

        return {
            "new_patrons": new_patrons,
            "active_patrons": active_patrons,
            "top_borrowers": top_borrowers,
            "fine_stats": fine_stats,
            "demographics": demographics,
        }

    async def aggregate(self, data: Dict[str, Any], filters: ReportFilters) -> ReportResult:
        engagement_rate = 0.0
        total_registered = data["demographics"]["total_registered"]
        if total_registered > 0:
            engagement_rate = round(
                data["active_patrons"] / total_registered * 100, 1
            )

        return ReportResult(
            title="Patron Activity Report",
            period_start=filters.start_date,
            period_end=filters.end_date,
            summary={
                "new_patrons": data["new_patrons"],
                "active_patrons": data["active_patrons"],
                "total_registered": total_registered,
                "engagement_rate": f"{engagement_rate}%",
                "patrons_with_fines": data["fine_stats"]["patrons_with_fines"],
                "total_fines_outstanding": data["fine_stats"]["outstanding_total"],
            },
            sections={
                "top_borrowers": data["top_borrowers"],
                "demographics": data["demographics"]["by_age_group"],
                "fine_summary": data["fine_stats"],
            },
            rows=data["top_borrowers"],
        )

    # -- queries -----------------------------------------------------------

    async def _count_new_patrons(self, start, end) -> int:
        q = select(func.count(User.id)).where(and_(
            User.created_at >= start,
            User.created_at <= end,
            User.role == UserRole.PATRON,
        ))
        return (await self.db.execute(q)).scalar() or 0

    async def _count_active_patrons(self, start, end) -> int:
        q = select(func.count(func.distinct(Checkout.user_id))).where(and_(
            Checkout.checked_out_at >= start,
            Checkout.checked_out_at <= end,
        ))
        return (await self.db.execute(q)).scalar() or 0

    async def _get_top_borrowers(self, start, end, limit=25):
        q = select(
            Checkout.user_id,
            func.count(Checkout.id).label("checkouts"),
        ).where(and_(
            Checkout.checked_out_at >= start,
            Checkout.checked_out_at <= end,
        )).group_by(Checkout.user_id).order_by(
            func.count(Checkout.id).desc()
        ).limit(limit)

        rows = (await self.db.execute(q)).all()
        return [
            {"patron_id": uid, "checkouts": cnt}
            for uid, cnt in rows
        ]

    async def _get_patron_fine_stats(self, start, end) -> Dict[str, Any]:
        patrons_q = select(func.count(func.distinct(Fine.user_id))).where(and_(
            Fine.created_at >= start,
            Fine.created_at <= end,
        ))
        patrons_with_fines = (await self.db.execute(patrons_q)).scalar() or 0

        outstanding_q = select(
            func.sum(Fine.amount - Fine.amount_paid),
        ).where(Fine.status.in_([FineStatus.unpaid, FineStatus.partial]))
        outstanding_total = float((await self.db.execute(outstanding_q)).scalar() or 0)

        return {
            "patrons_with_fines": patrons_with_fines,
            "outstanding_total": round(outstanding_total, 2),
        }

    async def _get_demographics(self) -> Dict[str, Any]:
        total_q = select(func.count(User.id)).where(
            User.role == UserRole.PATRON
        )
        total = (await self.db.execute(total_q)).scalar() or 0

        # Patron age distribution (using date_of_birth if available)
        users_q = select(User.date_of_birth).where(and_(
            User.role == UserRole.PATRON,
            User.date_of_birth.isnot(None),
        ))
        dobs = (await self.db.execute(users_q)).scalars().all()

        today = date.today()
        age_groups = {
            "child_0_12": 0,
            "teen_13_18": 0,
            "adult_19_64": 0,
            "senior_65_plus": 0,
        }
        for dob in dobs:
            age = today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day)
            )
            if age < 13:
                age_groups["child_0_12"] += 1
            elif age < 19:
                age_groups["teen_13_18"] += 1
            elif age < 65:
                age_groups["adult_19_64"] += 1
            else:
                age_groups["senior_65_plus"] += 1

        return {
            "total_registered": total,
            "by_age_group": age_groups,
        }
