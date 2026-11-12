# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Donation Intake Workflow API Endpoints

Staff-facing:
- Log incoming book/material donations
- Review and accept/decline donations
- Process accepted donations into catalog
- View donation statistics and history
"""

from app.core.logging import get_logger
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.catalog import CatalogItem, CatalogingStatus
from ...models.donation import DonationRecord, DonationStatus
from ...models.inventory import AcquisitionSource, ItemCopy
from ...models.lifecycle import LifecycleEventType
from ...models.user import User
from ...schemas.donation import (
    DonationCreate,
    DonationProcessRequest,
    DonationResponse,
    DonationReviewRequest,
    DonationUpdate,
)
from .auth import get_current_user
from .dependencies import check_staff_access
from .lifecycle import create_lifecycle_event

logger = get_logger(__name__)

router = APIRouter(prefix="/donations", tags=["donations"])


# ============ Authorization ============


def _generate_barcode() -> str:
    return f"DON-{uuid.uuid4().hex[:8].upper()}"


def _donation_to_response(donation: DonationRecord) -> dict:
    data = {
        "id": donation.id,
        "donor_name": donation.donor_name,
        "donor_email": donation.donor_email,
        "donor_phone": donation.donor_phone,
        "donor_address": donation.donor_address,
        "is_anonymous": donation.is_anonymous,
        "tax_receipt_requested": donation.tax_receipt_requested,
        "tax_receipt_sent": donation.tax_receipt_sent,
        "title": donation.title,
        "author": donation.author,
        "isbn": donation.isbn,
        "material_type": donation.material_type,
        "quantity": donation.quantity,
        "condition_notes": donation.condition_notes,
        "estimated_value": donation.estimated_value,
        "status": str(donation.status) if donation.status else "pending",
        "received_date": donation.received_date,
        "received_by_id": donation.received_by_id,
        "received_by_name": (
            donation.received_by.full_name
            if donation.received_by else None
        ),
        "reviewed_by_id": donation.reviewed_by_id,
        "reviewed_by_name": (
            donation.reviewed_by.full_name
            if donation.reviewed_by else None
        ),
        "reviewed_at": donation.reviewed_at,
        "decline_reason": donation.decline_reason,
        "staff_notes": donation.staff_notes,
        "catalog_item_id": donation.catalog_item_id,
        "item_copy_id": donation.item_copy_id,
        "created_at": donation.created_at,
        "updated_at": donation.updated_at,
    }
    return data


def _load_options():
    return [
        selectinload(DonationRecord.received_by),
        selectinload(DonationRecord.reviewed_by),
    ]


# ============ Stats (must be before /{id} routes) ============


@router.get("/stats")
async def donation_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get donation counts grouped by status."""
    check_staff_access(current_user)

    result = await db.execute(
        select(DonationRecord.status, func.count(DonationRecord.id))
        .group_by(DonationRecord.status)
    )
    rows = result.all()
    counts = {s.value: 0 for s in DonationStatus}
    for row_status, count in rows:
        counts[row_status.value] = count

    total = sum(counts.values())
    return {"total": total, "by_status": counts}


# ============ List / Create ============


