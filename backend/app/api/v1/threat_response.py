# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Active Threat Response API Endpoints

Provides endpoints for:
- Initiating threat alerts
- Managing staff check-ins (I'm safe button)
- Evacuation procedures
- Reunification tracking
- Parent notifications
- Media response coordination
- All-clear announcements

Restricted to staff/admin/director roles.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.threat_response import (
    ThreatAlert,
    ThreatLevel,
    ThreatType,
    StaffCheckIn,
    EvacuationRoute,
    RallyPoint,
)
from ...models.user import User, UserRole
from ...services.threat_response_service import ThreatResponseService
from .dependencies import require_staff, require_director

router = APIRouter(prefix="/threat-response", tags=["threat-response"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class InitiateThreatAlertRequest(BaseModel):
    threat_type: ThreatType
    threat_level: ThreatLevel
    branch_id: int
    description: str
    location_description: Optional[str] = None
    external_information: Optional[str] = None


class ThreatAlertResponse(BaseModel):
    id: int
    threat_type: str
    threat_level: str
    branch_id: int
    location_description: Optional[str]
    dispatch_called: bool
    dispatch_time: Optional[datetime]
    lockdown_initiated: bool
    lockdown_time: Optional[datetime]
    evacuation_initiated: bool
    evacuation_time: Optional[datetime]
    staff_checked_in: int
    staff_checked_in_safe: int
    children_present: bool
    parent_notification_sent: bool
    all_clear_issued: bool
    created_at: datetime

    class Config:
        from_attributes = True


class StaffCheckInRequest(BaseModel):
    is_safe: bool
    location: Optional[str] = None
    notes: Optional[str] = None


class StaffCheckInResponse(BaseModel):
    id: int
    threat_alert_id: int
    user_id: int
    is_safe: bool
    location: Optional[str]
    notes: Optional[str]
    checked_in_at: datetime

    class Config:
        from_attributes = True


class EvacuationInitiateRequest(BaseModel):
    evacuation_route_id: int
    rally_point_id: int


class EvacuationRouteResponse(BaseModel):
    id: int
    route_name: str
    description: Optional[str]
    starting_point: str
    exit_point: str
    rally_point_id: Optional[int]
    waypoints: list = []
    estimated_duration_seconds: Optional[int]
    capacity: Optional[int]

    class Config:
        from_attributes = True


class RallyPointResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    latitude: float
    longitude: float
    address: Optional[str]
    max_capacity: Optional[int]
    covered: bool
    assembly_instructions: Optional[str]
    is_primary: bool

    class Config:
        from_attributes = True


class ReunifyChildRequest(BaseModel):
    child_patron_id: int
    parent_patron_id: Optional[int] = None
    parent_contact_name: str
    parent_contact_phone: str
    reunified_with: str
    id_verified: bool = False


class IssuAllClearRequest(BaseModel):
    pass


class ThreatStatusResponse(BaseModel):
    alert_id: int
    threat_type: str
    threat_level: str
    created_at: datetime
    lockdown_initiated: bool
    evacuation_initiated: bool
    all_clear_issued: bool
    staff_checked_in: int
    staff_safe: int
    staff_needs_help: int
    children_reunified: int
    dispatch_called: bool
    parent_notification_sent: bool


# =============================================================================
# API Endpoints
# =============================================================================


@router.post(
    "/alerts",
    response_model=ThreatAlertResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def initiate_threat_alert(
    request: Request,
    body: InitiateThreatAlertRequest,
    current_user: User = Depends(require_director),
    db: AsyncSession = Depends(get_db),
) -> ThreatAlert:
    """
    Initiate an active threat alert at a facility.

    **CRITICAL**: This endpoint initiates:
    - Automatic 911 emergency dispatch
    - Facility lockdown (if SHELTER_IN_PLACE)
    - Staff notification
    - Alert tracking and accountability

    Requires DIRECTOR role (not just STAFF).
    Rate limited to 5 per minute (prevents accidental triggers).
    """
    alert = await ThreatResponseService.initiate_threat_alert(
        db=db,
        threat_type=body.threat_type,
        threat_level=body.threat_level,
        branch_id=body.branch_id,
        created_by_id=current_user.id,
        description=body.description,
        location_description=body.location_description,
        external_information=body.external_information,
    )

    return alert


@router.post(
    "/alerts/{alert_id}/lockdown",
    response_model=ThreatAlertResponse,
)
@limiter.limit("10/minute")
async def initiate_lockdown(
    request: Request,
    alert_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> ThreatAlert:
    """
    Initiate lockdown procedures for a threat alert.

    Broadcasts lockdown orders to all staff and patrons.
    """
    alert = await ThreatResponseService.initiate_lockdown(db, alert_id)
    return alert


@router.post(
    "/alerts/{alert_id}/staff-checkin",
    response_model=StaffCheckInResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def staff_check_in(
    request: Request,
    alert_id: int,
    body: StaffCheckInRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> StaffCheckIn:
    """
    Staff member checks in with "I'm safe" status.

    This is the critical accountability mechanism during threats.
    Each staff member should check in when in a safe location.
    """
    checkin = await ThreatResponseService.staff_check_in(
        db=db,
        alert_id=alert_id,
        user_id=current_user.id,
        is_safe=body.is_safe,
        location=body.location,
        notes=body.notes,
    )

    return checkin


@router.get(
    "/branches/{branch_id}/evacuation-routes",
    response_model=list[EvacuationRouteResponse],
)
async def get_evacuation_routes(
    branch_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> list[EvacuationRoute]:
    """Get active evacuation routes for a branch."""
    routes = await ThreatResponseService.get_evacuation_routes(db, branch_id)
    return routes


@router.get(
    "/branches/{branch_id}/rally-points",
    response_model=list[RallyPointResponse],
)
async def get_rally_points(
    branch_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> list[RallyPoint]:
    """Get rally point locations for a branch."""
    points = await ThreatResponseService.get_rally_points(db, branch_id)
    return points


@router.post(
    "/alerts/{alert_id}/evacuate",
    response_model=dict,
)
@limiter.limit("10/minute")
async def initiate_evacuation(
    request: Request,
    alert_id: int,
    body: EvacuationInitiateRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Initiate evacuation procedures.

    Broadcasts evacuation orders and directs all personnel to
    evacuation routes and rally points.
    """
    evac = await ThreatResponseService.initiate_evacuation(
        db=db,
        alert_id=alert_id,
        evacuation_route_id=body.evacuation_route_id,
        rally_point_id=body.rally_point_id,
    )

    return {
        "id": evac.id,
        "threat_alert_id": evac.threat_alert_id,
        "evacuation_route_id": evac.evacuation_route_id,
        "rally_point_id": evac.rally_point_id,
        "evacuation_initiated_at": evac.evacuation_initiated_at,
    }


@router.post(
    "/alerts/{alert_id}/reunify",
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def reunify_child(
    request: Request,
    alert_id: int,
    body: ReunifyChildRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Record reunification of child with parent/guardian.

    Tracks ID verification and reunification for reunification
    process documentation.
    """
    event = await ThreatResponseService.reunify_child_with_guardian(
        db=db,
        alert_id=alert_id,
        child_patron_id=body.child_patron_id,
        parent_patron_id=body.parent_patron_id,
        parent_contact_name=body.parent_contact_name,
        parent_contact_phone=body.parent_contact_phone,
        reunified_with=body.reunified_with,
        id_verified=body.id_verified,
    )

    return {
        "id": event.id,
        "child_patron_id": event.child_patron_id,
        "reunified_with": event.reunified_with,
        "reunification_time": event.reunification_time,
    }


@router.post(
    "/alerts/{alert_id}/notify-parents",
)
@limiter.limit("10/minute")
async def notify_parents(
    request: Request,
    alert_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send notifications to parents about reunification procedures."""
    await ThreatResponseService.send_parent_notification(db, alert_id)

    return {"status": "Parent notifications queued"}


@router.post(
    "/alerts/{alert_id}/media-statement",
)
@limiter.limit("10/minute")
async def issue_media_statement(
    request: Request,
    alert_id: int,
    statement: Optional[str] = None,
    current_user: User = Depends(require_director),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Issue media response statement during threat incident."""
    await ThreatResponseService.issue_media_statement(db, alert_id, statement)

    return {"status": "Media statement issued"}


@router.post(
    "/alerts/{alert_id}/all-clear",
)
@limiter.limit("5/minute")
async def issue_all_clear(
    request: Request,
    alert_id: int,
    body: IssuAllClearRequest,
    current_user: User = Depends(require_director),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Issue all-clear announcement after threat is resolved.

    Broadcasts all-clear to all staff, patrons, and parent guardians
    via intercom, email, SMS, and app notifications.
    """
    announcement = await ThreatResponseService.issue_all_clear(
        db=db,
        alert_id=alert_id,
        announced_by_id=current_user.id,
    )

    return {
        "id": announcement.id,
        "threat_alert_id": announcement.threat_alert_id,
        "announced_at": announcement.announced_at,
        "announcement_text": announcement.announcement_text,
    }


@router.get(
    "/alerts/{alert_id}/status",
    response_model=ThreatStatusResponse,
)
async def get_threat_status(
    alert_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current status and accountability metrics for a threat alert."""
    status_data = await ThreatResponseService.get_threat_alert_status(db, alert_id)

    return ThreatStatusResponse(**status_data)
