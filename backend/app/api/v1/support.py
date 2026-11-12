# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Support Tickets API
Handles creation and management of support tickets and escalations from guided walkthroughs.

Includes:
- Patron-facing POST /support/tickets with honeypot + rate limit
- Staff-facing list/detail/patch/claim/release/respond endpoints
- Audit history via SupportTicketEvent
"""

from app.core.logging import get_logger
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.email import send_email
from ...core.rate_limit import limiter
from ...core.turnstile import verify_turnstile
from ...models.support_ticket import (
    SupportTicket,
    SupportTicketCategory,
    SupportTicketContactMethod,
    SupportTicketEvent,
    SupportTicketEventType,
    SupportTicketStatus,
)
from ...models.user import User
from .auth import get_current_user, get_optional_user
from .dependencies import is_admin, require_admin, require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/support", tags=["support"])


# ============================================================================
# SLA mapping
# ============================================================================


# Business-day SLA per category. Patrons expect different windows from
# different desks; an acquisitions request reviewed at the monthly
# collection meeting must not show red after 2 days.
SLA_BUSINESS_DAYS_BY_CATEGORY: dict[str, int] = {
    SupportTicketCategory.CIRCULATION.value: 1,
    SupportTicketCategory.REFERENCE.value: 1,  # 24h
    SupportTicketCategory.PROGRAMS_EVENTS.value: 2,
    SupportTicketCategory.YOUTH.value: 2,
    SupportTicketCategory.TEEN.value: 2,
    SupportTicketCategory.ACQUISITIONS.value: 22,  # monthly
    SupportTicketCategory.ILL.value: 5,
    SupportTicketCategory.ACCESSIBILITY.value: 10,
    SupportTicketCategory.DISCRIMINATION.value: 10,
    SupportTicketCategory.BOOK_CONCERN.value: 10,
    SupportTicketCategory.RECORDS_REQUEST.value: 4,  # Ohio R.C. 149.43
    SupportTicketCategory.BOARD.value: 5,
    SupportTicketCategory.DONATION.value: 5,
    SupportTicketCategory.WEBSITE_BUG.value: 3,
    SupportTicketCategory.GENERAL.value: 2,
}
DEFAULT_SLA_BUSINESS_DAYS = 2


def business_days_between(start: datetime, end: datetime) -> int:
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if end <= start:
        return 0
    days = 0
    cur = start.date()
    end_d = end.date()
    while cur < end_d:
        cur = cur + timedelta(days=1)
        if cur.weekday() < 5:
            days += 1
    return days


def sla_for_category(category: Optional[str]) -> int:
    if not category:
        return DEFAULT_SLA_BUSINESS_DAYS
    return SLA_BUSINESS_DAYS_BY_CATEGORY.get(category, DEFAULT_SLA_BUSINESS_DAYS)


# ============================================================================
# Schemas
# ============================================================================


_VALID_CATEGORIES = {c.value for c in SupportTicketCategory}


# The patron contact page uses friendly camelCase category keys for its
# 2-step taxonomy. Map them to the canonical SupportTicketCategory enum
# values so the stored ``category`` column keeps a single namespace that
# the staff triage UI + SLA lookups already understand.
PATRON_CATEGORY_TO_ENUM: dict[str, str] = {
    "referenceHelp": SupportTicketCategory.REFERENCE.value,
    "accountCard": SupportTicketCategory.CIRCULATION.value,
    "programsEvents": SupportTicketCategory.PROGRAMS_EVENTS.value,
    "youthFamily": SupportTicketCategory.YOUTH.value,
    "teens": SupportTicketCategory.TEEN.value,
    "suggestPurchase": SupportTicketCategory.ACQUISITIONS.value,
    "interlibraryLoan": SupportTicketCategory.ILL.value,
    "accessibility": SupportTicketCategory.ACCESSIBILITY.value,
    "discrimination": SupportTicketCategory.DISCRIMINATION.value,
    "bookConcern": SupportTicketCategory.BOOK_CONCERN.value,
    "recordsRequest": SupportTicketCategory.RECORDS_REQUEST.value,
    "board": SupportTicketCategory.BOARD.value,
    "donation": SupportTicketCategory.DONATION.value,
    "websiteBug": SupportTicketCategory.WEBSITE_BUG.value,
    "other": SupportTicketCategory.GENERAL.value,
}


# Routing destination string stored on the ticket for staff triage filtering.
# Keyed by the enum value (snake_case) so both patron-form submissions and
# staff-edited categories produce a consistent route.
SUPPORT_CATEGORY_ROUTES: dict[str, str] = {
    SupportTicketCategory.REFERENCE.value: "reference",
    SupportTicketCategory.CIRCULATION.value: "circulation",
    SupportTicketCategory.PROGRAMS_EVENTS.value: "programs",
    SupportTicketCategory.YOUTH.value: "youth_services",
    SupportTicketCategory.TEEN.value: "youth_services",
    SupportTicketCategory.ACQUISITIONS.value: "acquisitions",
    SupportTicketCategory.ILL.value: "ill_desk",
    SupportTicketCategory.ACCESSIBILITY.value: "ada_coordinator",
    SupportTicketCategory.DISCRIMINATION.value: "title_vi_coordinator",
    SupportTicketCategory.BOOK_CONCERN.value: "reconsideration_committee",
    SupportTicketCategory.RECORDS_REQUEST.value: "records_officer",
    SupportTicketCategory.BOARD.value: "board_secretary",
    SupportTicketCategory.DONATION.value: "development",
    SupportTicketCategory.WEBSITE_BUG.value: "systems",
    SupportTicketCategory.GENERAL.value: "general",
}


def _resolve_patron_category(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    if raw in _VALID_CATEGORIES:
        return raw
    return PATRON_CATEGORY_TO_ENUM.get(raw)


class SupportTicketBase(BaseModel):

    name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=20)
    guide_title: Optional[str] = Field(default=None, max_length=255)
    step_number: Optional[int] = None
    total_steps: Optional[int] = None
    issue_description: str = Field(..., min_length=1)
    contact_method: str = Field(..., pattern="^(email|phone|visit|none)$")
    category: Optional[str] = Field(default=None, max_length=64)
    subject_line: Optional[str] = Field(default=None, max_length=255)
    is_anonymous: bool = False


class SupportTicketCreate(SupportTicketBase):

    timestamp: str = Field(..., description="ISO format timestamp from client")
    # Honeypot: legitimate clients leave this blank. Bots fill every field.
    # Hidden via CSS on the patron form.
    website_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Honeypot. Do not fill.",
    )
    turnstile_token: Optional[str] = Field(
        default=None,
        description="Cloudflare Turnstile token from the public contact form",
    )


class SupportTicketUpdate(BaseModel):

    status: Optional[str] = Field(default=None, pattern="^(open|in_progress|resolved|closed)$")
    category: Optional[str] = Field(default=None, max_length=64)
    assigned_to_id: Optional[int] = Field(default=None, description="-1 to release")
    internal_notes: Optional[str] = None


class SupportTicketResponseSchema(BaseModel):

    ticket_id: str
    status: str
    reference_number: str
    message: str
    category: Optional[str] = None
    response_route: Optional[str] = None
    sla_business_days: Optional[int] = None

    class Config:
        from_attributes = True


class SupportTicketDetail(BaseModel):

    id: int
    ticket_number: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str]
    guide_title: Optional[str]
    step_number: Optional[int]
    total_steps: Optional[int]
    issue_description: str
    contact_method: str
    status: str
    category: Optional[str] = None
    subject_line: Optional[str] = None
    is_anonymous: bool = False
    response_route: Optional[str] = None
    submitted_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    assigned_to_id: Optional[int] = None
    internal_notes: Optional[str]
    sla_business_days: Optional[int] = None
    age_business_days: Optional[int] = None
    sla_breached: bool = False

    class Config:
        from_attributes = True


class SupportTicketListResponse(BaseModel):

    tickets: List[SupportTicketDetail]
    total: int


class TicketNoteCreate(BaseModel):
    note: str = Field(..., min_length=1)


class TicketResponseCreate(BaseModel):

    body: str = Field(..., min_length=1)
    set_status: Optional[str] = Field(
        default=None,
        pattern="^(in_progress|resolved|closed)$",
        description="If set, transition the ticket to this status when the response is logged.",
    )


class SupportTicketEventOut(BaseModel):
    id: int
    event_type: str
    actor_identifier: Optional[str]
    from_value: Optional[str]
    to_value: Optional[str]
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Helper Functions
# ============================================================================


def generate_ticket_number() -> str:
    now = datetime.now(timezone.utc)
    year = now.year
    random_part = str(uuid.uuid4()).replace("-", "")[:8].upper()
    return f"SUPPORT-{year}-{random_part}"


def _actor_id(user: Optional[User]) -> Optional[str]:
    if user is None:
        return None
    parts = []
    if getattr(user, "email", None):
        parts.append(f"email:{user.email}")
    if not parts:
        parts.append(f"id:{user.id}")
    return "|".join(parts)


async def _record_event(
    db: AsyncSession,
    *,
    ticket: SupportTicket,
    event_type: SupportTicketEventType,
    actor: Optional[User] = None,
    from_value: Optional[str] = None,
    to_value: Optional[str] = None,
    note: Optional[str] = None,
) -> None:
    try:
        evt = SupportTicketEvent(
            ticket_id=ticket.id,
            event_type=event_type.value,
            actor_user_id=getattr(actor, "id", None),
            actor_identifier=_actor_id(actor),
            from_value=str(from_value) if from_value is not None else None,
            to_value=str(to_value) if to_value is not None else None,
            note=note,
        )
        db.add(evt)
        await db.flush()
    except Exception:  # noqa: BLE001 - audit must not break the request
        logger.exception("Failed to record support_ticket_event")


def _role_value(user: Optional[User]) -> str:
    role = getattr(user, "role", None) if user else None
    if role is None:
        return ""
    return role.value if hasattr(role, "value") else str(role).lower()


def _is_staff(user: Optional[User]) -> bool:
    return _role_value(user) in {"staff", "admin", "super_admin", "director"}


def _is_admin(user: Optional[User]) -> bool:
    return _role_value(user) in {"admin", "super_admin", "director"}


def _serialize_detail(ticket: SupportTicket) -> SupportTicketDetail:
    sla = sla_for_category(ticket.category)
    age = None
    submitted = getattr(ticket, "submitted_at", None)
    if submitted is not None:
        end = ticket.resolved_at or datetime.now(timezone.utc)
        age = business_days_between(submitted, end)
    status_value = ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status)
    breached = (
        age is not None
        and age > sla
        and status_value not in ("resolved", "closed")
    )
    base = SupportTicketDetail.model_validate(ticket)
    return base.model_copy(
        update={
            "sla_business_days": sla,
            "age_business_days": age,
            "sla_breached": breached,
        }
    )


# ============================================================================
# Patron-facing endpoints
# ============================================================================


@router.post(
    "/tickets",
    response_model=SupportTicketResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/hour")
async def create_support_ticket(  # noqa: role-check -- public contact-page ticket creation, rate-limited
    request: Request,
    ticket_data: SupportTicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
) -> SupportTicketResponseSchema:
    """
    Create a new support ticket from a contact-page or escalation submission.

    Spam protection:
    - ``website_url`` is a honeypot. If filled, returns 201 with a fake
      reference number so the bot moves on, but never persists the row.
    - ``@limiter.limit("5/hour")`` per-IP via slowapi (Redis-backed).
    """

    # Honeypot: silently accept-and-drop. Returning 4xx tells the bot to
    # keep mutating; pretending success makes them stop.
    if ticket_data.website_url:
        logger.info(
            "Support honeypot triggered, ip=%s",
            request.client.host if request.client else "?",
        )
        fake = generate_ticket_number()
        return SupportTicketResponseSchema(
            ticket_id="0",
            status="open",
            reference_number=fake,
            message=f"Your support request has been received. Reference number: {fake}.",
        )

    # Cloudflare Turnstile bot verification -- gate BEFORE any DB work. The
    # honeypot above is the cheap first layer; this rejects scripted bots that
    # skip the widget. Fails open in dev when CF_TURNSTILE_SECRET is unset (see
    # core.turnstile); fails closed in production.
    if not await verify_turnstile(
        ticket_data.turnstile_token,
        request.client.host if request.client else None,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Captcha verification failed. Please retry.",
        )

    # Contact method. ``none`` is a contact-form path (under-13 / "no reply
    # needed") that the DB enum doesn't have. We store it as EMAIL with
    # email=None; triage UI keys off ``is_anonymous`` / null email instead
    # of contact_method to suppress reply UI.
    requested_method = ticket_data.contact_method
    if requested_method == "none":
        stored_method = SupportTicketContactMethod.EMAIL
    else:
        try:
            stored_method = SupportTicketContactMethod(requested_method)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid contact method. Must be one of: email, phone, visit, none",
            ) from None

    # Resolve the patron camelCase or canonical snake_case category to a
    # single canonical value. Unknown values 400 rather than silently
    # storing garbage.
    raw_category = ticket_data.category
    resolved_category: Optional[str] = None
    if raw_category:
        resolved_category = _resolve_patron_category(raw_category)
        if resolved_category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Invalid category. Must be a SupportTicketCategory enum "
                    f"value or a known patron-form key. Got: {raw_category!r}"
                ),
            )

    # Anonymous enforcement: strip identifiers server-side regardless of
    # what the client sent. This is defense-in-depth — the frontend already
    # omits these fields when the toggle is on.
    is_anonymous = bool(ticket_data.is_anonymous)

    submitted_name = (
        None if is_anonymous else (ticket_data.name.strip() if ticket_data.name else None)
    )
    submitted_email = (
        None
        if is_anonymous
        else (ticket_data.email.lower().strip() if ticket_data.email else None)
    )
    submitted_phone = (
        None if is_anonymous else (ticket_data.phone.strip() if ticket_data.phone else None)
    )

    # Per-method validation when not anonymous: a return channel requires
    # the matching contact info. visit / none collect no identifiers, so
    # only check email + phone/text.
    if not is_anonymous:
        if requested_method == "email" and not submitted_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email required when contact method is email.",
            )
        if requested_method == "phone" and not submitted_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone required when contact method is phone.",
            )

    response_route = (
        SUPPORT_CATEGORY_ROUTES.get(resolved_category) if resolved_category else None
    )

    ticket_number = generate_ticket_number()

    new_ticket = SupportTicket(
        ticket_number=ticket_number,
        name=submitted_name,
        email=submitted_email,
        phone=submitted_phone,
        guide_title=ticket_data.guide_title,
        step_number=ticket_data.step_number,
        total_steps=ticket_data.total_steps,
        issue_description=ticket_data.issue_description.strip(),
        contact_method=stored_method,
        category=resolved_category,
        subject_line=ticket_data.subject_line,
        is_anonymous=is_anonymous,
        response_route=response_route,
        status=SupportTicketStatus.OPEN,
        submitted_at=datetime.fromisoformat(ticket_data.timestamp),
    )

    db.add(new_ticket)
    await db.flush()

    await _record_event(
        db,
        ticket=new_ticket,
        event_type=SupportTicketEventType.CREATED,
        actor=current_user,
        to_value=ticket_number,
    )
    await db.commit()

    sla_days = sla_for_category(resolved_category)

    return SupportTicketResponseSchema(
        ticket_id=str(new_ticket.id),
        # After commit the ORM reloads ``status`` as a plain str (StrEnum-backed
        # column), so ``.value`` would raise; handle both str and enum.
        status=getattr(new_ticket.status, "value", new_ticket.status),
        reference_number=new_ticket.ticket_number,
        message=(
            f"Your support request has been received. Reference number: "
            f"{new_ticket.ticket_number}."
        ),
        category=resolved_category,
        response_route=response_route,
        sla_business_days=sla_days,
    )


@router.get("/tickets/user/me", response_model=SupportTicketListResponse)
async def get_user_support_tickets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> SupportTicketListResponse:
    """Get all support tickets for the current authenticated user by email."""

    query = (
        select(SupportTicket)
        .where(SupportTicket.email == current_user.email)
        .order_by(desc(SupportTicket.submitted_at))
    )
    count_query = (
        select(func.count())
        .select_from(SupportTicket)
        .where(SupportTicket.email == current_user.email)
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    tickets = result.scalars().all()

    return SupportTicketListResponse(
        tickets=[_serialize_detail(t) for t in tickets],
        total=total,
    )


# ============================================================================
# Staff-facing endpoints (list / detail / patch / events / responses)
# ============================================================================


@router.get("/tickets", response_model=SupportTicketListResponse)
async def list_support_tickets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
    status_filter: Optional[str] = Query(
        default=None,
        description="Filter by status: open, in_progress, resolved, closed, unassigned",
    ),
    category: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, max_length=200),
    submitted_from: Optional[date] = Query(default=None),
    submitted_to: Optional[date] = Query(default=None),
    assigned_to_id: Optional[int] = Query(default=None),
    sla_breached: Optional[bool] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SupportTicketListResponse:
    """List support tickets with filters (staff+)."""

    conditions = []

    if status_filter:
        if status_filter == "unassigned":
            conditions.append(
                and_(
                    SupportTicket.status == SupportTicketStatus.OPEN,
                    SupportTicket.assigned_to_id.is_(None),
                )
            )
        else:
            try:
                SupportTicketStatus(status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid status filter.",
                ) from None
            conditions.append(SupportTicket.status == SupportTicketStatus(status_filter))

    if category:
        if category not in _VALID_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category filter.",
            )
        conditions.append(SupportTicket.category == category)

    if assigned_to_id is not None:
        if assigned_to_id == 0:
            conditions.append(SupportTicket.assigned_to_id.is_(None))
        else:
            conditions.append(SupportTicket.assigned_to_id == assigned_to_id)

    if submitted_from:
        conditions.append(
            SupportTicket.submitted_at
            >= datetime.combine(submitted_from, datetime.min.time(), tzinfo=timezone.utc)
        )
    if submitted_to:
        end_of_day = datetime.combine(submitted_to, datetime.max.time(), tzinfo=timezone.utc)
        conditions.append(SupportTicket.submitted_at <= end_of_day)

    if search:
        like = f"%{search.lower()}%"
        conditions.append(
            or_(
                func.lower(SupportTicket.name).like(like),
                func.lower(SupportTicket.email).like(like),
                func.lower(SupportTicket.issue_description).like(like),
                func.lower(SupportTicket.ticket_number).like(like),
            )
        )

    base = select(SupportTicket)
    if conditions:
        base = base.where(and_(*conditions))

    count_query = select(func.count()).select_from(base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = base.order_by(desc(SupportTicket.submitted_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    tickets = result.scalars().all()

    serialized = [_serialize_detail(t) for t in tickets]
    if sla_breached is True:
        serialized = [t for t in serialized if t.sla_breached]
    elif sla_breached is False:
        serialized = [t for t in serialized if not t.sla_breached]

    return SupportTicketListResponse(tickets=serialized, total=total)


@router.get("/tickets/{ticket_id}", response_model=SupportTicketDetail)
async def get_support_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SupportTicketDetail:
    """Get a single ticket. Patrons see their own; staff+ see any."""

    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found",
        )

    # Staff need to view tickets to triage them; patrons can only view their own
    if not _is_staff(current_user) and ticket.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this ticket",
        )

    return _serialize_detail(ticket)


@router.get("/tickets/{ticket_id}/events", response_model=List[SupportTicketEventOut])
async def list_ticket_events(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> List[SupportTicketEventOut]:
    """Audit history for a ticket (staff+)."""

    exists = await db.execute(
        select(SupportTicket.id).where(SupportTicket.id == ticket_id)
    )
    if not exists.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Support ticket not found")

    result = await db.execute(
        select(SupportTicketEvent)
        .where(SupportTicketEvent.ticket_id == ticket_id)
        .order_by(asc(SupportTicketEvent.created_at))
    )
    events = result.scalars().all()
    return [SupportTicketEventOut.model_validate(e) for e in events]


@router.patch("/tickets/{ticket_id}", response_model=SupportTicketDetail)
async def update_support_ticket(
    ticket_id: int,
    update_data: SupportTicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> SupportTicketDetail:
    """
    Update a support ticket.

    - Staff can claim/release (set assigned_to_id = self.id or -1 to release).
    - Staff can change status (excluding close).
    - Admin+ can close, reassign to another user, and change category.
    """

    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Support ticket not found")

    is_admin = _is_admin(current_user)

    if (
        update_data.assigned_to_id is not None
        and update_data.assigned_to_id not in (-1, current_user.id, ticket.assigned_to_id)
        and not is_admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reassigning to another user requires admin role.",
        )

    if update_data.status:
        previous = ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status)
        if previous != update_data.status:
            if update_data.status == "closed" and not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Closing a ticket requires admin role.",
                )
            ticket.status = SupportTicketStatus(update_data.status)
            if update_data.status in ("resolved", "closed"):
                ticket.resolved_at = datetime.now(timezone.utc)
            elif previous in ("resolved", "closed"):
                ticket.resolved_at = None
            await _record_event(
                db,
                ticket=ticket,
                event_type=SupportTicketEventType.STATUS_CHANGED,
                actor=current_user,
                from_value=previous,
                to_value=update_data.status,
            )

    if update_data.category is not None:
        if update_data.category and update_data.category not in _VALID_CATEGORIES:
            raise HTTPException(status_code=400, detail="Invalid category.")
        previous_cat = ticket.category
        if previous_cat != update_data.category:
            ticket.category = update_data.category or None
            await _record_event(
                db,
                ticket=ticket,
                event_type=SupportTicketEventType.CATEGORY_CHANGED,
                actor=current_user,
                from_value=previous_cat,
                to_value=update_data.category,
            )

    if update_data.assigned_to_id is not None:
        previous_assignee = ticket.assigned_to_id
        if update_data.assigned_to_id == -1:
            if previous_assignee is not None:
                ticket.assigned_to_id = None
                await _record_event(
                    db,
                    ticket=ticket,
                    event_type=SupportTicketEventType.UNASSIGNED,
                    actor=current_user,
                    from_value=str(previous_assignee),
                    to_value=None,
                )
        else:
            if previous_assignee != update_data.assigned_to_id:
                ticket.assigned_to_id = update_data.assigned_to_id
                await _record_event(
                    db,
                    ticket=ticket,
                    event_type=SupportTicketEventType.ASSIGNED,
                    actor=current_user,
                    from_value=str(previous_assignee) if previous_assignee is not None else None,
                    to_value=str(update_data.assigned_to_id),
                )

    if update_data.internal_notes is not None:
        ticket.internal_notes = update_data.internal_notes.strip()

    ticket.updated_at = datetime.now(timezone.utc)
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    return _serialize_detail(ticket)


@router.post("/tickets/{ticket_id}/notes", response_model=SupportTicketDetail)
async def add_support_ticket_note(
    ticket_id: int,
    note_data: TicketNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> SupportTicketDetail:
    """Append an internal note to a ticket."""

    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Support ticket not found")

    timestamp = datetime.now(timezone.utc).isoformat()
    new_note = f"[{timestamp}] {current_user.email}: {note_data.note}"

    if ticket.internal_notes:
        ticket.internal_notes += f"\n{new_note}"
    else:
        ticket.internal_notes = new_note

    ticket.updated_at = datetime.now(timezone.utc)
    db.add(ticket)
    await _record_event(
        db,
        ticket=ticket,
        event_type=SupportTicketEventType.NOTE_ADDED,
        actor=current_user,
        note=note_data.note[:500],
    )
    await db.commit()
    await db.refresh(ticket)
    return _serialize_detail(ticket)


@router.post("/tickets/{ticket_id}/responses", response_model=SupportTicketDetail)
async def respond_to_support_ticket(
    ticket_id: int,
    payload: TicketResponseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> SupportTicketDetail:
    """
    Log an outbound response to the patron and deliver via email.

    Records a RESPONSE_SENT event with the body in ``note``. If
    ``set_status`` is provided, transitions the ticket and records a
    STATUS_CHANGED event as well. Email delivery goes through
    ``core.email.send_email`` (daily-cap + dedup enforced); a cap or
    dedup hit is logged but does not fail the endpoint.
    """

    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Support ticket not found")

    await _record_event(
        db,
        ticket=ticket,
        event_type=SupportTicketEventType.RESPONSE_SENT,
        actor=current_user,
        note=payload.body,
        to_value=ticket.email,
    )

    if ticket.email and not ticket.is_anonymous:
        await send_email(
            to_email=ticket.email,
            subject=f"Re: your support ticket #{ticket.ticket_number}",
            html_content=f"<p>{payload.body}</p>",
            categories=["support_response"],
            notification_type="support_response",
        )

    if payload.set_status:
        if payload.set_status == "closed" and not _is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Closing a ticket requires admin role.",
            )
        previous = ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status)
        if previous != payload.set_status:
            ticket.status = SupportTicketStatus(payload.set_status)
            if payload.set_status in ("resolved", "closed"):
                ticket.resolved_at = datetime.now(timezone.utc)
            await _record_event(
                db,
                ticket=ticket,
                event_type=SupportTicketEventType.STATUS_CHANGED,
                actor=current_user,
                from_value=previous,
                to_value=payload.set_status,
            )

    ticket.updated_at = datetime.now(timezone.utc)
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    return _serialize_detail(ticket)


@router.post("/tickets/{ticket_id}/close", response_model=SupportTicketDetail)
async def close_support_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SupportTicketDetail:
    """Close a ticket. Admin+ only."""

    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Support ticket not found")

    previous = ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status)
    ticket.status = SupportTicketStatus.CLOSED
    ticket.resolved_at = datetime.now(timezone.utc)
    ticket.updated_at = datetime.now(timezone.utc)

    db.add(ticket)
    if previous != "closed":
        await _record_event(
            db,
            ticket=ticket,
            event_type=SupportTicketEventType.STATUS_CHANGED,
            actor=current_user,
            from_value=previous,
            to_value="closed",
        )
    await db.commit()
    await db.refresh(ticket)
    return _serialize_detail(ticket)
