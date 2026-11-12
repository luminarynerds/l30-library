# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
HomeDelivery Delivery Service - Delivery Management and Tracking API Endpoints

Provides endpoints for:
- Delivery scheduling and management
- Item selection and preparation
- Route planning and optimization
- Delivery tracking and status updates
- Patron feedback
- Circulation integration (checkouts)
"""
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.catalog import CatalogItem
from ...models.home_delivery import (
    Delivery, DeliveryFeedback, DeliveryItem, DeliveryItemStatus,
    DeliveryRoute, DeliveryStatus, DeliveryVolunteer, HomeDeliveryEnrollment,
    HomeDeliveryEnrollmentStatus, RouteStatus
)
from ...models.inventory import ItemCopy
from ...models.user import User, name_search_clause
from ...schemas.home_delivery import (
    DeliveryCreate, DeliveryDetailResponse, DeliveryFeedbackCreate,
    DeliveryFeedbackFollowUp, DeliveryFeedbackResponse, DeliveryItemAdd,
    DeliveryItemResponse, DeliveryItemUpdate, DeliveryListResponse,
    DeliveryResponse, DeliveryRouteCreate, DeliveryRouteDetailResponse,
    DeliveryRouteListResponse, DeliveryRouteOptimizeRequest,
    DeliveryRouteReorderRequest, DeliveryRouteResponse, DeliveryRouteStatusUpdate, DeliveryRouteUpdate,
    DeliveryStatusUpdate, DeliveryUpdate
)
from ...services.home_delivery_service import (
    DeliveryRouteService, DeliveryService, HomeDeliveryFeedbackService
)
from .auth import get_current_user
from .dependencies import require_authenticated, require_staff

router = APIRouter(prefix="/home-delivery", tags=["home-delivery-deliveries"])


# ============================================================================
# Delivery Management (Staff)
# ============================================================================

@router.post("/staff/deliveries", response_model=DeliveryResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery(
    data: DeliveryCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new delivery for a home delivery patron."""
    try:
        delivery = await DeliveryService.create_delivery(
            db=db,
            enrollment_id=data.enrollment_id,
            scheduled_date=data.scheduled_date,
            scheduled_time_start=data.scheduled_time_start,
            scheduled_time_end=data.scheduled_time_end,
            route_id=data.route_id,
            staff_notes=data.staff_notes
        )

        # Reload with relationships
        result = await db.execute(
            select(Delivery)
            .options(
                joinedload(Delivery.enrollment).joinedload(HomeDeliveryEnrollment.patron),
                joinedload(Delivery.route)
            )
            .where(Delivery.id == delivery.id)
        )
        delivery = result.scalar_one()

        return _build_delivery_response(delivery)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/staff/deliveries", response_model=DeliveryListResponse)
