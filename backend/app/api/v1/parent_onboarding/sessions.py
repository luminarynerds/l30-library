# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Parent Onboarding API Endpoints

Provides endpoints for the 7-component parent onboarding system:
1. Welcome onboarding sessions (in-person intake)
2. Care coordinator assignments and check-ins
3. Resource guide management (hybrid CMS/i18n)
4. Emergency childcare sessions and registration
5. Parent connection groups
6. Social service enrollment facilitation
7. Home visit scheduling and tracking
"""
import contextlib
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....models.parent_onboarding import (
    CareCoordinatorAssignment, CareCoordinatorCheckIn,
    ChildcareRegistration, ChildcareRegistrationStatus, ChildcareSession,
    HomeVisitAccessNotes,
    ParentConnectionGroup, ParentConnectionGroupMeeting, ParentConnectionGroupMember,
    ParentHomeVisit, ParentOnboardingSession,
)
from ....models.user import User, UserRole
from ....schemas.parent_onboarding import (
    ArchiveGroupRequest, ArchiveGroupResponse,
    CancelMeetingRequest, CapacityConflictDetail,
    CareCheckInCreate, CareCheckInListResponse, CareCheckInResponse,
    CareCoordinatorAssignmentCreate, CareCoordinatorAssignmentListResponse,
    CareCoordinatorAssignmentResponse, CareCoordinatorAssignmentUpdate,
    ChildcareCheckoutRequest,
    ChildcareRegistrationCreate, ChildcareRegistrationResponse,
    ChildcareRegistrationUpdate,
    ChildcareRosterCounts, ChildcareRosterEntry, ChildcareRosterResponse,
    ChildcareSessionCreate, ChildcareSessionListResponse,
    ChildcareSessionResponse, ChildcareSessionUpdate,
    EnrollMemberResponse, GroupMemberDetailResponse,
    GroupMembersListResponse, GroupMeetingResponse, GroupMeetingsListResponse,
    MeetingDispatchResponse, RescheduleMeetingRequest, StaffEnrollRequest,
    ParentConnectionGroupCreate, ParentConnectionGroupListResponse,
    ParentConnectionGroupResponse, ParentConnectionGroupUpdate,
    ConfidentialJoinRequest, ConfidentialJoinRequestResponse,
    ApprovalQueueResponse, DecideRequestPayload, DecideRequestResponse,
    ParentHomeVisitComplete, ParentHomeVisitCreate,
    ParentHomeVisitListResponse, ParentHomeVisitResponse,
    ParentHomeVisitUpdate,
    HomeVisitCancelRequest, HomeVisitCompleteRequest, HomeVisitConfirmRequest,
    HomeVisitConflictItem, HomeVisitConflictResponse,
    HomeVisitRescheduleRequest, HomeVisitRescheduleResponse,
    HomeVisitSafetyCheckinRequest, HomeVisitSafetyResponse,
    HomeVisitStatusHistoryItem, HomeVisitStatusHistoryResponse,
    OverdueHomeVisitListResponse, OverdueHomeVisitSummary,
    DayPlanResponse, DayPlanSortPatch,
    GeocodeManualOverride,
    HomeVisitAccessNotesRead, HomeVisitAccessNotesUpsert,
    ParentOnboardingSessionComplete, ParentOnboardingSessionCreate,
    ParentOnboardingSessionListResponse, ParentOnboardingSessionResponse,
    ParentOnboardingSessionUpdate,
)
from ....services.organization_features_service import OrganizationFeaturesService
from ....services.parent_onboarding import (
    CareCoordinatorService, ChildcareService, ConnectionGroupService,
    HomeVisitSafetyService, HomeVisitService, InvalidHomeVisitTransitionError,
    ParentOnboardingSessionService, PickupNotAuthorized,
)
from ....services.organization_features_service import OrganizationFeaturesService
from ....services import home_visit_day_plan_service as day_plan_service
from ....services import pii_access_log_service
# pii_audit imported *after* models to avoid a known circular when this
# module is loaded before app.models.__init__ finishes resolving.
from ..auth import get_current_user
from ..dependencies import require_authenticated, require_library_admin, require_staff

router = APIRouter()


# ============================================================================
# Component 1: Welcome Onboarding Sessions
# ============================================================================

@router.post("/sessions", response_model=ParentOnboardingSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: ParentOnboardingSessionCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Schedule a new parent onboarding session (staff-only)."""
    session = await ParentOnboardingSessionService.create_session(db, data.model_dump())
    return ParentOnboardingSessionResponse.model_validate(session)


