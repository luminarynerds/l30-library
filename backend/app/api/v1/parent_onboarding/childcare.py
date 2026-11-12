# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Parent Onboarding — Emergency Childcare routes (Component 4).

Extracted from _legacy.py. Zero behaviour change — pure file move.
"""
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....models.parent_onboarding import (
    ChildcareRegistration, ChildcareRegistrationStatus,
)
from ....models.user import User
from ....schemas.parent_onboarding import (
    ChildcareCheckoutRequest,
    ChildcareRegistrationCreate, ChildcareRegistrationResponse,
    ChildcareRegistrationUpdate,
    ChildcareRosterCounts, ChildcareRosterEntry, ChildcareRosterResponse,
    ChildcareSessionCreate, ChildcareSessionListResponse,
    ChildcareSessionResponse, ChildcareSessionUpdate,
)
from ....services.organization_features_service import OrganizationFeaturesService
from ....services.parent_onboarding.childcare import ChildcareService, PickupNotAuthorized
from ....core.pii_audit import log_pii_access
from ..auth import get_current_user
from ..dependencies import require_authenticated, require_library_admin, require_staff

router = APIRouter()


def _is_staff(user: User) -> bool:
    return user.role in ("staff", "library_admin", "admin", "super_admin", "director")


# ============================================================================
# Component 4: Emergency Childcare
# ============================================================================

@router.post("/childcare/sessions", response_model=ChildcareSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_childcare_session(
    data: ChildcareSessionCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a childcare session (staff-only)."""
    session = await ChildcareService.create_session(db, data.model_dump())
    return ChildcareSessionResponse(
        **{k: v for k, v in session.__dict__.items() if not k.startswith("_")},
        registered_count=0,
    )


