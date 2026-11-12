# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.event_review import EventReview, ReviewModerationStatus
from ..models.monitoring import (
    MonitoringAlertSeverity, AlertThreshold, ModerationAlert, PrivacyAlert,
    PrivacyChangeType, SystemHealth
)
from ..models.reading_list import ReadingList
from ..models.user import User
from ..models.social_sharing import ShareEvent

logger = get_logger(__name__)

# Default thresholds (can be overridden via database)
DEFAULT_THRESHOLDS = {
    "privacy_changes_per_hour": {"warning": 5, "critical": 10},
    "bulk_public_changes": {"warning": 20, "critical": 50},
    "moderation_queue_size": {"warning": 10, "critical": 20},
    "moderation_queue_age_hours": {"warning": 24, "critical": 48},
}


class PrivacyMonitoringService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_privacy_alerts(self) -> List[PrivacyAlert]:
        alerts = []

        # Check for rapid privacy changes
        rapid_changes = await self._detect_rapid_changes()
        alerts.extend(rapid_changes)

        # Check for bulk public content changes
        bulk_changes = await self._detect_bulk_public_changes()
        alerts.extend(bulk_changes)

        # Check for all-public account changes
        all_public = await self._detect_all_public_changes()
        alerts.extend(all_public)

        return alerts

    async def _detect_rapid_changes(self) -> List[PrivacyAlert]:
        alerts = []

        # Get threshold
        threshold = await self._get_threshold("privacy_changes_per_hour")
        if not threshold:
            return alerts

        # Look at social shares in last hour
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

        # Query for users with many shares
        query = select(
            ShareEvent.user_id,
            func.count(ShareEvent.id).label("share_count")
        ).where(
            ShareEvent.shared_at >= one_hour_ago
        ).group_by(ShareEvent.user_id)

        result = await self.db.execute(query)
        user_share_counts = result.fetchall()

        for user_id, share_count in user_share_counts:
            if share_count >= threshold.critical_level:
                severity = MonitoringAlertSeverity.HIGH
            elif share_count >= threshold.warning_level:
                severity = MonitoringAlertSeverity.MEDIUM
            else:
                continue

            # Create alert
            alert = PrivacyAlert(
                user_id=user_id,
                alert_type=PrivacyChangeType.CONTENT_VISIBILITY,
                severity=severity,
                change_count=share_count,
                time_window_minutes=60,
                resource_type="social_shares",
                description=f"User made {share_count} privacy/sharing changes in 1 hour",
                is_anomalous=True
            )
            self.db.add(alert)
            alerts.append(alert)

        if alerts:
            await self.db.commit()

        return alerts

    async def _detect_bulk_public_changes(self) -> List[PrivacyAlert]:
        alerts = []

        threshold = await self._get_threshold("bulk_public_changes")
        if not threshold:
            return alerts

        # Check reading lists made public recently
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

        query = select(
            ReadingList.user_id,
            func.count(ReadingList.id).label("public_count")
        ).where(
            and_(
                ReadingList.is_public == True,
                ReadingList.updated_at >= one_hour_ago
            )
        ).group_by(ReadingList.user_id)

        result = await self.db.execute(query)
        user_public_counts = result.fetchall()

        for user_id, public_count in user_public_counts:
            if public_count >= threshold.critical_level:
                severity = MonitoringAlertSeverity.HIGH
            elif public_count >= threshold.warning_level:
                severity = MonitoringAlertSeverity.MEDIUM
            else:
                continue

            alert = PrivacyAlert(
                user_id=user_id,
                alert_type=PrivacyChangeType.BULK_CHANGE,
                severity=severity,
                change_count=public_count,
                time_window_minutes=60,
                resource_type="reading_lists",
                description=f"User made {public_count} reading lists public in 1 hour",
                is_anomalous=True
            )
            self.db.add(alert)
            alerts.append(alert)

        if alerts:
            await self.db.commit()

        return alerts

    async def _detect_all_public_changes(self) -> List[PrivacyAlert]:
        alerts = []

        # Get users who recently made many lists public

        query = select(
            ReadingList.user_id,
            func.count(ReadingList.id).label("total_lists"),
            func.sum(func.cast(ReadingList.is_public, "INTEGER")).label("public_lists")
        ).group_by(ReadingList.user_id)

        result = await self.db.execute(query)
        user_lists = result.fetchall()

        for user_id, total_lists, public_lists in user_lists:
            if total_lists is None or public_lists is None:
                continue

            public_percentage = (public_lists / total_lists * 100) if total_lists > 0 else 0

            # Alert if suddenly made 80%+ of content public
            if public_percentage >= 80 and total_lists >= 3:
                alert = PrivacyAlert(
                    user_id=user_id,
                    alert_type=PrivacyChangeType.BULK_CHANGE,
                    severity=MonitoringAlertSeverity.HIGH,
                    change_count=public_lists,
                    resource_type="reading_lists",
                    description=f"User has made {public_lists} of {total_lists} reading lists public ({public_percentage:.0f}%)",
                    is_anomalous=True
                )
                self.db.add(alert)
                alerts.append(alert)

        if alerts:
            await self.db.commit()

        return alerts

    async def _get_threshold(self, threshold_name: str) -> Optional[AlertThreshold]:
        result = await self.db.execute(
            select(AlertThreshold).where(
                and_(
                    AlertThreshold.name == threshold_name,
                    AlertThreshold.enabled == True
                )
            )
        )
        return result.scalar_one_or_none()


