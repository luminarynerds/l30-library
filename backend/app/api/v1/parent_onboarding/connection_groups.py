# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Parent Onboarding — Connection Groups API sub-router.

Pure move from parent_onboarding/_legacy.py — all 15 routes that live under
/parent-onboarding/connection-groups*.  No behaviour change.
"""
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.parent_onboarding import (
    ParentConnectionGroup, ParentConnectionGroupMeeting, ParentConnectionGroupMember,
)
from ....models.user import User, UserRole
from ....schemas.parent_onboarding import (
    ArchiveGroupRequest, ArchiveGroupResponse,
    CancelMeetingRequest, CapacityConflictDetail,
    EnrollMemberResponse, GroupMemberDetailResponse,
    GroupMembersListResponse, GroupMeetingResponse, GroupMeetingsListResponse,
    MeetingDispatchResponse, RescheduleMeetingRequest, StaffEnrollRequest,
    ParentConnectionGroupCreate, ParentConnectionGroupListResponse,
    ParentConnectionGroupResponse, ParentConnectionGroupUpdate,
    ConfidentialJoinRequest, ConfidentialJoinRequestResponse,
    ApprovalQueueResponse, DecideRequestPayload, DecideRequestResponse,
)
from ....services.parent_onboarding import ConnectionGroupService
from ..dependencies import require_authenticated, require_library_admin, require_staff
from ....core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

_STAFF_ROLES = {
    UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN,
    UserRole.DIRECTOR,
}


def _is_staff(user: Optional[User]) -> bool:
    return user is not None and getattr(user, "role", None) in _STAFF_ROLES


# Keys stripped from JSON when caller is not staff and group is confidential.
# Spec property #1/#2: omit, do NOT null. We build a dict and return via
# JSONResponse so Pydantic can't re-add them.
_CONFIDENTIAL_STRIPPED_KEYS = {
    "facilitator_id", "facilitator_name", "current_members",
    "member_count", "members",
}


def _serialize_group(
    g: ParentConnectionGroup, *, is_staff_caller: bool
) -> dict:
    member_count = len([m for m in (g.members or []) if m.status == "active"])
    is_confidential = bool(getattr(g, "confidential", False))
    description = g.description
    if is_confidential and not is_staff_caller and g.confidential_card_description:
        description = g.confidential_card_description
    base = {
        "id": g.id,
        "name": g.name,
        "description": description,
        "facilitator_id": g.facilitator_id,
        "branch_id": g.branch_id,
        "group_type": g.group_type,
        "max_members": g.max_members,
        "meeting_frequency": g.meeting_frequency,
        "meeting_day_of_week": g.meeting_day_of_week,
        "meeting_time": g.meeting_time,
        "location": g.location,
        "languages": list(g.languages or []),
        "is_active": g.is_active,
        "member_count": member_count,
        "confidential": is_confidential,
        "confidential_card_description": g.confidential_card_description,
        "confidential_approval_message": g.confidential_approval_message,
        "estimated_response_window_hours": g.estimated_response_window_hours,
        "created_at": g.created_at.isoformat() if g.created_at else None,
    }
    if is_confidential and not is_staff_caller:
        for k in _CONFIDENTIAL_STRIPPED_KEYS:
            base.pop(k, None)
    return base


async def _caller_can_approve(
    db: AsyncSession, user: User, group: ParentConnectionGroup
) -> bool:
    role = getattr(user, "role", None)
    if role in {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR}:
        return True
    if group.facilitator_id and group.facilitator_id == user.id:
        return True
    return False


@router.post("/connection-groups", response_model=ParentConnectionGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_connection_group(
    data: ParentConnectionGroupCreate,
    current_user: User = Depends(require_library_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a connection group (library_admin only — was staff; tightened
    in cg_lifecycle_001 so lifecycle CRUD lives behind the same admin gate)."""
    group = await ConnectionGroupService.create_group(db, data.model_dump())
    return ParentConnectionGroupResponse(
        **{k: v for k, v in group.__dict__.items() if not k.startswith("_") and k not in ("members", "meetings")},
        member_count=0,
    )


