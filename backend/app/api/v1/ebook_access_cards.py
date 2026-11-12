# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Ebook Access Card API Endpoints

Provides endpoints for:
- Browsing available subscription tiers and pricing
- Purchasing an ebook access card (out-of-district patrons)
- Viewing and managing active subscriptions
- Staff admin: viewing card stats, managing cards
"""
import secrets
import string
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.ebook_access_card import (
    EbookAccessCard, EbookCardStatus, EbookCardTier, EbookCardTierConfig,
)
from ...models.user import User
from ...schemas.ebook_access_card import (
    EbookCardPurchaseRequest,
    EbookCardRenewRequest,
    EbookCardResponse,
    EbookCardStatsResponse,
    EbookCardTierInfo,
)
from .auth import get_current_user
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/ebook-access-cards", tags=["ebook-access-cards"])
admin_router = APIRouter(prefix="/admin/ebook-access-cards", tags=["admin-ebook-access-cards"])


# ============================================================================
# Default tier configurations (used when DB configs don't exist yet)
# ============================================================================

DEFAULT_TIERS = {
    EbookCardTier.BASIC: {
        "display_name": "Basic",
        "description": "Legacy tier – no longer available.",
        "annual_fee": 25.00,
        "max_concurrent_borrows": 2,
        "max_monthly_borrows": 5,
        "author_royalty_share_pct": 40.0,
        "is_available": False,
    },
    EbookCardTier.STANDARD: {
        "display_name": "Indie Card",
        "description": "Unlimited access to our indie ebook collection. $35/year, read everything.",
        "annual_fee": 35.00,
        "max_concurrent_borrows": 10,
        "max_monthly_borrows": 999,
        "author_royalty_share_pct": 40.0,
    },
    EbookCardTier.UNLIMITED: {
        "display_name": "Unlimited",
        "description": "Legacy tier – no longer available.",
        "annual_fee": 50.00,
        "max_concurrent_borrows": 10,
        "max_monthly_borrows": 999,
        "author_royalty_share_pct": 40.0,
        "is_available": False,
    },
}


def _generate_card_number() -> str:
    chars = string.ascii_uppercase + string.digits
    random_part = "".join(secrets.choice(chars) for _ in range(8))
    return f"EAC-{random_part}"


async def _get_tier_config(tier: EbookCardTier, db: AsyncSession) -> dict:
    result = await db.execute(
        select(EbookCardTierConfig).where(EbookCardTierConfig.tier == tier)
    )
    config = result.scalar_one_or_none()
    if config:
        return {
            "display_name": config.display_name,
            "description": config.description,
            "annual_fee": config.annual_fee,
            "max_concurrent_borrows": config.max_concurrent_borrows,
            "max_monthly_borrows": config.max_monthly_borrows,
            "is_available": config.is_available,
            "author_royalty_share_pct": config.author_royalty_share_pct,
        }
    defaults = DEFAULT_TIERS.get(tier, DEFAULT_TIERS[EbookCardTier.STANDARD])
    return {**{"is_available": True}, **defaults}


# ============================================================================
# Public Endpoints
# ============================================================================

@router.get("/tiers", response_model=list[EbookCardTierInfo])
async def list_tiers(db: AsyncSession = Depends(get_db)):
    """List available ebook access card tiers and pricing."""
    tiers = []
    for tier in EbookCardTier:
        config = await _get_tier_config(tier, db)
        if config.get("is_available", True):
            tiers.append(EbookCardTierInfo(
                tier=tier.value,
                display_name=config["display_name"],
                description=config.get("description"),
                annual_fee=config["annual_fee"],
                max_concurrent_borrows=config["max_concurrent_borrows"],
                max_monthly_borrows=config["max_monthly_borrows"],
                is_available=True,
            ))
    return tiers


@router.post("/purchase", response_model=EbookCardResponse, status_code=status.HTTP_201_CREATED)
async def purchase_ebook_card(
    request: EbookCardPurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Purchase an ebook access card for indie ebook borrowing.

    This creates the card in PENDING_PAYMENT status. In production,
    the Stripe payment flow would activate it upon successful charge.
    For now, cards are auto-activated for development.
    """
    # Validate tier
    try:
        tier = EbookCardTier(request.tier)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier. Choose from: {', '.join(t.value for t in EbookCardTier)}",
        ) from None

    # Check for existing active card
    existing = await db.execute(
        select(EbookAccessCard).where(
            EbookAccessCard.user_id == current_user.id,
            EbookAccessCard.status == EbookCardStatus.ACTIVE,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="You already have an active ebook access card. Renew or cancel it first.",
        )

    config = await _get_tier_config(tier, db)
    if not config.get("is_available", True):
        raise HTTPException(status_code=400, detail="This tier is not currently available.")

    now = datetime.now(timezone.utc)
    card = EbookAccessCard(
        user_id=current_user.id,
        card_number=_generate_card_number(),
        tier=tier,
        status=EbookCardStatus.ACTIVE,  # Auto-activate for now
        annual_fee=config["annual_fee"],
        fee_paid_at=now,
        starts_at=now,
        expires_at=now + timedelta(days=365),
        max_concurrent_borrows=config["max_concurrent_borrows"],
        max_monthly_borrows=config["max_monthly_borrows"],
        borrows_this_month=0,
        month_reset_at=now,
        home_state=request.home_state,
        home_zip=request.home_zip,
        auto_renew=request.auto_renew,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)

    logger.info(
        "Ebook access card purchased: card=%s user=%s tier=%s fee=$%.2f",
        card.card_number, current_user.id, tier.value, config["annual_fee"],
    )

    return EbookCardResponse(
        id=card.id,
        card_number=card.card_number,
        tier=str(card.tier),
        status=str(card.status),
        annual_fee=card.annual_fee,
        starts_at=card.starts_at,
        expires_at=card.expires_at,
        max_concurrent_borrows=card.max_concurrent_borrows,
        max_monthly_borrows=card.max_monthly_borrows,
        borrows_this_month=card.borrows_this_month,
        total_borrows=card.total_borrows,
        auto_renew=card.auto_renew,
        can_borrow=card.can_borrow,
        created_at=card.created_at,
    )


@router.get("/my-card", response_model=EbookCardResponse | None)
async def get_my_card(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's active ebook access card, or null if none."""
    result = await db.execute(
        select(EbookAccessCard).where(
            EbookAccessCard.user_id == current_user.id,
            EbookAccessCard.status.in_([
                EbookCardStatus.ACTIVE,
                EbookCardStatus.PENDING_PAYMENT,
            ]),
        ).order_by(EbookAccessCard.created_at.desc())
    )
    card = result.scalar_one_or_none()
    if not card:
        return None

    return EbookCardResponse(
        id=card.id,
        card_number=card.card_number,
        tier=str(card.tier),
        status=str(card.status),
        annual_fee=card.annual_fee,
        starts_at=card.starts_at,
        expires_at=card.expires_at,
        max_concurrent_borrows=card.max_concurrent_borrows,
        max_monthly_borrows=card.max_monthly_borrows,
        borrows_this_month=card.borrows_this_month,
        total_borrows=card.total_borrows,
        auto_renew=card.auto_renew,
        can_borrow=card.can_borrow,
        created_at=card.created_at,
    )


@router.post("/my-card/cancel")
async def cancel_my_card(
    reason: str = Query(None, description="Optional cancellation reason"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel the current user's ebook access card."""
    result = await db.execute(
        select(EbookAccessCard).where(
            EbookAccessCard.user_id == current_user.id,
            EbookAccessCard.status == EbookCardStatus.ACTIVE,
        )
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="No active card to cancel.")

    card.status = EbookCardStatus.CANCELLED
    card.cancelled_at = datetime.now(timezone.utc)
    card.cancellation_reason = reason
    await db.commit()

    logger.info("Ebook access card cancelled: card=%s user=%s", card.card_number, current_user.id)
    return {"message": "Card cancelled. Access remains until expiration date.", "expires_at": str(card.expires_at)}


@router.post("/my-card/renew", response_model=EbookCardResponse)
async def renew_my_card(
    request: EbookCardRenewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Renew an expiring or expired ebook access card."""
    result = await db.execute(
        select(EbookAccessCard).where(
            EbookAccessCard.user_id == current_user.id,
        ).order_by(EbookAccessCard.created_at.desc())
    )
    old_card = result.scalars().first()
    if not old_card:
        raise HTTPException(status_code=404, detail="No card found to renew. Purchase a new one instead.")

    # Determine tier (keep existing or upgrade/downgrade)
    tier = EbookCardTier(request.tier) if request.tier else old_card.tier
    config = await _get_tier_config(tier, db)

    now = datetime.now(timezone.utc)
    # Start from expiration if card hasn't expired yet, otherwise from now
    start = old_card.expires_at if old_card.expires_at and old_card.expires_at > now else now

    old_card.status = EbookCardStatus.EXPIRED
    new_card = EbookAccessCard(
        user_id=current_user.id,
        card_number=_generate_card_number(),
        tier=tier,
        status=EbookCardStatus.ACTIVE,
        annual_fee=config["annual_fee"],
        fee_paid_at=now,
        starts_at=start,
        expires_at=start + timedelta(days=365),
        max_concurrent_borrows=config["max_concurrent_borrows"],
        max_monthly_borrows=config["max_monthly_borrows"],
        borrows_this_month=0,
        month_reset_at=now,
        home_state=old_card.home_state,
        home_zip=old_card.home_zip,
        auto_renew=old_card.auto_renew,
    )
    db.add(new_card)
    await db.commit()
    await db.refresh(new_card)

    return EbookCardResponse(
        id=new_card.id,
        card_number=new_card.card_number,
        tier=str(new_card.tier),
        status=str(new_card.status),
        annual_fee=new_card.annual_fee,
        starts_at=new_card.starts_at,
        expires_at=new_card.expires_at,
        max_concurrent_borrows=new_card.max_concurrent_borrows,
        max_monthly_borrows=new_card.max_monthly_borrows,
        borrows_this_month=new_card.borrows_this_month,
        total_borrows=new_card.total_borrows,
        auto_renew=new_card.auto_renew,
        can_borrow=new_card.can_borrow,
        created_at=new_card.created_at,
    )


# ============================================================================
# Admin Endpoints
# ============================================================================

@admin_router.get("/stats", response_model=EbookCardStatsResponse)
async def get_card_stats(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    # Total counts by status
    status_counts = {}
    for s in EbookCardStatus:
        result = await db.execute(
            select(func.count(EbookAccessCard.id)).where(EbookAccessCard.status == s)
        )
        status_counts[s.value] = result.scalar() or 0

    # Total revenue
    rev_result = await db.execute(
        select(func.coalesce(func.sum(EbookAccessCard.annual_fee), 0.0)).where(
            EbookAccessCard.fee_paid_at.isnot(None)
        )
    )
    total_revenue = rev_result.scalar() or 0.0

    # Revenue this year
    year_start = datetime(datetime.now(timezone.utc).year, 1, 1, tzinfo=timezone.utc)
    yr_result = await db.execute(
        select(func.coalesce(func.sum(EbookAccessCard.annual_fee), 0.0)).where(
            EbookAccessCard.fee_paid_at >= year_start
        )
    )
    revenue_this_year = yr_result.scalar() or 0.0

    # Cards by tier
    tier_counts = {}
    for t in EbookCardTier:
        result = await db.execute(
            select(func.count(EbookAccessCard.id)).where(
                EbookAccessCard.tier == t,
                EbookAccessCard.status == EbookCardStatus.ACTIVE,
            )
        )
        tier_counts[t.value] = result.scalar() or 0

    # Top states
    state_result = await db.execute(
        select(
            EbookAccessCard.home_state,
            func.count(EbookAccessCard.id).label("count"),
        )
        .where(EbookAccessCard.home_state.isnot(None))
        .group_by(EbookAccessCard.home_state)
        .order_by(func.count(EbookAccessCard.id).desc())
        .limit(10)
    )
    top_states = [{"state": row[0], "count": row[1]} for row in state_result.all()]

    return EbookCardStatsResponse(
        total_cards_issued=sum(status_counts.values()),
        active_cards=status_counts.get("active", 0),
        expired_cards=status_counts.get("expired", 0),
        cancelled_cards=status_counts.get("cancelled", 0),
        total_revenue=total_revenue,
        revenue_this_year=revenue_this_year,
        cards_by_tier=tier_counts,
        top_states=top_states,
    )


@admin_router.get("/cards")
async def list_all_cards(
    status_filter: str = Query(None, alias="status"),
    tier_filter: str = Query(None, alias="tier"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    query = select(EbookAccessCard).order_by(EbookAccessCard.created_at.desc())

    if status_filter:
        try:
            query = query.where(EbookAccessCard.status == EbookCardStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status filter.") from None
    if tier_filter:
        try:
            query = query.where(EbookAccessCard.tier == EbookCardTier(tier_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid tier filter.") from None

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    cards = result.scalars().all()

    return [
        EbookCardResponse(
            id=c.id,
            card_number=c.card_number,
            tier=str(c.tier),
            status=str(c.status),
            annual_fee=c.annual_fee,
            starts_at=c.starts_at,
            expires_at=c.expires_at,
            max_concurrent_borrows=c.max_concurrent_borrows,
            max_monthly_borrows=c.max_monthly_borrows,
            borrows_this_month=c.borrows_this_month,
            total_borrows=c.total_borrows,
            auto_renew=c.auto_renew,
            can_borrow=c.can_borrow,
            created_at=c.created_at,
        )
        for c in cards
    ]
