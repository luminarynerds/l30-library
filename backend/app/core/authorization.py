# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from app.core.logging import get_logger
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Callable, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.cache_strategies import CacheTTL
from ..core.database import get_db
from ..models.permission import Permission, RolePermission, RoleSettings
from ..models.user import User, UserRole

# Note: get_current_user is imported locally in functions that use it
# to avoid circular imports (authorization is imported by api.v1.auth)

logger = get_logger(__name__)


def _get_current_user():
    from ..api.v1.auth import get_current_user
    return get_current_user

# =============================================================================
# Permission Caching with TTL and Stampede Protection
# =============================================================================

# Cache TTL in seconds (5 minutes)
PERMISSION_CACHE_TTL = CacheTTL.MEDIUM

# Cache data structure: {role: (permissions_set, timestamp)}
_permissions_cache: dict[UserRole, tuple[set[str], datetime]] = {}
_role_settings_cache: dict[UserRole, tuple[RoleSettings, datetime]] = {}

# Locks for stampede protection
_permissions_cache_lock = asyncio.Lock()
_role_settings_cache_lock = asyncio.Lock()

# Cache metrics
_permission_cache_hits = 0
_permission_cache_misses = 0


def _is_cache_valid(cached_time: Optional[datetime]) -> bool:
    if cached_time is None:
        return False
    age = (datetime.now(timezone.utc) - cached_time).total_seconds()
    return age < PERMISSION_CACHE_TTL


def get_permission_cache_metrics() -> dict:
    total = _permission_cache_hits + _permission_cache_misses
    hit_rate = (_permission_cache_hits / total * 100) if total > 0 else 0.0
    return {
        "cache_hits": _permission_cache_hits,
        "cache_misses": _permission_cache_misses,
        "total_requests": total,
        "hit_rate_percent": round(hit_rate, 2),
        "ttl_seconds": PERMISSION_CACHE_TTL
    }


def reset_permission_cache_metrics() -> None:
    global _permission_cache_hits, _permission_cache_misses
    _permission_cache_hits = 0
    _permission_cache_misses = 0
    logger.info("Permission cache metrics reset")


def clear_permissions_cache() -> None:
    _permissions_cache.clear()
    _role_settings_cache.clear()
    logger.info("Permissions and role settings cache cleared")


async def load_permissions_cache(db: AsyncSession) -> None:
    _permissions_cache.clear()
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(RolePermission, Permission).join(
            Permission, RolePermission.permission_id == Permission.id
        )
    )

    # Build permissions dict first, then add timestamp
    temp_permissions: dict[UserRole, set[str]] = {}
    for rp, perm in result.all():
        if rp.role not in temp_permissions:
            temp_permissions[rp.role] = set()
        temp_permissions[rp.role].add(perm.code)

    # Store with timestamp
    for role, perms in temp_permissions.items():
        _permissions_cache[role] = (perms, now)

    logger.debug("Loaded permissions cache for %s roles", len(temp_permissions))


async def load_role_settings_cache(db: AsyncSession) -> None:
    _role_settings_cache.clear()
    now = datetime.now(timezone.utc)

    result = await db.execute(select(RoleSettings))
    for settings in result.scalars().all():
        # Expunge from session so the cached object doesn't trigger
        # DetachedInstanceError when accessed in a different request/session
        db.expunge(settings)
        _role_settings_cache[settings.role] = (settings, now)

    logger.debug("Loaded role settings cache for %s roles", len(_role_settings_cache))


# =============================================================================
# Permission Checking
# =============================================================================


async def get_user_permissions(user: User, db: AsyncSession) -> set[str]:
    global _permission_cache_hits, _permission_cache_misses

    # Check if we have cached data and if it's still valid
    if user.role in _permissions_cache:
        perms, cached_time = _permissions_cache[user.role]
        if _is_cache_valid(cached_time):
            _permission_cache_hits += 1
            logger.debug("Permission cache HIT for role %s", user.role)
            return perms

    # Cache miss or expired - acquire lock to prevent stampede
    async with _permissions_cache_lock:
        # Double-check cache after acquiring lock (another request may have populated it)
        if user.role in _permissions_cache:
            perms, cached_time = _permissions_cache[user.role]
            if _is_cache_valid(cached_time):
                _permission_cache_hits += 1
                logger.debug("Permission cache HIT (after lock) for role %s", user.role)
                return perms

        # Cache miss or expired - reload cache
        _permission_cache_misses += 1
        logger.debug("Permission cache MISS for role %s", user.role)
        await load_permissions_cache(db)

    # Return permissions (may be empty set if role has no permissions)
    if user.role in _permissions_cache:
        perms, _ = _permissions_cache[user.role]
        return perms
    return set()


