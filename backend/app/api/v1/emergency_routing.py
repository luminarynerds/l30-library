# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Emergency Routing API Endpoints

After-hours emergency incident management:
- POST /incidents - Report new emergency
- GET /incidents - List incidents
- GET /incidents/{id} - Get incident details
- PATCH /incidents/{id} - Update incident
- POST /incidents/{id}/resolve - Mark as resolved
- GET /building-status - Get current building status
- POST /building-status - Update building status
- POST /emergency-contacts - Manage contacts
- GET /oncall-manager - Get current on-call manager
- POST /followups - Create follow-up task
- GET /followups - List pending follow-ups
- GET /dashboard - Emergency routing dashboard
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .dependencies import get_db, get_current_user, require_staff
from ...models.user import User
from ...models.emergency_routing import (
    BuildingStatus, EmergencyContact, IncidentSeverity, ContactType, FollowUpStatus
)
from ...schemas.emergency_routing import (
    BuildingStatusUpdate, BuildingStatusQueryResponse, BuildingStatusLogResponse,
    EmergencyIncidentCreate, EmergencyIncidentUpdate, EmergencyIncidentResponse,
    EmergencyIncidentListResponse, EmergencyContactCreate, EmergencyContactResponse,
    OnCallScheduleCreate, OnCallScheduleResponse, CurrentOnCallManager,
    IncidentFollowUpCreate, IncidentFollowUpUpdate, IncidentFollowUpResponse,
    SystemSecurityCheckCreate, SystemSecurityCheckResponse,
    EmergencyRoutingDashboard
)
from ...services.emergency_routing_service import EmergencyRoutingService

router = APIRouter(prefix="/emergency", tags=["emergency-routing"])


# ============================================================================
# Building Status Endpoints
# ============================================================================


@router.get(
    "/building-status",
    response_model=BuildingStatusQueryResponse,
    summary="Get current building status",
    description="Get the current building status (open/closed) and recent history"
)
async def get_building_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get current building operational status."""
    current_status = await EmergencyRoutingService.get_building_status(db)
    history = await EmergencyRoutingService.get_building_status_history(db, limit=5)

    status_log_responses = [
        BuildingStatusLogResponse.model_validate(log) for log in history
    ]

    return BuildingStatusQueryResponse(
        current_status=current_status.status if current_status else BuildingStatus.OPEN,
        status_changed_at=current_status.created_at if current_status else None,
        changed_by_id=current_status.changed_by_id if current_status else None,
        recent_history=status_log_responses
    )


@router.post(
    "/building-status",
    response_model=BuildingStatusLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Update building status",
    description="Update building status (open, closing, closed, emergency)"
)
async def update_building_status(
    status_update: BuildingStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update building operational status."""
    log = await EmergencyRoutingService.update_building_status(
        db,
        status_update.status,
        changed_by_id=current_user.id,
        reason=status_update.reason
    )
    await db.commit()
    return BuildingStatusLogResponse.model_validate(log)


# ============================================================================
# Emergency Incident Endpoints
# ============================================================================


@router.post(
    "/incidents",
    response_model=EmergencyIncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report emergency incident",
    description="Report a new emergency incident (intrusion, fire, alarm, etc.)"
)
async def create_emergency_incident(
    incident_create: EmergencyIncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Report new emergency incident."""
    incident = await EmergencyRoutingService.create_incident(
        db,
        incident_create,
        reported_by_id=current_user.id if current_user else None
    )

    # Send notifications based on response type
    contacts = await EmergencyRoutingService.get_response_contacts(
        db, incident.response_type
    )

    if contacts:
        await EmergencyRoutingService.send_notifications(db, incident.id, contacts)

    await db.commit()
    return EmergencyIncidentResponse.model_validate(incident)


@router.get(
    "/incidents",
    response_model=List[EmergencyIncidentListResponse],
    summary="List emergency incidents",
    description="List emergency incidents (filtered to unresolved by default)"
)
async def list_incidents(
    resolved: Optional[bool] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List emergency incidents."""
    if resolved is None:
        incidents = await EmergencyRoutingService.get_unresolved_incidents(db, limit)
    else:
        # For resolved filtering, need custom query
        incidents = await EmergencyRoutingService.get_recent_incidents(db, limit)

    return [EmergencyIncidentListResponse.model_validate(i) for i in incidents]


@router.get(
    "/incidents/{incident_id}",
    response_model=EmergencyIncidentResponse,
    summary="Get incident details",
    description="Get detailed information about a specific incident"
)
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get incident details."""
    incident = await EmergencyRoutingService.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found"
        )
    return EmergencyIncidentResponse.model_validate(incident)


@router.patch(
    "/incidents/{incident_id}",
    response_model=EmergencyIncidentResponse,
    summary="Update incident",
    description="Update incident information or status"
)
async def update_incident(
    incident_id: int,
    update: EmergencyIncidentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update incident information."""
    incident = await EmergencyRoutingService.update_incident(db, incident_id, update)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found"
        )
    await db.commit()
    return EmergencyIncidentResponse.model_validate(incident)


