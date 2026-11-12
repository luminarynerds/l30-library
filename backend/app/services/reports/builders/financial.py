# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import and_, func, select, extract

from ....models.fine import (
    Fine, FinePaymentHistory, FineStatus, FineType, PaymentMethod,
)
from ....models.user import User
from ..base import ReportBuilder, ReportFilters, ReportResult

logger = get_logger(__name__)


class FinancialReportBuilder(ReportBuilder):

    report_name = "financial"

    async def query_data(self, filters: ReportFilters) -> Dict[str, Any]:
        start = filters.start_date
        end = filters.end_date

        # Run sequentially — shared DB session cannot handle concurrent ops
        revenue = await self._query_revenue(start, end)
        trends = await self._query_fine_trends(start, end)
        payment_methods = await self._query_payment_methods(start, end)
        waived = await self._query_waived_fines(start, end)
        outstanding = await self._query_outstanding_balances()
        budget = await self._query_budget_vs_actual(filters.fiscal_year or end.year)

        return {
            "revenue": revenue,
            "trends": trends,
            "payment_methods": payment_methods,
            "waived": waived,
            "outstanding": outstanding,
            "budget": budget,
        }

    async def aggregate(self, data: Dict[str, Any], filters: ReportFilters) -> ReportResult:
        revenue = data["revenue"]
        waived = data["waived"]
        outstanding = data["outstanding"]

        total_outstanding = sum(
            cat["summary"]["total"]
            for cat in outstanding["categories"].values()
        )
        total_outstanding_count = sum(
            cat["summary"]["count"]
            for cat in outstanding["categories"].values()
        )

        result = ReportResult(
            title="Financial Report",
            period_start=filters.start_date,
            period_end=filters.end_date,
            summary={
                "total_revenue": revenue["total_revenue"],
                "total_waived_count": waived["count"],
                "total_waived_amount": waived["total"],
                "total_outstanding_count": total_outstanding_count,
                "total_outstanding_balance": total_outstanding,
                "total_payment_transactions": sum(
                    m["count"] for m in data["payment_methods"]["methods"].values()
                ),
            },
            sections={
                "revenue_by_type": [
                    {"type": k, "count": v["count"], "total": v["total"]}
                    for k, v in revenue["by_type"].items()
                ],
                "monthly_breakdown": revenue["monthly_breakdown"],
                "payment_methods": [
                    {"method": k, **v}
                    for k, v in data["payment_methods"]["methods"].items()
                ],
                "outstanding_aging": {
                    k: v["summary"]
                    for k, v in outstanding["categories"].items()
                },
                "budget_vs_actual": data["budget"],
            },
            rows=outstanding.get("detail_rows", []),
            metadata={"collection_trend_days": (filters.end_date - filters.start_date).days},
        )
        return result

    # -- revenue -----------------------------------------------------------

    async def _query_revenue(self, start, end) -> Dict[str, Any]:
        q = select(
            Fine.fine_type,
            func.count(Fine.id).label("count"),
            func.sum(Fine.amount_paid).label("total"),
        ).where(and_(
            Fine.status.in_([FineStatus.paid, FineStatus.partial]),
            Fine.paid_at >= start,
            Fine.paid_at <= end,
        )).group_by(Fine.fine_type)

        rows = (await self.db.execute(q)).all()

        by_type = {}
        total_revenue = Decimal("0")
        for fine_type, count, total in rows:
            amount = total or Decimal("0")
            by_type[fine_type.value] = {"count": count, "total": float(amount)}
            total_revenue += amount

        # Monthly breakdown
        monthly_q = select(
            extract("year", Fine.paid_at).label("year"),
            extract("month", Fine.paid_at).label("month"),
            func.sum(Fine.amount_paid).label("total"),
        ).where(and_(
            Fine.status.in_([FineStatus.paid, FineStatus.partial]),
            Fine.paid_at >= start,
            Fine.paid_at <= end,
        )).group_by("year", "month").order_by("year", "month")

        monthly_rows = (await self.db.execute(monthly_q)).all()
        monthly = [
            {"month": f"{int(y)}-{int(m):02d}", "revenue": float(t or 0)}
            for y, m, t in monthly_rows
        ]

        return {
            "total_revenue": float(total_revenue),
            "by_type": by_type,
            "monthly_breakdown": monthly,
        }

    # -- fine trends -------------------------------------------------------

    async def _query_fine_trends(self, start, end) -> Dict[str, Any]:
        daily_q = select(
            func.date(Fine.paid_at).label("day"),
            func.count(Fine.id).label("count"),
            func.sum(Fine.amount_paid).label("total"),
        ).where(and_(
            Fine.status.in_([FineStatus.paid, FineStatus.partial]),
            Fine.paid_at >= start,
            Fine.paid_at <= end,
        )).group_by(func.date(Fine.paid_at)).order_by(func.date(Fine.paid_at))

        rows = (await self.db.execute(daily_q)).all()
        return {
            "daily_collection": [
                {"date": str(d), "count": c, "amount": float(t or 0)}
                for d, c, t in rows
            ],
        }

    # -- payment methods ---------------------------------------------------

    async def _query_payment_methods(self, start, end) -> Dict[str, Any]:
        q = select(
            FinePaymentHistory.payment_method,
            func.count(FinePaymentHistory.id).label("count"),
            func.sum(FinePaymentHistory.amount).label("total"),
        ).where(and_(
            FinePaymentHistory.created_at >= start,
            FinePaymentHistory.created_at <= end,
        )).group_by(FinePaymentHistory.payment_method)

        rows = (await self.db.execute(q)).all()
        methods = {}
        total_amount = Decimal("0")

        for method, count, total in rows:
            amount = total or Decimal("0")
            key = method.value if hasattr(method, "value") else str(method)
            methods[key] = {"count": count, "total": float(amount), "percentage": 0.0}
            total_amount += amount

        if total_amount > 0:
            for m in methods.values():
                m["percentage"] = round(m["total"] / float(total_amount) * 100, 1)

        return {"methods": methods, "total_collected": float(total_amount)}

    # -- waived fines ------------------------------------------------------

    async def _query_waived_fines(self, start, end) -> Dict[str, Any]:
        q = select(
            func.count(Fine.id).label("count"),
            func.sum(Fine.amount).label("total"),
        ).where(and_(
            Fine.status == FineStatus.waived,
            Fine.waived_at >= start,
            Fine.waived_at <= end,
        ))
        row = (await self.db.execute(q)).first()
        return {
            "count": row[0] or 0,
            "total": float(row[1] or Decimal("0")),
        }

    # -- outstanding balances (aging) --------------------------------------

    async def _query_outstanding_balances(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        q = select(Fine).where(and_(
            Fine.status.in_([FineStatus.unpaid, FineStatus.partial]),
            (Fine.amount - Fine.amount_paid) >= Decimal("0.01"),
        )).order_by(Fine.created_at).limit(10000)

        fines = (await self.db.execute(q)).scalars().all()

        buckets = {
            "current_0_30_days": {"fines": [], "summary": {"count": 0, "total": 0.0}},
            "days_31_60": {"fines": [], "summary": {"count": 0, "total": 0.0}},
            "days_61_90": {"fines": [], "summary": {"count": 0, "total": 0.0}},
            "days_90_plus": {"fines": [], "summary": {"count": 0, "total": 0.0}},
        }

        detail_rows = []
        for fine in fines:
            balance = float(fine.amount - fine.amount_paid)
            days_old = (now - fine.created_at).days
            row = {
                "id": fine.id,
                "patron_id": fine.user_id,
                "fine_type": str(fine.fine_type),
                "original_amount": float(fine.amount),
                "amount_paid": float(fine.amount_paid),
                "balance": balance,
                "created_at": fine.created_at.isoformat(),
                "days_outstanding": days_old,
            }
            detail_rows.append(row)

            if days_old <= 30:
                bucket = "current_0_30_days"
            elif days_old <= 60:
                bucket = "days_31_60"
            elif days_old <= 90:
                bucket = "days_61_90"
            else:
                bucket = "days_90_plus"

            buckets[bucket]["fines"].append(row)
            buckets[bucket]["summary"]["count"] += 1
            buckets[bucket]["summary"]["total"] += balance

        # Round totals
        for b in buckets.values():
            b["summary"]["total"] = round(b["summary"]["total"], 2)

        return {"categories": buckets, "detail_rows": detail_rows}

    # -- budget vs actual --------------------------------------------------

    async def _query_budget_vs_actual(self, year: int) -> Dict[str, Any]:
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        q = select(
            extract("month", Fine.paid_at).label("month"),
            func.sum(Fine.amount_paid).label("total"),
        ).where(and_(
            Fine.status.in_([FineStatus.paid, FineStatus.partial]),
            Fine.paid_at >= start,
            Fine.paid_at <= end,
        )).group_by(extract("month", Fine.paid_at)).order_by(
            extract("month", Fine.paid_at)
        )

        rows = (await self.db.execute(q)).all()
        monthly_actual = {
            f"month_{int(m):02d}": float(t or 0) for m, t in rows
        }
        return {"year": year, "monthly_actual": monthly_actual}