async def has_permission(user: User, permission_code: str, db: AsyncSession) -> bool:
    permissions = await get_user_permissions(user, db)
    return permission_code in permissions


def require_permission(permission_code: str) -> Callable:

    async def permission_dependency(
        current_user: User = Depends(_get_current_user()),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if not await has_permission(current_user, permission_code, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission_code}",
            )
        return current_user

    return permission_dependency


def require_any_permission(*permission_codes: str) -> Callable:

    async def permission_dependency(
        current_user: User = Depends(_get_current_user()),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        user_perms = await get_user_permissions(current_user, db)
        if not any(p in user_perms for p in permission_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these permissions required: {', '.join(permission_codes)}",
            )
        return current_user

    return permission_dependency


def require_all_permissions(*permission_codes: str) -> Callable:

    async def permission_dependency(
        current_user: User = Depends(_get_current_user()),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        user_perms = await get_user_permissions(current_user, db)
        missing = [p for p in permission_codes if p not in user_perms]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissions required: {', '.join(missing)}",
            )
        return current_user

    return permission_dependency


def require_role(*required_roles: UserRole) -> Callable:
    async def role_dependency(
        current_user: User = Depends(_get_current_user()),
    ) -> User:
        if current_user.role not in required_roles:
            roles_str = ", ".join(r.value for r in required_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This operation requires one of these roles: {roles_str}",
            )
        return current_user

    return role_dependency


# =============================================================================
# Role Settings
# =============================================================================


async def get_role_settings(role: UserRole, db: AsyncSession) -> RoleSettings | None:
    # Check if we have cached data and if it's still valid
    if role in _role_settings_cache:
        settings, cached_time = _role_settings_cache[role]
        if _is_cache_valid(cached_time):
            logger.debug("Role settings cache HIT for role %s", role)
            return settings

    # Cache miss or expired - acquire lock to prevent stampede
    async with _role_settings_cache_lock:
        # Double-check cache after acquiring lock (another request may have populated it)
        if role in _role_settings_cache:
            settings, cached_time = _role_settings_cache[role]
            if _is_cache_valid(cached_time):
                logger.debug("Role settings cache HIT (after lock) for role %s", role)
                return settings

        # Cache miss or expired - reload cache
        logger.debug("Role settings cache MISS for role %s", role)
        await load_role_settings_cache(db)

    # Return settings (may be None if role has no settings)
    if role in _role_settings_cache:
        settings, _ = _role_settings_cache[role]
        return settings
    return None


async def get_user_role_settings(user: User, db: AsyncSession) -> RoleSettings | None:
    return await get_role_settings(user.role, db)


# =============================================================================
# Convenience Functions
# =============================================================================


async def can_checkout(user: User, db: AsyncSession) -> bool:
    return await has_permission(user, "checkout", db)


async def can_access_adult_content(user: User, db: AsyncSession) -> bool:
    settings = await get_user_role_settings(user, db)
    if settings:
        return settings.can_access_adult_content
    return await has_permission(user, "access_adult_content", db)


async def is_fine_exempt(user: User, db: AsyncSession) -> bool:
    settings = await get_user_role_settings(user, db)
    return settings.fine_exempt if settings else False


async def get_unpaid_fine_balance(user: User, db: AsyncSession) -> Decimal:
    from ..models.fine import Fine, FineStatus
    result = await db.execute(
        select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), Decimal("0.00")))
        .where(
            Fine.user_id == user.id,
            Fine.status.in_([FineStatus.unpaid, FineStatus.partial])
        )
    )
    return result.scalar() or Decimal("0.00")


async def check_fine_block(user: User, db: AsyncSession) -> tuple[bool, Decimal]:
    from ..services.fine_service import FINE_FREE_MODE, check_overdue_block

    if await is_fine_exempt(user, db):
        return True, Decimal("0.00")

    if FINE_FREE_MODE:
        # In fine-free mode, check for long-overdue items instead of fines
        can_checkout, overdue_count = await check_overdue_block(user.id, db)
        if not can_checkout:
            # Return the overdue count as a pseudo-balance for error messaging
            # The actual block reason is overdue items, not money
            return False, Decimal(str(overdue_count))

        # Still check for lost/damaged item costs (these are replacement fees, not fines)
        from ..models.fine import Fine, FineStatus, FineType
        result = await db.execute(
            select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), Decimal("0.00")))
            .where(
                Fine.user_id == user.id,
                Fine.status.in_([FineStatus.unpaid, FineStatus.partial]),
                Fine.fine_type.in_([FineType.lost_item, FineType.damaged_item]),
            )
        )
        replacement_balance = result.scalar() or Decimal("0.00")

        # Only block if there are unpaid replacement costs
        settings = await get_user_role_settings(user, db)
        max_fine = Decimal(str(settings.max_fine_amount)) / 100 if settings else Decimal("25.00")
        return replacement_balance < max_fine, replacement_balance

    # Legacy mode: check all fines
    settings = await get_user_role_settings(user, db)
    max_fine = Decimal(str(settings.max_fine_amount)) / 100 if settings else Decimal("25.00")

    balance = await get_unpaid_fine_balance(user, db)
    return balance < max_fine, balance


