# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Equipment Lending API routes.

Handles equipment CRUD, checkout/return, agreements, maintenance, and reservations.
"""

import math
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.pagination_config import PaginationDefaults
from ...core.shortcuts import get_or_404
from ...models.equipment import (
    Equipment,
    EquipmentAgreement,
    EquipmentAlert,
    EquipmentCheckout,
    EquipmentCondition,
    EquipmentStatus,
    EquipmentType,
    EquipmentMaintenanceStatus,
    EquipmentMaintenanceType,
)
from ...models.user import User
from ...schemas.equipment import (
    AgreementCreate,
    AgreementListResponse,
    AgreementResponse,
    AgreementSign,
    AgreementStatusResponse,
    AlertAcknowledge,
    AlertListResponse,
    AlertResolve,
    AlertResponse,
    EquipmentAvailabilityResponse,
    EquipmentBriefResponse,
    EquipmentCheckoutCreate,
    EquipmentCheckoutListResponse,
    EquipmentCheckoutResponse,
    EquipmentCheckoutReturn,
    EquipmentCreate,
    EquipmentItemResponse,
    EquipmentReportDamaged,
    EquipmentReportLost,
    EquipmentListResponse,
    EquipmentReportSummary,
    EquipmentDemandAnalytics,
    EquipmentResponse,
    EquipmentUpdate,
    EquipmentUtilizationReport,
    MaintenanceComplete,
    MaintenanceCreate,
    MaintenanceListResponse,
    MaintenanceResponse,
    MaintenanceUpdate,
    PatronCheckoutRequest,
    PatronCheckoutResponse,
    PatronEquipmentHistory,
    PatronEquipmentListResponse,
    PatronLoanListResponse,
    PatronLoanResponse,
    PopularEquipmentReport,
    ReservationCreate,
    ReservationListResponse,
    ReservationResponse,
)
from ...services import equipment_service
from ...services import equipment_reports_service as reports

from .auth import get_current_user, get_optional_user
from .dependencies import is_staff_or_admin, require_patron, require_staff

router = APIRouter(prefix="/equipment", tags=["equipment"])


# ============================================================================
# Equipment CRUD Endpoints
# ============================================================================


@router.get("", response_model=EquipmentListResponse)
async def list_equipment(
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    equipment_type: Optional[EquipmentType] = Query(None),
    status: Optional[EquipmentStatus] = Query(None),
    condition: Optional[EquipmentCondition] = Query(None),
    location: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    available_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """List equipment with optional filters. Available to all users (public endpoint)."""
    items, total = await equipment_service.list_equipment(
        db=db,
        page=page,
        per_page=per_page,
        equipment_type=equipment_type,
        status=status,
        condition=condition,
        location=location,
        search=search,
        available_only=available_only,
    )

    return EquipmentListResponse(
        items=[EquipmentResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.get("/available", response_model=list[EquipmentBriefResponse])
async def list_available_equipment(
    equipment_type: Optional[EquipmentType] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """List available equipment for checkout. Quick public endpoint for patron view."""
    items, _ = await equipment_service.list_equipment(
        db=db,
        page=1,
        per_page=100,
        equipment_type=equipment_type,
        available_only=True,
    )

    return [EquipmentBriefResponse.model_validate(item) for item in items]


@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get equipment details by ID."""
    equipment = await equipment_service.get_equipment(db, equipment_id)
    if not equipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    return EquipmentResponse.model_validate(equipment)


