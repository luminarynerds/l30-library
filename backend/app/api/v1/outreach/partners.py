# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Outreach Partner CRUD + contacts endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.logging import get_logger
from ....models.outreach import (
    OutreachPartner, OutreachPartnerContact, OutreachDeposit,
    OutreachVisit, InstitutionalCard, BulkCheckout,
    OutreachPartnerStatus, PartnerType, DepositStatus, VisitStatus,
    InstitutionalCardStatus, BulkCheckoutStatus
)
from ....models.user import User
from ....schemas.outreach import (
    OutreachPartnerCreate, OutreachPartnerUpdate, OutreachPartnerResponse,
    OutreachPartnerListResponse,
    OutreachPartnerContactCreate, OutreachPartnerContactResponse,
)
from .helpers import require_staff

logger = get_logger(__name__)

router = APIRouter()


@router.post("/partners", response_model=OutreachPartnerResponse, status_code=status.HTTP_201_CREATED)
async def create_partner(
    partner_data: OutreachPartnerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Create a new outreach partner (school, organization, etc.)."""
    partner = OutreachPartner(
        **partner_data.model_dump(exclude={"school_level"}),
        school_level=str(partner_data.school_level) if partner_data.school_level else None,
        created_by_id=current_user.id
    )
    db.add(partner)
    await db.commit()
    await db.refresh(partner)

    logger.info(f"Created outreach partner: {partner.name}", extra={"partner_id": partner.id})
    return partner


@router.get("/partners", response_model=OutreachPartnerListResponse)
async def list_partners(
    status: Optional[OutreachPartnerStatus] = None,
    partner_type: Optional[PartnerType] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """List outreach partners with optional filtering."""
    query = select(OutreachPartner)

    if status:
        query = query.where(OutreachPartner.status == status.value)
    if partner_type:
        query = query.where(OutreachPartner.partner_type == partner_type.value)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                OutreachPartner.name.ilike(search_pattern),
                OutreachPartner.city.ilike(search_pattern),
                OutreachPartner.primary_contact_name.ilike(search_pattern)
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get paginated results
    query = query.order_by(OutreachPartner.name).offset(offset).limit(limit)
    result = await db.execute(query)
    partners = result.scalars().all()

    return OutreachPartnerListResponse(
        partners=[OutreachPartnerResponse.model_validate(p) for p in partners],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/partners/{partner_id}", response_model=OutreachPartnerResponse)
async def get_partner(
    partner_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Get details of a specific outreach partner."""
    query = select(OutreachPartner).where(OutreachPartner.id == partner_id)
    result = await db.execute(query)
    partner = result.scalar_one_or_none()

    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    # Get related counts
    response = OutreachPartnerResponse.model_validate(partner)

    # Count active bulk checkouts
    bc_query = select(func.count()).select_from(BulkCheckout).where(
        BulkCheckout.partner_id == partner_id,
        BulkCheckout.status == BulkCheckoutStatus.ACTIVE.value
    )
    response.active_bulk_checkouts = (await db.execute(bc_query)).scalar() or 0

    # Count active institutional cards
    ic_query = select(func.count()).select_from(InstitutionalCard).where(
        InstitutionalCard.partner_id == partner_id,
        InstitutionalCard.status == InstitutionalCardStatus.ACTIVE.value
    )
    response.active_institutional_cards = (await db.execute(ic_query)).scalar() or 0

    # Count total visits
    visit_query = select(func.count()).select_from(OutreachVisit).where(
        OutreachVisit.partner_id == partner_id
    )
    response.total_visits = (await db.execute(visit_query)).scalar() or 0

    # Sum pending deposits
    deposit_query = select(func.sum(OutreachDeposit.amount - OutreachDeposit.amount_applied - OutreachDeposit.amount_refunded)).where(
        OutreachDeposit.partner_id == partner_id,
        OutreachDeposit.status == DepositStatus.HELD.value
    )
    response.pending_deposits = (await db.execute(deposit_query)).scalar() or 0.0

    return response


@router.patch("/partners/{partner_id}", response_model=OutreachPartnerResponse)
async def update_partner(
    partner_id: int,
    update_data: OutreachPartnerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Update an outreach partner."""
    query = select(OutreachPartner).where(OutreachPartner.id == partner_id)
    result = await db.execute(query)
    partner = result.scalar_one_or_none()

    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    update_dict = update_data.model_dump(exclude_unset=True, exclude={"school_level"})
    if update_data.school_level is not None:
        update_dict["school_level"] = str(update_data.school_level)

    for field, value in update_dict.items():
        setattr(partner, field, value)

    await db.commit()
    await db.refresh(partner)

    logger.info(f"Updated outreach partner: {partner.name}", extra={"partner_id": partner_id})
    return partner


@router.delete("/partners/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_partner(
    partner_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Delete an outreach partner (soft delete by setting status to terminated)."""
    query = select(OutreachPartner).where(OutreachPartner.id == partner_id)
    result = await db.execute(query)
    partner = result.scalar_one_or_none()

    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    partner.status = OutreachPartnerStatus.TERMINATED.value
    await db.commit()

    logger.info(f"Terminated outreach partner: {partner.name}", extra={"partner_id": partner_id})


# Partner Contacts
@router.post("/partners/{partner_id}/contacts", response_model=OutreachPartnerContactResponse, status_code=status.HTTP_201_CREATED)
async def add_partner_contact(
    partner_id: int,
    contact_data: OutreachPartnerContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Add a contact to an outreach partner."""
    # Verify partner exists
    partner_query = select(OutreachPartner).where(OutreachPartner.id == partner_id)
    partner = (await db.execute(partner_query)).scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    contact = OutreachPartnerContact(
        partner_id=partner_id,
        **contact_data.model_dump()
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)

    return contact


@router.get("/partners/{partner_id}/contacts", response_model=list[OutreachPartnerContactResponse])
async def list_partner_contacts(
    partner_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """List all contacts for a partner."""
    query = select(OutreachPartnerContact).where(
        OutreachPartnerContact.partner_id == partner_id
    ).order_by(OutreachPartnerContact.is_primary.desc(), OutreachPartnerContact.name)

    result = await db.execute(query)
    return result.scalars().all()
