# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Database Subscription Management API Endpoints.

Provides endpoints for:
- Database subscription CRUD (admin)
- Proxy configuration management
- Vendor management
- Public A-Z database list (patrons)
- Usage statistics
- Access logging
"""

import ipaddress
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.encryption import encrypt_token
from ...core.shortcuts import get_or_404
from ...models.database_subscription import (
    DatabaseAccessLog,
    DatabaseRenewalNotification,
    DatabaseSubscription,
    DatabaseUsageStats,
    DatabaseVendor,
    ProxyConfiguration,
    SUSHICredential,
    SubscriptionStatus,
)
from ...models.user import User, UserRole
from ...schemas.database_subscription import (
    DatabaseAccessLogCreate,
    DatabaseAccessLogResponse,
    DatabaseAZListResponse,
    DatabaseSubscriptionCreate,
    DatabaseSubscriptionPublic,
    DatabaseSubscriptionResponse,
    DatabaseSubscriptionUpdate,
    DatabaseSubscriptionWithVendor,
    DatabaseUsageStatsBase,
    DatabaseUsageStatsResponse,
    DatabaseUsageStatsUpdate,
    DatabaseUsageSummary,
    UsageReportPreview,
    UsageReportRow,
    DatabaseVendorCreate,
    DatabaseVendorResponse,
    DatabaseVendorUpdate,
    ProxyConfigurationCreate,
    ProxyConfigurationResponse,
    ProxyConfigurationUpdate,
    ProxyUrlRequest,
    ProxyUrlResponse,
    RenewalNotificationResponse,
    SUSHICredentialCreate,
    SUSHICredentialResponse,
    SUSHICredentialUpdate,
    SubscriptionDashboard,
    SubscriptionExpirationAlert,
)
from .auth import get_current_user, get_current_user_optional
from .dependencies import require_staff

router = APIRouter(prefix="/databases", tags=["databases"])


def update_subscription_status(subscription: DatabaseSubscription) -> None:
    today = date.today()

    if subscription.subscription_end < today:
        subscription.status = SubscriptionStatus.EXPIRED.value
    elif subscription.is_expiring_soon:
        subscription.status = SubscriptionStatus.EXPIRING_SOON.value
    elif subscription.trial_end and subscription.trial_end >= today:
        subscription.status = SubscriptionStatus.TRIAL.value
    elif subscription.subscription_start > today:
        subscription.status = SubscriptionStatus.PENDING.value
    else:
        subscription.status = SubscriptionStatus.ACTIVE.value


async def _increment_turnaway_stats(db: AsyncSession, subscription_id: int) -> None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(DatabaseUsageStats).where(
            DatabaseUsageStats.subscription_id == subscription_id,
            DatabaseUsageStats.stat_year == now.year,
            DatabaseUsageStats.stat_month == now.month,
        )
    )
    stats = result.scalar_one_or_none()
    if stats:
        stats.no_license = (stats.no_license or 0) + 1
    else:
        stats = DatabaseUsageStats(
            subscription_id=subscription_id,
            stat_year=now.year,
            stat_month=now.month,
            no_license=1,
            data_source="l30_enforcement",
        )
        db.add(stats)


# ============ PROXY CONFIGURATION ============


@router.get("/proxy-configs", response_model=List[ProxyConfigurationResponse])
async def list_proxy_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all proxy configurations (staff only)."""
    await require_staff(current_user)

    result = await db.execute(select(ProxyConfiguration).order_by(ProxyConfiguration.name))
    return result.scalars().all()


