# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Streaming service API endpoints for Palace Project integration."""

from app.core.logging import get_logger
from datetime import datetime
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.streaming import (
    StreamingCheckoutStatus,
    StreamingContentType,
    StreamingService,
)
from ...models.user import User
from ...schemas.streaming import (
    BulkStreamingAvailability,
    CatalogStreamingAvailability,
    CollectionDevelopmentReport,
    DeepLinkResponse,
    DefaultPatronStreamingLimitCreate,
    DefaultPatronStreamingLimitResponse,
    PatronStreamingDashboard,
    PatronStreamingLimitCreate,
    PatronStreamingLimitResponse,
    PatronStreamingLimitUpdate,
    StreamingBudgetCreate,
    StreamingBudgetResponse,
    StreamingBudgetUpdate,
    StreamingCatalogItemResponse,
    StreamingCheckoutCreate,
    StreamingCheckoutResponse,
    StreamingDashboardStats,
    StreamingServiceConfigCreate,
    StreamingServiceConfigResponse,
    StreamingServiceConfigUpdate,
    UnifiedSearchQuery,
    UnifiedSearchResponse,
)
from ...services.streaming_service import (
    BudgetExceededError,
    CheckoutLimitExceededError,
    StreamingServiceError,
    StreamingServiceManager,
)
from ...core.config import get_settings
from .auth import get_current_user
from .dependencies import check_staff_access, check_admin_access
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)

router = APIRouter(prefix="/streaming", tags=["streaming"])


async def require_streaming_enabled():
    settings = get_settings()
    if not settings.palace_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Streaming services are not enabled",
        )




async def get_streaming_manager(
    db: AsyncSession = Depends(get_db),
) -> StreamingServiceManager:
    manager = StreamingServiceManager(db)
    try:
        yield manager
    finally:
        await manager.close_clients()


# =============================================================================
# Service Configuration Endpoints (Admin only)
# =============================================================================


