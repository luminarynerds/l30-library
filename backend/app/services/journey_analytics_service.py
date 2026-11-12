# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from ..models.journey_instrumentation import (
    JourneyEvent,
    JourneyMetrics,
    JourneyDropOff,
    JourneyAlert,
    JOURNEY_TYPES,
)
from ..schemas.journey_analytics import (
    FunnelStage,
    JourneyFunnelResponse,
    SegmentMetrics,
    DropOffPoint,
    JourneyDropOffResponse,
    RegressionAlert,
)

logger = get_logger(__name__)


# Journey stages configuration
JOURNEY_STAGES = {
    "search_to_hold": [
        "search_initiated",
        "filters_applied",
        "results_displayed",
        "item_selected",
        "hold_initiated",
        "hold_placed",
    ],
    "register": [
        "registration_started",
        "personal_info_entered",
        "address_entered",
        "verification_sent",
        "verification_confirmed",
        "registration_completed",
    ],
    "renewal": [
        "renewal_initiated",
        "items_displayed",
        "items_selected",
        "renewal_submitted",
        "renewal_confirmed",
    ],
    "account_self_service": [
        "account_accessed",
        "section_selected",
        "action_initiated",
        "action_completed",
    ],
    "staff_checkin": [
        "checkin_started",
        "patron_identified",
        "items_scanned",
        "payment_processed",
        "receipt_printed",
        "checkin_completed",
    ],
}