@router.get("/barcode/{barcode}", response_model=EquipmentResponse)
async def get_equipment_by_barcode(
    barcode: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get equipment by barcode (for scanning)."""
    equipment = await equipment_service.get_equipment_by_barcode(db, barcode)
    if not equipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    return EquipmentResponse.model_validate(equipment)


@router.post("", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    equipment_in: EquipmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create new equipment item. Staff only."""
    equipment = await equipment_service.create_equipment(
        db=db,
        data=equipment_in.model_dump(),
        created_by_id=current_user.id,
    )
    return EquipmentResponse.model_validate(equipment)


@router.patch("/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: int,
    equipment_in: EquipmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update equipment item. Staff only."""
    equipment = await equipment_service.update_equipment(
        db=db,
        equipment_id=equipment_id,
        data=equipment_in.model_dump(exclude_unset=True),
    )
    if not equipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    return EquipmentResponse.model_validate(equipment)


@router.post("/{equipment_id}/retire", response_model=EquipmentResponse)
async def retire_equipment(
    equipment_id: int,
    notes: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Retire equipment from circulation. Staff only."""
    equipment = await equipment_service.retire_equipment(
        db=db,
        equipment_id=equipment_id,
        notes=notes,
    )
    if not equipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    return EquipmentResponse.model_validate(equipment)


@router.get("/{equipment_id}/availability", response_model=EquipmentAvailabilityResponse)
async def check_equipment_availability(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check equipment availability and reservation queue."""
    equipment = await equipment_service.get_equipment(db, equipment_id)
    if not equipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")

    reservations = await equipment_service.get_equipment_reservations(db, equipment_id)

    # Calculate next available date
    next_available = None
    if equipment.status != EquipmentStatus.AVAILABLE and reservations:
        # Simple estimate based on reservation end dates
        for res in reservations:
            if res.end_date > date.today():
                if not next_available or res.end_date < next_available:
                    next_available = res.end_date

    # Calculate queue position for current user
    queue_position = None
    for i, res in enumerate(reservations, 1):
        if res.user_id == current_user.id:
            queue_position = i
            break

    return EquipmentAvailabilityResponse(
        equipment_id=equipment_id,
        is_available=equipment.is_available,
        current_status=equipment.status,
        next_available_date=next_available,
        pending_reservations=len(reservations),
        queue_position=queue_position,
    )


# ============================================================================
# Equipment Checkout Endpoints
# ============================================================================


@router.post("/checkout", response_model=EquipmentCheckoutResponse, status_code=status.HTTP_201_CREATED)
async def checkout_equipment(
    checkout_in: EquipmentCheckoutCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check out equipment. Patrons checkout for themselves, staff can checkout for patrons."""
    # Determine patron ID
    patron_id = current_user.id
    staff_id = None

    if checkout_in.patron_id and is_staff_or_admin(current_user):
        patron_id = checkout_in.patron_id
        staff_id = current_user.id
    elif checkout_in.patron_id and checkout_in.patron_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot checkout equipment for another patron"
        )

    checkout = await equipment_service.checkout_equipment(
        db=db,
        equipment_id=checkout_in.equipment_id,
        patron_id=patron_id,
        staff_id=staff_id,
        notes=checkout_in.checkout_notes,
        deposit_collected=checkout_in.deposit_collected,
    )

    # Get equipment details for response
    equipment = await equipment_service.get_equipment(db, checkout.equipment_id)

    return EquipmentCheckoutResponse(
        id=checkout.id,
        equipment_id=checkout.equipment_id,
        user_id=checkout.user_id,
        status=checkout.status,
        checked_out_at=checkout.checked_out_at,
        due_date=checkout.due_date,
        returned_at=checkout.returned_at,
        renewal_count=checkout.renewal_count,
        condition_at_checkout=checkout.condition_at_checkout,
        condition_at_return=checkout.condition_at_return,
        checkout_notes=checkout.checkout_notes,
        return_notes=checkout.return_notes,
        fine_amount=checkout.fine_amount,
        fine_paid=checkout.fine_paid,
        deposit_amount=checkout.deposit_amount,
        deposit_collected=checkout.deposit_collected,
        deposit_refunded=checkout.deposit_refunded,
        deposit_refund_amount=checkout.deposit_refund_amount,
        deposit_deduction_reason=checkout.deposit_deduction_reason,
        equipment_name=equipment.name if equipment else None,
        equipment_type=equipment.equipment_type if equipment else None,
        equipment_barcode=equipment.barcode if equipment else None,
        return_instructions=equipment.return_instructions if equipment else None,
        included_accessories=equipment.included_accessories if equipment else None,
    )


@router.post("/return/{checkout_id}", response_model=EquipmentCheckoutResponse)
async def return_equipment(
    checkout_id: int,
    return_in: EquipmentCheckoutReturn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Return checked out equipment. Staff only - requires condition inspection."""
    checkout = await equipment_service.return_equipment(
        db=db,
        checkout_id=checkout_id,
        condition_at_return=return_in.condition_at_return,
        staff_id=current_user.id,
        notes=return_in.return_notes,
        refund_deposit=return_in.refund_deposit,
        deposit_deduction_amount=return_in.deposit_deduction_amount,
        deposit_deduction_reason=return_in.deposit_deduction_reason,
    )

    equipment = await equipment_service.get_equipment(db, checkout.equipment_id)

    return EquipmentCheckoutResponse(
        id=checkout.id,
        equipment_id=checkout.equipment_id,
        user_id=checkout.user_id,
        status=checkout.status,
        checked_out_at=checkout.checked_out_at,
        due_date=checkout.due_date,
        returned_at=checkout.returned_at,
        renewal_count=checkout.renewal_count,
        condition_at_checkout=checkout.condition_at_checkout,
        condition_at_return=checkout.condition_at_return,
        checkout_notes=checkout.checkout_notes,
        return_notes=checkout.return_notes,
        fine_amount=checkout.fine_amount,
        fine_paid=checkout.fine_paid,
        deposit_amount=checkout.deposit_amount,
        deposit_collected=checkout.deposit_collected,
        deposit_refunded=checkout.deposit_refunded,
        deposit_refund_amount=checkout.deposit_refund_amount,
        deposit_deduction_reason=checkout.deposit_deduction_reason,
        equipment_name=equipment.name if equipment else None,
        equipment_type=equipment.equipment_type if equipment else None,
        equipment_barcode=equipment.barcode if equipment else None,
        return_instructions=equipment.return_instructions if equipment else None,
        included_accessories=equipment.included_accessories if equipment else None,
    )


@router.post("/return/barcode/{barcode}", response_model=EquipmentCheckoutResponse)
async def return_equipment_by_barcode(
    barcode: str,
    return_in: EquipmentCheckoutReturn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Return equipment by scanning barcode. Staff only."""
    checkout = await equipment_service.return_equipment_by_barcode(
        db=db,
        barcode=barcode,
        condition_at_return=return_in.condition_at_return,
        staff_id=current_user.id,
        notes=return_in.return_notes,
        refund_deposit=return_in.refund_deposit,
        deposit_deduction_amount=return_in.deposit_deduction_amount,
        deposit_deduction_reason=return_in.deposit_deduction_reason,
    )

    equipment = await equipment_service.get_equipment(db, checkout.equipment_id)

    return EquipmentCheckoutResponse(
        id=checkout.id,
        equipment_id=checkout.equipment_id,
        user_id=checkout.user_id,
        status=checkout.status,
        checked_out_at=checkout.checked_out_at,
        due_date=checkout.due_date,
        returned_at=checkout.returned_at,
        renewal_count=checkout.renewal_count,
        condition_at_checkout=checkout.condition_at_checkout,
        condition_at_return=checkout.condition_at_return,
        checkout_notes=checkout.checkout_notes,
        return_notes=checkout.return_notes,
        fine_amount=checkout.fine_amount,
        fine_paid=checkout.fine_paid,
        deposit_amount=checkout.deposit_amount,
        deposit_collected=checkout.deposit_collected,
        deposit_refunded=checkout.deposit_refunded,
        deposit_refund_amount=checkout.deposit_refund_amount,
        deposit_deduction_reason=checkout.deposit_deduction_reason,
        equipment_name=equipment.name if equipment else None,
        equipment_type=equipment.equipment_type if equipment else None,
        equipment_barcode=equipment.barcode if equipment else None,
        return_instructions=equipment.return_instructions if equipment else None,
        included_accessories=equipment.included_accessories if equipment else None,
    )


def _build_checkout_response(
    checkout: EquipmentCheckout,
    equipment: Optional[Equipment],
) -> EquipmentCheckoutResponse:
    return EquipmentCheckoutResponse(
        id=checkout.id,
        equipment_id=checkout.equipment_id,
        user_id=checkout.user_id,
        status=checkout.status,
        checked_out_at=checkout.checked_out_at,
        due_date=checkout.due_date,
        returned_at=checkout.returned_at,
        renewal_count=checkout.renewal_count,
        condition_at_checkout=checkout.condition_at_checkout,
        condition_at_return=checkout.condition_at_return,
        checkout_notes=checkout.checkout_notes,
        return_notes=checkout.return_notes,
        fine_amount=checkout.fine_amount,
        fine_paid=checkout.fine_paid,
        deposit_amount=checkout.deposit_amount,
        deposit_collected=checkout.deposit_collected,
        deposit_refunded=checkout.deposit_refunded,
        deposit_refund_amount=checkout.deposit_refund_amount,
        deposit_deduction_reason=checkout.deposit_deduction_reason,
        equipment_name=equipment.name if equipment else None,
        equipment_type=equipment.equipment_type if equipment else None,
        equipment_barcode=equipment.barcode if equipment else None,
        return_instructions=equipment.return_instructions if equipment else None,
        included_accessories=equipment.included_accessories if equipment else None,
    )


@router.post(
    "/checkouts/{checkout_id}/report-lost",
    response_model=EquipmentCheckoutResponse,
)
async def report_equipment_lost_endpoint(
    checkout_id: int,
    payload: EquipmentReportLost,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Declare a checked-out equipment item as lost.

    Marks the checkout as lost, the equipment status as LOST, and
    (optionally) creates a replacement-cost fine on the patron. Writes
    to both audit systems (ops_audit + HMAC-signed file log).
    """
    checkout = await equipment_service.report_equipment_lost(
        db=db,
        checkout_id=checkout_id,
        staff_id=current_user.id,
        reason=payload.reason,
        assess_replacement_fee=payload.assess_replacement_fee,
        notes=payload.notes,
    )
    equipment = await equipment_service.get_equipment(db, checkout.equipment_id)
    return _build_checkout_response(checkout, equipment)


@router.post(
    "/checkouts/{checkout_id}/report-damaged",
    response_model=EquipmentCheckoutResponse,
)
async def report_equipment_damaged_endpoint(
    checkout_id: int,
    payload: EquipmentReportDamaged,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Declare a checked-out equipment item as damaged.

    Adds a condition log entry, sets the equipment status to DAMAGED,
    and (when fee_amount is provided) creates a damage fine on the
    patron. Writes to both audit systems.
    """
    checkout = await equipment_service.report_equipment_damaged(
        db=db,
        checkout_id=checkout_id,
        staff_id=current_user.id,
        damage_description=payload.damage_description,
        fee_amount=payload.fee_amount,
        notes=payload.notes,
    )
    equipment = await equipment_service.get_equipment(db, checkout.equipment_id)
    return _build_checkout_response(checkout, equipment)


@router.post("/renew/{checkout_id}", response_model=EquipmentCheckoutResponse)
async def renew_equipment_checkout(
    checkout_id: int,
    notes: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Renew equipment checkout."""
    checkout = await equipment_service.renew_equipment_checkout(
        db=db,
        checkout_id=checkout_id,
        patron_id=current_user.id,
        notes=notes,
    )

    equipment = await equipment_service.get_equipment(db, checkout.equipment_id)

    return EquipmentCheckoutResponse(
        id=checkout.id,
        equipment_id=checkout.equipment_id,
        user_id=checkout.user_id,
        status=checkout.status,
        checked_out_at=checkout.checked_out_at,
        due_date=checkout.due_date,
        returned_at=checkout.returned_at,
        renewal_count=checkout.renewal_count,
        condition_at_checkout=checkout.condition_at_checkout,
        condition_at_return=checkout.condition_at_return,
        checkout_notes=checkout.checkout_notes,
        return_notes=checkout.return_notes,
        fine_amount=checkout.fine_amount,
        fine_paid=checkout.fine_paid,
        deposit_amount=checkout.deposit_amount,
        deposit_collected=checkout.deposit_collected,
        deposit_refunded=checkout.deposit_refunded,
        deposit_refund_amount=checkout.deposit_refund_amount,
        deposit_deduction_reason=checkout.deposit_deduction_reason,
        equipment_name=equipment.name if equipment else None,
        equipment_type=equipment.equipment_type if equipment else None,
        equipment_barcode=equipment.barcode if equipment else None,
        return_instructions=equipment.return_instructions if equipment else None,
        included_accessories=equipment.included_accessories if equipment else None,
    )


@router.get("/checkouts/my", response_model=EquipmentCheckoutListResponse)
async def get_my_equipment_checkouts(
    include_history: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's equipment checkouts."""
    checkouts, total = await equipment_service.get_patron_equipment_checkouts(
        db=db,
        patron_id=current_user.id,
        include_history=include_history,
        page=page,
        per_page=per_page,
    )

    items = []
    for checkout in checkouts:
        equipment = await equipment_service.get_equipment(db, checkout.equipment_id)
        items.append(EquipmentCheckoutResponse(
            id=checkout.id,
            equipment_id=checkout.equipment_id,
            user_id=checkout.user_id,
            status=checkout.status,
            checked_out_at=checkout.checked_out_at,
            due_date=checkout.due_date,
            returned_at=checkout.returned_at,
            renewal_count=checkout.renewal_count,
            condition_at_checkout=checkout.condition_at_checkout,
            condition_at_return=checkout.condition_at_return,
            checkout_notes=checkout.checkout_notes,
            return_notes=checkout.return_notes,
            fine_amount=checkout.fine_amount,
            fine_paid=checkout.fine_paid,
            deposit_amount=checkout.deposit_amount,
            deposit_collected=checkout.deposit_collected,
            deposit_refunded=checkout.deposit_refunded,
            deposit_refund_amount=checkout.deposit_refund_amount,
            deposit_deduction_reason=checkout.deposit_deduction_reason,
            equipment_name=equipment.name if equipment else None,
            equipment_type=equipment.equipment_type if equipment else None,
            equipment_barcode=equipment.barcode if equipment else None,
            return_instructions=equipment.return_instructions if equipment else None,
            included_accessories=equipment.included_accessories if equipment else None,
        ))

    return EquipmentCheckoutListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.get("/checkouts/patron/{patron_id}", response_model=EquipmentCheckoutListResponse)
async def get_patron_equipment_checkouts(
    patron_id: int,
    include_history: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get patron's equipment checkouts. Staff only."""
    checkouts, total = await equipment_service.get_patron_equipment_checkouts(
        db=db,
        patron_id=patron_id,
        include_history=include_history,
        page=page,
        per_page=per_page,
    )

    items = []
    for checkout in checkouts:
        equipment = await equipment_service.get_equipment(db, checkout.equipment_id)
        patron = await db.get(User, checkout.user_id)
        items.append(EquipmentCheckoutResponse(
            id=checkout.id,
            equipment_id=checkout.equipment_id,
            user_id=checkout.user_id,
            status=checkout.status,
            checked_out_at=checkout.checked_out_at,
            due_date=checkout.due_date,
            returned_at=checkout.returned_at,
            renewal_count=checkout.renewal_count,
            condition_at_checkout=checkout.condition_at_checkout,
            condition_at_return=checkout.condition_at_return,
            checkout_notes=checkout.checkout_notes,
            return_notes=checkout.return_notes,
            fine_amount=checkout.fine_amount,
            fine_paid=checkout.fine_paid,
            deposit_amount=checkout.deposit_amount,
            deposit_collected=checkout.deposit_collected,
            deposit_refunded=checkout.deposit_refunded,
            deposit_refund_amount=checkout.deposit_refund_amount,
            deposit_deduction_reason=checkout.deposit_deduction_reason,
            equipment_name=equipment.name if equipment else None,
            equipment_type=equipment.equipment_type if equipment else None,
            equipment_barcode=equipment.barcode if equipment else None,
            return_instructions=equipment.return_instructions if equipment else None,
            included_accessories=equipment.included_accessories if equipment else None,
            patron_name=patron.full_name if patron else None,
            patron_email=patron.email if patron else None,
        ))

    return EquipmentCheckoutListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


# ============================================================================
# Equipment Agreement Endpoints
# ============================================================================


@router.get("/agreements/my", response_model=AgreementStatusResponse)
async def get_my_agreement_status(
    equipment_type: Optional[EquipmentType] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if current user has a valid equipment agreement."""
    has_agreement, agreement = await equipment_service.check_patron_agreement(
        db=db,
        user_id=current_user.id,
        equipment_type=equipment_type,
    )

    return AgreementStatusResponse(
        has_valid_agreement=has_agreement,
        agreement_id=agreement.id if agreement else None,
        signed_at=agreement.signed_at if agreement else None,
        valid_until=agreement.valid_until if agreement else None,
        equipment_types_covered=(
            agreement.equipment_types_covered.split(",")
            if agreement and agreement.equipment_types_covered
            else None
        ),
    )


@router.get("/agreements", response_model=AgreementStatusResponse)
async def get_my_agreements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's equipment agreements."""
    agreements_result = await db.execute(
        select(EquipmentAgreement).where(EquipmentAgreement.user_id == current_user.id)
    )
    agreements = agreements_result.scalars().all()
    return AgreementStatusResponse(
        has_agreement=len(agreements) > 0,
        agreement_count=len(agreements),
        agreements=[agreement for agreement in agreements],
        last_agreement=agreements[0] if agreements else None,
    )


@router.post("/agreements", response_model=AgreementResponse, status_code=status.HTTP_201_CREATED)
async def create_agreement(
    agreement_in: AgreementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or get pending equipment agreement."""
    # Determine patron ID
    patron_id = current_user.id
    if agreement_in.patron_id and is_staff_or_admin(current_user):
        patron_id = agreement_in.patron_id

    agreement = await equipment_service.get_or_create_agreement(
        db=db,
        user_id=patron_id,
        equipment_types=agreement_in.equipment_types_covered,
    )

    patron = await db.get(User, agreement.user_id)

    return AgreementResponse(
        id=agreement.id,
        user_id=agreement.user_id,
        agreement_version=agreement.agreement_version,
        status=agreement.status,
        agreement_text=agreement.agreement_text,
        signature=agreement.signature,
        signed_at=agreement.signed_at,
        valid_from=agreement.valid_from,
        valid_until=agreement.valid_until,
        equipment_types_covered=agreement.equipment_types_covered,
        is_valid=agreement.is_valid,
        created_at=agreement.created_at,
        updated_at=agreement.updated_at,
        patron_name=patron.full_name if patron else None,
        patron_email=patron.email if patron else None,
    )


@router.post("/agreements/{agreement_id}/sign", response_model=AgreementResponse)
async def sign_agreement(
    agreement_id: int,
    sign_in: AgreementSign,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sign equipment agreement."""
    # Get client IP for audit trail
    client_ip = request.client.host if request.client else None

    agreement = await equipment_service.sign_agreement(
        db=db,
        agreement_id=agreement_id,
        user_id=current_user.id,
        signature=sign_in.signature,
        ip_address=client_ip,
    )

    patron = await db.get(User, agreement.user_id)

    return AgreementResponse(
        id=agreement.id,
        user_id=agreement.user_id,
        agreement_version=agreement.agreement_version,
        status=agreement.status,
        agreement_text=agreement.agreement_text,
        signature=agreement.signature,
        signed_at=agreement.signed_at,
        valid_from=agreement.valid_from,
        valid_until=agreement.valid_until,
        equipment_types_covered=agreement.equipment_types_covered,
        is_valid=agreement.is_valid,
        created_at=agreement.created_at,
        updated_at=agreement.updated_at,
        patron_name=patron.full_name if patron else None,
        patron_email=patron.email if patron else None,
    )


@router.post("/agreements/{agreement_id}/revoke", response_model=AgreementResponse)
async def revoke_agreement(
    agreement_id: int,
    reason: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Revoke equipment agreement. Staff only."""
    agreement = await equipment_service.revoke_agreement(
        db=db,
        agreement_id=agreement_id,
        revoked_by_id=current_user.id,
        reason=reason,
    )

    patron = await db.get(User, agreement.user_id)

    return AgreementResponse(
        id=agreement.id,
        user_id=agreement.user_id,
        agreement_version=agreement.agreement_version,
        status=agreement.status,
        agreement_text=agreement.agreement_text,
        signature=agreement.signature,
        signed_at=agreement.signed_at,
        valid_from=agreement.valid_from,
        valid_until=agreement.valid_until,
        equipment_types_covered=agreement.equipment_types_covered,
        is_valid=agreement.is_valid,
        created_at=agreement.created_at,
        updated_at=agreement.updated_at,
        patron_name=patron.full_name if patron else None,
        patron_email=patron.email if patron else None,
    )


@router.get("/agreements/patron/{patron_id}", response_model=AgreementStatusResponse)
async def get_patron_agreement_status(
    patron_id: int,
    equipment_type: Optional[EquipmentType] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Check patron's equipment agreement status. Staff only."""
    has_agreement, agreement = await equipment_service.check_patron_agreement(
        db=db,
        user_id=patron_id,
        equipment_type=equipment_type,
    )

    return AgreementStatusResponse(
        has_valid_agreement=has_agreement,
        agreement_id=agreement.id if agreement else None,
        signed_at=agreement.signed_at if agreement else None,
        valid_until=agreement.valid_until if agreement else None,
        equipment_types_covered=(
            agreement.equipment_types_covered.split(",")
            if agreement and agreement.equipment_types_covered
            else None
        ),
    )


# ============================================================================
# Equipment Reservation Endpoints
# ============================================================================


@router.post("/reservations", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    reservation_in: ReservationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create equipment reservation."""
    reservation = await equipment_service.create_reservation(
        db=db,
        equipment_id=reservation_in.equipment_id,
        patron_id=current_user.id,
        start_date=reservation_in.start_date,
        end_date=reservation_in.end_date,
        purpose=reservation_in.purpose,
        notes=reservation_in.notes,
    )

    equipment = await equipment_service.get_equipment(db, reservation.equipment_id)

    return ReservationResponse(
        id=reservation.id,
        equipment_id=reservation.equipment_id,
        user_id=reservation.user_id,
        status=reservation.status,
        start_date=reservation.start_date,
        end_date=reservation.end_date,
        position=reservation.position,
        notified_at=reservation.notified_at,
        pickup_deadline=reservation.pickup_deadline,
        purpose=reservation.purpose,
        notes=reservation.notes,
        confirmed_at=reservation.confirmed_at,
        cancelled_at=reservation.cancelled_at,
        cancellation_reason=reservation.cancellation_reason,
        created_at=reservation.created_at,
        updated_at=reservation.updated_at,
        equipment_name=equipment.name if equipment else None,
        equipment_type=equipment.equipment_type if equipment else None,
        equipment_barcode=equipment.barcode if equipment else None,
    )


@router.delete("/reservations/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_reservation(
    reservation_id: int,
    reason: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel equipment reservation."""
    reservation = await equipment_service.cancel_reservation(
        db=db,
        reservation_id=reservation_id,
        user_id=current_user.id,
        is_staff=is_staff_or_admin(current_user),
        reason=reason,
    )

    equipment = await equipment_service.get_equipment(db, reservation.equipment_id)

    return ReservationResponse(
        id=reservation.id,
        equipment_id=reservation.equipment_id,
        user_id=reservation.user_id,
        status=reservation.status,
        start_date=reservation.start_date,
        end_date=reservation.end_date,
        position=reservation.position,
        notified_at=reservation.notified_at,
        pickup_deadline=reservation.pickup_deadline,
        purpose=reservation.purpose,
        notes=reservation.notes,
        confirmed_at=reservation.confirmed_at,
        cancelled_at=reservation.cancelled_at,
        cancellation_reason=reservation.cancellation_reason,
        created_at=reservation.created_at,
        updated_at=reservation.updated_at,
        equipment_name=equipment.name if equipment else None,
        equipment_type=equipment.equipment_type if equipment else None,
        equipment_barcode=equipment.barcode if equipment else None,
    )


@router.get("/reservations/my", response_model=ReservationListResponse)
async def get_my_reservations(
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's equipment reservations."""
    reservations, total = await equipment_service.get_patron_reservations(
        db=db,
        patron_id=current_user.id,
        page=page,
        per_page=per_page,
    )

    items = []
    for res in reservations:
        equipment = await equipment_service.get_equipment(db, res.equipment_id)
        items.append(ReservationResponse(
            id=res.id,
            equipment_id=res.equipment_id,
            user_id=res.user_id,
            status=res.status,
            start_date=res.start_date,
            end_date=res.end_date,
            position=res.position,
            notified_at=res.notified_at,
            pickup_deadline=res.pickup_deadline,
            purpose=res.purpose,
            notes=res.notes,
            confirmed_at=res.confirmed_at,
            cancelled_at=res.cancelled_at,
            cancellation_reason=res.cancellation_reason,
            created_at=res.created_at,
            updated_at=res.updated_at,
            equipment_name=equipment.name if equipment else None,
            equipment_type=equipment.equipment_type if equipment else None,
            equipment_barcode=equipment.barcode if equipment else None,
        ))

    return ReservationListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.get("/{equipment_id}/reservations", response_model=list[ReservationResponse])
async def get_equipment_reservations(
    equipment_id: int,
    include_past: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get reservations for equipment. Staff only."""
    reservations = await equipment_service.get_equipment_reservations(
        db=db,
        equipment_id=equipment_id,
        include_past=include_past,
    )

    equipment = await equipment_service.get_equipment(db, equipment_id)
    items = []

    for res in reservations:
        patron = await db.get(User, res.user_id)
        items.append(ReservationResponse(
            id=res.id,
            equipment_id=res.equipment_id,
            user_id=res.user_id,
            status=res.status,
            start_date=res.start_date,
            end_date=res.end_date,
            position=res.position,
            notified_at=res.notified_at,
            pickup_deadline=res.pickup_deadline,
            purpose=res.purpose,
            notes=res.notes,
            confirmed_at=res.confirmed_at,
            cancelled_at=res.cancelled_at,
            cancellation_reason=res.cancellation_reason,
            created_at=res.created_at,
            updated_at=res.updated_at,
            equipment_name=equipment.name if equipment else None,
            equipment_type=equipment.equipment_type if equipment else None,
            equipment_barcode=equipment.barcode if equipment else None,
            patron_name=patron.full_name if patron else None,
            patron_email=patron.email if patron else None,
        ))

    return items


# ============================================================================
# Equipment Maintenance Endpoints
# ============================================================================


@router.post("/maintenance", response_model=MaintenanceResponse, status_code=status.HTTP_201_CREATED)
async def schedule_maintenance(
    maintenance_in: MaintenanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Schedule equipment maintenance. Staff only."""
    maintenance = await equipment_service.schedule_maintenance(
        db=db,
        equipment_id=maintenance_in.equipment_id,
        maintenance_type=maintenance_in.maintenance_type,
        scheduled_date=maintenance_in.scheduled_date,
        description=maintenance_in.description,
        staff_id=current_user.id,
    )

    equipment = await equipment_service.get_equipment(db, maintenance.equipment_id)

    return MaintenanceResponse(
        id=maintenance.id,
        equipment_id=maintenance.equipment_id,
        maintenance_type=maintenance.maintenance_type,
        status=maintenance.status,
        description=maintenance.description,
        issues_found=maintenance.issues_found,
        work_performed=maintenance.work_performed,
        scheduled_date=maintenance.scheduled_date,
        started_at=maintenance.started_at,
        completed_at=maintenance.completed_at,
        condition_before=maintenance.condition_before,
        condition_after=maintenance.condition_after,
        parts_cost=maintenance.parts_cost,
        labor_cost=maintenance.labor_cost,
        total_cost=maintenance.total_cost,
        external_vendor=maintenance.external_vendor,
        vendor_invoice=maintenance.vendor_invoice,
        performed_by_id=maintenance.performed_by_id,
        requires_followup=maintenance.requires_followup,
        followup_notes=maintenance.followup_notes,
        followup_date=maintenance.followup_date,
        created_at=maintenance.created_at,
        updated_at=maintenance.updated_at,
        equipment_name=equipment.name if equipment else None,
        equipment_barcode=equipment.barcode if equipment else None,
    )


@router.post("/maintenance/{maintenance_id}/start", response_model=MaintenanceResponse)
async def start_maintenance(
    maintenance_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Start scheduled maintenance. Staff only."""
    maintenance = await equipment_service.start_maintenance(
        db=db,
        maintenance_id=maintenance_id,
        staff_id=current_user.id,
    )

    equipment = await equipment_service.get_equipment(db, maintenance.equipment_id)

    return MaintenanceResponse(
        id=maintenance.id,
        equipment_id=maintenance.equipment_id,
        maintenance_type=maintenance.maintenance_type,
        status=maintenance.status,
        description=maintenance.description,
        issues_found=maintenance.issues_found,
        work_performed=maintenance.work_performed,
        scheduled_date=maintenance.scheduled_date,
        started_at=maintenance.started_at,
        completed_at=maintenance.completed_at,
        condition_before=maintenance.condition_before,
        condition_after=maintenance.condition_after,
        parts_cost=maintenance.parts_cost,
        labor_cost=maintenance.labor_cost,
        total_cost=maintenance.total_cost,
        external_vendor=maintenance.external_vendor,
        vendor_invoice=maintenance.vendor_invoice,
        performed_by_id=maintenance.performed_by_id,
        requires_followup=maintenance.requires_followup,
        followup_notes=maintenance.followup_notes,
        followup_date=maintenance.followup_date,
        created_at=maintenance.created_at,
        updated_at=maintenance.updated_at,
        equipment_name=equipment.name if equipment else None,
        equipment_barcode=equipment.barcode if equipment else None,
    )


@router.post("/maintenance/{maintenance_id}/complete", response_model=MaintenanceResponse)
async def complete_maintenance(
    maintenance_id: int,
    complete_in: MaintenanceComplete,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Complete maintenance task. Staff only."""
    maintenance = await equipment_service.complete_maintenance(
        db=db,
        maintenance_id=maintenance_id,
        staff_id=current_user.id,
        work_performed=complete_in.work_performed,
        condition_after=complete_in.condition_after,
        issues_found=complete_in.issues_found,
        parts_cost=complete_in.parts_cost,
        labor_cost=complete_in.labor_cost,
        external_vendor=complete_in.external_vendor,
        vendor_invoice=complete_in.vendor_invoice,
        requires_followup=complete_in.requires_followup,
        followup_notes=complete_in.followup_notes,
        followup_date=complete_in.followup_date,
    )

    equipment = await equipment_service.get_equipment(db, maintenance.equipment_id)

    return MaintenanceResponse(
        id=maintenance.id,
        equipment_id=maintenance.equipment_id,
        maintenance_type=maintenance.maintenance_type,
        status=maintenance.status,
        description=maintenance.description,
        issues_found=maintenance.issues_found,
        work_performed=maintenance.work_performed,
        scheduled_date=maintenance.scheduled_date,
        started_at=maintenance.started_at,
        completed_at=maintenance.completed_at,
        condition_before=maintenance.condition_before,
        condition_after=maintenance.condition_after,
        parts_cost=maintenance.parts_cost,
        labor_cost=maintenance.labor_cost,
        total_cost=maintenance.total_cost,
        external_vendor=maintenance.external_vendor,
        vendor_invoice=maintenance.vendor_invoice,
        performed_by_id=maintenance.performed_by_id,
        requires_followup=maintenance.requires_followup,
        followup_notes=maintenance.followup_notes,
        followup_date=maintenance.followup_date,
        created_at=maintenance.created_at,
        updated_at=maintenance.updated_at,
        equipment_name=equipment.name if equipment else None,
        equipment_barcode=equipment.barcode if equipment else None,
    )


@router.get("/{equipment_id}/maintenance", response_model=MaintenanceListResponse)
async def get_equipment_maintenance_history(
    equipment_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get maintenance history for equipment. Staff only."""
    records, total = await equipment_service.get_maintenance_history(
        db=db,
        equipment_id=equipment_id,
        page=page,
        per_page=per_page,
    )

    equipment = await equipment_service.get_equipment(db, equipment_id)
    items = []

    for m in records:
        items.append(MaintenanceResponse(
            id=m.id,
            equipment_id=m.equipment_id,
            maintenance_type=m.maintenance_type,
            status=m.status,
            description=m.description,
            issues_found=m.issues_found,
            work_performed=m.work_performed,
            scheduled_date=m.scheduled_date,
            started_at=m.started_at,
            completed_at=m.completed_at,
            condition_before=m.condition_before,
            condition_after=m.condition_after,
            parts_cost=m.parts_cost,
            labor_cost=m.labor_cost,
            total_cost=m.total_cost,
            external_vendor=m.external_vendor,
            vendor_invoice=m.vendor_invoice,
            performed_by_id=m.performed_by_id,
            requires_followup=m.requires_followup,
            followup_notes=m.followup_notes,
            followup_date=m.followup_date,
            created_at=m.created_at,
            updated_at=m.updated_at,
            equipment_name=equipment.name if equipment else None,
            equipment_barcode=equipment.barcode if equipment else None,
        ))

    return MaintenanceListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.get("/maintenance/due", response_model=list[EquipmentBriefResponse])
async def get_equipment_due_for_maintenance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get equipment that needs maintenance. Staff only."""
    equipment_list = await equipment_service.get_due_maintenance(db)
    return [EquipmentBriefResponse.model_validate(e) for e in equipment_list]


# ============================================================================
# Equipment Alerts Endpoints
# ============================================================================


@router.get("/alerts", response_model=AlertListResponse)
async def get_active_alerts(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    priority: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get active equipment alerts. Staff only."""
    alerts, total = await equipment_service.get_active_alerts(
        db=db,
        page=page,
        per_page=per_page,
        priority=priority,
        alert_type=alert_type,
    )

    items = []
    for alert in alerts:
        equipment = await equipment_service.get_equipment(db, alert.equipment_id) if alert.equipment_id else None
        patron = await db.get(User, alert.user_id) if alert.user_id else None

        items.append(AlertResponse(
            id=alert.id,
            alert_type=alert.alert_type,
            priority=alert.priority,
            status=alert.status,
            equipment_id=alert.equipment_id,
            checkout_id=alert.checkout_id,
            reservation_id=alert.reservation_id,
            user_id=alert.user_id,
            title=alert.title,
            message=alert.message,
            days_overdue=alert.days_overdue,
            escalation_level=alert.escalation_level,
            created_at=alert.created_at,
            acknowledged_at=alert.acknowledged_at,
            resolved_at=alert.resolved_at,
            equipment_name=equipment.name if equipment else None,
            equipment_barcode=equipment.barcode if equipment else None,
            patron_name=patron.full_name if patron else None,
            patron_email=patron.email if patron else None,
            patron_phone=patron.phone if patron else None,
        ))

    return AlertListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: int,
    ack_in: AlertAcknowledge,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Acknowledge an alert. Staff only."""
    alert = await equipment_service.acknowledge_alert(
        db=db,
        alert_id=alert_id,
        staff_id=current_user.id,
        notes=ack_in.notes,
    )

    equipment = await equipment_service.get_equipment(db, alert.equipment_id) if alert.equipment_id else None
    patron = await db.get(User, alert.user_id) if alert.user_id else None

    return AlertResponse(
        id=alert.id,
        alert_type=alert.alert_type,
        priority=alert.priority,
        status=alert.status,
        equipment_id=alert.equipment_id,
        checkout_id=alert.checkout_id,
        reservation_id=alert.reservation_id,
        user_id=alert.user_id,
        title=alert.title,
        message=alert.message,
        days_overdue=alert.days_overdue,
        escalation_level=alert.escalation_level,
        created_at=alert.created_at,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at,
        equipment_name=equipment.name if equipment else None,
        equipment_barcode=equipment.barcode if equipment else None,
        patron_name=patron.full_name if patron else None,
        patron_email=patron.email if patron else None,
        patron_phone=patron.phone if patron else None,
    )


@router.post("/alerts/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: int,
    resolve_in: AlertResolve,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Resolve an alert. Staff only."""
    alert = await equipment_service.resolve_alert(
        db=db,
        alert_id=alert_id,
        staff_id=current_user.id,
        resolution_notes=resolve_in.resolution_notes,
    )

    equipment = await equipment_service.get_equipment(db, alert.equipment_id) if alert.equipment_id else None
    patron = await db.get(User, alert.user_id) if alert.user_id else None

    return AlertResponse(
        id=alert.id,
        alert_type=alert.alert_type,
        priority=alert.priority,
        status=alert.status,
        equipment_id=alert.equipment_id,
        checkout_id=alert.checkout_id,
        reservation_id=alert.reservation_id,
        user_id=alert.user_id,
        title=alert.title,
        message=alert.message,
        days_overdue=alert.days_overdue,
        escalation_level=alert.escalation_level,
        created_at=alert.created_at,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at,
        equipment_name=equipment.name if equipment else None,
        equipment_barcode=equipment.barcode if equipment else None,
        patron_name=patron.full_name if patron else None,
        patron_email=patron.email if patron else None,
        patron_phone=patron.phone if patron else None,
    )


@router.post("/alerts/process-overdue")
async def process_overdue_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create/update alerts for overdue equipment. Staff only."""
    count = await equipment_service.create_overdue_alerts(db)
    return {"alerts_created": count}


# ============================================================================
# Equipment Reports Endpoints
# ============================================================================


@router.get("/reports/summary", response_model=EquipmentReportSummary)
async def get_equipment_summary_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get equipment summary statistics. Staff only."""
    summary = await reports.get_equipment_summary(db)
    return EquipmentReportSummary(**summary)


@router.get("/reports/utilization", response_model=list[EquipmentUtilizationReport])
async def get_utilization_report(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    equipment_type: Optional[EquipmentType] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get equipment utilization report. Staff only."""
    data = await reports.get_utilization_report(
        db=db,
        start_date=start_date,
        end_date=end_date,
        equipment_type=equipment_type,
    )
    return [EquipmentUtilizationReport(**item) for item in data]


@router.get("/reports/popular", response_model=list[PopularEquipmentReport])
async def get_popular_equipment_report(
    limit: int = Query(20, ge=1, le=100),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get popular equipment report. Staff only."""
    data = await reports.get_popular_equipment(
        db=db,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
    )
    return [PopularEquipmentReport(**item) for item in data]




@router.get("/reports/demand-analytics", response_model=list[EquipmentDemandAnalytics])
async def get_demand_analytics_report(
    lookback_days: int = Query(90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get demand analytics and suggested device expansion quantities. Staff only."""
    data = await reports.get_demand_analytics(db=db, lookback_days=lookback_days)
    return [EquipmentDemandAnalytics(**item) for item in data]

@router.get("/reports/condition-trends")
async def get_condition_trends_report(
    months: int = Query(6, ge=1, le=24),
    equipment_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get equipment condition trends. Staff only."""
    return await reports.get_condition_trends(
        db=db,
        months=months,
        equipment_id=equipment_id,
    )


@router.get("/reports/by-type")
async def get_equipment_by_type_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get equipment statistics by type. Staff only."""
    return await reports.get_equipment_by_type(db)


@router.get("/reports/overdue")
async def get_overdue_equipment_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get overdue equipment report. Staff only."""
    return await reports.get_overdue_equipment_report(db)


@router.get("/reports/maintenance")
async def get_maintenance_report(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get maintenance statistics report. Staff only."""
    return await reports.get_maintenance_report(
        db=db,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/reports/patron/{patron_id}", response_model=PatronEquipmentHistory)
async def get_patron_equipment_report(
    patron_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get patron equipment history. Staff only."""
    data = await reports.get_patron_equipment_history(db, patron_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patron not found")
    return PatronEquipmentHistory(**data)


@router.get("/reports/dashboard")
async def get_equipment_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get equipment dashboard metrics. Staff only."""
    return await reports.get_dashboard_metrics(db)


# ============================================================================
# Patron-Facing Endpoints
# ============================================================================


@router.get("/catalog", response_model=PatronEquipmentListResponse)
async def list_equipment_catalog(
    equipment_type: Optional[EquipmentType] = Query(None),
    available_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    List available equipment for patrons.

    Public endpoint that returns equipment with optional filtering by type
    and availability. Returns a simplified patron-friendly response.
    """
    items, total = await equipment_service.list_equipment(
        db=db,
        page=1,
        per_page=100,
        equipment_type=equipment_type,
        available_only=available_only,
    )

    return PatronEquipmentListResponse(
        items=[EquipmentItemResponse.model_validate(item) for item in items],
        total=total,
    )


@router.post(
    "/checkouts",
    response_model=PatronCheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
async def patron_checkout_equipment(
    checkout_in: PatronCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    patron: User = Depends(require_patron),
):
    """
    Patron checks out equipment for themselves.

    Requires patron authentication. Creates a checkout record and marks
    the equipment as checked out. The patron must have a signed agreement
    if the equipment requires one.
    """
    checkout = await equipment_service.checkout_equipment(
        db=db,
        equipment_id=checkout_in.equipment_id,
        patron_id=patron.id,
    )

    # Fetch equipment name for the response
    equipment = await equipment_service.get_equipment(db, checkout.equipment_id)

    return PatronCheckoutResponse(
        id=checkout.id,
        equipment_id=checkout.equipment_id,
        equipment_name=equipment.name if equipment else None,
        checked_out_at=checkout.checked_out_at,
        due_date=checkout.due_date,
        status=checkout.status,
    )


@router.get("/checkouts/mine", response_model=PatronLoanListResponse)
async def patron_get_my_loans(
    db: AsyncSession = Depends(get_db),
    patron: User = Depends(require_patron),
):
    """
    Patron views their own equipment loans.

    Returns all active and historical loans for the authenticated patron,
    including an overdue indicator for each loan.
    """
    from app.core.datetime_utils import utc_now

    checkouts, _ = await equipment_service.get_patron_equipment_checkouts(
        db=db,
        patron_id=patron.id,
        include_history=True,
    )

    items = []
    for checkout in checkouts:
        equipment = await equipment_service.get_equipment(db, checkout.equipment_id)

        is_overdue = (
            checkout.status in ("active", "overdue")
            and checkout.due_date is not None
            and utc_now() > checkout.due_date
        )

        items.append(
            PatronLoanResponse(
                id=checkout.id,
                equipment_id=checkout.equipment_id,
                equipment_name=equipment.name if equipment else None,
                checked_out_at=checkout.checked_out_at,
                due_date=checkout.due_date,
                returned_at=checkout.returned_at,
                status=checkout.status,
                is_overdue=is_overdue,
            )
        )

    return PatronLoanListResponse(items=items)


@router.post("/checkouts/{checkout_id}/return", response_model=PatronLoanResponse)
async def patron_return_equipment(
    checkout_id: int,
    db: AsyncSession = Depends(get_db),
    patron: User = Depends(require_patron),
):
    """
    Patron initiates return of checked-out equipment.

    Marks the checkout as returned. The patron can only return their own
    checkouts. Condition is set to the same condition as at checkout time
    (staff can update condition later via the staff return endpoint).
    """
    from app.core.datetime_utils import utc_now

    # Verify the checkout belongs to the patron
    result = await db.execute(
        select(EquipmentCheckout).where(
            EquipmentCheckout.id == checkout_id,
            EquipmentCheckout.user_id == patron.id,
        )
    )
    checkout = result.scalar_one_or_none()

    if not checkout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkout not found",
        )

    if checkout.status not in ("active", "overdue"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This checkout is not currently active",
        )

    # Use the condition at checkout as the default return condition
    condition_at_return = checkout.condition_at_checkout or EquipmentCondition.GOOD

    returned = await equipment_service.return_equipment(
        db=db,
        checkout_id=checkout_id,
        condition_at_return=condition_at_return,
        staff_id=patron.id,
        notes="Self-service return by patron",
    )

    equipment = await equipment_service.get_equipment(db, returned.equipment_id)

    is_overdue = (
        returned.status in ("active", "overdue")
        and returned.due_date is not None
        and utc_now() > returned.due_date
    )

    return PatronLoanResponse(
        id=returned.id,
        equipment_id=returned.equipment_id,
        equipment_name=equipment.name if equipment else None,
        checked_out_at=returned.checked_out_at,
        due_date=returned.due_date,
        returned_at=returned.returned_at,
        status=returned.status,
        is_overdue=is_overdue,
    )

