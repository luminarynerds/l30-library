# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API endpoints for book challenges and intellectual freedom resources."""

from app.core.logging import get_logger
from datetime import date
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...core.turnstile import verify_turnstile
from ...models.user import User, UserRole
from ...schemas.acquisition_rationale import AcquisitionRationaleRead
from ...schemas.book_challenge import (
    BookChallengeCreate, BookChallengeUpdate, BookChallengeResponse,
    BookChallengeDetailResponse, BookChallengePublicResponse,
    BookChallengeNoteCreate, BookChallengeNoteResponse,
    BookChallengeStats, PaginatedBookChallenges,
    PaginatedBookChallengePublic,
    PublicReconsiderationRequest, PublicReconsiderationResponse,
    IntellectualFreedomResourceCreate, IntellectualFreedomResourceUpdate,
    IntellectualFreedomResourceResponse
)
from ...services.acquisition_rationale_service import RationaleService
from ...services.book_challenge_service import (
    BookChallengeService, IntellectualFreedomService
)
from .auth import get_current_user, get_optional_user

logger = get_logger(__name__)
router = APIRouter(prefix="/book-challenges", tags=["book-challenges"])


def _ensure_staff(current_user: User) -> None:
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff or admin access required",
        )


# ============================================================================
# Public Endpoints (for intellectual freedom page)
# ============================================================================

def _public_challenge_to_response(c) -> BookChallengePublicResponse:
    suppress_author = bool(c.public_title)
    return BookChallengePublicResponse(
        id=c.id,
        catalog_item_id=c.catalog_item_id,
        public_title=c.public_title,
        title=c.title,
        author=None if suppress_author else c.author,
        primary_reason=(
            c.primary_reason.value
            if hasattr(c.primary_reason, "value")
            else (c.primary_reason or "other")
        ),
        outcome=(
            c.outcome.value
            if hasattr(c.outcome, "value")
            else (c.outcome or "pending")
        ),
        public_summary=c.public_summary,
        lessons_learned=c.lessons_learned,
        date_received=c.date_received,
        date_resolved=c.date_resolved,
    )


