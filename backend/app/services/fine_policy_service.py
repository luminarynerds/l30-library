# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.fine import Fine, FinePolicy, FinePolicyType, FineType, FineStatus
from ..models.circulation import Checkout
from ..models.user import User, UserRole
from ..models.catalog import CatalogItem

logger = get_logger(__name__)


class TieredRate:

    def __init__(self, min_days: int, max_days: int, rate: Decimal):
        self.min_days = min_days
        self.max_days = max_days
        self.rate = Decimal(str(rate))

    def applies_to_days(self, days: int) -> bool:
        return self.min_days <= days <= self.max_days


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def get_active_fine_policies(
    db: AsyncSession,
    item_type: Optional[str] = None,
    user_role: Optional[UserRole] = None,
) -> List[FinePolicy]:
    stmt = select(FinePolicy).where(FinePolicy.is_active == True)

    if item_type:
        # Match if applies to 'all' or the specific item type is in the comma-separated list
        # This will be filtered in Python since SQLAlchemy doesn't have great LIKE support
        pass

    if user_role:
        # Similar to item type, will filter in Python
        pass

    result = await db.execute(stmt)
    policies = result.scalars().all()

    # Filter in Python for item type and user role
    filtered_policies = []
    for policy in policies:
        if item_type:
            if policy.applies_to_item_types != "all":
                item_types = [t.strip() for t in policy.applies_to_item_types.split(",")]
                if item_type not in item_types:
                    continue

        if user_role:
            if policy.applies_to_user_roles != "all":
                roles = [r.strip() for r in policy.applies_to_user_roles.split(",")]
                if user_role.value not in roles:
                    continue

        filtered_policies.append(policy)

    return filtered_policies


async def find_applicable_policy(
    db: AsyncSession,
    checkout: Checkout,
    user: User,
    item: CatalogItem,
    *,
    cached_policies: list | None = None,
) -> Optional[FinePolicy]:
    item_type = item.item_type.value if hasattr(item.item_type, 'value') else str(item.item_type)

    # Use cached policies if provided (batch optimization), otherwise fetch from DB
    if cached_policies is not None:
        all_policies = cached_policies
    else:
        stmt = select(FinePolicy).where(FinePolicy.is_active == True)
        result = await db.execute(stmt)
        all_policies = result.scalars().all()

    if not all_policies:
        return None

    best_match = None
    best_score = -1

    for policy in all_policies:
        score = 0

        # Check item type match
        item_type_match = False
        if policy.applies_to_item_types == "all":
            item_type_match = True
        else:
            item_types = [t.strip() for t in policy.applies_to_item_types.split(",")]
            item_type_match = item_type in item_types

        # Check user role match
        role_match = False
        if policy.applies_to_user_roles == "all":
            role_match = True
        else:
            roles = [r.strip() for r in policy.applies_to_user_roles.split(",")]
            user_role_str = user.role.value if hasattr(user.role, 'value') else str(user.role)
            role_match = user_role_str in roles

        # Calculate score (higher = more specific match)
        # Specific matches beat generic 'all' matches
        if not item_type_match or not role_match:
            continue

        item_specific = policy.applies_to_item_types != "all"
        role_specific = policy.applies_to_user_roles != "all"

        if item_specific and role_specific:
            score = 4  # Most specific: explicit item + explicit role
        elif item_specific:
            score = 3  # Specific item type, any role
        elif role_specific:
            score = 3  # Any item, specific role
        else:
            score = 1  # Generic fallback (all/all)

        if score > best_score:
            best_score = score
            best_match = policy

    return best_match


def parse_tiered_configuration(config_json: str) -> List[TieredRate]:
    try:
        config = json.loads(config_json)
        if not isinstance(config, list):
            raise ValueError("Tiered configuration must be a JSON array")

        tiers = []
        for tier_data in config:
            if not all(k in tier_data for k in ["min_days", "max_days", "rate"]):
                raise ValueError(
                    "Each tier must have min_days, max_days, and rate fields"
                )
            tiers.append(
                TieredRate(
                    min_days=int(tier_data["min_days"]),
                    max_days=int(tier_data["max_days"]),
                    rate=Decimal(str(tier_data["rate"])),
                )
            )

        return sorted(tiers, key=lambda t: t.min_days)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in tiered configuration: {e}") from e


