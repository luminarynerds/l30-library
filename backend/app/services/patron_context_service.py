# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Patron Context Service

Assembles multi-table patron context payloads used by the staff patron
detail and context-card endpoints. Extracted from
app/api/v1/staff/patron_operations.py to keep route handlers thin.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.catalog import CatalogItem, ItemStatus
from ..models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ..models.fine import Fine, FineStatus
from ..models.gamification import Achievement, UserAchievement, UserStats
from ..models.patron_communication import PatronNote
from ..models.user import PatronStatus, User
from ..schemas.circulation import CheckoutResponse, HoldResponse
from ..schemas.fine import FineResponse


# =============================================================================
# Context Card Schemas
# =============================================================================


class StaffNote(BaseModel):
    category: str
    content: str
    priority: str
    created_at: datetime | None = None


class AccountAlert(BaseModel):
    alert_type: str  # 'block', 'suspension', 'overdue', 'high_fines', 'no_holds'
    severity: str  # 'info', 'warning', 'critical'
    message: str
    details: dict | None = None


class CheckoutSummary(BaseModel):
    total_count: int
    active_count: int
    overdue_count: int
    due_soon_count: int  # Items due within 3 days
    due_soon_items: list[dict] = []  # id, title, due_date


class HoldSummary(BaseModel):
    total_pending: int
    ready_for_pickup_count: int
    in_transit_count: int = 0  # Pending holds whose item is currently in transit between branches
    ready_items: list[dict] = []  # id, title, position, expires_at


class RecentGenre(BaseModel):
    genre: str
    count: int


class LoyaltyStatus(BaseModel):
    total_xp: int = 0
    current_level: str = "Member"
    achievements_earned: int = 0
    achievements_list: list[dict] = []  # name, icon, earned_at


class PatronContextCardResponse(BaseModel):
    # Basic identity & verification
    id: int
    first_name: str
    last_name: str
    preferred_name: str | None = None
    pronouns: str | None = None
    photo_url: str | None = None
    library_card: str | None = None

    # Status indicators (prominently displayed)
    patron_status: str  # 'active', 'suspended', 'blocked', 'deceased'
    account_alerts: list[AccountAlert] = []

    # Contact & preferences
    email: str
    phone: str | None = None
    language_preference: str | None = None
    accessibility_needs: str | None = None

    # Visit & activity history
    created_at: datetime
    last_login: datetime | None = None  # Last time here (login/visit)
    checkout_frequency: str  # 'very_active', 'active', 'moderate', 'inactive'
    total_checkouts_lifetime: int = 0

    # Current borrowing status
    checkouts: CheckoutSummary
    holds: HoldSummary
    fines: dict | None = None  # total_owed, unpaid_count

    # Patron preferences
    reading_preferences: list[RecentGenre] = []
    staff_notes: list[StaffNote] = []

    # Loyalty & engagement
    loyalty_status: LoyaltyStatus


# =============================================================================
# Assembly functions
# =============================================================================