class ModerationMonitoringService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_moderation_alerts(self) -> List[ModerationAlert]:
        alerts = []

        # Check queue size
        queue_alerts = await self._check_queue_size()
        alerts.extend(queue_alerts)

        # Check for overdue items
        overdue_alerts = await self._check_overdue_items()
        alerts.extend(overdue_alerts)

        return alerts

    async def _check_queue_size(self) -> List[ModerationAlert]:
        alerts = []

        # Count pending reviews
        pending_result = await self.db.execute(
            select(func.count(EventReview.id)).where(
                EventReview.moderation_status == ReviewModerationStatus.PENDING
            )
        )
        pending_count = pending_result.scalar() or 0

        threshold = await self._get_threshold("moderation_queue_size")
        if not threshold:
            return alerts

        if pending_count >= threshold.critical_level:
            severity = MonitoringAlertSeverity.CRITICAL
        elif pending_count >= threshold.warning_level:
            severity = MonitoringAlertSeverity.MEDIUM
        else:
            return alerts

        # Get oldest pending review age
        oldest_result = await self.db.execute(
            select(func.min(EventReview.created_at)).where(
                EventReview.moderation_status == ReviewModerationStatus.PENDING
            )
        )
        oldest_date = oldest_result.scalar()
        oldest_age_hours = 0
        if oldest_date:
            oldest_age_hours = int(
                (datetime.now(timezone.utc) - oldest_date).total_seconds() / 3600
            )

        alert = ModerationAlert(
            alert_type="queue_backlog",
            severity=severity,
            pending_count=pending_count,
            oldest_item_age_hours=oldest_age_hours,
            threshold_exceeded="pending_count",
            threshold_value=threshold.warning_level,
            actual_value=pending_count,
            description=f"{pending_count} reviews pending (oldest: {oldest_age_hours}h)",
        )
        self.db.add(alert)
        alerts.append(alert)

        await self.db.commit()
        return alerts

    async def _check_overdue_items(self) -> List[ModerationAlert]:
        alerts = []

        # Find reviews older than 24 hours
        age_threshold = datetime.now(timezone.utc) - timedelta(hours=24)

        overdue_result = await self.db.execute(
            select(func.count(EventReview.id)).where(
                and_(
                    EventReview.moderation_status == ReviewModerationStatus.PENDING,
                    EventReview.created_at < age_threshold
                )
            )
        )
        overdue_count = overdue_result.scalar() or 0

        if overdue_count > 0:
            alert = ModerationAlert(
                alert_type="overdue_item",
                severity=MonitoringAlertSeverity.HIGH,
                overdue_count=overdue_count,
                oldest_item_age_hours=24,
                threshold_exceeded="age",
                threshold_value=24,
                actual_value=overdue_count,
                description=f"{overdue_count} reviews pending for over 24 hours",
            )
            self.db.add(alert)
            alerts.append(alert)

            await self.db.commit()

        return alerts

    async def get_moderation_queue_status(self) -> Dict:
        pending_result = await self.db.execute(
            select(func.count(EventReview.id)).where(
                EventReview.moderation_status == ReviewModerationStatus.PENDING
            )
        )
        pending_count = pending_result.scalar() or 0

        approved_result = await self.db.execute(
            select(func.count(EventReview.id)).where(
                EventReview.moderation_status == ReviewModerationStatus.APPROVED
            )
        )
        approved_count = approved_result.scalar() or 0

        rejected_result = await self.db.execute(
            select(func.count(EventReview.id)).where(
                EventReview.moderation_status == ReviewModerationStatus.REJECTED
            )
        )
        rejected_count = rejected_result.scalar() or 0

        # Get average turnaround time
        completed_reviews = await self.db.execute(
            select(EventReview.created_at, EventReview.updated_at).where(
                EventReview.moderation_status.in_([ReviewModerationStatus.APPROVED, ReviewModerationStatus.REJECTED])
            ).order_by(EventReview.updated_at.desc()).limit(100)
        )

        turnaround_times = []
        for created, updated in completed_reviews.fetchall():
            if created and updated:
                turnaround = (updated - created).total_seconds() / 3600
                turnaround_times.append(turnaround)

        avg_turnaround = sum(turnaround_times) / len(turnaround_times) if turnaround_times else 0

        # Get oldest pending
        oldest_result = await self.db.execute(
            select(func.min(EventReview.created_at)).where(
                EventReview.moderation_status == ReviewModerationStatus.PENDING
            )
        )
        oldest_date = oldest_result.scalar()
        oldest_age_hours = 0
        if oldest_date:
            oldest_age_hours = int(
                (datetime.now(timezone.utc) - oldest_date).total_seconds() / 3600
            )

        return {
            "pending": pending_count,
            "approved": approved_count,
            "rejected": rejected_count,
            "total_processed": approved_count + rejected_count,
            "average_turnaround_hours": round(avg_turnaround, 2),
            "oldest_pending_hours": oldest_age_hours,
        }

    async def _get_threshold(self, threshold_name: str) -> Optional[AlertThreshold]:
        result = await self.db.execute(
            select(AlertThreshold).where(
                and_(
                    AlertThreshold.name == threshold_name,
                    AlertThreshold.enabled == True
                )
            )
        )
        return result.scalar_one_or_none()


