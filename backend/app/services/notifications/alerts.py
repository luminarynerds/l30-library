# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseNotificationService
from .types import NotificationType

logger = get_logger(__name__)


class AlertNotificationService(BaseNotificationService):

    async def notify_privacy_alert(self, alert, db: AsyncSession) -> bool:
        from ...models.monitoring import MonitoringAlertSeverity

        try:
            if alert.severity not in (MonitoringAlertSeverity.HIGH, MonitoringAlertSeverity.CRITICAL):
                return False

            admins = await self._get_admin_users(db)
            if not admins:
                return False

            subject = f"Privacy Alert: {str(alert.alert_type).replace('_', ' ').title()}"
            body = self._format_privacy_alert_email(alert)

            for admin in admins:
                if admin.email:
                    context = {
                        "severity": str(alert.severity),
                        "user_id": alert.user_id,
                        "change_count": alert.change_count,
                    }
                    await self.send_notification(
                        notification_type=NotificationType.PRIVACY_ALERT,
                        recipient_email=admin.email,
                        subject=subject,
                        html_body=body,
                        context_data=context,
                    )

            logger.info(
                f"Privacy alert notification sent for alert {alert.id}",
                extra={"severity": alert.severity, "user_id": alert.user_id}
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to send privacy alert notification: {e}",
                exc_info=True,
                extra={"alert_id": alert.id}
            )
            return False

    async def notify_moderation_alert(self, alert, db: AsyncSession) -> bool:
        from ...models.monitoring import MonitoringAlertSeverity

        try:
            if alert.severity not in (MonitoringAlertSeverity.HIGH, MonitoringAlertSeverity.CRITICAL):
                return False

            admins = await self._get_admin_users(db)
            if not admins:
                return False

            subject = f"Moderation Alert: {alert.alert_type.replace('_', ' ').title()}"
            body = self._format_moderation_alert_email(alert)

            for admin in admins:
                if admin.email:
                    context = {
                        "severity": str(alert.severity),
                        "pending_count": alert.pending_count,
                    }
                    await self.send_notification(
                        notification_type=NotificationType.MODERATION_ALERT,
                        recipient_email=admin.email,
                        subject=subject,
                        html_body=body,
                        context_data=context,
                    )

            logger.info(
                f"Moderation alert notification sent for alert {alert.id}",
                extra={"severity": alert.severity, "pending_count": alert.pending_count}
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to send moderation alert notification: {e}",
                exc_info=True,
                extra={"alert_id": alert.id}
            )
            return False

    async def send_daily_digest(self, db: AsyncSession) -> bool:
        from ...models.monitoring import MonitoringAlertSeverity, ModerationAlert, PrivacyAlert

        try:
            one_day_ago = datetime.now(timezone.utc) - timedelta(hours=24)

            privacy_result = await db.execute(
                select(PrivacyAlert).where(PrivacyAlert.detected_at >= one_day_ago)
            )
            privacy_alerts = privacy_result.scalars().all()

            mod_result = await db.execute(
                select(ModerationAlert).where(ModerationAlert.triggered_at >= one_day_ago)
            )
            mod_alerts = mod_result.scalars().all()

            admins = await self._get_admin_users(db)
            if not admins:
                return False

            subject = f"Daily Alert Digest - {datetime.now().strftime('%Y-%m-%d')}"
            body = self._format_daily_digest_email(privacy_alerts, mod_alerts)

            for admin in admins:
                if admin.email:
                    context = {
                        "privacy_alerts": len(privacy_alerts),
                        "moderation_alerts": len(mod_alerts),
                    }
                    await self.send_notification(
                        notification_type=NotificationType.DAILY_DIGEST,
                        recipient_email=admin.email,
                        subject=subject,
                        html_body=body,
                        context_data=context,
                    )

            logger.info(
                "Daily alert digest sent",
                extra={
                    "privacy_alerts": len(privacy_alerts),
                    "moderation_alerts": len(mod_alerts),
                    "recipients": len(admins)
                }
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send daily digest: {e}", exc_info=True)
            return False

    # =========================================================================
    # Private helper methods for email formatting
    # =========================================================================

    @staticmethod
    def _format_privacy_alert_email(alert) -> str:
        return f"""
Privacy Alert Notification
===========================

Severity: {str(alert.severity).upper()}
Type: {str(alert.alert_type).replace('_', ' ').title()}
User ID: {alert.user_id}
Detected: {alert.detected_at.isoformat()}

Description:
{alert.description}

Details:
- Changes Made: {alert.change_count}
- Time Window: {alert.time_window_minutes} minutes
- Resource Type: {alert.resource_type}
- Anomalous Pattern: {alert.is_anomalous}

Action Required:
Please review this alert in the monitoring dashboard and take appropriate action.

Alert ID: {alert.id}
"""

    @staticmethod
    def _format_moderation_alert_email(alert) -> str:
        return f"""
Moderation Alert Notification
==============================

Severity: {str(alert.severity).upper()}
Type: {alert.alert_type.replace('_', ' ').title()}
Triggered: {alert.triggered_at.isoformat()}

Description:
{alert.description}

Queue Metrics:
- Pending Items: {alert.pending_count}
- Overdue Items: {alert.overdue_count}
- Oldest Item Age: {alert.oldest_item_age_hours} hours
- Average Turnaround: {alert.average_turnaround_hours:.1f} hours

Threshold Exceeded:
{alert.threshold_exceeded}: {alert.actual_value} (threshold: {alert.threshold_value})

Action Required:
Please address the moderation backlog immediately.

Alert ID: {alert.id}
"""

    @staticmethod
    def _format_daily_digest_email(privacy_alerts, mod_alerts) -> str:
        from ...models.monitoring import MonitoringAlertSeverity

        privacy_by_severity = {}
        for alert in privacy_alerts:
            severity = str(alert.severity)
            privacy_by_severity[severity] = privacy_by_severity.get(severity, 0) + 1

        mod_by_severity = {}
        for alert in mod_alerts:
            severity = str(alert.severity)
            mod_by_severity[severity] = mod_by_severity.get(severity, 0) + 1

        def _format_section(title, by_severity):
            if not by_severity:
                return f"{title}: None"
            lines = [f"{title}:"]
            for sev in [MonitoringAlertSeverity.CRITICAL.value, MonitoringAlertSeverity.HIGH.value,
                        MonitoringAlertSeverity.MEDIUM.value, MonitoringAlertSeverity.LOW.value]:
                count = by_severity.get(sev, 0)
                if count > 0:
                    lines.append(f"  - {sev.title()}: {count}")
            return "\n".join(lines)

        privacy_section = _format_section("Privacy Alerts", privacy_by_severity)
        mod_section = _format_section("Moderation Alerts", mod_by_severity)

        return f"""
Daily Alert Digest
==================

Generated: {datetime.now().isoformat()}

{privacy_section}

{mod_section}

Summary:
- Total Privacy Alerts: {len(privacy_alerts)}
- Total Moderation Alerts: {len(mod_alerts)}
- Critical Issues: {sum(1 for a in privacy_alerts if a.severity == MonitoringAlertSeverity.CRITICAL) + sum(1 for a in mod_alerts if a.severity == MonitoringAlertSeverity.CRITICAL)}

Please review the monitoring dashboard for details on all alerts.
"""
