# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc

from ..models.emergency_routing import (
    BuildingStatus, BuildingStatusLog, IncidentType, IncidentSeverity,
    ResponseType, ContactType, FollowUpStatus, EmergencyIncident,
    EmergencyContact, OnCallSchedule, EmergencyNotification,
    IncidentFollowUp, SystemSecurityCheck
)
from ..models.user import User
from ..schemas.emergency_routing import (
    EmergencyIncidentCreate, EmergencyIncidentUpdate,
    IncidentFollowUpCreate, SystemSecurityCheckCreate
)

logger = get_logger(__name__)


class EmergencyRoutingService:

    # ========================================================================
    # Building Status Management
    # ========================================================================

    @staticmethod
    async def get_building_status(session: AsyncSession) -> Optional[BuildingStatusLog]:
        query = select(BuildingStatusLog).order_by(
            desc(BuildingStatusLog.created_at)
        ).limit(1)
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def update_building_status(
        session: AsyncSession,
        new_status: BuildingStatus,
        changed_by_id: Optional[int] = None,
        reason: Optional[str] = None
    ) -> BuildingStatusLog:
        status_log = BuildingStatusLog(
            status=new_status,
            changed_by_id=changed_by_id,
            reason=reason,
            created_at=datetime.now(timezone.utc)
        )
        session.add(status_log)
        await session.flush()
        logger.info(
            f"Building status changed to {new_status} by user {changed_by_id}: {reason}"
        )
        return status_log

    @staticmethod
    async def get_building_status_history(
        session: AsyncSession,
        limit: int = 10
    ) -> List[BuildingStatusLog]:
        query = select(BuildingStatusLog).order_by(
            desc(BuildingStatusLog.created_at)
        ).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def is_building_closed(session: AsyncSession) -> bool:
        status = await EmergencyRoutingService.get_building_status(session)
        return status and status.status in [
            BuildingStatus.CLOSED,
            BuildingStatus.EMERGENCY
        ]

    # ========================================================================
    # Emergency Incident Management
    # ========================================================================

    @staticmethod
    async def determine_response_type(
        incident_type: IncidentType,
        severity: IncidentSeverity,
        is_building_closed: bool
    ) -> ResponseType:
        if severity == IncidentSeverity.CRITICAL:
            return ResponseType.POLICE_EMERGENCY

        if severity == IncidentSeverity.HIGH:
            if is_building_closed:
                return ResponseType.COMBINED  # Security + Police
            return ResponseType.POLICE_NONEMERGENCY

        if severity == IncidentSeverity.MEDIUM:
            if is_building_closed:
                return ResponseType.SECURITY_COMPANY
            return ResponseType.INTERNAL_ONLY

        return ResponseType.INTERNAL_ONLY

    @staticmethod
    async def create_incident(
        session: AsyncSession,
        incident_create: EmergencyIncidentCreate,
        reported_by_id: Optional[int] = None
    ) -> EmergencyIncident:
        # Determine if building is closed
        is_closed = await EmergencyRoutingService.is_building_closed(session)

        # Determine response type
        response_type = await EmergencyRoutingService.determine_response_type(
            incident_create.incident_type,
            incident_create.severity,
            is_closed
        )

        # Get current building status
        building_status = await EmergencyRoutingService.get_building_status(session)
        current_status = building_status.status if building_status else BuildingStatus.OPEN

        # Create incident record
        incident = EmergencyIncident(
            incident_type=incident_create.incident_type,
            severity=incident_create.severity,
            response_type=response_type,
            location_description=incident_create.location_description,
            building_status_at_incident=current_status,
            reported_by_id=reported_by_id,
            reporter_name=incident_create.reporter_name,
            reporter_contact=incident_create.reporter_contact,
            description=incident_create.description,
            camera_footage_available=incident_create.camera_footage_available,
            camera_footage_urls=incident_create.camera_footage_urls,
            alarm_triggered=incident_create.alarm_triggered,
            alarm_panel_id=incident_create.alarm_panel_id,
            doors_unlocked_count=incident_create.doors_unlocked_count,
            door_status_details=incident_create.door_status_details or {},
            additional_details=incident_create.additional_details or {},
            created_at=datetime.now(timezone.utc)
        )

        session.add(incident)
        await session.flush()

        logger.info(
            f"Emergency incident created: {incident.id} "
            f"Type={incident.incident_type}, Severity={incident.severity}, "
            f"Response={response_type}"
        )

        return incident

    @staticmethod
    async def get_incident(
        session: AsyncSession,
        incident_id: int
    ) -> Optional[EmergencyIncident]:
        query = select(EmergencyIncident).where(
            EmergencyIncident.id == incident_id
        )
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def get_unresolved_incidents(
        session: AsyncSession,
        limit: int = 50
    ) -> List[EmergencyIncident]:
        query = select(EmergencyIncident).where(
            EmergencyIncident.resolved == False
        ).order_by(
            desc(EmergencyIncident.created_at)
        ).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_incident(
        session: AsyncSession,
        incident_id: int,
        update_data: EmergencyIncidentUpdate
    ) -> Optional[EmergencyIncident]:
        incident = await EmergencyRoutingService.get_incident(session, incident_id)
        if not incident:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if value is not None:
                setattr(incident, field, value)

        incident.updated_at = datetime.now(timezone.utc)
        await session.flush()

        logger.info(f"Incident {incident_id} updated with: {update_dict}")
        return incident

    @staticmethod
    async def resolve_incident(
        session: AsyncSession,
        incident_id: int,
        resolution_notes: str,
        resolved_by_id: Optional[int] = None
    ) -> Optional[EmergencyIncident]:
        incident = await EmergencyRoutingService.get_incident(session, incident_id)
        if not incident:
            return None

        incident.resolved = True
        incident.resolution_notes = resolution_notes
        incident.resolved_by_id = resolved_by_id
        incident.resolved_at = datetime.now(timezone.utc)
        incident.updated_at = datetime.now(timezone.utc)

        await session.flush()
        logger.info(f"Incident {incident_id} resolved: {resolution_notes}")
        return incident

    # ========================================================================
    # Emergency Contact Management
    # ========================================================================

    @staticmethod
    async def get_emergency_contacts_by_type(
        session: AsyncSession,
        contact_type: ContactType
    ) -> List[EmergencyContact]:
        query = select(EmergencyContact).where(
            and_(
                EmergencyContact.contact_type == contact_type,
                EmergencyContact.is_active == True
            )
        ).order_by(EmergencyContact.escalation_level)
        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_response_contacts(
        session: AsyncSession,
        response_type: ResponseType
    ) -> List[EmergencyContact]:
        contacts = []

        contact_type_map = {
            ResponseType.SECURITY_COMPANY: [ContactType.SECURITY_PRIMARY, ContactType.SECURITY_BACKUP],
            ResponseType.POLICE_NONEMERGENCY: [ContactType.POLICE_NONEMERGENCY],
            ResponseType.POLICE_EMERGENCY: [ContactType.POLICE_DISPATCH],
            ResponseType.INTERNAL_ONLY: [ContactType.MANAGER_ONCALL],
            ResponseType.COMBINED: [
                ContactType.SECURITY_PRIMARY,
                ContactType.MANAGER_ONCALL
            ]
        }

        for contact_type in contact_type_map.get(response_type, []):
            type_contacts = await EmergencyRoutingService.get_emergency_contacts_by_type(
                session, contact_type
            )
            contacts.extend(type_contacts)

        return contacts

    # ========================================================================
    # On-Call Manager Management
    # ========================================================================

    @staticmethod
    async def get_current_oncall_manager(
        session: AsyncSession
    ) -> Optional[Tuple[OnCallSchedule, EmergencyContact, User]]:
        now = datetime.now(timezone.utc)
        query = select(OnCallSchedule).where(
            and_(
                OnCallSchedule.start_date <= now,
                OnCallSchedule.end_date >= now
            )
        ).order_by(OnCallSchedule.escalation_level).limit(1)
        result = await session.execute(query)
        schedule = result.scalars().first()

        if not schedule:
            return None

        # Load manager user
        manager_query = select(User).where(User.id == schedule.manager_id)
        manager_result = await session.execute(manager_query)
        manager = manager_result.scalars().first()

        return (schedule, None, manager)  # Contact would be from schedule or manager

    @staticmethod
    async def create_oncall_schedule(
        session: AsyncSession,
        manager_id: int,
        start_date: datetime,
        end_date: datetime,
        escalation_level: int = 1,
        phone_override: Optional[str] = None,
        email_override: Optional[str] = None,
        notes: Optional[str] = None
    ) -> OnCallSchedule:
        schedule = OnCallSchedule(
            manager_id=manager_id,
            start_date=start_date,
            end_date=end_date,
            escalation_level=escalation_level,
            phone_override=phone_override,
            email_override=email_override,
            notes=notes,
            created_at=datetime.now(timezone.utc)
        )
        session.add(schedule)
        await session.flush()
        logger.info(f"On-call schedule created for manager {manager_id}")
        return schedule

    # ========================================================================
    # Emergency Notification Management
    # ========================================================================

    @staticmethod
    async def create_notification(
        session: AsyncSession,
        incident_id: int,
        contact: EmergencyContact,
        notification_type: str = "sms"
    ) -> EmergencyNotification:
        notification = EmergencyNotification(
            incident_id=incident_id,
            contact_id=contact.id,
            recipient_name=contact.name,
            recipient_phone=contact.phone_number,
            recipient_email=contact.email,
            notification_type=notification_type,
            created_at=datetime.now(timezone.utc)
        )
        session.add(notification)
        await session.flush()
        logger.info(
            f"Notification created for {contact.name} ({contact.contact_type}) "
            f"for incident {incident_id}"
        )
        return notification

    @staticmethod
    async def send_notifications(
        session: AsyncSession,
        incident_id: int,
        contacts: List[EmergencyContact]
    ) -> List[EmergencyNotification]:
        notifications = []
        incident = await EmergencyRoutingService.get_incident(session, incident_id)

        if not incident:
            return []

        for contact in contacts:
            notification = await EmergencyRoutingService.create_notification(
                session, incident_id, contact
            )

            # In a real implementation, this would integrate with:
            # - SMS service
            # - Phone service (CallRail, etc.)
            # - Email service (Resend, etc.)

            notification.sent_successfully = True
            notification.sent_at = datetime.now(timezone.utc)

            notifications.append(notification)
            logger.info(f"Notification sent to {contact.name}")

        incident.response_initiated = True
        incident.response_initiated_at = datetime.now(timezone.utc)

        await session.flush()
        return notifications

    # ========================================================================
    # Follow-Up Task Management
    # ========================================================================

    @staticmethod
    async def create_followup(
        session: AsyncSession,
        followup_create: IncidentFollowUpCreate
    ) -> IncidentFollowUp:
        # Default due date is next business day if not specified
        due_date = followup_create.due_date or (
            datetime.now(timezone.utc) + timedelta(days=1)
        )

        followup = IncidentFollowUp(
            incident_id=followup_create.incident_id,
            task_description=followup_create.task_description,
            task_category=followup_create.task_category,
            assigned_to_id=followup_create.assigned_to_id,
            status=FollowUpStatus.PENDING,
            due_date=due_date,
            priority=followup_create.priority,
            estimated_hours=followup_create.estimated_hours,
            created_at=datetime.now(timezone.utc)
        )
        session.add(followup)
        await session.flush()
        logger.info(
            f"Follow-up task created for incident {followup_create.incident_id}: "
            f"{followup_create.task_description}"
        )
        return followup

    @staticmethod
    async def get_pending_followups(
        session: AsyncSession,
        assigned_to_id: Optional[int] = None
    ) -> List[IncidentFollowUp]:
        query = select(IncidentFollowUp).where(
            IncidentFollowUp.status == FollowUpStatus.PENDING
        )

        if assigned_to_id:
            query = query.where(IncidentFollowUp.assigned_to_id == assigned_to_id)

        query = query.order_by(desc(IncidentFollowUp.priority), IncidentFollowUp.due_date)
        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_followup_status(
        session: AsyncSession,
        followup_id: int,
        new_status: FollowUpStatus,
        completion_notes: Optional[str] = None,
        actual_hours: Optional[float] = None
    ) -> Optional[IncidentFollowUp]:
        query = select(IncidentFollowUp).where(IncidentFollowUp.id == followup_id)
        result = await session.execute(query)
        followup = result.scalars().first()

        if not followup:
            return None

        followup.status = new_status
        if completion_notes:
            followup.completion_notes = completion_notes
        if actual_hours is not None:
            followup.actual_hours = actual_hours

        if new_status == FollowUpStatus.COMPLETED:
            followup.completed_at = datetime.now(timezone.utc)

        followup.updated_at = datetime.now(timezone.utc)
        await session.flush()

        logger.info(f"Follow-up task {followup_id} status updated to {new_status}")
        return followup

    # ========================================================================
    # System Security Checks
    # ========================================================================

    @staticmethod
    async def create_security_check(
        session: AsyncSession,
        check_create: SystemSecurityCheckCreate,
        verified_by_id: Optional[int] = None
    ) -> SystemSecurityCheck:
        check = SystemSecurityCheck(
            incident_id=check_create.incident_id,
            all_doors_locked=check_create.all_doors_locked,
            cameras_operational=check_create.cameras_operational,
            alarm_armed=check_create.alarm_armed,
            alarm_triggered=check_create.alarm_triggered,
            door_status=check_create.door_status or {},
            camera_status=check_create.camera_status or {},
            alarm_status_details=check_create.alarm_status_details or {},
            verified_at=datetime.now(timezone.utc),
            verified_by_id=verified_by_id,
            remote_access_available=check_create.remote_access_available,
            camera_review_url=check_create.camera_review_url,
            access_log_url=check_create.access_log_url,
            created_at=datetime.now(timezone.utc)
        )
        session.add(check)
        await session.flush()
        logger.info("System security check created")
        return check

    @staticmethod
    async def get_latest_security_check(
        session: AsyncSession,
        incident_id: Optional[int] = None
    ) -> Optional[SystemSecurityCheck]:
        query = select(SystemSecurityCheck).order_by(
            desc(SystemSecurityCheck.created_at)
        )

        if incident_id:
            query = query.where(SystemSecurityCheck.incident_id == incident_id)

        query = query.limit(1)
        result = await session.execute(query)
        return result.scalars().first()

    # ========================================================================
    # Dashboard/Summary Methods
    # ========================================================================

    @staticmethod
    async def get_active_incidents_count(session: AsyncSession) -> int:
        query = select(EmergencyIncident).where(
            EmergencyIncident.resolved == False
        )
        result = await session.execute(query)
        incidents = result.scalars().all()
        return len(incidents)

    @staticmethod
    async def get_pending_followups_count(session: AsyncSession) -> int:
        query = select(IncidentFollowUp).where(
            IncidentFollowUp.status == FollowUpStatus.PENDING
        )
        result = await session.execute(query)
        followups = result.scalars().all()
        return len(followups)

    @staticmethod
    async def get_recent_incidents(
        session: AsyncSession,
        limit: int = 5
    ) -> List[EmergencyIncident]:
        query = select(EmergencyIncident).order_by(
            desc(EmergencyIncident.created_at)
        ).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()