@router.post(
    "/incidents/{incident_id}/resolve",
    response_model=EmergencyIncidentResponse,
    summary="Resolve incident",
    description="Mark incident as resolved with completion notes"
)
async def resolve_incident(
    incident_id: int,
    resolution_notes: str = "Incident resolved",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Mark incident as resolved."""
    incident = await EmergencyRoutingService.resolve_incident(
        db,
        incident_id,
        resolution_notes,
        resolved_by_id=current_user.id
    )
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found"
        )
    await db.commit()
    return EmergencyIncidentResponse.model_validate(incident)


# ============================================================================
# Emergency Contact Endpoints
# ============================================================================


@router.post(
    "/emergency-contacts",
    response_model=EmergencyContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create emergency contact",
    description="Add new emergency contact (security, police, manager, etc.)"
)
async def create_emergency_contact(
    contact_create: EmergencyContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create new emergency contact."""
    from ...models.emergency_routing import EmergencyContact
    contact = EmergencyContact(**contact_create.model_dump())
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return EmergencyContactResponse.model_validate(contact)


@router.get(
    "/emergency-contacts",
    response_model=List[EmergencyContactResponse],
    summary="List emergency contacts",
    description="Get list of emergency contacts"
)
async def list_emergency_contacts(
    contact_type: Optional[ContactType] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List emergency contacts."""
    if contact_type:
        contacts = await EmergencyRoutingService.get_emergency_contacts_by_type(
            db, contact_type
        )
    else:
        from sqlalchemy import select
        result = await db.execute(select(EmergencyContact))
        contacts = result.scalars().all()

    return [EmergencyContactResponse.model_validate(c) for c in contacts]


# ============================================================================
# On-Call Manager Endpoints
# ============================================================================


@router.get(
    "/oncall-manager",
    response_model=Optional[CurrentOnCallManager],
    summary="Get current on-call manager",
    description="Get the manager currently on-call for emergency notifications"
)
async def get_oncall_manager(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get current on-call manager."""
    result = await EmergencyRoutingService.get_current_oncall_manager(db)
    if not result:
        return None

    schedule, _, manager = result
    return CurrentOnCallManager(
        schedule_id=schedule.id,
        manager_id=manager.id,
        manager_name=f"{manager.first_name} {manager.last_name}",
        escalation_level=schedule.escalation_level,
        phone=schedule.phone_override or manager.phone or "",
        email=schedule.email_override or manager.email,
        is_available=True
    )


@router.post(
    "/oncall-schedules",
    response_model=OnCallScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create on-call schedule",
    description="Create new on-call manager schedule"
)
async def create_oncall_schedule(
    schedule_create: OnCallScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create on-call schedule."""
    schedule = await EmergencyRoutingService.create_oncall_schedule(
        db,
        schedule_create.manager_id,
        schedule_create.start_date,
        schedule_create.end_date,
        schedule_create.escalation_level,
        schedule_create.phone_override,
        schedule_create.email_override,
        schedule_create.notes
    )
    await db.commit()
    return OnCallScheduleResponse.model_validate(schedule)


# ============================================================================
# Follow-Up Task Endpoints
# ============================================================================


@router.post(
    "/followups",
    response_model=IncidentFollowUpResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create follow-up task",
    description="Create next-day follow-up task for incident"
)
async def create_followup(
    followup_create: IncidentFollowUpCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create follow-up task."""
    followup = await EmergencyRoutingService.create_followup(db, followup_create)
    await db.commit()
    return IncidentFollowUpResponse.model_validate(followup)


@router.get(
    "/followups",
    response_model=List[IncidentFollowUpResponse],
    summary="List follow-up tasks",
    description="Get list of pending follow-up tasks"
)
async def list_followups(
    assigned_to_me: bool = False,
    status_filter: Optional[FollowUpStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List follow-up tasks."""
    assigned_to_id = current_user.id if assigned_to_me else None
    followups = await EmergencyRoutingService.get_pending_followups(db, assigned_to_id)

    if status_filter:
        followups = [f for f in followups if f.status == status_filter]

    return [IncidentFollowUpResponse.model_validate(f) for f in followups]


@router.patch(
    "/followups/{followup_id}",
    response_model=IncidentFollowUpResponse,
    summary="Update follow-up task",
    description="Update follow-up task status or details"
)
async def update_followup(
    followup_id: int,
    update: IncidentFollowUpUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update follow-up task."""
    from sqlalchemy import select
    from ...models.emergency_routing import IncidentFollowUp

    result = await db.execute(
        select(IncidentFollowUp).where(IncidentFollowUp.id == followup_id)
    )
    followup = result.scalars().first()

    if not followup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Follow-up task {followup_id} not found"
        )

    update_dict = update.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        if value is not None:
            setattr(followup, field, value)

    await db.commit()
    await db.refresh(followup)
    return IncidentFollowUpResponse.model_validate(followup)


# ============================================================================
# System Security Endpoints
# ============================================================================


@router.post(
    "/security-check",
    response_model=SystemSecurityCheckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create security check",
    description="Log door lock, camera, and alarm system status"
)
async def create_security_check(
    check_create: SystemSecurityCheckCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create system security check."""
    check = await EmergencyRoutingService.create_security_check(
        db, check_create, verified_by_id=current_user.id
    )
    await db.commit()
    return SystemSecurityCheckResponse.model_validate(check)


@router.get(
    "/security-check/latest",
    response_model=Optional[SystemSecurityCheckResponse],
    summary="Get latest security check",
    description="Get most recent system security status"
)
async def get_latest_security_check(
    incident_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get latest security check."""
    check = await EmergencyRoutingService.get_latest_security_check(db, incident_id)
    if not check:
        return None
    return SystemSecurityCheckResponse.model_validate(check)


# ============================================================================
# Dashboard Endpoint
# ============================================================================


@router.get(
    "/dashboard",
    response_model=EmergencyRoutingDashboard,
    summary="Emergency routing dashboard",
    description="Overall emergency response status and recent incidents"
)
async def get_emergency_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get emergency routing dashboard."""
    building_status = await EmergencyRoutingService.get_building_status(db)
    active_count = await EmergencyRoutingService.get_active_incidents_count(db)
    pending_count = await EmergencyRoutingService.get_pending_followups_count(db)
    oncall = await EmergencyRoutingService.get_current_oncall_manager(db)
    recent = await EmergencyRoutingService.get_recent_incidents(db, limit=5)
    security_check = await EmergencyRoutingService.get_latest_security_check(db)

    oncall_manager = None
    if oncall:
        schedule, _, manager = oncall
        oncall_manager = CurrentOnCallManager(
            schedule_id=schedule.id,
            manager_id=manager.id,
            manager_name=f"{manager.first_name} {manager.last_name}",
            escalation_level=schedule.escalation_level,
            phone=schedule.phone_override or manager.phone or "",
            email=schedule.email_override or manager.email,
            is_available=True
        )

    return EmergencyRoutingDashboard(
        current_building_status=building_status.status if building_status else BuildingStatus.OPEN,
        active_incidents_count=active_count,
        unresolved_incidents_count=active_count,
        pending_followups_count=pending_count,
        current_oncall_manager=oncall_manager,
        system_security_status=security_check.model_dump() if security_check else None,
        recent_incidents=[
            EmergencyIncidentListResponse.model_validate(i) for i in recent
        ]
    )
