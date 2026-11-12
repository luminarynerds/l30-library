# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Acquisition - Vendor Management API Endpoints

Provides endpoints for:
- Vendor CRUD operations
- Vendor search
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.acquisition import Vendor
from ....models.user import User, UserRole
from ....schemas.acquisition import VendorCreate, VendorListResponse, VendorResponse, VendorUpdate
from ..auth import get_current_user
from ..dependencies import require_staff

router = APIRouter(prefix="/acquisition", tags=["acquisition-vendors"])



@router.get("/vendors", response_model=VendorListResponse)
async def list_vendors(
    q: str | None = Query(None),
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List vendors"""
    await require_staff(current_user)

    query = select(Vendor)
    count_query = select(func.count(Vendor.id))

    if q:
        search = f"%{q}%"
        search_filter = or_(
            Vendor.name.ilike(search),
            Vendor.contact_name.ilike(search),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if is_active is not None:
        query = query.where(Vendor.is_active == is_active)
        count_query = count_query.where(Vendor.is_active == is_active)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Vendor.name)

    result = await db.execute(query)
    vendors = result.scalars().all()

    return VendorListResponse(
        items=[VendorResponse.model_validate(v) for v in vendors],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/vendors", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    vendor_in: VendorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a vendor"""
    await require_staff(current_user)

    vendor = Vendor(**vendor_in.model_dump())
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)
    return vendor


@router.get("/vendors/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get vendor details"""
    await require_staff(current_user)

    vendor = await get_or_404(db, Vendor, vendor_id, "Vendor not found")
    return vendor


@router.patch("/vendors/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: int,
    vendor_in: VendorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a vendor"""
    await require_staff(current_user)

    vendor = await get_or_404(db, Vendor, vendor_id, "Vendor not found")

    for field, value in vendor_in.model_dump(exclude_unset=True).items():
        setattr(vendor, field, value)

    await db.commit()
    await db.refresh(vendor)
    return vendor


@router.get("/vendors/{vendor_id}/serial-subscriptions")
async def list_vendor_serial_subscriptions(
    vendor_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List serial subscriptions for a vendor."""
    await require_staff(current_user)
    from ....models.serial import SerialSubscription, SerialTitle

    await get_or_404(db, Vendor, vendor_id, "Vendor not found")

    count_result = await db.execute(
        select(func.count(SerialSubscription.id))
        .where(SerialSubscription.vendor_id == vendor_id)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * per_page
    result = await db.execute(
        select(
            SerialSubscription,
            SerialTitle.title.label("serial_title_name"),
        )
        .outerjoin(SerialTitle, SerialTitle.id == SerialSubscription.serial_title_id)
        .where(SerialSubscription.vendor_id == vendor_id)
        .order_by(SerialSubscription.end_date.desc())
        .offset(offset)
        .limit(per_page)
    )
    rows = result.all()

    items = []
    for row in rows:
        sub = row[0]
        items.append({
            "id": sub.id,
            "serial_title_id": sub.serial_title_id,
            "serial_title_name": row.serial_title_name,
            "subscription_number": sub.subscription_number,
            "renewal_status": sub.renewal_status,
            "start_date": str(sub.start_date) if sub.start_date else None,
            "end_date": str(sub.end_date) if sub.end_date else None,
            "cost": float(sub.cost) if sub.cost else None,
            "copies_ordered": sub.copies_ordered,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/vendors/{vendor_id}/summary")
async def get_vendor_summary(
    vendor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consolidated vendor view with PO and serial subscription stats."""
    await require_staff(current_user)
    from ....models.serial import SerialSubscription, SubscriptionRenewalStatus
    from ....models.acquisition import PurchaseOrder

    vendor = await get_or_404(db, Vendor, vendor_id, "Vendor not found")

    # PO stats
    po_result = await db.execute(
        select(
            func.count(PurchaseOrder.id).label("po_count"),
            func.coalesce(func.sum(PurchaseOrder.total_amount), 0).label("po_total"),
        ).where(PurchaseOrder.vendor_id == vendor_id)
    )
    po_row = po_result.one()

    # Serial subscription stats
    sub_result = await db.execute(
        select(
            func.count(SerialSubscription.id).label("sub_count"),
            func.count(SerialSubscription.id).filter(
                SerialSubscription.renewal_status.in_([
                    SubscriptionRenewalStatus.active.value,
                    SubscriptionRenewalStatus.pending_renewal.value,
                ])
            ).label("active_count"),
            func.coalesce(
                func.sum(SerialSubscription.cost).filter(
                    SerialSubscription.renewal_status.in_([
                        SubscriptionRenewalStatus.active.value,
                        SubscriptionRenewalStatus.pending_renewal.value,
                    ])
                ), 0
            ).label("annual_cost"),
        ).where(SerialSubscription.vendor_id == vendor_id)
    )
    sub_row = sub_result.one()

    return {
        "vendor": {
            "id": vendor.id,
            "name": vendor.name,
            "is_active": vendor.is_active,
        },
        "purchase_orders": {
            "count": po_row.po_count,
            "total_amount": float(po_row.po_total),
        },
        "serial_subscriptions": {
            "count": sub_row.sub_count,
            "active_count": sub_row.active_count,
            "annual_cost": float(sub_row.annual_cost),
        },
    }