def calculate_fine_amount(
    policy: FinePolicy,
    days_overdue: int,
) -> Decimal:
    if days_overdue <= 0:
        return Decimal("0.00")

    amount = Decimal("0.00")

    if policy.policy_type == FinePolicyType.daily_rate:
        # Simple: days * rate
        amount = Decimal(str(days_overdue)) * policy.fine_per_day

    elif policy.policy_type == FinePolicyType.progressive:
        # Progressive: rate increases each day by percentage
        # Day 1: base_rate
        # Day 2: base_rate * (1 + percentage/100)
        # Day 3: base_rate * (1 + percentage/100)^2, etc.
        base_rate = policy.fine_per_day
        increase_factor = Decimal("1.00") + (policy.progressive_increase_percent / Decimal("100"))

        for day in range(1, days_overdue + 1):
            daily_fine = base_rate * (increase_factor ** (day - 1))
            amount += daily_fine

    elif policy.policy_type == FinePolicyType.tiered:
        # Tiered: cumulative calculation across tiers
        if policy.tiered_configuration:
            try:
                tiers = parse_tiered_configuration(policy.tiered_configuration)

                for tier in tiers:
                    if days_overdue <= tier.min_days:
                        continue
                    tier_end = min(days_overdue, tier.max_days) if tier.max_days else days_overdue
                    tier_days = tier_end - tier.min_days
                    if tier_days > 0:
                        amount += Decimal(str(tier_days)) * tier.rate

            except ValueError as e:
                logger.error(
                    "Error parsing tiered configuration for policy %s: %s", policy.id, e
                )
                # Fall back to simple daily rate
                amount = Decimal(str(days_overdue)) * policy.fine_per_day

    elif policy.policy_type == FinePolicyType.maximum_cap:
        # Maximum cap: charge the cap or daily_rate * days, whichever is lower
        daily_amount = Decimal(str(days_overdue)) * policy.fine_per_day
        # NOTE: `is not None`, not truthiness -- a 0.00 cap means "cap fines
        # at $0", while NULL is the no-cap representation (models/fine.py:271)
        if policy.maximum_cap is not None:
            amount = min(daily_amount, policy.maximum_cap)
        else:
            amount = daily_amount

    # Apply boundaries
    amount = max(amount, policy.minimum_fine_amount)

    if policy.maximum_daily_fine:
        # Apply per-day cap: can't exceed max_daily_fine * days
        max_possible = Decimal(str(days_overdue)) * policy.maximum_daily_fine
        amount = min(amount, max_possible)

    # Apply global maximum cap if set (`is not None`: 0.00 is a real $0 cap)
    if policy.maximum_cap is not None:
        amount = min(amount, policy.maximum_cap)

    return amount


async def calculate_overdue_days(
    checkout: Checkout,
    policy: Optional[FinePolicy] = None,
    now: Optional[datetime] = None,
) -> int:
    if now is None:
        now = datetime.now(timezone.utc)

    due_date = ensure_utc(checkout.due_date)

    if due_date >= now:
        return 0

    # Calculate time overdue
    overdue_delta = now - due_date
    overdue_hours = overdue_delta.total_seconds() / 3600

    # Apply grace period if specified in policy
    grace_hours = 0
    if policy:
        grace_hours = policy.grace_period_hours

    # Subtract grace period
    overdue_hours = max(0, overdue_hours - grace_hours)

    if overdue_hours <= 0:
        return 0

    # Round up: any part of a day counts as a full day
    # e.g., 0.5 hours = 1 day, 24.1 hours = 2 days
    import math
    days_overdue = math.ceil(overdue_hours / 24)

    return max(1, days_overdue)


async def apply_fine_policy(
    checkout: Checkout,
    user: User,
    item: Optional[CatalogItem],
    db: AsyncSession,
    force_update: bool = False,
) -> tuple[Optional[Fine], bool]:
    from ..models.circulation import CheckoutStatus
    from ..models.permission import RoleSettings

    # Skip if already returned or lost
    if checkout.status not in [CheckoutStatus.active, CheckoutStatus.overdue]:
        return None, False

    # Find applicable policy
    policy = await find_applicable_policy(db, checkout, user, item or CatalogItem())

    if not policy:
        logger.warning(
            f"No fine policy found for checkout {checkout.id}, "
            f"user {user.id}, item {item.id if item else 'unknown'}"
        )
        return None, False

    # Calculate days overdue
    days_overdue = await calculate_overdue_days(checkout, policy)

    if days_overdue <= 0 and not force_update:
        return None, False

    now = datetime.now(timezone.utc)

    # Check if user is fine-exempt or uses reading minutes
    settings_result = await db.execute(
        select(RoleSettings).where(RoleSettings.role == user.role)
    )
    settings = settings_result.scalar_one_or_none()

    # Handle reading minutes (for children)
    if settings and settings.use_reading_minutes:
        already_processed = checkout.last_overdue_days_processed or 0
        new_days = days_overdue - already_processed

        if new_days > 0:
            from sqlalchemy import func, update

            minutes_to_add = new_days * settings.minutes_per_day_overdue
            await db.execute(
                update(User)
                .where(User.id == user.id)
                .values(
                    reading_minutes_owed=func.least(
                        User.reading_minutes_owed + minutes_to_add,
                        settings.max_reading_minutes_owed,
                    )
                )
            )
            checkout.last_overdue_days_processed = days_overdue
            checkout.status = CheckoutStatus.overdue

        return None, False

    # Skip if fine-exempt
    if settings and settings.fine_exempt:
        checkout.status = CheckoutStatus.overdue
        return None, False

    # Calculate fine amount
    fine_amount = calculate_fine_amount(policy, days_overdue)

    if fine_amount <= Decimal("0.00") and not force_update:
        return None, False

    # Update checkout status
    checkout.status = CheckoutStatus.overdue

    # Check if fine already exists
    existing_fine_result = await db.execute(
        select(Fine).where(
            and_(Fine.checkout_id == checkout.id, Fine.fine_type == FineType.overdue)
        )
    )
    existing_fine = existing_fine_result.scalar_one_or_none()

    if existing_fine:
        # Update existing fine if amount has increased
        if fine_amount > existing_fine.amount and existing_fine.status in [
            FineStatus.unpaid,
            FineStatus.partial,
        ]:
            existing_fine.amount = fine_amount
            existing_fine.description = (
                f"Overdue fine: {days_overdue} days at policy '{policy.name}'"
            )
            if existing_fine.amount_paid > Decimal("0.00"):
                existing_fine.status = FineStatus.partial
            existing_fine.updated_at = now

        return existing_fine, True

    # Create new fine
    new_fine = Fine(
        user_id=checkout.user_id,
        checkout_id=checkout.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=fine_amount,
        amount_paid=Decimal("0.00"),
        description=f"Overdue fine: {days_overdue} days at policy '{policy.name}'",
    )
    db.add(new_fine)

    # Flush so new_fine.id is populated, then stage the in-app feed row
    # transactionally with the fine creation.
    await db.flush()
    from .fine_service import record_fine_assessed_in_app

    await record_fine_assessed_in_app(new_fine, checkout, db)

    return new_fine, True