@router.post(
    "/proxy-configs", response_model=ProxyConfigurationResponse, status_code=status.HTTP_201_CREATED
)
async def create_proxy_config(
    config_in: ProxyConfigurationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new proxy configuration (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create proxy configs"
        )

    # If setting as default, unset other defaults
    if config_in.is_default:
        await db.execute(select(ProxyConfiguration).where(ProxyConfiguration.is_default == True))
        existing_defaults = (
            (
                await db.execute(
                    select(ProxyConfiguration).where(ProxyConfiguration.is_default == True)
                )
            )
            .scalars()
            .all()
        )
        for existing in existing_defaults:
            existing.is_default = False

    config = ProxyConfiguration(**config_in.model_dump(), created_by_id=current_user.id)
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.put("/proxy-configs/{config_id}", response_model=ProxyConfigurationResponse)
async def update_proxy_config(
    config_id: int,
    config_update: ProxyConfigurationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a proxy configuration (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can update proxy configs"
        )

    config = await get_or_404(db, ProxyConfiguration, config_id, "Proxy configuration not found")

    update_data = config_update.model_dump(exclude_unset=True)

    # Handle default flag
    if update_data.get("is_default"):
        existing_defaults = (
            (
                await db.execute(
                    select(ProxyConfiguration).where(
                        ProxyConfiguration.is_default == True, ProxyConfiguration.id != config_id
                    )
                )
            )
            .scalars()
            .all()
        )
        for existing in existing_defaults:
            existing.is_default = False

    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)
    return config


@router.delete("/proxy-configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_proxy_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a proxy configuration (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete proxy configs"
        )

    config = await get_or_404(db, ProxyConfiguration, config_id, "Proxy configuration not found")

    # Check if any subscriptions use this config
    subs_using = await db.execute(
        select(func.count(DatabaseSubscription.id)).where(
            DatabaseSubscription.proxy_config_id == config_id
        )
    )
    if subs_using.scalar() > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete proxy configuration that is in use by subscriptions",
        )

    await db.delete(config)
    await db.commit()


# ============ DATABASE VENDORS ============


@router.get("/vendors", response_model=List[DatabaseVendorResponse])
async def list_vendors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all database vendors (staff only)."""
    await require_staff(current_user)

    result = await db.execute(select(DatabaseVendor).order_by(DatabaseVendor.name))
    return result.scalars().all()


@router.post("/vendors", response_model=DatabaseVendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    vendor_in: DatabaseVendorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new database vendor (staff only)."""
    await require_staff(current_user)

    # Check for duplicate name
    existing = await db.execute(select(DatabaseVendor).where(DatabaseVendor.name == vendor_in.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Vendor with this name already exists"
        )

    vendor = DatabaseVendor(**vendor_in.model_dump())
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)
    return vendor


