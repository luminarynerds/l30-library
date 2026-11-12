# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.panic_alert import PanicAlert, PanicAlertNotificationPreferences, PanicAlertStatus
from ..models.notification import Notification, NotificationStatus, NotificationType
from ..models.user import User
from ..schemas.panic_alert import (
    PanicAlertCreate,
    PanicAlertNotificationPreferencesCreate,
    PanicAlertResponse,
    PanicAlertListResponse,
)
from app.core.datetime_utils import utc_now
from ..services.unified_notification_service import (
    UnifiedNotificationService,
    NotificationType as UnifiedNotificationType,
)
from ..core.config import get_settings
from ..core.frontend_routes import routes
from ..core.logging import get_logger
from ..app_logging.panic_alert_logger import PanicAlertLogger

settings = get_settings()
logger = get_logger(__name__)
panic_logger = PanicAlertLogger()


class PanicAlertService:

    @staticmethod
    async def trigger_alert(
        session: AsyncSession,
        user_id: int,
        alert_data: PanicAlertCreate,
        branch_id: Optional[int] = None,
    ) -> PanicAlertResponse:
        try:
            db_alert = PanicAlert(
                triggered_by_user_id=user_id,
                branch_id=branch_id,
                activation_source=alert_data.activation_source,
                situation_notes=alert_data.situation_notes,
                alert_metadata=alert_data.metadata,
                status=PanicAlertStatus.ACTIVE,
            )

            session.add(db_alert)
            await session.flush()
            await session.refresh(db_alert)  # Ensure created_at is loaded from DB
            await session.commit()  # Commit FIRST to ensure alert exists in DB

            # Get location info for logging
            location = "Unknown Location"
            if branch_id:
                from ..models.branch import Branch
                branch_result = await session.execute(
                    select(Branch).where(Branch.id == branch_id)
                )
                branch = branch_result.scalar_one_or_none()
                location = branch.name if branch else f"Branch ID {branch_id}"

            # Log alert creation
            panic_logger.log_alert_created(
                alert_id=db_alert.id,
                user_id=user_id,
                branch_id=branch_id,
                activation_source=str(alert_data.activation_source),
                location=location,
                has_notes=bool(alert_data.situation_notes),
                metadata=alert_data.metadata,
            )

            # Notify relevant managers/security staff AFTER successful commit
            await PanicAlertService._notify_alert_recipients(session, db_alert)

            return PanicAlertResponse.model_validate(db_alert)
        except Exception as e:
            panic_logger.log_database_error(
                operation="create_panic_alert",
                error_message=str(e),
                user_id=user_id,
            )
            raise

    @staticmethod
    async def acknowledge_alert(
        session: AsyncSession, alert_id: int, acknowledged_by_user_id: int
    ) -> PanicAlertResponse:
        result = await session.execute(select(PanicAlert).where(PanicAlert.id == alert_id))
        alert = result.scalar_one_or_none()

        if not alert:
            raise ValueError(f"Panic alert {alert_id} not found")

        old_status = alert.status
        alert.status = PanicAlertStatus.ACKNOWLEDGED
        alert.acknowledged_by_user_id = acknowledged_by_user_id
        alert.acknowledged_at = utc_now()

        # Calculate response time
        response_time_seconds = None
        if alert.created_at:
            response_time_seconds = (alert.acknowledged_at - alert.created_at).total_seconds()

        await session.commit()
        await session.refresh(alert)

        # Log acknowledgment
        panic_logger.log_alert_acknowledged(
            alert_id=alert_id,
            acknowledged_by_user_id=acknowledged_by_user_id,
            response_time_seconds=response_time_seconds,
        )

        # Log status transition
        panic_logger.log_status_transition(
            alert_id=alert_id,
            from_status=str(old_status),
            to_status=str(PanicAlertStatus.ACKNOWLEDGED),
            user_id=acknowledged_by_user_id,
        )

        # Notify the staff member who triggered the alert
        await PanicAlertService._notify_triggerer_acknowledged(
            session, alert, acknowledged_by_user_id
        )

        return PanicAlertResponse.model_validate(alert)

    @staticmethod
    async def resolve_alert(
        session: AsyncSession,
        alert_id: int,
        resolution_notes: Optional[str] = None,
    ) -> PanicAlertResponse:
        result = await session.execute(select(PanicAlert).where(PanicAlert.id == alert_id))
        alert = result.scalar_one_or_none()

        if not alert:
            raise ValueError(f"Panic alert {alert_id} not found")

        old_status = alert.status
        alert.status = PanicAlertStatus.RESOLVED
        alert.resolution_notes = resolution_notes
        alert.resolved_at = utc_now()

        # Calculate resolution time
        resolution_time_seconds = None
        if alert.created_at:
            resolution_time_seconds = (alert.resolved_at - alert.created_at).total_seconds()

        await session.commit()
        await session.refresh(alert)

        # Detect false alert (quick resolution without acknowledgment)
        false_alert = False
        if resolution_time_seconds and resolution_time_seconds < 300:  # < 5 minutes
            if not alert.acknowledged_at:
                false_alert = True

        # Log resolution
        panic_logger.log_alert_resolved(
            alert_id=alert_id,
            resolution_time_seconds=resolution_time_seconds,
            has_notes=bool(resolution_notes),
            false_alert=false_alert,
        )

        # Log status transition
        panic_logger.log_status_transition(
            alert_id=alert_id,
            from_status=str(old_status),
            to_status=str(PanicAlertStatus.RESOLVED),
        )

        return PanicAlertResponse.model_validate(alert)

    @staticmethod
    async def get_alert(session: AsyncSession, alert_id: int) -> Optional[PanicAlertResponse]:
        result = await session.execute(select(PanicAlert).where(PanicAlert.id == alert_id))
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        return PanicAlertResponse.model_validate(alert)

    @staticmethod
    async def get_active_alerts(
        session: AsyncSession,
        branch_id: Optional[int] = None,
        limit: int = 100,
    ) -> list[PanicAlertListResponse]:
        query = select(PanicAlert).where(PanicAlert.status == PanicAlertStatus.ACTIVE)

        if branch_id:
            query = query.where(PanicAlert.branch_id == branch_id)

        query = query.order_by(PanicAlert.created_at.desc()).limit(limit)

        result = await session.execute(query)
        alerts = result.scalars().all()

        return [PanicAlertListResponse.model_validate(alert) for alert in alerts]

    @staticmethod
    async def get_recent_alerts(
        session: AsyncSession,
        user_id: int,
        hours: int = 24,
        limit: int = 50,
    ) -> list[PanicAlertListResponse]:
        # Calculate timestamp for lookback
        cutoff_time = utc_now() - timedelta(hours=hours)

        query = (
            select(PanicAlert)
            .where(
                and_(
                    PanicAlert.triggered_by_user_id == user_id,
                    PanicAlert.created_at >= cutoff_time,
                )
            )
            .order_by(PanicAlert.created_at.desc())
            .limit(limit)
        )

        result = await session.execute(query)
        alerts = result.scalars().all()

        return [PanicAlertListResponse.model_validate(alert) for alert in alerts]

    @staticmethod
    async def _notify_alert_recipients(session: AsyncSession, alert: PanicAlert) -> None:
        # Get users who want to receive panic alerts
        query = select(PanicAlertNotificationPreferences).where(
            PanicAlertNotificationPreferences.receive_panic_alerts == True
        )

        result = await session.execute(query)
        preferences = result.scalars().all()

        # Filter by branch if needed
        if alert.branch_id:
            filtered_prefs = [
                p
                for p in preferences
                if p.notify_for_all_branches or (p.branch_ids and alert.branch_id in p.branch_ids)
            ]
        else:
            filtered_prefs = [p for p in preferences if p.notify_for_all_branches]

        # Get alert triggerer info
        triggerer_result = await session.execute(
            select(User).where(User.id == alert.triggered_by_user_id)
        )
        triggerer = triggerer_result.scalar_one_or_none()
        staff_name = triggerer.full_name if triggerer else "Unknown Staff"

        # Get branch info if available
        location = "Unknown Location"
        if alert.branch_id:
            from ..models.branch import Branch
            branch_result = await session.execute(
                select(Branch).where(Branch.id == alert.branch_id)
            )
            branch = branch_result.scalar_one_or_none()
            location = branch.name if branch else f"Branch ID {alert.branch_id}"

        # Prepare context data
        alert_number = f"PA-{alert.id:06d}"
        context_data = {
            "alert_number": alert_number,
            "location": location,
            "triggered_at": alert.created_at.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "staff_name": staff_name,
            "alert_url": routes.url(settings.frontend_url, routes.staff_panic_alerts, id=alert.id),
            "situation_notes": (
                f'<p style="background-color: #FFF9F0; padding: 15px; border-radius: 5px;">'
                f'<strong>Notes:</strong> {alert.situation_notes}</p>'
                if alert.situation_notes else ''
            ),
        }

        # Initialize notification service
        notification_service = UnifiedNotificationService()

        # Track notification channels used
        notification_channels = []
        email_count = 0
        sms_count = 0
        in_app_count = 0

        # Send notifications to all recipients
        for pref in filtered_prefs:
            # Get user details
            user_result = await session.execute(
                select(User).where(User.id == pref.user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                continue

            # Send EMAIL notification (HIGH PRIORITY - bypasses DND)
            if pref.notify_via_email and user.email:
                # Log email send attempt
                panic_logger.log_email_send_attempt(
                    alert_id=alert.id,
                    recipient_email=user.email,
                    recipient_user_id=user.id,
                    notification_type="panic_alert",
                )

                try:
                    import time
                    start_time = time.time()

                    await notification_service.send_templated(
                        notification_type=UnifiedNotificationType.PANIC_ALERT,
                        recipient_email=user.email,
                        context_data=context_data,
                        user_id=user.id,
                        db=session,
                    )

                    send_duration = time.time() - start_time
                    email_count += 1
                    if "email" not in notification_channels:
                        notification_channels.append("email")

                    # Log email send success
                    panic_logger.log_email_send_success(
                        alert_id=alert.id,
                        recipient_email=user.email,
                        recipient_user_id=user.id,
                        send_duration_seconds=send_duration,
                    )
                except Exception as e:  # noqa: BLE001 - panic-alert channel failure must not block other channels (SMS, in-app)
                    # Log email send failure
                    panic_logger.log_email_send_failure(
                        alert_id=alert.id,
                        recipient_email=user.email,
                        recipient_user_id=user.id,
                        error_message=str(e),
                        error_type=type(e).__name__,
                    )
                    logger.error(
                        f"Failed to send panic alert email to {user.email}: {e}",
                        extra={"alert_id": alert.id, "user_id": user.id}
                    )

            # Send SMS notification (HIGH PRIORITY - bypasses DND)
            if pref.notify_via_sms and user.phone:
                try:
                    # Queue SMS via SMS service (bypasses DND for emergency)
                    from ..services.sms_service import SMSService
                    from ..models.sms import SMSNotificationType

                    sms_message = f"EMERGENCY PANIC ALERT #{alert_number}: {location}. Respond immediately."

                    await SMSService.queue_sms(
                        user_id=user.id,
                        phone_number=user.phone,
                        notification_type=SMSNotificationType.ACCOUNT_ALERT,
                        message=sms_message,
                        context_data={
                            "alert_id": alert.id,
                            "alert_number": alert_number,
                            "location": location,
                            "priority": "HIGH",
                        },
                        db=session,
                        check_opt_out=False,  # Emergency - bypass opt-out
                        check_dnd=False,  # Emergency - bypass DND
                    )

                    sms_count += 1
                    if "sms" not in notification_channels:
                        notification_channels.append("sms")

                    logger.info(
                        f"SMS panic alert notification queued for user {user.id}",
                        extra={
                            "alert_id": alert.id,
                            "alert_number": alert_number,
                            "phone_number": user.phone[-4:],  # Log last 4 digits only
                            "location": location
                        }
                    )
                except Exception as e:  # noqa: BLE001 - panic-alert channel failure must not block other channels (email, in-app)
                    logger.error(
                        f"Failed to queue panic alert SMS: {e}",
                        extra={"alert_id": alert.id, "user_id": user.id}
                    )

            # In-app notification
            if pref.notify_via_in_app:
                try:
                    session.add(
                        Notification(
                            user_id=user.id,
                            notification_type=NotificationType.PANIC_ALERT,
                            status=NotificationStatus.SENT,
                            subject=f"Panic Alert #{alert_number}",
                            message=(
                                f"Emergency panic alert triggered by {staff_name} at {location}. "
                                "Respond immediately."
                            ),
                            context_data={
                                "alert_id": alert.id,
                                "alert_number": alert_number,
                                "location": location,
                                "triggered_by_user_id": alert.triggered_by_user_id,
                                "priority": "HIGH",
                            },
                            sent_at=utc_now(),
                        )
                    )
                    in_app_count += 1
                    if "in_app" not in notification_channels:
                        notification_channels.append("in_app")

                    logger.info(
                        f"In-app panic alert notification for user {user.id}",
                        extra={"alert_id": alert.id, "alert_number": alert_number}
                    )
                except Exception as e:  # noqa: BLE001 - panic-alert channel failure must not block other channels (email, SMS)
                    logger.error(
                        f"Failed to create in-app panic alert notification: {e}",
                        extra={"alert_id": alert.id, "user_id": user.id}
                    )

        await session.flush()

        # Log overall notification broadcast
        panic_logger.log_notification_sent(
            alert_id=alert.id,
            recipient_count=len(filtered_prefs),
            notification_channels=notification_channels,
            location=location,
        )

        # Log notification attempt
        logger.warning(
            f"Panic alert {alert_number} notifications sent to {len(filtered_prefs)} recipients",
            extra={
                "alert_id": alert.id,
                "location": location,
                "recipients": len(filtered_prefs),
                "staff_name": staff_name,
                "email_count": email_count,
                "sms_count": sms_count,
                "in_app_count": in_app_count,
            }
        )

    @staticmethod
    async def _notify_triggerer_acknowledged(
        session: AsyncSession, alert: PanicAlert, acknowledged_by_user_id: int
    ) -> None:
        # Get acknowledger name
        ack_result = await session.execute(
            select(User).where(User.id == acknowledged_by_user_id)
        )
        acknowledger = ack_result.scalar_one_or_none()
        ack_name = acknowledger.full_name if acknowledger else "A manager"

        alert_number = f"PA-{alert.id:06d}"

        session.add(
            Notification(
                user_id=alert.triggered_by_user_id,
                notification_type=NotificationType.PANIC_ALERT,
                status=NotificationStatus.SENT,
                subject=f"Alert #{alert_number} acknowledged",
                message=f"{ack_name} has acknowledged your alert. Help is on the way.",
                context_data={
                    "alert_id": alert.id,
                    "alert_number": alert_number,
                    "acknowledged_by_user_id": acknowledged_by_user_id,
                    "acknowledged_by_name": ack_name,
                    "priority": "HIGH",
                },
                sent_at=utc_now(),
            )
        )
        await session.flush()

        logger.info(
            f"Notified triggerer (user {alert.triggered_by_user_id}) that alert {alert_number} was acknowledged",
            extra={"alert_id": alert.id, "acknowledged_by": acknowledged_by_user_id},
        )

    @staticmethod
    async def get_notification_preferences(
        session: AsyncSession, user_id: int
    ) -> Optional[PanicAlertNotificationPreferences]:
        result = await session.execute(
            select(PanicAlertNotificationPreferences).where(
                PanicAlertNotificationPreferences.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def set_notification_preferences(
        session: AsyncSession,
        user_id: int,
        preferences: PanicAlertNotificationPreferencesCreate,
    ) -> PanicAlertNotificationPreferences:
        result = await session.execute(
            select(PanicAlertNotificationPreferences).where(
                PanicAlertNotificationPreferences.user_id == user_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing preferences
            existing.receive_panic_alerts = preferences.receive_panic_alerts
            existing.notify_via_email = preferences.notify_via_email
            existing.notify_via_sms = preferences.notify_via_sms
            existing.notify_via_in_app = preferences.notify_via_in_app
            existing.notify_for_all_branches = preferences.notify_for_all_branches
            existing.branch_ids = preferences.branch_ids
            existing.sound_enabled = preferences.sound_enabled
            existing.sound_preference = preferences.sound_preference
            existing.vibration_enabled = preferences.vibration_enabled
        else:
            # Create new preferences
            existing = PanicAlertNotificationPreferences(
                user_id=user_id,
                receive_panic_alerts=preferences.receive_panic_alerts,
                notify_via_email=preferences.notify_via_email,
                notify_via_sms=preferences.notify_via_sms,
                notify_via_in_app=preferences.notify_via_in_app,
                notify_for_all_branches=preferences.notify_for_all_branches,
                branch_ids=preferences.branch_ids,
                sound_enabled=preferences.sound_enabled,
                sound_preference=preferences.sound_preference,
                vibration_enabled=preferences.vibration_enabled,
            )
            session.add(existing)

        await session.commit()
        return existing