async def create_or_update_fine_policy(
    db: AsyncSession,
    name: str,
    policy_type: FinePolicyType,
    fine_per_day: Decimal = Decimal("0.25"),
    applies_to_item_types: str = "all",
    applies_to_user_roles: str = "all",
    maximum_cap: Optional[Decimal] = None,
    grace_period_hours: int = 0,
    minimum_fine_amount: Decimal = Decimal("0.00"),
    maximum_daily_fine: Decimal = Decimal("50.00"),
    progressive_increase_percent: Decimal = Decimal("0.00"),
    tiered_configuration: Optional[str] = None,
    is_active: bool = True,
    description: Optional[str] = None,
    created_by_id: Optional[int] = None,
) -> FinePolicy:
    # Check if policy already exists
    stmt = select(FinePolicy).where(FinePolicy.name == name)
    result = await db.execute(stmt)
    existing_policy = result.scalar_one_or_none()

    if existing_policy:
        # Update existing
        existing_policy.policy_type = policy_type
        existing_policy.fine_per_day = fine_per_day
        existing_policy.applies_to_item_types = applies_to_item_types
        existing_policy.applies_to_user_roles = applies_to_user_roles
        existing_policy.maximum_cap = maximum_cap
        existing_policy.grace_period_hours = grace_period_hours
        existing_policy.minimum_fine_amount = minimum_fine_amount
        existing_policy.maximum_daily_fine = maximum_daily_fine
        existing_policy.progressive_increase_percent = progressive_increase_percent
        existing_policy.tiered_configuration = tiered_configuration
        existing_policy.is_active = is_active
        if description:
            existing_policy.description = description
        existing_policy.updated_at = datetime.now(timezone.utc)

        logger.info(f"Updated fine policy: {name}")
        return existing_policy

    # Create new
    new_policy = FinePolicy(
        name=name,
        policy_type=policy_type,
        fine_per_day=fine_per_day,
        applies_to_item_types=applies_to_item_types,
        applies_to_user_roles=applies_to_user_roles,
        maximum_cap=maximum_cap,
        grace_period_hours=grace_period_hours,
        minimum_fine_amount=minimum_fine_amount,
        maximum_daily_fine=maximum_daily_fine,
        progressive_increase_percent=progressive_increase_percent,
        tiered_configuration=tiered_configuration,
        is_active=is_active,
        description=description,
        created_by_id=created_by_id,
    )
    db.add(new_policy)

    logger.info(f"Created new fine policy: {name}")
    return new_policy


async def get_user_overdue_checkouts(
    db: AsyncSession,
    user_id: int,
    policy: Optional[FinePolicy] = None,
) -> List[tuple[Checkout, int]]:
    from ..models.circulation import CheckoutStatus

    stmt = (
        select(Checkout)
        .where(
            and_(
                Checkout.user_id == user_id,
                Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
                Checkout.returned_at.is_(None),
            )
        )
    )
    result = await db.execute(stmt)
    checkouts = result.scalars().all()

    overdue = []
    for checkout in checkouts:
        days = await calculate_overdue_days(checkout, policy)
        if days > 0:
            overdue.append((checkout, days))

    return overdue