@router.get(
    "/connection-groups",
    # response_model intentionally omitted so we can return a dict with
    # confidentiality-stripped keys; Pydantic would re-add them as null.
    response_model=None,
)
async def list_connection_groups(
    branch_id: Optional[int] = None,
    group_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """List connection groups.

    Behavior change vs the pre-confidentiality endpoint: now requires
    authentication so we can branch on staff-vs-patron for confidential
    groups. Anonymous browsing was not a customer-facing path on staff
    routes anyway.
    """
    groups, total = await ConnectionGroupService.list_groups(
        db, branch_id=branch_id, group_type=group_type,
        limit=limit, offset=offset,
    )
    is_staff = _is_staff(current_user)
    return JSONResponse(content={
        "groups": [_serialize_group(g, is_staff_caller=is_staff) for g in groups],
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@router.get("/connection-groups/{group_id}", response_model=None)
async def get_connection_group(
    group_id: int,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific connection group (confidentiality-aware)."""
    group = await ConnectionGroupService.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return JSONResponse(content=_serialize_group(group, is_staff_caller=_is_staff(current_user)))


@router.patch("/connection-groups/{group_id}", response_model=ParentConnectionGroupResponse)
async def update_connection_group(
    group_id: int,
    data: ParentConnectionGroupUpdate,
    current_user: User = Depends(require_library_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a connection group (library_admin only — tightened in
    cg_lifecycle_001).

    Capacity guard: if ``max_members`` is being lowered to below the current
    active member count, return 422 with the list of affected member ids so
    the admin can remove members first. We intentionally do NOT auto-bump
    excess members to waitlisted — that's a side-effect the admin wouldn't
    see in their request (see spec Open Q2 + the staff-enroll spec's remove
    endpoint for the explicit removal flow).
    """
    group = await ConnectionGroupService.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    patch = data.model_dump(exclude_unset=True)
    if "max_members" in patch and patch["max_members"] is not None:
        requested = int(patch["max_members"])
        current_active = await ConnectionGroupService.count_active_members(db, group_id)
        if requested < current_active:
            affected = await ConnectionGroupService.active_member_ids(db, group_id)
            detail = CapacityConflictDetail(
                requested_max_members=requested,
                current_active_count=current_active,
                excess=current_active - requested,
                affected_member_ids=affected,
            )
            raise HTTPException(status_code=422, detail=detail.model_dump())

    for key, value in patch.items():
        setattr(group, key, value)
    await db.flush()
    await db.refresh(group)
    return ParentConnectionGroupResponse(
        **{k: v for k, v in group.__dict__.items() if not k.startswith("_") and k not in ("members", "meetings")},
        member_count=len([m for m in (group.members or []) if m.status == "active"]),
    )


_REMOVAL_REASONS = {"patron_request", "attendance_lapse", "safety", "program_ended", "other"}
_ADMIN_ROLES = {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR}


@router.post(
    "/connection-groups/{group_id}/enroll",
    # response_model omitted: confidential general-staff path returns 202 +
    # pending_approval row; non-confidential path returns 201 + EnrollMember.
    response_model=None,
    status_code=status.HTTP_201_CREATED,
)
async def staff_enroll_connection_group(
    group_id: int,
    data: StaffEnrollRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff-mediated enrollment of a patron into a connection group.

    Confidential groups: facilitator/admin → direct enroll (201, auto-decided).
    General staff → pending_approval (202).

    Capacity overrides require admin role; not allowed on confidential groups.
    """
    if data.override_capacity and current_user.role not in _ADMIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Capacity override requires admin role",
        )
    # Need the group to decide caller_is_facilitator_or_admin before service call.
    group = await ConnectionGroupService.get_group(db, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Connection group not found")
    can_approve = await _caller_can_approve(db, current_user, group)
    try:
        payload = await ConnectionGroupService.staff_enroll(
            db,
            group_id=group_id,
            patron_id=data.patron_id,
            enrolled_by_id=current_user.id,
            consent_note=data.consent_note,
            capacity_override=data.override_capacity,
            override_justification=data.override_justification,
            caller_is_facilitator_or_admin=can_approve,
        )
        # If the row is pending_approval, fire the notify-facilitator email and
        # return 202 with the request-shaped response.
        if payload.get("status") == "pending_approval":
            email_partial = await _notify_request_received_and_pending(
                db, group=group, patron_id=data.patron_id,
            )
            content = ConfidentialJoinRequestResponse(
                id=payload["id"],
                group_id=payload["group_id"],
                patron_id=payload["patron_id"],
                status=payload["status"],
                requested_at=datetime.now(timezone.utc),
                requested_by_id=current_user.id,
                estimated_response_window_hours=group.estimated_response_window_hours,
                email_partial=email_partial,
            ).model_dump(mode="json")
            return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=content)
        return EnrollMemberResponse.model_validate(payload)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from e
        raise HTTPException(status_code=400, detail=msg) from e


@router.get(
    "/connection-groups/{group_id}/members",
    response_model=GroupMembersListResponse,
)
async def list_connection_group_members(
    group_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List active + waitlisted members of a group (staff-only).

    Endpoint is staff-only, so the confidential-omit-keys behavior on the
    list/detail surface does not apply here; staff see the full shape.

    For CONFIDENTIAL groups, the staff floor is tightened: only the
    facilitator and admin/director/super_admin may see member identities.
    Same gate as approval actions — admin/director/super_admin or facilitator.
    """
    group = await ConnectionGroupService.get_group(db, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.confidential and not await _caller_can_approve(db, current_user, group):
        raise HTTPException(
            status_code=403,
            detail="Insufficient role for confidential group roster",
        )
    rows = await ConnectionGroupService.list_members(db, group_id)
    active = sum(1 for r in rows if r["status"] == "active")
    waitlisted = sum(1 for r in rows if r["status"] == "waitlisted")
    return GroupMembersListResponse(
        members=[GroupMemberDetailResponse.model_validate(r) for r in rows],
        active_count=active,
        waitlisted_count=waitlisted,
    )


# ============================================================================
# Component 5b: Confidentiality + approval-gated waitlist
# ============================================================================


async def _send_resend(*, to_email: str, subject: str, html: str, tag: str) -> bool:
    from ....core.email import send_email
    try:
        return await send_email(
            to_email=to_email,
            subject=subject,
            html_content=html,
            categories=[tag],
        )
    except Exception:  # noqa: BLE001  # send_email helper — return False on any failure
        return False


async def _notify_request_received_and_pending(
    db: AsyncSession,
    *,
    group: ParentConnectionGroup,
    patron_id: int,
) -> bool:
    patron_q = await db.execute(select(User).where(User.id == patron_id))
    patron = patron_q.scalar_one_or_none()
    partial = False
    if patron and getattr(patron, "email", None):
        ok = await _send_resend(
            to_email=patron.email,
            subject="Your request to join " + (group.name or "a group") + " was received",
            html=(
                "<p>Hi " + (getattr(patron, "first_name", "") or "there") + ",</p>"
                "<p>We received your request to join <strong>" + (group.name or "") + "</strong>. "
                "Library staff will review it within "
                + str(group.estimated_response_window_hours) + " hours.</p>"
            ),
            tag="connection_group_request_received",
        )
        if not ok:
            partial = True
    # Notify facilitator + admins. Facilitator first; admins as a separate send.
    if group.facilitator_id:
        fac_q = await db.execute(select(User).where(User.id == group.facilitator_id))
        facilitator = fac_q.scalar_one_or_none()
        if facilitator and getattr(facilitator, "email", None):
            ok = await _send_resend(
                to_email=facilitator.email,
                subject="New request awaiting approval: " + (group.name or ""),
                html=(
                    "<p>A new request is pending in <strong>" + (group.name or "")
                    + "</strong>.</p><p>Review it in the approval queue.</p>"
                ),
                tag="connection_group_approval_pending",
            )
            if not ok:
                partial = True
    return partial


async def _notify_decision(
    db: AsyncSession,
    *,
    group: ParentConnectionGroup,
    patron_id: int,
    decision: str,
    patron_message: Optional[str],
) -> bool:
    patron_q = await db.execute(select(User).where(User.id == patron_id))
    patron = patron_q.scalar_one_or_none()
    if not patron or not getattr(patron, "email", None):
        return False
    if decision == "approve":
        subject = "You're in: " + (group.name or "")
        body_intro = "Welcome! Your request to join <strong>" + (group.name or "") + "</strong> has been approved."
        tag = "connection_group_request_approved"
    else:
        subject = "Update on your request to join " + (group.name or "")
        body_intro = "Thank you for reaching out. Your request to join <strong>" + (group.name or "") + "</strong> was not approved at this time."
        tag = "connection_group_request_denied"
    note = ""
    if patron_message:
        note = "<p><em>From staff:</em> " + patron_message + "</p>"
    html = "<p>Hi " + (getattr(patron, "first_name", "") or "there") + ",</p><p>" + body_intro + "</p>" + note
    ok = await _send_resend(to_email=patron.email, subject=subject, html=html, tag=tag)
    return not ok  # email_partial = True iff send was suppressed


@router.post(
    "/connection-groups/{group_id}/request",
    response_model=None,
    status_code=status.HTTP_201_CREATED,
)
async def request_to_join_confidential_group(
    group_id: int,
    data: ConfidentialJoinRequest,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Request approval to join a confidential group.

    Patrons may only request for themselves (patron_id must equal current
    user id). Staff may request on behalf of any patron.
    """
    if not _is_staff(current_user) and data.patron_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Patrons may only submit requests for themselves",
        )
    try:
        payload = await ConnectionGroupService.request_join(
            db,
            group_id=group_id,
            patron_id=data.patron_id,
            requested_by_id=current_user.id,
            request_message=data.request_message,
            consent_to_share_contact=data.consent_to_share_contact,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from e
        raise HTTPException(status_code=400, detail=msg) from e

    group = await ConnectionGroupService.get_group(db, group_id)
    email_partial = await _notify_request_received_and_pending(
        db, group=group, patron_id=data.patron_id,
    )
    content = ConfidentialJoinRequestResponse(
        id=payload["id"],
        group_id=payload["group_id"],
        patron_id=payload["patron_id"],
        status=payload["status"],
        requested_at=payload.get("requested_at") or datetime.now(timezone.utc),
        requested_by_id=payload["requested_by_id"],
        estimated_response_window_hours=payload["estimated_response_window_hours"],
        email_partial=email_partial,
    ).model_dump(mode="json")
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=content)


@router.get(
    "/connection-groups/{group_id}/approval-queue",
    response_model=ApprovalQueueResponse,
)
async def get_approval_queue(
    group_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Facilitator + admin only. Returns pending requests + recent decisions."""
    group = await ConnectionGroupService.get_group(db, group_id)
    if group is None or not getattr(group, "confidential", False):
        # Spec: 404 (not 403) for non-confidential groups — the queue resource
        # simply doesn't exist for them.
        raise HTTPException(status_code=404, detail="Approval queue not found")
    if not await _caller_can_approve(db, current_user, group):
        raise HTTPException(
            status_code=403,
            detail="Approval queue is restricted to facilitator and admins",
        )
    try:
        result = await ConnectionGroupService.list_approval_queue(db, group_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    # Spec property #7: decision audit visible to library_admin only, not
    # general facilitators. Hide the log for non-admin facilitator callers.
    if current_user.role not in _ADMIN_ROLES:
        result = {**result, "approval_decision_log": []}
    return ApprovalQueueResponse.model_validate(result)


@router.post(
    "/connection-groups/{group_id}/approval-queue/{member_id}/decide",
    response_model=DecideRequestResponse,
)
async def decide_request(
    group_id: int,
    member_id: int,
    data: DecideRequestPayload,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Approve or deny a pending request. Facilitator + admin only."""
    group = await ConnectionGroupService.get_group(db, group_id)
    if group is None or not getattr(group, "confidential", False):
        raise HTTPException(status_code=404, detail="Approval queue not found")
    if not await _caller_can_approve(db, current_user, group):
        raise HTTPException(
            status_code=403,
            detail="Only the facilitator or an admin can decide requests",
        )
    try:
        payload = await ConnectionGroupService.decide_request(
            db,
            group_id=group_id,
            member_id=member_id,
            decision=data.decision,
            decided_by_id=current_user.id,
            decision_note=data.decision_note,
            patron_message=data.patron_message,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from e
        raise HTTPException(status_code=400, detail=msg) from e

    if payload.get("already_decided"):
        # 409 with the current state body, per spec.
        content = DecideRequestResponse(
            id=payload["id"],
            group_id=payload["group_id"],
            patron_id=payload["patron_id"],
            status=payload["status"],
            decided_at=payload["decided_at"] or datetime.now(timezone.utc),
            decided_by_id=payload["decided_by_id"] or current_user.id,
            email_partial=False,
        ).model_dump(mode="json")
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=content)

    email_partial = await _notify_decision(
        db,
        group=group,
        patron_id=payload["patron_id"],
        decision=data.decision,
        patron_message=data.patron_message,
    )
    return DecideRequestResponse(
        id=payload["id"],
        group_id=payload["group_id"],
        patron_id=payload["patron_id"],
        status=payload["status"],
        decided_at=payload["decided_at"],
        decided_by_id=payload["decided_by_id"],
        email_partial=email_partial,
    )


@router.delete("/connection-groups/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_connection_group_member(
    group_id: int,
    user_id: int,
    reason: str = Query(..., description="Short-code removal reason (audit trail)."),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff-mediated remove. Requires ?reason= for audit trail."""
    if reason not in _REMOVAL_REASONS:
        # FastAPI Query has no easy enum-pattern for free-form short codes; do
        # explicit validation so the error message is helpful.
        raise HTTPException(
            status_code=422,
            detail=f"reason must be one of {sorted(_REMOVAL_REASONS)}",
        )
    try:
        await ConnectionGroupService.staff_remove(
            db,
            group_id=group_id,
            patron_id=user_id,
            removed_by_id=current_user.id,
            reason=reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ============================================================================
# Component 5c: Lifecycle (cg_lifecycle_001) — archive/unarchive + meeting CRUD
# ============================================================================
#
# All routes here are library_admin-gated. They share three helpers:
#   * _get_group_or_404: read + 404 short-circuit
#   * _get_meeting_or_404: scoped to group_id so we never leak meetings
#     across groups when an admin types the wrong id
#   * _dispatch_meeting_emails: per-member send loop that records the
#     dispatch count back onto the meeting row and surfaces email_partial
#     when the daily-cap safeguard truncates a batch.


async def _get_group_or_404(
    db: AsyncSession, group_id: int
) -> ParentConnectionGroup:
    group = await ConnectionGroupService.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Connection group not found")
    return group


async def _get_meeting_or_404(
    db: AsyncSession, group_id: int, meeting_id: int
) -> ParentConnectionGroupMeeting:
    q = select(ParentConnectionGroupMeeting).where(
        ParentConnectionGroupMeeting.id == meeting_id,
        ParentConnectionGroupMeeting.group_id == group_id,
    )
    result = await db.execute(q)
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


async def _dispatch_meeting_emails(
    db: AsyncSession,
    *,
    group: ParentConnectionGroup,
    meeting: ParentConnectionGroupMeeting,
    kind: str,
    new_meeting: Optional[ParentConnectionGroupMeeting] = None,
    patron_message: Optional[str] = None,
) -> tuple[int, bool, bool]:
    # Local import keeps the import graph clean — email.py imports config
    # which imports settings, and we don't want that on module load for a
    # rarely-hit code path.
    from ....core.email import (
        send_connection_group_meeting_cancelled_email,
        send_connection_group_meeting_rescheduled_email,
    )

    rows = await ConnectionGroupService.active_member_emails(db, group.id)
    dispatched = 0
    partial = False
    for patron_id, email, first_name in rows:
        try:
            user_like = type("U", (), {
                "email": email, "first_name": first_name, "id": patron_id,
            })()
            if kind == "cancelled":
                logger.info(
                    "EMAIL_SEND connection_group_meeting_cancelled user=%s group=%s meeting=%s",
                    patron_id, group.id, meeting.id,
                )
                ok = await send_connection_group_meeting_cancelled_email(
                    user_like, group, meeting, patron_message=patron_message,
                )
            elif kind == "rescheduled":
                logger.info(
                    "EMAIL_SEND connection_group_meeting_rescheduled user=%s group=%s meeting=%s -> %s",
                    patron_id, group.id, meeting.id,
                    getattr(new_meeting, "id", None),
                )
                ok = await send_connection_group_meeting_rescheduled_email(
                    user_like, group, meeting, new_meeting,
                    patron_message=patron_message,
                )
            else:
                ok = False
            if ok:
                dispatched += 1
            else:
                partial = True
        except Exception:
            logger.exception(
                "connection_group meeting notification failed",
                extra={
                    "patron_id": patron_id,
                    "group_id": group.id,
                    "meeting_id": meeting.id,
                    "kind": kind,
                },
            )
            partial = True

    # Audit columns on the historical (cancelled / rescheduled) row.
    meeting.email_dispatched_at = datetime.now(timezone.utc)
    meeting.email_dispatched_count = dispatched
    await db.flush()
    return dispatched, dispatched > 0, partial


@router.post(
    "/connection-groups/{group_id}/archive",
    response_model=ArchiveGroupResponse,
)
async def archive_connection_group(
    group_id: int,
    data: ArchiveGroupRequest,
    current_user: User = Depends(require_library_admin),
    db: AsyncSession = Depends(get_db),
):
    """Archive a connection group (library_admin only).

    Spec UX: archiving is the "this cohort is done" flow. Members are NOT
    removed (historical roster + attendance counts stay readable).
    Optionally emails members with a wrap-up note when ``notify_members``
    is True — that path uses the ``connection_group_archived`` Resend tag
    (distinct from cancel/reschedule).
    """
    group = await _get_group_or_404(db, group_id)
    if not group.is_active:
        # Idempotency: 404 on already-archived to keep the UI simple.
        raise HTTPException(status_code=404, detail="Group is already archived")

    await ConnectionGroupService.archive_group(
        db,
        group=group,
        archived_by_id=current_user.id,
        archive_reason=data.archive_reason,
        archive_notes=data.archive_notes,
    )

    notified = 0
    email_dispatched = False
    email_partial = False
    if data.notify_members:
        from ....core.email import send_connection_group_archived_email
        # Archive notice goes to active + waitlisted (spec); call list_members
        # to scoop both, then send unique-by-email.
        member_rows = await ConnectionGroupService.list_members(db, group_id)
        seen_emails: set[str] = set()
        for row in member_rows:
            # Need to look up the user — list_members returns patron_name not
            # email. Cheap single-row lookup per recipient is fine at L30 scale.
            patron_q = await db.execute(
                select(User).where(User.id == row["patron_id"])
            )
            patron = patron_q.scalar_one_or_none()
            if not patron or not patron.email or patron.email in seen_emails:
                continue
            seen_emails.add(patron.email)
            try:
                logger.info(
                    "EMAIL_SEND connection_group_archived user=%s group=%s",
                    patron.id, group.id,
                )
                ok = await send_connection_group_archived_email(
                    patron, group, patron_message=data.patron_message,
                )
                if ok:
                    notified += 1
                    email_dispatched = True
                else:
                    email_partial = True
            except Exception:
                logger.exception(
                    "connection_group archive notification failed",
                    extra={"patron_id": patron.id, "group_id": group.id},
                )
                email_partial = True

    return ArchiveGroupResponse(
        id=group.id,
        is_active=group.is_active,
        archived_at=group.archived_at,
        archived_by_id=group.archived_by_id,
        archive_reason=group.archive_reason,
        archive_notes=group.archive_notes,
        notified_member_count=notified,
        email_dispatched=email_dispatched,
        email_partial=email_partial,
    )


@router.post(
    "/connection-groups/{group_id}/unarchive",
    response_model=ArchiveGroupResponse,
)
async def unarchive_connection_group(
    group_id: int,
    current_user: User = Depends(require_library_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reverse an archive. Restores is_active=True and clears the audit
    columns. Sends no patron emails (unarchive is rare + low-signal)."""
    group = await _get_group_or_404(db, group_id)
    if group.is_active:
        raise HTTPException(status_code=404, detail="Group is not archived")
    await ConnectionGroupService.unarchive_group(db, group=group)
    return ArchiveGroupResponse(
        id=group.id,
        is_active=group.is_active,
        archived_at=group.archived_at,
        archived_by_id=group.archived_by_id,
        archive_reason=group.archive_reason,
        archive_notes=group.archive_notes,
    )


@router.get(
    "/connection-groups/{group_id}/meetings",
    response_model=GroupMeetingsListResponse,
)
async def list_connection_group_meetings(
    group_id: int,
    current_user: User = Depends(require_library_admin),
    db: AsyncSession = Depends(get_db),
):
    """List meeting instances for a connection group.

    Lazy materialization: the first call on a group materializes the next
    8 upcoming meeting dates from the recurring schedule. Subsequent calls
    only add more if fewer than 8 upcoming-scheduled rows exist (e.g.
    after some get cancelled). Existing rows are never regenerated, so
    individual reschedules + cancellations survive across reads.
    """
    group = await _get_group_or_404(db, group_id)
    meetings = await ConnectionGroupService.list_meetings(db, group=group)
    return GroupMeetingsListResponse(
        meetings=[GroupMeetingResponse.model_validate(m) for m in meetings],
        total=len(meetings),
    )


@router.post(
    "/connection-groups/{group_id}/meetings/{meeting_id}/cancel",
    response_model=MeetingDispatchResponse,
)
async def cancel_connection_group_meeting(
    group_id: int,
    meeting_id: int,
    data: CancelMeetingRequest,
    current_user: User = Depends(require_library_admin),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a single meeting instance and email active members.

    Errors:
      * 404 — group or meeting not found, or group is archived.
      * 422 — meeting is already in the past, or already cancelled.

    Email send failures do NOT 500 the route. The response carries
    ``email_partial=True`` when at least one send dropped (Resend error,
    daily-cap hit, or per-row exception). See
    feedback_l30_email_safeguard_cap_masks_failure for the why.
    """
    group = await _get_group_or_404(db, group_id)
    if not group.is_active:
        raise HTTPException(status_code=404, detail="Group is archived")
    meeting = await _get_meeting_or_404(db, group_id, meeting_id)

    if meeting.status == "cancelled":
        raise HTTPException(status_code=422, detail="Meeting is already cancelled")
    if meeting.meeting_date < date.today():
        raise HTTPException(status_code=422, detail="Meeting is in the past")

    await ConnectionGroupService.cancel_meeting(
        db,
        meeting=meeting,
        cancelled_by_id=current_user.id,
        reason=data.reason,
        staff_notes=data.notes,
        patron_message=data.patron_message,
    )

    dispatched, email_dispatched, email_partial = await _dispatch_meeting_emails(
        db,
        group=group,
        meeting=meeting,
        kind="cancelled",
        patron_message=data.patron_message,
    )
    # Refresh the meeting so the response carries the persisted
    # email_dispatched_at + email_dispatched_count audit columns.
    await db.refresh(meeting)

    return MeetingDispatchResponse(
        meeting=GroupMeetingResponse.model_validate(meeting),
        notified_member_count=dispatched,
        email_dispatched=email_dispatched,
        email_partial=email_partial,
    )


@router.post(
    "/connection-groups/{group_id}/meetings/{meeting_id}/reschedule",
    response_model=MeetingDispatchResponse,
)
async def reschedule_connection_group_meeting(
    group_id: int,
    meeting_id: int,
    data: RescheduleMeetingRequest,
    current_user: User = Depends(require_library_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reschedule a single meeting instance and email active members.

    Implementation: marks the original row as ``rescheduled`` and creates
    a fresh row on the new date. Per spec, no cascade to future meetings —
    if the admin needs to move the entire series, they reschedule per-date.

    Errors:
      * 404 — group or meeting not found, group archived.
      * 422 — original meeting is already past or already cancelled/rescheduled.
      * 422 — new_date conflicts with an existing scheduled row in this group.
    """
    group = await _get_group_or_404(db, group_id)
    if not group.is_active:
        raise HTTPException(status_code=404, detail="Group is archived")
    meeting = await _get_meeting_or_404(db, group_id, meeting_id)

    if meeting.status != "scheduled":
        raise HTTPException(
            status_code=422,
            detail=f"Cannot reschedule a meeting in status '{meeting.status}'",
        )
    if meeting.meeting_date < date.today():
        raise HTTPException(status_code=422, detail="Meeting is in the past")

    # Pre-flight: reject if new_date collides with another scheduled row.
    # The unique index would catch this on flush, but a clean 422 is
    # friendlier than letting the integrity error bubble.
    collision_q = await db.execute(
        select(ParentConnectionGroupMeeting).where(
            ParentConnectionGroupMeeting.group_id == group_id,
            ParentConnectionGroupMeeting.meeting_date == data.new_date,
            ParentConnectionGroupMeeting.status == "scheduled",
        )
    )
    if collision_q.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=422,
            detail="A scheduled meeting already exists on that date",
        )

    old, new = await ConnectionGroupService.reschedule_meeting(
        db,
        group=group,
        meeting=meeting,
        rescheduled_by_id=current_user.id,
        new_date=data.new_date,
        new_time=data.new_time,
        new_location=data.new_location,
        staff_notes=data.notes,
        patron_message=data.patron_message,
    )

    dispatched, email_dispatched, email_partial = await _dispatch_meeting_emails(
        db,
        group=group,
        meeting=old,
        new_meeting=new,
        kind="rescheduled",
        patron_message=data.patron_message,
    )
    await db.refresh(old)
    await db.refresh(new)

    return MeetingDispatchResponse(
        meeting=GroupMeetingResponse.model_validate(old),
        new_meeting=GroupMeetingResponse.model_validate(new),
        notified_member_count=dispatched,
        email_dispatched=email_dispatched,
        email_partial=email_partial,
    )