@router.get("/childcare/sessions", response_model=ChildcareSessionListResponse)
async def list_childcare_sessions(
    branch_id: Optional[int] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """List childcare sessions.

    Filters are inclusive on both ends. ``from_date`` and ``to_date`` are
    independent -- callers may pass either, both, or neither. ``status``
    accepts any value from :class:`ChildcareSessionStatus`.
    """
    sessions, total = await ChildcareService.list_sessions(
        db, branch_id=branch_id, from_date=from_date, to_date=to_date,
        status=status_filter, limit=limit, offset=offset,
    )
    return ChildcareSessionListResponse(
        sessions=[
            ChildcareSessionResponse(
                **{k: v for k, v in s.__dict__.items() if not k.startswith("_") and k != "registrations"},
                registered_count=len([r for r in (s.registrations or []) if r.status in ("registered", "checked_in")]),
            )
            for s in sessions
        ],
        total=total, limit=limit, offset=offset,
    )


@router.patch(
    "/childcare/sessions/{session_id}",
    response_model=ChildcareSessionResponse,
)
async def update_childcare_session(
    session_id: int,
    data: ChildcareSessionUpdate,
    # NOTE: gated to library_admin to match the pattern used by other
    # parent-onboarding admin endpoints in this module (resource-guide
    # sections, etc.). ``require_library_admin`` is STRICT -- only the
    # LIBRARY_ADMIN role passes; ADMIN / SUPER_ADMIN / DIRECTOR are NOT
    # included. This is intentional; see app/api/v1/dependencies.py.
    current_user: User = Depends(require_library_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing childcare session (library_admin only).

    Wires the previously orphaned :class:`ChildcareSessionUpdate` schema.
    ``branch_id`` and ``date`` are immutable post-create (mutating them
    would orphan existing registrations); the schema does not expose them.

    Returns 404 if the session does not exist. Returns 422 if
    ``max_children`` would drop below the current count of active
    registrations (``registered`` + ``checked_in``).
    """
    updates = data.model_dump(exclude_unset=True)
    try:
        session = await ChildcareService.update_session(db, session_id, updates)
    except ValueError as e:
        # Service surfaces "not found" and "max_children below active count"
        # as ValueError; map to the appropriate HTTP status.
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from e
        raise HTTPException(status_code=422, detail=msg) from e

    return ChildcareSessionResponse(
        **{k: v for k, v in session.__dict__.items() if not k.startswith("_") and k != "registrations"},
        registered_count=len([
            r for r in (session.registrations or [])
            if r.status in ("registered", "checked_in")
        ]),
    )


@router.get(
    "/childcare/sessions/{session_id}/roster",
    response_model=ChildcareRosterResponse,
)
async def get_childcare_roster(
    request: Request,
    session_id: int,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Staff-only roster for a childcare session.

    Returns kids + their parent + authorized-pickup list + status counts.
    Writes a single batched ``pii_access_log`` row covering every patron
    whose registration appears in the response (one row per request, not
    per registration, to keep the audit table from exploding under
    polling).

    Originally gated behind ``pickup_authorization_enabled`` (the flag
    introduced in PR #1037). Loosened in this PR: the roster is also the
    surface the check-in / no-show flow lives on, which is independent of
    whether the library has enabled the authorized-pickup feature. The
    parent_onboarding flag at the router level still applies.
    """
    if not _is_staff(current_user):
        raise HTTPException(status_code=403, detail="Staff only")

    # selectinload patron AND the three staff-audit relationships so
    # Pydantic serialization doesn't trip MissingGreenlet
    # (memory: feedback_l30_async_property_landmine).
    result = await db.execute(
        select(ChildcareRegistration)
        .where(ChildcareRegistration.session_id == session_id)
        .options(
            selectinload(ChildcareRegistration.patron),
            selectinload(ChildcareRegistration.checked_in_by),
            selectinload(ChildcareRegistration.checked_out_by),
            selectinload(ChildcareRegistration.no_show_flagged_by),
        )
        .order_by(ChildcareRegistration.id)
    )
    registrations = list(result.scalars().all())

    entries: list[ChildcareRosterEntry] = []
    counts = ChildcareRosterCounts()
    patron_ids: list[int] = []
    for reg in registrations:
        parent = reg.patron
        if parent is None:
            parent_name = "(unknown)"
            parent_email = None
        else:
            parent_name = f"{parent.first_name} {parent.last_name}".strip() or parent.email
            parent_email = parent.email
            patron_ids.append(parent.id)

        def _staff_name(u: Optional[User]) -> Optional[str]:
            if u is None:
                return None
            return f"{u.first_name} {u.last_name}".strip() or u.email

        entries.append(
            ChildcareRosterEntry(
                registration=ChildcareRegistrationResponse.model_validate(reg),
                parent_name=parent_name,
                parent_email=parent_email,
                checked_in_by_name=_staff_name(reg.checked_in_by),
                checked_out_by_staff_name=_staff_name(reg.checked_out_by),
                no_show_flagged_by_name=_staff_name(reg.no_show_flagged_by),
            )
        )

        # Tally counts. ``reg.status`` is either the enum or the raw
        # string (depends on driver); normalize via the enum's .value
        # when it's an enum, else use the str directly.
        s = reg.status.value if hasattr(reg.status, "value") else str(reg.status)
        if s == "registered":
            counts.registered += 1
        elif s == "checked_in":
            counts.checked_in += 1
        elif s == "checked_out":
            counts.checked_out += 1
        elif s == "no_show":
            counts.no_show += 1
        elif s == "cancelled":
            counts.cancelled += 1

    # PII access audit: one batched row per roster read covering every
    # parent whose record appeared (memory feedback_l30_pii_access_log_dual_flow:
    # the middleware-batched path is the right shape for a multi-record read).
    # The minor-child fields are listed under fields_accessed so a compliance
    # query can find "who looked at child PII when".
    if patron_ids:
        await log_pii_access(
            db=db,
            user_id=current_user.id,
            user_role=current_user.role,
            endpoint=str(request.url.path),
            fields_accessed=[
                "child_name",
                "child_age_months",
                "emergency_contact_name",
                "emergency_contact_phone",
                "special_needs_notes",
                "authorized_pickup",
            ],
            fields_redacted=[],
            patron_ids_accessed=patron_ids,
            ip_address=request.client.host if request.client else None,
            additional_context={
                "reason": "childcare_roster_view",
                "session_id": session_id,
                "registration_count": len(registrations),
            },
        )

    return ChildcareRosterResponse(
        session_id=session_id, entries=entries, counts=counts
    )


@router.post("/childcare/sessions/{session_id}/register", response_model=ChildcareRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_for_childcare(
    session_id: int,
    data: ChildcareRegistrationCreate,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Register a child for a childcare session."""
    try:
        registration = await ChildcareService.register_child(
            db, session_id, current_user.id, data.model_dump()
        )
        return ChildcareRegistrationResponse.model_validate(registration)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/childcare/registrations/{registration_id}", response_model=ChildcareRegistrationResponse)
async def update_childcare_registration(
    registration_id: int,
    data: ChildcareRegistrationUpdate,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update a childcare registration (check-in/out, cancel).

    When ``pickup_authorization_enabled`` is ON and the requested transition
    is ``checked_out``, this endpoint refuses and points the caller to
    ``POST /childcare/registrations/{id}/checkout`` -- that path requires the
    ``picked_up_by_*`` body fields and validates them against the authorized
    list.
    """
    result = await db.execute(
        select(ChildcareRegistration).where(ChildcareRegistration.id == registration_id)
    )
    registration = result.scalar_one_or_none()
    if not registration:
        raise HTTPException(status_code=404, detail="Registration not found")

    payload = data.model_dump(exclude_unset=True)

    # Ownership: only the registering patron or staff may touch a
    # registration. Without this any authenticated patron could rewrite
    # anyone's authorized_pickup list.
    if not _is_staff(current_user) and registration.patron_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this registration")

    # Flag-gate the authorized_pickup field. When the flag is OFF, we accept
    # the request shape (frontends may post it speculatively) but silently
    # drop the field rather than persist it -- avoids surfacing the feature
    # before the library has opted in.
    pickup_flag_on = await OrganizationFeaturesService.is_feature_enabled(
        db, "pickup_authorization_enabled"
    )
    if "authorized_pickup" in payload and not pickup_flag_on:
        payload.pop("authorized_pickup")
    elif "authorized_pickup" in payload and payload["authorized_pickup"] is not None:
        # Normalize Pydantic models to plain dicts for JSONB persistence.
        payload["authorized_pickup"] = [
            e.model_dump() if hasattr(e, "model_dump") else dict(e)
            for e in payload["authorized_pickup"]
        ]

    # When flag is ON, refuse a checkout transition through PATCH -- force
    # callers to use the validated /checkout endpoint instead. Legacy
    # frontends (flag OFF) keep working unchanged.
    if (
        pickup_flag_on
        and data.status is not None
        and data.status.value == "checked_out"
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Use POST /childcare/registrations/{id}/checkout when "
                "pickup_authorization_enabled is on."
            ),
        )

    # Compare via .value because ChildcareRegistrationStatus is a
    # ``(str, Enum)`` mixin -- ``str(enum_member)`` returns
    # ``"ChildcareRegistrationStatus.checked_in"``, not ``"checked_in"``,
    # so the previous ``str(data.status) == "checked_in"`` check was
    # silently dead. ``data.status.value`` returns the lowercase string.
    status_value = data.status.value if data.status is not None else None

    # Status transitions that are *staff operations* on the floor
    # (signing kids in, marking no-shows, recording check-outs) require
    # the caller to actually be staff. The ownership gate above already
    # blocks unrelated patrons; this second gate blocks the registering
    # patron from forging their own check-in/no-show audit row.
    # ``cancelled`` is the one self-service patron mutation and is left
    # un-gated. ``checked_out`` is already routed through the dedicated
    # /checkout endpoint when pickup_flag_on; this branch covers the
    # legacy (flag off) path.
    _STAFF_ONLY_TRANSITIONS = {"checked_in", "checked_out", "no_show"}
    if status_value in _STAFF_ONLY_TRANSITIONS and not _is_staff(current_user):
        raise HTTPException(
            status_code=403,
            detail="Staff role required for check-in / check-out / no-show.",
        )

    # no_show_reason is only meaningful when the transition is no_show;
    # drop it silently if attached to any other status so a confused
    # client can't accidentally annotate an unrelated transition.
    if "no_show_reason" in payload and status_value != "no_show":
        payload.pop("no_show_reason")

    for key, value in payload.items():
        setattr(registration, key, value)
    # Auto-set check-in/out timestamps + staff-audit triad. The
    # ``not registration.checked_in_at`` guards make re-flips idempotent:
    # a second PATCH ``checked_in`` on an already-checked-in row keeps
    # the original timestamp + staff_id so we don't rewrite history.
    now = datetime.now(timezone.utc)
    if status_value == "checked_in" and not registration.checked_in_at:
        registration.checked_in_at = now
        registration.checked_in_by_staff_id = current_user.id
    if status_value == "checked_out" and not registration.checked_out_at:
        registration.checked_out_at = now
        registration.checked_out_by_staff_id = current_user.id
    if status_value == "no_show" and not registration.no_show_flagged_at:
        registration.no_show_flagged_at = now
        registration.no_show_flagged_by_staff_id = current_user.id
    await db.flush()
    await db.refresh(registration)
    return ChildcareRegistrationResponse.model_validate(registration)


@router.post(
    "/childcare/registrations/{registration_id}/checkout",
    response_model=ChildcareRegistrationResponse,
)
async def checkout_childcare_registration(
    registration_id: int,
    data: ChildcareCheckoutRequest,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Check a child out, validating against the authorized pickup list.

    Staff-only. Returns 404 when the feature flag is off so the endpoint
    doesn't leak its existence in OpenAPI scrapes.
    """
    if not await OrganizationFeaturesService.is_feature_enabled(
        db, "pickup_authorization_enabled"
    ):
        raise HTTPException(
            status_code=404,
            detail="Pickup authorization feature is not enabled",
        )
    if not _is_staff(current_user):
        raise HTTPException(status_code=403, detail="Staff only")

    result = await db.execute(
        select(ChildcareRegistration).where(ChildcareRegistration.id == registration_id)
    )
    registration = result.scalar_one_or_none()
    if not registration:
        raise HTTPException(status_code=404, detail="Registration not found")

    if registration.checked_out_at is not None:
        raise HTTPException(status_code=409, detail="Already checked out")

    try:
        matched = ChildcareService.validate_pickup_authorization(
            registration,
            picked_up_by_name=data.picked_up_by_name,
            picked_up_by_phone=data.picked_up_by_phone,
            staff_override_reason=data.staff_override_reason,
        )
    except PickupNotAuthorized as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": exc.detail,
                "has_authorized_list": exc.has_authorized_list,
            },
        ) from exc

    if matched is not None:
        # Audit columns from the matched entry (authoritative).
        registration.checked_out_by_name = str(matched.get("name", ""))[:200]
        registration.checked_out_by_phone = str(matched.get("phone", ""))[:50]
        registration.pickup_override_reason = None
    else:
        # Override path: log what the staff entered + the reason.
        registration.checked_out_by_name = data.picked_up_by_name[:200]
        registration.checked_out_by_phone = data.picked_up_by_phone[:50]
        registration.pickup_override_reason = (
            (data.staff_override_reason or "").strip()[:500] or None
        )

    registration.status = ChildcareRegistrationStatus.checked_out
    registration.checked_out_at = datetime.now(timezone.utc)
    # Stamp the staff member who operated this checkout. This is distinct
    # from checked_out_by_name (the adult who picked the child up).
    registration.checked_out_by_staff_id = current_user.id
    await db.flush()
    await db.refresh(registration)
    return ChildcareRegistrationResponse.model_validate(registration)
