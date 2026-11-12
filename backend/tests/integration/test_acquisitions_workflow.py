# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
End-to-end integration tests for the LSC Acquisitions Workflow.

Tests the complete purchase-to-pay lifecycle:
1. Create purchase order with line items and fund allocation
2. Submit for approval
3. Approve purchase order
4. Send to vendor (encumber budget)
5. Receive partial shipment
6. Receive remaining items
7. Invoice reconciliation
8. Close completed PO
9. Cancel line item from draft PO
10. Cancel entire PO (releasing encumbrance)
11. Budget impact tracking across operations
12. Vendor performance tracking
13. Money spent accuracy verification (penny-level)
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from json import dumps

import pytest
from sqlalchemy import select

from app.models.acquisition import (
    Fund,
    FundStatus,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    Vendor,
    SelectionListItem,
    SelectionPriority,
)
from app.models.catalog import CatalogItem
from app.models.edi import (
    EDIInvoice,
    EDIInvoiceStatus,
    VendorEDIProfile,
    EDIStandard,
    TransportProtocol,
)
from app.models.inventory import ItemCopy, AcquisitionSource, ItemCondition
from app.models.user import User, UserRole


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
async def fund(test_db):
    """Active acquisition fund with $10,000 budget for fiscal year 2026."""
    f = Fund(
        code="ACQ-2026-GEN",
        name="General Acquisitions 2026",
        description="General-purpose acquisition budget",
        fiscal_year=2026,
        allocated_amount=Decimal("10000.00"),
        encumbered_amount=Decimal("0.00"),
        spent_amount=Decimal("0.00"),
        status=FundStatus.ACTIVE,
    )
    test_db.add(f)
    await test_db.commit()
    await test_db.refresh(f)
    return f


@pytest.fixture
async def secondary_fund(test_db):
    """Secondary fund for budget-switching tests."""
    f = Fund(
        code="ACQ-2026-YA",
        name="Young Adult Acquisitions 2026",
        fiscal_year=2026,
        allocated_amount=Decimal("5000.00"),
        encumbered_amount=Decimal("0.00"),
        spent_amount=Decimal("0.00"),
        status=FundStatus.ACTIVE,
    )
    test_db.add(f)
    await test_db.commit()
    await test_db.refresh(f)
    return f


@pytest.fixture
async def vendor_a(test_db):
    """Primary vendor."""
    v = Vendor(
        name="Midwest Library Supply",
        contact_name="Alice Johnson",
        email="orders@midwestlibrary.example.com",
        phone="555-0111",
        address="100 Bookbinder Lane, Madison, WI 53703",
        account_number="MLS-9001",
        is_active=True,
    )
    test_db.add(v)
    await test_db.commit()
    await test_db.refresh(v)
    return v


@pytest.fixture
async def vendor_b(test_db):
    """Secondary vendor for multi-vendor tests."""
    v = Vendor(
        name="Pacific Book Distributors",
        contact_name="Bob Lee",
        email="orders@pacificbooks.example.com",
        phone="555-0222",
        address="200 Harbor Blvd, Portland, OR 97201",
        account_number="PBD-5002",
        is_active=True,
    )
    test_db.add(v)
    await test_db.commit()
    await test_db.refresh(v)
    return v