@router.get("", response_model=list[DonationResponse])
async def list_donations(
    status_filter: DonationStatus | None = Query(None, alias="status"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all donations with optional filters."""
    check_staff_access(current_user)

    query = select(DonationRecord).options(*_load_options())

    if status_filter:
        query = query.where(DonationRecord.status == status_filter)
    if date_from:
        query = query.where(DonationRecord.received_date >= date_from)
    if date_to:
        query = query.where(DonationRecord.received_date <= date_to)

    query = query.order_by(DonationRecord.created_at.desc())
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    donations = result.scalars().all()

    return [DonationResponse(**_donation_to_response(d)) for d in donations]


@router.post("", response_model=DonationResponse, status_code=status.HTTP_201_CREATED)
async def create_donation(
    body: DonationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Log a new incoming donation."""
    check_staff_access(current_user)

    donation = DonationRecord(
        donor_name=body.donor_name,
        donor_email=body.donor_email,
        donor_phone=body.donor_phone,
        donor_address=body.donor_address,
        is_anonymous=body.is_anonymous,
        tax_receipt_requested=body.tax_receipt_requested,
        title=body.title,
        author=body.author,
        isbn=body.isbn,
        material_type=body.material_type,
        quantity=body.quantity,
        condition_notes=body.condition_notes,
        estimated_value=body.estimated_value,
        received_date=body.received_date or date.today(),
        received_by_id=current_user.id,
        staff_notes=body.staff_notes,
        status=DonationStatus.PENDING,
    )
    db.add(donation)
    await db.commit()
    await db.refresh(donation, ["received_by", "reviewed_by"])

    return DonationResponse(**_donation_to_response(donation))


# ============ Single Donation ============


@router.get("/{donation_id}", response_model=DonationResponse)
async def get_donation(
    donation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single donation with full details."""
    check_staff_access(current_user)

    result = await db.execute(
        select(DonationRecord)
        .options(*_load_options())
        .where(DonationRecord.id == donation_id)
    )
    donation = result.scalar_one_or_none()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    return DonationResponse(**_donation_to_response(donation))


@router.patch("/{donation_id}", response_model=DonationResponse)
async def update_donation(
    donation_id: int,
    body: DonationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update donation details. Only allowed for PENDING or UNDER_REVIEW donations."""
    check_staff_access(current_user)

    result = await db.execute(
        select(DonationRecord)
        .options(*_load_options())
        .where(DonationRecord.id == donation_id)
    )
    donation = result.scalar_one_or_none()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    if donation.status not in [DonationStatus.PENDING, DonationStatus.UNDER_REVIEW]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update a donation with status '{donation.status}'",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(donation, field, value)

    await db.commit()
    await db.refresh(donation, ["received_by", "reviewed_by"])

    return DonationResponse(**_donation_to_response(donation))


# ============ Workflow Actions ============


@router.post("/{donation_id}/review", response_model=DonationResponse)
async def review_donation(
    donation_id: int,
    body: DonationReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accept or decline a donation."""
    check_staff_access(current_user)

    result = await db.execute(
        select(DonationRecord)
        .options(*_load_options())
        .where(DonationRecord.id == donation_id)
    )
    donation = result.scalar_one_or_none()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    if donation.status not in [DonationStatus.PENDING, DonationStatus.UNDER_REVIEW]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot review a donation with status '{donation.status}'",
        )

    now = datetime.now(timezone.utc)

    if body.action == "accept":
        donation.status = DonationStatus.ACCEPTED
    elif body.action == "decline":
        if not body.decline_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="decline_reason is required when declining",
            )
        donation.status = DonationStatus.DECLINED
        donation.decline_reason = body.decline_reason

    donation.reviewed_by_id = current_user.id
    donation.reviewed_at = now
    if body.staff_notes:
        donation.staff_notes = body.staff_notes

    await db.commit()
    await db.refresh(donation, ["received_by", "reviewed_by"])

    return DonationResponse(**_donation_to_response(donation))


@router.post("/{donation_id}/process", response_model=DonationResponse)
async def process_donation(
    donation_id: int,
    body: DonationProcessRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Process an accepted donation into the catalog.

    Creates a CatalogItem (if requested) and an ItemCopy with
    acquisition_source=DONATION, then fires a RECEIVED lifecycle event.
    """
    check_staff_access(current_user)

    result = await db.execute(
        select(DonationRecord)
        .options(*_load_options())
        .where(DonationRecord.id == donation_id)
    )
    donation = result.scalar_one_or_none()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    if donation.status != DonationStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only accepted donations can be processed (current: {donation.status})",
        )

    # Determine catalog item
    catalog_item_id = body.catalog_item_id

    if body.create_new_catalog_item:
        new_item = CatalogItem(
            title=donation.title or "Untitled Donation",
            author=donation.author,
            isbn=donation.isbn,
            cataloging_status=CatalogingStatus.UNCATALOGED,
        )
        db.add(new_item)
        await db.flush()
        catalog_item_id = new_item.id
    elif catalog_item_id:
        # Verify the catalog item exists
        cat_result = await db.execute(
            select(CatalogItem).where(CatalogItem.id == catalog_item_id)
        )
        if not cat_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Catalog item not found",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either catalog_item_id or create_new_catalog_item must be provided",
        )

    # Determine copy number
    existing_copies_result = await db.execute(
        select(ItemCopy)
        .where(ItemCopy.catalog_item_id == catalog_item_id)
        .with_for_update()
    )
    existing_copies = existing_copies_result.scalars().all()
    copy_number = len(existing_copies) + 1

    barcode = _generate_barcode()
    # Ensure barcode uniqueness
    barcode_check = await db.execute(select(ItemCopy).where(ItemCopy.barcode == barcode))
    if barcode_check.scalar_one_or_none():
        barcode = _generate_barcode()  # retry once

    copy = ItemCopy(
        catalog_item_id=catalog_item_id,
        barcode=barcode,
        copy_number=copy_number,
        acquisition_source=AcquisitionSource.DONATION,
        location=body.location,
    )
    db.add(copy)
    await db.flush()

    # Fire lifecycle event
    await create_lifecycle_event(
        db=db,
        item_copy_id=copy.id,
        event_type=LifecycleEventType.RECEIVED,
        description=f"Received via donation #{donation.id}",
        performed_by_id=current_user.id,
    )

    # Update donation record
    donation.status = DonationStatus.PROCESSED
    donation.catalog_item_id = catalog_item_id
    donation.item_copy_id = copy.id

    await db.commit()
    await db.refresh(donation, ["received_by", "reviewed_by"])

    return DonationResponse(**_donation_to_response(donation))
