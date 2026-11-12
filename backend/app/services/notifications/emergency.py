# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.user import User, UserRole
from .base import BaseNotificationService
from .types import NotificationType

logger = get_logger(__name__)


class EmergencyNotificationService(BaseNotificationService):

    async def notify_police_911(
        self,
        panic_alert,
        db: AsyncSession,
        emergency_type: str = "security_emergency",
        location_details: Optional[str] = None,
    ):
        from ...models.panic_alert import (
            EmergencyNotification, EmergencyNotificationType,
            EmergencyNotificationStatus
        )

        try:
            notification = EmergencyNotification(
                panic_alert_id=panic_alert.id,
                notification_type=EmergencyNotificationType.POLICE_911,
                status=EmergencyNotificationStatus.QUEUED,
                recipient_name="911 Dispatch",
                recipient_phone="911",
                message=self._generate_911_message(panic_alert, emergency_type, location_details),
            )

            db.add(notification)
            await db.flush()
            notification.status = EmergencyNotificationStatus.SENT
            notification.sent_at = datetime.now(timezone.utc)

            logger.warning(f"911 dispatch notified for alert {panic_alert.alert_number}")
            return notification

        except Exception as e:  # noqa: BLE001  # emergency dispatch boundary - record failure, other channels must still fire
            logger.error(f"Failed to notify 911: {str(e)}")
            return None

    async def notify_security_company(
        self,
        panic_alert,
        db: AsyncSession,
        company_name: str = "Building Security Company",
        phone: Optional[str] = None,
    ):
        from ...models.panic_alert import (
            EmergencyNotification, EmergencyNotificationType,
            EmergencyNotificationStatus
        )

        try:
            if not phone:
                phone = "+1-555-SEC-COMPANY"

            notification = EmergencyNotification(
                panic_alert_id=panic_alert.id,
                notification_type=EmergencyNotificationType.SECURITY_COMPANY,
                status=EmergencyNotificationStatus.QUEUED,
                recipient_name=company_name,
                recipient_phone=phone,
                message=self._generate_security_company_message(panic_alert),
            )

            db.add(notification)
            await db.flush()
            notification.status = EmergencyNotificationStatus.SENT
            notification.sent_at = datetime.now(timezone.utc)

            logger.info(f"Security company {company_name} notified for alert {panic_alert.alert_number}")
            return notification

        except Exception as e:  # noqa: BLE001  # emergency dispatch boundary - record failure, other channels must still fire
            logger.error(f"Failed to notify security company: {str(e)}")
            return None

    async def notify_building_staff(self, panic_alert, db: AsyncSession) -> List:
        from ...models.panic_alert import (
            EmergencyNotification, EmergencyNotificationType,
            EmergencyNotificationStatus
        )

        notifications = []

        try:
            result = await db.execute(
                select(User).where(
                    User.role.in_([UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN])
                )
            )
            staff = result.scalars().all()

            for staff_member in staff:
                notification = EmergencyNotification(
                    panic_alert_id=panic_alert.id,
                    notification_type=EmergencyNotificationType.BUILDING_STAFF,
                    status=EmergencyNotificationStatus.QUEUED,
                    recipient_name=staff_member.name,
                    recipient_email=staff_member.email,
                    message=self._generate_staff_message(panic_alert),
                )

                db.add(notification)
                notifications.append(notification)

                if staff_member.email:
                    await self.send_notification(
                        notification_type=NotificationType.BUILDING_STAFF_ALERT,
                        recipient_email=staff_member.email,
                        subject="EMERGENCY ALERT",
                        html_body=notification.message,
                        context_data={"staff_member": staff_member.name},
                    )

                notification.status = EmergencyNotificationStatus.SENT
                notification.sent_at = datetime.now(timezone.utc)

            await db.flush()
            logger.info(f"Notified {len(notifications)} staff members for alert {panic_alert.alert_number}")
            return notifications

        except Exception as e:  # noqa: BLE001  # emergency dispatch boundary - record failure, other channels must still fire
            logger.error(f"Failed to notify building staff: {str(e)}")
            return notifications

    # =========================================================================
    # Private helper methods for message generation
    # =========================================================================

    @staticmethod
    def _generate_911_message(panic_alert, emergency_type, location_details) -> str:
        from ...models.panic_alert import AlertType

        alert_type_map = {
            AlertType.PANIC_BUTTON: "Panic Button Activated",
            AlertType.ACTIVE_SHOOTER: "Active Shooter Report",
            AlertType.BOMB_THREAT: "Bomb Threat",
            AlertType.FIRE_ALARM: "Fire Alarm",
            AlertType.MEDICAL_EMERGENCY: "Medical Emergency",
            AlertType.SECURITY_THREAT: "Security Threat",
        }

        alert_description = alert_type_map.get(panic_alert.alert_type, "Emergency Alert")

        return f"""
EMERGENCY DISPATCH NOTIFICATION
================================
Alert Number: {panic_alert.alert_number}
Type: {alert_description}
Severity: {str(panic_alert.severity).upper()}
Time: {panic_alert.triggered_at.isoformat()}
Location: {panic_alert.location or 'Unknown'}
{"Details: " + location_details if location_details else ""}
Description: {panic_alert.description or "No description provided"}

IMMEDIATE RESPONSE REQUIRED
"""

    @staticmethod
    def _generate_security_company_message(panic_alert) -> str:
        return f"""
SECURITY ALERT NOTIFICATION
============================
Alert Number: {panic_alert.alert_number}
Type: {panic_alert.alert_type}
Severity: {str(panic_alert.severity).upper()}
Time Triggered: {panic_alert.triggered_at.isoformat()}
Location: {panic_alert.location or "Building"}

Description:
{panic_alert.description or "No description provided"}

Affected Areas: {", ".join(panic_alert.affected_areas) if panic_alert.affected_areas else "Full Building"}

Please dispatch immediate response.
Reference: {panic_alert.alert_number}
"""

    @staticmethod
    def _generate_staff_message(panic_alert) -> str:
        from ...models.panic_alert import AlertType

        instructions = {
            AlertType.ACTIVE_SHOOTER: """
ACTIVE SHOOTER PROTOCOL:
1. Evacuate if safe to do so
2. If trapped, barricade yourself
3. Silence phones, remain quiet
4. Wait for emergency personnel instructions
""",
            AlertType.BOMB_THREAT: """
BOMB THREAT PROTOCOL:
1. Evacuate building immediately
2. Use designated evacuation routes
3. Assembly point: [SPECIFY LOCATION]
4. Do not return until all-clear given
""",
            AlertType.FIRE_ALARM: """
FIRE EMERGENCY PROTOCOL:
1. Evacuate immediately using nearest exit
2. Close doors behind you
3. Proceed to assembly area
4. Do not use elevators
""",
            AlertType.MEDICAL_EMERGENCY: """
MEDICAL EMERGENCY PROTOCOL:
1. Medical personnel are responding
2. Clear pathways for paramedics
3. Do not move injured persons
4. Provide information to first responders
""",
        }

        protocol = instructions.get(panic_alert.alert_type, "Follow emergency procedures")

        return f"""
BUILDING EMERGENCY ALERT
========================
Alert Number: {panic_alert.alert_number}
Type: {str(panic_alert.alert_type).replace('_', ' ').title()}
Time: {panic_alert.triggered_at.isoformat()}
Location: {panic_alert.location or "Building"}

{protocol}

This is an automated emergency notification.
Follow building emergency procedures.

For more information, check building PA system and emergency alerts.
"""
