# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Shift Swap Board API Endpoints

Provides REST API for:
- Creating and managing shift swap listings
- Claiming shifts
- Viewing matches and notifications
- Managing staff preferences
- Viewing reliability scores
"""

from app.core.logging import get_logger
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from .dependencies import require_staff
from ...models.multi_branch import Branch
from ...services.shift_swap_service import ShiftSwapService
from ...schemas.shift_swap import (
    ShiftSwapListingCreate, ShiftSwapListingUpdate, ShiftSwapListingResponse,
    ShiftSwapListingDetailResponse,
    ShiftSwapListingType, ShiftSwapListingStatus,
    ShiftSwapClaimCreate, ShiftSwapClaimApprove, ShiftSwapClaimReject,
    ShiftSwapClaimResponse,
    StaffPreferenceProfileCreate, StaffPreferenceProfileUpdate, StaffPreferenceProfileResponse,
    SwapperReliabilityScoreResponse,
    ShiftSwapMatchResponse, ShiftSwapMatchDetailResponse,
    ShiftSwapNotificationResponse, ShiftSwapNotificationBatch,
    ShiftSwapListingFilter,
    UserShiftSwapSummary, ShiftSwapDashboardResponse,
    ShiftType,
)
from ...models import User

logger = get_logger(__name__)

router = APIRouter(prefix="/shift-swap", tags=["shift-swap"])


# ============================================================================
# Listing Endpoints
# ============================================================================

@router.post("/listings", response_model=ShiftSwapListingResponse)
async def create_listing(
    listing: ShiftSwapListingCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new shift swap listing"""
    try:
        service = ShiftSwapService(db)
        created_listing = await service.create_listing(
            user_id=current_user.id,
            branch_id=listing.branch_id,
            listing_type=listing.listing_type,
            shift_date=listing.shift_date,
            shift_start_time=listing.shift_start_time,
            shift_end_time=listing.shift_end_time,
            shift_type=listing.shift_type,
            is_partial=listing.is_partial,
            partial_description=listing.partial_description,
            description=listing.description,
            expires_at=listing.expires_at,
        )
        await db.commit()

        return ShiftSwapListingResponse.model_validate(created_listing)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/listings", response_model=dict)
