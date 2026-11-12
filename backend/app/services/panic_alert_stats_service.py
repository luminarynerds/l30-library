# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.panic_alert import PanicAlert, PanicAlertStatus, PanicAlertHistory
from ..core.datetime_utils import utc_now
from ..core.logging import get_logger

logger = get_logger(__name__)


class PanicAlertStatsService:

    @staticmethod
    async def get_statistics(
        session: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        branch_id: Optional[int] = None,
    ) -> dict:
        # Set default date range (last 30 days)
        if not start_date:
            start_date = utc_now() - timedelta(days=30)
        if not end_date:
            end_date = utc_now()

        # Build base query
        base_query = select(PanicAlert).where(
            and_(
                PanicAlert.created_at >= start_date,
                PanicAlert.created_at <= end_date,
            )
        )

        if branch_id:
            base_query = base_query.where(PanicAlert.branch_id == branch_id)

        # Get all alerts in range
        result = await session.execute(base_query)
        alerts = result.scalars().all()

        # Calculate statistics
        total_alerts = len(alerts)
        active_alerts = sum(1 for a in alerts if a.status == PanicAlertStatus.ACTIVE)
        acknowledged_alerts = sum(1 for a in alerts if a.status == PanicAlertStatus.ACKNOWLEDGED)
        resolved_alerts = sum(1 for a in alerts if a.status == PanicAlertStatus.RESOLVED)
        cancelled_alerts = sum(1 for a in alerts if a.status == PanicAlertStatus.CANCELLED)

        # Calculate average response time
        response_times = []
        for alert in alerts:
            if alert.acknowledged_at and alert.created_at:
                response_time = (alert.acknowledged_at - alert.created_at).total_seconds() / 60
                response_times.append(response_time)

        average_response_time = sum(response_times) / len(response_times) if response_times else None

        # Calculate false alert rate
        false_alert_rate = (cancelled_alerts / total_alerts * 100) if total_alerts > 0 else None

        # Get most common situations (extract keywords from notes)
        situation_keywords = {}
        for alert in alerts:
            if alert.situation_notes:
                # Simple keyword extraction (could be enhanced with NLP)
                words = alert.situation_notes.lower().split()
                for word in words:
                    if len(word) > 4:  # Only count words longer than 4 chars
                        situation_keywords[word] = situation_keywords.get(word, 0) + 1

        # Sort and get top 10
        most_common_situations = [
            {"keyword": k, "count": v}
            for k, v in sorted(situation_keywords.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        # Get alerts by branch
        alerts_by_branch = {}
        for alert in alerts:
            branch = alert.branch_id or "unknown"
            alerts_by_branch[branch] = alerts_by_branch.get(branch, 0) + 1

        alerts_by_branch_list = [
            {"branch_id": k, "count": v}
            for k, v in sorted(alerts_by_branch.items(), key=lambda x: x[1], reverse=True)
        ]

        # Get alerts by time of day (hour)
        alerts_by_hour = {}
        for alert in alerts:
            hour = alert.created_at.hour
            alerts_by_hour[hour] = alerts_by_hour.get(hour, 0) + 1

        alerts_by_time_of_day = [
            {"hour": k, "count": v}
            for k, v in sorted(alerts_by_hour.items())
        ]

        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "acknowledged_alerts": acknowledged_alerts,
            "resolved_alerts": resolved_alerts,
            "cancelled_alerts": cancelled_alerts,
            "average_response_time_minutes": average_response_time,
            "false_alert_rate": false_alert_rate,
            "most_common_situations": most_common_situations,
            "alerts_by_branch": alerts_by_branch_list,
            "alerts_by_time_of_day": alerts_by_time_of_day,
        }

    @staticmethod
    async def get_alert_timeline(
        session: AsyncSession,
        alert_id: int,
    ) -> dict:
        # Get all history entries for this alert
        query = (
            select(PanicAlertHistory)
            .where(PanicAlertHistory.panic_alert_id == alert_id)
            .order_by(PanicAlertHistory.created_at.asc())
        )

        result = await session.execute(query)
        history_entries = result.scalars().all()

        return {
            "alert_id": alert_id,
            "entries": history_entries,
        }

    @staticmethod
    async def bulk_acknowledge(
        session: AsyncSession,
        alert_ids: list[int],
        acknowledged_by_user_id: int,
    ) -> dict:
        acknowledged_count = 0
        failed_ids = []
        errors = {}

        for alert_id in alert_ids:
            try:
                # Get the alert
                result = await session.execute(
                    select(PanicAlert).where(PanicAlert.id == alert_id)
                )
                alert = result.scalar_one_or_none()

                if not alert:
                    failed_ids.append(alert_id)
                    errors[alert_id] = "Alert not found"
                    continue

                # Only acknowledge if currently active
                if alert.status != PanicAlertStatus.ACTIVE:
                    failed_ids.append(alert_id)
                    errors[alert_id] = f"Alert not active (current status: {alert.status})"
                    continue

                # Update alert
                old_status = alert.status
                alert.status = PanicAlertStatus.ACKNOWLEDGED
                alert.acknowledged_by_user_id = acknowledged_by_user_id
                alert.acknowledged_at = utc_now()

                # Add history entry
                history_entry = PanicAlertHistory(
                    panic_alert_id=alert_id,
                    action="acknowledged",
                    performed_by_user_id=acknowledged_by_user_id,
                    old_status=old_status.value,
                    new_status=PanicAlertStatus.ACKNOWLEDGED.value,
                    notes="Bulk acknowledged",
                )
                session.add(history_entry)

                acknowledged_count += 1

            except Exception as e:  # noqa: BLE001 -- per-iteration boundary: one alert ack failure must not crash bulk acknowledge
                failed_ids.append(alert_id)
                errors[alert_id] = str(e)
                logger.error(
                    f"Failed to acknowledge alert {alert_id}: {e}",
                    extra={"alert_id": alert_id, "user_id": acknowledged_by_user_id}
                )

        await session.commit()

        return {
            "acknowledged_count": acknowledged_count,
            "failed_ids": failed_ids,
            "errors": errors,
        }
