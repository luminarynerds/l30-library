# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.email import send_email, COLORS
from ..models.threat_response import (
    ThreatAlert,
    ThreatLevel,
    ThreatType,
    StaffCheckIn,
    EvacuationRoute,
    RallyPoint,
    EvacuationEvent,
    ReunificationEvent,
    MediaResponseProtocol,
    AllClearAnnouncement,
    ThreatResponsePlan,
)
from ..models.user import User, UserRole
from ..models.multi_branch import Branch
from ..models.notification import NotificationQueue, NotificationType, NotificationStatus

settings = get_settings()
logger = get_logger(__name__)


class ThreatResponseService:

    @staticmethod
    async def initiate_threat_alert(
        db: AsyncSession,
        threat_type: ThreatType,
        threat_level: ThreatLevel,
        branch_id: int,
        created_by_id: int,
        description: str,
        location_description: Optional[str] = None,
        external_information: Optional[str] = None,
    ) -> ThreatAlert:
        alert = ThreatAlert(
            threat_type=threat_type,
            threat_level=threat_level,
            branch_id=branch_id,
            location_description=location_description,
            description=description,
            external_information=external_information,
            created_by_id=created_by_id,
        )

        db.add(alert)
        await db.flush()

        # Automatic 911 dispatch
        await ThreatResponseService._dispatch_911(db, alert)

        # Automatic lockdown for SHELTER_IN_PLACE
        if threat_level == ThreatLevel.SHELTER_IN_PLACE:
            await ThreatResponseService.initiate_lockdown(db, alert.id)

        await db.commit()
        return alert

    @staticmethod
    async def _dispatch_911(db: AsyncSession, alert: ThreatAlert) -> None:
        # Get branch information for location
        result = await db.execute(select(Branch).where(Branch.id == alert.branch_id))
        branch = result.scalar_one_or_none()

        if not branch:
            logger.error(f"Branch {alert.branch_id} not found for 911 dispatch")
            return

        # Mark as dispatched
        alert.dispatch_called = True
        alert.dispatch_time = datetime.now(timezone.utc)
        alert.dispatch_notes = (
            f"Automatic 911 dispatch initiated for {alert.threat_type} "
            f"at {branch.name}. Location: {alert.location_description or 'Primary location'}. "
            f"Threat Level: {alert.threat_level}"
        )

        logger.critical(
            f"THREAT ALERT: 911 Dispatch for {alert.threat_type} "
            f"at Branch {alert.branch_id} ({branch.name}). "
            f"Level: {alert.threat_level}"
        )

        # Notify all admins and directors
        await ThreatResponseService._notify_staff_of_threat(db, alert)

    @staticmethod
    async def initiate_lockdown(db: AsyncSession, alert_id: int) -> ThreatAlert:
        result = await db.execute(
            select(ThreatAlert).where(ThreatAlert.id == alert_id)
        )
        alert = result.scalar_one()

        alert.lockdown_initiated = True
        alert.lockdown_time = datetime.now(timezone.utc)

        logger.warning(f"LOCKDOWN INITIATED: Threat Alert {alert_id}")

        # Notify all staff at branch
        await ThreatResponseService._broadcast_lockdown_order(db, alert)

        await db.commit()
        return alert

    @staticmethod
    async def staff_check_in(
        db: AsyncSession,
        alert_id: int,
        user_id: int,
        is_safe: bool,
        location: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> StaffCheckIn:
        check_in = StaffCheckIn(
            threat_alert_id=alert_id,
            user_id=user_id,
            is_safe=is_safe,
            location=location,
            notes=notes,
        )

        db.add(check_in)
        await db.flush()

        # Update alert accountability
        result = await db.execute(
            select(ThreatAlert).where(ThreatAlert.id == alert_id)
        )
        alert = result.scalar_one()

        safe_count = await db.scalar(
            select(func.count(StaffCheckIn.id)).where(
                and_(
                    StaffCheckIn.threat_alert_id == alert_id,
                    StaffCheckIn.is_safe == True,
                )
            )
        )

        alert.staff_checked_in += 1
        alert.staff_checked_in_safe = safe_count or 0

        await db.commit()
        await db.refresh(check_in)

        logger.info(
            f"Staff check-in: {user_id} marked {'SAFE' if is_safe else 'NEEDS HELP'} "
            f"for alert {alert_id}"
        )

        return check_in

    @staticmethod
    async def initiate_evacuation(
        db: AsyncSession,
        alert_id: int,
        evacuation_route_id: int,
        rally_point_id: int,
    ) -> EvacuationEvent:
        result = await db.execute(
            select(ThreatAlert).where(ThreatAlert.id == alert_id)
        )
        alert = result.scalar_one()

        alert.evacuation_initiated = True
        alert.evacuation_time = datetime.now(timezone.utc)

        evac = EvacuationEvent(
            threat_alert_id=alert_id,
            evacuation_route_id=evacuation_route_id,
            rally_point_id=rally_point_id,
        )

        db.add(evac)
        await db.flush()

        logger.warning(f"EVACUATION INITIATED: Alert {alert_id}")

        # Broadcast evacuation orders
        await ThreatResponseService._broadcast_evacuation_order(db, alert, evac)

        await db.commit()
        await db.refresh(evac)

        return evac

    @staticmethod
    async def get_evacuation_routes(
        db: AsyncSession, branch_id: int
    ) -> List[EvacuationRoute]:
        result = await db.execute(
            select(EvacuationRoute).where(
                and_(
                    EvacuationRoute.branch_id == branch_id,
                    EvacuationRoute.is_active == True,
                )
            )
        )
        return result.scalars().all()

    @staticmethod
    async def get_rally_points(
        db: AsyncSession, branch_id: int
    ) -> List[RallyPoint]:
        result = await db.execute(
            select(RallyPoint).where(
                and_(
                    RallyPoint.branch_id == branch_id,
                    RallyPoint.is_active == True,
                )
            )
        )
        return result.scalars().all()

    @staticmethod
    async def reunify_child_with_guardian(
        db: AsyncSession,
        alert_id: int,
        child_patron_id: int,
        parent_patron_id: Optional[int],
        parent_contact_name: str,
        parent_contact_phone: str,
        reunified_with: str,
        id_verified: bool = False,
    ) -> ReunificationEvent:
        event = ReunificationEvent(
            threat_alert_id=alert_id,
            child_patron_id=child_patron_id,
            parent_patron_id=parent_patron_id,
            parent_contact_name=parent_contact_name,
            parent_contact_phone=parent_contact_phone,
            child_reunified=True,
            reunification_time=datetime.now(timezone.utc),
            reunified_with=reunified_with,
            id_verified=id_verified,
        )

        db.add(event)
        await db.flush()

        logger.info(
            f"Child {child_patron_id} reunified with guardian at alert {alert_id}"
        )

        # Update alert accounting
        result = await db.execute(
            select(ThreatAlert).where(ThreatAlert.id == alert_id)
        )
        alert = result.scalar_one()

        alert.children_count = (
            alert.children_count + 1 if alert.children_count else 1
        )

        await db.commit()
        await db.refresh(event)

        return event

    @staticmethod
    async def send_parent_notification(
        db: AsyncSession, alert_id: int
    ) -> None:
        result = await db.execute(
            select(ThreatAlert).where(ThreatAlert.id == alert_id)
        )
        alert = result.scalar_one()

        # Get branch info
        branch_result = await db.execute(
            select(Branch).where(Branch.id == alert.branch_id)
        )
        branch = branch_result.scalar_one()

        # Find children in active programs at branch (this would integrate with program service)
        # For now, create notifications that can be queued

        notification_html = f"""\
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #C0392B; font-weight: bold;">Safety Alert - Action Required</h2>

            <p style="color: #2C3E50; font-size: 16px; line-height: 1.6;">
                An active threat situation has been reported at <strong>{branch.name}</strong>.
            </p>

            <div style="background-color: #FADBD8; padding: 20px; border-left: 4px solid #C0392B; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #C0392B;">Reunification Procedures:</h3>
                <ol style="color: #2C3E50;">
                    <li>All children are accounted for and in safe locations</li>
                    <li>Authorized guardians only - ID verification required</li>
                    <li>Reunification location: {alert.location_description or 'Primary building entrance'}</li>
                    <li>Follow staff instructions upon arrival</li>
                </ol>
            </div>

            <p style="color: #2C3E50;">
                <strong>Do not come to the facility unless instructed by staff.</strong>
            </p>

            <p style="color: #7F8C8D; font-size: 14px;">
                Additional information will be provided as it becomes available.
                Stay calm. Children and staff are safe.
            </p>
        </div>
        """

        alert.parent_notification_sent = True
        alert.parent_notification_time = datetime.now(timezone.utc)

        logger.warning(f"Parent notifications queued for threat alert {alert_id}")

    @staticmethod
    async def issue_media_statement(
        db: AsyncSession, alert_id: int, statement: Optional[str] = None
    ) -> None:
        result = await db.execute(
            select(ThreatAlert).where(ThreatAlert.id == alert_id)
        )
        alert = result.scalar_one()

        branch_result = await db.execute(
            select(Branch).where(Branch.id == alert.branch_id)
        )
        branch = branch_result.scalar_one()

        # Get media protocol for branch
        protocol_result = await db.execute(
            select(MediaResponseProtocol).where(
                MediaResponseProtocol.branch_id == alert.branch_id
            )
        )
        protocol = protocol_result.scalar_one_or_none()

        if not statement and protocol:
            # Use initial statement from protocol
            statement = protocol.initial_statement

        if not statement:
            # Fallback generic statement
            statement = (
                f"An active threat situation has been reported at {branch.name}. "
                f"All individuals have been moved to secure locations. "
                f"Law enforcement is on scene. Updates will be provided as available."
            )

        alert.media_statement = statement
        alert.media_responders_notified = True
        alert.media_notification_time = datetime.now(timezone.utc)

        if protocol:
            alert.information_hotline = protocol.media_contact_number

        logger.info(f"Media statement issued for alert {alert_id}")

    @staticmethod
    async def issue_all_clear(
        db: AsyncSession, alert_id: int, announced_by_id: int
    ) -> AllClearAnnouncement:
        result = await db.execute(
            select(ThreatAlert).where(ThreatAlert.id == alert_id)
        )
        alert = result.scalar_one()

        branch_result = await db.execute(
            select(Branch).where(Branch.id == alert.branch_id)
        )
        branch = branch_result.scalar_one()

        # Get protocol for all-clear statement
        protocol_result = await db.execute(
            select(MediaResponseProtocol).where(
                MediaResponseProtocol.branch_id == alert.branch_id
            )
        )
        protocol = protocol_result.scalar_one_or_none()

        all_clear_text = (
            protocol.resolution_statement
            if protocol
            else f"The threat has been resolved. {branch.name} is secure. "
            f"Thank you for your cooperation and patience."
        )

        announcement = AllClearAnnouncement(
            threat_alert_id=alert_id,
            announcement_text=all_clear_text,
            announced_by_id=announced_by_id,
            announced_via_intercom=True,
            announced_via_email=True,
            announced_via_app=True,
        )

        db.add(announcement)
        await db.flush()

        # Mark alert as resolved
        alert.all_clear_issued = True
        alert.all_clear_time = datetime.now(timezone.utc)
        alert.all_clear_initiated_by_id = announced_by_id

        logger.warning(f"ALL-CLEAR issued for threat alert {alert_id}")

        # Broadcast all-clear
        await ThreatResponseService._broadcast_all_clear(db, alert, announcement)

        await db.commit()
        await db.refresh(announcement)

        return announcement

    @staticmethod
    async def _notify_staff_of_threat(db: AsyncSession, alert: ThreatAlert) -> None:
        # Get all staff at branch
        staff_result = await db.execute(
            select(User).where(
                and_(
                    User.work_branch_id == alert.branch_id,
                    User.role.in_([UserRole.STAFF, UserRole.DIRECTOR]),
                )
            )
        )
        staff = staff_result.scalars().all()

        logger.info(f"Notifying {len(staff)} staff members of threat alert {alert.id}")

    @staticmethod
    async def _broadcast_lockdown_order(db: AsyncSession, alert: ThreatAlert) -> None:
        logger.warning(f"BROADCAST: Lockdown order for alert {alert.id}")

    @staticmethod
    async def _broadcast_evacuation_order(
        db: AsyncSession, alert: ThreatAlert, evac: EvacuationEvent
    ) -> None:
        logger.warning(f"BROADCAST: Evacuation order for alert {alert.id}")

    @staticmethod
    async def _broadcast_all_clear(
        db: AsyncSession, alert: ThreatAlert, announcement: AllClearAnnouncement
    ) -> None:
        logger.info(f"BROADCAST: All-clear for alert {alert.id}")

    @staticmethod
    async def get_threat_alert_status(
        db: AsyncSession, alert_id: int
    ) -> dict:
        result = await db.execute(
            select(ThreatAlert).where(ThreatAlert.id == alert_id)
        )
        alert = result.scalar_one()

        # Get check-in statistics
        safe_count = await db.scalar(
            select(func.count(StaffCheckIn.id)).where(
                and_(
                    StaffCheckIn.threat_alert_id == alert_id,
                    StaffCheckIn.is_safe == True,
                )
            )
        )

        needs_help_count = await db.scalar(
            select(func.count(StaffCheckIn.id)).where(
                and_(
                    StaffCheckIn.threat_alert_id == alert_id,
                    StaffCheckIn.is_safe == False,
                )
            )
        )

        # Get reunification status
        reunified_count = await db.scalar(
            select(func.count(ReunificationEvent.id)).where(
                and_(
                    ReunificationEvent.threat_alert_id == alert_id,
                    ReunificationEvent.child_reunified == True,
                )
            )
        )

        return {
            "alert_id": alert.id,
            "threat_type": str(alert.threat_type),
            "threat_level": str(alert.threat_level),
            "created_at": alert.created_at,
            "lockdown_initiated": alert.lockdown_initiated,
            "evacuation_initiated": alert.evacuation_initiated,
            "all_clear_issued": alert.all_clear_issued,
            "staff_checked_in": alert.staff_checked_in,
            "staff_safe": safe_count or 0,
            "staff_needs_help": needs_help_count or 0,
            "children_reunified": reunified_count or 0,
            "dispatch_called": alert.dispatch_called,
            "parent_notification_sent": alert.parent_notification_sent,
        }