@router.get("/sessions", response_model=ParentOnboardingSessionListResponse)
async def list_sessions(
    status_filter: Optional[str] = Query(None, alias="status"),
    branch_id: Optional[int] = None,
    staff_id: Optional[int] = None,
    patron_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """List parent onboarding sessions."""
    sessions, total = await ParentOnboardingSessionService.list_sessions(
        db, status=status_filter, branch_id=branch_id,
        staff_id=staff_id, patron_id=patron_id, limit=limit, offset=offset,
    )
    return ParentOnboardingSessionListResponse(
        sessions=[ParentOnboardingSessionResponse.model_validate(s) for s in sessions],
        total=total, limit=limit, offset=offset,
    )


@router.get("/sessions/{session_id}", response_model=ParentOnboardingSessionResponse)
async def get_session(
    session_id: int,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific session."""
    session = await ParentOnboardingSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return ParentOnboardingSessionResponse.model_validate(session)


@router.patch("/sessions/{session_id}", response_model=ParentOnboardingSessionResponse)
async def update_session(
    session_id: int,
    data: ParentOnboardingSessionUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a session (staff-only)."""
    session = await ParentOnboardingSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(session, key, value)
    await db.flush()
    await db.refresh(session)
    return ParentOnboardingSessionResponse.model_validate(session)


@router.post("/sessions/{session_id}/complete", response_model=ParentOnboardingSessionResponse)
async def complete_session(
    session_id: int,
    data: ParentOnboardingSessionComplete,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Mark a session as completed with outcomes (staff-only)."""
    session = await ParentOnboardingSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # exclude_unset: fields the caller didn't send stay untouched instead of
    # being reset to the schema default (e.g. needs_identified back to []),
    # which previously clobbered data set by an earlier PATCH.
    session = await ParentOnboardingSessionService.complete_session(
        db, session, data.model_dump(exclude_unset=True),
    )
    return ParentOnboardingSessionResponse.model_validate(session)


# ============================================================================
# Component 2: Care Coordinator
# ============================================================================

@router.post("/care-assignments", response_model=CareCoordinatorAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_care_assignment(
    data: CareCoordinatorAssignmentCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Assign a care coordinator to a family (staff-only)."""
    assignment = await CareCoordinatorService.create_assignment(db, data.model_dump())
    return CareCoordinatorAssignmentResponse.model_validate(assignment)


@router.get("/care-assignments", response_model=CareCoordinatorAssignmentListResponse)
async def list_care_assignments(
    status_filter: Optional[str] = Query(None, alias="status"),
    coordinator_id: Optional[int] = None,
    patron_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List care coordinator assignments (staff-only)."""
    assignments, total = await CareCoordinatorService.list_assignments(
        db, status=status_filter, coordinator_id=coordinator_id,
        patron_id=patron_id, limit=limit, offset=offset,
    )
    return CareCoordinatorAssignmentListResponse(
        assignments=[CareCoordinatorAssignmentResponse.model_validate(a) for a in assignments],
        total=total, limit=limit, offset=offset,
    )


@router.get("/care-assignments/{assignment_id}", response_model=CareCoordinatorAssignmentResponse)
async def get_care_assignment(
    assignment_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific care assignment with check-in history (staff-only)."""
    assignment = await CareCoordinatorService.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return CareCoordinatorAssignmentResponse.model_validate(assignment)


@router.patch("/care-assignments/{assignment_id}", response_model=CareCoordinatorAssignmentResponse)
async def update_care_assignment(
    assignment_id: int,
    data: CareCoordinatorAssignmentUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a care assignment (staff-only)."""
    assignment = await CareCoordinatorService.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(assignment, key, value)
    await db.flush()
    await db.refresh(assignment)
    return CareCoordinatorAssignmentResponse.model_validate(assignment)


@router.post("/care-assignments/{assignment_id}/check-ins", response_model=CareCheckInResponse, status_code=status.HTTP_201_CREATED)
async def create_check_in(
    assignment_id: int,
    data: CareCheckInCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Log a check-in for a care assignment (staff-only)."""
    assignment = await CareCoordinatorService.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    check_in = await CareCoordinatorService.create_check_in(db, assignment_id, data.model_dump())
    return CareCheckInResponse.model_validate(check_in)


@router.get("/care-assignments/{assignment_id}/check-ins", response_model=CareCheckInListResponse)
async def list_check_ins(
    assignment_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List check-ins for a care assignment (staff-only)."""
    result = await db.execute(
        select(CareCoordinatorCheckIn)
        .where(CareCoordinatorCheckIn.assignment_id == assignment_id)
        .order_by(CareCoordinatorCheckIn.scheduled_date.desc())
        .limit(limit).offset(offset)
    )
    check_ins = list(result.scalars().all())
    from sqlalchemy import func as sqlfunc
    total = (await db.execute(
        select(sqlfunc.count(CareCoordinatorCheckIn.id))
        .where(CareCoordinatorCheckIn.assignment_id == assignment_id)
    )).scalar() or 0
    return CareCheckInListResponse(
        check_ins=[CareCheckInResponse.model_validate(c) for c in check_ins],
        total=total, limit=limit, offset=offset,
    )


# ============================================================================
# Component 3: Resource Guide — moved to resource_guide.py
# ============================================================================

# ============================================================================
# Component 6: Service Enrollments  →  service_enrollments.py
# ============================================================================

# ============================================================================
# Component 7: Home Visits
# ============================================================================


# ============================================================================
# Component 8: Session follow-ups + referrals
# ============================================================================
#
# Route ordering note:
#   FastAPI matches routes in registration order, so any literal session
#   subpath ("/sessions/{session_id}/followups") must register BEFORE
#   broader param routes that could shadow it. The existing
#   "/sessions/{session_id}" GET is fine because FastAPI distinguishes by
#   path depth/segment, but we keep follow-up routes contiguous so future
#   refactors don't accidentally interleave a "/sessions/{session_id}/x"
#   under a "/sessions/{any}" handler.

from ....models.parent_onboarding import (  # noqa: E402
    FollowupPriority, FollowupStatus, ParentOnboardingFollowup,
    ParentOnboardingReferral, PartnerAgency, ReferralStatus,
)
from ....schemas.parent_onboarding import (  # noqa: E402
    FollowupComplete, FollowupCreate, FollowupListResponse, FollowupResponse,
    FollowupUpdate, PartnerAgencyListResponse, PartnerAgencyResponse,
    ReferralCreate, ReferralListResponse, ReferralResponse, ReferralUpdate,
)
from ....services.parent_onboarding import (  # noqa: E402
    FollowupService, PartnerAgencyService, ReferralService,
)


def _compose_followup_response(
    followup: ParentOnboardingFollowup,
) -> FollowupResponse:
    assignee_name: Optional[str] = None
    if followup.assignee is not None:
        first = followup.assignee.first_name or ""
        last = followup.assignee.last_name or ""
        full = f"{first} {last}".strip()
        assignee_name = full or followup.assignee.email
    return FollowupResponse(
        id=followup.id,
        session_id=followup.session_id,
        title=followup.title,
        description=followup.description,
        assignee_id=followup.assignee_id,
        assignee_name=assignee_name,
        due_date=followup.due_date,
        status=followup.status,
        priority=followup.priority,
        completed_at=followup.completed_at,
        completed_by_id=followup.completed_by_id,
        completion_note=followup.completion_note,
        created_at=followup.created_at,
        updated_at=followup.updated_at,
        created_by_id=followup.created_by_id,
    )


def _compose_referral_response(
    referral: ParentOnboardingReferral,
) -> ReferralResponse:
    agency_name: Optional[str] = None
    if referral.partner_agency is not None:
        agency_name = referral.partner_agency.name
    return ReferralResponse(
        id=referral.id,
        session_id=referral.session_id,
        partner_agency_id=referral.partner_agency_id,
        partner_agency_name=agency_name,
        agency_name_freetext=referral.agency_name_freetext,
        purpose=referral.purpose,
        status=referral.status,
        warm_handoff=referral.warm_handoff,
        patron_consent_to_share=referral.patron_consent_to_share,
        notes=referral.notes,
        made_at=referral.made_at,
        made_by_id=referral.made_by_id,
        created_at=referral.created_at,
        updated_at=referral.updated_at,
    )


# ----- Partner-agency autocomplete -----------------------------------------

@router.get(
    "/partner-agencies",
    response_model=PartnerAgencyListResponse,
)
async def list_partner_agencies(
    q: Optional[str] = Query(None, description="search prefix / fragment"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Search canonical partner agencies for the referral autocomplete.

    Returns active agencies whose name or slug ILIKEs the query. Capped at
    `limit` results (default 20). Out-of-scope: an admin UI to manage these
    rows -- see spec section "Out of Scope".
    """
    agencies = await PartnerAgencyService.search(db, q=q, limit=limit)
    return PartnerAgencyListResponse(
        agencies=[PartnerAgencyResponse.model_validate(a) for a in agencies],
        total=len(agencies),
    )


# ----- Followups -----------------------------------------------------------

@router.get(
    "/sessions/{session_id}/followups",
    response_model=FollowupListResponse,
)
async def list_session_followups(
    session_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all follow-ups attached to a session (staff-only)."""
    # Session-existence guard so we 404 on a stale URL rather than returning
    # an empty list (which would look like "no follow-ups" to the operator).
    session = await ParentOnboardingSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    rows, total = await FollowupService.list_for_session(db, session_id)
    return FollowupListResponse(
        followups=[_compose_followup_response(r) for r in rows],
        total=total,
    )


@router.post(
    "/sessions/{session_id}/followups",
    response_model=FollowupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_followup(
    session_id: int,
    data: FollowupCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new follow-up task on a session."""
    session = await ParentOnboardingSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    followup = await FollowupService.create(
        db,
        session_id=session_id,
        data=data.model_dump(),
        created_by_id=current_user.id,
    )
    await db.commit()
    # Re-fetch with assignee eager-loaded so the response composition can
    # read .assignee.first_name without MissingGreenlet.
    followup = await FollowupService.get(db, followup.id) or followup
    return _compose_followup_response(followup)


@router.patch(
    "/followups/{followup_id}",
    response_model=FollowupResponse,
)
async def update_followup(
    followup_id: int,
    data: FollowupUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Partial-update a follow-up (staff-only).

    Authorization: any staff user can update any follow-up. The spec's
    finer-grained "assignee or library_admin" gate is deferred to a follow-up
    PR once we have an in-app audit-of-edits panel; for now an audit log
    entry is written downstream.
    """
    followup = await FollowupService.get(db, followup_id)
    if not followup:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    payload = data.model_dump(exclude_unset=True)
    followup = await FollowupService.update(db, followup, payload)
    await db.commit()
    followup = await FollowupService.get(db, followup.id) or followup
    return _compose_followup_response(followup)


@router.post(
    "/followups/{followup_id}/complete",
    response_model=FollowupResponse,
)
async def complete_followup(
    followup_id: int,
    data: FollowupComplete,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Mark a follow-up as completed with an optional completion note."""
    followup = await FollowupService.get(db, followup_id)
    if not followup:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    followup = await FollowupService.complete(
        db,
        followup,
        completed_by=current_user,
        completion_note=data.completion_note,
    )
    await db.commit()
    followup = await FollowupService.get(db, followup.id) or followup
    return _compose_followup_response(followup)


@router.delete(
    "/followups/{followup_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_followup(
    followup_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Hard-delete a follow-up. The PII access log records the deletion."""
    followup = await FollowupService.get(db, followup_id)
    if not followup:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    await FollowupService.delete(db, followup)
    await db.commit()


# ----- Referrals -----------------------------------------------------------

@router.get(
    "/sessions/{session_id}/referrals",
    response_model=ReferralListResponse,
)
async def list_session_referrals(
    session_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all referrals attached to a session (staff-only)."""
    session = await ParentOnboardingSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    rows, total = await ReferralService.list_for_session(db, session_id)
    return ReferralListResponse(
        referrals=[_compose_referral_response(r) for r in rows],
        total=total,
    )


@router.post(
    "/sessions/{session_id}/referrals",
    response_model=ReferralResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_referral(
    session_id: int,
    data: ReferralCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new referral on a session.

    Pass `partner_agency_id` to link to a canonical row, OR
    `agency_name_freetext` to capture a name that has no row yet. The
    request schema rejects payloads where both are blank with a 422.
    """
    session = await ParentOnboardingSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if data.partner_agency_id is not None:
        agency = await PartnerAgencyService.get(db, data.partner_agency_id)
        if agency is None:
            raise HTTPException(
                status_code=400, detail="Unknown partner_agency_id",
            )
    referral = await ReferralService.create(
        db,
        session_id=session_id,
        data=data.model_dump(),
        made_by_id=current_user.id,
    )
    await db.commit()
    referral = await ReferralService.get(db, referral.id) or referral
    return _compose_referral_response(referral)


@router.patch(
    "/referrals/{referral_id}",
    response_model=ReferralResponse,
)
async def update_referral(
    referral_id: int,
    data: ReferralUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Partial-update a referral (staff-only)."""
    referral = await ReferralService.get(db, referral_id)
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    payload = data.model_dump(exclude_unset=True)
    referral = await ReferralService.update(db, referral, payload)
    await db.commit()
    referral = await ReferralService.get(db, referral.id) or referral
    return _compose_referral_response(referral)


@router.delete(
    "/referrals/{referral_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_referral(
    referral_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Hard-delete a referral."""
    referral = await ReferralService.get(db, referral_id)
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    await ReferralService.delete(db, referral)
    await db.commit()


# ============================================================================
# Component 9: Session resource handouts (catalog + per-session assignments)
# ============================================================================
#
# Route ordering: the literal "/sessions/{session_id}/handouts" subpaths are
# kept contiguous below so future refactors don't interleave a more-general
# "/sessions/{any}" handler in between.

from ....models.parent_onboarding import (  # noqa: E402
    ParentOnboardingSessionHandout, ResourceHandout,
)
from ....schemas.parent_onboarding import (  # noqa: E402
    ResourceHandoutListResponse, ResourceHandoutResponse,
    SessionHandoutCreate, SessionHandoutListResponse, SessionHandoutResponse,
)
from ....services.parent_onboarding import (  # noqa: E402
    ResourceHandoutService, SessionHandoutService,
)


# Static URL prefix where handout PDFs and thumbnails are served. Stored as
# a config setting so the relative ``file_path`` in the DB doesn't have to
# bake in a host. Default matches the spec's "/static/handouts/" / "/static/
# packets/" layout.
_HANDOUT_STATIC_PREFIX = "/static/handouts"


def _file_url(relative_path: Optional[str]) -> Optional[str]:
    if not relative_path:
        return None
    # Already absolute? Pass through. Catalog rows might point at an
    # external CDN someday and we don't want to mangle that.
    if relative_path.startswith(("http://", "https://", "/")):
        return relative_path
    return f"{_HANDOUT_STATIC_PREFIX}/{relative_path.lstrip('/')}"


def _compose_handout_response(
    handout: ResourceHandout,
) -> ResourceHandoutResponse:
    return ResourceHandoutResponse(
        id=handout.id,
        slug=handout.slug,
        title=handout.title,
        category=handout.category,
        language=handout.language,
        description=handout.description,
        file_url=_file_url(handout.file_path) or "",
        file_size_bytes=handout.file_size_bytes,
        page_count=handout.page_count,
        preview_thumbnail_url=_file_url(handout.preview_thumbnail_path),
        tags=list(handout.tags or []),
        is_active=handout.is_active,
    )


def _compose_session_handout_response(
    assignment: ParentOnboardingSessionHandout,
) -> SessionHandoutResponse:
    display_title: Optional[str] = None
    if assignment.resource_handout is not None:
        display_title = assignment.resource_handout.title
    elif assignment.community_resource_link is not None:
        display_title = assignment.community_resource_link.name

    given_by_name: Optional[str] = None
    if assignment.given_by is not None:
        first = assignment.given_by.first_name or ""
        last = assignment.given_by.last_name or ""
        full = f"{first} {last}".strip()
        given_by_name = full or assignment.given_by.email

    return SessionHandoutResponse(
        id=assignment.id,
        session_id=assignment.session_id,
        resource_handout_id=assignment.resource_handout_id,
        community_resource_link_id=assignment.community_resource_link_id,
        display_title=display_title,
        given_at=assignment.given_at,
        given_by_id=assignment.given_by_id,
        given_by_name=given_by_name,
        given_in_language=assignment.given_in_language,
        delivery_method=assignment.delivery_method,
        notes=assignment.notes,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


# ----- Catalog (staff-readable, admin CRUD deferred) ------------------------


@router.get(
    "/handouts",
    response_model=ResourceHandoutListResponse,
)
async def list_resource_handouts(
    language: Optional[str] = Query(
        None, max_length=8, description="BCP-47 language code",
    ),
    category: Optional[str] = Query(None, max_length=64),
    search: Optional[str] = Query(None, max_length=200),
    is_active: bool = Query(True),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Filter the resource-handout catalog (language + category + search).

    Used by the session-page picker; default ``is_active=True`` keeps
    deprecated handouts out of staff view. Returns the unpaginated
    ``total`` so the FE can render "All resources (47)".
    """
    rows, total = await ResourceHandoutService.list_catalog(
        db,
        language=language,
        category=category,
        search=search,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return ResourceHandoutListResponse(
        handouts=[_compose_handout_response(r) for r in rows],
        total=total,
    )


# ----- Session assignments --------------------------------------------------


@router.get(
    "/sessions/{session_id}/handouts",
    response_model=SessionHandoutListResponse,
)
async def list_session_handouts(
    session_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List handouts/links given to a family during a session."""
    session = await ParentOnboardingSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    rows, total = await SessionHandoutService.list_for_session(db, session_id)

    # PII access log: this read surfaces patron-linked handout history.
    # The session belongs to a patron, and the handout list reveals what
    # services were referenced for that family. Action ``read`` per the
    # ALLOWED_ACTIONS contract in pii_access_log_service.
    # PII log failure must not 500 the read; the middleware-batched
    # flow already captures the access at a coarser grain.
    with contextlib.suppress(Exception):  # noqa: BLE001 - any log failure is non-fatal to the read
        await pii_access_log_service.log_access(
            db,
            user_id=current_user.id,
            patron_id=session.patron_id,
            subject_type="parent_onboarding_session_handouts",
            subject_id=session_id,
            action="read",
            user_role=current_user.role,
        )

    return SessionHandoutListResponse(
        handouts=[_compose_session_handout_response(r) for r in rows],
        total=total,
    )


@router.post(
    "/sessions/{session_id}/handouts",
    response_model=SessionHandoutResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_handout(
    session_id: int,
    data: SessionHandoutCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Record a handout (or URL-only link) given to the family.

    Pass exactly one of ``resource_handout_id`` or
    ``community_resource_link_id``; the request schema enforces this. The
    server validates that the referenced row exists before write.
    """
    session = await ParentOnboardingSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if data.resource_handout_id is not None:
        handout = await ResourceHandoutService.get(db, data.resource_handout_id)
        if handout is None:
            raise HTTPException(
                status_code=400, detail="Unknown resource_handout_id",
            )
    if data.community_resource_link_id is not None:
        # The model lives in app.models.community_resource; lazy import to
        # keep this module's imports tidy.
        from ....models.community_resource import CommunityResourceLink
        crl = (await db.execute(
            select(CommunityResourceLink).where(
                CommunityResourceLink.id == data.community_resource_link_id,
            )
        )).scalar_one_or_none()
        if crl is None:
            raise HTTPException(
                status_code=400, detail="Unknown community_resource_link_id",
            )

    assignment = await SessionHandoutService.create(
        db,
        session_id=session_id,
        data=data.model_dump(),
        given_by_id=current_user.id,
    )
    await db.commit()
    assignment = await SessionHandoutService.get(db, assignment.id) or assignment
    return _compose_session_handout_response(assignment)


@router.delete(
    "/sessions/{session_id}/handouts/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session_handout(
    session_id: int,
    assignment_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Hard-delete a session-handout assignment.

    Only deletes the join row; the underlying catalog handout (or community
    resource link) is untouched. Path includes ``session_id`` so a
    misrouted delete on the wrong session 404s instead of silently
    succeeding.
    """
    assignment = await SessionHandoutService.get(db, assignment_id)
    if assignment is None or assignment.session_id != session_id:
        raise HTTPException(
            status_code=404, detail="Handout assignment not found",
        )
    await SessionHandoutService.delete(db, assignment)
    await db.commit()


# ----- Print packet (501 stub, behind the Resources print-handout-mode dep) -


@router.post(
    "/sessions/{session_id}/handouts/print-packet",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def print_session_handout_packet(
    session_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Generate a single PDF bundling the session's checked handouts.

    Currently returns 501. PR #1217 shipped the Resources page handout
    builder (FE-only, client-side print), but the server-side PDF
    generator that this spec depends on is its own follow-up PR. See spec
    "Out of Scope" + "Dependencies".

    The structured 501 body tells the FE to render the
    "Print packet (not available yet)" disabled state.
    """
    session = await ParentOnboardingSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={
            "detail": "Print packet generator is not available yet.",
            "dependent_spec": (
                "2026-05-18-l30-resources-print-handout-mode"
            ),
        },
    )