class JourneyAnalyticsService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # FUNNEL ANALYSIS
    # ========================================================================

    async def get_journey_funnel(
        self,
        journey_type: str,
        hours: int = 24,
        device_type: Optional[str] = None,
        user_type: Optional[str] = None,
        accessibility_mode: Optional[bool] = None,
    ) -> JourneyFunnelResponse:

        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stages = JOURNEY_STAGES.get(journey_type, [])

        # Build segment key
        segment_key = self._build_segment_key(device_type, user_type, accessibility_mode)

        # Get all sessions for this journey
        sessions_query = select(func.count(func.distinct(JourneyEvent.session_id))).where(
            and_(
                JourneyEvent.journey_type == journey_type,
                JourneyEvent.event_timestamp >= since,
            )
        )

        if device_type:
            sessions_query = sessions_query.where(JourneyEvent.device_type == device_type)
        if user_type:
            sessions_query = sessions_query.where(JourneyEvent.user_type == user_type)
        if accessibility_mode is not None:
            sessions_query = sessions_query.where(
                JourneyEvent.accessibility_mode == accessibility_mode
            )

        total_sessions = (await self.db.execute(sessions_query)).scalar() or 0

        # Calculate completed sessions (reached final stage)
        final_stage = stages[-1] if stages else None
        completed_query = (
            select(func.count(func.distinct(JourneyEvent.session_id)))
            .where(
                and_(
                    JourneyEvent.journey_type == journey_type,
                    JourneyEvent.stage_name == final_stage,
                    JourneyEvent.event_timestamp >= since,
                )
            )
        )

        if device_type:
            completed_query = completed_query.where(JourneyEvent.device_type == device_type)
        if user_type:
            completed_query = completed_query.where(JourneyEvent.user_type == user_type)
        if accessibility_mode is not None:
            completed_query = completed_query.where(
                JourneyEvent.accessibility_mode == accessibility_mode
            )

        completed_sessions = (await self.db.execute(completed_query)).scalar() or 0

        # Build funnel stages
        funnel_stages = []
        for stage in stages:
            stage_data = await self._get_stage_metrics(
                journey_type, stage, since, device_type, user_type, accessibility_mode
            )
            funnel_stages.append(stage_data)

        # Calculate average completion time
        avg_completion_time = await self._get_avg_completion_time(
            journey_type, since, device_type, user_type, accessibility_mode
        )

        completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0

        return JourneyFunnelResponse(
            journey_type=journey_type,
            segment_key=segment_key if device_type or user_type or accessibility_mode else None,
            total_sessions=total_sessions,
            completed_sessions=completed_sessions,
            overall_completion_rate=completion_rate,
            avg_time_to_completion_ms=int(avg_completion_time or 0),
            stages=funnel_stages,
        )

    async def _get_stage_metrics(
        self,
        journey_type: str,
        stage_name: str,
        since: datetime,
        device_type: Optional[str] = None,
        user_type: Optional[str] = None,
        accessibility_mode: Optional[bool] = None,
    ) -> FunnelStage:

        # Count events at this stage
        event_count_query = select(func.count(JourneyEvent.id)).where(
            and_(
                JourneyEvent.journey_type == journey_type,
                JourneyEvent.stage_name == stage_name,
                JourneyEvent.event_timestamp >= since,
            )
        )

        # Count unique sessions reaching this stage
        sessions_query = select(func.count(func.distinct(JourneyEvent.session_id))).where(
            and_(
                JourneyEvent.journey_type == journey_type,
                JourneyEvent.stage_name == stage_name,
                JourneyEvent.event_timestamp >= since,
            )
        )

        # Error count
        error_query = select(func.count(JourneyEvent.id)).where(
            and_(
                JourneyEvent.journey_type == journey_type,
                JourneyEvent.stage_name == stage_name,
                JourneyEvent.event_timestamp >= since,
                JourneyEvent.error_code.isnot(None),
            )
        )

        # Time metrics
        time_query = select(
            func.avg(JourneyEvent.time_since_journey_start_ms).label("avg_time"),
            func.percentile_cont(0.5).within_group(
                JourneyEvent.time_since_journey_start_ms
            ).label("median_time"),
            func.percentile_cont(0.95).within_group(
                JourneyEvent.time_since_journey_start_ms
            ).label("p95_time"),
        ).where(
            and_(
                JourneyEvent.journey_type == journey_type,
                JourneyEvent.stage_name == stage_name,
                JourneyEvent.event_timestamp >= since,
            )
        )

        # Apply filters
        for query in [event_count_query, sessions_query, error_query, time_query]:
            if device_type:
                query = query.where(JourneyEvent.device_type == device_type)
            if user_type:
                query = query.where(JourneyEvent.user_type == user_type)
            if accessibility_mode is not None:
                query = query.where(JourneyEvent.accessibility_mode == accessibility_mode)

        event_count = (await self.db.execute(event_count_query)).scalar() or 0
        unique_sessions = (await self.db.execute(sessions_query)).scalar() or 0
        error_count = (await self.db.execute(error_query)).scalar() or 0

        time_result = (await self.db.execute(time_query)).first()
        avg_time = int(time_result[0]) if time_result and time_result[0] else 0
        median_time = int(time_result[1]) if time_result and time_result[1] else 0
        p95_time = int(time_result[2]) if time_result and time_result[2] else 0

        # Get total sessions for completion rate
        total_sessions = (
            (await self.db.execute(
                select(func.count(func.distinct(JourneyEvent.session_id)))
                .where(and_(
                    JourneyEvent.journey_type == journey_type,
                    JourneyEvent.event_timestamp >= since,
                ))
            )).scalar() or 1
        )

        completion_rate = (unique_sessions / total_sessions * 100) if total_sessions > 0 else 0
        error_rate = (error_count / event_count * 100) if event_count > 0 else 0

        return FunnelStage(
            stage_name=stage_name,
            event_count=event_count,
            unique_sessions=unique_sessions,
            completion_rate=completion_rate,
            avg_time_to_stage_ms=avg_time,
            median_time_to_stage_ms=median_time,
            p95_time_to_stage_ms=p95_time,
            error_count=error_count,
            error_rate=error_rate,
        )

    # ========================================================================
    # DROP-OFF ANALYSIS
    # ========================================================================

    async def get_journey_dropoffs(
        self,
        journey_type: str,
        hours: int = 24,
    ) -> JourneyDropOffResponse:

        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stages = JOURNEY_STAGES.get(journey_type, [])

        # Get all drop-offs
        query = select(JourneyDropOff).where(
            and_(
                JourneyDropOff.journey_type == journey_type,
                JourneyDropOff.created_at >= since,
            )
        )

        result = await self.db.execute(query)
        dropoffs = result.scalars().all()

        # Get total abandoned sessions (didn't reach final stage)
        final_stage = stages[-1] if stages else None
        not_completed = select(func.count(func.distinct(JourneyEvent.session_id))).where(
            and_(
                JourneyEvent.journey_type == journey_type,
                JourneyEvent.event_timestamp >= since,
            )
        )
        total_sessions = (await self.db.execute(not_completed)).scalar() or 1

        completed = select(func.count(func.distinct(JourneyEvent.session_id))).where(
            and_(
                JourneyEvent.journey_type == journey_type,
                JourneyEvent.stage_name == final_stage,
                JourneyEvent.event_timestamp >= since,
            )
        )
        completed_sessions = (await self.db.execute(completed)).scalar() or 0
        total_abandoned = total_sessions - completed_sessions

        abandonment_rate = (total_abandoned / total_sessions * 100) if total_sessions > 0 else 0

        # Group by stage
        stage_dropoffs = {}
        for dropoff in dropoffs:
            stage = dropoff.last_completed_stage
            if stage not in stage_dropoffs:
                stage_dropoffs[stage] = []
            stage_dropoffs[stage].append(dropoff)

        # Build drop-off points
        dropoff_points = []
        most_problematic = None
        max_dropoff_count = 0

        for stage in stages:
            stage_drops = stage_dropoffs.get(stage, [])
            dropoff_count = len(stage_drops)

            if dropoff_count > max_dropoff_count:
                max_dropoff_count = dropoff_count
                most_problematic = stage

            dropoff_rate = (dropoff_count / total_sessions * 100) if total_sessions > 0 else 0

            # Average time at stage for drops
            avg_time = (
                sum(d.time_at_last_stage_ms for d in stage_drops) / len(stage_drops)
                if stage_drops
                else 0
            )

            # Segment breakdown
            segment_breakdown = {}
            for drop in stage_drops:
                device = drop.device_type or "unknown"
                segment_breakdown[device] = segment_breakdown.get(device, 0) + 1

            # Most common reason
            reasons = [d.reason for d in stage_drops if d.reason]
            primary_reason = max(set(reasons), key=reasons.count) if reasons else None

            if dropoff_count > 0:
                dropoff_points.append(
                    DropOffPoint(
                        stage=stage,
                        dropoff_count=dropoff_count,
                        dropoff_rate=dropoff_rate,
                        time_at_stage_ms=int(avg_time),
                        primary_reason=primary_reason,
                        segment_breakdown=segment_breakdown,
                    )
                )

        return JourneyDropOffResponse(
            journey_type=journey_type,
            total_dropoffs=total_abandoned,
            overall_abandonment_rate=abandonment_rate,
            dropoff_points=dropoff_points,
            most_problematic_stage=most_problematic or (stages[-2] if len(stages) > 1 else stages[0]),
        )

    # ========================================================================
    # SEGMENT METRICS
    # ========================================================================

    async def get_segment_metrics(
        self,
        journey_type: str,
        hours: int = 24,
    ) -> List[SegmentMetrics]:

        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        segments = []

        # Device segments
        device_query = select(
            func.distinct(JourneyEvent.device_type)
        ).where(
            and_(
                JourneyEvent.journey_type == journey_type,
                JourneyEvent.event_timestamp >= since,
                JourneyEvent.device_type.isnot(None),
            )
        )
        devices = (await self.db.execute(device_query)).scalars().all()

        for device in devices or []:
            metrics = await self._compute_segment_metrics(
                journey_type, since, device_type=device
            )
            segments.append(metrics)

        # User type segments
        user_type_query = select(
            func.distinct(JourneyEvent.user_type)
        ).where(
            and_(
                JourneyEvent.journey_type == journey_type,
                JourneyEvent.event_timestamp >= since,
                JourneyEvent.user_type.isnot(None),
            )
        )
        user_types = (await self.db.execute(user_type_query)).scalars().all()

        for user_type in user_types or []:
            metrics = await self._compute_segment_metrics(
                journey_type, since, user_type=user_type
            )
            segments.append(metrics)

        # Accessibility segments
        accessibility_query = select(
            select(JourneyEvent).where(
                and_(
                    JourneyEvent.journey_type == journey_type,
                    JourneyEvent.event_timestamp >= since,
                    JourneyEvent.accessibility_mode == True,
                )
            ).exists()
        )
        has_accessibility = (await self.db.execute(accessibility_query)).scalar() or False

        if has_accessibility:
            metrics = await self._compute_segment_metrics(
                journey_type, since, accessibility_mode=True
            )
            segments.append(metrics)

        return segments

    async def _compute_segment_metrics(
        self,
        journey_type: str,
        since: datetime,
        device_type: Optional[str] = None,
        user_type: Optional[str] = None,
        accessibility_mode: Optional[bool] = None,
    ) -> SegmentMetrics:

        stages = JOURNEY_STAGES.get(journey_type, [])
        final_stage = stages[-1] if stages else None

        # Build base query
        base_filters = [
            JourneyEvent.journey_type == journey_type,
            JourneyEvent.event_timestamp >= since,
        ]

        if device_type:
            base_filters.append(JourneyEvent.device_type == device_type)
        if user_type:
            base_filters.append(JourneyEvent.user_type == user_type)
        if accessibility_mode is not None:
            base_filters.append(JourneyEvent.accessibility_mode == accessibility_mode)

        # Total sessions
        total_sessions = (
            (await self.db.execute(
                select(func.count(func.distinct(JourneyEvent.session_id))).where(
                    and_(*base_filters)
                )
            )).scalar() or 0
        )

        # Completed sessions
        completed_sessions = (
            (await self.db.execute(
                select(func.count(func.distinct(JourneyEvent.session_id))).where(
                    and_(
                        *base_filters,
                        JourneyEvent.stage_name == final_stage,
                    )
                )
            )).scalar() or 0
        )

        # Error count
        error_count = (
            (await self.db.execute(
                select(func.count(JourneyEvent.id)).where(
                    and_(
                        *base_filters,
                        JourneyEvent.error_code.isnot(None),
                    )
                )
            )).scalar() or 0
        )

        # Event count for error rate
        event_count = (
            (await self.db.execute(
                select(func.count(JourneyEvent.id)).where(and_(*base_filters))
            )).scalar() or 1
        )

        # Completion metrics
        completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        error_rate = (error_count / event_count * 100) if event_count > 0 else 0
        abandonment_rate = 100 - completion_rate

        # Avg completion time
        avg_time_result = (
            (await self.db.execute(
                select(func.avg(JourneyEvent.time_since_journey_start_ms)).where(
                    and_(
                        *base_filters,
                        JourneyEvent.stage_name == final_stage,
                    )
                )
            )).scalar() or 0
        )

        segment_name = self._build_segment_name(device_type, user_type, accessibility_mode)
        segment_key = self._build_segment_key(device_type, user_type, accessibility_mode)

        return SegmentMetrics(
            segment_name=segment_name,
            segment_key=segment_key,
            device_type=device_type,
            user_type=user_type,
            accessibility_mode=accessibility_mode,
            total_sessions=total_sessions,
            completed_sessions=completed_sessions,
            completion_rate=completion_rate,
            avg_completion_time_ms=int(avg_time_result or 0),
            error_rate=error_rate,
            abandonment_rate=abandonment_rate,
        )

    # ========================================================================
    # ALERTS & REGRESSIONS
    # ========================================================================

    async def get_active_alerts(
        self,
        journey_type: Optional[str] = None,
    ) -> List[RegressionAlert]:

        query = select(JourneyAlert).where(
            and_(
                JourneyAlert.is_resolved == False,
            )
        )

        if journey_type:
            query = query.where(JourneyAlert.journey_type == journey_type)

        query = query.order_by(desc(JourneyAlert.alert_timestamp))

        result = await self.db.execute(query)
        alerts = result.scalars().all()

        return [
            RegressionAlert(
                alert_id=alert.id,
                journey_type=alert.journey_type,
                alert_type=alert.alert_type,
                severity=alert.severity,
                current_value=alert.current_value,
                baseline_value=alert.baseline_value,
                percent_change=alert.percent_change,
                description=self._build_alert_description(alert),
                segment_affected=alert.segment_key,
                created_at=alert.created_at,
                is_resolved=alert.is_resolved,
            )
            for alert in alerts
        ]

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    async def _get_avg_completion_time(
        self,
        journey_type: str,
        since: datetime,
        device_type: Optional[str] = None,
        user_type: Optional[str] = None,
        accessibility_mode: Optional[bool] = None,
    ) -> Optional[float]:

        stages = JOURNEY_STAGES.get(journey_type, [])
        final_stage = stages[-1] if stages else None

        query = select(func.avg(JourneyEvent.time_since_journey_start_ms)).where(
            and_(
                JourneyEvent.journey_type == journey_type,
                JourneyEvent.stage_name == final_stage,
                JourneyEvent.event_timestamp >= since,
            )
        )

        if device_type:
            query = query.where(JourneyEvent.device_type == device_type)
        if user_type:
            query = query.where(JourneyEvent.user_type == user_type)
        if accessibility_mode is not None:
            query = query.where(JourneyEvent.accessibility_mode == accessibility_mode)

        return (await self.db.execute(query)).scalar()

    def _build_segment_key(
        self,
        device_type: Optional[str],
        user_type: Optional[str],
        accessibility_mode: Optional[bool],
    ) -> str:
        parts = []
        if device_type:
            parts.append(f"device_{device_type}")
        if user_type:
            parts.append(f"user_{user_type}")
        if accessibility_mode is not None:
            parts.append(f"access_{str(accessibility_mode).lower()}")
        return "|".join(parts) if parts else "overall"

    def _build_segment_name(
        self,
        device_type: Optional[str],
        user_type: Optional[str],
        accessibility_mode: Optional[bool],
    ) -> str:
        parts = []
        if device_type:
            parts.append(f"{device_type.capitalize()} Users")
        if user_type:
            parts.append(f"{user_type.capitalize()}")
        if accessibility_mode:
            parts.append("with Accessibility")

        if not parts:
            return "All Users"
        return " ".join(parts)

    def _build_alert_description(self, alert: JourneyAlert) -> str:
        journey_name = JOURNEY_TYPES.get(alert.journey_type, alert.journey_type)

        if alert.alert_type == "completion_rate_drop":
            return (
                f"{journey_name} completion rate dropped {abs(alert.percent_change):.1f}% "
                f"below baseline ({alert.current_value:.1f}% vs {alert.baseline_value:.1f}%)"
            )
        elif alert.alert_type == "error_rate_spike":
            return (
                f"{journey_name} error rate spiked {alert.percent_change:.1f}% "
                f"({alert.current_value:.1f}%)"
            )
        elif alert.alert_type == "abandonment_increase":
            return (
                f"{journey_name} abandonment increased {alert.percent_change:.1f}% "
                f"({alert.current_value:.1f}%)"
            )

        return f"{journey_name}: {alert.alert_type}"