@router.put("/vendors/{vendor_id}", response_model=DatabaseVendorResponse)
async def update_vendor(
    vendor_id: int,
    vendor_update: DatabaseVendorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a database vendor (staff only)."""
    await require_staff(current_user)

    vendor = await get_or_404(db, DatabaseVendor, vendor_id, "Vendor not found")

    update_data = vendor_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vendor, field, value)

    await db.commit()
    await db.refresh(vendor)
    return vendor


@router.delete("/vendors/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a database vendor (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete vendors"
        )

    vendor = await get_or_404(db, DatabaseVendor, vendor_id, "Vendor not found")

    await db.delete(vendor)
    await db.commit()


# ============ SUSHI CREDENTIALS ============


def _sushi_credential_to_response(cred: SUSHICredential) -> SUSHICredentialResponse:
    return SUSHICredentialResponse(
        id=cred.id,
        vendor_id=cred.vendor_id,
        label=cred.label,
        base_url=cred.base_url,
        customer_id=cred.customer_id,
        requestor_id=cred.requestor_id,
        platform=cred.platform,
        has_api_key=bool(cred.api_key),
        is_active=cred.is_active,
        last_harvest_at=cred.last_harvest_at,
        last_harvest_status=cred.last_harvest_status,
        last_harvest_error=cred.last_harvest_error,
        notes=cred.notes,
        created_at=cred.created_at,
        updated_at=cred.updated_at,
    )


@router.get("/sushi-credentials", response_model=List[SUSHICredentialResponse])
async def list_sushi_credentials(
    vendor_id: Optional[int] = Query(None, gt=0),
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List SUSHI credentials (staff only). Filter by vendor or active state."""
    await require_staff(current_user)

    query = select(SUSHICredential)
    if vendor_id is not None:
        query = query.where(SUSHICredential.vendor_id == vendor_id)
    if not include_inactive:
        query = query.where(SUSHICredential.is_active.is_(True))
    query = query.order_by(SUSHICredential.vendor_id, SUSHICredential.label)

    result = await db.execute(query)
    return [_sushi_credential_to_response(c) for c in result.scalars().all()]


@router.post(
    "/sushi-credentials",
    response_model=SUSHICredentialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sushi_credential(
    cred_in: SUSHICredentialCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a SUSHI credential for a vendor (staff only)."""
    await require_staff(current_user)

    await get_or_404(db, DatabaseVendor, cred_in.vendor_id, "Vendor not found")

    existing = await db.execute(
        select(SUSHICredential).where(
            SUSHICredential.vendor_id == cred_in.vendor_id,
            SUSHICredential.label == cred_in.label,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A SUSHI credential with this label already exists for the vendor",
        )

    data = cred_in.model_dump()
    plain_api_key = data.pop("api_key", None)
    cred = SUSHICredential(**data)
    if plain_api_key:
        cred.api_key = encrypt_token(plain_api_key)

    db.add(cred)
    await db.commit()
    await db.refresh(cred)
    return _sushi_credential_to_response(cred)


@router.put("/sushi-credentials/{cred_id}", response_model=SUSHICredentialResponse)
async def update_sushi_credential(
    cred_id: int,
    cred_update: SUSHICredentialUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a SUSHI credential (staff only). Send api_key only to rotate it."""
    await require_staff(current_user)

    cred = await get_or_404(db, SUSHICredential, cred_id, "SUSHI credential not found")

    update_data = cred_update.model_dump(exclude_unset=True)
    new_api_key = update_data.pop("api_key", None)
    new_label = update_data.get("label")
    if new_label and new_label != cred.label:
        dup = await db.execute(
            select(SUSHICredential).where(
                SUSHICredential.vendor_id == cred.vendor_id,
                SUSHICredential.label == new_label,
                SUSHICredential.id != cred_id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A SUSHI credential with this label already exists for the vendor",
            )

    for field, value in update_data.items():
        setattr(cred, field, value)
    if new_api_key is not None:
        cred.api_key = encrypt_token(new_api_key) if new_api_key else None

    await db.commit()
    await db.refresh(cred)
    return _sushi_credential_to_response(cred)


@router.delete("/sushi-credentials/{cred_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sushi_credential(
    cred_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a SUSHI credential (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete SUSHI credentials",
        )

    cred = await get_or_404(db, SUSHICredential, cred_id, "SUSHI credential not found")
    await db.delete(cred)
    await db.commit()


# ============ DATABASE SUBSCRIPTIONS ============


@router.get("/subscriptions", response_model=List[DatabaseSubscriptionWithVendor])
async def list_subscriptions(
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    vendor_id: Optional[int] = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all database subscriptions (staff only)."""
    await require_staff(current_user)

    query = select(DatabaseSubscription).options(selectinload(DatabaseSubscription.vendor))

    if not include_inactive:
        query = query.where(DatabaseSubscription.is_active == True)

    if status_filter:
        query = query.where(DatabaseSubscription.status == status_filter)

    if category:
        query = query.where(DatabaseSubscription.category == category)

    if vendor_id:
        query = query.where(DatabaseSubscription.vendor_id == vendor_id)

    query = query.order_by(DatabaseSubscription.name)
    result = await db.execute(query)
    subscriptions = result.scalars().all()

    # Update statuses before returning
    for sub in subscriptions:
        update_subscription_status(sub)

    await db.commit()
    return subscriptions


@router.get("/subscriptions/{subscription_id}", response_model=DatabaseSubscriptionWithVendor)
async def get_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific database subscription (staff only)."""
    await require_staff(current_user)

    result = await db.execute(
        select(DatabaseSubscription)
        .options(selectinload(DatabaseSubscription.vendor))
        .where(DatabaseSubscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    update_subscription_status(subscription)
    await db.commit()
    return subscription


@router.post(
    "/subscriptions",
    response_model=DatabaseSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(
    subscription_in: DatabaseSubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new database subscription (staff only)."""
    await require_staff(current_user)

    # Validate vendor exists
    if subscription_in.vendor_id:
        vendor_result = await db.execute(
            select(DatabaseVendor).where(DatabaseVendor.id == subscription_in.vendor_id)
        )
        if not vendor_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vendor not found")

    # Validate proxy config exists
    if subscription_in.proxy_config_id:
        config_result = await db.execute(
            select(ProxyConfiguration).where(
                ProxyConfiguration.id == subscription_in.proxy_config_id
            )
        )
        if not config_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Proxy configuration not found"
            )

    subscription = DatabaseSubscription(
        **subscription_in.model_dump(), created_by_id=current_user.id
    )
    update_subscription_status(subscription)

    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    return subscription


@router.put("/subscriptions/{subscription_id}", response_model=DatabaseSubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    subscription_update: DatabaseSubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a database subscription (staff only)."""
    await require_staff(current_user)

    subscription = await get_or_404(
        db, DatabaseSubscription, subscription_id, "Subscription not found"
    )

    update_data = subscription_update.model_dump(exclude_unset=True)

    # Validate vendor if changing
    if "vendor_id" in update_data and update_data["vendor_id"]:
        vendor_result = await db.execute(
            select(DatabaseVendor).where(DatabaseVendor.id == update_data["vendor_id"])
        )
        if not vendor_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vendor not found")

    for field, value in update_data.items():
        setattr(subscription, field, value)

    update_subscription_status(subscription)
    await db.commit()
    await db.refresh(subscription)
    return subscription


@router.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a database subscription (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete subscriptions"
        )

    subscription = await get_or_404(
        db, DatabaseSubscription, subscription_id, "Subscription not found"
    )

    await db.delete(subscription)
    await db.commit()


# ============ PUBLIC A-Z DATABASE LIST ============


@router.get("/public/list", response_model=DatabaseAZListResponse)
async def get_public_database_list(
    category: Optional[str] = None,
    search: Optional[str] = None,
    featured_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get the public A-Z database list for patrons.

    Returns active, non-expired databases with pre-generated proxy URLs.
    Filters by patron type restrictions if user is logged in.
    """
    query = (
        select(DatabaseSubscription)
        .options(selectinload(DatabaseSubscription.proxy_config))
        .where(
            DatabaseSubscription.is_active == True,
            DatabaseSubscription.subscription_end >= date.today(),
        )
    )

    if category:
        query = query.where(DatabaseSubscription.category == category)

    if featured_only:
        query = query.where(DatabaseSubscription.is_featured == True)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                DatabaseSubscription.name.ilike(search_term),
                DatabaseSubscription.description.ilike(search_term),
            )
        )

    query = query.order_by(DatabaseSubscription.display_order, DatabaseSubscription.name)
    result = await db.execute(query)
    subscriptions = result.scalars().all()

    # Build public response with proxy URLs
    public_databases = []
    for sub in subscriptions:
        # Check patron type restrictions
        if sub.patron_types_allowed and current_user:
            patron_type = getattr(current_user, "patron_type", None)
            if patron_type and patron_type not in sub.patron_types_allowed:
                continue

        _proxy_cfg = sub.proxy_config
        _requires_auth = bool(
            _proxy_cfg and _proxy_cfg.requires_library_card and not _proxy_cfg.allows_guest_access
        )
        public_databases.append(
            DatabaseSubscriptionPublic(
                id=sub.id,
                name=sub.name,
                short_name=sub.short_name,
                description=sub.description,
                category=sub.category,
                subjects=sub.subjects or [],
                proxy_url=sub.get_proxy_url(),
                mobile_url=sub.mobile_url,
                help_url=sub.help_url,
                is_featured=sub.is_featured,
                logo_url=sub.logo_url,
                patron_types_allowed=sub.patron_types_allowed or [],
                simultaneous_users=sub.simultaneous_users,
                requires_authentication=_requires_auth,
            )
        )

    # Get unique categories
    categories_result = await db.execute(
        select(DatabaseSubscription.category)
        .distinct()
        .where(
            DatabaseSubscription.is_active == True,
            DatabaseSubscription.subscription_end >= date.today(),
        )
    )
    categories = [row[0] for row in categories_result.all() if row[0]]

    return DatabaseAZListResponse(
        databases=public_databases, total=len(public_databases), categories=sorted(categories)
    )


@router.get("/public/{database_id}", response_model=DatabaseSubscriptionPublic)
async def get_public_database(
    database_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get a specific database's public information with proxy URL."""
    result = await db.execute(
        select(DatabaseSubscription)
        .options(selectinload(DatabaseSubscription.proxy_config))
        .where(
            DatabaseSubscription.id == database_id,
            DatabaseSubscription.is_active == True,
            DatabaseSubscription.subscription_end >= date.today(),
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database not found")

    _proxy_cfg = subscription.proxy_config
    _requires_auth = bool(
        _proxy_cfg and _proxy_cfg.requires_library_card and not _proxy_cfg.allows_guest_access
    )
    return DatabaseSubscriptionPublic(
        id=subscription.id,
        name=subscription.name,
        short_name=subscription.short_name,
        description=subscription.description,
        category=subscription.category,
        subjects=subscription.subjects or [],
        proxy_url=subscription.get_proxy_url(),
        mobile_url=subscription.mobile_url,
        help_url=subscription.help_url,
        is_featured=subscription.is_featured,
        logo_url=subscription.logo_url,
        patron_types_allowed=subscription.patron_types_allowed or [],
        simultaneous_users=subscription.simultaneous_users,
        requires_authentication=_requires_auth,
    )


# ============ ACCESS LOGGING ============


@router.get("/access/{database_id}", response_model=ProxyUrlResponse)
async def check_database_access(
    database_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Check if a database is accessible without logging the access.

    Returns the appropriate access URL if available.
    """
    result = await db.execute(
        select(DatabaseSubscription)
        .options(selectinload(DatabaseSubscription.proxy_config))
        .where(DatabaseSubscription.id == database_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database not found")

    if not subscription.is_active or subscription.subscription_end < date.today():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This database subscription is not currently available",
        )

    return ProxyUrlResponse(
        database_id=subscription.id,
        database_name=subscription.name,
        original_url=subscription.access_url,
        proxy_url=subscription.get_proxy_url(),
        requires_authentication=subscription.requires_proxy
        and subscription.proxy_config.requires_library_card
        if subscription.proxy_config
        else False,
    )


@router.post("/access/{database_id}", status_code=status.HTTP_201_CREATED)
async def log_database_access(  # noqa: role-check -- public database access log, optional auth
    database_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Log database access and return the proxy URL.

    Called when a patron clicks on a database link.
    Returns the appropriate access URL.
    """
    result = await db.execute(
        select(DatabaseSubscription)
        .options(selectinload(DatabaseSubscription.proxy_config))
        .where(DatabaseSubscription.id == database_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database not found")

    if not subscription.is_active or subscription.subscription_end < date.today():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This database subscription is not currently available",
        )

    # Enforce library card authentication requirement
    proxy_cfg = subscription.proxy_config
    if proxy_cfg and proxy_cfg.requires_library_card and not proxy_cfg.allows_guest_access:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Library card authentication required to access this database. Please log in.",
            )

    # Determine client IP early (needed for concurrent check)
    client_ip = request.client.host if request.client else None

    # --- Concurrent user enforcement ---
    if subscription.simultaneous_users is not None:
        from ...services.concurrent_session_service import check_and_acquire_session

        admitted, active_count = await check_and_acquire_session(
            subscription_id=subscription.id,
            simultaneous_users=subscription.simultaneous_users,
            session_ttl_minutes=getattr(subscription, "session_ttl_minutes", None),
            user_id=current_user.id if current_user else None,
            ip_hash=sha256(client_ip.encode()).hexdigest()[:16] if client_ip else None,
        )

        if not admitted:
            # Log the turnaway
            turnaway_log = DatabaseAccessLog(
                subscription_id=database_id,
                user_id=current_user.id if current_user else None,
                patron_type=getattr(current_user, "patron_type", None) if current_user else None,
                user_role=str(current_user.role) if current_user else None,
                is_onsite=False,
                ip_hash=sha256(client_ip.encode()).hexdigest()[:16] if client_ip else None,
                access_method="web",
                referrer_type="a-z_list",
                success=False,
                error_type="license_limit",
            )
            db.add(turnaway_log)

            # Increment monthly turnaway stats
            await _increment_turnaway_stats(db, database_id)

            await db.commit()

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "license_limit",
                    "message": (
                        f"All {subscription.simultaneous_users} access slots for "
                        f'"{subscription.name}" are currently in use. '
                        f"Please try again in a few minutes."
                    ),
                    "simultaneous_users": subscription.simultaneous_users,
                    "retry_after_seconds": 60,
                },
            )

    # Determine if on-site (check against proxy config IP ranges)
    is_onsite = False

    if client_ip and subscription.proxy_config and subscription.proxy_config.onsite_ip_ranges:
        try:
            client_addr = ipaddress.ip_address(client_ip)
            for cidr in subscription.proxy_config.onsite_ip_ranges:
                try:
                    if client_addr in ipaddress.ip_network(cidr, strict=False):
                        is_onsite = True
                        break
                except ValueError:
                    pass  # Skip malformed CIDR entries
        except ValueError:
            pass  # Skip malformed client IP (e.g., from proxy headers)

    # Hash IP for privacy
    ip_hash = sha256(client_ip.encode()).hexdigest()[:16] if client_ip else None

    # Create access log
    access_log = DatabaseAccessLog(
        subscription_id=database_id,
        user_id=current_user.id if current_user else None,
        patron_type=getattr(current_user, "patron_type", None) if current_user else "guest",
        user_role=str(current_user.role) if current_user else None,
        is_onsite=is_onsite,
        ip_hash=ip_hash,
        access_method="web",
        referrer_type="a-z_list",
        success=True,
    )
    db.add(access_log)
    await db.commit()

    # Return appropriate URL
    if is_onsite and not subscription.requires_proxy:
        return {"url": subscription.access_url, "proxied": False}

    return {"url": subscription.get_proxy_url(), "proxied": subscription.requires_proxy}


# ============ USAGE STATISTICS ============


@router.get(
    "/subscriptions/{subscription_id}/usage", response_model=List[DatabaseUsageStatsResponse]
)
async def get_subscription_usage(
    subscription_id: int,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get usage statistics for a subscription (staff only)."""
    await require_staff(current_user)

    query = select(DatabaseUsageStats).where(DatabaseUsageStats.subscription_id == subscription_id)

    if year:
        query = query.where(DatabaseUsageStats.stat_year == year)

    query = query.order_by(
        DatabaseUsageStats.stat_year.desc(), DatabaseUsageStats.stat_month.desc()
    )
    # cost_per_use (response schema) is a model property that reads
    # self.subscription; without this the sync serialization pass lazy-loads it
    # and raises MissingGreenlet.
    query = query.options(selectinload(DatabaseUsageStats.subscription))
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/subscriptions/{subscription_id}/usage", response_model=DatabaseUsageStatsResponse)
async def upsert_usage_stats(
    subscription_id: int,
    stats_in: DatabaseUsageStatsBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update usage statistics for a subscription period (staff only).

    Upsert by (subscription_id, stat_year, stat_month). Re-posting the same
    month overwrites previous values rather than creating a duplicate row.
    Returns 200 with the resulting row in either case. subscription_id comes
    from the path, not the body.
    """
    await require_staff(current_user)

    sub_result = await db.execute(
        select(DatabaseSubscription).where(DatabaseSubscription.id == subscription_id)
    )
    if not sub_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    existing_result = await db.execute(
        select(DatabaseUsageStats).where(
            DatabaseUsageStats.subscription_id == subscription_id,
            DatabaseUsageStats.stat_year == stats_in.stat_year,
            DatabaseUsageStats.stat_month == stats_in.stat_month,
        )
    )
    existing = existing_result.scalar_one_or_none()

    payload = stats_in.model_dump()
    # data_source defaults to "manual" when unset; preserves existing value if present
    if payload.get("data_source") is None:
        payload["data_source"] = existing.data_source if existing else "manual"

    if existing is None:
        stats = DatabaseUsageStats(subscription_id=subscription_id, **payload)
        db.add(stats)
    else:
        for field, value in payload.items():
            setattr(existing, field, value)
        stats = existing

    await db.commit()
    # Name the relationship: a bare refresh() reloads columns only, and the
    # cost_per_use property in the response schema reads self.subscription.
    await db.refresh(stats, attribute_names=["subscription"])
    return stats


@router.put(
    "/subscriptions/{subscription_id}/usage/{stats_id}",
    response_model=DatabaseUsageStatsResponse,
)
async def update_usage_stats(
    subscription_id: int,
    stats_id: int,
    stats_in: DatabaseUsageStatsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Partial update of an existing usage stats row (staff only)."""
    await require_staff(current_user)

    result = await db.execute(
        select(DatabaseUsageStats).where(
            DatabaseUsageStats.id == stats_id,
            DatabaseUsageStats.subscription_id == subscription_id,
        )
    )
    stats = result.scalar_one_or_none()
    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usage stats row not found"
        )

    for field, value in stats_in.model_dump(exclude_unset=True).items():
        setattr(stats, field, value)

    await db.commit()
    await db.refresh(stats, attribute_names=["subscription"])
    return stats


@router.delete(
    "/subscriptions/{subscription_id}/usage/{stats_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_usage_stats(
    subscription_id: int,
    stats_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a usage stats row (staff only). Used to correct period mistakes."""
    await require_staff(current_user)

    result = await db.execute(
        select(DatabaseUsageStats).where(
            DatabaseUsageStats.id == stats_id,
            DatabaseUsageStats.subscription_id == subscription_id,
        )
    )
    stats = result.scalar_one_or_none()
    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usage stats row not found"
        )

    await db.delete(stats)
    await db.commit()


@router.get("/reports/usage", response_model=UsageReportPreview)
async def get_usage_report_preview(
    year: int = Query(..., ge=2000, le=2100),
    format: str = Query("json", pattern="^(json|csv|tsv)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """COUNTER R5 DR_D1 usage report (staff only).

    `format=json` returns a structured preview suitable for table rendering.
    `format=csv` or `format=tsv` returns a TSV file download conforming to
    the COUNTER R5 Code of Practice. The extension may say .csv for state
    library compatibility, but the contents are tab-separated.
    """
    await require_staff(current_user)

    from ...services.counter_report_service import (
        CounterReportService,
        DR_D1_COLUMNS,
        estimate_cost_per_use,
    )

    if format in ("csv", "tsv"):
        service = CounterReportService(db)
        tsv = await service.generate_dr_d1(year)
        filename = f"counter_dr_d1_{year}.tsv"

        def iterator():
            yield tsv

        return StreamingResponse(
            iterator(),
            media_type="text/tab-separated-values",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # JSON preview
    from ...core.branding import branding

    sub_result = await db.execute(
        select(DatabaseSubscription)
        .options(
            selectinload(DatabaseSubscription.vendor),
            selectinload(DatabaseSubscription.usage_stats),
        )
        .order_by(DatabaseSubscription.name)
    )
    subs = sub_result.scalars().all()

    rows: list[UsageReportRow] = []
    totals = {col: 0 for col in DR_D1_COLUMNS if col not in ("Database", "Publisher", "Platform")}

    for sub in subs:
        year_stats = [s for s in (sub.usage_stats or []) if s.stat_year == year]
        if not year_stats:
            continue

        agg = {
            "searches_regular": sum(s.searches_regular or 0 for s in year_stats),
            "searches_federated": sum(s.searches_federated or 0 for s in year_stats),
            "searches_automated": sum(s.searches_automated or 0 for s in year_stats),
            "total_item_requests": sum(s.total_item_requests or 0 for s in year_stats),
            "unique_item_requests": sum(s.unique_item_requests or 0 for s in year_stats),
            "total_item_investigations": sum(s.total_item_investigations or 0 for s in year_stats),
            "unique_item_investigations": sum(
                s.unique_item_investigations or 0 for s in year_stats
            ),
            "no_license": sum(s.no_license or 0 for s in year_stats),
        }

        publisher = sub.vendor.name if sub.vendor else None
        platform = sub.vendor.short_name if sub.vendor and sub.vendor.short_name else publisher

        rows.append(
            UsageReportRow(
                subscription_id=sub.id,
                database=sub.name,
                publisher=publisher,
                platform=platform,
                annual_cost=sub.annual_cost,
                cost_per_use=estimate_cost_per_use(sub.annual_cost, agg["total_item_requests"]),
                **agg,
            )
        )

        totals["Searches_Regular"] += agg["searches_regular"]
        totals["Searches_Federated"] += agg["searches_federated"]
        totals["Searches_Automated"] += agg["searches_automated"]
        totals["Total_Item_Requests"] += agg["total_item_requests"]
        totals["Unique_Item_Requests"] += agg["unique_item_requests"]
        totals["Total_Item_Investigations"] += agg["total_item_investigations"]
        totals["Unique_Item_Investigations"] += agg["unique_item_investigations"]
        totals["No_License"] += agg["no_license"]

    return UsageReportPreview(
        year=year,
        institution_name=branding.library_name,
        rows=rows,
        totals=totals,
    )


# ============ DASHBOARD ============


@router.get("/dashboard", response_model=SubscriptionDashboard)
async def get_subscription_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get subscription management dashboard (staff only)."""
    await require_staff(current_user)

    today = date.today()

    # Count by status
    active_count = (
        await db.execute(
            select(func.count(DatabaseSubscription.id)).where(
                DatabaseSubscription.is_active == True,
                DatabaseSubscription.subscription_end >= today,
            )
        )
    ).scalar() or 0

    expired_count = (
        await db.execute(
            select(func.count(DatabaseSubscription.id)).where(
                DatabaseSubscription.subscription_end < today
            )
        )
    ).scalar() or 0

    # Get subscriptions expiring within 60 days
    expiring_result = await db.execute(
        select(DatabaseSubscription)
        .options(selectinload(DatabaseSubscription.vendor))
        .where(
            DatabaseSubscription.is_active == True,
            DatabaseSubscription.subscription_end >= today,
            DatabaseSubscription.subscription_end <= today + timedelta(days=60),
        )
        .order_by(DatabaseSubscription.subscription_end)
        .limit(10)
    )
    expiring_subs = expiring_result.scalars().all()

    # Build expiration alerts
    expiring_alerts = []
    for sub in expiring_subs:
        if sub.is_expiring_soon:
            expiring_alerts.append(
                SubscriptionExpirationAlert(
                    id=sub.id,
                    name=sub.name,
                    vendor_name=sub.vendor.name if sub.vendor else None,
                    subscription_end=sub.subscription_end,
                    days_until_expiry=sub.days_until_expiry,
                    status=sub.status,
                    annual_cost=sub.annual_cost,
                    renewal_contact_email=sub.renewal_contact_email,
                )
            )

    # Calculate total annual cost
    total_cost = (
        await db.execute(
            select(func.sum(DatabaseSubscription.annual_cost)).where(
                DatabaseSubscription.is_active == True,
                DatabaseSubscription.subscription_end >= today,
            )
        )
    ).scalar() or Decimal("0")

    return SubscriptionDashboard(
        total_active=active_count,
        total_expired=expired_count,
        total_expiring_soon=len(expiring_alerts),
        total_annual_cost=total_cost,
        expiring_alerts=expiring_alerts,
        recently_renewed=[],  # Would need renewal tracking
        top_used=[],  # Would need usage aggregation
    )


# ============ RENEWAL NOTIFICATIONS ============


@router.get(
    "/subscriptions/{subscription_id}/notifications",
    response_model=List[RenewalNotificationResponse],
)
async def get_renewal_notifications(
    subscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get renewal notification history for a subscription (staff only)."""
    await require_staff(current_user)

    result = await db.execute(
        select(DatabaseRenewalNotification)
        .where(DatabaseRenewalNotification.subscription_id == subscription_id)
        .order_by(DatabaseRenewalNotification.sent_at.desc())
    )
    return result.scalars().all()


# ============ PROXY URL GENERATION ============


@router.post("/generate-proxy-url", response_model=ProxyUrlResponse)
async def generate_proxy_url(
    request: ProxyUrlRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a proxy URL for a database (any authenticated user)."""
    result = await db.execute(
        select(DatabaseSubscription)
        .options(selectinload(DatabaseSubscription.proxy_config))
        .where(DatabaseSubscription.id == request.database_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database not found")

    return ProxyUrlResponse(
        database_id=subscription.id,
        database_name=subscription.name,
        original_url=subscription.access_url,
        proxy_url=subscription.get_proxy_url(),
        requires_authentication=subscription.requires_proxy
        and subscription.proxy_config.requires_library_card
        if subscription.proxy_config
        else False,
    )


@router.get("/subscriptions/{subscription_id}/active-sessions")
async def get_active_sessions(
    subscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current active session count for a subscription (staff only)."""
    await require_staff(current_user)

    subscription = await get_or_404(
        db, DatabaseSubscription, subscription_id, "Subscription not found"
    )

    from ...services.concurrent_session_service import (
        get_active_session_count,
        DEFAULT_SESSION_TTL_MINUTES,
    )

    count = await get_active_session_count(subscription_id)

    return {
        "subscription_id": subscription_id,
        "database_name": subscription.name,
        "active_sessions": count,
        "simultaneous_users_limit": subscription.simultaneous_users,
        "session_ttl_minutes": subscription.session_ttl_minutes or DEFAULT_SESSION_TTL_MINUTES,
        "redis_available": count is not None,
    }
