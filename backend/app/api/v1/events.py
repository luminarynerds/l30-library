# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Optional
from app.core.logging import get_logger
from app.core.branding import branding
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings

logger = get_logger(__name__)

from ...core.database import get_db
from ...core.pagination import PaginationParams, calculate_total_pages
from ...core.exceptions import InternalServerError
from ...core.error_codes import ErrorCode
from ...core.shortcuts import get_or_404
from ...core.rate_limit import limiter
from ...core.turnstile import verify_turnstile
from ...models.event import Event
from ...models.event_registration import EventRegistration, EventRegistrationStatus
from ...models.event_waitlist import (
    EventWaitlistEntry,
    WaitlistStatus,
)
from ...models.event_review import EventReview, ReviewModerationStatus
from ...models.user import User
from ...schemas.common import PaginatedResponse, PaginationInfo
from ...schemas.event import (
    EventBulkCreateDryRunResponse,
    EventBulkCreateRequest,
    EventBulkCreateResponse,
    EventBulkInstancePreview,
    EventCreate,
    EventResponse,
    EventUpdate,
    EventWithStats,
    RelatedEventsResponse,
)
from ...schemas.event_registration import (
    RegistrationCreate,
    RegistrationListResponse,
    RegistrationResponse,
    MyEventRegistrationResponse,
)
from ...schemas.event_review import (
    EventReviewCreate,
    EventReviewResponse,
    EventReviewSummary,
    EventReviewDetailResponse,
    ReviewModerationAction,
    ReviewModerationQueue,
    EventReviewEditRequest,
)
from dateutil.rrule import rrulestr
from ...services.event_recurrence import expand_event_instances
from .auth import get_current_user, get_optional_user
from .dependencies import require_staff
from app.services.notifications.types import NotificationType as NType
from .event_helpers import (
    branch_names_by_id as _branch_names_by_id,
    ensure_aware_start as _ensure_aware_start,
    normalize_email,
    send_event_email as _send_event_email,
)
from .event_calendar import (
    escape_ical as _ical_escape,
    fold_ical as _ical_fold,
    format_utc as _format_utc,
)
from .event_waitlist_routes import router as event_waitlist_router

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/tags", response_model=list[str])
@limiter.limit("60/minute")
async def list_event_tags(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get all unique tags used across published events."""
    # Get all unique tags from published events using PostgreSQL unnest
    result = await db.execute(
        select(func.unnest(Event.tags))
        .where(Event.is_published == True)
        .where(Event.tags.isnot(None))
        .distinct()
    )
    tags = [row[0] for row in result.all() if row[0]]
    return sorted(tags)


@router.get("/categories", response_model=list[str])
@limiter.limit("60/minute")
async def list_event_categories(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get all unique categories used across published events."""
    result = await db.execute(
        select(Event.category)
        .where(Event.is_published == True)
        .where(Event.category.isnot(None))
        .distinct()
    )
    categories = [row[0] for row in result.all() if row[0]]
    return sorted(categories)


@router.get("/audiences", response_model=list[str])
@limiter.limit("60/minute")
async def list_event_audiences(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get all unique audiences used across published events."""
    result = await db.execute(
        select(Event.audience)
        .where(Event.is_published == True)
        .where(Event.audience.isnot(None))
        .distinct()
    )
    audiences = [row[0] for row in result.all() if row[0]]
    return sorted(audiences)


# ---------------------------------------------------------------------------
# Public iCal subscription feed
# ---------------------------------------------------------------------------


@router.get("/calendar.ics")
async def events_ical_feed(
    request: Request,
    branch: int | None = Query(None, description="Filter by hosting branch id"),
    audience: str | None = Query(None, description="Filter by audience"),
    limit: int = Query(200, ge=1, le=500, description="Max events to include"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Public, subscribable iCal feed of upcoming published events.

    Mountable in Google Calendar / Apple Calendar / Outlook. Returns a single
    VCALENDAR with one VEVENT per published, upcoming event (with a 1-day tail
    so freshly-finished events remain discoverable, capped 6 months ahead).
    """
    settings = get_settings()
    site_url = settings.frontend_url.rstrip("/")
    parsed = urlparse(site_url)
    host = parsed.hostname or "l30.org"

    now = datetime.now(timezone.utc)
    lower_bound = now - timedelta(days=1)
    upper_bound = now + timedelta(days=183)  # ~6 months

    query = (
        select(Event)
        .where(Event.is_published == True)  # noqa: E712
        .where(Event.start_time >= lower_bound)
        .where(Event.start_time <= upper_bound)
        .order_by(Event.start_time.asc())
        .limit(limit)
    )
    if audience:
        query = query.where(Event.audience == audience)
    if branch is not None:
        query = query.where(Event.branch_id == branch)

    result = await db.execute(query)
    events = result.scalars().all()

    dtstamp = _format_utc(now)
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//L30 Community Library//Events//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_ical_escape('L30 Library Events')}",
        "X-WR-TIMEZONE:UTC",
    ]

    for event in events:
        start = event.start_time
        if event.end_time:
            end = event.end_time
        else:
            # Default to 1-hour duration if end_time is null.
            end = (start if start.tzinfo else start.replace(tzinfo=timezone.utc)) + timedelta(
                hours=1
            )

        last_modified = (
            getattr(event, "updated_at", None) or getattr(event, "created_at", None) or now
        )
        url = f"{site_url}/events/detail/{event.id}"

        categories: list[str] = []
        if event.tags:
            categories.extend(t for t in event.tags if t)
        if event.category:
            categories.append(event.category)

        ev_lines: list[str] = [
            "BEGIN:VEVENT",
            f"UID:event-{event.id}@{host}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{_format_utc(start)}",
            f"DTEND:{_format_utc(end)}",
            f"SUMMARY:{_ical_escape(event.title)}",
            "STATUS:CONFIRMED",
            f"URL:{url}",
            f"LAST-MODIFIED:{_format_utc(last_modified)}",
        ]
        if event.description:
            ev_lines.append(f"DESCRIPTION:{_ical_escape(event.description)}")
        # Prefer physical location; fall back to virtual link if virtual.
        loc = event.location or (event.virtual_link if event.is_virtual else None)
        if loc:
            ev_lines.append(f"LOCATION:{_ical_escape(loc)}")
        if categories:
            # Per RFC 5545, CATEGORIES is a comma-separated list of escaped TEXT values.
            ev_lines.append("CATEGORIES:" + ",".join(_ical_escape(c) for c in categories))
        ev_lines.append("END:VEVENT")
        lines.extend(ev_lines)

    lines.append("END:VCALENDAR")

    folded = "\r\n".join(_ical_fold(line) for line in lines) + "\r\n"

    return Response(
        content=folded,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'inline; filename="library-events.ics"',
            "Cache-Control": "public, max-age=900",
        },
    )