async def get_listings(
    branch_id: Optional[int] = Query(None),
    listing_type: Optional[ShiftSwapListingType] = Query(None),
    shift_type: Optional[ShiftType] = Query(None),
    status: Optional[ShiftSwapListingStatus] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get shift swap listings with optional filters, enriched with display fields."""
    try:
        service = ShiftSwapService(db)
        listings, total = await service.get_listings(
            branch_id=branch_id,
            listing_type=listing_type,
            shift_type=shift_type,
            status=status,
            shift_date_from=date_from,
            shift_date_to=date_to,
            limit=limit,
            offset=offset,
            eager_load_relations=True,
        )

        listing_ids = [l.id for l in listings]
        branch_ids = {l.branch_id for l in listings if l.branch_id is not None}

        branches_by_id: dict = {}
        if branch_ids:
            branch_result = await db.execute(
                select(Branch).where(Branch.id.in_(branch_ids))
            )
            branches_by_id = {b.id: b for b in branch_result.scalars().all()}

        claim_counts = await service.get_claim_counts(listing_ids)
        claimed_by_me = await service.get_listings_claimed_by(current_user.id, listing_ids)

        enriched = []
        for l in listings:
            base = ShiftSwapListingResponse.model_validate(l).dict()
            user_full_name = None
            if getattr(l, "user", None) is not None:
                user_full_name = f"{l.user.first_name or ''} {l.user.last_name or ''}".strip() or None
            branch = branches_by_id.get(l.branch_id)
            enriched.append({
                **base,
                "user_name": user_full_name,
                "branch_name": branch.name if branch else None,
                "claims_count": claim_counts.get(l.id, 0),
                "is_owner": l.user_id == current_user.id,
                "has_claimed": l.id in claimed_by_me,
            })

        return {
            "listings": enriched,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/listings/{listing_id}", response_model=ShiftSwapListingDetailResponse)
async def get_listing(
    listing_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific listing with details"""
    try:
        service = ShiftSwapService(db)
        listing = await service.get_listing(listing_id)

        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")

        # Get claims count
        claims = await service.get_claims_for_listing(listing_id)

        # The branch relationship on ShiftSwapListing is intentionally disabled,
        # so look the branch up explicitly.
        branch = None
        if listing.branch_id is not None:
            branch_result = await db.execute(
                select(Branch).where(Branch.id == listing.branch_id)
            )
            branch = branch_result.scalar_one_or_none()

        user_full_name = None
        if getattr(listing, "user", None) is not None:
            user_full_name = f"{listing.user.first_name or ''} {listing.user.last_name or ''}".strip() or None

        return {
            **ShiftSwapListingResponse.model_validate(listing).dict(),
            "user_name": user_full_name,
            "branch_name": branch.name if branch else None,
            "claims_count": len(claims),
            "is_owner": listing.user_id == current_user.id,
            "has_claimed": any(c.claimer_id == current_user.id for c in claims),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/listings/{listing_id}", response_model=ShiftSwapListingResponse)
async def update_listing(
    listing_id: int,
    update: ShiftSwapListingUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a listing (owner only)"""
    try:
        service = ShiftSwapService(db)
        listing = await service.get_listing(listing_id)

        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")

        if listing.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this listing")

        # Update fields
        for key, value in update.dict(exclude_unset=True).items():
            if hasattr(listing, key) and value is not None:
                setattr(listing, key, value)

        listing.updated_at = datetime.now()
        await db.commit()

        return ShiftSwapListingResponse.model_validate(listing)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/listings/{listing_id}/withdraw", response_model=ShiftSwapListingResponse)
async def withdraw_listing(
    listing_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Withdraw a listing"""
    try:
        service = ShiftSwapService(db)
        listing = await service.withdraw_listing(listing_id, current_user.id)
        await db.commit()

        return ShiftSwapListingResponse.model_validate(listing)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# Claim Endpoints
# ============================================================================

@router.post("/claims", response_model=ShiftSwapClaimResponse)
async def claim_shift(
    claim: ShiftSwapClaimCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Claim a shift swap listing"""
    try:
        service = ShiftSwapService(db)
        created_claim = await service.claim_listing(
            listing_id=claim.listing_id,
            claimer_id=current_user.id,
            swap_shift_date=claim.swap_shift_date,
            swap_shift_start_time=claim.swap_shift_start_time,
            swap_shift_end_time=claim.swap_shift_end_time,
            message=claim.message,
        )
        await db.commit()

        result = ShiftSwapClaimResponse.model_validate(created_claim)
        result.claimer_name = current_user.first_name + " " + current_user.last_name
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/listings/{listing_id}/claims", response_model=list)
async def get_listing_claims(
    listing_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all claims for a listing (owner only)"""
    try:
        service = ShiftSwapService(db)
        listing = await service.get_listing(listing_id)

        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")

        if listing.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view claims")

        claims = await service.get_claims_for_listing(listing_id)

        return [
            {
                **ShiftSwapClaimResponse.model_validate(c).dict(),
                "claimer_name": c.claimer.first_name + " " + c.claimer.last_name,
            }
            for c in claims
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/claims/{claim_id}/approve", response_model=ShiftSwapClaimResponse)
async def approve_claim(
    claim_id: int,
    approval: ShiftSwapClaimApprove,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Approve a claim (listing owner only)"""
    try:
        service = ShiftSwapService(db)
        claim = await service.approve_claim(
            claim_id=claim_id,
            approver_id=current_user.id,
            approval_notes=approval.approval_notes,
        )
        await db.commit()

        result = ShiftSwapClaimResponse.model_validate(claim)
        result.claimer_name = claim.claimer.first_name + " " + claim.claimer.last_name
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/claims/{claim_id}/reject", response_model=ShiftSwapClaimResponse)
async def reject_claim(
    claim_id: int,
    rejection: ShiftSwapClaimReject,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Reject a claim (listing owner only)"""
    try:
        service = ShiftSwapService(db)
        claim = await service.reject_claim(
            claim_id=claim_id,
            rejector_id=current_user.id,
            rejection_reason=rejection.rejection_reason,
        )
        await db.commit()

        result = ShiftSwapClaimResponse.model_validate(claim)
        result.claimer_name = claim.claimer.first_name + " " + claim.claimer.last_name
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# Preference Profile Endpoints
# ============================================================================

@router.get("/preferences", response_model=StaffPreferenceProfileResponse)
async def get_preference_profile(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get staff preference profile"""
    try:
        service = ShiftSwapService(db)
        profile = await service.get_or_create_preference_profile(current_user.id)
        return StaffPreferenceProfileResponse.model_validate(profile)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/preferences", response_model=StaffPreferenceProfileResponse)
async def create_preference_profile(
    preferences: StaffPreferenceProfileCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create or update staff preference profile"""
    try:
        service = ShiftSwapService(db)
        profile = await service.update_preference_profile(
            current_user.id,
            **preferences.dict()
        )
        await db.commit()
        return StaffPreferenceProfileResponse.model_validate(profile)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/preferences", response_model=StaffPreferenceProfileResponse)
async def update_preference_profile(
    preferences: StaffPreferenceProfileUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update staff preference profile"""
    try:
        service = ShiftSwapService(db)
        profile = await service.update_preference_profile(
            current_user.id,
            **preferences.dict(exclude_unset=True)
        )
        await db.commit()
        return StaffPreferenceProfileResponse.model_validate(profile)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# Reliability Score Endpoints
# ============================================================================

@router.get("/reliability/{user_id}", response_model=SwapperReliabilityScoreResponse)
async def get_reliability_score(
    user_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get reliability score for a user"""
    try:
        service = ShiftSwapService(db)
        score = await service.get_or_create_reliability_score(user_id)
        return SwapperReliabilityScoreResponse.model_validate(score)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/reliability", response_model=SwapperReliabilityScoreResponse)
async def get_my_reliability_score(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get your own reliability score"""
    try:
        service = ShiftSwapService(db)
        score = await service.get_or_create_reliability_score(current_user.id)
        return SwapperReliabilityScoreResponse.model_validate(score)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# Notifications Endpoints
# ============================================================================

@router.get("/notifications", response_model=ShiftSwapNotificationBatch)
async def get_notifications(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get shift swap notifications"""
    try:
        service = ShiftSwapService(db)
        notifications, total = await service.get_user_notifications(
            current_user.id,
            limit=limit,
            offset=offset,
        )

        unread = sum(1 for n in notifications if not n.is_read)

        return ShiftSwapNotificationBatch(
            notifications=[ShiftSwapNotificationResponse.model_validate(n) for n in notifications],
            total=total,
            unread_count=unread,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read"""
    try:
        service = ShiftSwapService(db)
        notification = await service.mark_notification_read(notification_id, current_user.id)
        await db.commit()
        return ShiftSwapNotificationResponse.model_validate(notification)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# Matches Endpoints
# ============================================================================

@router.get("/matches", response_model=dict)
async def get_my_matches(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get matches for the current user's listings"""
    try:
        service = ShiftSwapService(db)
        matches = await service.get_user_matches(current_user.id)
        return {
            "matches": [
                {
                    **ShiftSwapMatchResponse.model_validate(m).dict(),
                    "giver_listing": ShiftSwapListingResponse.model_validate(m.giver_listing).dict()
                    if m.giver_listing else None,
                    "taker_listing": ShiftSwapListingResponse.model_validate(m.taker_listing).dict()
                    if m.taker_listing else None,
                }
                for m in matches
            ],
            "total": len(matches),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/matches/{match_id}/accept")
async def accept_match(
    match_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Accept a shift swap match"""
    try:
        service = ShiftSwapService(db)
        match = await service.accept_match(match_id, current_user.id)
        await db.commit()
        return ShiftSwapMatchResponse.model_validate(match)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/matches/{match_id}/reject")
async def reject_match(
    match_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Reject a shift swap match"""
    try:
        service = ShiftSwapService(db)
        match = await service.reject_match(match_id, current_user.id)
        await db.commit()
        return ShiftSwapMatchResponse.model_validate(match)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/matches/run")
async def run_matching(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Trigger on-demand match finding for all open listings"""
    try:
        service = ShiftSwapService(db)
        matches = await service.find_matches()
        notified = await service.notify_matches(matches)
        await db.commit()
        return {
            "matches_found": len(matches),
            "notifications_sent": len(notified),
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# Dashboard Endpoint
# ============================================================================

@router.get("/dashboard", response_model=ShiftSwapDashboardResponse)
async def get_dashboard(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get shift swap dashboard with summary and recent activity"""
    try:
        service = ShiftSwapService(db)

        # Get user's listings
        user_listings, _ = await service.get_listings(user_id=current_user.id, limit=5)

        # Get reliability score
        reliability = await service.get_or_create_reliability_score(current_user.id)

        # Get notifications
        notifications, _ = await service.get_user_notifications(current_user.id, limit=5)

        # Get preference profile
        try:
            preferences = await service.get_or_create_preference_profile(current_user.id)
            pref_response = StaffPreferenceProfileResponse.model_validate(preferences)
        except Exception as e:  # noqa: BLE001  # preference profile best-effort — degrade dashboard gracefully
            logger.warning(
                f"Failed to load preference profile for user {current_user.id}: {e}",
                exc_info=True,
            )
            pref_response = None

        summary = UserShiftSwapSummary(
            active_listings_count=sum(1 for l in user_listings if l.status.value == "open"),
            pending_claims_count=sum(1 for l in user_listings if l.status.value == "claimed"),
            approved_swaps_count=reliability.total_completed_swaps,
            completed_swaps_count=reliability.total_completed_swaps,
            reliability_score=reliability.reliability_score,
            total_swaps=reliability.total_swap_claims,
            open_matches_count=0,  # Would need to query matches
        )

        return ShiftSwapDashboardResponse(
            user_summary=summary,
            recent_listings=[ShiftSwapListingResponse.model_validate(l) for l in user_listings],
            recent_notifications=[ShiftSwapNotificationResponse.model_validate(n) for n in notifications],
            recent_matches=[],  # Would populate with actual matches
            preference_profile=pref_response,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
