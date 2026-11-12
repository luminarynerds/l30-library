# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Library Card Application API Endpoints

Provides endpoints for:
- Public card application submission
- Patron application status checking
- Staff review of applications
- Application approval/denial workflow
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ...core.coppa import COPPA_AGE_THRESHOLD, calculate_age, is_under_coppa_age
from ...core.database import get_db
from ...core.branding import branding
from ...core.config import get_settings
from ...core.email import (
    send_card_application_approved,
    send_card_application_denied,
    send_card_application_received,
)
from ...core.logging import get_logger
from ...core.rate_limit import limiter
from ...core.turnstile import verify_turnstile
from ...models.card_application import CardApplicationStatus, LibraryCardApplication
from ...models.user import User, email_blind_hash
from ...schemas.card_application import (
    CardApplicationCoppaResponse,
    CardApplicationCreate,
    CardApplicationListResponse,
    CardApplicationPublicStatusResponse,
    CardApplicationResponse,
    CardApplicationReview,
    CardApplicationStats,
)
from .auth import get_optional_user
from .dependencies import require_authenticated, require_staff

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/card-applications", tags=["card-applications"])

# How recently an approved or denied application blocks a resubmit.
# Approved-within-this-window means "you already have a card, talk to staff"
# Denied-within-this-window means "wait or contact staff if things changed"
APPROVED_RESUBMIT_BLOCK_DAYS = 90
DENIED_RESUBMIT_BLOCK_DAYS = 30


def generate_card_number() -> str:
    # Format: {CARD_PREFIX}-XXXXXX (6 alphanumeric characters)
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(secrets.choice(chars) for _ in range(6))
    return f"{branding.CARD_PREFIX}-{random_part}"


def _build_application_response(
    application: LibraryCardApplication,
    reviewer: Optional[User] = None
) -> CardApplicationResponse:
    reviewer_name = None
    if reviewer:
        reviewer_name = reviewer.full_name
    elif application.reviewer:
        reviewer_name = application.reviewer.full_name

    return CardApplicationResponse(
        id=application.id,
        user_id=application.user_id,
        first_name=application.first_name,
        last_name=application.last_name,
        full_name=application.full_name,
        email=application.email,
        phone=application.phone,
        date_of_birth=application.date_of_birth,
        address_line1=application.address_line1,
        address_line2=application.address_line2,
        city=application.city,
        state=application.state,
        zip_code=application.zip_code,
        id_type=application.id_type,
        id_number_last4=application.id_number_last4,
        status=application.status,
        submitted_at=application.submitted_at,
        reviewed_by_id=application.reviewed_by_id,
        reviewed_by_name=reviewer_name,
        reviewed_at=application.reviewed_at,
        review_notes=application.review_notes,
        denial_reason=application.denial_reason,
        assigned_card_number=application.assigned_card_number,
    )


# ============================================================================
# Public Application Endpoints
# ============================================================================

