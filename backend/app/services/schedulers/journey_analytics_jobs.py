# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timezone, timedelta

from sqlalchemy import and_, func, select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ...models.journey_instrumentation import (
    JourneyEvent,
    JourneyMetrics,
    JourneyDropOff,
    JOURNEY_TYPES,
)

logger = get_logger(__name__)

# Sessions with no new event in this window are considered abandoned
DROPOFF_TIMEOUT_MINUTES = 30

# Journey stage definitions (must match journey_analytics_service.py)
JOURNEY_STAGES = {
    "search_to_hold": [
        "search_initiated", "filters_applied", "results_displayed",
        "item_selected", "hold_initiated", "hold_placed",
    ],
    "register": [
        "registration_started", "personal_info_entered", "address_entered",
        "verification_sent", "verification_confirmed", "registration_completed",
    ],
    "renewal": [
        "renewal_initiated", "items_displayed", "items_selected",
        "renewal_submitted", "renewal_confirmed",
    ],
    "account_self_service": [
        "account_accessed", "section_selected", "action_initiated",
        "action_completed",
    ],
    "staff_checkin": [
        "checkin_started", "patron_identified", "items_scanned",
        "payment_processed", "receipt_printed", "checkin_completed",
    ],
}


async def detect_journey_dropoffs():
    async with get_async_session() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=DROPOFF_TIMEOUT_MINUTES)

        for journey_type, stages in JOURNEY_STAGES.items():
            final_stage = stages[-1]

            # Find sessions that have events before cutoff but never reached final stage
            # Subquery: sessions that completed
            completed = (
                select(JourneyEvent.session_id)
                .where(
                    and_(
                        JourneyEvent.journey_type == journey_type,
                        JourneyEvent.stage_name == final_stage,
                    )
                )
            )

            # Subquery: sessions already recorded as dropoffs
            already_recorded = (
                select(JourneyDropOff.session_id)
                .where(JourneyDropOff.journey_type == journey_type)
            )

            # Find abandoned sessions
            abandoned = await db.execute(
                select(
                    JourneyEvent.session_id,
                    JourneyEvent.user_id,
                    func.max(JourneyEvent.stage_name).label("last_stage"),
                    func.max(JourneyEvent.event_sequence).label("max_seq"),
                    func.max(JourneyEvent.time_since_journey_start_ms).label("total_time"),
                    func.max(JourneyEvent.device_type).label("device_type"),
                    func.max(JourneyEvent.user_type).label("user_type"),
                    func.bool_or(JourneyEvent.accessibility_mode).label("accessibility"),
                )
                .where(
                    and_(
                        JourneyEvent.journey_type == journey_type,
                        JourneyEvent.event_timestamp < cutoff,
                        JourneyEvent.session_id.notin_(completed),
                        JourneyEvent.session_id.notin_(already_recorded),
                    )
                )
                .group_by(JourneyEvent.session_id, JourneyEvent.user_id)
            )

            rows = abandoned.all()
            for row in rows:
                # Find the last completed stage and next expected stage
                last_stage = row.last_stage
                last_idx = stages.index(last_stage) if last_stage in stages else 0
                next_stage = stages[last_idx + 1] if last_idx + 1 < len(stages) else stages[-1]

                dropoff = JourneyDropOff(
                    journey_type=journey_type,
                    session_id=row.session_id,
                    user_id=row.user_id,
                    last_completed_stage=last_stage,
                    expected_next_stage=next_stage,
                    stages_completed=row.max_seq,
                    total_stages=len(stages),
                    time_in_journey_ms=row.total_time or 0,
                    time_at_last_stage_ms=0,
                    device_type=row.device_type,
                    user_type=row.user_type,
                    accessibility_mode=row.accessibility or False,
                    reason="timeout",
                )
                db.add(dropoff)

            if rows:
                logger.info(f"Detected {len(rows)} dropoffs for {journey_type}")

        logger.info("Journey dropoff detection complete")


async def aggregate_journey_metrics():
    async with get_async_session() as db:
        now = datetime.now(timezone.utc)
        # Aggregate the previous hour
        hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        hour_end = hour_start + timedelta(hours=1)

        for journey_type, stages in JOURNEY_STAGES.items():
            for stage in stages:
                # Count events and sessions for this stage in this hour
                result = await db.execute(
                    select(
                        func.count(JourneyEvent.id).label("event_count"),
                        func.count(distinct(JourneyEvent.session_id)).label("unique_sessions"),
                        func.count(distinct(JourneyEvent.user_id)).label("unique_users"),
                        func.avg(JourneyEvent.time_since_journey_start_ms).label("avg_time"),
                        func.count().filter(JourneyEvent.error_code.isnot(None)).label("error_count"),
                    ).where(
                        and_(
                            JourneyEvent.journey_type == journey_type,
                            JourneyEvent.stage_name == stage,
                            JourneyEvent.event_timestamp >= hour_start,
                            JourneyEvent.event_timestamp < hour_end,
                        )
                    )
                )
                row = result.one()

                if row.event_count == 0:
                    continue

                error_rate = (row.error_count / row.event_count * 100) if row.event_count > 0 else 0

                metric = JourneyMetrics(
                    metric_time=hour_start,
                    metric_date=hour_start.strftime("%Y-%m-%d"),
                    metric_hour=hour_start.hour,
                    journey_type=journey_type,
                    segment_key="overall",
                    stage_name=stage,
                    stage_event_count=row.event_count,
                    unique_sessions=row.unique_sessions,
                    unique_users=row.unique_users or 0,
                    avg_time_to_stage_ms=float(row.avg_time) if row.avg_time else 0,
                    error_event_count=row.error_count,
                    error_rate=error_rate,
                )
                db.add(metric)

        logger.info(f"Journey metrics aggregated for hour {hour_start.isoformat()}")
