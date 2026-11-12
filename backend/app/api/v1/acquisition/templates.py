# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Acquisition - Order Template API Endpoints

Provides endpoints for:
- Order template CRUD
- Creating POs from templates
- Saving existing POs as templates
"""
import json
from app.core.logging import get_logger
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.error_codes import ErrorCode
from ....core.exceptions import APIError, InternalServerError
from ....models.acquisition import (
    Fund,
    FundStatus,
    OrderTemplate,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)
from ....models.user import User, UserRole
from ....schemas.acquisition import (
    CreatePOFromTemplateRequest,
    OrderTemplateCreate,
    OrderTemplateResponse,
    OrderTemplateUpdate,
    SaveAsTemplateRequest,
    TemplateItemBase,
)
from ..auth import get_current_user
from ..dependencies import check_staff_access

logger = get_logger(__name__)

router = APIRouter(prefix="/acquisition", tags=["acquisition-templates"])

ADMIN_ROLES = {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR}




def _is_admin(user: User) -> bool:
    return user.role in ADMIN_ROLES


def _parse_template_items(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        items = json.loads(raw)
        return items if isinstance(items, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _serialize_template_items(items: list[TemplateItemBase] | None) -> str:
    if not items:
        return "[]"
    return json.dumps(
        [item.model_dump(mode="json") for item in items]
    )


def _build_response(template: OrderTemplate) -> OrderTemplateResponse:
    items = _parse_template_items(template.template_items)
    return OrderTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        vendor_id=template.vendor_id,
        fund_id=template.fund_id,
        is_shared=template.is_shared,
        created_by_id=template.created_by_id,
        created_by_name=(
            template.created_by.full_name
            if template.created_by
            else None
        ),
        vendor_name=template.vendor.name if template.vendor else None,
        fund_name=template.fund.name if template.fund else None,
        template_items=[TemplateItemBase(**i) for i in items],
        item_count=len(items),
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


# ============ Order Template CRUD ============


@router.get("/order-templates", response_model=list[OrderTemplateResponse])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List order templates (own + shared)."""
    check_staff_access(current_user)
    try:
        result = await db.execute(
            select(OrderTemplate)
            .where(
                or_(
                    OrderTemplate.created_by_id == current_user.id,
                    OrderTemplate.is_shared == True,  # noqa: E712
                )
            )
            .options(
                selectinload(OrderTemplate.vendor),
                selectinload(OrderTemplate.fund),
                selectinload(OrderTemplate.created_by),
            )
            .order_by(OrderTemplate.name)
        )
        templates = result.scalars().all()
        return [_build_response(t) for t in templates]
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to list order templates")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.get("/order-templates/{template_id}", response_model=OrderTemplateResponse)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single order template."""
    check_staff_access(current_user)
    try:
        result = await db.execute(
            select(OrderTemplate)
            .where(OrderTemplate.id == template_id)
            .options(
                selectinload(OrderTemplate.vendor),
                selectinload(OrderTemplate.fund),
                selectinload(OrderTemplate.created_by),
            )
        )
        template = result.scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=404, detail="Order template not found")

        # Check access: own or shared
        if template.created_by_id != current_user.id and not template.is_shared and not _is_admin(current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this template")

        return _build_response(template)
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to get order template")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.post("/order-templates", response_model=OrderTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: OrderTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new order template."""
    check_staff_access(current_user)
    try:
        template = OrderTemplate(
            name=payload.name,
            description=payload.description,
            vendor_id=payload.vendor_id,
            fund_id=payload.fund_id,
            is_shared=payload.is_shared,
            created_by_id=current_user.id,
            template_items=_serialize_template_items(payload.template_items),
        )
        db.add(template)
        await db.commit()
        await db.refresh(template)

        # Re-fetch with relationships
        result = await db.execute(
            select(OrderTemplate)
            .where(OrderTemplate.id == template.id)
            .options(
                selectinload(OrderTemplate.vendor),
                selectinload(OrderTemplate.fund),
                selectinload(OrderTemplate.created_by),
            )
        )
        template = result.scalar_one()
        logger.info(f"Created order template '{template.name}' by user {current_user.id}")
        return _build_response(template)
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to create order template")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.patch("/order-templates/{template_id}", response_model=OrderTemplateResponse)
async def update_template(
    template_id: int,
    payload: OrderTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an order template (own only, unless admin)."""
    check_staff_access(current_user)
    try:
        result = await db.execute(
            select(OrderTemplate).where(OrderTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=404, detail="Order template not found")

        # Ownership check
        if template.created_by_id != current_user.id and not _is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this template",
            )

        update_data = payload.model_dump(exclude_unset=True)

        # Handle template_items serialization
        if "template_items" in update_data and update_data["template_items"] is not None:
            update_data["template_items"] = _serialize_template_items(payload.template_items)
        elif "template_items" in update_data and update_data["template_items"] is None:
            update_data["template_items"] = "[]"

        for field, value in update_data.items():
            setattr(template, field, value)

        template.updated_at = datetime.now(timezone.utc)
        await db.commit()

        # Re-fetch with relationships
        result = await db.execute(
            select(OrderTemplate)
            .where(OrderTemplate.id == template.id)
            .options(
                selectinload(OrderTemplate.vendor),
                selectinload(OrderTemplate.fund),
                selectinload(OrderTemplate.created_by),
            )
        )
        template = result.scalar_one()
        logger.info(f"Updated order template {template_id} by user {current_user.id}")
        return _build_response(template)
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to update order template")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.delete("/order-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an order template (own only, unless admin)."""
    check_staff_access(current_user)
    try:
        result = await db.execute(
            select(OrderTemplate).where(OrderTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=404, detail="Order template not found")

        # Ownership check
        if template.created_by_id != current_user.id and not _is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this template",
            )

        await db.delete(template)
        await db.commit()
        logger.info(f"Deleted order template {template_id} by user {current_user.id}")
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to delete order template")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


# ============ Template <-> PO Operations ============


@router.post("/order-templates/{template_id}/create-po")
async def create_po_from_template(
    template_id: int,
    payload: CreatePOFromTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new Purchase Order from a template."""
    check_staff_access(current_user)
    try:
        # 1. Load template
        result = await db.execute(
            select(OrderTemplate)
            .where(OrderTemplate.id == template_id)
            .options(
                selectinload(OrderTemplate.vendor),
                selectinload(OrderTemplate.fund),
            )
        )
        template = result.scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=404, detail="Order template not found")

        # Check access
        if template.created_by_id != current_user.id and not template.is_shared and not _is_admin(current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to use this template")

        # 2. Resolve vendor and fund (payload overrides template defaults)
        vendor_id = payload.vendor_id or template.vendor_id
        fund_id = payload.fund_id or template.fund_id

        # Validate fund if provided
        if fund_id:
            fund_result = await db.execute(select(Fund).where(Fund.id == fund_id))
            fund = fund_result.scalar_one_or_none()
            if not fund:
                raise HTTPException(status_code=400, detail="Selected fund not found")
            if fund.status != FundStatus.ACTIVE:
                raise HTTPException(status_code=400, detail=f"Fund '{fund.name}' is not active")

        # 3. Generate PO number
        from sqlalchemy import func
        count_result = await db.execute(select(func.count()).select_from(PurchaseOrder))
        po_count = count_result.scalar() or 0
        po_number = f"PO-{datetime.now().strftime('%Y%m')}-{po_count + 1:04d}"

        # 4. Create PurchaseOrder in DRAFT status
        po = PurchaseOrder(
            po_number=po_number,
            vendor_id=vendor_id,
            fund_id=fund_id,
            order_date=date.today(),
            notes=payload.notes or f"Created from template: {template.name}",
            created_by_id=current_user.id,
            status=PurchaseOrderStatus.DRAFT,
        )
        db.add(po)
        await db.flush()

        # 5. Create PurchaseOrderItem for each template item
        items = _parse_template_items(template.template_items)
        total = Decimal("0.00")
        for item_data in items:
            quantity = item_data.get("quantity", 1)
            unit_price = Decimal(str(item_data.get("unit_price", 0) or 0))
            po_item = PurchaseOrderItem(
                purchase_order_id=po.id,
                title=item_data.get("title", "Untitled"),
                author=item_data.get("author"),
                isbn=item_data.get("isbn"),
                quantity=quantity,
                unit_price=unit_price,
                notes=item_data.get("notes"),
            )
            db.add(po_item)
            total += Decimal(str(quantity)) * unit_price

        po.total_amount = total
        await db.commit()

        logger.info(f"Created PO {po.po_number} from template '{template.name}' by user {current_user.id}")
        return {
            "id": po.id,
            "po_number": po.po_number,
            "items_added": len(items),
            "total_amount": float(total),
        }
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to create PO from template")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.post("/purchase-orders/{po_id}/save-as-template", response_model=OrderTemplateResponse)
async def save_po_as_template(
    po_id: int,
    payload: SaveAsTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save an existing PO as a reusable template."""
    check_staff_access(current_user)
    try:
        # 1. Load PO with items
        result = await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id)
            .options(selectinload(PurchaseOrder.items))
        )
        po = result.scalar_one_or_none()
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        # 2. Serialize PO items to template_items JSON
        template_items = []
        for item in po.items:
            template_items.append({
                "title": item.title,
                "author": item.author,
                "isbn": item.isbn,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price) if item.unit_price else None,
                "notes": item.notes,
            })

        # 3. Create OrderTemplate
        template = OrderTemplate(
            name=payload.name,
            description=payload.description,
            vendor_id=po.vendor_id,
            fund_id=po.fund_id,
            created_by_id=current_user.id,
            is_shared=payload.is_shared,
            template_items=json.dumps(template_items),
        )
        db.add(template)
        await db.commit()
        await db.refresh(template)

        # Re-fetch with relationships
        result = await db.execute(
            select(OrderTemplate)
            .where(OrderTemplate.id == template.id)
            .options(
                selectinload(OrderTemplate.vendor),
                selectinload(OrderTemplate.fund),
                selectinload(OrderTemplate.created_by),
            )
        )
        template = result.scalar_one()
        logger.info(f"Saved PO {po.po_number} as template '{template.name}' by user {current_user.id}")
        return _build_response(template)
    except (HTTPException, APIError):
        raise
    except Exception:
        logger.exception("Failed to save PO as template")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None
