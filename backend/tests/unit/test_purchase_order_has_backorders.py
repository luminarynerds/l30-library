# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for PurchaseOrder.has_backorders (derived, no DB needed)."""
from datetime import date

from app.models.acquisition import PurchaseOrder, PurchaseOrderItem


def _item(**kwargs) -> PurchaseOrderItem:
    defaults = dict(title="Test Book", quantity=1, unit_price=10)
    defaults.update(kwargs)
    return PurchaseOrderItem(**defaults)


def test_has_backorders_true_when_any_line_backordered():
    po = PurchaseOrder(po_number="PO-TEST-1", created_by_id=1)
    po.items = [
        _item(backordered_quantity=None),
        _item(backordered_quantity=3, expected_ship_date=date(2026, 8, 1)),
    ]
    assert po.has_backorders is True


def test_has_backorders_false_when_zero_or_none():
    po = PurchaseOrder(po_number="PO-TEST-2", created_by_id=1)
    po.items = [
        _item(backordered_quantity=None),
        _item(backordered_quantity=0),
    ]
    assert po.has_backorders is False


def test_has_backorders_false_when_no_items():
    po = PurchaseOrder(po_number="PO-TEST-3", created_by_id=1)
    po.items = []
    assert po.has_backorders is False
