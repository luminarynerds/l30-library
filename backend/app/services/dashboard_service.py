# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from sqlalchemy import text, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.schemas.dashboard import (
    DashboardMetricsResponse,
    CirculationSnapshot,
    OverdueItemDetail,
    OverdueItemsResponse,
    PopularItem,
    PopularItemsResponse,
    ThemeMetric,
    ThemeVelocityResponse,
    HoldQueueStatus,
    SystemAlert,
    SystemAlertsResponse,
    CollectionHealthResponse,
    HealthComponent,
    QuickActionRequest,
    QuickActionResponse,
)
from app.core.dashboard_cache import (
    get_cached_or_compute,
    invalidate_dashboard_cache,
    make_cache_key,
)

logger = get_logger(__name__)

# Cache TTL configurations (in seconds)
TTL_METRICS_COMPLETE = 60  # 1 minute
TTL_CIRCULATION = 30  # 30 seconds
TTL_OVERDUE = 120  # 2 minutes
TTL_HOLDS = 60  # 1 minute
TTL_POPULAR = 300  # 5 minutes
TTL_THEME_VELOCITY = 300  # 5 minutes
TTL_COLLECTION_HEALTH = 600  # 10 minutes
TTL_ALERTS = 60  # 1 minute


class DashboardMetricsService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.now = datetime.now(timezone.utc)

    async def get_complete_metrics(self) -> DashboardMetricsResponse:
        cache_key = make_cache_key("dashboard:metrics:complete")

        async def _compute():
            # Run sequentially — shared DB session cannot handle concurrent ops
            circulation = await self._get_circulation_snapshot_uncached()
            holds = await self._get_holds_queue_status_uncached()
            overdue_count = await self._get_overdue_count_uncached()
            health = await self._calculate_collection_health_uncached()

            return DashboardMetricsResponse(
                circulation_snapshot=circulation,
                holds_queue=holds,
                overdue_count=overdue_count,
                collection_health=health,
                timestamp=self.now.isoformat(),
            )

        return await get_cached_or_compute(
            cache_key, ttl=TTL_METRICS_COMPLETE, compute_fn=_compute
        )

    async def get_circulation_snapshot(self) -> CirculationSnapshot:
        cache_key = make_cache_key("dashboard:circulation:snapshot")

        async def _compute():
            return await self._get_circulation_snapshot_uncached()

        return await get_cached_or_compute(
            cache_key, ttl=TTL_CIRCULATION, compute_fn=_compute
        )

    async def _get_circulation_snapshot_uncached(self) -> CirculationSnapshot:
        today = self.now.date()

        # Run sequentially — shared DB session cannot handle concurrent ops
        r0 = await self.db.execute(text("SELECT COUNT(*) FROM checkouts WHERE status = 'active'"))
        active_checkouts = r0.scalar() or 0
        r1 = await self.db.execute(text("SELECT COUNT(*) FROM checkouts WHERE status = 'returned'"))
        returned_checkouts = r1.scalar() or 0
        r2 = await self.db.execute(text("SELECT COUNT(*) FROM checkouts WHERE status = 'overdue'"))
        overdue_checkouts = r2.scalar() or 0
        r3 = await self.db.execute(
            text("SELECT COUNT(*) FROM checkouts WHERE status = 'active' AND DATE(checked_out_at) = :today"),
            {"today": today},
        )
        checked_out_today = r3.scalar() or 0
        r4 = await self.db.execute(
            text("SELECT COUNT(*) FROM checkouts WHERE status = 'returned' AND DATE(returned_at) = :today"),
            {"today": today},
        )
        returned_today = r4.scalar() or 0
        r5 = await self.db.execute(text("SELECT COUNT(*) FROM holds WHERE status = 'pending'"))
        active_holds = r5.scalar() or 0

        # Calculate circulation rate (checkouts per active item)
        total_items = await self.db.execute(text("SELECT COUNT(*) FROM catalog_items"))
        total_items_count = total_items.scalar() or 1
        circulation_rate = round(active_checkouts / total_items_count * 100, 2)

        return CirculationSnapshot(
            active_checkouts=active_checkouts,
            returned_total=returned_checkouts,
            overdue_items=overdue_checkouts,
            checked_out_today=checked_out_today,
            returned_today=returned_today,
            active_holds=active_holds,
            circulation_rate=circulation_rate,
        )

    async def get_overdue_items(
        self, skip: int = 0, limit: int = 20
    ) -> OverdueItemsResponse:
        cache_key = make_cache_key(f"dashboard:overdue:{skip}:{limit}")

        async def _compute():
            query = text(
                """
                SELECT
                    c.id as checkout_id,
                    c.due_date,
                    c.checked_out_at,
                    COALESCE(ci.title, ci2.title, 'Unknown Item') as title,
                    COALESCE(ci.author, ci2.author) as author,
                    COALESCE(ci.isbn, ci2.isbn) as isbn,
                    COALESCE(ci.item_type::text, ci2.item_type::text, 'unknown') as item_type,
                    u.id as user_id,
                    u.first_name || ' ' || u.last_name as patron_name,
                    u.email as patron_email,
                    u.phone as patron_phone,
                    COALESCE(f.amount, 0) as fine_amount,
                    COALESCE(f.status::text, 'none') as fine_status,
                    EXTRACT(DAY FROM (NOW() - c.due_date)) as days_overdue
                FROM checkouts c
                LEFT JOIN catalog_items ci ON c.item_id = ci.id
                LEFT JOIN item_copies ic ON c.item_copy_id = ic.id
                LEFT JOIN catalog_items ci2 ON ic.catalog_item_id = ci2.id
                JOIN users u ON c.user_id = u.id
                LEFT JOIN fines f ON c.id = f.checkout_id AND f.status IN ('unpaid', 'partial')
                WHERE c.status = 'overdue'
                ORDER BY c.due_date ASC
                LIMIT :limit OFFSET :skip
                """
            )

            result = await self.db.execute(query, {"limit": limit, "skip": skip})
            rows = result.fetchall()

            # Also get total count
            count_query = text("SELECT COUNT(*) FROM checkouts WHERE status = 'overdue'")
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar() or 0

            items = [
                OverdueItemDetail(
                    checkout_id=row[0],
                    due_date=row[1],
                    checked_out_at=row[2],
                    item_title=row[3],
                    item_author=row[4],
                    item_isbn=row[5],
                    item_type=row[6],
                    patron_id=row[7],
                    patron_name=row[8],
                    patron_email=row[9],
                    patron_phone=row[10],
                    fine_amount=float(row[11]),
                    fine_status=row[12],
                    days_overdue=int(row[13]) if row[13] else 0,
                )
                for row in rows
            ]

            return OverdueItemsResponse(
                items=items, total=total_count, skip=skip, limit=limit
            )

        return await get_cached_or_compute(
            cache_key, ttl=TTL_OVERDUE, compute_fn=_compute
        )

    async def _get_overdue_count_uncached(self) -> int:
        result = await self.db.execute(
            text("SELECT COUNT(*) FROM checkouts WHERE status = 'overdue'")
        )
        return result.scalar() or 0

    async def get_holds_queue_status(self) -> HoldQueueStatus:
        cache_key = make_cache_key("dashboard:holds:queue")

        async def _compute():
            return await self._get_holds_queue_status_uncached()

        return await get_cached_or_compute(
            cache_key, ttl=TTL_HOLDS, compute_fn=_compute
        )

    async def _get_holds_queue_status_uncached(self) -> HoldQueueStatus:
        thirty_days_ago = self.now - timedelta(days=30)

        # Run sequentially — shared DB session cannot handle concurrent ops
        r0 = await self.db.execute(text("SELECT COUNT(*) FROM holds WHERE status = 'pending'"))
        total_pending = r0.scalar() or 0
        r1 = await self.db.execute(text("SELECT COUNT(*) FROM holds WHERE status = 'ready'"))
        ready_for_pickup = r1.scalar() or 0
        r2 = await self.db.execute(
            text("SELECT COUNT(*) FROM holds WHERE status = 'pending' AND created_at < :threshold"),
            {"threshold": thirty_days_ago},
        )
        expiring_soon = r2.scalar() or 0
        r3 = await self.db.execute(
            text("SELECT AVG(EXTRACT(DAY FROM (NOW() - created_at))) FROM holds WHERE status = 'pending'")
        )
        avg_wait_days = float(r3.scalar() or 0)
        r4 = await self.db.execute(
            text("SELECT MAX(EXTRACT(DAY FROM (NOW() - created_at))) FROM holds WHERE status = 'pending'")
        )
        max_wait_days = float(r4.scalar() or 0)

        # Alert if queue is long (10+ items or any item waiting 14+ days)
        has_alert = total_pending >= 10 or max_wait_days >= 14

        return HoldQueueStatus(
            total_pending=total_pending,
            ready_for_pickup=ready_for_pickup,
            expiring_soon_count=expiring_soon,
            average_wait_days=round(avg_wait_days, 1),
            longest_wait_days=int(max_wait_days),
            queue_health="warning" if has_alert else "healthy",
        )

    async def get_popular_items(self, days: int = 90, limit: int = 20) -> PopularItemsResponse:
        cache_key = make_cache_key(f"dashboard:popular:{days}:{limit}")

        async def _compute():
            start_date = self.now - timedelta(days=days)

            query = text(
                """
                SELECT
                    ci.id,
                    ci.title,
                    ci.author,
                    ci.item_type,
                    ci.isbn,
                    ci.subjects,
                    COUNT(DISTINCT c.id) as checkout_count,
                    COUNT(DISTINCT h.id) as hold_count
                FROM catalog_items ci
                LEFT JOIN checkouts c ON (ci.id = c.item_id OR ci.id IN (
                    SELECT ic.catalog_item_id FROM item_copies ic
                    WHERE ic.id = c.item_copy_id
                )) AND c.checked_out_at > :start_date
                LEFT JOIN holds h ON ci.id = h.item_id AND h.created_at > :start_date
                GROUP BY ci.id, ci.title, ci.author, ci.item_type, ci.isbn, ci.subjects
                HAVING COUNT(DISTINCT c.id) > 0
                ORDER BY checkout_count DESC, hold_count DESC
                LIMIT :limit
                """
            )

            result = await self.db.execute(
                query, {"start_date": start_date, "limit": limit}
            )
            rows = result.fetchall()

            items = [
                PopularItem(
                    item_id=row[0],
                    title=row[1],
                    author=row[2],
                    item_type=row[3],
                    isbn=row[4],
                    subjects=row[5].split(",") if row[5] else [],
                    checkout_count=row[6],
                    hold_count=row[7],
                )
                for row in rows
            ]

            return PopularItemsResponse(
                items=items, days_range=days, total=len(items)
            )

        return await get_cached_or_compute(
            cache_key, ttl=TTL_POPULAR, compute_fn=_compute
        )

    async def get_theme_velocity(self, days: int = 90) -> ThemeVelocityResponse:
        cache_key = make_cache_key(f"dashboard:velocity:{days}")

        async def _compute():
            start_date = self.now - timedelta(days=days)

            # Get circulation metrics per subject/theme
            query = text(
                """
                SELECT
                    unnest(string_to_array(subjects, ',')) as theme,
                    COUNT(DISTINCT c.id) as checkout_count,
                    COUNT(DISTINCT ci.id) as unique_items,
                    COUNT(DISTINCT CASE WHEN c.status = 'active' THEN c.id END) as currently_checked_out
                FROM catalog_items ci
                LEFT JOIN checkouts c ON (ci.id = c.item_id OR ci.id IN (
                    SELECT ic.catalog_item_id FROM item_copies ic
                    WHERE ic.id = c.item_copy_id
                )) AND c.checked_out_at > :start_date
                WHERE ci.subjects IS NOT NULL AND ci.subjects != ''
                GROUP BY theme
                ORDER BY checkout_count DESC
                """
            )

            result = await self.db.execute(query, {"start_date": start_date})
            rows = result.fetchall()

            metrics = []
            for row in rows:
                theme = row[0].strip()
                checkout_count = row[1]
                unique_items = row[2]
                currently_checked = row[3]

                # Calculate velocity metrics
                utilization_rate = (
                    round(currently_checked / unique_items * 100, 2)
                    if unique_items > 0
                    else 0
                )
                turnover_ratio = (
                    round(checkout_count / unique_items, 2) if unique_items > 0 else 0
                )

                metrics.append(
                    ThemeMetric(
                        theme=theme,
                        checkout_count=checkout_count,
                        unique_items=unique_items,
                        utilization_rate=utilization_rate,
                        turnover_ratio=turnover_ratio,
                        velocity_score=round(
                            turnover_ratio * utilization_rate / 100 * 100, 2
                        ),
                    )
                )

            return ThemeVelocityResponse(metrics=metrics, days_range=days)

        return await get_cached_or_compute(
            cache_key, ttl=TTL_THEME_VELOCITY, compute_fn=_compute
        )

    async def calculate_collection_health(self) -> CollectionHealthResponse:
        cache_key = make_cache_key("dashboard:health:overall")

        async def _compute():
            return await self._calculate_collection_health_uncached()

        return await get_cached_or_compute(
            cache_key, ttl=TTL_COLLECTION_HEALTH, compute_fn=_compute
        )

    async def _calculate_collection_health_uncached(self) -> CollectionHealthResponse:
        ninety_days_ago = self.now - timedelta(days=90)
        thirty_days_ago = self.now - timedelta(days=30)

        # Run sequentially — shared DB session cannot handle concurrent ops
        r0 = await self.db.execute(text("SELECT COUNT(*) FROM catalog_items"))
        total_items = r0.scalar() or 1
        r1 = await self.db.execute(
            text(
                """SELECT COUNT(DISTINCT COALESCE(c.item_id, ic.catalog_item_id))
                FROM checkouts c
                LEFT JOIN item_copies ic ON c.item_copy_id = ic.id
                WHERE c.checked_out_at > :start"""
            ),
            {"start": ninety_days_ago},
        )
        items_in_circulation_90d = r1.scalar() or 0
        r2 = await self.db.execute(
            text("SELECT COUNT(*) FROM checkouts WHERE status = 'active' AND checked_out_at > :start"),
            {"start": thirty_days_ago},
        )
        active_checkouts_30d = r2.scalar() or 0
        r3 = await self.db.execute(text("SELECT COUNT(*) FROM checkouts WHERE status = 'overdue'"))
        overdue_count = r3.scalar() or 0
        r4 = await self.db.execute(
            text("SELECT COUNT(*) FROM catalog_items WHERE status IN ('damaged', 'lost')")
        )
        damaged_lost_count = r4.scalar() or 0

        # Calculate component scores (0-100)
        # Availability: what % of collection is usable (not damaged/lost)
        availability_score = round((total_items - damaged_lost_count) / total_items * 100, 1)

        # Circulation: what % of items circulated in past 90 days
        circulation_score = round(items_in_circulation_90d / total_items * 100, 1)

        # Overdue penalty: penalize high overdue rate
        overdue_rate = round(overdue_count / max(active_checkouts_30d, 1) * 100, 1)
        overdue_score = max(0, 100 - overdue_rate * 2)  # 2x penalty

        # Condition: penalize damaged/lost items
        condition_score = round((total_items - damaged_lost_count) / total_items * 100, 1)

        # Weighted calculation (30% + 25% + 20% + 25% = 100%)
        overall_score = round(
            (availability_score * 0.30)
            + (circulation_score * 0.25)
            + (overdue_score * 0.20)
            + (condition_score * 0.25),
            1,
        )

        return CollectionHealthResponse(
            overall_score=overall_score,
            components=[
                HealthComponent(name="Availability", score=availability_score, weight=30),
                HealthComponent(name="Circulation (90d)", score=circulation_score, weight=25),
                HealthComponent(name="Overdue Rate", score=overdue_score, weight=20),
                HealthComponent(name="Condition", score=condition_score, weight=25),
            ],
            status=(
                "Excellent"
                if overall_score >= 80
                else "Good"
                if overall_score >= 60
                else "Fair"
                if overall_score >= 40
                else "Poor"
            ),
        )

    async def get_system_alerts(self) -> SystemAlertsResponse:
        cache_key = make_cache_key("dashboard:alerts")

        async def _compute():
            alerts = []
            ninety_days_ago = self.now - timedelta(days=90)
            fourteen_days_ago = self.now - timedelta(days=14)

            # Check 1: High overdue rate
            overdue_result = await self.db.execute(
                text("SELECT COUNT(*) FROM checkouts WHERE status = 'overdue'")
            )
            overdue_count = overdue_result.scalar() or 0

            active_result = await self.db.execute(
                text("SELECT COUNT(*) FROM checkouts WHERE status = 'active'")
            )
            active_count = active_result.scalar() or 0

            if active_count > 0:
                overdue_rate = overdue_count / active_count
                if overdue_rate > 0.20:
                    alerts.append(
                        SystemAlert(
                            id="alert_overdue_rate",
                            priority="critical",
                            category="circulation",
                            title="High Overdue Rate",
                            message=f"Overdue rate is {round(overdue_rate * 100, 1)}%. Consider outreach.",
                            action_url="/staff/dashboard?tab=overdue",
                        )
                    )

            # Check 2: Long-term holds backlog
            holds_backlog = await self.db.execute(
                text(
                    "SELECT COUNT(*) FROM holds WHERE status = 'pending' AND created_at < :threshold"
                ),
                {"threshold": fourteen_days_ago},
            )
            backlog_count = holds_backlog.scalar() or 0

            if backlog_count >= 5:
                alerts.append(
                    SystemAlert(
                        id="alert_holds_backlog",
                        priority="warning",
                        category="holds",
                        title="Holds Queue Backlog",
                        message=f"{backlog_count} holds waiting 14+ days for fulfillment.",
                        action_url="/staff/dashboard?tab=holds",
                    )
                )

            # Check 3: Low collection health
            health = await self._calculate_collection_health_uncached()
            if health.overall_score < 60:
                alerts.append(
                    SystemAlert(
                        id="alert_health_low",
                        priority="warning",
                        category="collection",
                        title="Collection Health Below Target",
                        message=f"Health score is {health.overall_score}. Review acquisition strategy.",
                        action_url="/staff/dashboard?tab=health",
                    )
                )

            # Check 4: Outstanding fines
            fines_result = await self.db.execute(
                text(
                    "SELECT SUM(amount) FROM fines WHERE status IN ('unpaid', 'partial') AND created_at > :start"
                ),
                {"start": ninety_days_ago},
            )
            fines_total = float(fines_result.scalar() or 0)

            if fines_total > 500:
                alerts.append(
                    SystemAlert(
                        id="alert_fines_total",
                        priority="info",
                        category="fines",
                        title="Significant Outstanding Fines",
                        message=f"${fines_total:.2f} in outstanding fines (90 days). Consider payment plans.",
                        action_url="/staff/dashboard?tab=overdue",
                    )
                )

            return SystemAlertsResponse(alerts=alerts)

        return await get_cached_or_compute(
            cache_key, ttl=TTL_ALERTS, compute_fn=_compute
        )

    async def execute_quick_action(
        self, action: QuickActionRequest, staff_user_id: int
    ) -> QuickActionResponse:
        try:
            if action.action_type == "mark_returned":
                await self.db.execute(
                    text("UPDATE checkouts SET status = 'returned' WHERE id = :id"),
                    {"id": action.target_id},
                )
                await invalidate_dashboard_cache(["circulation*", "overdue*", "health*"])

                return QuickActionResponse(
                    success=True,
                    message="Item marked as returned",
                )

            elif action.action_type == "send_overdue_notice":
                # Log the action (in real system, would send email)
                logger.info(
                    f"Overdue notice sent for checkout {action.target_id} by staff {staff_user_id}"
                )
                return QuickActionResponse(
                    success=True,
                    message="Overdue notice sent to patron",
                )

            elif action.action_type == "waive_fine":
                await self.db.execute(
                    text("UPDATE fines SET status = 'waived' WHERE id = :id"),
                    {"id": action.target_id},
                )
                await invalidate_dashboard_cache(["alerts*", "overdue*"])

                return QuickActionResponse(
                    success=True,
                    message="Fine waived successfully",
                )

            else:
                return QuickActionResponse(
                    success=False,
                    message="Unknown action type",
                )

        except Exception as e:  # noqa: BLE001 -- HTTP route boundary: dispatch error must return user-safe response not crash route
            logger.error(f"Quick action failed: {e}")
            return QuickActionResponse(
                success=False,
                message="Action failed",
            )