async def list_deliveries(
    status: Optional[DeliveryStatus] = Query(None),
    enrollment_id: Optional[int] = Query(None),
    route_id: Optional[int] = Query(None),
    scheduled_from: Optional[date] = Query(None),
    scheduled_to: Optional[date] = Query(None),
    needs_items: bool = Query(False, description="Filter deliveries that need items selected"),
    needs_packing: bool = Query(False, description="Filter deliveries ready to pack"),
    search: Optional[str] = Query(None, description="Search by patron name or card"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all deliveries with filtering options."""
    query = (
        select(Delivery)
        .options(
            joinedload(Delivery.enrollment).joinedload(HomeDeliveryEnrollment.patron),
            joinedload(Delivery.route),
            selectinload(Delivery.feedback)
        )
    )
    count_query = select(func.count(Delivery.id))

    if status:
        query = query.where(Delivery.status == status)
        count_query = count_query.where(Delivery.status == status)

    if enrollment_id:
        query = query.where(Delivery.enrollment_id == enrollment_id)
        count_query = count_query.where(Delivery.enrollment_id == enrollment_id)

    if route_id:
        query = query.where(Delivery.route_id == route_id)
        count_query = count_query.where(Delivery.route_id == route_id)

    if scheduled_from:
        query = query.where(Delivery.scheduled_date >= scheduled_from)
        count_query = count_query.where(Delivery.scheduled_date >= scheduled_from)

    if scheduled_to:
        query = query.where(Delivery.scheduled_date <= scheduled_to)
        count_query = count_query.where(Delivery.scheduled_date <= scheduled_to)

    if needs_items:
        query = query.where(Delivery.status == DeliveryStatus.scheduled)
        count_query = count_query.where(Delivery.status == DeliveryStatus.scheduled)

    if needs_packing:
        query = query.where(Delivery.status == DeliveryStatus.items_selected)
        count_query = count_query.where(Delivery.status == DeliveryStatus.items_selected)

    if search:
        safe_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = (
            query.join(HomeDeliveryEnrollment, Delivery.enrollment_id == HomeDeliveryEnrollment.id)
            .join(User, HomeDeliveryEnrollment.patron_id == User.id)
            .where(
                or_(
                    User.library_card.ilike(f"%{safe_search}%"),
                    *([name_search_clause(search)] if name_search_clause(search) is not None else []),
                )
            )
        )
        count_query = (
            count_query.join(HomeDeliveryEnrollment, Delivery.enrollment_id == HomeDeliveryEnrollment.id)
            .join(User, HomeDeliveryEnrollment.patron_id == User.id)
            .where(
                or_(
                    User.library_card.ilike(f"%{safe_search}%"),
                    *([name_search_clause(search)] if name_search_clause(search) is not None else []),
                )
            )
        )

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Delivery.scheduled_date.asc()).limit(limit).offset(offset)
    result = await db.execute(query)
    deliveries = result.unique().scalars().all()

    return DeliveryListResponse(
        deliveries=[_build_delivery_response(d) for d in deliveries],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/staff/deliveries/{delivery_id}", response_model=DeliveryDetailResponse)
async def get_delivery(
    delivery_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific delivery with items."""
    result = await db.execute(
        select(Delivery)
        .options(
            joinedload(Delivery.enrollment).joinedload(HomeDeliveryEnrollment.patron),
            joinedload(Delivery.route),
            selectinload(Delivery.items),
            selectinload(Delivery.feedback)
        )
        .where(Delivery.id == delivery_id)
    )
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")

    return _build_delivery_detail_response(delivery)


@router.patch("/staff/deliveries/{delivery_id}", response_model=DeliveryResponse)
async def update_delivery(
    delivery_id: int,
    data: DeliveryUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update delivery details."""
    delivery = await get_or_404(db, Delivery, delivery_id, "Delivery not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(delivery, key, value)

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Delivery)
        .options(
            joinedload(Delivery.enrollment).joinedload(HomeDeliveryEnrollment.patron),
            joinedload(Delivery.route)
        )
        .where(Delivery.id == delivery_id)
    )
    delivery = result.scalar_one()

    return _build_delivery_response(delivery)


@router.post("/staff/deliveries/{delivery_id}/status", response_model=DeliveryResponse)
async def update_delivery_status(
    delivery_id: int,
    data: DeliveryStatusUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update delivery status (pack, dispatch, deliver, etc.)."""
    try:
        delivery = await DeliveryService.update_delivery_status(
            db=db,
            delivery_id=delivery_id,
            status=data.status,
            staff_id=staff_user.id,
            volunteer_notes=data.volunteer_notes,
            delivery_signature=data.delivery_signature,
            delivery_photo=data.delivery_photo,
            failure_reason=data.failure_reason,
            reschedule_date=data.reschedule_date
        )

        # If delivered, trigger checkout
        if data.status == DeliveryStatus.delivered:
            await DeliveryService.checkout_delivery_items(db=db, delivery_id=delivery_id)

        # Reload with relationships
        result = await db.execute(
            select(Delivery)
            .options(
                joinedload(Delivery.enrollment).joinedload(HomeDeliveryEnrollment.patron),
                joinedload(Delivery.route)
            )
            .where(Delivery.id == delivery.id)
        )
        delivery = result.scalar_one()

        return _build_delivery_response(delivery)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============================================================================
# Item Selection for Deliveries
# ============================================================================

@router.post("/staff/deliveries/{delivery_id}/items", response_model=DeliveryItemResponse, status_code=status.HTTP_201_CREATED)
async def add_item_to_delivery(
    delivery_id: int,
    data: DeliveryItemAdd,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Add an item to a delivery."""
    try:
        item = await DeliveryService.add_item_to_delivery(
            db=db,
            delivery_id=delivery_id,
            item_id=data.item_id,
            item_copy_id=data.item_copy_id,
            selected_by_id=staff_user.id,
            selection_reason=data.selection_reason,
            patron_requested=data.patron_requested
        )

        return DeliveryItemResponse.model_validate(item)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/staff/deliveries/{delivery_id}/items", response_model=list[DeliveryItemResponse])
async def get_delivery_items(
    delivery_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all items for a delivery."""
    result = await db.execute(
        select(DeliveryItem)
        .where(DeliveryItem.delivery_id == delivery_id)
        .order_by(DeliveryItem.id)
    )
    items = result.scalars().all()

    return [DeliveryItemResponse.model_validate(item) for item in items]


@router.patch("/staff/deliveries/{delivery_id}/items/{item_id}", response_model=DeliveryItemResponse)
async def update_delivery_item(
    delivery_id: int,
    item_id: int,
    data: DeliveryItemUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a delivery item status."""
    result = await db.execute(
        select(DeliveryItem)
        .where(
            DeliveryItem.id == item_id,
            DeliveryItem.delivery_id == delivery_id
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery item not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    if data.status == DeliveryItemStatus.returned:
        item.returned_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(item)

    return DeliveryItemResponse.model_validate(item)


@router.delete("/staff/deliveries/{delivery_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item_from_delivery(
    delivery_id: int,
    item_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Remove an item from a delivery."""
    result = await db.execute(
        select(DeliveryItem)
        .where(
            DeliveryItem.id == item_id,
            DeliveryItem.delivery_id == delivery_id
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery item not found")

    if item.status not in [DeliveryItemStatus.pending, DeliveryItemStatus.selected]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove item in current status")

    # Update delivery count
    delivery_result = await db.execute(
        select(Delivery).where(Delivery.id == delivery_id)
    )
    delivery = delivery_result.scalar_one()
    delivery.items_count = max(0, (delivery.items_count or 0) - 1)

    await db.delete(item)
    await db.commit()

    return None


# ============================================================================
# Route Management
# ============================================================================

@router.post("/staff/routes", response_model=DeliveryRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_route(
    data: DeliveryRouteCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new delivery route."""
    route = await DeliveryRouteService.create_route(
        db=db,
        name=data.name,
        date=data.date,
        created_by_id=staff_user.id,
        volunteer_id=data.volunteer_id,
        planned_start_time=data.planned_start_time,
        planned_end_time=data.planned_end_time,
        notes=data.notes
    )

    return _build_route_response(route)


@router.get("/staff/routes", response_model=DeliveryRouteListResponse)
async def list_routes(
    status: Optional[RouteStatus] = Query(None),
    volunteer_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all delivery routes."""
    query = (
        select(DeliveryRoute)
        .options(joinedload(DeliveryRoute.volunteer).joinedload(DeliveryVolunteer.user))
    )
    count_query = select(func.count(DeliveryRoute.id))

    if status:
        query = query.where(DeliveryRoute.status == status)
        count_query = count_query.where(DeliveryRoute.status == status)

    if volunteer_id:
        query = query.where(DeliveryRoute.volunteer_id == volunteer_id)
        count_query = count_query.where(DeliveryRoute.volunteer_id == volunteer_id)

    if date_from:
        query = query.where(DeliveryRoute.date >= date_from)
        count_query = count_query.where(DeliveryRoute.date >= date_from)

    if date_to:
        query = query.where(DeliveryRoute.date <= date_to)
        count_query = count_query.where(DeliveryRoute.date <= date_to)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(DeliveryRoute.date.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    routes = result.unique().scalars().all()

    return DeliveryRouteListResponse(
        routes=[_build_route_response(r) for r in routes],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/staff/routes/{route_id}", response_model=DeliveryRouteDetailResponse)
async def get_route(
    route_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific route with deliveries."""
    result = await db.execute(
        select(DeliveryRoute)
        .options(
            joinedload(DeliveryRoute.volunteer).joinedload(DeliveryVolunteer.user),
            selectinload(DeliveryRoute.deliveries).joinedload(Delivery.enrollment).joinedload(HomeDeliveryEnrollment.patron)
        )
        .where(DeliveryRoute.id == route_id)
    )
    route = result.scalar_one_or_none()

    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")

    return _build_route_detail_response(route)


@router.patch("/staff/routes/{route_id}", response_model=DeliveryRouteResponse)
async def update_route(
    route_id: int,
    data: DeliveryRouteUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update route details."""
    route = await get_or_404(db, DeliveryRoute, route_id, "Route not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(route, key, value)

    await db.commit()

    # Reload with volunteer
    result = await db.execute(
        select(DeliveryRoute)
        .options(joinedload(DeliveryRoute.volunteer).joinedload(DeliveryVolunteer.user))
        .where(DeliveryRoute.id == route_id)
    )
    route = result.scalar_one()

    return _build_route_response(route)


@router.put("/staff/routes/{route_id}/order", response_model=DeliveryRouteResponse)
async def reorder_route_stops(
    route_id: int,
    data: DeliveryRouteReorderRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Persist a manual stop order for a route.

    Accepts a complete permutation of the route current delivery IDs.
    Updates both optimized_order on the route and route_order on each
    assigned delivery so the on-reload sort fallback stays consistent.
    """
    result = await db.execute(
        select(DeliveryRoute)
        .options(selectinload(DeliveryRoute.deliveries))
        .where(DeliveryRoute.id == route_id)
    )
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")

    actual_ids = {d.id for d in route.deliveries}
    requested_ids = set(data.optimized_order)

    if len(data.optimized_order) != len(requested_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="optimized_order contains duplicate delivery IDs",
        )
    if requested_ids != actual_ids:
        missing = actual_ids - requested_ids
        extra = requested_ids - actual_ids
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "optimized_order must match the route stops exactly"
                f" (missing: {sorted(missing)}, extra: {sorted(extra)})"
            ),
        )

    order_index = {delivery_id: i + 1 for i, delivery_id in enumerate(data.optimized_order)}
    for delivery in route.deliveries:
        delivery.route_order = order_index[delivery.id]
    route.optimized_order = list(data.optimized_order)

    await db.commit()

    result = await db.execute(
        select(DeliveryRoute)
        .options(joinedload(DeliveryRoute.volunteer).joinedload(DeliveryVolunteer.user))
        .where(DeliveryRoute.id == route_id)
    )
    route = result.scalar_one()
    return _build_route_response(route)


@router.post("/staff/routes/{route_id}/assign-deliveries", response_model=DeliveryRouteResponse)
async def assign_deliveries_to_route(
    route_id: int,
    delivery_ids: list[int],
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Assign deliveries to a route."""
    try:
        route = await DeliveryRouteService.assign_deliveries_to_route(
            db=db,
            route_id=route_id,
            delivery_ids=delivery_ids
        )

        # Reload with volunteer
        result = await db.execute(
            select(DeliveryRoute)
            .options(joinedload(DeliveryRoute.volunteer).joinedload(DeliveryVolunteer.user))
            .where(DeliveryRoute.id == route_id)
        )
        route = result.scalar_one()

        return _build_route_response(route)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/staff/routes/{route_id}/optimize", response_model=DeliveryRouteResponse)
async def optimize_route(
    route_id: int,
    data: Optional[DeliveryRouteOptimizeRequest] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Optimize delivery order for a route."""
    try:
        route = await DeliveryRouteService.optimize_route(
            db=db,
            route_id=route_id,
            start_location=data.start_location if data else None
        )

        # Reload with volunteer
        result = await db.execute(
            select(DeliveryRoute)
            .options(joinedload(DeliveryRoute.volunteer).joinedload(DeliveryVolunteer.user))
            .where(DeliveryRoute.id == route_id)
        )
        route = result.scalar_one()

        return _build_route_response(route)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/staff/routes/{route_id}/status", response_model=DeliveryRouteResponse)
async def update_route_status(
    route_id: int,
    data: DeliveryRouteStatusUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update route status (start, complete, cancel)."""
    try:
        if data.status == RouteStatus.in_progress:
            route = await DeliveryRouteService.start_route(db=db, route_id=route_id)
        elif data.status == RouteStatus.completed:
            # Get route to find volunteer
            result = await db.execute(
                select(DeliveryRoute).where(DeliveryRoute.id == route_id)
            )
            route = result.scalar_one_or_none()
            if not route:
                raise ValueError("Route not found")

            route = await DeliveryRouteService.complete_route(
                db=db,
                route_id=route_id,
                volunteer_id=route.volunteer_id or staff_user.id
            )
        else:
            route = await get_or_404(db, DeliveryRoute, route_id, "Route not found")

            route.status = data.status
            if data.actual_start_time:
                route.actual_start_time = data.actual_start_time
            if data.actual_end_time:
                route.actual_end_time = data.actual_end_time

            await db.commit()

        # Reload with volunteer
        result = await db.execute(
            select(DeliveryRoute)
            .options(joinedload(DeliveryRoute.volunteer).joinedload(DeliveryVolunteer.user))
            .where(DeliveryRoute.id == route_id)
        )
        route = result.scalar_one()

        return _build_route_response(route)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============================================================================
# Patron-Facing Delivery Tracking
# ============================================================================

@router.get("/deliveries/my", response_model=DeliveryListResponse)
async def get_my_deliveries(
    status: Optional[DeliveryStatus] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's deliveries."""
    # Get patron's enrollment
    enrollment_result = await db.execute(
        select(HomeDeliveryEnrollment)
        .where(HomeDeliveryEnrollment.patron_id == current_user.id)
    )
    enrollment = enrollment_result.scalar_one_or_none()

    if not enrollment:
        return DeliveryListResponse(deliveries=[], total=0, limit=limit, offset=offset)

    query = (
        select(Delivery)
        .options(selectinload(Delivery.feedback))
        .where(Delivery.enrollment_id == enrollment.id)
    )
    count_query = select(func.count(Delivery.id)).where(
        Delivery.enrollment_id == enrollment.id
    )

    if status:
        query = query.where(Delivery.status == status)
        count_query = count_query.where(Delivery.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Delivery.scheduled_date.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    deliveries = result.unique().scalars().all()

    return DeliveryListResponse(
        deliveries=[
            DeliveryResponse(
                id=d.id,
                enrollment_id=d.enrollment_id,
                patron_id=current_user.id,
                patron_name=current_user.full_name,
                patron_library_card=current_user.library_card,
                route_id=d.route_id,
                status=d.status,
                scheduled_date=d.scheduled_date,
                scheduled_time_start=d.scheduled_time_start,
                scheduled_time_end=d.scheduled_time_end,
                delivery_address=d.delivery_address,
                delivery_instructions=d.delivery_instructions,
                packed_at=d.packed_at,
                out_for_delivery_at=d.out_for_delivery_at,
                delivered_at=d.delivered_at,
                delivery_failed_at=d.delivery_failed_at,
                failure_reason=d.failure_reason,
                reschedule_date=d.reschedule_date,
                pickup_requested=d.pickup_requested,
                picked_up_at=d.picked_up_at,
                items_count=d.items_count,
                items_delivered=d.items_delivered,
                items_picked_up=d.items_picked_up,
                patron_notes=d.patron_notes,
                has_feedback=d.feedback is not None,
                created_at=d.created_at
            )
            for d in deliveries
        ],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/deliveries/my/upcoming")
async def get_my_upcoming_deliveries(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get upcoming deliveries for mobile dashboard."""
    # Get patron's enrollment
    enrollment_result = await db.execute(
        select(HomeDeliveryEnrollment)
        .where(HomeDeliveryEnrollment.patron_id == current_user.id)
    )
    enrollment = enrollment_result.scalar_one_or_none()

    if not enrollment:
        return {"upcoming": [], "next_delivery": None}

    # Get upcoming deliveries (scheduled in the future)
    from datetime import date as date_type
    today = date_type.today()

    result = await db.execute(
        select(Delivery)
        .options(joinedload(Delivery.route))
        .where(
            Delivery.enrollment_id == enrollment.id,
            Delivery.scheduled_date >= today,
            Delivery.status.in_([
                DeliveryStatus.scheduled,
                DeliveryStatus.items_selected,
                DeliveryStatus.packed,
                DeliveryStatus.out_for_delivery
            ])
        )
        .order_by(Delivery.scheduled_date.asc())
        .limit(5)
    )
    deliveries = result.unique().scalars().all()

    upcoming = []
    for d in deliveries:
        time_window = None
        if d.scheduled_time_start and d.scheduled_time_end:
            time_window = f"{d.scheduled_time_start} - {d.scheduled_time_end}"

        upcoming.append({
            "id": d.id,
            "scheduled_date": d.scheduled_date,
            "time_window": time_window,
            "status": d.status,
            "items_count": d.items_count or 0,
            "is_out_for_delivery": d.status == DeliveryStatus.out_for_delivery
        })

    return {
        "upcoming": upcoming,
        "next_delivery": upcoming[0] if upcoming else None,
        "enrollment_status": enrollment.status,
        "total_deliveries": enrollment.total_deliveries
    }


@router.get("/deliveries/my/{delivery_id}", response_model=DeliveryDetailResponse)
async def get_my_delivery(
    delivery_id: int,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific delivery (patron-facing)."""
    # Get patron's enrollment
    enrollment_result = await db.execute(
        select(HomeDeliveryEnrollment)
        .where(HomeDeliveryEnrollment.patron_id == current_user.id)
    )
    enrollment = enrollment_result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")

    result = await db.execute(
        select(Delivery)
        .options(
            selectinload(Delivery.items),
            selectinload(Delivery.feedback)
        )
        .where(
            Delivery.id == delivery_id,
            Delivery.enrollment_id == enrollment.id
        )
    )
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")

    # Build response (hide some staff-only fields)
    return DeliveryDetailResponse(
        id=delivery.id,
        enrollment_id=delivery.enrollment_id,
        patron_id=current_user.id,
        patron_name=current_user.full_name,
        patron_library_card=current_user.library_card,
        route_id=delivery.route_id,
        status=delivery.status,
        scheduled_date=delivery.scheduled_date,
        scheduled_time_start=delivery.scheduled_time_start,
        scheduled_time_end=delivery.scheduled_time_end,
        delivery_address=delivery.delivery_address,
        delivery_instructions=delivery.delivery_instructions,
        packed_at=delivery.packed_at,
        out_for_delivery_at=delivery.out_for_delivery_at,
        delivered_at=delivery.delivered_at,
        delivery_failed_at=delivery.delivery_failed_at,
        failure_reason=delivery.failure_reason,
        reschedule_date=delivery.reschedule_date,
        pickup_requested=delivery.pickup_requested,
        picked_up_at=delivery.picked_up_at,
        items_count=delivery.items_count,
        items_delivered=delivery.items_delivered,
        items_picked_up=delivery.items_picked_up,
        patron_notes=delivery.patron_notes,
        has_feedback=delivery.feedback is not None,
        created_at=delivery.created_at,
        items=[DeliveryItemResponse.model_validate(item) for item in delivery.items],
        feedback=DeliveryFeedbackResponse.model_validate(delivery.feedback) if delivery.feedback else None
    )


# ============================================================================
# Patron Self-Service Delivery Management
# ============================================================================

@router.post("/deliveries/my/{delivery_id}/reschedule", response_model=DeliveryResponse)
async def reschedule_my_delivery(
    delivery_id: int,
    new_date: date = Query(..., description="New delivery date"),
    reason: Optional[str] = Query(None, max_length=500, description="Reason for rescheduling"),
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Request to reschedule a delivery (patron-facing)."""
    # Get patron's enrollment
    enrollment_result = await db.execute(
        select(HomeDeliveryEnrollment)
        .where(HomeDeliveryEnrollment.patron_id == current_user.id)
    )
    enrollment = enrollment_result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No enrollment found")

    # Get delivery
    result = await db.execute(
        select(Delivery)
        .where(
            Delivery.id == delivery_id,
            Delivery.enrollment_id == enrollment.id
        )
    )
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")

    # Only allow rescheduling deliveries that haven't been packed yet
    if delivery.status not in [DeliveryStatus.scheduled, DeliveryStatus.items_selected]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reschedule delivery in {delivery.status} status"
        )

    # Validate new date is in the future
    from datetime import date as date_type
    if new_date <= date_type.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New date must be in the future"
        )

    # Update delivery
    delivery.scheduled_date = new_date
    if reason:
        delivery.patron_notes = f"Rescheduled by patron: {reason}"

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Delivery)
        .options(
            joinedload(Delivery.enrollment).joinedload(HomeDeliveryEnrollment.patron),
            joinedload(Delivery.route)
        )
        .where(Delivery.id == delivery.id)
    )
    delivery = result.scalar_one()

    return _build_delivery_response(delivery)


@router.get("/deliveries/my/tracking/{delivery_id}")
async def track_my_delivery(
    delivery_id: int,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get mobile-friendly tracking info for a delivery."""
    # Get patron's enrollment
    enrollment_result = await db.execute(
        select(HomeDeliveryEnrollment)
        .where(HomeDeliveryEnrollment.patron_id == current_user.id)
    )
    enrollment = enrollment_result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No enrollment found")

    # Get delivery with route and volunteer info
    result = await db.execute(
        select(Delivery)
        .options(
            joinedload(Delivery.route).joinedload(DeliveryRoute.volunteer).joinedload(DeliveryVolunteer.user),
            selectinload(Delivery.items)
        )
        .where(
            Delivery.id == delivery_id,
            Delivery.enrollment_id == enrollment.id
        )
    )
    delivery = result.unique().scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")

    # Build timeline
    timeline = _build_delivery_timeline(delivery)

    # Format time window
    time_window = None
    if delivery.scheduled_time_start and delivery.scheduled_time_end:
        time_window = f"{delivery.scheduled_time_start} - {delivery.scheduled_time_end}"
    elif delivery.scheduled_time_start:
        time_window = f"after {delivery.scheduled_time_start}"
    elif delivery.scheduled_time_end:
        time_window = f"before {delivery.scheduled_time_end}"

    # Get volunteer name if route is assigned
    volunteer_name = None
    if delivery.route and delivery.route.volunteer and delivery.route.volunteer.user:
        volunteer_name = delivery.route.volunteer.user.first_name

    # Status display mapping
    status_display_map = {
        DeliveryStatus.scheduled: "Scheduled",
        DeliveryStatus.items_selected: "Items Being Selected",
        DeliveryStatus.packed: "Ready for Delivery",
        DeliveryStatus.out_for_delivery: "Out for Delivery",
        DeliveryStatus.delivered: "Delivered",
        DeliveryStatus.delivery_failed: "Delivery Unsuccessful",
        DeliveryStatus.picked_up: "Items Picked Up",
        DeliveryStatus.cancelled: "Cancelled"
    }

    return {
        "delivery_id": delivery.id,
        "status": delivery.status,
        "status_display": status_display_map.get(delivery.status, str(delivery.status)),
        "scheduled_date": delivery.scheduled_date,
        "time_window": time_window,
        "delivery_address": delivery.delivery_address,
        "items_count": delivery.items_count or 0,
        "estimated_arrival": time_window,  # Could be enhanced with real-time tracking
        "volunteer_name": volunteer_name,
        "is_out_for_delivery": delivery.status == DeliveryStatus.out_for_delivery,
        "can_reschedule": delivery.status in [DeliveryStatus.scheduled, DeliveryStatus.items_selected],
        "timeline": timeline
    }


def _build_delivery_timeline(delivery: Delivery) -> list[dict]:
    timeline = []

    # Scheduled
    timeline.append({
        "event": "scheduled",
        "timestamp": delivery.created_at,
        "description": f"Delivery scheduled for {delivery.scheduled_date}",
        "completed": True
    })

    # Items selected
    if delivery.status != DeliveryStatus.scheduled:
        timeline.append({
            "event": "items_selected",
            "timestamp": None,
            "description": f"{delivery.items_count or 0} items selected",
            "completed": delivery.status not in [DeliveryStatus.scheduled]
        })

    # Packed
    timeline.append({
        "event": "packed",
        "timestamp": delivery.packed_at,
        "description": "Items packed and ready",
        "completed": delivery.packed_at is not None
    })

    # Out for delivery
    timeline.append({
        "event": "out_for_delivery",
        "timestamp": delivery.out_for_delivery_at,
        "description": "Out for delivery",
        "completed": delivery.out_for_delivery_at is not None
    })

    # Delivered or failed
    if delivery.status == DeliveryStatus.delivered:
        timeline.append({
            "event": "delivered",
            "timestamp": delivery.delivered_at,
            "description": "Delivered successfully",
            "completed": True
        })
    elif delivery.status == DeliveryStatus.delivery_failed:
        timeline.append({
            "event": "delivery_failed",
            "timestamp": delivery.delivery_failed_at,
            "description": f"Delivery unsuccessful: {delivery.failure_reason or 'Unknown reason'}",
            "completed": True
        })
    else:
        timeline.append({
            "event": "delivered",
            "timestamp": None,
            "description": "Awaiting delivery",
            "completed": False
        })

    return timeline


# ============================================================================
# Patron Feedback
# ============================================================================

@router.post("/deliveries/{delivery_id}/feedback", response_model=DeliveryFeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    delivery_id: int,
    data: DeliveryFeedbackCreate,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback for a delivery (patron-facing)."""
    # Verify patron owns this delivery
    enrollment_result = await db.execute(
        select(HomeDeliveryEnrollment)
        .where(HomeDeliveryEnrollment.patron_id == current_user.id)
    )
    enrollment = enrollment_result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")

    delivery_result = await db.execute(
        select(Delivery)
        .where(
            Delivery.id == delivery_id,
            Delivery.enrollment_id == enrollment.id
        )
    )
    if not delivery_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")

    try:
        feedback = await HomeDeliveryFeedbackService.submit_feedback(
            db=db,
            delivery_id=delivery_id,
            data=data.model_dump()
        )

        return DeliveryFeedbackResponse.model_validate(feedback)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/staff/feedback/requiring-followup", response_model=list[DeliveryFeedbackResponse])
async def get_feedback_requiring_followup(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all feedback requiring follow-up."""
    result = await db.execute(
        select(DeliveryFeedback)
        .options(joinedload(DeliveryFeedback.follow_up_by))
        .where(
            DeliveryFeedback.requires_follow_up == True,
            DeliveryFeedback.follow_up_completed == False
        )
        .order_by(DeliveryFeedback.submitted_at.asc())
    )
    feedbacks = result.unique().scalars().all()

    return [
        DeliveryFeedbackResponse(
            **{k: v for k, v in f.__dict__.items() if not k.startswith("_")},
            follow_up_by_name=f.follow_up_by.full_name if f.follow_up_by else None
        )
        for f in feedbacks
    ]


@router.post("/staff/feedback/{feedback_id}/follow-up", response_model=DeliveryFeedbackResponse)
async def complete_feedback_followup(
    feedback_id: int,
    data: DeliveryFeedbackFollowUp,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Complete follow-up for feedback."""
    try:
        feedback = await HomeDeliveryFeedbackService.complete_follow_up(
            db=db,
            feedback_id=feedback_id,
            staff_id=staff_user.id,
            notes=data.follow_up_notes
        )

        return DeliveryFeedbackResponse(
            **{k: v for k, v in feedback.__dict__.items() if not k.startswith("_")},
            follow_up_by_name=staff_user.full_name
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============================================================================
# Helper Functions
# ============================================================================

def _build_delivery_response(delivery: Delivery) -> DeliveryResponse:
    from sqlalchemy import inspect as sa_inspect
    patron = delivery.enrollment.patron if delivery.enrollment else None
    route = delivery.route

    # Check if feedback is loaded without triggering lazy load
    insp = sa_inspect(delivery)
    has_feedback = False
    if 'feedback' in insp.dict:
        has_feedback = delivery.feedback is not None

    return DeliveryResponse(
        id=delivery.id,
        enrollment_id=delivery.enrollment_id,
        patron_id=patron.id if patron else None,
        patron_name=patron.full_name if patron else None,
        patron_library_card=patron.library_card if patron else None,
        route_id=delivery.route_id,
        route_name=route.name if route else None,
        route_order=delivery.route_order,
        status=delivery.status,
        scheduled_date=delivery.scheduled_date,
        scheduled_time_start=delivery.scheduled_time_start,
        scheduled_time_end=delivery.scheduled_time_end,
        delivery_address=delivery.delivery_address,
        delivery_instructions=delivery.delivery_instructions,
        packed_at=delivery.packed_at,
        out_for_delivery_at=delivery.out_for_delivery_at,
        delivered_at=delivery.delivered_at,
        delivery_failed_at=delivery.delivery_failed_at,
        failure_reason=delivery.failure_reason,
        reschedule_date=delivery.reschedule_date,
        pickup_requested=delivery.pickup_requested,
        picked_up_at=delivery.picked_up_at,
        items_count=delivery.items_count or 0,
        items_delivered=delivery.items_delivered or 0,
        items_picked_up=delivery.items_picked_up or 0,
        staff_notes=delivery.staff_notes,
        patron_notes=delivery.patron_notes,
        volunteer_notes=delivery.volunteer_notes,
        has_feedback=has_feedback,
        created_at=delivery.created_at
    )


def _build_delivery_detail_response(delivery: Delivery) -> DeliveryDetailResponse:
    base = _build_delivery_response(delivery)

    items = [DeliveryItemResponse.model_validate(item) for item in delivery.items] if delivery.items else []
    feedback = None
    if delivery.feedback:
        feedback = DeliveryFeedbackResponse.model_validate(delivery.feedback)

    return DeliveryDetailResponse(
        **base.model_dump(),
        items=items,
        feedback=feedback
    )


def _build_route_response(route: DeliveryRoute) -> DeliveryRouteResponse:
    volunteer_name = None
    if route.volunteer and route.volunteer.user:
        volunteer_name = route.volunteer.user.full_name

    return DeliveryRouteResponse(
        id=route.id,
        name=route.name,
        date=route.date,
        status=route.status,
        volunteer_id=route.volunteer_id,
        volunteer_name=volunteer_name,
        estimated_duration_minutes=route.estimated_duration_minutes,
        estimated_distance_miles=route.estimated_distance_miles,
        optimized_order=route.optimized_order or [],
        planned_start_time=route.planned_start_time,
        planned_end_time=route.planned_end_time,
        actual_start_time=route.actual_start_time,
        actual_end_time=route.actual_end_time,
        total_stops=route.total_stops,
        completed_stops=route.completed_stops,
        total_items=route.total_items,
        notes=route.notes,
        created_by_id=route.created_by_id,
        created_at=route.created_at
    )


def _build_route_detail_response(route: DeliveryRoute) -> DeliveryRouteDetailResponse:
    base = _build_route_response(route)

    deliveries = []
    if route.deliveries:
        for d in sorted(route.deliveries, key=lambda x: x.route_order or 0):
            deliveries.append(_build_delivery_response(d))

    return DeliveryRouteDetailResponse(
        **base.model_dump(),
        deliveries=deliveries
    )