async def assemble_patron_context_card(
    patron_id: int,
    patron: User,
    db: AsyncSession,
) -> PatronContextCardResponse:
    """Gather all data needed for the patron context card and return it assembled.

    Called by the /staff/patrons/{patron_id}/context-card route after auth and
    the audit log entry have been handled by the route itself.
    """
    # =========================================================================
    # Checkouts Summary
    # =========================================================================
    now = datetime.now(timezone.utc)
    three_days_ahead = now + timedelta(days=3)

    checkouts_result = await db.execute(
        select(Checkout, CatalogItem)
        .join(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(
            Checkout.user_id == patron_id,
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
        .order_by(Checkout.due_date)
    )
    checkout_rows = checkouts_result.all()

    active_count = sum(1 for c, _ in checkout_rows if c.status == CheckoutStatus.active)
    overdue_count = sum(1 for c, _ in checkout_rows if c.status == CheckoutStatus.overdue)
    due_soon_items = [
        {
            "id": c.id,
            "item_id": item.id,
            "title": item.title,
            "author": item.author,
            "due_date": c.due_date,
        }
        for c, item in checkout_rows
        if c.status == CheckoutStatus.active and now < c.due_date <= three_days_ahead
    ]

    # Get total lifetime checkouts
    total_checkouts_result = await db.execute(
        select(func.count(Checkout.id)).where(Checkout.user_id == patron_id)
    )
    total_checkouts = total_checkouts_result.scalar() or 0

    # Determine checkout frequency
    if total_checkouts > 0:
        days_member = (now - patron.created_at).days + 1 if patron.created_at else 1
        checkouts_per_month = (total_checkouts / max(1, days_member)) * 30
        if checkouts_per_month >= 5:
            checkout_frequency = "very_active"
        elif checkouts_per_month >= 2:
            checkout_frequency = "active"
        elif checkouts_per_month >= 0.5:
            checkout_frequency = "moderate"
        else:
            checkout_frequency = "inactive"
    else:
        checkout_frequency = "inactive"

    checkouts_summary = CheckoutSummary(
        total_count=len(checkout_rows),
        active_count=active_count,
        overdue_count=overdue_count,
        due_soon_count=len(due_soon_items),
        due_soon_items=due_soon_items[:5],  # Show top 5
    )

    # =========================================================================
    # Holds Summary
    # =========================================================================
    holds_result = await db.execute(
        select(Hold, CatalogItem)
        .join(CatalogItem, Hold.item_id == CatalogItem.id)
        .where(
            Hold.user_id == patron_id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
        .order_by(Hold.status.desc(), Hold.created_at)  # Ready items first
    )
    holds_rows = holds_result.all()

    ready_items = [
        {
            "id": h.id,
            "item_id": item.id,
            "title": item.title,
            "author": item.author,
            "status": h.status,
            "position": h.position,
            "expires_at": h.expires_at,
        }
        for h, item in holds_rows
        if h.status == HoldStatus.ready
    ]

    holds_summary = HoldSummary(
        total_pending=sum(1 for h, _ in holds_rows if h.status == HoldStatus.pending),
        ready_for_pickup_count=len(ready_items),
        in_transit_count=sum(
            1 for h, item in holds_rows
            if h.status == HoldStatus.pending and item.status == ItemStatus.in_transit
        ),
        ready_items=ready_items[:5],  # Show top 5
    )

    # =========================================================================
    # Account Alerts
    # =========================================================================
    alerts: list[AccountAlert] = []

    if patron.patron_status == PatronStatus.BLOCKED:
        alerts.append(AccountAlert(
            alert_type="block",
            severity="critical",
            message=f"Account Blocked: {patron.block_reason or 'No reason provided'}",
            details={"blocked_at": patron.blocked_at},
        ))
    elif patron.patron_status == PatronStatus.SUSPENDED:
        alerts.append(AccountAlert(
            alert_type="suspension",
            severity="warning",
            message=f"Account Suspended: {patron.suspension_reason or 'No reason provided'}",
            details={"suspended_at": patron.suspended_at, "suspended_until": patron.suspended_until},
        ))
    elif patron.patron_status == PatronStatus.DECEASED:
        alerts.append(AccountAlert(
            alert_type="deceased",
            severity="critical",
            message="Patron marked as deceased",
            details={"date_of_death": patron.date_of_death},
        ))

    # Check for overdue items
    if overdue_count > 0:
        alerts.append(AccountAlert(
            alert_type="overdue",
            severity="warning",
            message=f"{overdue_count} overdue item(s)",
            details={"count": overdue_count},
        ))

    # Check for high fines
    fines_result = await db.execute(
        select(Fine)
        .where(
            Fine.user_id == patron_id,
            Fine.status.in_([FineStatus.unpaid, FineStatus.partial]),
        )
    )
    fines_list = fines_result.scalars().all()
    total_owed = sum(f.amount - f.amount_paid for f in fines_list)

    if total_owed > 0:
        alerts.append(AccountAlert(
            alert_type="high_fines",
            severity="warning" if total_owed <= 25 else "critical",
            message=f"Outstanding fines: ${total_owed:.2f}",
            details={"total": float(total_owed), "count": len(fines_list)},
        ))

    # Check for no holds ready (info for staff)
    if len(ready_items) == 0 and len(holds_rows) > 0:
        alerts.append(AccountAlert(
            alert_type="no_holds_ready",
            severity="info",
            message=f"{holds_summary.total_pending} hold(s) pending",
            details=None,
        ))

    # =========================================================================
    # Staff Notes (recent, high priority first)
    # =========================================================================
    notes_result = await db.execute(
        select(PatronNote)
        .where(
            PatronNote.patron_id == patron_id,
            PatronNote.is_deleted == False,
        )
        .order_by(PatronNote.priority.desc(), PatronNote.created_at.desc())
        .limit(5)  # Show top 5 notes
    )
    notes_rows = notes_result.scalars().all()

    staff_notes = [
        StaffNote(
            category=n.category.value if hasattr(n.category, 'value') else str(n.category),
            content=n.content,
            priority=n.priority.value if hasattr(n.priority, 'value') else str(n.priority),
            created_at=n.created_at,
        )
        for n in notes_rows
    ]

    # =========================================================================
    # Reading Preferences (recent genres from checkouts)
    # =========================================================================
    # Get recently returned items to determine reading preferences
    recent_checkouts_result = await db.execute(
        select(Checkout, CatalogItem)
        .join(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(
            Checkout.user_id == patron_id,
            Checkout.status == CheckoutStatus.returned,
            Checkout.returned_at.isnot(None),
        )
        .order_by(Checkout.returned_at.desc())
        .limit(30)  # Get last 30 returned items
    )
    recent_items = recent_checkouts_result.all()

    # Count genres from subjects field
    genre_counts: dict[str, int] = {}
    for checkout, item in recent_items:
        if item.subjects:
            for subject in item.subjects.split(","):
                subject = subject.strip()
                if subject:
                    genre_counts[subject] = genre_counts.get(subject, 0) + 1

    # Sort by count and get top 5
    top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    reading_preferences = [
        RecentGenre(genre=genre, count=count)
        for genre, count in top_genres
    ]

    # =========================================================================
    # Loyalty Program Status & Achievements
    # =========================================================================
    user_stats_result = await db.execute(
        select(UserStats).where(UserStats.user_id == patron_id)
    )
    user_stats = user_stats_result.scalar_one_or_none()

    # Determine loyalty level based on XP
    xp = user_stats.total_xp if user_stats else 0
    if xp >= 1000:
        current_level = "Platinum"
    elif xp >= 500:
        current_level = "Gold"
    elif xp >= 100:
        current_level = "Silver"
    else:
        current_level = "Member"

    # Get achievements
    achievements_result = await db.execute(
        select(UserAchievement, Achievement)
        .join(Achievement, UserAchievement.achievement_id == Achievement.id)
        .where(UserAchievement.user_id == patron_id)
        .order_by(UserAchievement.earned_at.desc())
        .limit(10)
    )
    achievements_rows = achievements_result.all()

    achievements_list = [
        {
            "name": ach.name,
            "icon": ach.icon,
            "earned_at": ua.earned_at,
        }
        for ua, ach in achievements_rows
    ]

    loyalty_status = LoyaltyStatus(
        total_xp=xp,
        current_level=current_level,
        achievements_earned=len(achievements_list),
        achievements_list=achievements_list,
    )

    # =========================================================================
    # Build Response
    # =========================================================================
    return PatronContextCardResponse(
        id=patron.id,
        first_name=patron.first_name,
        last_name=patron.last_name,
        preferred_name=getattr(patron, 'preferred_name', None),  # If field exists
        pronouns=getattr(patron, 'pronouns', None),  # If field exists
        photo_url=patron.photo_url,
        library_card=patron.library_card,
        patron_status=patron.patron_status.value if hasattr(patron.patron_status, 'value') else str(patron.patron_status),
        account_alerts=alerts,
        email=patron.email,
        phone=patron.phone,
        language_preference=patron.language_preference,
        accessibility_needs=patron.accessibility_needs,
        created_at=patron.created_at,
        last_login=patron.last_login,
        checkout_frequency=checkout_frequency,
        total_checkouts_lifetime=total_checkouts,
        checkouts=checkouts_summary,
        holds=holds_summary,
        fines={"total_owed": float(total_owed), "unpaid_count": len(fines_list)},
        reading_preferences=reading_preferences,
        staff_notes=staff_notes,
        loyalty_status=loyalty_status,
    )


async def assemble_patron_detail_fields(
    patron_id: int,
    db: AsyncSession,
) -> tuple[list[CheckoutResponse], list[HoldResponse], list[FineResponse], Decimal]:
    """Fetch and assemble checkouts, holds, fines, and total owed for a patron.

    Called by the /staff/patrons/{patron_id} route after auth and the audit
    log entry have been handled by the route itself.
    """
    checkouts_result = await db.execute(
        select(Checkout, CatalogItem)
        .join(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(
            Checkout.user_id == patron_id,
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
        .order_by(Checkout.due_date)
    )
    checkouts = [
        CheckoutResponse(
            id=c.id,
            user_id=c.user_id,
            item_id=c.item_id,
            status=c.status,
            checked_out_at=c.checked_out_at,
            due_date=c.due_date,
            returned_at=c.returned_at,
            renewal_count=c.renewal_count,
            item_title=item.title,
            item_author=item.author,
        )
        for c, item in checkouts_result.all()
    ]

    holds_result = await db.execute(
        select(Hold, CatalogItem)
        .join(CatalogItem, Hold.item_id == CatalogItem.id)
        .where(
            Hold.user_id == patron_id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
        .order_by(Hold.created_at)
    )
    holds = [
        HoldResponse(
            id=h.id,
            user_id=h.user_id,
            item_id=h.item_id,
            status=h.status,
            position=h.position,
            created_at=h.created_at,
            notified_at=h.notified_at,
            expires_at=h.expires_at,
            item_title=item.title,
            item_author=item.author,
        )
        for h, item in holds_result.all()
    ]

    fines_result = await db.execute(
        select(Fine)
        .where(
            Fine.user_id == patron_id,
            Fine.status.in_([FineStatus.unpaid, FineStatus.partial]),
        )
        .order_by(Fine.created_at.desc())
    )
    fines_list = fines_result.scalars().all()
    fines = [
        FineResponse(
            id=f.id,
            user_id=f.user_id,
            checkout_id=f.checkout_id,
            fine_type=f.fine_type,
            status=f.status,
            amount=f.amount,
            amount_paid=f.amount_paid,
            balance=f.amount - f.amount_paid,
            description=f.description,
            notes=f.notes,
            created_at=f.created_at,
            paid_at=f.paid_at,
            waived_at=f.waived_at,
            waived_by_id=f.waived_by_id,
        )
        for f in fines_list
    ]

    total_owed = sum(f.balance for f in fines)
    return checkouts, holds, fines, total_owed
