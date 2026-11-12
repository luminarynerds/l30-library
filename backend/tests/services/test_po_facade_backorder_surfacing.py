# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""End-to-end: a PO item with backorder data, fetched through
POFacadeService.get_purchase_order (the same path GET /purchase-orders/{id}
uses), surfaces backordered_quantity/expected_ship_date and has_backorders."""
from datetime import date
from decimal import Decimal

import pytest

from app.models.acquisition import (
    Fund, FundStatus, PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus,
    Vendor,
)
from app.services.po_facade_service import POFacadeService


@pytest.mark.asyncio
async def test_get_purchase_order_surfaces_backorder_fields(db_session, staff_user):
    vendor = Vendor(name="Facade Test Vendor", is_active=True)
    db_session.add(vendor)
    await db_session.flush()

    fund = Fund(
        code="FACADE-TEST-FUND",
        name="Facade Test Fund",
        fiscal_year=2026,
        allocated_amount=Decimal("1000.00"),
        status=FundStatus.ACTIVE,
    )
    db_session.add(fund)
    await db_session.flush()

    po = PurchaseOrder(
        po_number="PO-FACADE-BACKORDER-TEST",
        vendor_id=vendor.id,
        fund_id=fund.id,
        status=PurchaseOrderStatus.SUBMITTED,
        total_amount=Decimal("20.00"),
        created_by_id=staff_user.id,
    )
    db_session.add(po)
    await db_session.flush()

    backordered_item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Backordered Line",
        quantity=2,
        unit_price=Decimal("10.00"),
        backordered_quantity=1,
        expected_ship_date=date(2026, 8, 15),
    )
    clean_item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Fully Available Line",
        quantity=1,
        unit_price=Decimal("10.00"),
        backordered_quantity=0,
    )
    db_session.add_all([backordered_item, clean_item])
    await db_session.commit()

    facade = POFacadeService(db_session)
    detail = await facade.get_purchase_order(po.id, staff_user)

    assert detail.has_backorders is True
    items_by_title = {i.title: i for i in detail.items}
    assert items_by_title["Backordered Line"].backordered_quantity == 1
    assert items_by_title["Backordered Line"].expected_ship_date == date(2026, 8, 15)
    assert items_by_title["Fully Available Line"].backordered_quantity == 0