class SystemHealthService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_system_health(self) -> SystemHealth:
        # Count share events in last hour
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        share_hour_result = await self.db.execute(
            select(func.count(ShareEvent.id)).where(
                ShareEvent.shared_at >= one_hour_ago
            )
        )
        share_events_last_hour = share_hour_result.scalar() or 0

        # Count share events in last 24 hours
        one_day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        share_day_result = await self.db.execute(
            select(func.count(ShareEvent.id)).where(
                ShareEvent.shared_at >= one_day_ago
            )
        )
        share_events_last_24h = share_day_result.scalar() or 0

        # --- DB connection pool counts (SQLAlchemy NullPool has no pool attr) ---
        db_connection_active: Optional[int] = None
        db_connection_idle: Optional[int] = None
        try:
            from ..core.database import engine
            pool = engine.pool
            # QueuePool / AsyncAdaptedQueuePool expose these attributes.
            # NullPool and StaticPool do not, so guard with hasattr.
            if hasattr(pool, "checkedout"):
                db_connection_active = pool.checkedout()
            if hasattr(pool, "checkedin"):
                db_connection_idle = pool.checkedin()
        except Exception:  # noqa: BLE001 -- best-effort diagnostic; must never break the health endpoint
            pass  # Pool stats unavailable; leave as None

        # --- Slow query count and average query time from the perf monitor ---
        db_slow_queries: Optional[int] = None
        db_query_avg_time_ms: Optional[float] = None
        api_response_p50_ms: Optional[float] = None
        api_response_p95_ms: Optional[float] = None
        api_response_p99_ms: Optional[float] = None
        error_count_last_hour: Optional[int] = None
        error_count_last_24h: Optional[int] = None
        error_rate_percent: Optional[float] = None
        try:
            from ..core.performance_monitoring import get_monitor
            monitor = get_monitor()

            slow_qs = monitor.get_slow_queries(hours=24)
            db_slow_queries = len(slow_qs)

            # Average query duration across all recorded slow queries (best
            # proxy without a separate all-query latency store).
            if slow_qs:
                db_query_avg_time_ms = round(
                    sum(q["duration_ms"] for q in slow_qs) / len(slow_qs), 2
                )

            endpoint_metrics = monitor.get_endpoint_metrics()
            if endpoint_metrics:
                all_durations: list[float] = []
                total_errors = 0
                total_requests = 0
                for em in endpoint_metrics.values():
                    count = em.get("count", 0)
                    avg = em.get("avg_duration_ms", 0.0)
                    if count:
                        all_durations.extend([avg] * min(count, 100))
                    total_errors += em.get("error_count", 0)
                    total_requests += count

                if all_durations:
                    sorted_d = sorted(all_durations)
                    n = len(sorted_d)
                    api_response_p50_ms = round(sorted_d[int(n * 0.50)], 2)
                    api_response_p95_ms = round(sorted_d[int(n * 0.95)], 2)
                    api_response_p99_ms = round(sorted_d[min(int(n * 0.99), n - 1)], 2)

                error_count_last_24h = total_errors
                # error_count_last_hour not available without per-request
                # timestamps in the monitor — leave as None rather than 0.
                error_rate_percent = (
                    round(total_errors / total_requests * 100, 2)
                    if total_requests
                    else 0.0
                )
        except Exception:  # noqa: BLE001 -- best-effort diagnostic; must never break the health endpoint
            pass  # Perf monitor unavailable; leave fields as None

        # --- Cache hit rate from the cache metrics singleton ---
        cache_hit_rate_percent: Optional[float] = None
        try:
            from ..core.cache import get_cache_metrics
            cache_snap = get_cache_metrics()
            per_prefix = cache_snap.get("per_prefix", {})
            if per_prefix:
                total_hits = sum(v.get("hits", 0) for v in per_prefix.values())
                total_misses = sum(v.get("misses", 0) for v in per_prefix.values())
                total_ops = total_hits + total_misses
                if total_ops:
                    cache_hit_rate_percent = round(total_hits / total_ops * 100, 2)
        except Exception:  # noqa: BLE001 -- best-effort diagnostic; must never break the health endpoint
            pass  # Cache metrics unavailable; leave as None

        # Derive overall status from what we could measure.
        status = "healthy"
        status_reason = "All systems operational"
        if db_connection_active is None and api_response_p50_ms is None:
            status_reason = "Metrics partially unavailable — system appears operational"

        # Only persist the row if we have at least some real measurements.
        has_real_metrics = any(
            v is not None
            for v in (
                db_connection_active, db_slow_queries, api_response_p50_ms,
                cache_hit_rate_percent, error_rate_percent,
            )
        )

        health = SystemHealth(
            status=status,
            status_reason=status_reason,
            share_events_last_hour=share_events_last_hour,
            share_events_last_24h=share_events_last_24h,
            db_connection_active=db_connection_active if db_connection_active is not None else 0,
            db_connection_idle=db_connection_idle if db_connection_idle is not None else 0,
            db_slow_queries=db_slow_queries if db_slow_queries is not None else 0,
            db_query_avg_time_ms=db_query_avg_time_ms if db_query_avg_time_ms is not None else 0.0,
            error_count_last_hour=error_count_last_hour if error_count_last_hour is not None else 0,
            error_count_last_24h=error_count_last_24h if error_count_last_24h is not None else 0,
            error_rate_percent=error_rate_percent if error_rate_percent is not None else 0.0,
            api_response_p50_ms=api_response_p50_ms if api_response_p50_ms is not None else 0.0,
            api_response_p95_ms=api_response_p95_ms if api_response_p95_ms is not None else 0.0,
            api_response_p99_ms=api_response_p99_ms if api_response_p99_ms is not None else 0.0,
            cache_hit_rate_percent=cache_hit_rate_percent if cache_hit_rate_percent is not None else 0.0,
        )

        if has_real_metrics:
            self.db.add(health)
            await self.db.commit()
            await self.db.refresh(health)

        return health

    async def get_recent_health_history(self, hours: int = 24) -> List[SystemHealth]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        result = await self.db.execute(
            select(SystemHealth).where(
                SystemHealth.created_at >= cutoff_time
            ).order_by(desc(SystemHealth.created_at)).limit(100)
        )

        return result.scalars().all()