@router.post(
    "",
    response_model=CardApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": CardApplicationCoppaResponse, "description": "COPPA: parental consent required"},
    },
)
@limiter.limit("5/minute")
async def submit_application(  # noqa: role-check -- public library card application
    request: Request,
    data: CardApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Submit a library card application.

    This endpoint is public - anyone can apply for a card.
    If the user is authenticated, the application is linked to their account.

    **COPPA compliance:** If the applicant's date of birth indicates they
    are under 13, the application is rejected immediately and no PII is
    stored.  The response directs the family to apply in person at a
    library branch with a parent or guardian present.
    """
    # ------------------------------------------------------------------
    # Cloudflare Turnstile bot verification -- gate BEFORE any DB work.
    # Fails open in dev when CF_TURNSTILE_SECRET is unset (see
    # core.turnstile); rejects bogus tokens once the secret is set.
    # ------------------------------------------------------------------
    if not await verify_turnstile(
        data.turnstile_token,
        request.client.host if request.client else None,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Captcha verification failed. Please retry.",
        )

    # ------------------------------------------------------------------
    # COPPA age gate -- must run BEFORE any PII is persisted
    # ------------------------------------------------------------------
    if data.date_of_birth is not None and is_under_coppa_age(data.date_of_birth):
        applicant_age = calculate_age(data.date_of_birth)
        coppa_message = (
            "Applicants under 13 cannot register for a library card "
            "online. Please visit your local library branch with a "
            "parent or guardian to complete the application in person."
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=CardApplicationCoppaResponse(
                consent_required=True,
                # ``detail`` mirrors ``message`` so the frontend's standard
                # ``error.detail`` fallback (card-applications-api.ts) renders
                # the helpful guidance instead of "Failed to submit application".
                detail=coppa_message,
                message=coppa_message,
                applicant_age=applicant_age,
                minimum_online_age=COPPA_AGE_THRESHOLD,
            ).model_dump(),
        )

    # Check for any existing application on this email and apply the
    # right block based on its status + recency. UTC for all date math.
    now = datetime.now(timezone.utc)
    approved_cutoff = now - timedelta(days=APPROVED_RESUBMIT_BLOCK_DAYS)
    denied_cutoff = now - timedelta(days=DENIED_RESUBMIT_BLOCK_DAYS)

    existing_result = await db.execute(
        select(LibraryCardApplication)
        .where(LibraryCardApplication.email == data.email)
        .order_by(LibraryCardApplication.submitted_at.desc())
    )
    for existing in existing_result.scalars():
        if existing.status in (
            CardApplicationStatus.pending,
            CardApplicationStatus.under_review,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an application in review.",
            )
        if existing.status == CardApplicationStatus.approved:
            approved_at = existing.reviewed_at or existing.submitted_at
            if approved_at and approved_at >= approved_cutoff:
                approved_date = approved_at.strftime("%Y-%m-%d")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"An application for this email was approved on "
                        f"{approved_date}. Contact staff to recover your card."
                    ),
                )
            # Older approval -- clean slate, fall through to next existing or create.
            continue
        if existing.status == CardApplicationStatus.denied:
            denied_at = existing.reviewed_at or existing.submitted_at
            if denied_at and denied_at >= denied_cutoff:
                denied_date = denied_at.strftime("%Y-%m-%d")
                reason = existing.denial_reason or "no reason provided"
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Your previous application was denied on "
                        f"{denied_date}: {reason}. Contact staff if "
                        f"circumstances have changed."
                    ),
                )
            # Older denial -- clean slate, fall through.
            continue

    # Create the application. check_token is the random handle the patron
    # uses to view application status via the emailed link (Issue #1028).
    # 32 url-safe bytes (~256 bits) makes brute-force discovery infeasible,
    # so no rate-limit on the token endpoint.
    application = LibraryCardApplication(
        user_id=current_user.id if current_user else None,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        date_of_birth=data.date_of_birth,
        address_line1=data.address_line1,
        address_line2=data.address_line2,
        city=data.city,
        state=data.state,
        zip_code=data.zip_code,
        id_type=data.id_type,
        id_number_last4=data.id_number_last4,
        status=CardApplicationStatus.pending,
        check_token=secrets.token_urlsafe(32),
    )

    db.add(application)
    await db.commit()
    await db.refresh(application)

    # Send confirmation email -- failures are non-fatal; the application
    # is already saved.
    try:
        await send_card_application_received(
            to_email=application.email,
            first_name=application.first_name,
            check_token=application.check_token,
        )
    except Exception as exc:  # noqa: BLE001  # best-effort email — application already saved
        logger.warning(
            "Failed to send card application received email",
            extra={"application_id": application.id, "error": str(exc)},
        )

    return _build_application_response(application)


@router.get(
    "/check-by-token/{token}",
    response_model=CardApplicationPublicStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def check_application_by_token(  # noqa: role-check -- public token-gated status
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Public, token-gated status lookup for a card application.

    Patrons reach this via a link in their submission-confirmation email.
    Response is intentionally narrow: status + key timestamps only, NO PII.
    Returns 404 (not 403) on bad/unknown token to avoid leaking that any
    given token-shaped string exists in our DB (email-existence oracle).
    """
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    result = await db.execute(
        select(LibraryCardApplication).where(
            LibraryCardApplication.check_token == token
        )
    )
    application = result.scalar_one_or_none()

    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return CardApplicationPublicStatusResponse(
        status=application.status,
        submitted_at=application.submitted_at,
        reviewed_at=application.reviewed_at,
    )


@router.get("/check/{email}", response_model=CardApplicationResponse)
async def check_application_status(
    email: str,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """
    Check application status by email (staff only).

    Returns full application details for staff review.
    """
    result = await db.execute(
        select(LibraryCardApplication)
        .options(joinedload(LibraryCardApplication.reviewer))
        .where(LibraryCardApplication.email == email)
        .order_by(LibraryCardApplication.submitted_at.desc())
    )
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No application found with this email"
        )

    return _build_application_response(application)


# ============================================================================
# Authenticated User Endpoints
# ============================================================================

@router.get("/my", response_model=list[CardApplicationResponse])
async def get_my_applications(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get all applications submitted by the current user."""
    result = await db.execute(
        select(LibraryCardApplication)
        .options(joinedload(LibraryCardApplication.reviewer))
        .where(
            or_(
                LibraryCardApplication.user_id == current_user.id,
                LibraryCardApplication.email == current_user.email
            )
        )
        .order_by(LibraryCardApplication.submitted_at.desc())
    )
    applications = result.unique().scalars().all()

    return [_build_application_response(app) for app in applications]


# ============================================================================
# Staff Endpoints
# ============================================================================

@router.get("/staff", response_model=CardApplicationListResponse)
async def list_applications(
    status_filter: Optional[CardApplicationStatus] = Query(None, alias="status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    sort: Optional[Literal["oldest_first", "newest_first"]] = Query(
        None,
        description=(
            "Sort order. Defaults to oldest_first for pending/under_review "
            "(fair triage) and newest_first for approved/denied."
        ),
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all card applications (staff-facing)."""
    query = (
        select(LibraryCardApplication)
        .options(joinedload(LibraryCardApplication.reviewer))
    )
    count_query = select(func.count(LibraryCardApplication.id))

    if status_filter:
        query = query.where(LibraryCardApplication.status == status_filter)
        count_query = count_query.where(LibraryCardApplication.status == status_filter)

    if search:
        safe_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search_filter = or_(
            LibraryCardApplication.first_name.ilike(f"%{safe_search}%"),
            LibraryCardApplication.last_name.ilike(f"%{safe_search}%"),
            LibraryCardApplication.email.ilike(f"%{safe_search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Default sort: oldest-first for actionable queue (fair triage), newest-first
    # for review history. Caller can override via `sort` param.
    if sort is None:
        if status_filter in (
            CardApplicationStatus.pending,
            CardApplicationStatus.under_review,
        ):
            effective_sort = "oldest_first"
        else:
            effective_sort = "newest_first"
    else:
        effective_sort = sort

    if effective_sort == "oldest_first":
        order_clause = LibraryCardApplication.submitted_at.asc()
    else:
        order_clause = LibraryCardApplication.submitted_at.desc()

    query = query.order_by(order_clause).limit(limit).offset(offset)
    result = await db.execute(query)
    applications = result.unique().scalars().all()

    return CardApplicationListResponse(
        applications=[_build_application_response(app) for app in applications],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/staff/stats", response_model=CardApplicationStats)
async def get_application_stats(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get statistics about card applications."""
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Count by status
    status_counts = {}
    for app_status in CardApplicationStatus:
        count_result = await db.execute(
            select(func.count(LibraryCardApplication.id))
            .where(LibraryCardApplication.status == app_status)
        )
        status_counts[app_status] = count_result.scalar() or 0

    # Count this week and month
    week_result = await db.execute(
        select(func.count(LibraryCardApplication.id))
        .where(LibraryCardApplication.submitted_at >= week_ago)
    )
    total_this_week = week_result.scalar() or 0

    month_result = await db.execute(
        select(func.count(LibraryCardApplication.id))
        .where(LibraryCardApplication.submitted_at >= month_ago)
    )
    total_this_month = month_result.scalar() or 0

    # Calculate average review time for approved/denied applications
    avg_result = await db.execute(
        select(
            func.avg(
                func.extract('epoch', LibraryCardApplication.reviewed_at) -
                func.extract('epoch', LibraryCardApplication.submitted_at)
            )
        ).where(
            LibraryCardApplication.reviewed_at.isnot(None)
        )
    )
    avg_seconds = avg_result.scalar()
    avg_hours = round(avg_seconds / 3600, 1) if avg_seconds else None

    return CardApplicationStats(
        total_pending=status_counts.get(CardApplicationStatus.pending, 0),
        total_under_review=status_counts.get(CardApplicationStatus.under_review, 0),
        total_approved=status_counts.get(CardApplicationStatus.approved, 0),
        total_denied=status_counts.get(CardApplicationStatus.denied, 0),
        total_this_week=total_this_week,
        total_this_month=total_this_month,
        average_review_time_hours=avg_hours,
    )


@router.get("/staff/{application_id}", response_model=CardApplicationResponse)
async def get_application(
    application_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific application by ID."""
    result = await db.execute(
        select(LibraryCardApplication)
        .options(joinedload(LibraryCardApplication.reviewer))
        .where(LibraryCardApplication.id == application_id)
    )
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    return _build_application_response(application)


@router.post("/staff/{application_id}/review", response_model=CardApplicationResponse)
async def review_application(
    application_id: int,
    data: CardApplicationReview,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Review and update application status (approve, deny, or mark under review)."""
    result = await db.execute(
        select(LibraryCardApplication)
        .where(LibraryCardApplication.id == application_id)
    )
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # Validate state transition
    if application.status in [CardApplicationStatus.approved, CardApplicationStatus.denied]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application has already been {application.status}"
        )

    # If approving, refuse early when the linked user already has a card.
    # Overwriting silently is destructive; staff should consciously
    # deactivate the old card first. Anon-submit applications carry no
    # user_id, so probe by email for the same overwrite-protection (#688).
    if data.status == CardApplicationStatus.approved:
        linked_user = None
        if application.user_id:
            user_result = await db.execute(
                select(User).where(User.id == application.user_id)
            )
            linked_user = user_result.scalar_one_or_none()
        elif application.email:
            email_match = await db.execute(
                select(User).where(User.email_hash == email_blind_hash(application.email))
            )
            email_matches = email_match.scalars().all()
            if len(email_matches) == 1:
                linked_user = email_matches[0]
        if linked_user and linked_user.library_card:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": (
                        "This patron already has an active library card "
                        f"({linked_user.library_card}). Deactivate the "
                        "existing card before approving a new application."
                    ),
                    "existing_card_number": linked_user.library_card,
                    "user_id": linked_user.id,
                },
            )

    # Update application
    application.status = data.status
    application.review_notes = data.review_notes
    application.reviewed_by_id = staff_user.id
    application.reviewed_at = datetime.now(timezone.utc)

    if data.status == CardApplicationStatus.denied:
        application.denial_reason = data.denial_reason

    # If approved, generate a card number
    if data.status == CardApplicationStatus.approved:
        # Generate unique card number
        while True:
            card_number = generate_card_number()
            existing = await db.execute(
                select(LibraryCardApplication)
                .where(LibraryCardApplication.assigned_card_number == card_number)
            )
            if not existing.scalar_one_or_none():
                break

        application.assigned_card_number = card_number

        # Link the card to a user account. Prefer the explicit
        # application.user_id; otherwise fall back to a unique-email match
        # (#688: anon-submit applications register later and would
        # otherwise leave the user on a TMP card after approval).
        target_user = None
        if application.user_id:
            user_result = await db.execute(
                select(User).where(User.id == application.user_id)
            )
            target_user = user_result.scalar_one_or_none()
        elif application.email:
            user_result = await db.execute(
                select(User).where(User.email_hash == email_blind_hash(application.email))
            )
            email_matches = user_result.scalars().all()
            if len(email_matches) == 1:
                target_user = email_matches[0]
                application.user_id = target_user.id

        if target_user and not target_user.library_card:
            target_user.library_card = card_number

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(LibraryCardApplication)
        .options(joinedload(LibraryCardApplication.reviewer))
        .where(LibraryCardApplication.id == application_id)
    )
    application = result.scalar_one()

    # Send approval / denial notifications -- failures are non-fatal; the
    # review decision is already persisted.
    try:
        if application.status == CardApplicationStatus.approved:
            await send_card_application_approved(
                to_email=application.email,
                first_name=application.first_name,
                card_number=application.assigned_card_number,
                pickup_location=settings.library_name,
            )
        elif application.status == CardApplicationStatus.denied:
            await send_card_application_denied(
                to_email=application.email,
                first_name=application.first_name,
                denial_reason=application.denial_reason,
            )
    except Exception as exc:  # noqa: BLE001  # best-effort email — review already committed
        logger.warning(
            "Failed to send card application review email",
            extra={
                "application_id": application.id,
                "decision": application.status,
                "error": str(exc),
            },
        )

    return _build_application_response(application, staff_user)