async def get_checkout_limit(user: User, db: AsyncSession) -> int:
    from ..services.age_group_service import get_age_group_checkout_limit
    from ..services.organization_features_service import OrganizationFeaturesService

    features = await OrganizationFeaturesService.get_or_create_features(db)
    age_limit = get_age_group_checkout_limit(user, features)
    if age_limit is not None:
        return age_limit

    settings = await get_user_role_settings(user, db)
    return settings.max_checkouts if settings else 10


async def get_checkout_duration(user: User, db: AsyncSession) -> int:
    from ..services.age_group_service import get_age_group_checkout_duration
    from ..services.organization_features_service import OrganizationFeaturesService

    features = await OrganizationFeaturesService.get_or_create_features(db)
    age_duration = get_age_group_checkout_duration(user, features)
    if age_duration is not None:
        return age_duration

    settings = await get_user_role_settings(user, db)
    return settings.checkout_duration_days if settings else 21


async def get_hold_limit(user: User, db: AsyncSession) -> int:
    from ..services.age_group_service import get_age_group_hold_limit
    from ..services.organization_features_service import OrganizationFeaturesService

    features = await OrganizationFeaturesService.get_or_create_features(db)
    age_limit = get_age_group_hold_limit(user, features)
    if age_limit is not None:
        return age_limit

    settings = await get_user_role_settings(user, db)
    return settings.max_holds if settings else 5


async def get_max_renewals(user: User, db: AsyncSession) -> int:
    settings = await get_user_role_settings(user, db)
    return settings.max_renewals if settings else 2


# =============================================================================
# Card Expiration Checking
# =============================================================================

# Default grace period in days (allows checkout even after card expiration)
DEFAULT_CARD_EXPIRATION_GRACE_PERIOD_DAYS = 7


async def get_card_expiry_years(user: User, db: AsyncSession) -> int:
    if user.home_library_system_id:
        from ..models.multi_branch import SystemSettings
        result = await db.execute(
            select(SystemSettings).where(
                SystemSettings.library_system_id == user.home_library_system_id
            )
        )
        system_settings = result.scalar_one_or_none()
        if system_settings and system_settings.card_expiry_years:
            return system_settings.card_expiry_years
    return 3  # Default from multi_branch.py


async def get_card_grace_period_days(user: User, db: AsyncSession) -> int:
    if user.home_library_system_id:
        from ..models.multi_branch import SystemSettings
        result = await db.execute(
            select(SystemSettings).where(
                SystemSettings.library_system_id == user.home_library_system_id
            )
        )
        system_settings = result.scalar_one_or_none()
        if system_settings and system_settings.grace_period_days:
            return system_settings.grace_period_days
    return DEFAULT_CARD_EXPIRATION_GRACE_PERIOD_DAYS


async def check_card_expiration(
    user: User,
    db: AsyncSession,
    allow_grace_period: bool = True,
) -> tuple[bool, int | None]:
    # Check if user has a card expiration date
    if user.card_expires_at is None:
        return True, None

    grace_period_days = 0
    if allow_grace_period:
        grace_period_days = await get_card_grace_period_days(user, db)

    is_expired = user.is_card_expired(grace_period_days=grace_period_days)
    days_until_expires = user.days_until_card_expires()

    if is_expired:
        # Card is expired past grace period
        return False, days_until_expires

    # Card is valid (or within grace period)
    return True, days_until_expires


async def check_consortium_patron_expiration(
    user: User,
    linked_member_id: int,
    db: AsyncSession,
) -> tuple[bool, int | None]:
    from ..models.multi_branch import ConsortiumPatronLink

    result = await db.execute(
        select(ConsortiumPatronLink).where(
            ConsortiumPatronLink.home_user_id == user.id,
            ConsortiumPatronLink.linked_member_id == linked_member_id,
            ConsortiumPatronLink.is_active == True,
        )
    )
    link = result.scalar_one_or_none()

    if not link:
        return False, None

    if link.blocked:
        return False, None

    if link.expires_at is None:
        return True, None

    now = datetime.now(timezone.utc)
    days_remaining = (link.expires_at - now).days

    if link.expires_at < now:
        return False, days_remaining

    return True, days_remaining


def calculate_card_expiration_date(
    from_date: datetime | None = None,
    expiry_years: int = 3,
) -> datetime:
    if from_date is None:
        from_date = datetime.now(timezone.utc)

    return from_date + timedelta(days=expiry_years * 365)
