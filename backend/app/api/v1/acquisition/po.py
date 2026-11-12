# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Acquisition - Purchase Order API Endpoints

Provides endpoints for:
- Purchase order CRUD
- PO workflow (submit, approve, reject)
- PO item management
- Receiving orders
- PDF generation and vendor email

Refactored to use POFacadeService for business logic encapsulation.
Separates HTTP concerns from database operations and business rules.
"""
import asyncio
from app.core.logging import get_logger
from io import BytesIO

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.config import get_settings
from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....core.email import send_email
from ....core.error_codes import ErrorCode
from ....core.exceptions import APIError, InternalServerError
from ....models.acquisition import PurchaseOrder
from ....models.user import User, UserRole
from ....schemas.acquisition import (
    POItemCreate, POItemResponse, POItemUpdate,
    PurchaseOrderCreate, PurchaseOrderDetail, PurchaseOrderListResponse,
    PurchaseOrderResponse, PurchaseOrderUpdate, ReceiveItemsRequest,
    RejectionRequest, PurchaseOrderStatus, BudgetValidationResponse, FundSuggestion
)
from ....services.email_templates import (
    render_po_approved_email, render_po_rejected_email,
    render_po_submitted_email, render_vendor_email
)
from ....services.po_facade_service import POFacadeService
from ....services.po_pdf import generate_po_pdf
from ..auth import get_current_user
from ..dependencies import require_staff, require_director
from ..lifecycle import create_lifecycle_event

logger = get_logger(__name__)

router = APIRouter(prefix="/acquisition", tags=["acquisition-po"])


# ============ Purchase Order CRUD ============


@router.get("/purchase-orders", response_model=PurchaseOrderListResponse)
async def list_purchase_orders(
    status: PurchaseOrderStatus | None = Query(None),
    vendor_id: int | None = Query(None),
    fund_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List purchase orders with optional filters and pagination"""
    try:

        facade = POFacadeService(db)
        result = await facade.list_purchase_orders(
            status=status,
            vendor_id=vendor_id,
            fund_id=fund_id,
            page=page,
            per_page=per_page,
            current_user=current_user,
        )
        return result
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to list purchase orders")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.post("/purchase-orders", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    po_in: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new purchase order with items and budget validation"""
    try:

        facade = POFacadeService(db)
        po = await facade.create_purchase_order(po_in, current_user)
        logger.info(f"Created PO {po.po_number} by user {current_user.id}")
        return po
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to create purchase order")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderDetail)
async def get_purchase_order(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get purchase order details with items and relationships"""
    try:

        facade = POFacadeService(db)
        po = await facade.get_purchase_order(po_id, current_user)
        return po
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to retrieve purchase order")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.patch("/purchase-orders/{po_id}", response_model=PurchaseOrderResponse)
async def update_purchase_order(
    po_id: int,
    po_in: PurchaseOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a purchase order (draft status only)"""
    try:

        facade = POFacadeService(db)
        po = await facade.update_purchase_order(po_id, po_in, current_user)
        logger.info(f"Updated PO {po.po_number} by user {current_user.id}")
        return po
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to update purchase order")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.delete("/purchase-orders/{po_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase_order(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a purchase order (draft status only)"""
    try:

        facade = POFacadeService(db)
        await facade.delete_purchase_order(po_id, current_user)
        logger.info(f"Deleted PO {po_id} by user {current_user.id}")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to delete purchase order")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


# ============ PO Items ============


@router.post("/purchase-orders/{po_id}/items", response_model=POItemResponse, status_code=status.HTTP_201_CREATED)
async def add_po_item(
    po_id: int,
    item_in: POItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add line item to purchase order (draft only)"""
    try:

        facade = POFacadeService(db)
        po_item = await facade.add_po_item(po_id, item_in, current_user)
        logger.info(f"Added item to PO {po_id} by user {current_user.id}")
        return po_item
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to add item to purchase order")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.delete("/purchase-orders/{po_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase_order_item(
    po_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete line item from DRAFT purchase order only"""
    try:

        facade = POFacadeService(db)
        await facade.delete_po_item(po_id, item_id, current_user)
        logger.info(f"Deleted item {item_id} from PO {po_id} by user {current_user.id}")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to delete item from purchase order")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.patch("/purchase-orders/{po_id}/items/{item_id}", response_model=POItemResponse)
async def update_purchase_order_item(
    po_id: int,
    item_id: int,
    item_update: POItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update line item in DRAFT purchase order only"""
    try:

        facade = POFacadeService(db)
        po_item = await facade.update_po_item(po_id, item_id, item_update, current_user)
        logger.info(f"Updated item {item_id} in PO {po_id} by user {current_user.id}")
        return po_item
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to update purchase order item")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


# ============ Budget Validation ============


@router.get("/purchase-orders/{po_id}/budget-validation", response_model=BudgetValidationResponse)
async def validate_po_budget(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Validate budget for a purchase order.
    Returns fund availability, warning levels, and suggestions if over budget.
    """
    from decimal import Decimal
    from sqlalchemy import select
    from ....models.acquisition import Fund, FundStatus

    try:

        facade = POFacadeService(db)
        po = await facade.get_purchase_order(po_id, current_user)

        if not po.fund_id:
            return BudgetValidationResponse(
                is_valid=False,
                fund_id=None,
                fund_code=None,
                fund_name=None,
                available_amount=Decimal("0.00"),
                order_total=po.total_amount,
                remaining_after_order=Decimal("0.00"),
                usage_percentage=0.0,
                warning_level="danger",
                message="No fund selected for this purchase order",
                suggested_funds=[]
            )

        # Get fund details
        result = await db.execute(select(Fund).where(Fund.id == po.fund_id))
        fund = result.scalar_one_or_none()

        if not fund:
            return BudgetValidationResponse(
                is_valid=False,
                fund_id=po.fund_id,
                fund_code=None,
                fund_name=None,
                available_amount=Decimal("0.00"),
                order_total=po.total_amount,
                remaining_after_order=Decimal("0.00"),
                usage_percentage=0.0,
                warning_level="danger",
                message="Selected fund not found",
                suggested_funds=[]
            )

        available = fund.available_amount
        order_total = po.total_amount or Decimal("0.00")
        remaining = available - order_total

        # Calculate usage percentage
        if available > 0:
            usage_percentage = float((order_total / available) * 100)
        else:
            usage_percentage = 100.0 if order_total > 0 else 0.0

        # Determine warning level
        if remaining < 0:
            warning_level = "danger"
            message = f"This order exceeds available funds by ${abs(remaining):.2f}"
            exceeds_by = abs(remaining)
            is_valid = False
        elif usage_percentage > 75:
            warning_level = "warning"
            message = f"This order uses {usage_percentage:.1f}% of available funds"
            exceeds_by = None
            is_valid = True
        else:
            warning_level = "none"
            message = "Budget is within limits"
            exceeds_by = None
            is_valid = True

        # If over budget, find alternative funds with sufficient balance
        suggested_funds = []
        if not is_valid:
            result = await db.execute(
                select(Fund).where(
                    Fund.status == FundStatus.ACTIVE,
                    Fund.id != fund.id,
                    Fund.fiscal_year == fund.fiscal_year
                )
            )
            other_funds = result.scalars().all()

            for other_fund in other_funds:
                if other_fund.available_amount >= order_total:
                    suggested_funds.append(FundSuggestion(
                        id=other_fund.id,
                        code=other_fund.code,
                        name=other_fund.name,
                        available_amount=other_fund.available_amount
                    ))

        return BudgetValidationResponse(
            is_valid=is_valid,
            fund_id=fund.id,
            fund_code=fund.code,
            fund_name=fund.name,
            available_amount=available,
            order_total=order_total,
            remaining_after_order=remaining,
            usage_percentage=usage_percentage,
            warning_level=warning_level,
            message=message,
            exceeds_budget_by=exceeds_by,
            suggested_funds=suggested_funds
        )
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to validate budget")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.get("/funds/{fund_id}/budget-check", response_model=BudgetValidationResponse)
async def check_fund_budget(
    fund_id: int,
    order_total: float = Query(0.0, description="Proposed order total to check against"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check budget availability for a specific fund and proposed order total.
    Useful for real-time validation before submitting.
    """
    from decimal import Decimal
    from sqlalchemy import select
    from ....models.acquisition import Fund, FundStatus

    try:

        fund = await get_or_404(db, Fund, fund_id, "Fund not found")

        available = fund.available_amount
        order_total_decimal = Decimal(str(order_total))
        remaining = available - order_total_decimal

        # Calculate usage percentage
        if available > 0:
            usage_percentage = float((order_total_decimal / available) * 100)
        else:
            usage_percentage = 100.0 if order_total_decimal > 0 else 0.0

        # Determine warning level
        if remaining < 0:
            warning_level = "danger"
            message = f"This order exceeds available funds by ${abs(remaining):.2f}"
            exceeds_by = abs(remaining)
            is_valid = False
        elif usage_percentage > 75:
            warning_level = "warning"
            message = f"This order uses {usage_percentage:.1f}% of available funds"
            exceeds_by = None
            is_valid = True
        else:
            warning_level = "none"
            message = "Budget is within limits"
            exceeds_by = None
            is_valid = True

        # If over budget, find alternative funds
        suggested_funds = []
        if not is_valid:
            result = await db.execute(
                select(Fund).where(
                    Fund.status == FundStatus.ACTIVE,
                    Fund.id != fund.id,
                    Fund.fiscal_year == fund.fiscal_year
                )
            )
            other_funds = result.scalars().all()

            for other_fund in other_funds:
                if other_fund.available_amount >= order_total_decimal:
                    suggested_funds.append(FundSuggestion(
                        id=other_fund.id,
                        code=other_fund.code,
                        name=other_fund.name,
                        available_amount=other_fund.available_amount
                    ))

        return BudgetValidationResponse(
            is_valid=is_valid,
            fund_id=fund.id,
            fund_code=fund.code,
            fund_name=fund.name,
            available_amount=available,
            order_total=order_total_decimal,
            remaining_after_order=remaining,
            usage_percentage=usage_percentage,
            warning_level=warning_level,
            message=message,
            exceeds_budget_by=exceeds_by,
            suggested_funds=suggested_funds
        )
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to check budget")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


# ============ PO Workflow ============


@router.patch(
    "/purchase-orders/{po_id}/submit-for-approval", response_model=PurchaseOrderResponse
)
async def submit_for_approval(
    po_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit purchase order for director approval"""
    try:

        async def notify_directors_callback(po):
            from sqlalchemy import select

            directors_result = await db.execute(
                select(User).where(User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN]))
            )
            directors = directors_result.scalars().all()
            director_emails = [d.email for d in directors if d.email]
            po_number = po.po_number
            email_content = render_po_submitted_email(po)

            async def _send_emails():
                tasks = [
                    send_email(
                        to_email=email,
                        subject=f"PO {po_number} Awaiting Approval",
                        html_content=email_content,
                    )
                    for email in director_emails
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for email, result in zip(director_emails, results):
                    if isinstance(result, Exception):
                        logger.error(f"Failed to notify director {email}: {result}")

            background_tasks.add_task(_send_emails)

        facade = POFacadeService(db)
        po = await facade.submit_for_approval(
            po_id,
            current_user,
            notify_directors_callback=notify_directors_callback,
        )
        logger.info(f"Submitted PO {po.po_number} for approval by user {current_user.id}")
        return po
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to submit purchase order for approval")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.patch("/purchase-orders/{po_id}/approve", response_model=PurchaseOrderResponse)
async def approve_purchase_order(
    po_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a purchase order (Director only)"""
    try:

        async def notify_creator_callback(po, approved_by_name):
            creator_email = po.created_by.email
            po_number = po.po_number
            email_content = render_po_approved_email(po, approved_by_name)

            async def _send_email():
                try:
                    await send_email(
                        to_email=creator_email,
                        subject=f"PO {po_number} Approved",
                        html_content=email_content,
                    )
                except Exception as e:  # noqa: BLE001  # background task — log and continue
                    logger.error(f"Failed to notify creator about PO approval: {e}")

            background_tasks.add_task(_send_email)

        facade = POFacadeService(db)
        po = await facade.approve_purchase_order(
            po_id,
            current_user,
            notify_creator_callback=notify_creator_callback,
        )
        logger.info(f"Approved PO {po.po_number} by user {current_user.id}")
        return po
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to approve purchase order")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.patch("/purchase-orders/{po_id}/reject", response_model=PurchaseOrderResponse)
async def reject_purchase_order(
    po_id: int,
    request: RejectionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject a purchase order (Director only)"""
    try:

        async def notify_creator_callback(po, rejected_by_name):
            creator_email = po.created_by.email
            po_number = po.po_number
            email_content = render_po_rejected_email(po, rejected_by_name)

            async def _send_email():
                try:
                    await send_email(
                        to_email=creator_email,
                        subject=f"PO {po_number} Rejected",
                        html_content=email_content,
                    )
                except Exception as e:  # noqa: BLE001  # background task — log and continue
                    logger.error(f"Failed to notify creator about PO rejection: {e}")

            background_tasks.add_task(_send_email)

        facade = POFacadeService(db)
        po = await facade.reject_purchase_order(
            po_id,
            request,
            current_user,
            notify_creator_callback=notify_creator_callback,
        )
        logger.info(f"Rejected PO {po.po_number} by user {current_user.id}")
        return po
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to reject purchase order")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.patch("/purchase-orders/{po_id}/submit", response_model=PurchaseOrderResponse)
async def submit_to_vendor(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit approved order to vendor (encumbers budget)"""
    try:

        facade = POFacadeService(db)
        po = await facade.submit_to_vendor(po_id, current_user)
        logger.info(
            f"Submitted PO {po.po_number} to vendor by user {current_user.id}"
        )
        return po
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to submit order to vendor")
        raise InternalServerError(code=ErrorCode.EXTERNAL_SERVICE_ERROR) from None


# ============ Receiving ============


@router.patch("/purchase-orders/{po_id}/receive", response_model=PurchaseOrderResponse)
async def receive_order(
    po_id: int,
    request: ReceiveItemsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Receive items from vendor (creates catalog items, moves budget to spent)"""
    try:

        async def create_lifecycle_event_callback(
            item_copy_id,
            event_type,
            description,
            metadata,
            performed_by_id,
            related_po_id,
        ):
            await create_lifecycle_event(
                db=db,
                item_copy_id=item_copy_id,
                event_type=event_type,
                description=description,
                metadata=metadata,
                performed_by_id=performed_by_id,
                related_po_id=related_po_id,
            )

        facade = POFacadeService(db)
        po = await facade.receive_order(
            po_id,
            request,
            current_user,
            create_lifecycle_event_callback=create_lifecycle_event_callback,
        )
        logger.info(f"Received items for PO {po.po_number} by user {current_user.id}")
        return po
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to receive order")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


# ============ PDF and Email ============


@router.get("/purchase-orders/{po_id}/pdf")
async def download_purchase_order_pdf(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download PO as PDF (creator or director only)"""
    try:

        facade = POFacadeService(db)
        facade._require_staff(current_user)

        # Load ORM object with relationships for PDF generation
        result = await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id)
            .options(
                selectinload(PurchaseOrder.items),
                selectinload(PurchaseOrder.vendor),
                selectinload(PurchaseOrder.fund),
            )
        )
        po = result.scalar_one_or_none()
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        # Authorization check: creator or director
        if (
            current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]
            and po.created_by_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this purchase order"
            )

        # Run PDF generation in thread executor to avoid blocking event loop
        pdf_bytes = await asyncio.to_thread(generate_po_pdf, po)

        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=PO_{po.po_number}.pdf"
            },
        )
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to generate PDF")
        raise InternalServerError(code=ErrorCode.EXTERNAL_SERVICE_ERROR) from None


@router.post("/purchase-orders/{po_id}/email-vendor")
async def email_purchase_order_to_vendor(
    po_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Email approved purchase order to vendor with PDF attachment"""
    try:

        facade = POFacadeService(db)
        facade._require_staff(current_user)

        # Load ORM object with relationships for PDF and email
        result = await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id)
            .options(
                selectinload(PurchaseOrder.items),
                selectinload(PurchaseOrder.vendor),
                selectinload(PurchaseOrder.fund),
            )
        )
        po = result.scalar_one_or_none()
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        # Authorization check: creator or director
        if (
            current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]
            and po.created_by_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to email this purchase order"
            )

        if po.status != PurchaseOrderStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Can only email approved purchase orders"
            )

        if not po.vendor or not po.vendor.email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vendor email address not set")

        # Run PDF generation in thread executor to avoid blocking event loop
        pdf_bytes = await asyncio.to_thread(generate_po_pdf, po)

        # Queue email sending in background to return response faster
        async def _send_vendor_email():
            try:
                settings = get_settings()
                await send_email(
                    to_email=po.vendor.email,
                    subject=f"Purchase Order {po.po_number} from {settings.library_name}",
                    html_content=render_vendor_email(po),
                    attachment_data=pdf_bytes,
                    attachment_filename=f"PO_{po.po_number}.pdf",
                )
                logger.info(f"Emailed PO {po.po_number} to vendor {po.vendor.name}")
            except Exception as e:  # noqa: BLE001  # background task — log and continue
                logger.error(f"Failed to email PO {po.po_number} to vendor: {e}")

        background_tasks.add_task(_send_vendor_email)

        return {"message": f"Purchase order being emailed to {po.vendor.email}"}
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to email purchase order")
        raise InternalServerError(code=ErrorCode.EXTERNAL_SERVICE_ERROR) from None