@router.get("/public", response_model=PaginatedBookChallengePublic)
async def list_public_challenges(
    year: int | None = Query(None, ge=1900, le=2100, description="Filter by year of date_received"),
    outcome: str | None = Query(None, description="Filter by outcome (lowercase enum value)"),
    reason: str | None = Query(None, description="Filter by primary reason (lowercase enum value)"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    List publicly visible book challenges for the intellectual freedom page.

    This endpoint is public and returns sanitised challenge information
    that the library has chosen to share. The response is paginated and
    supports filtering by year (of ``date_received``), outcome, and reason.

    Anonymity policy: rows with a ``public_title`` set ALSO have ``author``
    suppressed. See ``_public_challenge_to_response`` for the rationale.
    """
    items, total = await BookChallengeService.list_public_challenges(
        db,
        year=year,
        outcome=outcome,
        reason=reason,
        page=page,
        per_page=per_page,
    )
    return PaginatedBookChallengePublic(
        items=[_public_challenge_to_response(c) for c in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=ceil(total / per_page) if total > 0 else 1,
    )


@router.get("/public/stats", response_model=BookChallengeStats)
async def get_public_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Get public statistics about book challenges.

    Returns aggregate data about challenges without exposing sensitive details.
    """
    stats = await BookChallengeService.get_statistics(db)
    return BookChallengeStats(**stats)


@router.post(
    "/public/request",
    response_model=PublicReconsiderationResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/hour")
async def submit_reconsideration_request(  # noqa: role-check -- public reconsideration request intake, Turnstile-gated
    request: Request,
    request_data: PublicReconsiderationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a public request for reconsideration of library materials.

    This allows patrons to submit a formal challenge online. The request
    will be reviewed by library staff. No authentication is required.

    The patron must confirm they have read/viewed the material in its entirety.
    Bot abuse is blocked via Cloudflare Turnstile (fails open in dev when
    CF_TURNSTILE_SECRET is unset).
    """

    remote_ip = request.client.host if request.client else None
    if not await verify_turnstile(request_data.turnstile_token, remote_ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Captcha verification failed. Please retry.",
        )

    if not request_data.has_read_material:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must confirm that you have read or viewed the material in its entirety.",
        )

    challenge = await BookChallengeService.create_from_public_request(
        db, request_data.model_dump()
    )

    return PublicReconsiderationResponse(
        message=(
            "Thank you for submitting your request for reconsideration. "
            "Your request has been received and will be reviewed by the "
            "Materials Review Committee. You will receive a written response "
            "within 30 days. During the review process, the material will "
            "remain available to all patrons."
        ),
        reference_id=challenge.id,
        expected_response_days=30,
    )


# ============================================================================
# Staff Endpoints (require authentication)
# ============================================================================

@router.get("", response_model=PaginatedBookChallenges)
async def list_challenges(
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    outcome: str | None = Query(None, description="Filter by outcome"),
    reason: str | None = Query(None, description="Filter by primary reason"),
    search: str | None = Query(None, description="Search by title, author, challenger name, or ISBN"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all book challenges (staff only).

    Supports filtering by status, outcome, reason, and free-text search
    across title, author, challenger name, and ISBN.
    """
    _ensure_staff(current_user)

    challenges, total = await BookChallengeService.list_challenges(
        db,
        status=status_filter,
        outcome=outcome,
        reason=reason,
        search=search,
        page=page,
        per_page=per_page,
    )

    return PaginatedBookChallenges(
        items=[BookChallengeResponse.model_validate(c) for c in challenges],
        total=total,
        page=page,
        per_page=per_page,
        pages=ceil(total / per_page) if total > 0 else 1,
    )


@router.post("", response_model=BookChallengeResponse, status_code=status.HTTP_201_CREATED)
async def create_challenge(
    challenge_data: BookChallengeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new book challenge (staff only).

    Used when a formal reconsideration request is received in person or by mail.
    """
    _ensure_staff(current_user)

    challenge = await BookChallengeService.create_challenge(
        db, challenge_data.model_dump()
    )
    return BookChallengeResponse.model_validate(challenge)


@router.get("/stats", response_model=BookChallengeStats)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed statistics about book challenges (staff only)."""
    _ensure_staff(current_user)
    stats = await BookChallengeService.get_statistics(db)
    return BookChallengeStats(**stats)


@router.get("/export", response_class=StreamingResponse)
async def export_challenges_csv(
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    outcome: str | None = Query(None, description="Filter by outcome"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export book challenges as CSV (staff only).

    Useful for board reports, annual ALA reporting, and state compliance.
    """
    _ensure_staff(current_user)

    csv_content = await BookChallengeService.export_challenges_csv(
        db, status=status_filter, outcome=outcome
    )

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=book_challenges_export.csv"
        },
    )


@router.get("/{challenge_id}", response_model=BookChallengeDetailResponse)
async def get_challenge(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific book challenge with full details (staff only).

    Includes acquisition_rationale (or null) so staff can defend the item
    against the challenge using the original acquisition reasoning.
    """
    _ensure_staff(current_user)

    challenge = await BookChallengeService.get_challenge(
        db, challenge_id, include_notes=True
    )
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book challenge not found",
        )

    response = BookChallengeDetailResponse.model_validate(challenge)

    # M3: auto-load acquisition rationale (anti-banning defense surface).
    # Lookup is keyed by catalog_item_id; staff-entered challenges without
    # a catalog link return null.
    if challenge.catalog_item_id is not None:
        rationale = await RationaleService(db).get_by_catalog_item(
            challenge.catalog_item_id
        )
        if rationale is not None:
            response.acquisition_rationale = (
                AcquisitionRationaleRead.model_validate(rationale)
            )

    return response


@router.put("/{challenge_id}", response_model=BookChallengeResponse)
async def update_challenge(
    challenge_id: int,
    update_data: BookChallengeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a book challenge (staff only).

    M3: When lessons_learned is included and the challenge points at a
    catalog item with an existing acquisition rationale, the lesson is
    appended to rationale.weeding_signal_note with a timestamped prefix
    so future weeding/defense workflows pick up what we learned.
    """
    _ensure_staff(current_user)

    payload = update_data.model_dump(exclude_unset=True)
    lessons_learned = payload.get("lessons_learned")

    challenge = await BookChallengeService.update_challenge(
        db, challenge_id, payload, resolved_by=current_user
    )
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book challenge not found",
        )

    # M3 writeback: append lessons_learned to the rationale's weeding signal
    # note when both exist. Skipped when no catalog link, no rationale, or
    # no lessons text. Failure here must not break the challenge update,
    # so we log and continue.
    if lessons_learned and challenge.catalog_item_id is not None:
        try:
            svc = RationaleService(db)
            rat = await svc.get_by_catalog_item(challenge.catalog_item_id)
            if rat is not None:
                outcome_label = (
                    challenge.outcome.value
                    if hasattr(challenge.outcome, "value")
                    else str(challenge.outcome)
                )
                prefix = (
                    f"[Challenge #{challenge.id} ({outcome_label}, "
                    f"{date.today().isoformat()})]: "
                )
                prior = rat.weeding_signal_note or ""
                appended = (
                    (prior + "\n" if prior else "")
                    + prefix
                    + lessons_learned.strip()
                ).strip()
                rat.weeding_signal_note = appended
                await db.commit()
                await db.refresh(rat)
        except Exception:
            logger.exception(
                "Failed to write back challenge lessons to acquisition rationale "
                "(challenge_id=%s, catalog_item_id=%s)",
                challenge.id, challenge.catalog_item_id,
            )

    return BookChallengeResponse.model_validate(challenge)


@router.delete("/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_challenge(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a book challenge (admin only).

    This permanently removes the challenge and all associated notes.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to delete challenges",
        )

    success = await BookChallengeService.delete_challenge(db, challenge_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book challenge not found",
        )


@router.get("/{challenge_id}/notes", response_model=list[BookChallengeNoteResponse])
async def list_challenge_notes(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all notes for a book challenge (staff only)."""
    _ensure_staff(current_user)

    challenge = await BookChallengeService.get_challenge(
        db, challenge_id, include_notes=True
    )
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book challenge not found",
        )

    return [BookChallengeNoteResponse.model_validate(n) for n in challenge.notes]


@router.post(
    "/{challenge_id}/notes",
    response_model=BookChallengeNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_challenge_note(
    challenge_id: int,
    note_data: BookChallengeNoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a note to a book challenge (staff only)."""
    _ensure_staff(current_user)

    challenge = await BookChallengeService.get_challenge(db, challenge_id)
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book challenge not found",
        )

    note = await BookChallengeService.add_note(
        db, challenge_id,
        note=note_data.note,
        is_internal=note_data.is_internal,
        created_by=current_user
    )
    return BookChallengeNoteResponse.model_validate(note)


# ============================================================================
# Intellectual Freedom Resources Endpoints
# ============================================================================

resources_router = APIRouter(
    prefix="/intellectual-freedom-resources",
    tags=["intellectual-freedom"]
)


@resources_router.get("", response_model=list[IntellectualFreedomResourceResponse])
async def list_resources(
    resource_type: str | None = Query(None, description="Filter by type"),
    db: AsyncSession = Depends(get_db),
):
    resources = await IntellectualFreedomService.list_resources(
        db, active_only=True, resource_type=resource_type
    )
    return [IntellectualFreedomResourceResponse.model_validate(r) for r in resources]


@resources_router.post(
    "",
    response_model=IntellectualFreedomResourceResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_resource(
    resource_data: IntellectualFreedomResourceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_staff(current_user)

    resource = await IntellectualFreedomService.create_resource(
        db, resource_data.model_dump()
    )
    return IntellectualFreedomResourceResponse.model_validate(resource)


@resources_router.get("/{resource_id}", response_model=IntellectualFreedomResourceResponse)
async def get_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
):
    resource = await IntellectualFreedomService.get_resource(db, resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    return IntellectualFreedomResourceResponse.model_validate(resource)


@resources_router.put("/{resource_id}", response_model=IntellectualFreedomResourceResponse)
async def update_resource(
    resource_id: int,
    update_data: IntellectualFreedomResourceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_staff(current_user)

    resource = await IntellectualFreedomService.update_resource(
        db, resource_id, update_data.model_dump(exclude_unset=True)
    )
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    return IntellectualFreedomResourceResponse.model_validate(resource)


@resources_router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_staff(current_user)

    success = await IntellectualFreedomService.delete_resource(db, resource_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