@router.get("/sitemap-events.xml", include_in_schema=False)
async def events_sitemap(db: AsyncSession = Depends(get_db)) -> Response:
    """sitemap.xml entries for published, upcoming, non-recurring events.

    Referenced from the static sitemap index (frontend/public/sitemap.xml).
    Excludes recurring parents and override children — each expanded instance
    is not a stable URL (see _published_upcoming_events in seo_meta.py for the
    same rationale). Caps at 200 future events to keep the response bounded.
    """
    settings = get_settings()
    base = settings.frontend_url.rstrip("/")
    now = datetime.now(timezone.utc)

    stmt = (
        select(Event)
        .where(Event.is_published == True)  # noqa: E712
        .where(Event.start_time >= now)
        .where(Event.recurrence_rule.is_(None))
        .where(Event.parent_event_id.is_(None))
        .order_by(Event.start_time)
        .limit(200)
    )
    result = await db.execute(stmt)
    events = result.scalars().all()

    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for ev in events:
        # lastmod: use updated_at when available (TimestampMixin), else start_time
        lastmod_dt = getattr(ev, "updated_at", None) or ev.start_time
        lastmod = lastmod_dt.date().isoformat() if lastmod_dt else now.date().isoformat()
        lines.append("  <url>")
        lines.append(f"    <loc>{base}/events/detail/{ev.id}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("    <changefreq>weekly</changefreq>")
        lines.append("    <priority>0.6</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    body = "\n".join(lines) + "\n"

    return Response(
        content=body,
        media_type="application/xml; charset=utf-8",
        headers={"Cache-Control": "public, max-age=1800"},
    )


# Accessibility provisions a patron can filter the events list by. The
# query-param token is the Event column name; the explicit whitelist keeps
# an `accessibility=` value from reaching an arbitrary model attribute.
_ACCESSIBILITY_FILTER_COLUMNS = {
    "wheelchair_accessible": Event.wheelchair_accessible,
    "asl_provided": Event.asl_provided,
    "captioning_provided": Event.captioning_provided,
    "assistive_listening": Event.assistive_listening,
    "sensory_friendly": Event.sensory_friendly,
    "large_print_available": Event.large_print_available,
}


@router.get("", response_model=PaginatedResponse[EventWithStats])
@limiter.limit("60/minute")
async def list_events(
    request: Request,
    response: Response,
    upcoming: bool = Query(True, description="Only show upcoming events"),
    category: str | None = Query(None),
    audience: str | None = Query(None),
    audiences: list[str] | None = Query(
        None,
        description=(
            "Filter by one or more audiences (OR semantics). When supplied, "
            "overrides the singular `audience` param. Repeat the query "
            "parameter: `?audiences=children&audiences=teens`."
        ),
    ),
    tag: str | None = Query(None, description="Filter by tag"),
    featured_only: bool = Query(False, description="Only show featured events"),
    series_id: str | None = Query(None, description="Filter by series ID"),
    search: str | None = Query(None, description="Search in title and description"),
    expand_recurrence: bool = Query(
        False,
        description=(
            "If true, events with a recurrence_rule are expanded into virtual "
            "instances within a 183-day horizon (matches the iCal feed). "
            "Pagination still applies to the BASE event list before expansion, "
            "so one recurring parent may yield many response rows."
        ),
    ),
    starts_after: datetime | None = Query(
        None,
        description=(
            "Only events whose start_time is at or after this instant "
            "(ISO 8601). AND-combined with `upcoming` and `starts_before`."
        ),
    ),
    starts_before: datetime | None = Query(
        None,
        description=(
            "Only events whose start_time is at or before this instant "
            "(ISO 8601). Paired with `starts_after` to express the time-window "
            "quick filters (today / this weekend / next 7 days)."
        ),
    ),
    drop_in: bool = Query(
        False,
        description="If true, only drop-in events (no registration required).",
    ),
    accessibility: list[str] | None = Query(
        None,
        description=(
            "Filter to events providing ALL listed accessibility provisions "
            "(AND semantics). Repeat the param: "
            "`?accessibility=wheelchair_accessible&accessibility=asl_provided`. "
            "Unknown tokens are ignored."
        ),
    ),
    branch_ids: list[int] | None = Query(
        None,
        description=(
            "Filter by hosting branch (OR semantics, like `audiences`). "
            "Repeat the param: `?branch_ids=1&branch_ids=2`. Events with no "
            "branch assigned are excluded when this filter is active."
        ),
    ),
    languages: list[str] | None = Query(
        None,
        description=(
            "Filter by program language (OR semantics, like `audiences`). "
            "Values are ISO 639-1 codes matched against `event_language`. "
            "Repeat the param: `?languages=es&languages=zh`."
        ),
    ),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[EventWithStats]:
    """List published events, optionally expanding recurring events into instances.

    Pagination note: page/per_page apply to the BASE Event rows. When
    `expand_recurrence=true`, each recurring parent in the page is replaced by
    its expanded virtual instances, so the response `data` length can exceed
    `per_page`. `pagination.total` still reflects the count of base rows, not
    of expanded instances.

    Virtual instances have `id=None`, `is_virtual_instance=True`, and the
    parent's PK in `parent_event_id`. See EventWithStats docstring for the
    convention; see app/services/event_recurrence.py for the expander.
    """
    query = select(Event).where(Event.is_published == True)
    count_query = select(func.count(Event.id)).where(Event.is_published == True)

    if upcoming:
        now = datetime.now(timezone.utc)
        query = query.where(Event.start_time >= now)
        count_query = count_query.where(Event.start_time >= now)

    if category:
        query = query.where(Event.category == category)
        count_query = count_query.where(Event.category == category)

    if audiences:
        # Multi-select OR: match any audience in the list.
        query = query.where(Event.audience.in_(audiences))
        count_query = count_query.where(Event.audience.in_(audiences))
    elif audience:
        query = query.where(Event.audience == audience)
        count_query = count_query.where(Event.audience == audience)

    if tag:
        # Filter by tag - uses PostgreSQL array contains operator
        query = query.where(Event.tags.any(tag))
        count_query = count_query.where(Event.tags.any(tag))

    if featured_only:
        query = query.where(Event.is_featured == True)
        count_query = count_query.where(Event.is_featured == True)

    if series_id:
        query = query.where(Event.series_id == series_id)
        count_query = count_query.where(Event.series_id == series_id)

    if search:
        # Case-insensitive search in title and description
        search_pattern = f"%{search}%"
        search_filter = or_(
            Event.title.ilike(search_pattern), Event.description.ilike(search_pattern)
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if starts_after:
        query = query.where(Event.start_time >= starts_after)
        count_query = count_query.where(Event.start_time >= starts_after)

    if starts_before:
        query = query.where(Event.start_time <= starts_before)
        count_query = count_query.where(Event.start_time <= starts_before)

    if drop_in:
        # A "drop-in" event is one that needs no registration — the same
        # semantic the EventCard registration pill already uses.
        query = query.where(Event.registration_required == False)
        count_query = count_query.where(Event.registration_required == False)

    if languages:
        # OR semantics, mirroring `audiences`: match any requested language.
        query = query.where(Event.event_language.in_(languages))
        count_query = count_query.where(Event.event_language.in_(languages))

    if branch_ids:
        # OR semantics, mirroring `audiences`: match any requested branch.
        query = query.where(Event.branch_id.in_(branch_ids))
        count_query = count_query.where(Event.branch_id.in_(branch_ids))

    if accessibility:
        # AND semantics: an event must provide EVERY requested provision.
        # Unknown tokens are skipped (the column map is the whitelist) so a
        # stale client cannot 500 the list endpoint.
        for token in accessibility:
            column = _ACCESSIBILITY_FILTER_COLUMNS.get(token)
            if column is not None:
                query = query.where(column == True)
                count_query = count_query.where(column == True)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Sort by featured status first (featured events come first), then by start time
    query = (
        query.offset(pagination.offset)
        .limit(pagination.limit)
        .order_by(Event.is_featured.desc(), Event.start_time)
    )

    result = await db.execute(query)
    events = result.scalars().all()

    # Get registration counts for each event
    event_ids = [e.id for e in events]
    reg_counts = {}
    if event_ids:
        count_result = await db.execute(
            select(EventRegistration.event_id, func.count(EventRegistration.id))
            .where(EventRegistration.event_id.in_(event_ids))
            .where(EventRegistration.status == EventRegistrationStatus.CONFIRMED.value)
            .group_by(EventRegistration.event_id)
        )
        reg_counts = dict(count_result.all())

    # Get average ratings for past events (only approved, non-removed reviews).
    # Coerce naive starts to UTC: SQLite (test fallback) drops tzinfo on read
    # round-trips even when the column is DateTime(timezone=True), so the
    # comparison with `now` would otherwise TypeError.
    now = datetime.now(timezone.utc)
    past_event_ids = [e.id for e in events if _ensure_aware_start(e.start_time) < now]
    avg_ratings = {}
    review_counts = {}
    if past_event_ids:
        rating_result = await db.execute(
            select(EventReview.event_id, func.avg(EventReview.rating), func.count(EventReview.id))
            .where(EventReview.event_id.in_(past_event_ids))
            .where(EventReview.moderation_status == ReviewModerationStatus.APPROVED.value)
            .where(EventReview.is_removed == 0)
            .group_by(EventReview.event_id)
        )
        for row in rating_result.all():
            avg_ratings[row[0]] = round(float(row[1]), 1)
            review_counts[row[0]] = row[2]

    # 183 days matches the iCal feed horizon (PR #555); rationale: prevents
    # runaway expansion of unbounded RRULEs while still covering ~6 months.
    expansion_window_end = datetime.now(timezone.utc) + timedelta(days=183)

    branch_names = await _branch_names_by_id(db, {e.branch_id for e in events})

    items: list[EventWithStats] = []
    for e in events:
        reg_count = reg_counts.get(e.id, 0)
        spots_remaining = None
        if e.max_attendees:
            spots_remaining = max(0, e.max_attendees - reg_count)

        base_payload = EventResponse.model_validate(e).model_dump()
        base_payload["branch_name"] = branch_names.get(e.branch_id)

        # When expand_recurrence is on AND this row has an RRULE, replace it
        # with its virtual instances. Otherwise it passes through unchanged.
        # ID convention for virtual instances: id=None + is_virtual_instance=True
        # + parent_event_id=<parent PK>. Chosen over a string composite id
        # because EventResponse.id is typed `int` upstream; making it Optional
        # only on EventWithStats keeps the contract change scoped to this list
        # endpoint, and consumers already know `parent_event_id`.
        if expand_recurrence and e.recurrence_rule:
            instances = expand_event_instances(e, expansion_window_end)
            for inst in instances:
                inst_payload = dict(base_payload)
                inst_payload["id"] = None
                inst_payload["parent_event_id"] = inst["parent_event_id"]
                inst_payload["start_time"] = inst["start_time"]
                inst_payload["end_time"] = inst["end_time"]
                # recurrence_rule is intentionally kept on each instance so
                # consumers can still identify the source rule, but instances
                # themselves are not further expandable (id=None).
                items.append(
                    EventWithStats(
                        **inst_payload,
                        is_virtual_instance=True,
                        registration_count=reg_count,
                        spots_remaining=spots_remaining,
                        average_rating=avg_ratings.get(e.id),
                        review_count=review_counts.get(e.id, 0),
                    )
                )
        else:
            items.append(
                EventWithStats(
                    **base_payload,
                    registration_count=reg_count,
                    spots_remaining=spots_remaining,
                    average_rating=avg_ratings.get(e.id),
                    review_count=review_counts.get(e.id, 0),
                )
            )

    # When expansion is active, ensure the combined list is ordered by
    # start_time (the base query ordered by featured-then-start, but post-
    # expansion the virtual instances need to be re-sorted into place).
    if expand_recurrence:
        items.sort(key=lambda it: _ensure_aware_start(it.start_time))

    # Cache-Control: the anonymous public events list is identical for all
    # anonymous viewers, so promote it to a CDN-cacheable response when there
    # is no Authorization header. CachingHeadersMiddleware only sets headers
    # when none exist, so this assignment wins. SWR=600 lets edges serve a
    # stale list for 10 minutes while revalidating in the background.
    if "authorization" not in {k.lower() for k in request.headers.keys()}:
        response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"

    total_pages = calculate_total_pages(total, pagination.page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationInfo(
            page=pagination.page,
            per_page=pagination.page_size,
            total=total,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1,
        ),
    )


@router.get("/my-registrations", response_model=list[MyEventRegistrationResponse])
async def get_my_registrations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's event registrations with full event details."""
    # Match by user_id first (stable even after email change or NULL email),
    # then fall back to email for legacy rows not yet backfilled and for any
    # edge case where user_id is NULL despite a matching email address.
    result = await db.execute(
        select(
            EventRegistration.id,
            EventRegistration.event_id,
            EventRegistration.status,
            EventRegistration.registered_at,
            EventRegistration.reminder_requested,
            Event.title,
            Event.start_time,
            Event.end_time,
            Event.location,
            Event.category,
        )
        .join(Event, Event.id == EventRegistration.event_id)
        .where(
            or_(
                EventRegistration.user_id == current_user.id,
                (
                    EventRegistration.user_id.is_(None)
                    & (func.lower(EventRegistration.patron_email) == func.lower(current_user.email))
                ),
            )
        )
        .where(EventRegistration.status != EventRegistrationStatus.CANCELLED.value)
        .where(Event.start_time >= datetime.now(timezone.utc))
        .order_by(Event.start_time.asc())
    )
    rows = result.all()
    return [
        MyEventRegistrationResponse(
            id=row.id,
            event_id=row.event_id,
            status=row.status,
            registered_at=row.registered_at,
            reminder_requested=row.reminder_requested or False,
            event_title=row.title or "Unknown Event",
            event_start_time=row.start_time,
            event_end_time=row.end_time,
            event_location=row.location,
            event_category=row.category,
        )
        for row in rows
    ]


# ============================================================================
# Event Review Moderation Endpoints
# ============================================================================


@router.get("/moderation/queue", response_model=PaginatedResponse[ReviewModerationQueue])
async def get_moderation_queue(
    pagination: PaginationParams = Depends(),
    status_filter: str = Query(
        "PENDING", description="Filter by status: PENDING, APPROVED, REJECTED"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get moderation queue for staff to review pending reviews.
    Requires staff or admin role.
    """
    # Build base count query
    count_query = select(func.count(EventReview.id)).join(Event, EventReview.event_id == Event.id)

    # Build base data query
    query = select(EventReview, Event.title).join(Event, EventReview.event_id == Event.id)

    # Filter by status
    if status_filter.upper() in ["PENDING", "APPROVED", "REJECTED"]:
        _status = status_filter.lower()
        query = query.where(EventReview.moderation_status == _status)
        count_query = count_query.where(EventReview.moderation_status == _status)

    # Count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Order by created_at descending (newest first)
    query = (
        query.order_by(EventReview.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )

    result = await db.execute(query)
    rows = result.all()

    # Convert rows to ReviewModerationQueue responses
    items = []
    for review, event_title in rows:
        items.append(
            ReviewModerationQueue(
                id=review.id,
                event_id=review.event_id,
                event_title=event_title,
                patron_email=review.patron_email,
                rating=review.rating,
                comment=review.comment,
                created_at=review.created_at,
                moderation_status=review.moderation_status,
            )
        )

    total_pages = calculate_total_pages(total, pagination.page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationInfo(
            page=pagination.page,
            per_page=pagination.page_size,
            total=total,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1,
        ),
    )


@router.post("/reviews/{review_id}/moderate", response_model=EventReviewDetailResponse)
async def moderate_review(
    review_id: int,
    action: ReviewModerationAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Perform moderation action on a review (approve/reject/remove).
    Requires staff or admin role.

    Actions:
    - approve: Approve the review for display
    - reject: Reject the review (don't display, but keep record)
    - remove: Remove inappropriate content (set is_removed flag)
    """
    # Get the review
    review = await get_or_404(db, EventReview, review_id, "Review not found")

    now = datetime.now(timezone.utc)
    action_lower = action.action.lower()

    if action_lower == "approve":
        review.moderation_status = ReviewModerationStatus.APPROVED.value
        review.moderated_by = current_user.email
        review.moderated_at = now
        review.moderation_reason = action.reason
        logger.info(f"Review {review_id} approved by user_id={current_user.id}")

    elif action_lower == "reject":
        review.moderation_status = ReviewModerationStatus.REJECTED.value
        review.moderated_by = current_user.email
        review.moderated_at = now
        review.moderation_reason = action.reason
        logger.info(f"Review {review_id} rejected by user_id={current_user.id}: {action.reason}")

    elif action_lower == "remove":
        review.is_removed = 1
        review.removed_by = current_user.email
        review.removed_at = now
        review.removal_reason = action.reason
        logger.warning(f"Review {review_id} removed by user_id={current_user.id}: {action.reason}")

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'approve', 'reject', or 'remove'",
        )

    await db.commit()
    await db.refresh(review)

    return EventReviewDetailResponse.model_validate(review)


@router.patch("/reviews/{review_id}/hide", response_model=EventReviewDetailResponse)
async def hide_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Hide a review from public display by flipping moderation_status to REJECTED.
    Staff-only escape hatch for the trust-by-default review flow.
    """
    review = await get_or_404(db, EventReview, review_id, "Review not found")

    review.moderation_status = ReviewModerationStatus.REJECTED.value
    review.moderated_by = current_user.email
    review.moderated_at = datetime.now(timezone.utc)
    review.moderation_reason = "Hidden by staff"

    await db.commit()
    await db.refresh(review)

    logger.info(f"Review {review_id} hidden by user_id={current_user.id}")

    return EventReviewDetailResponse.model_validate(review)


@router.patch("/reviews/{review_id}/edit", response_model=EventReviewDetailResponse)
async def edit_review_by_staff(
    review_id: int,
    edit: EventReviewEditRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Edit a review comment as part of moderation workflow.
    This action approves the review after edits unless removed separately.
    """
    review = await get_or_404(db, EventReview, review_id, "Review not found")

    now = datetime.now(timezone.utc)

    review.comment = edit.comment
    review.moderation_status = ReviewModerationStatus.APPROVED.value
    review.moderated_by = current_user.email
    review.moderated_at = now
    if edit.reason:
        review.moderation_reason = f"Edited by staff: {edit.reason}"
    else:
        review.moderation_reason = "Edited by staff"

    review.is_removed = 0
    review.removal_reason = None
    review.removed_by = None
    review.removed_at = None

    await db.commit()
    await db.refresh(review)

    logger.info(f"Review {review_id} edited by user_id={current_user.id}")

    return EventReviewDetailResponse.model_validate(review)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review_by_staff(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Permanently delete a review. Requires staff or admin role.
    Use moderate endpoint with 'remove' action to flag as removed instead.
    """
    # Get the review
    review = await get_or_404(db, EventReview, review_id, "Review not found")

    await db.delete(review)
    await db.commit()

    logger.warning(f"Review {review_id} permanently deleted by user_id={current_user.id}")

    return {"message": "Review deleted successfully"}


@router.get("/reviews/stats", response_model=dict)
async def get_moderation_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get moderation statistics for staff dashboard.
    Requires staff or admin role.
    """
    # Count reviews by status
    stats_result = await db.execute(
        select(EventReview.moderation_status, func.count(EventReview.id)).group_by(
            EventReview.moderation_status
        )
    )
    stats = {}
    for mod_status, count in stats_result.all():
        stats[mod_status] = count

    # Count removed reviews
    removed_result = await db.execute(
        select(func.count(EventReview.id)).where(EventReview.is_removed == 1)
    )
    removed_count = removed_result.scalar() or 0

    return {
        "by_status": stats,
        "removed_count": removed_count,
        "total": sum(stats.values()),
        "pending": stats.get("PENDING", 0),
        "approved": stats.get("APPROVED", 0),
        "rejected": stats.get("REJECTED", 0),
    }


@router.post(
    "/{event_id}/registrations/{registration_id}/mark-no-show",
    status_code=status.HTTP_200_OK,
)
async def mark_registration_no_show(
    event_id: int,
    registration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Mark a registration as a no-show.

    Idempotent: re-calling on an already-no_show registration returns success
    without erroring, which lets the staff Registrant Roster bulk action be
    safely retried.

    Returns 404 if the registration does not exist, 422 if the registration
    exists but belongs to a different event than the one in the URL (which
    indicates a client wiring bug, not a missing resource). Requires staff
    or admin role.

    Placed BEFORE GET /{event_id} so the literal `/mark-no-show` suffix is
    matched before the catch-all event-detail handler (see PR #555 for the
    history of route-shadowing in this file).
    """
    result = await db.execute(
        select(EventRegistration).where(EventRegistration.id == registration_id)
    )
    registration = result.scalar_one_or_none()
    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")
    if registration.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Registration does not belong to this event",
        )

    if registration.status != EventRegistrationStatus.NO_SHOW.value:
        registration.status = EventRegistrationStatus.NO_SHOW.value
        await db.commit()
        await db.refresh(registration)
        logger.info(
            f"Registration {registration_id} marked no_show by user_id={current_user.id} "
            f"(event_id={event_id})"
        )

    return {"id": registration.id, "status": registration.status}


@router.post(
    "/{event_id}/registrations/{registration_id}/check-in",
    status_code=status.HTTP_201_CREATED,
)
async def check_in_registered_patron(
    event_id: int,
    registration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Record day-of attendance for a pre-registered patron.

    Replaces the synthetic walk-in row the staff Roster "Mark attended"
    action used to create. The resulting AttendanceCheckIn has
    check_in_method='pre_registered' and registration_id pointing back at
    the EventRegistration, so rollups and per-row attribution are correct.

    Lazily ensures an AttendanceSession exists for the event (one is
    created with sensible defaults if missing), so the frontend doesn't
    have to.

    Idempotent: re-calling for the same (event, registration) returns the
    existing pre_registered check-in row, no double-count.

    Returns 404 if the registration does not exist, 422 if the registration
    exists but belongs to a different event (client wiring bug). Requires
    staff or admin role.

    Placed BEFORE GET /{event_id} so the literal `/check-in` suffix is
    matched before the catch-all event-detail handler (see PR #555 for the
    history of route-shadowing in this file).
    """
    from ...models.attendance import AttendanceSession, AttendanceSessionStatus
    from ...services.attendance_service import AttendanceService

    result = await db.execute(
        select(EventRegistration).where(EventRegistration.id == registration_id)
    )
    registration = result.scalar_one_or_none()
    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")
    if registration.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Registration does not belong to this event",
        )

    event = await get_or_404(db, Event, event_id)
    session_q = await db.execute(
        select(AttendanceSession)
        .where(AttendanceSession.event_id == event_id)
        .where(AttendanceSession.status == AttendanceSessionStatus.OPEN)
        .order_by(AttendanceSession.id.desc())
    )
    session = session_q.scalars().first()
    if not session:
        session = await AttendanceService.create_session(
            db=db,
            session_name=event.title,
            session_date=event.start_time.date(),
            staff_id=current_user.id,
            event_id=event.id,
        )

    try:
        check_in = await AttendanceService.check_in_pre_registered(
            db=db,
            session_id=session.id,
            registration_id=registration_id,
            staff_id=current_user.id,
            guest_name=registration.patron_name,
            guest_email=registration.patron_email,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    await db.commit()
    await db.refresh(check_in)
    logger.info(
        f"Registration {registration_id} pre-registered check-in by "
        f"user_id={current_user.id} (event_id={event_id}, "
        f"session_id={session.id}, check_in_id={check_in.id})"
    )

    method_value = (
        check_in.check_in_method.value
        if hasattr(check_in.check_in_method, "value")
        else check_in.check_in_method
    )
    return {
        "id": check_in.id,
        "session_id": check_in.session_id,
        "registration_id": check_in.registration_id,
        "check_in_method": method_value,
        "checked_in_at": check_in.checked_in_at.isoformat() if check_in.checked_in_at else None,
    }


@router.post(
    "/bulk-from-recurrence",
    status_code=status.HTTP_201_CREATED,
)
async def bulk_create_recurring_events(
    payload: EventBulkCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Bulk-create a recurring series as a parent event + N real child rows.

    Each occurrence becomes its own ``events`` row with ``parent_event_id``
    set so it has independent registrations, capacity, accommodations, and
    can be edited or cancelled in isolation. The parent stores the RRULE;
    the children store ``recurrence_rule=NULL``.

    Caps:
      - Hard ceiling of 52 child rows per call.
      - Horizon ceiling of +366 days from "now" even if the rule's UNTIL is
        further out. Callers wanting more must split into multiple calls.

    ``dry_run=true`` returns the expansion preview (count + dates) without
    persisting.

    NOTE on route placement: this route is registered BEFORE
    ``GET /{event_id}`` so the literal ``/bulk-from-recurrence`` path is
    not shadowed by the ``/{event_id}`` int-parser.
    """
    # 1. Validate the RRULE parses cleanly. dateutil raises ValueError for
    #    malformed rules; surface as 422 instead of leaking a 500.
    try:
        rrulestr(payload.recurrence_rule, dtstart=payload.start_time)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid recurrence_rule: {exc}",
        ) from exc

    # 2. Build a TRANSIENT (non-persisted) Event purely to feed
    #    expand_event_instances. We do NOT add this to the session.
    transient_parent = Event(
        title=payload.title,
        start_time=payload.start_time,
        end_time=payload.end_time,
        recurrence_rule=payload.recurrence_rule,
        location=payload.location,
        description=payload.description,
        is_virtual=payload.is_virtual or False,
        virtual_link=payload.virtual_link,
        category=payload.category,
        audience=payload.audience,
    )

    horizon = datetime.now(timezone.utc) + timedelta(days=366)
    instances = expand_event_instances(transient_parent, window_end=horizon)

    # 3. Enforce the 52-child cap.
    if len(instances) > 52:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Recurrence expands to {len(instances)} occurrences within the "
                "366-day horizon; the bulk-create cap is 52. Use a shorter range "
                "or split into multiple calls."
            ),
        )

    if not instances:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Recurrence produced zero occurrences within the 366-day horizon.",
        )

    # 4. Dry-run short-circuit: preview only, no writes.
    if payload.dry_run:
        previews = [
            EventBulkInstancePreview(start_time=i["start_time"], end_time=i["end_time"])
            for i in instances
        ]
        return EventBulkCreateDryRunResponse(
            count=len(previews),
            first_start=previews[0].start_time if previews else None,
            last_start=previews[-1].start_time if previews else None,
            instances=previews,
        )

    # 5. Real create — atomic. AsyncSession.commit() rolls back the pending
    #    parent + children if any insert fails.
    inherited = payload.model_dump(
        exclude={"recurrence_rule", "dry_run", "start_time", "end_time", "parent_event_id"}
    )

    parent = Event(
        **inherited,
        start_time=payload.start_time,
        end_time=payload.end_time,
        recurrence_rule=payload.recurrence_rule,
    )
    db.add(parent)

    try:
        await db.flush()  # assigns parent.id without committing.

        children: list[Event] = []
        for inst in instances:
            child = Event(
                **inherited,
                start_time=inst["start_time"],
                end_time=inst["end_time"],
                recurrence_rule=None,
                parent_event_id=parent.id,
            )
            db.add(child)
            children.append(child)

        await db.flush()
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        logger.exception("Failed to bulk-create recurring events")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None

    # Refresh to surface the assigned PKs.
    await db.refresh(parent)
    for c in children:
        await db.refresh(c)

    return EventBulkCreateResponse(
        parent_id=parent.id,
        child_ids=[c.id for c in children],
        count=len(children),
    )


@router.get("/{event_id}", response_model=EventWithStats)
@limiter.limit("120/minute")
async def get_event(
    request: Request, event_id: int, db: AsyncSession = Depends(get_db)
) -> EventWithStats:
    result = await db.execute(
        select(Event).where(Event.id == event_id).where(Event.is_published == True)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Get registration count
    count_result = await db.execute(
        select(func.count(EventRegistration.id))
        .where(EventRegistration.event_id == event_id)
        .where(EventRegistration.status == EventRegistrationStatus.CONFIRMED.value)
    )
    reg_count = count_result.scalar() or 0

    spots_remaining = None
    if event.max_attendees:
        spots_remaining = max(0, event.max_attendees - reg_count)

    # Include average rating for past events (only approved, non-removed reviews)
    average_rating = None
    review_count = 0
    now = datetime.now(timezone.utc)
    if _ensure_aware_start(event.start_time) < now:
        rating_result = await db.execute(
            select(func.avg(EventReview.rating), func.count(EventReview.id))
            .where(EventReview.event_id == event_id)
            .where(EventReview.moderation_status == ReviewModerationStatus.APPROVED.value)
            .where(EventReview.is_removed == 0)
        )
        rating_row = rating_result.one()
        average_rating = round(float(rating_row[0]), 1) if rating_row[0] else None
        review_count = rating_row[1] or 0

    branch_names = await _branch_names_by_id(db, {event.branch_id})
    payload = EventResponse.model_validate(event).model_dump()
    payload["branch_name"] = branch_names.get(event.branch_id)

    return EventWithStats(
        **payload,
        registration_count=reg_count,
        spots_remaining=spots_remaining,
        average_rating=average_rating,
        review_count=review_count,
    )


@router.get("/{event_id}/related", response_model=RelatedEventsResponse)
@limiter.limit("60/minute")
async def get_related_events(
    request: Request,
    event_id: int,
    limit: int = Query(3, ge=1, le=10, description="Maximum number of related events"),
    db: AsyncSession = Depends(get_db),
) -> RelatedEventsResponse:
    """
    Get related events based on category and audience.
    Returns up to 'limit' events that share the same category or audience.
    """
    # Get the source event
    result = await db.execute(
        select(Event).where(Event.id == event_id).where(Event.is_published == True)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    now = datetime.now(timezone.utc)

    # Build query for related events
    # Match by category OR audience, exclude the current event, only upcoming
    conditions = []
    if event.category:
        conditions.append(Event.category == event.category)
    if event.audience:
        conditions.append(Event.audience == event.audience)

    if not conditions:
        # No category or audience to match on
        return RelatedEventsResponse(items=[], source_event_id=event_id)

    query = (
        select(Event)
        .where(Event.is_published == True)
        .where(Event.id != event_id)
        .where(Event.start_time >= now)
        .where(or_(*conditions))
        .order_by(Event.start_time)
        .limit(limit)
    )

    result = await db.execute(query)
    related_events = result.scalars().all()

    # Get registration counts
    event_ids = [e.id for e in related_events]
    reg_counts = {}
    if event_ids:
        count_result = await db.execute(
            select(EventRegistration.event_id, func.count(EventRegistration.id))
            .where(EventRegistration.event_id.in_(event_ids))
            .where(EventRegistration.status == EventRegistrationStatus.CONFIRMED.value)
            .group_by(EventRegistration.event_id)
        )
        reg_counts = dict(count_result.all())

    items: list[EventWithStats] = []
    for e in related_events:
        reg_count = reg_counts.get(e.id, 0)
        spots_remaining = None
        if e.max_attendees:
            spots_remaining = max(0, e.max_attendees - reg_count)

        event_with_stats = EventWithStats(
            **EventResponse.model_validate(e).model_dump(),
            registration_count=reg_count,
            spots_remaining=spots_remaining,
            average_rating=None,  # Related events don't include ratings
            review_count=0,
        )
        items.append(event_with_stats)

    return RelatedEventsResponse(items=items, source_event_id=event_id)


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_in: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new event. Requires staff or admin role."""
    event = Event(**event_in.model_dump())
    db.add(event)
    try:
        await db.commit()
        await db.refresh(event)
    except Exception:
        await db.rollback()
        logger.exception("Failed to create event")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None
    return event


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_in: EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update an event. Requires staff or admin role."""
    event = await get_or_404(db, Event, event_id, "Event not found")

    # Check if reducing max_attendees below current confirmed count
    if event_in.max_attendees is not None:
        count_result = await db.execute(
            select(func.count(EventRegistration.id))
            .where(EventRegistration.event_id == event_id)
            .where(EventRegistration.status == EventRegistrationStatus.CONFIRMED.value)
        )
        current_count = count_result.scalar() or 0
        if event_in.max_attendees < current_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reduce capacity below current registration count ({current_count})",
            )

    update_fields = event_in.model_dump(exclude_unset=True)

    # Validate partial time updates against existing event data
    proposed_start_time = update_fields.get("start_time", event.start_time)
    proposed_end_time = update_fields.get("end_time", event.end_time)
    if proposed_end_time is not None and proposed_end_time <= proposed_start_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_time must be after start_time",
        )

    for field, value in update_fields.items():
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    reason: str | None = Query(
        None,
        description="Optional cancellation reason included in the patron notification.",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Delete an event. Requires staff or admin role.

    Before deleting, every confirmed/waitlisted registration is marked
    CANCELLED (preserves a clear audit trail rather than relying solely on
    the FK CASCADE) and an EVENT_CANCELLED email is dispatched to each
    affected patron. Email failures never block deletion.
    """
    result = await db.execute(select(Event).where(Event.id == event_id).with_for_update())
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Snapshot affected registrations before deletion. We mark them CANCELLED
    # explicitly (instead of relying on ondelete=CASCADE) so the audit trail
    # shows an intentional cancellation rather than a silent row vanish.
    affected_result = await db.execute(
        select(EventRegistration)
        .where(EventRegistration.event_id == event_id)
        .where(
            EventRegistration.status.in_(
                [
                    EventRegistrationStatus.CONFIRMED.value,
                    EventRegistrationStatus.WAITLISTED.value,
                ]
            )
        )
    )
    affected_registrations = affected_result.scalars().all()

    cancellation_reason = reason or "The library has cancelled this event."
    event_title = event.title
    event_date_str = event.start_time.strftime("%B %d, %Y")
    event_time_str = event.start_time.strftime("%I:%M %p")
    event_location_str = event.location or "See event details"

    # Notify affected patrons before tearing down the event row. Each send is
    # individually guarded so a single failure cannot block the deletion.
    for reg in affected_registrations:
        await _send_event_email(
            NType.EVENT_CANCELLED,
            reg.patron_email,
            {
                "patron_name": reg.patron_name,
                "event_title": event_title,
                "event_date": event_date_str,
                "event_time": event_time_str,
                "event_location": event_location_str,
                "cancellation_reason": cancellation_reason,
            },
            db,
        )

    # Mark registrations CANCELLED for audit clarity, then drop the event.
    for reg in affected_registrations:
        reg.status = EventRegistrationStatus.CANCELLED.value

    await db.flush()
    await db.delete(event)
    await db.commit()


@router.post(
    "/{event_id}/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("10/minute")
async def register_for_event(  # noqa: role-check -- public event registration, Turnstile-gated
    request: Request,
    event_id: int,
    registration: RegistrationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    # Bot verification (Cloudflare Turnstile). Fails open in dev when the
    # secret isn't configured; production deployments must set CF_TURNSTILE_SECRET.
    remote_ip = request.client.host if request.client else None
    if not await verify_turnstile(registration.turnstile_token, remote_ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bot verification failed",
        )

    # Check event exists and is published (with row lock to prevent race conditions)
    result = await db.execute(
        select(Event)
        .where(Event.id == event_id)
        .where(Event.is_published == True)
        .with_for_update()
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Check if event has already started
    now = datetime.now(timezone.utc)
    if event.start_time <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot register for an event that has already started",
        )

    # Check if event requires registration
    if not event.registration_required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This event does not require registration",
        )

    # Normalize email for consistent comparison and storage. Email is
    # optional when a phone number is given (schema enforces at-least-one),
    # so phone-only registrations dedupe on phone instead.
    normalized_email = (
        normalize_email(registration.patron_email) if registration.patron_email else None
    )

    # Check for duplicate registration (confirmed or waitlisted)
    active_statuses = [
        EventRegistrationStatus.CONFIRMED.value,
        EventRegistrationStatus.WAITLISTED.value,
    ]
    if normalized_email:
        dup_filter = func.lower(EventRegistration.patron_email) == normalized_email
    else:
        dup_filter = EventRegistration.patron_phone == registration.patron_phone
    existing = await db.execute(
        select(EventRegistration)
        .where(EventRegistration.event_id == event_id)
        .where(dup_filter)
        .where(EventRegistration.status.in_(active_statuses))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already registered for this event",
        )

    # Check capacity (lock already held on event row)
    reg_status = EventRegistrationStatus.CONFIRMED.value
    if event.max_attendees:
        count_result = await db.execute(
            select(func.count(EventRegistration.id))
            .where(EventRegistration.event_id == event_id)
            .where(EventRegistration.status == EventRegistrationStatus.CONFIRMED.value)
        )
        current_count = count_result.scalar() or 0
        if current_count >= event.max_attendees:
            # New waitlist entries use the claim-token flow. Legacy waitlisted
            # registrations still drain through cancel_registration.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "event_full",
                    "waitlist_url": f"/api/v1/events/{event_id}/waitlist",
                },
            )

    # Photo-release: only persist patron's answer when the event actually
    # asked the question. If event.photos_will_be_taken is False, store NULL
    # regardless of what the client sent so the three-valued semantics hold.
    photo_release = registration.photo_release_granted if event.photos_will_be_taken else None

    new_registration = EventRegistration(
        event_id=event_id,
        patron_name=registration.patron_name,
        patron_email=normalized_email,
        patron_phone=registration.patron_phone,
        user_id=current_user.id if current_user else None,
        status=reg_status,
        reminder_requested=registration.reminder_requested,
        accommodation_requested=registration.accommodation_requested,
        accommodation_details=registration.accommodation_details,
        photo_release_granted=photo_release,
    )
    db.add(new_registration)
    try:
        await db.commit()
    except IntegrityError:
        # Partial unique index (event_id, lower(patron_email)) WHERE status IN
        # ('confirmed','waitlisted') blocks duplicate active registrations.
        # The pre-check above usually catches duplicates, but a concurrent
        # request from a second browser tab can pass both unlocked SELECTs
        # before either commits. Translate to a clean 409.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already registered for this event",
        ) from None
    await db.refresh(new_registration)

    # Calculate waitlist position if waitlisted
    waitlist_position = None
    if reg_status == EventRegistrationStatus.WAITLISTED.value:
        # Get all waitlisted registrations ordered by registration time
        waitlist_result = await db.execute(
            select(EventRegistration.id)
            .where(EventRegistration.event_id == event_id)
            .where(EventRegistration.status == EventRegistrationStatus.WAITLISTED.value)
            .order_by(EventRegistration.registered_at)
        )
        waitlist_ids = [row[0] for row in waitlist_result.all()]
        try:
            waitlist_position = waitlist_ids.index(new_registration.id) + 1
        except ValueError:
            waitlist_position = len(waitlist_ids)

    # Send event registration confirmation email
    if reg_status != EventRegistrationStatus.WAITLISTED.value:
        await _send_event_email(
            NType.EVENT_REGISTRATION_CONFIRMATION,
            normalized_email,
            {
                "patron_name": registration.patron_name,
                "event_title": event.title,
                "event_date": event.start_time.strftime("%B %d, %Y"),
                "event_time": event.start_time.strftime("%I:%M %p"),
                "event_location": event.location or "See event details",
            },
            db,
        )

    # Build response with waitlist_position
    response_dict = RegistrationResponse.model_validate(new_registration).model_dump()
    response_dict["waitlist_position"] = waitlist_position

    return response_dict


@router.get("/{event_id}/registrations", response_model=RegistrationListResponse)
async def get_event_registrations(
    event_id: int,
    include_waitlist: bool = Query(False, description="Include waitlisted registrations"),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get all registrations for an event. Requires staff or admin role."""
    # Check event exists
    event = await get_or_404(db, Event, event_id, "Event not found")

    # Build status filter
    statuses = [EventRegistrationStatus.CONFIRMED.value]
    if include_waitlist:
        statuses.append(EventRegistrationStatus.WAITLISTED.value)

    # Count confirmed registrations (always needed for spots_remaining)
    confirmed_count_result = await db.execute(
        select(func.count(EventRegistration.id))
        .where(EventRegistration.event_id == event_id)
        .where(EventRegistration.status == EventRegistrationStatus.CONFIRMED.value)
    )
    confirmed_count = confirmed_count_result.scalar() or 0

    # Count waitlisted registrations
    waitlist_count = 0
    if include_waitlist:
        waitlist_count_result = await db.execute(
            select(func.count(EventRegistration.id))
            .where(EventRegistration.event_id == event_id)
            .where(EventRegistration.status == EventRegistrationStatus.WAITLISTED.value)
        )
        waitlist_count = waitlist_count_result.scalar() or 0

    # Paginated data query
    reg_result = await db.execute(
        select(EventRegistration)
        .where(EventRegistration.event_id == event_id)
        .where(EventRegistration.status.in_(statuses))
        .order_by(EventRegistration.registered_at)
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    registrations = reg_result.scalars().all()

    spots_remaining = None
    if event.max_attendees:
        spots_remaining = max(0, event.max_attendees - confirmed_count)

    return {
        "registrations": [RegistrationResponse.model_validate(r) for r in registrations],
        "total": confirmed_count,
        "waitlist_count": waitlist_count,
        "spots_remaining": spots_remaining,
    }


@router.delete("/{event_id}/register/{registration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_registration(
    event_id: int,
    registration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Lock the event row to prevent race conditions during waitlist promotion
    event_result = await db.execute(select(Event).where(Event.id == event_id).with_for_update())
    event = event_result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    result = await db.execute(
        select(EventRegistration)
        .where(EventRegistration.id == registration_id)
        .where(EventRegistration.event_id == event_id)
    )
    registration = result.scalar_one_or_none()
    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    # Authorization: only the patron who registered, OR staff/admin, may cancel.
    # The previous version compared a `patron_email` query string param to the
    # registration's email, allowing any authenticated user to cancel anyone's
    # registration by guessing the email. We now use the authenticated user's
    # own email, with a staff bypass mirroring the same role checks used by
    # require_staff (STAFF / ADMIN / SUPER_ADMIN / DIRECTOR).
    from ...models.user import UserRole

    staff_roles = {UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR}
    is_staff = current_user.role in staff_roles
    if not is_staff and (
        not current_user.email
        or current_user.email.lower() != (registration.patron_email or "").lower()
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only cancel your own registration",
        )

    # Check if already cancelled
    if registration.status == EventRegistrationStatus.CANCELLED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Registration already cancelled"
        )

    was_confirmed = registration.status == EventRegistrationStatus.CONFIRMED.value
    registration.status = EventRegistrationStatus.CANCELLED.value

    # Promote first waitlisted person if a confirmed spot was freed
    promoted_registration = None
    if was_confirmed and event.max_attendees:
        waitlist_result = await db.execute(
            select(EventRegistration)
            .where(EventRegistration.event_id == event_id)
            .where(EventRegistration.status == EventRegistrationStatus.WAITLISTED.value)
            .order_by(EventRegistration.registered_at)
            .limit(1)
        )
        next_in_line = waitlist_result.scalar_one_or_none()
        if next_in_line:
            next_in_line.status = EventRegistrationStatus.CONFIRMED.value
            promoted_registration = next_in_line

    # Send waitlist promotion email before commit, mirroring the
    # confirmation-email try/except pattern at the top of this module.
    if promoted_registration:
        await _send_event_email(
            NType.EVENT_WAITLIST_PROMOTED,
            promoted_registration.patron_email,
            {
                "patron_name": promoted_registration.patron_name,
                "event_title": event.title,
                "event_date": event.start_time.strftime("%B %d, %Y"),
                "event_time": event.start_time.strftime("%I:%M %p"),
                "event_location": event.location or "See event details",
            },
            db,
        )

    # Notify the new waitlist only after legacy waitlisted registrations drain.
    # The patron claims the available seat with a 15-minute magic link.
    new_waitlist_notified = None
    if was_confirmed and event.max_attendees and not promoted_registration:
        new_waitlist_result = await db.execute(
            select(EventWaitlistEntry)
            .where(EventWaitlistEntry.event_id == event_id)
            .where(EventWaitlistEntry.status == WaitlistStatus.WAITING.value)
            .order_by(EventWaitlistEntry.created_at)
            .limit(1)
            .with_for_update()
        )
        next_waitlister = new_waitlist_result.scalar_one_or_none()
        if next_waitlister:
            import secrets as _secrets

            next_waitlister.status = WaitlistStatus.NOTIFIED.value
            next_waitlister.notified_at = datetime.now(timezone.utc)
            next_waitlister.claim_token = _secrets.token_urlsafe(32)
            next_waitlister.claim_token_expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=15
            )
            new_waitlist_notified = next_waitlister

    if new_waitlist_notified:
        settings = get_settings()
        site_url = settings.frontend_url.rstrip("/")
        claim_url = (
            f"{site_url}/events/detail/{event_id}?claim_token={new_waitlist_notified.claim_token}"
        )
        await _send_event_email(
            NType.EVENT_WAITLIST_SPOT_AVAILABLE,
            new_waitlist_notified.email,
            {
                "patron_name": new_waitlist_notified.name or "",
                "event_title": event.title,
                "event_date": event.start_time.strftime("%B %d, %Y"),
                "event_time": event.start_time.strftime("%I:%M %p"),
                "event_location": event.location or "See event details",
                "claim_url": claim_url,
                "claim_minutes": 15,
            },
            db,
        )

    cancelled_email = registration.patron_email
    cancelled_name = registration.patron_name
    promoted_email = promoted_registration.patron_email if promoted_registration else None
    promoted_name = promoted_registration.patron_name if promoted_registration else None

    await db.commit()

    # Transactional emails (CAN-SPAM safe — no marketing CTAs).
    await _send_event_cancellation_email(event, cancelled_email, cancelled_name, db)
    if promoted_registration and promoted_email:
        await _send_event_waitlist_promoted_email(event, promoted_email, promoted_name, db)

    response = {"message": "Registration cancelled successfully"}
    if promoted_registration:
        response["promoted_email"] = promoted_registration.patron_email

    return response


async def _send_event_cancellation_email(event, recipient_email, patron_name, db):
    await _send_event_email(
        NType.EVENT_REGISTRATION_CANCELLED,
        recipient_email,
        {
            "patron_name": patron_name or "",
            "event_title": event.title,
            "event_date": event.start_time.strftime("%B %d, %Y"),
            "event_time": event.start_time.strftime("%I:%M %p"),
            "event_location": event.location or "See event details",
        },
        db,
    )


async def _send_event_waitlist_promoted_email(event, recipient_email, patron_name, db):
    await _send_event_email(
        NType.EVENT_WAITLIST_PROMOTED,
        recipient_email,
        {
            "patron_name": patron_name or "",
            "event_title": event.title,
            "event_date": event.start_time.strftime("%B %d, %Y"),
            "event_time": event.start_time.strftime("%I:%M %p"),
            "event_location": event.location or "See event details",
        },
        db,
    )


@router.delete(
    "/{event_id}/registrations/{registration_id}/admin", status_code=status.HTTP_204_NO_CONTENT
)
async def staff_cancel_registration(
    event_id: int,
    registration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Cancel a registration on behalf of a patron. Requires staff or admin role."""
    # Lock the event row to prevent race conditions during waitlist promotion
    event_result = await db.execute(select(Event).where(Event.id == event_id).with_for_update())
    event = event_result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    result = await db.execute(
        select(EventRegistration)
        .where(EventRegistration.id == registration_id)
        .where(EventRegistration.event_id == event_id)
    )
    registration = result.scalar_one_or_none()
    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    # Check if already cancelled
    if registration.status == EventRegistrationStatus.CANCELLED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Registration already cancelled"
        )

    was_confirmed = registration.status == EventRegistrationStatus.CONFIRMED.value
    registration.status = EventRegistrationStatus.CANCELLED.value

    # Promote first waitlisted person if a confirmed spot was freed
    promoted_registration = None
    if was_confirmed and event.max_attendees:
        waitlist_result = await db.execute(
            select(EventRegistration)
            .where(EventRegistration.event_id == event_id)
            .where(EventRegistration.status == EventRegistrationStatus.WAITLISTED.value)
            .order_by(EventRegistration.registered_at)
            .limit(1)
        )
        next_in_line = waitlist_result.scalar_one_or_none()
        if next_in_line:
            next_in_line.status = EventRegistrationStatus.CONFIRMED.value
            promoted_registration = next_in_line

    # Send waitlist promotion email before commit, mirroring the
    # confirmation-email try/except pattern at the top of this module.
    if promoted_registration:
        await _send_event_email(
            NType.EVENT_WAITLIST_PROMOTED,
            promoted_registration.patron_email,
            {
                "patron_name": promoted_registration.patron_name,
                "event_title": event.title,
                "event_date": event.start_time.strftime("%B %d, %Y"),
                "event_time": event.start_time.strftime("%I:%M %p"),
                "event_location": event.location or "See event details",
            },
            db,
        )

    cancelled_email = registration.patron_email
    cancelled_name = registration.patron_name
    promoted_email = promoted_registration.patron_email if promoted_registration else None
    promoted_name = promoted_registration.patron_name if promoted_registration else None

    await db.commit()

    # Transactional emails (CAN-SPAM safe — no marketing CTAs).
    await _send_event_cancellation_email(event, cancelled_email, cancelled_name, db)
    if promoted_registration and promoted_email:
        await _send_event_waitlist_promoted_email(event, promoted_email, promoted_name, db)

    response = {
        "message": "Registration cancelled successfully",
        "cancelled_email": cancelled_email,
    }
    if promoted_registration:
        response["promoted_email"] = promoted_registration.patron_email

    return response


@router.post(
    "/{event_id}/registrations/{registration_id}/acknowledge-accommodation",
    status_code=status.HTTP_200_OK,
)
async def acknowledge_accommodation(
    event_id: int,
    registration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Mark an accommodation request as acknowledged by staff.

    Records who acknowledged it and when, so patrons can be reassured the
    request has been read & arranged. Requires staff or admin role.
    """
    result = await db.execute(
        select(EventRegistration)
        .where(EventRegistration.id == registration_id)
        .where(EventRegistration.event_id == event_id)
    )
    registration = result.scalar_one_or_none()
    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    registration.accommodation_acknowledged_at = datetime.now(timezone.utc)
    registration.accommodation_acknowledged_by = current_user.id
    await db.commit()

    return {"ok": True}


# ============================================================================
# Event Review Endpoints
# ============================================================================


@router.post(
    "/{event_id}/reviews", response_model=EventReviewResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("10/minute")
async def submit_event_review(
    request: Request,
    event_id: int,
    review: EventReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a review for a past event.
    Only allows reviews from people who registered (confirmed) for the event.

    Reviews are automatically analyzed for:
    - Spam/advertising
    - Hate speech
    - Excessive caps/punctuation
    - Suspicious patterns
    - Off-topic content
    - Duplicates

    Flagged reviews (score > 70) are queued for staff review.
    """
    # Check event exists
    event = await get_or_404(db, Event, event_id, "Event not found")

    # Check event has ended
    now = datetime.now(timezone.utc)
    if event.start_time > now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot review an event that hasn't happened yet",
        )

    # Normalize email
    normalized_email = normalize_email(review.patron_email)

    # Check user attended the event (had a confirmed registration)
    reg_result = await db.execute(
        select(EventRegistration)
        .where(EventRegistration.event_id == event_id)
        .where(func.lower(EventRegistration.patron_email) == normalized_email)
        .where(EventRegistration.status == EventRegistrationStatus.CONFIRMED.value)
    )
    registration = reg_result.scalar_one_or_none()
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must have attended this event to leave a review",
        )

    # Check for existing review
    existing_review = await db.execute(
        select(EventReview)
        .where(EventReview.event_id == event_id)
        .where(func.lower(EventReview.patron_email) == normalized_email)
    )
    if existing_review.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You have already reviewed this event"
        )

    # Create review (auto-approved; staff can hide via PATCH /events/reviews/{id}/hide)
    new_review = EventReview(
        event_id=event_id,
        patron_email=normalized_email,
        rating=review.rating,
        comment=review.comment,
        moderation_status=ReviewModerationStatus.APPROVED.value,
    )
    db.add(new_review)
    await db.commit()
    await db.refresh(new_review)

    # Run content flagging analysis if comment exists
    if review.comment:
        try:
            from ...services.content_flagging_service import ContentFlaggingService

            analysis_result = await ContentFlaggingService.analyze_review(
                db=db,
                text=review.comment,
                user_email=normalized_email,
                review_id=new_review.id,
                review_type="event_review",
            )

            # Save flags to database
            if analysis_result.should_flag:
                await ContentFlaggingService.save_flags(
                    db=db,
                    review_id=new_review.id,
                    review_type="event_review",
                    analysis_result=analysis_result,
                )

                logger.info(
                    f"Event review flagged for moderation: event={event_id}, "
                    f"score={analysis_result.overall_score}, review_id={new_review.id}"
                )
        except Exception as e:  # noqa: BLE001  # best-effort moderation — must not fail review submission
            # Log error but don't fail the review submission
            logger.error(f"Error running content flagging for review {new_review.id}: {e}")

    logger.info(f"Event review submitted: event={event_id}, rating={review.rating}")

    return new_review


@router.get("/{event_id}/reviews", response_model=PaginatedResponse[EventReviewResponse])
@limiter.limit("60/minute")
async def get_event_reviews(
    request: Request,
    event_id: int,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Get all approved reviews for an event. Only shows approved reviews to patrons."""
    # Check event exists
    await get_or_404(db, Event, event_id, "Event not found")

    # Base filters for approved, non-removed reviews
    base_filters = [
        EventReview.event_id == event_id,
        EventReview.moderation_status == ReviewModerationStatus.APPROVED.value,
        EventReview.is_removed == 0,
    ]

    # Count query
    count_result = await db.execute(select(func.count(EventReview.id)).where(*base_filters))
    total = count_result.scalar() or 0

    # Data query
    reviews_result = await db.execute(
        select(EventReview)
        .where(*base_filters)
        .order_by(EventReview.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    reviews = reviews_result.scalars().all()

    total_pages = calculate_total_pages(total, pagination.page_size)
    # Redact patron_email from public review responses (PII protection)
    redacted_reviews = []
    for r in reviews:
        review_data = EventReviewResponse.model_validate(r)
        review_data.patron_email = None
        redacted_reviews.append(review_data)
    return PaginatedResponse(
        data=redacted_reviews,
        pagination=PaginationInfo(
            page=pagination.page,
            per_page=pagination.page_size,
            total=total,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1,
        ),
    )


@router.get("/{event_id}/reviews/summary", response_model=EventReviewSummary)
@limiter.limit("60/minute")
async def get_event_review_summary(
    request: Request,
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get review summary (average rating, distribution) for an event. Only counts approved reviews."""
    # Check event exists
    await get_or_404(db, Event, event_id, "Event not found")

    # Get average rating and total count (only approved, non-removed reviews)
    stats_result = await db.execute(
        select(func.avg(EventReview.rating), func.count(EventReview.id))
        .where(EventReview.event_id == event_id)
        .where(EventReview.moderation_status == ReviewModerationStatus.APPROVED.value)
        .where(EventReview.is_removed == 0)
    )
    stats_row = stats_result.one()
    average_rating = round(float(stats_row[0]), 1) if stats_row[0] else None
    total_reviews = stats_row[1] or 0

    # Get rating distribution (only approved, non-removed reviews)
    distribution_result = await db.execute(
        select(EventReview.rating, func.count(EventReview.id))
        .where(EventReview.event_id == event_id)
        .where(EventReview.moderation_status == ReviewModerationStatus.APPROVED.value)
        .where(EventReview.is_removed == 0)
        .group_by(EventReview.rating)
    )
    rating_distribution = {i: 0 for i in range(1, 6)}
    for row in distribution_result.all():
        rating_distribution[row[0]] = row[1]

    return EventReviewSummary(
        event_id=event_id,
        average_rating=average_rating,
        total_reviews=total_reviews,
        rating_distribution=rating_distribution,
    )


router.include_router(event_waitlist_router)


@router.get("/{event_id}/calendar.ics")
async def event_ical(
    event_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Single-event .ics download (RFC 5545)."""
    result = await db.execute(
        select(Event).where(Event.id == event_id).where(Event.is_published == True)  # noqa: E712
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    settings = get_settings()
    site_url = settings.frontend_url.rstrip("/")
    parsed = urlparse(site_url)
    host = parsed.hostname or "l30.org"
    now = datetime.now(timezone.utc)

    start = event.start_time
    end = event.end_time or (
        (start if start.tzinfo else start.replace(tzinfo=timezone.utc)) + timedelta(hours=1)
    )
    last_modified = getattr(event, "updated_at", None) or getattr(event, "created_at", None) or now
    url = f"{site_url}/events/detail/{event.id}"

    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//L30 Community Library//Events//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:event-{event.id}@{host}",
        f"DTSTAMP:{_format_utc(now)}",
        f"DTSTART:{_format_utc(start)}",
        f"DTEND:{_format_utc(end)}",
        f"SUMMARY:{_ical_escape(event.title)}",
        "STATUS:CONFIRMED",
        f"URL:{url}",
        f"LAST-MODIFIED:{_format_utc(last_modified)}",
    ]
    if event.description:
        lines.append(f"DESCRIPTION:{_ical_escape(event.description)}")
    loc = event.location or (event.virtual_link if event.is_virtual else None)
    if loc:
        lines.append(f"LOCATION:{_ical_escape(loc)}")
    lines.append(
        f"ORGANIZER;CN={_ical_escape(branding.library_name)}:mailto:{branding.contact_email}"
    )
    lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")

    folded = "\r\n".join(_ical_fold(line) for line in lines) + "\r\n"
    return Response(
        content=folded,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="event-{event.id}.ics"',
            "Cache-Control": "public, max-age=300, stale-while-revalidate=600",
        },
    )


@router.get("/series/{series_id}/calendar.ics")
async def series_ical(
    series_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Multi-event .ics: all upcoming events that belong to one series_id."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Event)
        .where(Event.series_id == series_id)
        .where(Event.is_published == True)  # noqa: E712
        .where(Event.start_time >= now - timedelta(days=1))
        .order_by(Event.start_time.asc())
    )
    events = result.scalars().all()
    if not events:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")

    settings = get_settings()
    site_url = settings.frontend_url.rstrip("/")
    parsed = urlparse(site_url)
    host = parsed.hostname or "l30.org"

    dtstamp = _format_utc(now)
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//L30 Community Library//Events//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_ical_escape(f'L30 Library Series {series_id}')}",
    ]
    for ev in events:
        start = ev.start_time
        end = ev.end_time or (
            (start if start.tzinfo else start.replace(tzinfo=timezone.utc)) + timedelta(hours=1)
        )
        url = f"{site_url}/events/detail/{ev.id}"
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:event-{ev.id}@{host}")
        lines.append(f"DTSTAMP:{dtstamp}")
        lines.append(f"DTSTART:{_format_utc(start)}")
        lines.append(f"DTEND:{_format_utc(end)}")
        lines.append(f"SUMMARY:{_ical_escape(ev.title)}")
        lines.append("STATUS:CONFIRMED")
        lines.append(f"URL:{url}")
        if ev.description:
            lines.append(f"DESCRIPTION:{_ical_escape(ev.description)}")
        loc = ev.location or (ev.virtual_link if ev.is_virtual else None)
        if loc:
            lines.append(f"LOCATION:{_ical_escape(loc)}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")

    folded = "\r\n".join(_ical_fold(line) for line in lines) + "\r\n"
    return Response(
        content=folded,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="series-{series_id}.ics"',
            "Cache-Control": "public, max-age=300, stale-while-revalidate=600",
        },
    )