@router.get("/config", response_model=List[StreamingServiceConfigResponse])
async def get_service_configs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
    _: None = Depends(require_streaming_enabled),
):
    """Get all streaming service configurations. Staff and above."""
    check_staff_access(current_user)

    configs = await manager.get_service_configs()

    return [
        StreamingServiceConfigResponse(
            id=c.id,
            service=c.service,
            is_active=c.is_active,
            api_base_url=c.api_base_url,
            library_id=c.library_id,
            cost_per_checkout=c.cost_per_checkout,
            app_deep_link_template=c.app_deep_link_template,
            web_deep_link_template=c.web_deep_link_template,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in configs
    ]


@router.post("/config", response_model=StreamingServiceConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_service_config(
    config_in: StreamingServiceConfigCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
):
    """Create a new streaming service configuration. Admin only."""
    check_admin_access(current_user)

    try:
        config = await manager.create_service_config(
            service=config_in.service,
            api_base_url=config_in.api_base_url,
            api_key=config_in.api_key,
            api_secret=config_in.api_secret,
            library_id=config_in.library_id,
            cost_per_checkout=config_in.cost_per_checkout,
            app_deep_link_template=config_in.app_deep_link_template,
            web_deep_link_template=config_in.web_deep_link_template,
        )
        await db.commit()

        return StreamingServiceConfigResponse(
            id=config.id,
            service=config.service,
            is_active=config.is_active,
            api_base_url=config.api_base_url,
            library_id=config.library_id,
            cost_per_checkout=config.cost_per_checkout,
            app_deep_link_template=config.app_deep_link_template,
            web_deep_link_template=config.web_deep_link_template,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
    except Exception as e:
        await db.rollback()
        logger.exception(f"Failed to create streaming config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create streaming service configuration",
        ) from e


@router.patch("/config/{config_id}", response_model=StreamingServiceConfigResponse)
async def update_service_config(
    config_id: int,
    config_update: StreamingServiceConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
):
    """Update a streaming service configuration. Admin only."""
    check_admin_access(current_user)


    try:
        config = await manager.update_service_config(
            config_id,
            **config_update.model_dump(exclude_unset=True),
        )

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Streaming service configuration not found",
            )

        await db.commit()

        return StreamingServiceConfigResponse(
            id=config.id,
            service=config.service,
            is_active=config.is_active,
            api_base_url=config.api_base_url,
            library_id=config.library_id,
            cost_per_checkout=config.cost_per_checkout,
            app_deep_link_template=config.app_deep_link_template,
            web_deep_link_template=config.web_deep_link_template,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Failed to update streaming config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update streaming service configuration",
        ) from e


# =============================================================================
# Budget Management Endpoints (Staff and above)
# =============================================================================


@router.get("/budgets", response_model=List[StreamingBudgetResponse])
async def get_budgets(
    service_config_id: int | None = None,
    fiscal_year: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
):
    """Get streaming budgets with optional filtering. Staff and above."""
    check_staff_access(current_user)

    budgets = await manager.get_budgets(
        service_config_id=service_config_id,
        fiscal_year=fiscal_year,
    )
    return budgets


@router.post("/budgets", response_model=StreamingBudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    budget_in: StreamingBudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
):
    """Create a new streaming budget. Admin only."""
    check_admin_access(current_user)


    try:
        budget = await manager.create_budget(
            service_config_id=budget_in.service_config_id,
            fiscal_year=budget_in.fiscal_year,
            fiscal_month=budget_in.fiscal_month,
            allocated_amount=budget_in.allocated_amount,
            max_checkouts=budget_in.max_checkouts,
        )
        await db.commit()

        utilization = 0.0
        if budget.allocated_amount > 0:
            utilization = float(budget.spent_amount / budget.allocated_amount * 100)

        return StreamingBudgetResponse(
            id=budget.id,
            service_config_id=budget.service_config_id,
            service_name=None,
            fiscal_year=budget.fiscal_year,
            fiscal_month=budget.fiscal_month,
            allocated_amount=budget.allocated_amount,
            spent_amount=budget.spent_amount,
            remaining_amount=budget.remaining_amount,
            max_checkouts=budget.max_checkouts,
            current_checkouts=budget.current_checkouts,
            remaining_checkouts=budget.remaining_checkouts,
            utilization_percentage=utilization,
            created_at=budget.created_at,
            updated_at=budget.updated_at,
        )
    except Exception as e:
        await db.rollback()
        logger.exception(f"Failed to create streaming budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create streaming budget",
        ) from e


# =============================================================================
# Patron Limit Management Endpoints
# =============================================================================


@router.get("/limits/defaults", response_model=List[DefaultPatronStreamingLimitResponse])
async def get_default_limits(
    service_config_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
):
    """Get default streaming limits by role. Staff and above."""
    check_staff_access(current_user)

    from sqlalchemy import select
    from ...models.streaming import DefaultPatronStreamingLimit

    query = select(DefaultPatronStreamingLimit)
    if service_config_id:
        query = query.where(DefaultPatronStreamingLimit.service_config_id == service_config_id)

    result = await db.execute(query)
    defaults = result.scalars().all()

    return [
        DefaultPatronStreamingLimitResponse(
            id=d.id,
            service_config_id=d.service_config_id,
            user_role=d.user_role,
            monthly_limit=d.monthly_limit,
            created_at=d.created_at,
        )
        for d in defaults
    ]


@router.post("/limits/defaults", response_model=DefaultPatronStreamingLimitResponse, status_code=status.HTTP_201_CREATED)
async def set_default_limit(
    limit_in: DefaultPatronStreamingLimitCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
):
    """Set default streaming limit for a user role. Admin only."""
    check_admin_access(current_user)


    try:
        default = await manager.set_default_patron_limit(
            service_config_id=limit_in.service_config_id,
            user_role=limit_in.user_role,
            monthly_limit=limit_in.monthly_limit,
        )
        await db.commit()

        return DefaultPatronStreamingLimitResponse(
            id=default.id,
            service_config_id=default.service_config_id,
            user_role=default.user_role,
            monthly_limit=default.monthly_limit,
            created_at=default.created_at,
        )
    except Exception as e:
        await db.rollback()
        logger.exception(f"Failed to set default limit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set default streaming limit",
        ) from e


@router.get("/limits/patron/{patron_id}", response_model=List[PatronStreamingLimitResponse])
async def get_patron_limits(
    patron_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
):
    """Get a patron's streaming limits. Staff can view any patron, patrons can view their own."""
    if current_user.id != patron_id:
        check_staff_access(current_user)

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from ...models.streaming import PatronStreamingLimit

    result = await db.execute(
        select(PatronStreamingLimit)
        .options(selectinload(PatronStreamingLimit.service_config))
        .where(PatronStreamingLimit.user_id == patron_id)
    )
    limits = result.scalars().all()

    return [
        PatronStreamingLimitResponse(
            id=l.id,
            user_id=l.user_id,
            service_config_id=l.service_config_id,
            service_name=str(l.service_config.service) if l.service_config else None,
            monthly_limit=l.monthly_limit,
            current_month_checkouts=l.current_month_checkouts,
            remaining_checkouts=l.remaining_checkouts,
            limit_reset_date=l.limit_reset_date,
        )
        for l in limits
    ]


@router.patch("/limits/patron/{user_id}/{service_config_id}", response_model=PatronStreamingLimitResponse)
async def update_patron_limit(
    user_id: int,
    service_config_id: int,
    limit_update: PatronStreamingLimitUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
):
    """Update a patron's streaming limit. Staff and above."""
    check_staff_access(current_user)

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from ...models.streaming import PatronStreamingLimit

    result = await db.execute(
        select(PatronStreamingLimit)
        .options(selectinload(PatronStreamingLimit.service_config))
        .where(
            PatronStreamingLimit.user_id == user_id,
            PatronStreamingLimit.service_config_id == service_config_id,
        )
    )
    limit = result.scalar_one_or_none()

    if not limit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patron streaming limit not found",
        )

    if limit_update.monthly_limit is not None:
        limit.monthly_limit = limit_update.monthly_limit
        limit.updated_at = utc_now()

    await db.commit()

    return PatronStreamingLimitResponse(
        id=limit.id,
        user_id=limit.user_id,
        service_config_id=limit.service_config_id,
        service_name=str(limit.service_config.service) if limit.service_config else None,
        monthly_limit=limit.monthly_limit,
        current_month_checkouts=limit.current_month_checkouts,
        remaining_checkouts=limit.remaining_checkouts,
        limit_reset_date=limit.limit_reset_date,
    )


# =============================================================================
# Search Endpoints
# =============================================================================


@router.post("/search", response_model=UnifiedSearchResponse)
async def unified_search(
    search_query: UnifiedSearchQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
    _: None = Depends(require_streaming_enabled),
):
    """Search across all streaming services."""

    try:
        result = await manager.unified_search(
            query=search_query.query,
            content_types=search_query.content_types,
            services=search_query.services,
            include_unavailable=search_query.include_unavailable,
            page=search_query.page,
            per_page=search_query.page_size,
        )
        return result
    except StreamingServiceError as e:
        logger.error("Streaming service error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Streaming service temporarily unavailable",
        ) from e
    finally:
        await manager.close_clients()


@router.get("/search", response_model=UnifiedSearchResponse)
async def search_streaming(
    q: str = Query(..., min_length=1, description="Search query"),
    content_type: StreamingContentType | None = Query(None, description="Filter by content type"),
    service: StreamingService | None = Query(None, description="Filter by service"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int | None = Query(None, ge=1, le=100, description="Results per page (legacy)"),
    page_size: int | None = Query(None, ge=1, le=100, description="Results per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
    _: None = Depends(require_streaming_enabled),
):
    """Search streaming services with query parameters."""

    content_types = [content_type] if content_type else None
    services = [service] if service else None
    effective_per_page = per_page if per_page is not None else (page_size if page_size is not None else 20)

    try:
        result = await manager.unified_search(
            query=q,
            content_types=content_types,
            services=services,
            page=page,
            per_page=effective_per_page,
        )
        return result
    except StreamingServiceError as e:
        logger.error("Streaming service error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Streaming service temporarily unavailable",
        ) from e
    finally:
        await manager.close_clients()


# =============================================================================
# Checkout Endpoints
# =============================================================================


@router.post("/checkouts", response_model=StreamingCheckoutResponse, status_code=status.HTTP_201_CREATED)
async def checkout_streaming_content(
    checkout_in: StreamingCheckoutCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
    _: None = Depends(require_streaming_enabled),
):
    """Check out streaming content."""

    try:
        checkout = await manager.checkout_content(
            user=current_user,
            streaming_item_id=checkout_in.streaming_item_id,
        )
        await db.commit()
        return checkout

    except BudgetExceededError as e:
        await db.rollback()
        logger.error("Streaming service error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Streaming budget exceeded",
        ) from e
    except CheckoutLimitExceededError as e:
        await db.rollback()
        logger.error("Streaming service error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Checkout limit exceeded",
        ) from e
    except StreamingServiceError as e:
        await db.rollback()
        logger.error("Streaming service error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Streaming service temporarily unavailable",
        ) from e
    finally:
        await manager.close_clients()


@router.post("/return/{checkout_id}")
async def return_streaming_content(
    checkout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
    _: None = Depends(require_streaming_enabled),
):
    """Return streaming content early."""

    try:
        success = await manager.return_content(
            user=current_user,
            checkout_id=checkout_id,
        )
        await db.commit()
        return {"ok": success, "message": "Content returned successfully" if success else "Return may be pending"}
    except StreamingServiceError as e:
        await db.rollback()
        logger.error("Streaming service error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Streaming service temporarily unavailable",
        ) from e
    finally:
        await manager.close_clients()


@router.get("/checkouts", response_model=List[StreamingCheckoutResponse])
async def get_my_checkouts(
    status_filter: StreamingCheckoutStatus | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
    _: None = Depends(require_streaming_enabled),
):
    """Get current user's streaming checkouts."""
    checkouts = await manager.get_patron_checkouts(
        user_id=current_user.id,
        status=status_filter,
    )
    return checkouts


@router.get("/checkouts/patron/{patron_id}", response_model=List[StreamingCheckoutResponse])
@router.get("/checkouts/user/{patron_id}", response_model=List[StreamingCheckoutResponse])
async def get_user_checkouts(
    patron_id: int,
    status_filter: StreamingCheckoutStatus | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
    _: None = Depends(require_streaming_enabled),
):
    """Get a patron's streaming checkouts. Staff and above."""
    if current_user.id != patron_id:
        check_staff_access(current_user)

    checkouts = await manager.get_patron_checkouts(
        user_id=patron_id,
        status=status_filter,
    )
    return checkouts


# =============================================================================
# Patron Dashboard Endpoints
# =============================================================================


@router.get("/dashboard", response_model=PatronStreamingDashboard)
async def get_patron_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
    _: None = Depends(require_streaming_enabled),
):
    """Get patron's streaming dashboard with limits and active checkouts."""
    try:
        dashboard = await manager.get_patron_dashboard(current_user)
        return dashboard
    except StreamingServiceError:
        raise
    except Exception:
        logger.exception("Failed to load patron streaming dashboard", extra={"user_id": current_user.id})
        return PatronStreamingDashboard(services=[], total_active_checkouts=0, recent_checkouts=[])


# =============================================================================
# Catalog Integration Endpoints
# =============================================================================


@router.get("/availability/{catalog_item_id}", response_model=CatalogStreamingAvailability)
async def get_streaming_availability(
    catalog_item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
    _: None = Depends(require_streaming_enabled),
):
    """Get streaming availability for a catalog item."""

    try:
        availability = await manager.get_streaming_availability(catalog_item_id)
        return availability
    except StreamingServiceError as e:
        logger.error("Streaming service error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Streaming availability not found",
        ) from e


@router.get("/availability/bulk", response_model=dict)
async def get_bulk_availability_info(
    current_user: User = Depends(get_current_user),
):
    """Get information about bulk availability checking."""
    return {
        "description": "Get streaming availability for multiple catalog items",
        "max_items_per_request": 50,
        "requires_catalog_ids": True,
        "response_includes": ["availability_status", "access_url", "expiration", "restrictions"],
    }


@router.post("/availability/bulk", response_model=BulkStreamingAvailability)
async def get_bulk_streaming_availability(
    catalog_item_ids: List[int],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
    _: None = Depends(require_streaming_enabled),
):
    """Get streaming availability for multiple catalog items."""
    if len(catalog_item_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 items per bulk request")
    availability = await manager.get_bulk_streaming_availability(catalog_item_ids)
    return availability


@router.post("/link/{streaming_item_id}/catalog/{catalog_item_id}", status_code=status.HTTP_201_CREATED)
async def link_streaming_to_catalog(
    streaming_item_id: int,
    catalog_item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
):
    """Link a streaming item to a catalog item. Staff and above."""
    check_staff_access(current_user)


    try:
        await manager.link_to_catalog(streaming_item_id, catalog_item_id)
        await db.commit()
        return {"ok": True, "message": "Streaming item linked to catalog item"}
    except StreamingServiceError as e:
        await db.rollback()
        logger.error("Streaming service error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Streaming service temporarily unavailable",
        ) from e


# =============================================================================
# Deep Link Endpoints
# =============================================================================


@router.get("/deeplink/{streaming_item_id}", response_model=DeepLinkResponse)
async def get_deep_link(
    streaming_item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
    _: None = Depends(require_streaming_enabled),
):
    """Get deep links for streaming content."""

    try:
        deep_link = await manager.get_deep_link(streaming_item_id, current_user)
        return deep_link
    except StreamingServiceError as e:
        logger.error("Streaming service error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Streaming deep link not found",
        ) from e


# =============================================================================
# Analytics and Reporting Endpoints (Staff and above)
# =============================================================================


@router.get("/dashboard/stats", response_model=StreamingDashboardStats)
async def get_dashboard_stats(
    start_date: datetime | None = Query(None, description="Start date for stats"),
    end_date: datetime | None = Query(None, description="End date for stats"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
    _: None = Depends(require_streaming_enabled),
):
    """Get streaming dashboard statistics. Staff and above."""
    check_staff_access(current_user)

    stats = await manager.get_dashboard_stats(start_date, end_date)
    return stats


@router.get("/reports/collection-development", response_model=CollectionDevelopmentReport)
async def get_collection_development_report(
    start_date: datetime = Query(..., description="Report start date"),
    end_date: datetime = Query(..., description="Report end date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
    _: None = Depends(require_streaming_enabled),
):
    """Get collection development report. Staff and above."""
    check_staff_access(current_user)

    if start_date >= end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date",
        )

    report = await manager.get_collection_development_report(start_date, end_date)
    return report


# =============================================================================
# Background Job Endpoints (Admin only)
# =============================================================================


@router.post("/jobs/expire-checkouts")
async def job_expire_checkouts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
):
    """Background job to expire old streaming checkouts. Admin only."""
    check_admin_access(current_user)

    expired_count = await manager.expire_checkouts()
    await db.commit()

    return {
        "ok": True,
        "message": f"Expired {expired_count} checkout(s)",
        "expired_count": expired_count,
        "triggered_by": current_user.email,
    }


@router.post("/jobs/aggregate-stats")
async def job_aggregate_stats(
    stat_date: datetime = Query(..., description="Date to aggregate stats for"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
):
    """Background job to aggregate daily usage stats. Admin only."""
    check_admin_access(current_user)

    await manager.aggregate_daily_stats(stat_date)
    await db.commit()

    return {
        "ok": True,
        "message": f"Aggregated stats for {stat_date.date()}",
        "stat_date": stat_date.isoformat(),
        "triggered_by": current_user.email,
    }


@router.post("/jobs/reset-monthly-limits")
async def job_reset_monthly_limits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: StreamingServiceManager = Depends(get_streaming_manager),
):
    """Background job to reset monthly patron limits. Admin only.

    This should be run on the 1st of each month.
    """
    check_admin_access(current_user)

    from sqlalchemy import select, update
    from ...models.streaming import PatronStreamingLimit

    now = utc_now()

    # Reset limits where reset date has passed
    result = await db.execute(
        update(PatronStreamingLimit)
        .where(PatronStreamingLimit.limit_reset_date <= now)
        .values(
            current_month_checkouts=0,
            limit_reset_date=datetime(
                now.year + (1 if now.month == 12 else 0),
                1 if now.month == 12 else now.month + 1,
                1,
            ),
            updated_at=now,
        )
        .returning(PatronStreamingLimit.id)
    )
    reset_ids = result.scalars().all()
    await db.commit()

    return {
        "ok": True,
        "message": f"Reset {len(reset_ids)} patron limit(s)",
        "reset_count": len(reset_ids),
        "triggered_by": current_user.email,
    }






