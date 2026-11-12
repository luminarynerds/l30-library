# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests: POItemResponse / PurchaseOrderResponse expose backorder fields."""
from datetime import date, datetime
from decimal import Decimal

from app.models.acquisition import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from app.schemas.acquisition import POItemResponse, PurchaseOrderResponse


def test_po_item_response_includes_backorder_fields():
    item = PurchaseOrderItem(
        id=1,
        purchase_order_id=1,
        title="Backordered Book",
        quantity=5,
        unit_price=10,
        received_quantity=0,
        backordered_quantity=3,
        expected_ship_date=date(2026, 8, 1),
        last_status_at=datetime(2026, 7, 9, 12, 0, 0),
    )
    resp = POItemResponse.model_validate(item)
    assert resp.backordered_quantity == 3
    assert resp.expected_ship_date == date(2026, 8, 1)
    assert resp.last_status_at == datetime(2026, 7, 9, 12, 0, 0)


def test_purchase_order_response_includes_has_backorders():
    po = PurchaseOrder(
        id=1,
        po_number="PO-1",
        created_by_id=1,
        status=PurchaseOrderStatus.SUBMITTED,
        total_amount=Decimal("10.00"),
    )
    po.items = [
        PurchaseOrderItem(title="A", quantity=1, unit_price=1, backordered_quantity=2),
    ]
    resp = PurchaseOrderResponse.model_validate(po)
    assert resp.has_backorders is True
