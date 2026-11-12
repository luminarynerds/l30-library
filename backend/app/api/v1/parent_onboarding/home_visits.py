# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Home Visits sub-router for the parent-onboarding API.

Covers two URL prefixes (both belong to the home-visit subdomain):
  /home-visits/*
  /home-visit-access-notes/*

Extracted from parent_onboarding/_legacy.py (pure move, no logic changes).
"""
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User, UserRole
from ....schemas.parent_onboarding import (
    DayPlanResponse, DayPlanSortPatch,
    GeocodeManualOverride,
    HomeVisitAccessNotesRead, HomeVisitAccessNotesUpsert,
    HomeVisitCancelRequest, HomeVisitCompleteRequest, HomeVisitConfirmRequest,
    HomeVisitConflictItem, HomeVisitConflictResponse,
    HomeVisitRescheduleRequest, HomeVisitRescheduleResponse,
    HomeVisitSafetyCheckinRequest, HomeVisitSafetyResponse,
    HomeVisitStatusHistoryItem, HomeVisitStatusHistoryResponse,
    OverdueHomeVisitListResponse, OverdueHomeVisitSummary,
    ParentHomeVisitComplete, ParentHomeVisitCreate,
    ParentHomeVisitListResponse, ParentHomeVisitResponse,
    ParentHomeVisitUpdate,
)
from ....services.organization_features_service import OrganizationFeaturesService
from ....services.parent_onboarding import (
    HomeVisitSafetyService, HomeVisitService, InvalidHomeVisitTransitionError,
)
from ....services import home_visit_day_plan_service as day_plan_service
from ....services import pii_access_log_service
from ..auth import get_current_user
from ..dependencies import require_authenticated, require_staff

router = APIRouter()


# ============================================================================
# Component 7: Home Visits
# ============================================================================

@router.post("/home-visits", response_model=ParentHomeVisitResponse, status_code=status.HTTP_201_CREATED)
async def create_home_visit(
    data: ParentHomeVisitCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Schedule a home visit (staff-only)."""
    visit = await HomeVisitService.create_visit(db, data.model_dump())
    return ParentHomeVisitResponse.model_validate(visit)


@router.get("/home-visits", response_model=ParentHomeVisitListResponse)
async def list_home_visits(
    patron_id: Optional[int] = None,
    visitor_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    from_date: Optional[date] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """List home visits."""
    visits, total = await HomeVisitService.list_visits(
        db, patron_id=patron_id, visitor_id=visitor_id,
        status=status_filter, from_date=from_date,
        limit=limit, offset=offset,
    )
    return ParentHomeVisitListResponse(
        visits=[ParentHomeVisitResponse.model_validate(v) for v in visits],
        total=total, limit=limit, offset=offset,
    )


# NOTE: This literal path MUST be registered before "/home-visits/{visit_id}"
# below - FastAPI matches routes in declaration order, so a param route declared
# first would swallow "/home-visits/my" and 422 ("my" can't coerce to int).
@router.get("/home-visits/my", response_model=ParentHomeVisitListResponse)
async def list_my_home_visits(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """List home visits where the current user is the assigned visitor.

    Used by the staff-side `ParentHomeVisitsPage`, which shows a visitor
    their own scheduled and past visits. Filters by `visitor_id ==
    current_user.id`. Optional `status` query narrows to a single status.

    Returns the same paginated `ParentHomeVisitListResponse` shape as
    `GET /home-visits`, so the frontend `getMyHomeVisits()` reuses the
    same `ParentHomeVisit` type.
    """
    visits, total = await HomeVisitService.list_visits(
        db,
        visitor_id=current_user.id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return ParentHomeVisitListResponse(
        visits=[ParentHomeVisitResponse.model_validate(v) for v in visits],
        total=total, limit=limit, offset=offset,
    )


# ----------------------------------------------------------------------------
# Lone-worker safety check-in mechanic (feature flag: home_visit_safety_enabled)
#
# NOTE: All three literal-suffix routes below (/safety-checkin,
# /safety-checkout, and the /home-visits/overdue list) MUST stay above
# /home-visits/{visit_id} declared further down. FastAPI matches routes
# in declaration order; /{visit_id} would otherwise swallow the literal
# "overdue" segment with a 422 coercion error.
# ----------------------------------------------------------------------------

async def require_home_visit_safety_enabled(
    db: AsyncSession = Depends(get_db),
) -> None:
    enabled = await OrganizationFeaturesService.is_feature_enabled(
        db, "home_visit_safety_enabled"
    )
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Home visit safety check-in is not enabled",
        )


@router.get(
    "/home-visits/eligible-buddies",
    dependencies=[Depends(require_home_visit_safety_enabled)],
)
async def list_eligible_safety_buddies(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return a slim list of users eligible to be assigned as a safety buddy.

    "Eligible" = active users with staff / library_admin / admin / director /
    super_admin role. Returned shape is deliberately minimal (id + full_name)
    so the consuming `<select>` does not leak email or any other PII.
    """
    eligible_roles = [
        UserRole.STAFF.value, UserRole.LIBRARY_ADMIN.value,
        UserRole.ADMIN.value, UserRole.DIRECTOR.value,
        UserRole.SUPER_ADMIN.value,
    ]
    result = await db.execute(
        select(User.id, User.first_name, User.last_name)
        .where(User.role.in_(eligible_roles), User.is_active.is_(True))
        .order_by(User.last_name, User.first_name)
    )
    rows = result.all()
    return [
        {"id": row[0], "full_name": f"{row[1]} {row[2]}".strip()}
        for row in rows
    ]


@router.get(
    "/home-visits/overdue",
    response_model=OverdueHomeVisitListResponse,
    dependencies=[Depends(require_home_visit_safety_enabled)],
)
async def list_overdue_home_visits(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List currently-overdue safety check-outs (admin/director-only).

    "Overdue" = staff checked-in safely, the due-at deadline has passed,
    but no safe-departure check-out has been recorded. Includes both
    already-flagged-and-notified visits and brand-new ones still pending
    the next scanner pass, so the staff view shows the full picture.
    """
    # Admin / director / super_admin can view; ordinary staff cannot.
    if current_user.role not in (UserRole.ADMIN, UserRole.DIRECTOR, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="Admin or Director role required")

    now = datetime.now(timezone.utc)
    visits = await HomeVisitSafetyService.list_overdue(db, include_flagged=True, now=now)

    rows: list[OverdueHomeVisitSummary] = []
    for v in visits:
        minutes_overdue = int(
            max(0, (now - v.safety_checkout_due_at).total_seconds() // 60)
        )
        rows.append(
            OverdueHomeVisitSummary(
                visit_id=v.id,
                visitor_id=v.visitor_id,
                visitor_name=(v.visitor.full_name if v.visitor else None),
                safety_buddy_user_id=v.safety_buddy_user_id,
                safety_buddy_name=(v.safety_buddy.full_name if v.safety_buddy else None),
                safety_checkin_at=v.safety_checkin_at,
                safety_checkout_due_at=v.safety_checkout_due_at,
                safety_overdue_flagged_at=v.safety_overdue_flagged_at,
                address=v.address,
                scheduled_date=v.scheduled_date,
                minutes_overdue=minutes_overdue,
            )
        )
    return OverdueHomeVisitListResponse(visits=rows, total=len(rows))


@router.post(
    "/home-visits/{visit_id}/safety-checkin",
    response_model=HomeVisitSafetyResponse,
    dependencies=[Depends(require_home_visit_safety_enabled)],
)
async def home_visit_safety_checkin(
    visit_id: int,
    payload: HomeVisitSafetyCheckinRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff marks 'arrived safely'. Sets check-in time and due-at deadline.

    Returns a warning string if no `safety_buddy_user_id` was assigned;
    the visit still proceeds but the staff member is alerted that there
    is no per-visit buddy escalation path (supervisors will still be
    notified by the scanner).
    """
    visit = await HomeVisitService.get_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Home visit not found")
    # Only the assigned visitor (or admins/directors) can check in.
    if (
        visit.visitor_id != current_user.id
        and current_user.role not in (UserRole.ADMIN, UserRole.DIRECTOR, UserRole.SUPER_ADMIN)
    ):
        raise HTTPException(status_code=403, detail="Only the assigned visitor can safety check-in")

    await HomeVisitSafetyService.mark_safe_arrival(
        db,
        visit,
        visit_duration_minutes=payload.visit_duration_minutes,
    )

    warning: Optional[str] = None
    if visit.safety_buddy_user_id is None:
        warning = (
            "No safety buddy assigned to this visit. Supervisors will still be "
            "notified if you do not check out on time, but no per-visit buddy "
            "alert will be sent. Assign a buddy in the visit details."
        )

    return HomeVisitSafetyResponse(
        visit_id=visit.id,
        safety_checkin_at=visit.safety_checkin_at,
        safety_checkout_at=visit.safety_checkout_at,
        safety_checkout_due_at=visit.safety_checkout_due_at,
        safety_buddy_user_id=visit.safety_buddy_user_id,
        buddy_warning=warning,
    )


@router.post(
    "/home-visits/{visit_id}/safety-checkout",
    response_model=HomeVisitSafetyResponse,
    dependencies=[Depends(require_home_visit_safety_enabled)],
)
async def home_visit_safety_checkout(
    visit_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff marks 'left safely'. Stops the overdue scanner for this visit."""
    visit = await HomeVisitService.get_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Home visit not found")
    if (
        visit.visitor_id != current_user.id
        and current_user.role not in (UserRole.ADMIN, UserRole.DIRECTOR, UserRole.SUPER_ADMIN)
    ):
        raise HTTPException(status_code=403, detail="Only the assigned visitor can safety check-out")
    if visit.safety_checkin_at is None:
        raise HTTPException(status_code=409, detail="Cannot check out before checking in")

    await HomeVisitSafetyService.mark_safe_departure(db, visit)
    return HomeVisitSafetyResponse(
        visit_id=visit.id,
        safety_checkin_at=visit.safety_checkin_at,
        safety_checkout_at=visit.safety_checkout_at,
        safety_checkout_due_at=visit.safety_checkout_due_at,
        safety_buddy_user_id=visit.safety_buddy_user_id,
        buddy_warning=None,
    )


# NOTE: /home-visits/conflicts is a literal-suffix sibling of /home-visits/
# and MUST register before /home-visits/{visit_id}. See the route-shadowing
# comments at the top of the home-visits block; same trap, different word.
@router.get(
    "/home-visits/conflicts",
    response_model=HomeVisitConflictResponse,
)

async def check_home_visit_conflicts(
    visitor_id: int = Query(..., description="Visitor whose calendar to check"),
    date_param: date = Query(..., alias="date"),
    exclude_visit_id: Optional[int] = Query(None),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return any same-visitor visits on the given date.

    Frontend uses this from the reschedule modal to warn (not block) staff
    when a visitor is double-booked. v1 is date-resolution only -- adding
    time-window arithmetic is a follow-up if libraries actually book
    multiple visits per visitor per day.
    """
    conflicts = await HomeVisitService.check_conflicts(
        db,
        visitor_id=visitor_id,
        scheduled_date=date_param,
        exclude_visit_id=exclude_visit_id,
    )
    items = [
        HomeVisitConflictItem(
            id=v.id,
            scheduled_date=v.scheduled_date,
            scheduled_time=v.scheduled_time,
            patron_id=v.patron_id,
            patron_name=(v.patron.full_name if v.patron else None),
            status=v.status,
        )
        for v in conflicts
    ]
    return HomeVisitConflictResponse(
        has_conflict=bool(items),
        conflicting_visits=items,
    )


# ----------------------------------------------------------------------------
# Day Plan / Map View (feature flag: home_visit_day_plan_enabled)
#
# NOTE: All five literal routes below (/day-plan, /day-plan-sort,
# /access-notes/*, /geocode) MUST stay above /home-visits/{visit_id}
# declared further down. FastAPI matches routes in declaration order;
# /{visit_id} would otherwise swallow "day-plan" and 422 on int coercion.
# This is the exact trap documented in feedback_l30_fastapi_literal_before_param_route
# and the existing /home-visits/my route already follows this pattern.
# ----------------------------------------------------------------------------

async def require_home_visit_day_plan_enabled(
    db: AsyncSession = Depends(get_db),
) -> None:
    enabled = await OrganizationFeaturesService.is_feature_enabled(
        db, "home_visit_day_plan_enabled"
    )
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Home visit day plan is not enabled",
        )


@router.get(
    "/home-visits/day-plan",
    response_model=DayPlanResponse,
    dependencies=[Depends(require_home_visit_day_plan_enabled)],
)
async def get_home_visit_day_plan(
    plan_date: date = Query(..., alias="date"),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return the current staff member's day plan for a given date.

    Day plan = ordered list of stops (visits assigned to current_user on
    ``date``), geocoded lat/lng for each, access notes joined from the
    per-patron table, and routing legs between consecutive stops.

    Visitor scoping is hard-coded to ``current_user.id``; admins viewing
    another visitor's plan would be a separate spec.
    """
    plan = await day_plan_service.assemble_day_plan(
        db, visitor_id=current_user.id, plan_date=plan_date
    )
    # Audit PII access: viewing the day plan reveals each patron's
    # address + access notes. One row per patron, action='read'.
    for stop in plan.stops:
        if stop.access_notes is not None:
            # log_access only raises ValueError on unknown action; we
            # control the action above, so this call cannot raise.
            await pii_access_log_service.log_access(
                db,
                user_id=current_user.id,
                patron_id=stop.patron_id,
                subject_type="home_visit_access_notes",
                action="read",
                user_role=current_user.role,
                reason="day_plan_view",
            )
    return plan


@router.patch(
    "/home-visits/{visit_id}/day-plan-sort",
    response_model=DayPlanResponse,
    dependencies=[Depends(require_home_visit_day_plan_enabled)],
)
async def patch_home_visit_day_plan_sort(
    visit_id: int,
    payload: DayPlanSortPatch,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Set or clear ``day_plan_sort_index`` for one visit, then re-return the plan.

    ``sort_index=None`` clears the manual override and reverts the stop to
    auto-order by scheduled_time.

    Only the assigned visitor (or admin/director/super_admin) can reorder
    their own day plan. Admins viewing another visitor's plan would need
    a separate spec; today this is a hard rule.
    """
    visit = await HomeVisitService.get_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Home visit not found")
    if (
        visit.visitor_id != current_user.id
        and current_user.role
        not in (UserRole.ADMIN, UserRole.DIRECTOR, UserRole.SUPER_ADMIN)
    ):
        raise HTTPException(
            status_code=403, detail="Only the assigned visitor can reorder a day plan"
        )

    visit.day_plan_sort_index = payload.sort_index
    await db.flush()

    return await day_plan_service.assemble_day_plan(
        db, visitor_id=visit.visitor_id, plan_date=visit.scheduled_date
    )


@router.post(
    "/home-visits/{visit_id}/geocode",
    response_model=ParentHomeVisitResponse,
    dependencies=[Depends(require_home_visit_day_plan_enabled)],
)
async def post_home_visit_geocode(
    visit_id: int,
    payload: Optional[GeocodeManualOverride] = None,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Manually pin a visit's coordinates, or trigger an automatic re-geocode.

    With a ``GeocodeManualOverride`` body, writes the staff-entered lat/lng
    to both the visit row and the geocode cache (provider='manual').
    Without a body, looks up the address via Nominatim again (skipping the
    cache freshness check) and stores the result.

    Either way, returns the updated visit so the UI can re-render the pin.
    """
    visit = await HomeVisitService.get_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Home visit not found")
    if not visit.address:
        raise HTTPException(status_code=400, detail="Visit has no address to geocode")

    if payload is not None:
        await day_plan_service.upsert_manual_geocode(
            db, visit.address, payload.lat, payload.lng
        )
        visit.geocoded_lat = payload.lat
        visit.geocoded_lng = payload.lng
    else:
        coords = await day_plan_service.get_or_geocode_address(db, visit.address)
        if coords is None:
            raise HTTPException(
                status_code=502, detail="Could not geocode this address"
            )
        visit.geocoded_lat, visit.geocoded_lng = coords

    await db.flush()
    await db.refresh(visit)
    return ParentHomeVisitResponse.model_validate(visit)


@router.get(
    "/home-visit-access-notes/{patron_id}",
    response_model=HomeVisitAccessNotesRead,
    dependencies=[Depends(require_home_visit_day_plan_enabled)],
)
async def get_home_visit_access_notes(
    patron_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return per-patron access notes (steps, dog, language, parking).

    Restricted to admin/director/super_admin OR any staff with a current
    or upcoming visit to the patron. Implements the spec's "narrow the
    PII surface" recommendation -- "any staff" would be over-broad.

    Writes a ``pii_access_log`` row on every successful read.
    """
    is_admin = current_user.role in (
        UserRole.ADMIN, UserRole.DIRECTOR, UserRole.SUPER_ADMIN, UserRole.LIBRARY_ADMIN
    )
    if not is_admin:
        allowed = await day_plan_service.staff_has_visit_access(
            db, current_user.id, patron_id
        )
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail="Access notes are limited to staff with a current or upcoming visit to this patron",
            )

    row = await day_plan_service.get_or_create_access_notes(db, patron_id)
    # log_access only raises ValueError on unknown action; action is hard-coded.
    await pii_access_log_service.log_access(
        db,
        user_id=current_user.id,
        patron_id=patron_id,
        subject_type="home_visit_access_notes",
        subject_id=row.id,
        action="read",
        user_role=current_user.role,
        reason="staff_view",
    )
    return HomeVisitAccessNotesRead.model_validate(row)


@router.put(
    "/home-visit-access-notes/{patron_id}",
    response_model=HomeVisitAccessNotesRead,
    dependencies=[Depends(require_home_visit_day_plan_enabled)],
)
async def put_home_visit_access_notes(
    patron_id: int,
    payload: HomeVisitAccessNotesUpsert,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Upsert per-patron access notes.

    Same visibility rule as the GET: admin/director OR staff with a
    current/upcoming visit. Missing fields in ``payload`` leave existing
    columns unchanged (partial update). ``updated_by_id`` and ``updated_at``
    are set on every write so the audit trail is complete.
    """
    is_admin = current_user.role in (
        UserRole.ADMIN, UserRole.DIRECTOR, UserRole.SUPER_ADMIN, UserRole.LIBRARY_ADMIN
    )
    if not is_admin:
        allowed = await day_plan_service.staff_has_visit_access(
            db, current_user.id, patron_id
        )
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail="Access notes are limited to staff with a current or upcoming visit to this patron",
            )

    row = await day_plan_service.get_or_create_access_notes(db, patron_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    row.updated_by_id = current_user.id
    row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(row)
    return HomeVisitAccessNotesRead.model_validate(row)


@router.get("/home-visits/{visit_id}", response_model=ParentHomeVisitResponse)
async def get_home_visit(
    visit_id: int,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific home visit."""
    visit = await HomeVisitService.get_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Home visit not found")
    return ParentHomeVisitResponse.model_validate(visit)


@router.patch("/home-visits/{visit_id}", response_model=ParentHomeVisitResponse)
async def update_home_visit(
    visit_id: int,
    data: ParentHomeVisitUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a home visit (staff-only)."""
    visit = await HomeVisitService.get_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Home visit not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(visit, key, value)
    await db.flush()
    await db.refresh(visit)
    return ParentHomeVisitResponse.model_validate(visit)


@router.post("/home-visits/{visit_id}/complete", response_model=ParentHomeVisitResponse)
async def complete_home_visit(
    visit_id: int,
    data: ParentHomeVisitComplete,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Legacy 'mark complete' route -- kept so the older /complete contract
    still works. New frontend code should call POST /complete-with-outcomes
    which captures outcomes properly and writes audit history.
    """
    visit = await HomeVisitService.get_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Home visit not found")
    visit = await HomeVisitService.complete_visit(db, visit, data.model_dump())
    return ParentHomeVisitResponse.model_validate(visit)


# ----------------------------------------------------------------------------
# Status-mutation routes (home_visit_mutations_001, 2026-05-25)
#
# These four routes are the inline-actions surface for the staff page.
# Each delegates to a service method that:
#   - validates the transition (raises InvalidHomeVisitTransitionError -> 409)
#   - updates the visit row
#   - writes a HomeVisitStatusHistory audit row
#   - writes a pii_access_log row tagged HOME_VISIT_STATUS_CHANGE
#
# The router owns the transaction boundary -- a commit happens implicitly
# via the get_db dependency; an HTTPException unwinds it.
# ----------------------------------------------------------------------------


def _map_transition_error(exc: InvalidHomeVisitTransitionError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "invalid_transition",
            "from_status": str(exc.from_status.value),
            "to_status": str(exc.to_status.value),
            "message": (
                f"Cannot transition home visit from {exc.from_status.value} "
                f"to {exc.to_status.value}."
            ),
        },
    )


@router.post(
    "/home-visits/{visit_id}/confirm",
    response_model=ParentHomeVisitResponse,
)
async def confirm_home_visit(
    visit_id: int,
    payload: HomeVisitConfirmRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Confirm a scheduled visit (one-click)."""
    visit = await HomeVisitService.get_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Home visit not found")
    try:
        visit = await HomeVisitService.confirm_visit(
            db,
            visit,
            changed_by=current_user,
            reason=payload.reason,
        )
    except InvalidHomeVisitTransitionError as exc:
        raise _map_transition_error(exc) from exc
    return ParentHomeVisitResponse.model_validate(visit)


@router.post(
    "/home-visits/{visit_id}/complete-with-outcomes",
    response_model=ParentHomeVisitResponse,
)
async def complete_home_visit_with_outcomes(
    visit_id: int,
    payload: HomeVisitCompleteRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Mark a visit complete and capture outcomes + resources + follow-up."""
    visit = await HomeVisitService.get_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Home visit not found")
    try:
        visit = await HomeVisitService.mark_complete(
            db,
            visit,
            changed_by=current_user,
            outcomes=payload.outcomes,
            resources_delivered=payload.resources_delivered,
            follow_up_needed=payload.follow_up_needed,
            follow_up_date=payload.follow_up_date,
            follow_up_notes=payload.follow_up_notes,
            referrals=payload.referrals,
        )
    except InvalidHomeVisitTransitionError as exc:
        raise _map_transition_error(exc) from exc
    return ParentHomeVisitResponse.model_validate(visit)


@router.post(
    "/home-visits/{visit_id}/cancel",
    response_model=ParentHomeVisitResponse,
)
async def cancel_home_visit(
    visit_id: int,
    payload: HomeVisitCancelRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a scheduled or confirmed visit with a required reason."""
    visit = await HomeVisitService.get_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Home visit not found")
    try:
        visit = await HomeVisitService.cancel_visit(
            db,
            visit,
            changed_by=current_user,
            cancelled_reason=payload.cancelled_reason,
            notify_acknowledged=payload.notify_acknowledged,
        )
    except InvalidHomeVisitTransitionError as exc:
        raise _map_transition_error(exc) from exc
    return ParentHomeVisitResponse.model_validate(visit)


@router.post(
    "/home-visits/{visit_id}/reschedule",
    response_model=HomeVisitRescheduleResponse,
)
async def reschedule_home_visit(
    visit_id: int,
    payload: HomeVisitRescheduleRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Reschedule a visit.

    Marks the original ``rescheduled`` and creates a new ``scheduled``
    row at the new date/time. Both visits are returned so the frontend
    can update its cache without a refetch.
    """
    visit = await HomeVisitService.get_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Home visit not found")
    try:
        original, replacement = await HomeVisitService.reschedule_visit(
            db,
            visit,
            changed_by=current_user,
            new_scheduled_date=payload.new_scheduled_date,
            new_scheduled_time=payload.new_scheduled_time,
            duration_minutes=payload.duration_minutes,
            reason=payload.reason,
        )
    except InvalidHomeVisitTransitionError as exc:
        raise _map_transition_error(exc) from exc
    return HomeVisitRescheduleResponse(
        visit=ParentHomeVisitResponse.model_validate(original),
        replacement_visit=ParentHomeVisitResponse.model_validate(replacement),
    )


@router.get(
    "/home-visits/{visit_id}/history",
    response_model=HomeVisitStatusHistoryResponse,
)
async def list_home_visit_status_history(
    visit_id: int,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return the audit-history rows for a visit (staff-only)."""
    visit = await HomeVisitService.get_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Home visit not found")
    rows, total = await HomeVisitService.get_history(db, visit_id, limit=limit)
    items = [
        HomeVisitStatusHistoryItem(
            id=r.id,
            visit_id=r.visit_id,
            from_status=r.from_status,
            to_status=r.to_status,
            changed_by_id=r.changed_by_id,
            changed_by_name=(r.changed_by.full_name if r.changed_by else None),
            changed_at=r.changed_at,
            reason=r.reason,
            metadata_json=r.metadata_json,
        )
        for r in rows
    ]
    return HomeVisitStatusHistoryResponse(history=items, total=total)
