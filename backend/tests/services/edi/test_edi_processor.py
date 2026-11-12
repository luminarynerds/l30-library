# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression test: ORDRSP backorder data persists to typed columns, not
just the free-text note.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.acquisition import (
    Fund, FundStatus, PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus,
    Vendor,
)
from app.models.edi import EDITransaction, VendorEDIProfile
from app.services.edi.edi_parser import ParsedLineItem, ParsedOrderResponse
from app.services.edi.edi_processor import EDIProcessor


async def _make_po_with_item(db_session, staff_user, *, isbn="9780000000001") -> PurchaseOrder:
    vendor = Vendor(name="Test Vendor EDI", is_active=True)
    db_session.add(vendor)
    await db_session.flush()

    fund = Fund(
        code="EDI-TEST-FUND",
        name="EDI Test Fund",
        fiscal_year=2026,
        allocated_amount=Decimal("1000.00"),
        status=FundStatus.ACTIVE,
    )
    db_session.add(fund)
    await db_session.flush()

    po = PurchaseOrder(
        po_number="PO-EDI-BACKORDER-TEST",
        vendor_id=vendor.id,
        fund_id=fund.id,
        status=PurchaseOrderStatus.SUBMITTED,
        total_amount=Decimal("50.00"),
        created_by_id=staff_user.id,
    )
    db_session.add(po)
    await db_session.flush()

    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Backordered Book",
        isbn=isbn,
        quantity=5,
        unit_price=Decimal("10.00"),
    )
    db_session.add(item)
    await db_session.commit()

    result = await db_session.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == po.id)
    )
    return result.scalar_one()


async def _make_profile_and_transaction(
    db_session, po: PurchaseOrder, control_number: str, profile: VendorEDIProfile | None = None
):
    if profile is None:
        profile = VendorEDIProfile(vendor_id=po.vendor_id, is_enabled=True)
        db_session.add(profile)
        await db_session.flush()

    transaction = EDITransaction(
        vendor_edi_profile_id=profile.id,
        purchase_order_id=po.id,
        message_type="ORDRSP",
        direction="inbound",
        interchange_control_number=control_number,
    )
    db_session.add(transaction)
    await db_session.flush()
    return profile, transaction


@pytest.mark.asyncio
async def test_ordrsp_persists_backorder_columns(db_session, staff_user):
    """A backordered line writes backordered_quantity + expected_ship_date
    + last_status_at, not just the notes string (regression against the
    old notes-only behavior)."""
    po = await _make_po_with_item(db_session, staff_user, isbn="9780000000001")
    profile, transaction = await _make_profile_and_transaction(
        db_session, po, "EDITEST0001"
    )

    ship_date = datetime.now() + timedelta(days=10)
    parsed = ParsedOrderResponse(
        purchase_order_number=po.po_number,
        response_code="AC",
        line_items=[
            ParsedLineItem(
                isbn="9780000000001",
                quantity=5,
                quantity_backordered=3,
                expected_ship_date=ship_date,
            )
        ],
    )

    processor = EDIProcessor(db_session)
    await processor._process_order_response(transaction, parsed, profile, po)
    await db_session.commit()

    result = await db_session.execute(
        select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == po.id)
    )
    item = result.scalar_one()

    assert item.backordered_quantity == 3
    assert item.expected_ship_date == ship_date.date()
    assert item.last_status_at is not None
    # Existing note behavior unchanged
    assert item.notes is not None
    assert "backordered" in item.notes.lower()


@pytest.mark.asyncio
async def test_ordrsp_clears_backorder_when_resolved(db_session, staff_user):
    """A later ORDRSP reporting quantity_backordered=0 clears the field so
    the per-line view stays current (goal: 'kept current automatically')."""
    po = await _make_po_with_item(db_session, staff_user, isbn="9780000000002")
    profile, transaction1 = await _make_profile_and_transaction(
        db_session, po, "EDITEST0002"
    )

    first = ParsedOrderResponse(
        purchase_order_number=po.po_number,
        response_code="AC",
        line_items=[
            ParsedLineItem(
                isbn="9780000000002",
                quantity=5,
                quantity_backordered=5,
                expected_ship_date=datetime.now() + timedelta(days=5),
            )
        ],
    )
    processor = EDIProcessor(db_session)
    await processor._process_order_response(transaction1, first, profile, po)
    await db_session.commit()

    _, transaction2 = await _make_profile_and_transaction(
        db_session, po, "EDITEST0003", profile=profile
    )
    second = ParsedOrderResponse(
        purchase_order_number=po.po_number,
        response_code="AC",
        line_items=[
            ParsedLineItem(isbn="9780000000002", quantity=5, quantity_backordered=0)
        ],
    )
    await processor._process_order_response(transaction2, second, profile, po)
    await db_session.commit()

    result = await db_session.execute(
        select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == po.id)
    )
    item = result.scalar_one()
    assert item.backordered_quantity == 0
    assert item.expected_ship_date is None


@pytest.mark.asyncio
async def test_ordrsp_no_regression_when_not_backordered(db_session, staff_user):
    """A fully-accepted line (no backorder reported) leaves backordered_quantity
    null and does not add a backorder note -- existing ORDERS/ORDRSP flow
    untouched."""
    po = await _make_po_with_item(db_session, staff_user, isbn="9780000000003")
    profile, transaction = await _make_profile_and_transaction(
        db_session, po, "EDITEST0004"
    )

    parsed = ParsedOrderResponse(
        purchase_order_number=po.po_number,
        response_code="AC",
        line_items=[
            ParsedLineItem(isbn="9780000000003", quantity=5, quantity_accepted=5)
        ],
    )
    processor = EDIProcessor(db_session)
    await processor._process_order_response(transaction, parsed, profile, po)
    await db_session.commit()

    result = await db_session.execute(
        select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == po.id)
    )
    item = result.scalar_one()
    assert item.backordered_quantity is None
    assert item.last_status_at is not None
    assert item.notes is None
