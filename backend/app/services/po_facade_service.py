# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from app.core.logging import get_logger
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.email import send_email
from ..core.error_codes import ErrorCode
from ..core.exceptions import (
    BusinessLogicError,
    ForbiddenError,
    InternalServerError,
    ResourceNotFoundError,
    ValidationError,
)
from ..core.input_validation import input_validator
from ..models.acquisition import (
    Fund,
    FundStatus,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)
from ..models.inventory import ProcessingStep
from ..models.lifecycle import LifecycleEventType
from ..models.user import User, UserRole
from ..schemas.acquisition import (
    BatchApproveRequest,
    BatchApproveResponse,
    BatchApproveResult,
    POItemCreate,
    POItemResponse,
    POItemUpdate,
    PurchaseOrderCreate,
    PurchaseOrderDetail,
    PurchaseOrderListResponse,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
    ReceiveItemsRequest,
    RejectionRequest,
)
from ..services.email_templates import (
    render_po_approved_email,
    render_po_rejected_email,
    render_po_submitted_email,
    render_vendor_email,
)
from .repositories.po_repository import PORepository

logger = get_logger(__name__)


class POFacadeService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PORepository()
        self.settings = get_settings()

    # =========================================================================
    # Authorization Helpers
    # =========================================================================

    def _require_staff(self, user: User) -> None:
        if user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
            raise ForbiddenError(
                code=ErrorCode.STAFF_ONLY,
                message="Staff access required"
            )

    def _require_director(self, user: User) -> None:
        if user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
            raise ForbiddenError(
                code=ErrorCode.ADMIN_ONLY,
                message="Director access required for approvals"
            )

    def _require_owner_or_director(self, user: User, po_created_by_id: int) -> None:
        if (
            user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]
            and user.id != po_created_by_id
        ):
            raise ForbiddenError(
                code=ErrorCode.INSUFFICIENT_PERMISSIONS,
                message="Not authorized to modify this purchase order"
            )

    # =========================================================================
    # PO CRUD Operations
    # =========================================================================

    async def list_purchase_orders(
        self,
        status: Optional[PurchaseOrderStatus] = None,
        vendor_id: Optional[int] = None,
        fund_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 20,
        current_user: Optional[User] = None,
    ) -> PurchaseOrderListResponse:
        if current_user:
            self._require_staff(current_user)

        orders, total = await self.repo.list_purchase_orders(
            self.db,
            status=status,
            vendor_id=vendor_id,
            fund_id=fund_id,
            page=page,
            per_page=per_page,
        )

        return PurchaseOrderListResponse(
            items=[PurchaseOrderResponse.model_validate(o) for o in orders],
            total=total,
            page=page,
            per_page=per_page,
        )

    async def create_purchase_order(
        self,
        po_in: PurchaseOrderCreate,
        current_user: User,
    ) -> PurchaseOrderResponse:
        self._require_staff(current_user)

        # Validate fund exists and is active (skip for drafts without fund)
        fund = None
        order_date = po_in.order_date or date.today()
        if po_in.fund_id is not None:
            fund = await self.repo.get_fund_by_id(self.db, po_in.fund_id)
            if not fund:
                raise ResourceNotFoundError(
                    code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="Fund not found"
                )
            if fund.status != FundStatus.ACTIVE:
                raise ValidationError(
                    code=ErrorCode.INVALID_STATE,
                    message=f"Cannot create PO against fund '{fund.code}' - fund is {fund.status}"
                )

            # Validate order date matches fund fiscal year
            if order_date.year != fund.fiscal_year:
                raise ValidationError(
                    code=ErrorCode.INVALID_DATE,
                    message=f"Order date year ({order_date.year}) does not match fund fiscal year ({fund.fiscal_year})"
                )

        # Generate PO number
        po_number = f"PO-{datetime.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

        # Validate and sanitize notes
        sanitized_notes = po_in.notes
        if po_in.notes:
            validation = input_validator._validate_string_field("note", po_in.notes)
            if not validation.is_valid:
                raise ValidationError(
                    code=ErrorCode.VALIDATION_FAILED,
                    message=f"Invalid notes: {', '.join(validation.errors)}"
                )
            sanitized_notes = validation.sanitized_input

        po = PurchaseOrder(
            po_number=po_number,
            vendor_id=po_in.vendor_id,
            fund_id=po_in.fund_id,
            order_date=order_date,
            expected_delivery=po_in.expected_delivery,
            notes=sanitized_notes,
            created_by_id=current_user.id,
        )
        self.db.add(po)
        await self.db.flush()

        # Add items if provided
        total = Decimal("0.00")
        if po_in.items:
            for item_in in po_in.items:
                po_item = PurchaseOrderItem(
                    purchase_order_id=po.id,
                    **item_in.model_dump(),
                )
                self.db.add(po_item)
                total += Decimal(str(item_in.quantity)) * item_in.unit_price

        po.total_amount = total
        await self.db.commit()

        # Re-fetch with items loaded so total_items property works
        po = await self.repo.get_purchase_order_by_id(
            self.db, po.id, with_items=True, with_relationships=True
        )
        return PurchaseOrderResponse.model_validate(po)

    async def get_purchase_order(
        self,
        po_id: int,
        current_user: User,
    ) -> PurchaseOrderDetail:
        self._require_staff(current_user)

        po = await self.repo.get_purchase_order_by_id(
            self.db,
            po_id,
            with_items=True,
            with_relationships=True,
        )
        if not po:
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Purchase order not found"
            )

        return PurchaseOrderDetail.model_validate(po)

    async def update_purchase_order(
        self,
        po_id: int,
        po_in: PurchaseOrderUpdate,
        current_user: User,
    ) -> PurchaseOrderResponse:
        self._require_staff(current_user)

        po = await self.repo.get_purchase_order_by_id(
            self.db,
            po_id,
            with_items=True,
            with_relationships=True,
        )
        if not po:
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Purchase order not found"
            )

        if po.status != PurchaseOrderStatus.DRAFT:
            raise ValidationError(
                code=ErrorCode.INVALID_STATE,
                message="Can only update draft orders"
            )

        for field, value in po_in.model_dump(exclude_unset=True).items():
            setattr(po, field, value)

        await self.db.commit()
        # Refresh items + vendor/fund: vendor_id/fund_id may have changed in
        # this update, so the relationship cache loaded before commit could
        # be stale. PurchaseOrderResponse.model_validate reads po.vendor.name
        # and po.fund.name for the computed vendor_name/fund_name fields, so
        # missing-greenlet errors otherwise.
        await self.db.refresh(po, attribute_names=["items", "vendor", "fund"])
        return PurchaseOrderResponse.model_validate(po)

    async def delete_purchase_order(
        self,
        po_id: int,
        current_user: User,
    ) -> None:
        self._require_staff(current_user)

        po = await self.repo.get_purchase_order_by_id(self.db, po_id)
        if not po:
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Purchase order not found"
            )

        self._require_owner_or_director(current_user, po.created_by_id)

        if po.status != PurchaseOrderStatus.DRAFT:
            raise ValidationError(
                code=ErrorCode.INVALID_STATE,
                message="Can only delete draft purchase orders"
            )

        await self.db.delete(po)
        await self.db.commit()

    # =========================================================================
    # PO Items
    # =========================================================================

    async def add_po_item(
        self,
        po_id: int,
        item_in: POItemCreate,
        current_user: User,
    ) -> POItemResponse:
        self._require_staff(current_user)

        po = await self.repo.get_purchase_order_by_id(self.db, po_id)
        if not po:
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Purchase order not found"
            )

        if po.status != PurchaseOrderStatus.DRAFT:
            raise ValidationError(
                code=ErrorCode.INVALID_STATE,
                message="Can only add items to draft orders"
            )

        po_item = PurchaseOrderItem(
            purchase_order_id=po_id,
            **item_in.model_dump(),
        )
        self.db.add(po_item)

        # Update total
        po.total_amount = (po.total_amount or Decimal("0.00")) + (
            Decimal(str(item_in.quantity)) * item_in.unit_price
        )

        await self.db.commit()
        await self.db.refresh(po_item)
        return POItemResponse.model_validate(po_item)

    async def delete_po_item(
        self,
        po_id: int,
        item_id: int,
        current_user: User,
    ) -> None:
        self._require_staff(current_user)

        po = await self.repo.get_purchase_order_by_id(self.db, po_id)
        if not po:
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Purchase order not found"
            )

        self._require_owner_or_director(current_user, po.created_by_id)

        if po.status != PurchaseOrderStatus.DRAFT:
            raise ValidationError(
                code=ErrorCode.INVALID_STATE,
                message="Can only delete items from purchase orders in DRAFT status"
            )

        item = await self.repo.get_po_item_by_id(self.db, item_id, po_id)
        if not item:
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Line item not found"
            )

        await self.db.delete(item)

        # Recalculate total
        items = await self.repo.get_po_items_by_po_id(self.db, po_id)
        po.total_amount = sum(
            Decimal(str(i.quantity)) * i.unit_price for i in items if i.id != item_id
        )

        await self.db.commit()

    async def update_po_item(
        self,
        po_id: int,
        item_id: int,
        item_update: POItemUpdate,
        current_user: User,
    ) -> POItemResponse:
        self._require_staff(current_user)

        po = await self.repo.get_purchase_order_by_id(self.db, po_id)
        if not po:
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Purchase order not found"
            )

        self._require_owner_or_director(current_user, po.created_by_id)

        if po.status != PurchaseOrderStatus.DRAFT:
            raise ValidationError(
                code=ErrorCode.INVALID_STATE,
                message="Can only update items in purchase orders in DRAFT status"
            )

        item = await self.repo.get_po_item_by_id(self.db, item_id, po_id)
        if not item:
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Line item not found"
            )

        update_data = item_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)

        # Recalculate PO total
        items = await self.repo.get_po_items_by_po_id(self.db, po_id)
        po.total_amount = sum(Decimal(str(i.quantity)) * i.unit_price for i in items)

        await self.db.commit()
        await self.db.refresh(item)
        return POItemResponse.model_validate(item)

    # =========================================================================
    # PO Workflow
    # =========================================================================

    async def submit_for_approval(
        self,
        po_id: int,
        current_user: User,
        notify_directors_callback=None,
    ) -> PurchaseOrderResponse:
        self._require_staff(current_user)

        po = await self.repo.get_purchase_order_by_id(
            self.db,
            po_id,
            with_items=True,
            with_relationships=True,
        )
        if not po:
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Purchase order not found"
            )

        if po.status != PurchaseOrderStatus.DRAFT:
            raise ValidationError(
                code=ErrorCode.INVALID_STATE,
                message="Can only submit draft orders"
            )

        if not po.items:
            raise ValidationError(
                code=ErrorCode.VALIDATION_FAILED,
                message="Cannot submit order without items"
            )

        po.status = PurchaseOrderStatus.PENDING_APPROVAL
        await self.db.commit()
        await self.db.refresh(po, attribute_names=["items"])

        # Notify directors via callback if provided
        if notify_directors_callback:
            await notify_directors_callback(po)

        return PurchaseOrderResponse.model_validate(po)

    async def approve_purchase_order(
        self,
        po_id: int,
        current_user: User,
        notify_creator_callback=None,
    ) -> PurchaseOrderResponse:
        self._require_director(current_user)

        po = await self.repo.get_purchase_order_by_id(
            self.db,
            po_id,
            with_relationships=True,
        )
        if not po:
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Purchase order not found"
            )

        if po.status != PurchaseOrderStatus.PENDING_APPROVAL:
            raise ValidationError(
                code=ErrorCode.INVALID_STATE,
                message="Order is not pending approval"
            )

        po.status = PurchaseOrderStatus.APPROVED
        po.approved_by_id = current_user.id
        po.approved_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(po, attribute_names=["items"])

        # Notify creator via callback if provided
        if notify_creator_callback:
            approved_by_name = f"{current_user.first_name} {current_user.last_name}"
            await notify_creator_callback(po, approved_by_name)

        return PurchaseOrderResponse.model_validate(po)

    async def reject_purchase_order(
        self,
        po_id: int,
        request: RejectionRequest,
        current_user: User,
        notify_creator_callback=None,
    ) -> PurchaseOrderResponse:
        self._require_director(current_user)

        po = await self.repo.get_purchase_order_by_id(
            self.db,
            po_id,
            with_relationships=True,
        )
        if not po:
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Purchase order not found"
            )

        if po.status != PurchaseOrderStatus.PENDING_APPROVAL:
            raise ValidationError(
                code=ErrorCode.INVALID_STATE,
                message="Order is not pending approval"
            )

        # Validate and sanitize rejection notes
        sanitized_notes = request.notes
        if request.notes:
            validation = input_validator._validate_string_field("note", request.notes)
            if not validation.is_valid:
                raise ValidationError(
                    code=ErrorCode.VALIDATION_FAILED,
                    message=f"Invalid rejection notes: {', '.join(validation.errors)}"
                )
            sanitized_notes = validation.sanitized_input

        po.status = PurchaseOrderStatus.REJECTED
        po.rejection_notes = sanitized_notes

        await self.db.commit()
        await self.db.refresh(po, attribute_names=["items"])

        # Notify creator via callback if provided
        if notify_creator_callback:
            rejected_by_name = f"{current_user.first_name} {current_user.last_name}"
            await notify_creator_callback(po, rejected_by_name)

        return PurchaseOrderResponse.model_validate(po)

    async def submit_to_vendor(
        self,
        po_id: int,
        current_user: User,
    ) -> PurchaseOrderResponse:
        self._require_staff(current_user)

        po = await self.repo.get_purchase_order_by_id(
            self.db,
            po_id,
            with_relationships=True,
        )
        if not po:
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Purchase order not found"
            )

        if po.status != PurchaseOrderStatus.APPROVED:
            raise ValidationError(
                code=ErrorCode.INVALID_STATE,
                message="Order must be approved first"
            )

        # Validate fund exists and is active; re-fetch with row lock before
        # checking availability and mutating encumbered_amount (TOCTOU guard).
        fund = po.fund
        if not fund:
            raise ValidationError(
                code=ErrorCode.INVALID_STATE,
                message="Cannot submit PO - no fund assigned"
            )
        result = await self.db.execute(
            select(Fund).where(Fund.id == fund.id).with_for_update()
        )
        fund = result.scalar_one_or_none()
        if not fund:
            raise ValidationError(
                code=ErrorCode.INVALID_STATE,
                message="Cannot submit PO - fund not found"
            )
        if fund.status != FundStatus.ACTIVE:
            raise ValidationError(
                code=ErrorCode.INVALID_STATE,
                message=f"Cannot submit PO - fund '{fund.code}' is {fund.status}"
            )

        # Encumber budget
        if fund.available_amount < po.total_amount:
            raise BusinessLogicError(
                code=ErrorCode.INSUFFICIENT_INVENTORY,
                message="Insufficient funds available"
            )

        fund.encumbered_amount = (
            fund.encumbered_amount or Decimal("0.00")
        ) + po.total_amount
        po.status = PurchaseOrderStatus.SUBMITTED

        # Flush so PO status is visible to EDI processor (FK references)
        await self.db.flush()

        # Attempt EDI submission if vendor supports it
        edi_result = await self._try_edi_submit(po)
        if edi_result and not edi_result["success"]:
            logger.warning(
                "EDI submit failed for PO %s (continuing with manual): %s",
                po.po_number,
                edi_result.get("error"),
            )

        await self.db.commit()
        await self.db.refresh(po, attribute_names=["items"])
        return PurchaseOrderResponse.model_validate(po)

    async def _try_edi_submit(self, po: PurchaseOrder) -> dict | None:
        try:
            from .edi.edi_processor import EDIProcessor

            processor = EDIProcessor(self.db)
            profile = await processor.get_vendor_profile(po.vendor_id)
            if not profile or not profile.is_enabled or not profile.supports_orders:
                return None

            success, transaction, message = await processor.send_purchase_order(po.id)
            return {
                "success": success,
                "transaction_id": transaction.id if transaction else None,
                "error": message if not success else None,
            }
        except Exception as e:
            logger.exception(
                "EDI submit attempt failed for PO %s: %s", po.po_number, e
            )
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Receiving
    # =========================================================================

    async def receive_order(
        self,
        po_id: int,
        request: ReceiveItemsRequest,
        current_user: User,
        create_lifecycle_event_callback=None,
    ) -> PurchaseOrderResponse:
        self._require_staff(current_user)

        po = await self.repo.get_purchase_order_by_id(
            self.db,
            po_id,
            with_items=True,
            with_relationships=True,
        )
        if not po:
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Purchase order not found"
            )

        if po.status not in [
            PurchaseOrderStatus.SUBMITTED,
            PurchaseOrderStatus.PARTIALLY_RECEIVED,
        ]:
            raise ValidationError(
                code=ErrorCode.INVALID_STATE,
                message="Order must be submitted to receive items"
            )

        # Validate fund is not closed
        if po.fund and po.fund.status == FundStatus.CLOSED:
            raise BusinessLogicError(
                code=ErrorCode.INVALID_STATE,
                message=f"Cannot receive items - fund '{po.fund.code}' is closed. "
                "Reopen the fund first or transfer the PO to an active fund."
            )

        try:
            received_value = Decimal("0.00")
            all_received = True

            for recv in request.items:
                item_id = recv.get("item_id")
                qty = recv.get("received_quantity", 0)

                po_item = next((i for i in po.items if i.id == item_id), None)
                if not po_item:
                    continue

                new_received = (po_item.received_quantity or 0) + qty
                if new_received > (po_item.quantity or 0):
                    raise ValidationError(
                        code=ErrorCode.VALIDATION_FAILED,
                        message=f"Cannot receive {qty} of '{po_item.title}': "
                                f"would exceed ordered quantity "
                                f"({po_item.received_quantity or 0} already received of {po_item.quantity} ordered)"
                    )

                po_item.received_quantity = new_received
                received_value += Decimal(str(qty)) * po_item.unit_price

                # Find or create catalog item
                catalog_item = None
                if po_item.catalog_item_id:
                    catalog_item = await self.repo.get_catalog_item_by_id(
                        self.db, po_item.catalog_item_id
                    )

                if not catalog_item:
                    catalog_item = await self.repo.create_catalog_item(
                        self.db,
                        title=po_item.title,
                        author=po_item.author,
                        isbn=po_item.isbn,
                    )
                    po_item.catalog_item_id = catalog_item.id

                # Create item copies
                for copy_num in range(qty):
                    from .po_pdf import generate_barcode

                    barcode = generate_barcode()

                    copy_number = (
                        await self.repo.get_item_copy_count_for_catalog(
                            self.db, catalog_item.id
                        )
                    ) + 1

                    item_copy = await self.repo.create_item_copy(
                        self.db,
                        catalog_item_id=catalog_item.id,
                        barcode=barcode,
                        copy_number=copy_number,
                        condition="new",
                        acquisition_source="purchase",
                        purchase_order_item_id=po_item.id,
                        replacement_cost=po_item.unit_price,
                    )

                    # Enter processing queue at first step
                    item_copy.processing_step = ProcessingStep.RECEIVED

                    # Lifecycle events via callback if provided
                    if create_lifecycle_event_callback:
                        await create_lifecycle_event_callback(
                            item_copy_id=item_copy.id,
                            event_type=LifecycleEventType.ORDERED,
                            description=f"Ordered from {po.vendor.name if po.vendor else 'vendor'} via {po.po_number}",
                            metadata={
                                "po_number": po.po_number,
                                "po_id": po.id,
                                "vendor_id": po.vendor_id,
                                "vendor_name": po.vendor.name if po.vendor else None,
                                "unit_price": float(po_item.unit_price),
                                "fund_code": po.fund.code if po.fund else None,
                            },
                            performed_by_id=current_user.id,
                            related_po_id=po.id,
                        )

                        await create_lifecycle_event_callback(
                            item_copy_id=item_copy.id,
                            event_type=LifecycleEventType.RECEIVED,
                            description=f"Received from {po.vendor.name if po.vendor else 'vendor'}",
                            metadata={
                                "po_number": po.po_number,
                                "received_date": date.today().isoformat(),
                                "condition": "new",
                            },
                            performed_by_id=current_user.id,
                            related_po_id=po.id,
                        )

                if not po_item.is_fully_received:
                    all_received = False

            # Update fund
            fund = po.fund
            fund.encumbered_amount = max(
                (fund.encumbered_amount or Decimal("0.00")) - received_value,
                Decimal("0.00"),
            )
            fund.spent_amount = (fund.spent_amount or Decimal("0.00")) + received_value

            # Update PO status
            po.status = (
                PurchaseOrderStatus.RECEIVED
                if all_received
                else PurchaseOrderStatus.PARTIALLY_RECEIVED
            )
            if all_received:
                po.actual_delivery = date.today()

            await self.db.commit()
            await self.db.refresh(po, attribute_names=["items"])
            return PurchaseOrderResponse.model_validate(po)
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            await self.db.rollback()
            raise InternalServerError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to receive order: {str(e)}"
            ) from e

    async def receive_order_from_edi(
        self,
        po: PurchaseOrder,
        items_to_receive: list[dict],
    ) -> None:
        received_value = Decimal("0.00")
        all_received = True

        for recv in items_to_receive:
            item_id = recv.get("item_id")
            qty = recv.get("received_quantity", 0)
            if not qty:
                continue

            po_item = next((i for i in po.items if i.id == item_id), None)
            if not po_item:
                continue

            new_received = (po_item.received_quantity or 0) + qty
            if new_received > (po_item.quantity or 0):
                # Cap at ordered quantity -- don't over-receive
                qty = (po_item.quantity or 0) - (po_item.received_quantity or 0)
                if qty <= 0:
                    continue
                new_received = (po_item.received_quantity or 0) + qty

            po_item.received_quantity = new_received
            received_value += Decimal(str(qty)) * po_item.unit_price

            # Find or create catalog item
            catalog_item = None
            if po_item.catalog_item_id:
                catalog_item = await self.repo.get_catalog_item_by_id(
                    self.db, po_item.catalog_item_id
                )

            if not catalog_item:
                catalog_item = await self.repo.create_catalog_item(
                    self.db,
                    title=po_item.title,
                    author=po_item.author,
                    isbn=po_item.isbn,
                )
                po_item.catalog_item_id = catalog_item.id

            # Create item copies
            for _ in range(qty):
                from .po_pdf import generate_barcode

                barcode = generate_barcode()

                copy_number = (
                    await self.repo.get_item_copy_count_for_catalog(
                        self.db, catalog_item.id
                    )
                ) + 1

                item_copy = await self.repo.create_item_copy(
                    self.db,
                    catalog_item_id=catalog_item.id,
                    barcode=barcode,
                    copy_number=copy_number,
                    condition="new",
                    acquisition_source="purchase",
                    purchase_order_item_id=po_item.id,
                    replacement_cost=po_item.unit_price,
                )

                item_copy.processing_step = ProcessingStep.RECEIVED

            if not po_item.is_fully_received:
                all_received = False

        if received_value > 0:
            fund = po.fund
            fund.encumbered_amount = max(
                (fund.encumbered_amount or Decimal("0.00")) - received_value,
                Decimal("0.00"),
            )
            fund.spent_amount = (fund.spent_amount or Decimal("0.00")) + received_value

        po.status = (
            PurchaseOrderStatus.RECEIVED
            if all_received
            else PurchaseOrderStatus.PARTIALLY_RECEIVED
        )
        if all_received:
            po.actual_delivery = date.today()

    # =========================================================================
    # Batch Operations
    # =========================================================================

    async def batch_approve_purchase_orders(
        self,
        request: BatchApproveRequest,
        current_user: User,
    ) -> BatchApproveResponse:
        self._require_director(current_user)

        results: list[BatchApproveResult] = []
        approved_count = 0
        failed_count = 0
        total_amount_approved = Decimal("0.00")

        for po_id in request.po_ids:
            try:
                po = await self.repo.get_purchase_order_by_id(
                    self.db,
                    po_id,
                    with_relationships=True,
                )

                if not po:
                    results.append(BatchApproveResult(
                        po_id=po_id,
                        po_number=f"PO-{po_id}",
                        success=False,
                        error="Purchase order not found",
                    ))
                    failed_count += 1
                    continue

                if po.status != PurchaseOrderStatus.PENDING_APPROVAL:
                    results.append(BatchApproveResult(
                        po_id=po_id,
                        po_number=po.po_number,
                        success=False,
                        error=f"Order is not pending approval (status: {po.status})",
                    ))
                    failed_count += 1
                    continue

                # Validate fund has sufficient budget
                fund = po.fund
                if fund and fund.available_amount < po.total_amount:
                    results.append(BatchApproveResult(
                        po_id=po_id,
                        po_number=po.po_number,
                        success=False,
                        error=f"Insufficient funds. Available: ${fund.available_amount}, Required: ${po.total_amount}",
                        total_amount=po.total_amount,
                    ))
                    failed_count += 1
                    continue

                # Approve the PO
                po.status = PurchaseOrderStatus.APPROVED
                po.approved_by_id = current_user.id
                po.approved_at = datetime.now(timezone.utc)

                results.append(BatchApproveResult(
                    po_id=po_id,
                    po_number=po.po_number,
                    success=True,
                    total_amount=po.total_amount,
                ))
                approved_count += 1
                total_amount_approved += po.total_amount or Decimal("0.00")

            except (ValueError, TypeError, KeyError, AttributeError) as e:
                results.append(BatchApproveResult(
                    po_id=po_id,
                    po_number=f"PO-{po_id}",
                    success=False,
                    error=str(e),
                ))
                failed_count += 1

        await self.db.commit()

        return BatchApproveResponse(
            total_requested=len(request.po_ids),
            approved_count=approved_count,
            failed_count=failed_count,
            total_amount_approved=total_amount_approved,
            results=results,
        )

    async def receive_all_items(
        self,
        po_id: int,
        current_user: User,
        create_lifecycle_event_callback=None,
    ) -> PurchaseOrderResponse:
        self._require_staff(current_user)

        po = await self.repo.get_purchase_order_by_id(
            self.db,
            po_id,
            with_items=True,
            with_relationships=True,
        )
        if not po:
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Purchase order not found"
            )

        if po.status not in [
            PurchaseOrderStatus.SUBMITTED,
            PurchaseOrderStatus.PARTIALLY_RECEIVED,
        ]:
            raise ValidationError(
                code=ErrorCode.INVALID_STATE,
                message="Order must be submitted to receive items"
            )

        # Validate fund is not closed
        if po.fund and po.fund.status == FundStatus.CLOSED:
            raise BusinessLogicError(
                code=ErrorCode.INVALID_STATE,
                message=f"Cannot receive items - fund '{po.fund.code}' is closed."
            )

        try:
            # Build receive request for all unreceived items
            items_to_receive = []
            for po_item in po.items:
                unreceived_qty = (po_item.quantity or 0) - (po_item.received_quantity or 0)
                if unreceived_qty > 0:
                    items_to_receive.append({
                        "item_id": po_item.id,
                        "received_quantity": unreceived_qty,
                    })

            if not items_to_receive:
                raise ValidationError(
                    code=ErrorCode.INVALID_STATE,
                    message="All items have already been received"
                )

            # Use the existing receive_order method with all items
            receive_request = ReceiveItemsRequest(items=items_to_receive)
            return await self.receive_order(
                po_id,
                receive_request,
                current_user,
                create_lifecycle_event_callback=create_lifecycle_event_callback,
            )

        except (ResourceNotFoundError, ValidationError, BusinessLogicError, InternalServerError):
            raise
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            await self.db.rollback()
            raise InternalServerError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to receive all items: {str(e)}"
            ) from e
