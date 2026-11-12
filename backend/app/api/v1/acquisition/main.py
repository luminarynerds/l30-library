# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Acquisition - Fund Management API Endpoints

This module provides endpoints for:
- Fund CRUD operations
- Budget management
- Fiscal year rollover

Related modules:
- acquisition_vendors.py: Vendor management
- acquisition_selection.py: Selection list (wishlist)
- acquisition_po.py: Purchase order workflow
- acquisition_external.py: External catalog search
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....core.logging import get_logger

logger = get_logger(__name__)
from ....models.acquisition import Fund, FundStatus, PurchaseOrder, PurchaseOrderStatus
from ....models.user import User, UserRole
from ....schemas.acquisition import (
    FundCreate, FundListResponse, FundResponse, FundRolloverRequest,
    FundRolloverResponse, FundUpdate
)
from ..auth import get_current_user
from ..dependencies import require_staff, require_director

router = APIRouter(prefix="/acquisition", tags=["acquisition-funds"])


# ============ Fund Routes ============


@router.get("/funds", response_model=FundListResponse)
async def list_funds(
    fiscal_year: int | None = Query(None),
    status: FundStatus | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all funds with optional filters"""
    await require_staff(current_user)

    query = select(Fund)
    count_query = select(func.count(Fund.id))

    if fiscal_year:
        query = query.where(Fund.fiscal_year == fiscal_year)
        count_query = count_query.where(Fund.fiscal_year == fiscal_year)

    if status:
        query = query.where(Fund.status == status)
        count_query = count_query.where(Fund.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Fund.name)

    result = await db.execute(query)
    funds = result.scalars().all()

    return FundListResponse(
        items=[FundResponse.model_validate(f) for f in funds],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/funds", response_model=FundResponse, status_code=status.HTTP_201_CREATED)
async def create_fund(
    fund_in: FundCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new fund"""
    await require_director(current_user)

    # Check for duplicate code
    existing = await db.execute(select(Fund).where(Fund.code == fund_in.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fund code already exists")

    fund = Fund(**fund_in.model_dump())
    db.add(fund)
    await db.commit()
    await db.refresh(fund)
    return fund


@router.get("/funds/{fund_id}", response_model=FundResponse)
async def get_fund(
    fund_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get fund details"""
    await require_staff(current_user)

    fund = await get_or_404(db, Fund, fund_id, "Fund not found")
    return fund


@router.patch("/funds/{fund_id}", response_model=FundResponse)
async def update_fund(
    fund_id: int,
    fund_in: FundUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a fund"""
    await require_director(current_user)

    fund = await get_or_404(db, Fund, fund_id, "Fund not found")

    # Prevent all modifications to closed funds - closed funds are final
    if fund.status == FundStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify a closed fund. Closed funds are final and cannot be reopened."
        )

    for field, value in fund_in.model_dump(exclude_unset=True).items():
        setattr(fund, field, value)

    await db.commit()
    await db.refresh(fund)
    return fund


@router.post("/funds/rollover", response_model=FundRolloverResponse)
async def rollover_funds(
    request: FundRolloverRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rollover funds from one fiscal year to another"""
    await require_director(current_user)

    # Get source funds
    result = await db.execute(
        select(Fund).where(
            Fund.fiscal_year == request.source_fiscal_year,
            Fund.status == FundStatus.ACTIVE,
        )
    )
    source_funds = result.scalars().all()

    if not source_funds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active funds found for source fiscal year"
        )

    # Check for existing funds in target year (prevent duplicate rollover)
    existing_target = await db.execute(
        select(func.count(Fund.id)).where(
            Fund.fiscal_year == request.target_fiscal_year
        )
    )
    existing_count = existing_target.scalar() or 0
    if existing_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Funds already exist for fiscal year {request.target_fiscal_year}. "
                   "Cannot rollover to an existing fiscal year."
        )

    # Check for pending/unprocessed POs against source funds
    source_fund_ids = [f.id for f in source_funds]
    pending_statuses = [
        PurchaseOrderStatus.DRAFT,
        PurchaseOrderStatus.PENDING_APPROVAL,
        PurchaseOrderStatus.APPROVED,
        PurchaseOrderStatus.SUBMITTED,
        PurchaseOrderStatus.PARTIALLY_RECEIVED,
    ]

    pending_po_result = await db.execute(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.fund_id.in_(source_fund_ids),
            PurchaseOrder.status.in_(pending_statuses),
        )
    )
    pending_count = pending_po_result.scalar() or 0

    if pending_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot rollover: {pending_count} purchase order(s) are still pending. "
                   "All POs must be completed, received, or cancelled before rollover."
        )

    try:
        created_funds = []
        for source in source_funds:
            # Calculate new allocation
            if request.carry_forward_unspent:
                # Use true unspent (allocated - spent), not available_amount
                # available_amount = allocated - encumbered - spent (loses encumbered)
                # true unspent = allocated - spent (encumbered should be 0 if all POs processed)
                true_unspent = source.allocated_amount - (source.spent_amount or Decimal("0.00"))
                # Only carry forward positive unspent amounts; cap at 0 for overspent funds
                new_allocation = max(Decimal("0.00"), true_unspent)
            else:
                new_allocation = source.allocated_amount

            # Create new fund with clean code (remove any existing -FY suffix)
            base_code = source.code.split("-FY")[0] if "-FY" in source.code else source.code
            new_fund = Fund(
                code=f"{base_code}-FY{request.target_fiscal_year}",
                name=source.name,
                description=source.description,
                fiscal_year=request.target_fiscal_year,
                allocated_amount=new_allocation,
                encumbered_amount=Decimal("0.00"),
                spent_amount=Decimal("0.00"),
                status=FundStatus.ACTIVE,
            )
            db.add(new_fund)
            created_funds.append(new_fund)

            # Close source fund
            source.status = FundStatus.CLOSED

        await db.commit()

        return FundRolloverResponse(
            message=f"Rolled over {len(created_funds)} funds to FY{request.target_fiscal_year}",
            funds_created=len(created_funds),
        )
    except Exception:
        await db.rollback()
        logger.exception("Failed to rollover funds")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to rollover funds"
        ) from None



