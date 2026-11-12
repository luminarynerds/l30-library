# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API routes for multi-branch management.

Provides endpoints for:
- Library system management
- Region management
- Branch management
- Branch hours and closures
- Branch settings
- Transit requests and shipments
- Branch-level reporting
"""

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.cache_strategies import CacheStrategy, CacheKeyBuilder, CacheTTL
from ...core.cache import get_cached_with_lock
from ...core.database import get_db
from ...core.authorization import require_role
from ...core.http_cache import cache_for
from .dependencies import require_admin, require_staff
from ...models.user import User, UserRole
from ...models.multi_branch import (
    BranchStatus,
    BranchType,
    DayOfWeek,
    TransitPriority,
    TransitReason,
    TransitStatus,
)
from ...schemas.multi_branch import (
    # Library System
    LibrarySystemCreate,
    LibrarySystemUpdate,
    LibrarySystemResponse,
    SystemSettingsUpdate,
    SystemSettingsResponse,
    # Region
    RegionCreate,
    RegionUpdate,
    RegionResponse,
    # Branch
    BranchCreate,
    BranchUpdate,
    BranchResponse,
    BranchDetailResponse,
    BranchHoursCreate,
    BranchHoursUpdate,
    BranchHoursResponse,
    BranchClosureCreate,
    BranchClosureResponse,
    CloseTodayRequest,
    ClosureStatusResponse,
    ClosureCompletionStatus,
    UpdateExternalServicesRequest,
    NotifyPartnersRequest,
    ScheduleReopeningRequest,
    PatronWithHolds,
    AffectedEvent,
    StaffMember,
    BranchSettingsUpdate,
    BranchSettingsResponse,
    # Transit
    TransitRequestCreate,
    TransitRequestResponse,
    TransitRequestDetailResponse,
    TransitShipmentCreate,
    TransitShipmentResponse,
    TransitShipmentDetailResponse,
    TransitShipmentItemResponse,
    TransitStatisticsResponse,
    # Statistics
    BranchStatisticsResponse,
    SystemStatisticsResponse,
    BranchComparisonResponse,
    # Item assignment
    BranchItemCopyCreate,
    BranchItemCopyResponse,
)
from ...services.branch_service import BranchService
from ...services.transit_service import TransitService
from ...services.branch_reporting_service import BranchReportingService
from ...services.closure_management_service import ClosureManagementService


router = APIRouter(prefix="/branches", tags=["branches"])


# =============================================================================
# DEPENDENCIES
# =============================================================================

async def get_branch_service(db: AsyncSession = Depends(get_db)) -> BranchService:
    return BranchService(db)


async def get_transit_service(db: AsyncSession = Depends(get_db)) -> TransitService:
    return TransitService(db)


async def get_reporting_service(db: AsyncSession = Depends(get_db)) -> BranchReportingService:
    return BranchReportingService(db)


async def get_closure_management_service(db: AsyncSession = Depends(get_db)) -> ClosureManagementService:
    return ClosureManagementService(db)


# =============================================================================
# LIBRARY SYSTEM ENDPOINTS
# =============================================================================

@router.post("/systems", response_model=LibrarySystemResponse, status_code=status.HTTP_201_CREATED)
async def create_library_system(
    data: LibrarySystemCreate,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    service: BranchService = Depends(get_branch_service),
):
    """Create a new library system. Requires SUPER_ADMIN role."""
    # Check if code already exists
    existing = await service.get_library_system_by_code(data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Library system with code '{data.code}' already exists"
        )

    return await service.create_library_system(**data.model_dump())


@router.get("/systems", response_model=list[LibrarySystemResponse])
async def list_library_systems(
    active_only: bool = Query(True, description="Only return active systems"),
    service: BranchService = Depends(get_branch_service),
):
    """List all library systems."""
    return await service.list_library_systems(active_only=active_only)


@router.get("/systems/{system_id}", response_model=LibrarySystemResponse)
async def get_library_system(
    system_id: int,
    service: BranchService = Depends(get_branch_service),
):
    """Get a library system by ID."""
    system = await service.get_library_system(system_id)
    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library system not found"
        )
    return system


@router.patch("/systems/{system_id}", response_model=LibrarySystemResponse)
async def update_library_system(
    system_id: int,
    data: LibrarySystemUpdate,
    current_user: User = Depends(require_admin),
    service: BranchService = Depends(get_branch_service),
):
    """Update a library system. Requires ADMIN role."""
    system = await service.update_library_system(
        system_id,
        **data.model_dump(exclude_unset=True)
    )
    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library system not found"
        )
    return system


@router.get("/systems/{system_id}/settings", response_model=SystemSettingsResponse)
async def get_system_settings(
    system_id: int,
    service: BranchService = Depends(get_branch_service),
):
    """Get system settings."""
    system = await service.get_library_system(system_id)
    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library system not found"
        )
    return system.system_settings


@router.patch("/systems/{system_id}/settings", response_model=SystemSettingsResponse)
async def update_system_settings(
    system_id: int,
    data: SystemSettingsUpdate,
    current_user: User = Depends(require_admin),
    service: BranchService = Depends(get_branch_service),
):
    """Update system settings. Requires ADMIN role."""
    system = await service.get_library_system(system_id)
    if not system or not system.system_settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library system not found"
        )

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(system.system_settings, key, value)

    await service.db.commit()
    await service.db.refresh(system.system_settings)
    return system.system_settings


# =============================================================================
# REGION ENDPOINTS
# =============================================================================

@router.post("/regions", response_model=RegionResponse, status_code=status.HTTP_201_CREATED)
async def create_region(
    data: RegionCreate,
    current_user: User = Depends(require_admin),
    service: BranchService = Depends(get_branch_service),
):
    """Create a new region. Requires ADMIN role."""
    return await service.create_region(**data.model_dump())


@router.get(
    "/systems/{system_id}/regions",
    response_model=list[RegionResponse],
    dependencies=[Depends(cache_for(CacheTTL.LONG))],
)
async def list_regions(
    system_id: int,
    active_only: bool = Query(True),
    service: BranchService = Depends(get_branch_service),
):
    """List regions for a library system."""
    return await service.list_regions(system_id, active_only=active_only)


@router.get("/regions/{region_id}", response_model=RegionResponse)
async def get_region(
    region_id: int,
    service: BranchService = Depends(get_branch_service),
):
    """Get a region by ID."""
    region = await service.get_region(region_id)
    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Region not found"
        )
    return region


@router.patch("/regions/{region_id}", response_model=RegionResponse)
async def update_region(
    region_id: int,
    data: RegionUpdate,
    current_user: User = Depends(require_admin),
    service: BranchService = Depends(get_branch_service),
):
    """Update a region. Requires ADMIN role."""
    region = await service.get_region(region_id)
    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Region not found"
        )

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(region, key, value)

    await service.db.commit()
    await service.db.refresh(region)
    return region


# =============================================================================
# BRANCH ENDPOINTS
# =============================================================================

@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_branch(
    data: BranchCreate,
    current_user: User = Depends(require_admin),
    service: BranchService = Depends(get_branch_service),
):
    """Create a new branch. Requires ADMIN role."""
    # Check if code already exists in system
    existing = await service.get_branch_by_code(data.library_system_id, data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Branch with code '{data.code}' already exists in this system"
        )

    return await service.create_branch(**data.model_dump())


@router.get(
    "",
    response_model=list[BranchResponse],
    dependencies=[Depends(cache_for(CacheTTL.MEDIUM))],
)
async def list_branches(
    library_system_id: int | None = Query(None, description="Filter by library system"),
    region_id: int | None = Query(None, description="Filter by region"),
    branch_type: BranchType | None = Query(None, description="Filter by branch type"),
    status: BranchStatus | None = Query(None, description="Filter by status"),
    active_only: bool = Query(True, description="Only return active branches"),
    service: BranchService = Depends(get_branch_service),
):
    """List branches with optional filters."""
    return await service.list_branches(
        library_system_id=library_system_id,
        region_id=region_id,
        branch_type=branch_type,
        status=status,
        active_only=active_only,
    )


@router.get(
    "/{branch_id}",
    response_model=BranchDetailResponse,
    dependencies=[Depends(cache_for(CacheTTL.MEDIUM))],
)
async def get_branch(
    branch_id: int,
    service: BranchService = Depends(get_branch_service),
):
    """Get a branch by ID with hours and settings."""

    async def _fetch():
        return await service.get_branch(branch_id)

    branch = await get_cached_with_lock(
        CacheKeyBuilder.branch(branch_id), _fetch, ttl_seconds=CacheTTL.LONG
    )
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found"
        )
    return branch


@router.patch("/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: int,
    data: BranchUpdate,
    current_user: User = Depends(require_admin),
    service: BranchService = Depends(get_branch_service),
):
    """Update a branch. Requires ADMIN role."""
    branch = await service.update_branch(
        branch_id,
        **data.model_dump(exclude_unset=True)
    )
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found"
        )
    return branch


@router.get("/{branch_id}/is-open")
async def check_branch_open(
    branch_id: int,
    check_time: datetime | None = Query(None, description="Time to check (defaults to now)"),
    service: BranchService = Depends(get_branch_service),
):
    """Check if a branch is currently open."""
    is_open, reason = await service.is_branch_open(branch_id, check_time)
    return {
        "branch_id": branch_id,
        "is_open": is_open,
        "reason": reason,
        "checked_at": check_time or datetime.now(),
    }


# =============================================================================
# BRANCH HOURS ENDPOINTS
# =============================================================================

@router.get(
    "/{branch_id}/hours",
    response_model=list[BranchHoursResponse],
    dependencies=[Depends(cache_for(CacheTTL.LONG))],
)
async def get_branch_hours(
    branch_id: int,
    effective_date: date | None = Query(None, description="Get hours effective on this date"),
    service: BranchService = Depends(get_branch_service),
):
    """Get branch hours."""
    return await service.get_branch_hours(branch_id, effective_date)


@router.put("/{branch_id}/hours/{day_of_week}", response_model=BranchHoursResponse)
async def set_branch_hours(
    branch_id: int,
    day_of_week: DayOfWeek,
    data: BranchHoursUpdate,
    current_user: User = Depends(require_admin),
    service: BranchService = Depends(get_branch_service),
):
    """Set hours for a specific day. Requires ADMIN role."""
    return await service.set_branch_hours(
        branch_id,
        day_of_week,
        **data.model_dump(exclude_unset=True)
    )


# =============================================================================
# BRANCH CLOSURE ENDPOINTS
# =============================================================================

@router.post("/{branch_id}/closures", response_model=BranchClosureResponse, status_code=status.HTTP_201_CREATED)
async def create_closure(
    branch_id: int,
    data: BranchClosureCreate,
    current_user: User = Depends(require_admin),
    service: BranchService = Depends(get_branch_service),
):
    """Create a branch closure. Requires ADMIN role."""
    return await service.create_closure(
        branch_id=branch_id,
        created_by_id=current_user.id,
        **data.model_dump(exclude={"branch_id"})
    )


@router.get("/{branch_id}/closures", response_model=list[BranchClosureResponse])
async def list_closures(
    branch_id: int,
    days_ahead: int = Query(30, description="Number of days ahead to look"),
    service: BranchService = Depends(get_branch_service),
):
    """Get upcoming closures for a branch."""
    return await service.get_upcoming_closures(
        branch_id=branch_id,
        days_ahead=days_ahead
    )


# =============================================================================
# BRANCH SETTINGS ENDPOINTS
# =============================================================================

@router.get("/{branch_id}/settings", response_model=BranchSettingsResponse)
async def get_branch_settings(
    branch_id: int,
    service: BranchService = Depends(get_branch_service),
):
    """Get branch settings."""
    branch = await service.get_branch(branch_id)
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found"
        )
    return branch.settings


@router.patch("/{branch_id}/settings", response_model=BranchSettingsResponse)
async def update_branch_settings(
    branch_id: int,
    data: BranchSettingsUpdate,
    current_user: User = Depends(require_admin),
    service: BranchService = Depends(get_branch_service),
):
    """Update branch settings. Requires ADMIN role."""
    branch = await service.get_branch(branch_id)
    if not branch or not branch.settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found"
        )

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(branch.settings, key, value)

    await service.db.commit()
    await service.db.refresh(branch.settings)
    return branch.settings


# =============================================================================
# TRANSIT REQUEST ENDPOINTS
# =============================================================================

@router.post("/transit/requests", response_model=TransitRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_transit_request(
    data: TransitRequestCreate,
    current_user: User = Depends(require_staff),
    service: TransitService = Depends(get_transit_service),
):
    """Create a transit request. Requires STAFF role."""
    return await service.create_transit_request(
        requested_by_id=current_user.id,
        **data.model_dump()
    )


@router.get("/transit/requests", response_model=list[TransitRequestDetailResponse])
async def list_transit_requests(
    from_branch_id: int | None = Query(None),
    to_branch_id: int | None = Query(None),
    status: TransitStatus | None = Query(None),
    priority: TransitPriority | None = Query(None),
    reason: TransitReason | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: TransitService = Depends(get_transit_service),
):
    """List transit requests with filters."""
    return await service.list_transit_requests(
        from_branch_id=from_branch_id,
        to_branch_id=to_branch_id,
        status=status,
        priority=priority,
        reason=reason,
        limit=limit,
        offset=offset,
    )


@router.get("/transit/requests/{request_id}", response_model=TransitRequestDetailResponse)
async def get_transit_request(
    request_id: int,
    service: TransitService = Depends(get_transit_service),
):
    """Get a transit request by ID."""
    request = await service.get_transit_request(request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transit request not found"
        )
    return request


@router.post("/transit/requests/{request_id}/approve", response_model=TransitRequestResponse)
async def approve_transit_request(
    request_id: int,
    current_user: User = Depends(require_staff),
    service: TransitService = Depends(get_transit_service),
):
    """Approve a transit request. Requires STAFF role."""
    try:
        return await service.approve_transit_request(request_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/transit/requests/{request_id}/pickup", response_model=TransitRequestResponse)
async def mark_item_picked_up(
    request_id: int,
    current_user: User = Depends(require_staff),
    service: TransitService = Depends(get_transit_service),
):
    """Mark an item as picked up. Requires STAFF role."""
    try:
        return await service.mark_item_picked_up(request_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/transit/requests/{request_id}/receive", response_model=TransitRequestResponse)
async def receive_transit_item(
    request_id: int,
    current_user: User = Depends(require_staff),
    service: TransitService = Depends(get_transit_service),
):
    """Receive a transit item. Requires STAFF role."""
    try:
        return await service.receive_transit_item(request_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/transit/requests/{request_id}/cancel", response_model=TransitRequestResponse)
async def cancel_transit_request(
    request_id: int,
    reason: str | None = Query(None),
    current_user: User = Depends(require_staff),
    service: TransitService = Depends(get_transit_service),
):
    """Cancel a transit request. Requires STAFF role."""
    try:
        return await service.cancel_transit_request(request_id, current_user.id, reason)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =============================================================================
# TRANSIT SHIPMENT ENDPOINTS
# =============================================================================

@router.post("/transit/shipments", response_model=TransitShipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_shipment(
    data: TransitShipmentCreate,
    current_user: User = Depends(require_staff),
    service: TransitService = Depends(get_transit_service),
):
    """Create a transit shipment. Requires STAFF role."""
    return await service.create_shipment(
        created_by_id=current_user.id,
        **data.model_dump()
    )


@router.get("/transit/shipments", response_model=list[TransitShipmentResponse])
async def list_shipments(
    from_branch_id: int | None = Query(None),
    to_branch_id: int | None = Query(None),
    shipped: bool | None = Query(None),
    received: bool | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: TransitService = Depends(get_transit_service),
):
    """List transit shipments with filters."""
    return await service.list_shipments(
        from_branch_id=from_branch_id,
        to_branch_id=to_branch_id,
        shipped=shipped,
        received=received,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )


@router.get("/transit/shipments/{shipment_id}", response_model=TransitShipmentDetailResponse)
async def get_shipment(
    shipment_id: int,
    service: TransitService = Depends(get_transit_service),
):
    """Get a shipment by ID."""
    shipment = await service.get_shipment(shipment_id)
    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )
    return shipment


@router.post("/transit/shipments/{shipment_id}/items", response_model=TransitShipmentItemResponse)
async def add_item_to_shipment(
    shipment_id: int,
    transit_request_id: int,
    current_user: User = Depends(require_staff),
    service: TransitService = Depends(get_transit_service),
):
    """Add an item to a shipment. Requires STAFF role."""
    try:
        return await service.add_item_to_shipment(
            shipment_id, transit_request_id, current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/transit/shipments/{shipment_id}/ship", response_model=TransitShipmentResponse)
async def ship_shipment(
    shipment_id: int,
    tracking_number: str | None = Query(None),
    current_user: User = Depends(require_staff),
    service: TransitService = Depends(get_transit_service),
):
    """Mark a shipment as shipped. Requires STAFF role."""
    try:
        return await service.ship_shipment(shipment_id, current_user.id, tracking_number)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/transit/shipments/{shipment_id}/receive", response_model=TransitShipmentResponse)
async def receive_shipment(
    shipment_id: int,
    current_user: User = Depends(require_staff),
    service: TransitService = Depends(get_transit_service),
):
    """Receive a shipment. Requires STAFF role."""
    try:
        return await service.receive_shipment(shipment_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =============================================================================
# TRANSIT STATISTICS ENDPOINTS
# =============================================================================

@router.get("/transit/statistics", response_model=TransitStatisticsResponse)
async def get_transit_statistics(
    library_system_id: int | None = Query(None),
    branch_id: int | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    service: TransitService = Depends(get_transit_service),
):
    """Get transit statistics."""
    return await service.get_transit_statistics(
        library_system_id=library_system_id,
        branch_id=branch_id,
        from_date=from_date,
        to_date=to_date,
    )


# =============================================================================
# BRANCH REPORTING ENDPOINTS
# =============================================================================

@router.get("/{branch_id}/statistics", response_model=BranchStatisticsResponse)
async def get_branch_statistics(
    branch_id: int,
    period_start: date,
    period_end: date,
    service: BranchReportingService = Depends(get_reporting_service),
):
    """Get or generate statistics for a branch."""
    return await service.generate_branch_statistics(
        branch_id, period_start, period_end
    )


@router.get("/systems/{system_id}/statistics", response_model=SystemStatisticsResponse)
async def get_system_statistics(
    system_id: int,
    period_start: date,
    period_end: date,
    service: BranchReportingService = Depends(get_reporting_service),
):
    """Get aggregated statistics for a library system."""
    return await service.get_system_statistics(
        system_id, period_start, period_end
    )


@router.get("/systems/{system_id}/comparison", response_model=list[BranchComparisonResponse])
async def get_branch_comparison(
    system_id: int,
    period_start: date,
    period_end: date,
    service: BranchReportingService = Depends(get_reporting_service),
):
    """Get comparative statistics across branches in a system."""
    return await service.get_branch_comparison(
        system_id, period_start, period_end
    )


@router.get("/systems/{system_id}/circulation-trend")
async def get_circulation_trend(
    system_id: int,
    months: int = Query(12, ge=1, le=36),
    service: BranchReportingService = Depends(get_reporting_service),
):
    """Get circulation trend for a library system."""
    return await service.get_circulation_trend(
        library_system_id=system_id,
        months=months,
    )


@router.get("/{branch_id}/circulation-trend")
async def get_branch_circulation_trend(
    branch_id: int,
    months: int = Query(12, ge=1, le=36),
    service: BranchReportingService = Depends(get_reporting_service),
):
    """Get circulation trend for a branch."""
    return await service.get_circulation_trend(
        branch_id=branch_id,
        months=months,
    )


# =============================================================================
# ITEM ASSIGNMENT ENDPOINTS
# =============================================================================

@router.post("/{branch_id}/items", response_model=BranchItemCopyResponse)
async def assign_item_to_branch(
    branch_id: int,
    data: BranchItemCopyCreate,
    current_user: User = Depends(require_staff),
    service: BranchService = Depends(get_branch_service),
):
    """Assign an item to a branch. Requires STAFF role."""
    return await service.assign_item_to_branch(
        item_copy_id=data.item_copy_id,
        branch_id=branch_id,
        is_floating=data.is_floating,
        float_scope=data.float_scope,
        shelving_location=data.shelving_location,
    )


@router.get("/{branch_id}/inventory", response_model=list[BranchItemCopyResponse])
async def get_branch_inventory(
    branch_id: int,
    service: BranchService = Depends(get_branch_service),
):
    """Get all items currently at a branch."""
    return await service.get_branch_inventory(branch_id)


@router.get("/{branch_id}/items-away")
async def get_items_away_from_home(
    branch_id: int,
    service: BranchService = Depends(get_branch_service),
):
    """Get items belonging to this branch but currently elsewhere."""
    return await service.get_items_away_from_home(branch_id)


# =============================================================================
# CLOSURE MANAGEMENT ENDPOINTS
# =============================================================================

@router.post("/{branch_id}/closures/close-today", response_model=BranchClosureResponse, status_code=status.HTTP_201_CREATED)
async def close_today(
    branch_id: int,
    data: CloseTodayRequest,
    current_user: User = Depends(require_admin),
    service: ClosureManagementService = Depends(get_closure_management_service),
):
    """
    One-click action to close a branch immediately for today.

    Handles:
    - Creating a full-day closure
    - Notifying patrons with holds
    - Notifying staff
    - Canceling today's events
    - Updating external services (website, maps, etc.)
    """
    try:
        return await service.close_today(
            branch_id=branch_id,
            reason=data.reason,
            created_by_id=current_user.id,
            closure_documentation=data.closure_documentation,
            send_notifications=data.send_notifications,
            cancel_events=data.cancel_events,
            reschedule_programs=data.reschedule_programs,
            update_external_services=data.update_external_services,
            notify_partner_organizations=data.notify_partner_organizations,
            partner_list=data.partner_list,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/{branch_id}/closures/{closure_id}/status", response_model=ClosureStatusResponse)
async def get_closure_status(
    branch_id: int,
    closure_id: int,
    current_user: User = Depends(require_staff),
    service: ClosureManagementService = Depends(get_closure_management_service),
):
    """Get comprehensive status of a closure including all notifications and integrations."""
    try:
        return await service.get_closure_status(closure_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/{branch_id}/closures/{closure_id}/completion", response_model=ClosureCompletionStatus)
async def get_closure_completion(
    branch_id: int,
    closure_id: int,
    current_user: User = Depends(require_staff),
    service: ClosureManagementService = Depends(get_closure_management_service),
):
    """Get summary of closure completion status."""
    try:
        return await service.get_closure_completion_status(closure_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/{branch_id}/closures/{closure_id}/affected-patrons", response_model=list[PatronWithHolds])
async def get_patrons_with_holds(
    branch_id: int,
    closure_id: int,
    current_user: User = Depends(require_staff),
    service: ClosureManagementService = Depends(get_closure_management_service),
):
    """Get list of patrons with holds ready for pickup during closure."""
    try:
        return await service.get_patrons_with_holds(closure_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/{branch_id}/closures/{closure_id}/affected-events", response_model=list[AffectedEvent])
async def get_affected_events(
    branch_id: int,
    closure_id: int,
    current_user: User = Depends(require_staff),
    service: ClosureManagementService = Depends(get_closure_management_service),
):
    """Get list of events that fall during the closure period."""
    try:
        return await service.get_affected_events(closure_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/{branch_id}/closures/{closure_id}/staff-notifications", response_model=list[StaffMember])
async def get_staff_notification_list(
    branch_id: int,
    closure_id: int,
    current_user: User = Depends(require_staff),
    service: ClosureManagementService = Depends(get_closure_management_service),
):
    """Get list of staff who need to be notified about the closure."""
    try:
        return await service.get_staff_notification_list(closure_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.patch("/{branch_id}/closures/{closure_id}/external-services", response_model=BranchClosureResponse)
async def update_external_services(
    branch_id: int,
    closure_id: int,
    data: UpdateExternalServicesRequest,
    current_user: User = Depends(require_admin),
    service: ClosureManagementService = Depends(get_closure_management_service),
):
    """Update status of external service integrations (website, maps, social media, etc.)."""
    try:
        return await service.update_external_services(
            closure_id=closure_id,
            updated_by_id=current_user.id,
            website=data.website,
            phone_message=data.phone_message,
            social_media=data.social_media,
            google_maps=data.google_maps,
            apple_maps=data.apple_maps,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/{branch_id}/closures/{closure_id}/notify-partners", response_model=BranchClosureResponse)
async def notify_partners(
    branch_id: int,
    closure_id: int,
    data: NotifyPartnersRequest,
    current_user: User = Depends(require_admin),
    service: ClosureManagementService = Depends(get_closure_management_service),
):
    """Notify partner organizations about the closure."""
    try:
        return await service.notify_partners(
            closure_id=closure_id,
            updated_by_id=current_user.id,
            partner_list=data.partner_list,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/{branch_id}/closures/{closure_id}/schedule-reopening", response_model=BranchClosureResponse)
async def schedule_reopening(
    branch_id: int,
    closure_id: int,
    data: ScheduleReopeningRequest,
    current_user: User = Depends(require_admin),
    service: ClosureManagementService = Depends(get_closure_management_service),
):
    """Schedule reopening with announcement message."""
    try:
        return await service.schedule_reopening(
            closure_id=closure_id,
            reopening_announcement=data.reopening_announcement,
            updated_by_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/{branch_id}/closures/active", response_model=list[BranchClosureResponse])
async def get_active_closures(
    branch_id: int,
    current_user: User = Depends(require_staff),
    service: ClosureManagementService = Depends(get_closure_management_service),
):
    """Get all currently active closures for a branch."""
    return await service.get_active_closures(branch_id=branch_id)