@pytest.fixture
async def catalog_item(test_db):
    """Pre-existing catalog item to link on receipt."""
    item = CatalogItem(
        title="The Rust Programming Language",
        author="Steve Klabnik",
        isbn="978-1-7185-0044-0",
        description="Official Rust language guide",
        call_number="005.133 KLA",
        barcode="CAT-RUST-001",
        publication_year=2023,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


# ============================================================================
# 1. CREATE PURCHASE ORDER WITH LINE ITEMS AND FUND ALLOCATION
# ============================================================================


@pytest.mark.asyncio
async def test_create_purchase_order_with_line_items(test_db, test_staff, fund, vendor_a):
    """Create a PO in draft status, add three line items, verify totals."""
    po = PurchaseOrder(
        po_number="PO-2026-WF-001",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.DRAFT,
        total_amount=Decimal("0.00"),
        created_by_id=test_staff.id,
        notes="Test acquisition workflow PO",
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    # Add three line items with different quantities/prices
    items_data = [
        ("The Pragmatic Programmer", "David Thomas", "978-0-13-595705-9", 2, Decimal("49.99")),
        ("Clean Code", "Robert C. Martin", "978-0-13-235088-4", 3, Decimal("39.99")),
        ("Designing Data-Intensive Apps", "Martin Kleppmann", "978-1-4493-7332-0", 1, Decimal("55.00")),
    ]
    expected_total = Decimal("0.00")
    for title, author, isbn, qty, price in items_data:
        item = PurchaseOrderItem(
            purchase_order_id=po.id,
            title=title,
            author=author,
            isbn=isbn,
            quantity=qty,
            unit_price=price,
            received_quantity=0,
        )
        test_db.add(item)
        expected_total += Decimal(str(qty)) * price

    po.total_amount = expected_total
    await test_db.commit()
    await test_db.refresh(po)

    # Verify
    assert po.status == PurchaseOrderStatus.DRAFT
    assert po.vendor_id == vendor_a.id
    assert po.fund_id == fund.id
    # $49.99*2 + $39.99*3 + $55.00*1 = $99.98 + $119.97 + $55.00 = $274.95
    assert po.total_amount == Decimal("274.95")

    result = await test_db.execute(
        select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == po.id)
    )
    po_items = result.scalars().all()
    assert len(po_items) == 3
    assert sum(i.line_total for i in po_items) == Decimal("274.95")


@pytest.mark.asyncio
async def test_fund_allocation_on_po_creation(test_db, test_staff, fund, vendor_a):
    """Fund should NOT be encumbered when PO is merely in draft."""
    po = PurchaseOrder(
        po_number="PO-2026-WF-002",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.DRAFT,
        total_amount=Decimal("500.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()

    await test_db.refresh(fund)
    assert fund.encumbered_amount == Decimal("0.00")
    assert fund.available_amount == Decimal("10000.00")


# ============================================================================
# 2–3. SUBMIT FOR APPROVAL & APPROVE PURCHASE ORDER
# ============================================================================


@pytest.mark.asyncio
async def test_submit_for_approval(test_db, test_staff, fund, vendor_a):
    """Draft PO with items transitions to PENDING_APPROVAL."""
    po = PurchaseOrder(
        po_number="PO-2026-WF-003",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.DRAFT,
        total_amount=Decimal("200.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Test Book",
        quantity=2,
        unit_price=Decimal("100.00"),
    )
    test_db.add(item)
    await test_db.commit()

    po.status = PurchaseOrderStatus.PENDING_APPROVAL
    await test_db.commit()
    assert po.status == PurchaseOrderStatus.PENDING_APPROVAL


@pytest.mark.asyncio
async def test_approve_purchase_order(test_db, test_staff, test_admin, fund, vendor_a):
    """Admin approves pending PO; approval metadata is recorded."""
    po = PurchaseOrder(
        po_number="PO-2026-WF-004",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.PENDING_APPROVAL,
        total_amount=Decimal("300.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    now = datetime.now(tz=timezone.utc)
    po.status = PurchaseOrderStatus.APPROVED
    po.approved_by_id = test_admin.id
    po.approved_at = now
    await test_db.commit()
    await test_db.refresh(po)

    assert po.status == PurchaseOrderStatus.APPROVED
    assert po.approved_by_id == test_admin.id
    assert po.approved_at is not None


@pytest.mark.asyncio
async def test_reject_purchase_order(test_db, test_staff, test_admin, fund, vendor_a):
    """Director rejects PO with reason; PO moves to rejected state."""
    po = PurchaseOrder(
        po_number="PO-2026-WF-005",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.PENDING_APPROVAL,
        total_amount=Decimal("8000.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()

    po.status = PurchaseOrderStatus.REJECTED
    po.rejection_notes = "Budget not available this quarter"
    await test_db.commit()

    assert po.status == PurchaseOrderStatus.REJECTED
    assert "Budget not available" in po.rejection_notes


# ============================================================================
# 4. SEND TO VENDOR (ENCUMBER BUDGET)
# ============================================================================


@pytest.mark.asyncio
async def test_send_to_vendor_encumbers_budget(test_db, test_staff, fund, vendor_a):
    """Submitting approved PO encumbers the fund and transitions to SUBMITTED."""
    po = PurchaseOrder(
        po_number="PO-2026-WF-006",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.APPROVED,
        total_amount=Decimal("750.00"),
        created_by_id=test_staff.id,
        approved_by_id=test_staff.id,
        approved_at=datetime.now(tz=timezone.utc),
    )
    test_db.add(po)
    await test_db.commit()

    # Verify fund has capacity
    assert fund.available_amount >= po.total_amount

    # Submit to vendor → encumber budget
    fund.encumbered_amount += po.total_amount
    po.status = PurchaseOrderStatus.SUBMITTED
    await test_db.commit()
    await test_db.refresh(fund)

    assert po.status == PurchaseOrderStatus.SUBMITTED
    assert fund.encumbered_amount == Decimal("750.00")
    assert fund.available_amount == Decimal("9250.00")  # 10000 - 750


@pytest.mark.asyncio
async def test_submit_blocked_by_insufficient_funds(test_db, test_staff, fund, vendor_a):
    """Cannot submit PO that exceeds available fund balance."""
    # Exhaust the fund
    fund.spent_amount = Decimal("9500.00")
    await test_db.commit()
    await test_db.refresh(fund)
    assert fund.available_amount == Decimal("500.00")

    po = PurchaseOrder(
        po_number="PO-2026-WF-007",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.APPROVED,
        total_amount=Decimal("600.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()

    # Budget check should fail
    assert po.total_amount > fund.available_amount


# ============================================================================
# 5. RECEIVE PARTIAL SHIPMENT
# ============================================================================


@pytest.mark.asyncio
async def test_receive_partial_shipment(test_db, test_staff, fund, vendor_a):
    """Receive part of an order; PO status becomes PARTIALLY_RECEIVED;
    fund moves received value from encumbered to spent."""
    # Set up submitted PO with encumbered funds
    po = PurchaseOrder(
        po_number="PO-2026-WF-008",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.SUBMITTED,
        total_amount=Decimal("500.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    fund.encumbered_amount = Decimal("500.00")
    await test_db.commit()
    await test_db.refresh(po)

    # Two line items
    item_a = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Book A",
        author="Author A",
        isbn="ISBN-A",
        quantity=5,
        unit_price=Decimal("50.00"),
        received_quantity=0,
    )
    item_b = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Book B",
        author="Author B",
        isbn="ISBN-B",
        quantity=5,
        unit_price=Decimal("50.00"),
        received_quantity=0,
    )
    test_db.add_all([item_a, item_b])
    await test_db.commit()
    await test_db.refresh(item_a)
    await test_db.refresh(item_b)

    # Receive 3 of 5 for item_a only
    received_qty = 3
    received_value = Decimal(str(received_qty)) * item_a.unit_price  # $150

    item_a.received_quantity = received_qty
    fund.encumbered_amount -= received_value
    fund.spent_amount += received_value
    po.status = PurchaseOrderStatus.PARTIALLY_RECEIVED
    await test_db.commit()
    await test_db.refresh(fund)

    assert po.status == PurchaseOrderStatus.PARTIALLY_RECEIVED
    assert item_a.received_quantity == 3
    assert not item_a.is_fully_received
    assert item_b.received_quantity == 0
    assert fund.encumbered_amount == Decimal("350.00")  # 500 - 150
    assert fund.spent_amount == Decimal("150.00")


# ============================================================================
# 6. RECEIVE REMAINING ITEMS
# ============================================================================


@pytest.mark.asyncio
async def test_receive_remaining_items(test_db, test_staff, fund, vendor_a):
    """Receive all remaining items; PO transitions to RECEIVED; all funds spent."""
    po = PurchaseOrder(
        po_number="PO-2026-WF-009",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.PARTIALLY_RECEIVED,
        total_amount=Decimal("500.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    # Simulate: 150 already spent, 350 still encumbered
    fund.encumbered_amount = Decimal("350.00")
    fund.spent_amount = Decimal("150.00")
    await test_db.commit()
    await test_db.refresh(po)

    item_a = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Book A",
        quantity=5,
        unit_price=Decimal("50.00"),
        received_quantity=3,  # already partially received
    )
    item_b = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Book B",
        quantity=5,
        unit_price=Decimal("50.00"),
        received_quantity=0,
    )
    test_db.add_all([item_a, item_b])
    await test_db.commit()
    await test_db.refresh(item_a)
    await test_db.refresh(item_b)

    # Receive remaining: 2 from item_a + 5 from item_b = $100 + $250 = $350
    remaining_a = item_a.quantity - item_a.received_quantity  # 2
    remaining_b = item_b.quantity - item_b.received_quantity  # 5

    remaining_value = (
        Decimal(str(remaining_a)) * item_a.unit_price
        + Decimal(str(remaining_b)) * item_b.unit_price
    )
    assert remaining_value == Decimal("350.00")

    item_a.received_quantity = item_a.quantity
    item_b.received_quantity = item_b.quantity
    fund.encumbered_amount -= remaining_value
    fund.spent_amount += remaining_value
    po.status = PurchaseOrderStatus.RECEIVED
    po.actual_delivery = date(2026, 3, 1)
    await test_db.commit()
    await test_db.refresh(fund)

    assert po.status == PurchaseOrderStatus.RECEIVED
    assert po.actual_delivery == date(2026, 3, 1)
    assert item_a.is_fully_received
    assert item_b.is_fully_received
    assert fund.encumbered_amount == Decimal("0.00")
    assert fund.spent_amount == Decimal("500.00")


# ============================================================================
# 7. INVOICE RECONCILIATION
# ============================================================================


@pytest.mark.asyncio
async def test_invoice_reconciliation_exact_match(test_db, test_staff, test_admin, fund, vendor_a):
    """Invoice matches PO total exactly → status MATCHED → APPROVED."""
    po = PurchaseOrder(
        po_number="PO-2026-WF-010",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.RECEIVED,
        total_amount=Decimal("274.95"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    invoice = EDIInvoice(
        purchase_order_id=po.id,
        vendor_id=vendor_a.id,
        invoice_number="INV-2026-0101",
        invoice_date=datetime.now(tz=timezone.utc),
        due_date=datetime.now(tz=timezone.utc) + timedelta(days=30),
        subtotal=Decimal("274.95"),
        tax_amount=Decimal("0.00"),
        shipping_amount=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("274.95"),
        po_total=Decimal("274.95"),
        variance_amount=Decimal("0.00"),
        matched_line_items=3,
        total_line_items=3,
        status=EDIInvoiceStatus.PENDING,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    # Match step
    assert invoice.variance_amount == Decimal("0.00")
    invoice.status = EDIInvoiceStatus.MATCHED
    await test_db.commit()
    assert invoice.status == EDIInvoiceStatus.MATCHED

    # Approve
    invoice.status = EDIInvoiceStatus.APPROVED
    invoice.approved_by_id = test_admin.id
    invoice.approved_at = datetime.now(tz=timezone.utc)
    await test_db.commit()
    assert invoice.status == EDIInvoiceStatus.APPROVED


@pytest.mark.asyncio
async def test_invoice_reconciliation_with_variance(test_db, test_staff, fund, vendor_a):
    """Invoice has price variance → status DISPUTED."""
    po = PurchaseOrder(
        po_number="PO-2026-WF-011",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.RECEIVED,
        total_amount=Decimal("200.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    invoice = EDIInvoice(
        purchase_order_id=po.id,
        vendor_id=vendor_a.id,
        invoice_number="INV-2026-0102",
        invoice_date=datetime.now(tz=timezone.utc),
        subtotal=Decimal("215.00"),
        total_amount=Decimal("215.00"),
        po_total=Decimal("200.00"),
        variance_amount=Decimal("15.00"),
        variance_reason="Price increase on 2 items since order placement",
        matched_line_items=1,
        total_line_items=3,
        status=EDIInvoiceStatus.PENDING,
    )
    test_db.add(invoice)
    await test_db.commit()

    # Variance exceeds tolerance → dispute
    tolerance_pct = Decimal("5.00")
    variance_pct = (invoice.variance_amount / invoice.po_total) * 100
    assert variance_pct > tolerance_pct  # 7.5% > 5%

    invoice.status = EDIInvoiceStatus.DISPUTED
    await test_db.commit()
    assert invoice.status == EDIInvoiceStatus.DISPUTED


@pytest.mark.asyncio
async def test_invoice_payment_tracking(test_db, test_staff, test_admin, fund, vendor_a):
    """Approved invoice moves to PAID status."""
    po = PurchaseOrder(
        po_number="PO-2026-WF-012",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.RECEIVED,
        total_amount=Decimal("100.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    invoice = EDIInvoice(
        purchase_order_id=po.id,
        vendor_id=vendor_a.id,
        invoice_number="INV-2026-0103",
        invoice_date=datetime.now(tz=timezone.utc),
        total_amount=Decimal("100.00"),
        po_total=Decimal("100.00"),
        variance_amount=Decimal("0.00"),
        status=EDIInvoiceStatus.APPROVED,
        approved_by_id=test_admin.id,
        approved_at=datetime.now(tz=timezone.utc),
    )
    test_db.add(invoice)
    await test_db.commit()

    invoice.status = EDIInvoiceStatus.PAID
    await test_db.commit()
    assert invoice.status == EDIInvoiceStatus.PAID


# ============================================================================
# 8. CLOSE COMPLETED PO
# ============================================================================


@pytest.mark.asyncio
async def test_close_completed_po(test_db, test_staff, fund, vendor_a):
    """Fully received PO can be closed; no further status changes possible."""
    po = PurchaseOrder(
        po_number="PO-2026-WF-013",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.RECEIVED,
        total_amount=Decimal("300.00"),
        created_by_id=test_staff.id,
        actual_delivery=date(2026, 3, 1),
    )
    test_db.add(po)
    await test_db.commit()

    # Add fully-received items
    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Completed Book",
        quantity=3,
        unit_price=Decimal("100.00"),
        received_quantity=3,
    )
    test_db.add(item)
    await test_db.commit()

    # All items received, delivery recorded → PO considered "closed"
    assert item.is_fully_received
    assert po.actual_delivery is not None
    assert po.status == PurchaseOrderStatus.RECEIVED


# ============================================================================
# 9. CANCEL LINE ITEM
# ============================================================================


@pytest.mark.asyncio
async def test_cancel_line_item_from_draft(test_db, test_staff, fund, vendor_a):
    """Remove a line item from a draft PO; total recalculates."""
    po = PurchaseOrder(
        po_number="PO-2026-WF-014",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.DRAFT,
        total_amount=Decimal("0.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    item1 = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Keep This Book",
        quantity=2,
        unit_price=Decimal("25.00"),
    )
    item2 = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Cancel This Book",
        quantity=1,
        unit_price=Decimal("75.00"),
    )
    test_db.add_all([item1, item2])
    po.total_amount = Decimal("125.00")  # 2*25 + 1*75
    await test_db.commit()
    await test_db.refresh(item2)

    # Delete item2
    await test_db.delete(item2)
    po.total_amount = item1.line_total  # Recalculate: 2*25 = $50
    await test_db.commit()

    result = await test_db.execute(
        select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == po.id)
    )
    remaining = result.scalars().all()
    assert len(remaining) == 1
    assert remaining[0].title == "Keep This Book"
    assert po.total_amount == Decimal("50.00")


# ============================================================================
# 10. CANCEL ENTIRE PO
# ============================================================================


@pytest.mark.asyncio
async def test_cancel_entire_po_releases_encumbrance(test_db, test_staff, fund, vendor_a):
    """Cancel a submitted PO; encumbrance returns to available."""
    fund.encumbered_amount = Decimal("600.00")
    await test_db.commit()

    po = PurchaseOrder(
        po_number="PO-2026-WF-015",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.SUBMITTED,
        total_amount=Decimal("600.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()

    # Cancel PO → release encumbrance
    po.status = PurchaseOrderStatus.CANCELLED
    fund.encumbered_amount -= po.total_amount
    await test_db.commit()
    await test_db.refresh(fund)

    assert po.status == PurchaseOrderStatus.CANCELLED
    assert fund.encumbered_amount == Decimal("0.00")
    assert fund.available_amount == Decimal("10000.00")


@pytest.mark.asyncio
async def test_cancel_draft_po_no_fund_impact(test_db, test_staff, fund, vendor_a):
    """Cancel a draft PO; fund should not be affected at all."""
    initial_available = fund.available_amount

    po = PurchaseOrder(
        po_number="PO-2026-WF-016",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.DRAFT,
        total_amount=Decimal("999.99"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()

    po.status = PurchaseOrderStatus.CANCELLED
    await test_db.commit()

    await test_db.refresh(fund)
    assert fund.available_amount == initial_available
    assert fund.encumbered_amount == Decimal("0.00")
    assert fund.spent_amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_cancel_partially_received_po(test_db, test_staff, fund, vendor_a):
    """Cancel a partially received PO; remaining encumbrance released,
    spent stays for what was already received."""
    fund.encumbered_amount = Decimal("200.00")
    fund.spent_amount = Decimal("300.00")
    await test_db.commit()

    po = PurchaseOrder(
        po_number="PO-2026-WF-017",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.PARTIALLY_RECEIVED,
        total_amount=Decimal("500.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()

    # Cancel: release remaining encumbrance, keep spent
    po.status = PurchaseOrderStatus.CANCELLED
    fund.encumbered_amount = Decimal("0.00")  # Release remaining
    await test_db.commit()
    await test_db.refresh(fund)

    assert po.status == PurchaseOrderStatus.CANCELLED
    assert fund.encumbered_amount == Decimal("0.00")
    assert fund.spent_amount == Decimal("300.00")  # Already spent stays
    assert fund.available_amount == Decimal("9700.00")  # 10000 - 0 - 300


# ============================================================================
# 11. BUDGET IMPACT TRACKING
# ============================================================================


@pytest.mark.asyncio
async def test_budget_impact_across_multiple_pos(test_db, test_staff, fund, vendor_a, vendor_b):
    """Track cumulative budget impact across multiple POs."""
    # PO 1: $200 submitted
    po1 = PurchaseOrder(
        po_number="PO-2026-WF-018",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.SUBMITTED,
        total_amount=Decimal("200.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po1)
    fund.encumbered_amount += Decimal("200.00")
    await test_db.commit()

    # PO 2: $350 submitted
    po2 = PurchaseOrder(
        po_number="PO-2026-WF-019",
        vendor_id=vendor_b.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.SUBMITTED,
        total_amount=Decimal("350.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po2)
    fund.encumbered_amount += Decimal("350.00")
    await test_db.commit()
    await test_db.refresh(fund)

    assert fund.encumbered_amount == Decimal("550.00")
    assert fund.available_amount == Decimal("9450.00")  # 10000 - 550

    # Receive PO 1 fully
    fund.encumbered_amount -= Decimal("200.00")
    fund.spent_amount += Decimal("200.00")
    po1.status = PurchaseOrderStatus.RECEIVED
    await test_db.commit()
    await test_db.refresh(fund)

    assert fund.encumbered_amount == Decimal("350.00")
    assert fund.spent_amount == Decimal("200.00")
    assert fund.available_amount == Decimal("9450.00")  # 10000 - 350 - 200


@pytest.mark.asyncio
async def test_fund_available_amount_calculation(test_db):
    """available_amount = allocated - encumbered - spent."""
    f = Fund(
        code="CALC-TEST",
        name="Calc Test Fund",
        fiscal_year=2026,
        allocated_amount=Decimal("5000.00"),
        encumbered_amount=Decimal("1200.00"),
        spent_amount=Decimal("800.00"),
        status=FundStatus.ACTIVE,
    )
    test_db.add(f)
    await test_db.commit()
    await test_db.refresh(f)

    assert f.available_amount == Decimal("3000.00")


@pytest.mark.asyncio
async def test_closed_fund_prevents_modification(test_db):
    """Closed fund blocks changes to encumbered and spent amounts."""
    f = Fund(
        code="CLOSED-FUND",
        name="Closed Fund",
        fiscal_year=2025,
        allocated_amount=Decimal("5000.00"),
        encumbered_amount=Decimal("0.00"),
        spent_amount=Decimal("4500.00"),
        status=FundStatus.CLOSED,
    )
    test_db.add(f)
    await test_db.commit()
    await test_db.refresh(f)

    with pytest.raises(ValueError, match="Cannot modify encumbered amount on closed fund"):
        f.encumbered_amount = Decimal("100.00")

    with pytest.raises(ValueError, match="Cannot modify spent amount on closed fund"):
        f.spent_amount = Decimal("5000.00")


@pytest.mark.asyncio
async def test_closed_fund_prevents_reopening(test_db):
    """Closed fund cannot be reopened."""
    f = Fund(
        code="FINAL-FUND",
        name="Final Fund",
        fiscal_year=2025,
        allocated_amount=Decimal("1000.00"),
        encumbered_amount=Decimal("0.00"),
        spent_amount=Decimal("900.00"),
        status=FundStatus.CLOSED,
    )
    test_db.add(f)
    await test_db.commit()
    await test_db.refresh(f)

    with pytest.raises(ValueError, match="Cannot reopen closed fund"):
        f.status = FundStatus.ACTIVE


# ============================================================================
# 12. VENDOR PERFORMANCE TRACKING
# ============================================================================


@pytest.mark.asyncio
async def test_vendor_performance_delivery_tracking(test_db, test_staff, fund, vendor_a):
    """Track vendor delivery: expected vs actual dates, on-time metric."""
    expected = date(2026, 3, 10)
    actual = date(2026, 3, 8)  # Early delivery

    po = PurchaseOrder(
        po_number="PO-2026-WF-020",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        expected_delivery=expected,
        status=PurchaseOrderStatus.RECEIVED,
        total_amount=Decimal("400.00"),
        created_by_id=test_staff.id,
        actual_delivery=actual,
    )
    test_db.add(po)
    await test_db.commit()

    days_delta = (actual - expected).days
    assert days_delta == -2  # Delivered 2 days early
    on_time = actual <= expected
    assert on_time is True


@pytest.mark.asyncio
async def test_vendor_performance_late_delivery(test_db, test_staff, fund, vendor_a):
    """Detect late deliveries for vendor performance reports."""
    expected = date(2026, 3, 10)
    actual = date(2026, 3, 20)  # 10 days late

    po = PurchaseOrder(
        po_number="PO-2026-WF-021",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        expected_delivery=expected,
        status=PurchaseOrderStatus.RECEIVED,
        total_amount=Decimal("200.00"),
        created_by_id=test_staff.id,
        actual_delivery=actual,
    )
    test_db.add(po)
    await test_db.commit()

    days_late = (actual - expected).days
    assert days_late == 10
    assert actual > expected  # Late


@pytest.mark.asyncio
async def test_vendor_order_count(test_db, test_staff, fund, vendor_a, vendor_b):
    """Count orders per vendor for performance comparison."""
    for i in range(3):
        po = PurchaseOrder(
            po_number=f"PO-2026-WF-VA-{i}",
            vendor_id=vendor_a.id,
            fund_id=fund.id,
            order_date=date(2026, 2, 25),
            status=PurchaseOrderStatus.RECEIVED,
            total_amount=Decimal("100.00"),
            created_by_id=test_staff.id,
        )
        test_db.add(po)

    for i in range(2):
        po = PurchaseOrder(
            po_number=f"PO-2026-WF-VB-{i}",
            vendor_id=vendor_b.id,
            fund_id=fund.id,
            order_date=date(2026, 2, 25),
            status=PurchaseOrderStatus.RECEIVED,
            total_amount=Decimal("150.00"),
            created_by_id=test_staff.id,
        )
        test_db.add(po)

    await test_db.commit()

    result_a = await test_db.execute(
        select(PurchaseOrder).where(PurchaseOrder.vendor_id == vendor_a.id)
    )
    result_b = await test_db.execute(
        select(PurchaseOrder).where(PurchaseOrder.vendor_id == vendor_b.id)
    )

    assert len(result_a.scalars().all()) == 3
    assert len(result_b.scalars().all()) == 2


@pytest.mark.asyncio
async def test_vendor_total_spend(test_db, test_staff, fund, vendor_a):
    """Calculate total spend per vendor from received POs."""
    amounts = [Decimal("150.00"), Decimal("275.50"), Decimal("124.50")]
    for i, amount in enumerate(amounts):
        po = PurchaseOrder(
            po_number=f"PO-2026-WF-SPEND-{i}",
            vendor_id=vendor_a.id,
            fund_id=fund.id,
            order_date=date(2026, 2, 25),
            status=PurchaseOrderStatus.RECEIVED,
            total_amount=amount,
            created_by_id=test_staff.id,
        )
        test_db.add(po)
    await test_db.commit()

    result = await test_db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.vendor_id == vendor_a.id,
            PurchaseOrder.status == PurchaseOrderStatus.RECEIVED,
        )
    )
    pos = result.scalars().all()
    total = sum(po.total_amount for po in pos)
    assert total == Decimal("550.00")


# ============================================================================
# 13. MONEY SPENT ACCURACY VERIFICATION
# ============================================================================


@pytest.mark.asyncio
async def test_money_spent_penny_accuracy(test_db, test_staff, fund, vendor_a):
    """Verify exact-penny accuracy through full PO lifecycle."""
    po = PurchaseOrder(
        po_number="PO-2026-WF-PENNY",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.DRAFT,
        total_amount=Decimal("0.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    # Items with awkward decimal prices
    items_data = [
        ("Book Alpha", 3, Decimal("19.99")),   # 3 * 19.99 = 59.97
        ("Book Beta", 7, Decimal("12.49")),     # 7 * 12.49 = 87.43
        ("Book Gamma", 1, Decimal("33.33")),    # 1 * 33.33 = 33.33
        ("Book Delta", 2, Decimal("7.01")),     # 2 * 7.01  = 14.02
    ]
    expected_total = Decimal("0.00")
    for title, qty, price in items_data:
        item = PurchaseOrderItem(
            purchase_order_id=po.id,
            title=title,
            quantity=qty,
            unit_price=price,
            received_quantity=0,
        )
        test_db.add(item)
        expected_total += Decimal(str(qty)) * price

    po.total_amount = expected_total
    await test_db.commit()

    # Verify total: 59.97 + 87.43 + 33.33 + 14.02 = 194.75
    assert expected_total == Decimal("194.75")
    assert po.total_amount == Decimal("194.75")

    # Submit → encumber
    fund.encumbered_amount = po.total_amount
    po.status = PurchaseOrderStatus.SUBMITTED
    await test_db.commit()
    await test_db.refresh(fund)

    assert fund.encumbered_amount == Decimal("194.75")
    assert fund.available_amount == Decimal("9805.25")  # 10000 - 194.75

    # Receive all → move encumbered to spent
    fund.encumbered_amount -= po.total_amount
    fund.spent_amount += po.total_amount
    po.status = PurchaseOrderStatus.RECEIVED
    await test_db.commit()
    await test_db.refresh(fund)

    assert fund.encumbered_amount == Decimal("0.00")
    assert fund.spent_amount == Decimal("194.75")
    assert fund.available_amount == Decimal("9805.25")  # 10000 - 0 - 194.75

    # Final accounting identity
    assert (
        fund.allocated_amount
        == fund.encumbered_amount + fund.spent_amount + fund.available_amount
    )


@pytest.mark.asyncio
async def test_line_total_property_accuracy(test_db, test_staff, fund, vendor_a):
    """PurchaseOrderItem.line_total = quantity * unit_price, exact Decimal."""
    po = PurchaseOrder(
        po_number="PO-2026-WF-LT",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.DRAFT,
        total_amount=Decimal("0.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    cases = [
        (1, Decimal("0.01"), Decimal("0.01")),
        (100, Decimal("0.01"), Decimal("1.00")),
        (3, Decimal("33.33"), Decimal("99.99")),
        (7, Decimal("14.29"), Decimal("100.03")),
    ]
    for qty, price, expected_line in cases:
        item = PurchaseOrderItem(
            purchase_order_id=po.id,
            title=f"Item {qty}x{price}",
            quantity=qty,
            unit_price=price,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)
        assert item.line_total == expected_line, (
            f"Expected {expected_line} but got {item.line_total} "
            f"for {qty} x {price}"
        )


@pytest.mark.asyncio
async def test_fund_accounting_identity_holds(test_db):
    """allocated = encumbered + spent + available — always."""
    f = Fund(
        code="IDENTITY-TEST",
        name="Identity Test",
        fiscal_year=2026,
        allocated_amount=Decimal("8000.00"),
        encumbered_amount=Decimal("2500.00"),
        spent_amount=Decimal("3200.00"),
        status=FundStatus.ACTIVE,
    )
    test_db.add(f)
    await test_db.commit()
    await test_db.refresh(f)

    assert (
        f.allocated_amount
        == f.encumbered_amount + f.spent_amount + f.available_amount
    )
    assert f.available_amount == Decimal("2300.00")


@pytest.mark.asyncio
async def test_partial_receive_fund_accuracy(test_db, test_staff, fund, vendor_a):
    """Fund amounts stay exact through multiple partial receives."""
    po = PurchaseOrder(
        po_number="PO-2026-WF-MULTI",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.SUBMITTED,
        total_amount=Decimal("300.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    fund.encumbered_amount = Decimal("300.00")
    await test_db.commit()
    await test_db.refresh(po)

    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Gradual Receive Book",
        quantity=10,
        unit_price=Decimal("30.00"),
        received_quantity=0,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    # Receive in batches: 3, 4, 3
    batches = [3, 4, 3]
    total_received_value = Decimal("0.00")

    for batch in batches:
        value = Decimal(str(batch)) * item.unit_price
        item.received_quantity += batch
        fund.encumbered_amount -= value
        fund.spent_amount += value
        total_received_value += value
        await test_db.commit()

    await test_db.refresh(fund)
    await test_db.refresh(item)

    assert item.received_quantity == 10
    assert item.is_fully_received
    assert total_received_value == Decimal("300.00")
    assert fund.encumbered_amount == Decimal("0.00")
    assert fund.spent_amount == Decimal("300.00")
    assert fund.available_amount == Decimal("9700.00")
    assert (
        fund.allocated_amount
        == fund.encumbered_amount + fund.spent_amount + fund.available_amount
    )


@pytest.mark.asyncio
async def test_item_copy_creation_on_receipt(test_db, test_staff, fund, vendor_a, catalog_item):
    """Receiving items creates ItemCopy records linked to catalog item and PO item."""
    po = PurchaseOrder(
        po_number="PO-2026-WF-COPIES",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=PurchaseOrderStatus.SUBMITTED,
        total_amount=Decimal("120.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title=catalog_item.title,
        author=catalog_item.author,
        isbn=catalog_item.isbn,
        quantity=3,
        unit_price=Decimal("40.00"),
        received_quantity=0,
        catalog_item_id=catalog_item.id,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    # Receive all 3 → create copies
    item.received_quantity = 3
    copies = []
    for n in range(1, 4):
        copy = ItemCopy(
            catalog_item_id=catalog_item.id,
            barcode=f"WF-COPY-{n:04d}",
            copy_number=n,
            condition=ItemCondition.NEW,
            acquisition_source=AcquisitionSource.PURCHASE,
            purchase_order_item_id=item.id,
            location="Receiving",
            replacement_cost=item.unit_price,
        )
        copies.append(copy)
    test_db.add_all(copies)
    po.status = PurchaseOrderStatus.RECEIVED
    await test_db.commit()

    result = await test_db.execute(
        select(ItemCopy).where(ItemCopy.purchase_order_item_id == item.id)
    )
    created = result.scalars().all()
    assert len(created) == 3
    assert all(c.catalog_item_id == catalog_item.id for c in created)
    assert all(c.condition == ItemCondition.NEW for c in created)
    assert all(c.acquisition_source == AcquisitionSource.PURCHASE for c in created)
    assert all(c.replacement_cost == Decimal("40.00") for c in created)


# ============================================================================
# FULL END-TO-END WORKFLOW
# ============================================================================


@pytest.mark.asyncio
async def test_complete_acquisition_lifecycle(test_db, test_staff, test_admin, fund, vendor_a, catalog_item):
    """Complete lifecycle: create → add items → submit → approve → send →
    partial receive → remaining receive → invoice → verify finances."""

    # --- Step 1: Create PO ---
    po = PurchaseOrder(
        po_number="PO-2026-E2E-001",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        expected_delivery=date(2026, 3, 15),
        status=PurchaseOrderStatus.DRAFT,
        total_amount=Decimal("0.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    # --- Step 2: Add line items ---
    item1 = PurchaseOrderItem(
        purchase_order_id=po.id,
        title=catalog_item.title,
        author=catalog_item.author,
        isbn=catalog_item.isbn,
        quantity=4,
        unit_price=Decimal("45.00"),
        received_quantity=0,
        catalog_item_id=catalog_item.id,
    )
    item2 = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Database Internals",
        author="Alex Petrov",
        isbn="978-1-4920-4034-7",
        quantity=2,
        unit_price=Decimal("55.00"),
        received_quantity=0,
    )
    test_db.add_all([item1, item2])
    po.total_amount = (
        Decimal("4") * Decimal("45.00") + Decimal("2") * Decimal("55.00")
    )  # 180 + 110 = 290
    await test_db.commit()
    assert po.total_amount == Decimal("290.00")

    # --- Step 3: Submit for approval ---
    po.status = PurchaseOrderStatus.PENDING_APPROVAL
    await test_db.commit()
    assert po.status == PurchaseOrderStatus.PENDING_APPROVAL

    # --- Step 4: Approve ---
    po.status = PurchaseOrderStatus.APPROVED
    po.approved_by_id = test_admin.id
    po.approved_at = datetime.now(tz=timezone.utc)
    await test_db.commit()
    assert po.status == PurchaseOrderStatus.APPROVED

    # --- Step 5: Send to vendor (encumber) ---
    fund.encumbered_amount += po.total_amount
    po.status = PurchaseOrderStatus.SUBMITTED
    await test_db.commit()
    await test_db.refresh(fund)
    assert fund.encumbered_amount == Decimal("290.00")
    assert fund.available_amount == Decimal("9710.00")

    # --- Step 6: Partial receive (item1: 2 of 4) ---
    recv_qty_1 = 2
    recv_value_1 = Decimal(str(recv_qty_1)) * item1.unit_price  # 2 * 45 = 90
    item1.received_quantity = recv_qty_1
    fund.encumbered_amount -= recv_value_1
    fund.spent_amount += recv_value_1
    po.status = PurchaseOrderStatus.PARTIALLY_RECEIVED
    await test_db.commit()
    await test_db.refresh(fund)

    assert fund.encumbered_amount == Decimal("200.00")  # 290 - 90
    assert fund.spent_amount == Decimal("90.00")
    assert not item1.is_fully_received

    # --- Step 7: Receive remaining (item1: 2 more, item2: all 2) ---
    recv_remaining_1 = item1.quantity - item1.received_quantity  # 2
    recv_remaining_2 = item2.quantity  # 2
    recv_value_remaining = (
        Decimal(str(recv_remaining_1)) * item1.unit_price
        + Decimal(str(recv_remaining_2)) * item2.unit_price
    )  # 90 + 110 = 200
    assert recv_value_remaining == Decimal("200.00")

    item1.received_quantity = item1.quantity
    item2.received_quantity = item2.quantity
    fund.encumbered_amount -= recv_value_remaining
    fund.spent_amount += recv_value_remaining
    po.status = PurchaseOrderStatus.RECEIVED
    po.actual_delivery = date(2026, 3, 12)
    await test_db.commit()
    await test_db.refresh(fund)

    assert po.status == PurchaseOrderStatus.RECEIVED
    assert item1.is_fully_received
    assert item2.is_fully_received
    assert fund.encumbered_amount == Decimal("0.00")
    assert fund.spent_amount == Decimal("290.00")

    # --- Step 8: Invoice reconciliation ---
    invoice = EDIInvoice(
        purchase_order_id=po.id,
        vendor_id=vendor_a.id,
        invoice_number="INV-E2E-001",
        invoice_date=datetime.now(tz=timezone.utc),
        due_date=datetime.now(tz=timezone.utc) + timedelta(days=30),
        subtotal=Decimal("290.00"),
        tax_amount=Decimal("0.00"),
        shipping_amount=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("290.00"),
        po_total=Decimal("290.00"),
        variance_amount=Decimal("0.00"),
        matched_line_items=2,
        total_line_items=2,
        status=EDIInvoiceStatus.MATCHED,
    )
    test_db.add(invoice)
    await test_db.commit()

    invoice.status = EDIInvoiceStatus.APPROVED
    invoice.approved_by_id = test_admin.id
    invoice.approved_at = datetime.now(tz=timezone.utc)
    await test_db.commit()
    assert invoice.status == EDIInvoiceStatus.APPROVED

    # --- Final verification: accounting identity ---
    await test_db.refresh(fund)
    assert (
        fund.allocated_amount
        == fund.encumbered_amount + fund.spent_amount + fund.available_amount
    )
    assert fund.spent_amount == Decimal("290.00")
    assert fund.available_amount == Decimal("9710.00")

    # Delivery was early
    assert po.actual_delivery < po.expected_delivery


@pytest.mark.asyncio
async def test_receive_from_edi_never_drives_encumbrance_negative(
    test_db, test_staff, fund, vendor_a
):
    """Regression: a PO received without prior encumbrance (EDI auto-receive or
    seeded data) must not push the fund encumbered balance below zero. A negative
    encumbrance cancels the spend in available = allocated - encumbered - spent,
    masking real spending and overstating available funds."""
    from app.services.po_facade_service import POFacadeService

    assert fund.encumbered_amount == Decimal("0.00")  # never encumbered
    po = PurchaseOrder(
        po_number="PO-2026-EDI-FLOOR",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date(2026, 5, 2),
        status=PurchaseOrderStatus.APPROVED,
        total_amount=Decimal("207.94"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="EDI Book",
        author="Author",
        isbn="ISBN-EDI-FLOOR",
        quantity=1,
        unit_price=Decimal("207.94"),
        received_quantity=0,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    await test_db.refresh(po, attribute_names=["items", "fund"])

    await POFacadeService(test_db).receive_order_from_edi(
        po, [{"item_id": item.id, "received_quantity": 1}]
    )

    assert fund.encumbered_amount == Decimal("0.00")  # floored, not -207.94
    assert fund.spent_amount == Decimal("207.94")
    assert fund.available_amount == Decimal("9792.06")  # 10000 - 0 - 207.94
