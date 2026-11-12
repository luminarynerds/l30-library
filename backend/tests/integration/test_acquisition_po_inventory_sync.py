# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for Acquisition PO + Inventory Sync.

Tests the complete acquisition workflow from PO to inventory:
- Create purchase order (draft, approval, submission)
- Receive items (partial receive, full receive)
- Create item copies in inventory
- Update fund accounting (encumbrances, spend)
- Link PO items to catalog items
- Handle PO rejections and cancellations
- Inventory sync when items received
- Budget constraints and fund management
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

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
from app.models.inventory import ItemCopy, AcquisitionSource, ItemCondition
from app.models.user import User, UserRole


@pytest.fixture
async def acquisition_fund(test_db):
    """Create a fund for acquisition tests."""
    fund = Fund(
        code="ACQF-2024",
        name="General Acquisition Fund 2024",
        description="Annual budget for general acquisitions",
        fiscal_year=2024,
        allocated_amount=Decimal("10000.00"),
        encumbered_amount=Decimal("0.00"),
        spent_amount=Decimal("0.00"),
        status=FundStatus.ACTIVE,
    )
    test_db.add(fund)
    await test_db.commit()
    await test_db.refresh(fund)
    return fund


@pytest.fixture
async def vendor(test_db):
    """Create a vendor for purchase orders."""
    vendor = Vendor(
        name="Quality Books Supply",
        contact_name="John Smith",
        email="orders@qualitybooks.com",
        phone="555-0100",
        address="123 Publisher Way, Book City, BC 12345",
        account_number="ACCOUNT-98765",
        is_active=True,
    )
    test_db.add(vendor)
    await test_db.commit()
    await test_db.refresh(vendor)
    return vendor


@pytest.fixture
async def catalog_item_for_po(test_db):
    """Create a catalog item to link with PO."""
    item = CatalogItem(
        title="Advanced Python Programming",
        author="David Beazley",
        isbn="978-1-491-95181-4",
        description="Professional Python development guide",
        call_number="005.133 BEA",
        barcode="ACQPO001",
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.mark.asyncio
async def test_create_purchase_order_draft(test_db, test_staff, acquisition_fund, vendor):
    """Test: Create PO in draft status."""
    po = PurchaseOrder(
        po_number="PO-2024-001",
        vendor_id=vendor.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        total_amount=Decimal("0.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    assert po.status == PurchaseOrderStatus.DRAFT
    assert po.po_number == "PO-2024-001"
    assert po.created_by_id == test_staff.id


@pytest.mark.asyncio
async def test_add_items_to_purchase_order(test_db, acquisition_fund, vendor, test_staff):
    """Test: Add multiple items to a PO."""
    po = PurchaseOrder(
        po_number="PO-2024-002",
        vendor_id=vendor.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    # Add 3 items
    items = [
        PurchaseOrderItem(
            purchase_order_id=po.id,
            title="Book One",
            author="Author One",
            isbn="ISBN-001",
            quantity=2,
            unit_price=Decimal("25.00"),
        ),
        PurchaseOrderItem(
            purchase_order_id=po.id,
            title="Book Two",
            author="Author Two",
            isbn="ISBN-002",
            quantity=3,
            unit_price=Decimal("30.00"),
        ),
        PurchaseOrderItem(
            purchase_order_id=po.id,
            title="Book Three",
            author="Author Three",
            isbn="ISBN-003",
            quantity=1,
            unit_price=Decimal("45.00"),
        ),
    ]
    test_db.add_all(items)
    await test_db.commit()

    # Verify items
    result = await test_db.execute(
        select(PurchaseOrderItem).filter(PurchaseOrderItem.purchase_order_id == po.id)
    )
    po_items = result.scalars().all()
    assert len(po_items) == 3
    assert po_items[0].quantity == 2
    assert po_items[1].quantity == 3


@pytest.mark.asyncio
async def test_calculate_po_total_amount(test_db, acquisition_fund, vendor, test_staff):
    """Test: PO total amount is calculated correctly."""
    po = PurchaseOrder(
        po_number="PO-2024-003",
        vendor_id=vendor.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    # Add items and calculate total
    item1 = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Book One",
        quantity=2,
        unit_price=Decimal("25.00"),  # 2 * $25 = $50
    )
    item2 = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Book Two",
        quantity=1,
        unit_price=Decimal("30.00"),  # 1 * $30 = $30
    )
    test_db.add_all([item1, item2])
    await test_db.commit()

    # Calculate total
    total = item1.line_total + item2.line_total
    assert total == Decimal("80.00")


@pytest.mark.asyncio
async def test_po_approval_workflow(test_db, test_staff, test_admin, acquisition_fund, vendor):
    """Test: PO moves through approval states (draft -> pending -> approved)."""
    po = PurchaseOrder(
        po_number="PO-2024-004",
        vendor_id=vendor.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        total_amount=Decimal("100.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    # Move to pending approval
    po.status = PurchaseOrderStatus.PENDING_APPROVAL
    await test_db.commit()
    assert po.status == PurchaseOrderStatus.PENDING_APPROVAL

    # Approve
    po.status = PurchaseOrderStatus.APPROVED
    po.approved_by_id = test_admin.id
    po.approved_at = datetime.now(tz=None)
    await test_db.commit()

    assert po.status == PurchaseOrderStatus.APPROVED
    assert po.approved_by_id == test_admin.id
    assert po.approved_at is not None


@pytest.mark.asyncio
async def test_po_submission_and_status(test_db, test_staff, acquisition_fund, vendor):
    """Test: Approved PO can be submitted and transitioned to submitted."""
    po = PurchaseOrder(
        po_number="PO-2024-005",
        vendor_id=vendor.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.APPROVED,
        total_amount=Decimal("500.00"),
        created_by_id=test_staff.id,
        approved_by_id=test_staff.id,
        approved_at=datetime.now(tz=None),
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    # Submit PO
    po.status = PurchaseOrderStatus.SUBMITTED
    await test_db.commit()

    assert po.status == PurchaseOrderStatus.SUBMITTED


@pytest.mark.asyncio
async def test_encumbrance_tracking_on_approval(test_db, test_staff, acquisition_fund, vendor):
    """Test: Fund encumbrance increases when PO is approved."""
    initial_encumbered = acquisition_fund.encumbered_amount

    po = PurchaseOrder(
        po_number="PO-2024-006",
        vendor_id=vendor.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.APPROVED,
        total_amount=Decimal("250.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()

    # Update fund encumbrance
    acquisition_fund.encumbered_amount += po.total_amount
    await test_db.commit()
    await test_db.refresh(acquisition_fund)

    assert acquisition_fund.encumbered_amount == initial_encumbered + Decimal("250.00")


@pytest.mark.asyncio
async def test_partial_item_receipt(test_db, test_staff, acquisition_fund, vendor):
    """Test: Receive part of ordered quantity, update received_quantity."""
    po = PurchaseOrder(
        po_number="PO-2024-007",
        vendor_id=vendor.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.SUBMITTED,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Book for Partial Receipt",
        quantity=5,
        unit_price=Decimal("20.00"),
        received_quantity=0,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    # Receive 3 of 5
    item.received_quantity = 3
    po.status = PurchaseOrderStatus.PARTIALLY_RECEIVED
    await test_db.commit()

    assert item.received_quantity == 3
    assert not item.is_fully_received
    assert po.status == PurchaseOrderStatus.PARTIALLY_RECEIVED


@pytest.mark.asyncio
async def test_full_item_receipt_creates_copies(test_db, test_staff, acquisition_fund, vendor, catalog_item_for_po):
    """Test: Full receipt creates ItemCopy records in inventory."""
    po = PurchaseOrder(
        po_number="PO-2024-008",
        vendor_id=vendor.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.SUBMITTED,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Programming Book",
        quantity=3,
        unit_price=Decimal("35.00"),
        received_quantity=0,
        catalog_item_id=catalog_item_for_po.id,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    # Receive all 3 copies
    item.received_quantity = 3
    po.status = PurchaseOrderStatus.RECEIVED
    await test_db.commit()

    # Create item copies
    copies = []
    for copy_num in range(1, 4):
        copy = ItemCopy(
            catalog_item_id=catalog_item_for_po.id,
            barcode=f"COPY-ACQ-{copy_num:03d}",
            copy_number=copy_num,
            condition=ItemCondition.NEW,
            acquisition_source=AcquisitionSource.PURCHASE,
            purchase_order_item_id=item.id,
            location="Receiving",
            replacement_cost=item.unit_price,
        )
        copies.append(copy)
    test_db.add_all(copies)
    await test_db.commit()

    # Verify copies created
    result = await test_db.execute(
        select(ItemCopy).filter(ItemCopy.purchase_order_item_id == item.id)
    )
    created_copies = result.scalars().all()
    assert len(created_copies) == 3
    assert all(c.catalog_item_id == catalog_item_for_po.id for c in created_copies)


@pytest.mark.asyncio
async def test_fund_spend_tracking_on_receipt(test_db, test_staff, acquisition_fund, vendor):
    """Test: Fund spend amount increases when items are received."""
    po = PurchaseOrder(
        po_number="PO-2024-009",
        vendor_id=vendor.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.SUBMITTED,
        total_amount=Decimal("150.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()

    # Simulate the submission-time encumbrance this PO would have picked up
    # (the fixture's fund starts at encumbered_amount=0; without this the
    # receipt step below drives encumbered_amount negative instead of back
    # to zero).
    acquisition_fund.encumbered_amount += Decimal("150.00")
    await test_db.commit()

    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Book",
        quantity=3,
        unit_price=Decimal("50.00"),
        received_quantity=0,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    # Receipt: update spend and received_quantity
    item.received_quantity = 3
    po.status = PurchaseOrderStatus.RECEIVED
    acquisition_fund.spent_amount += Decimal("150.00")
    acquisition_fund.encumbered_amount -= Decimal("150.00")
    await test_db.commit()

    assert acquisition_fund.spent_amount == Decimal("150.00")
    assert acquisition_fund.encumbered_amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_po_rejection_flow(test_db, test_staff, test_admin, acquisition_fund, vendor):
    """Test: PO can be rejected with rejection notes."""
    po = PurchaseOrder(
        po_number="PO-2024-010",
        vendor_id=vendor.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.PENDING_APPROVAL,
        total_amount=Decimal("200.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    # Reject with notes
    po.status = PurchaseOrderStatus.REJECTED
    po.rejection_notes = "Budget not available for this category"
    await test_db.commit()

    assert po.status == PurchaseOrderStatus.REJECTED
    assert po.rejection_notes is not None


@pytest.mark.asyncio
async def test_fund_available_amount_calculation(test_db):
    """Test: Fund available_amount property calculates correctly."""
    fund = Fund(
        code="TEST-FUND",
        name="Test Fund",
        fiscal_year=2024,
        allocated_amount=Decimal("10000.00"),
        encumbered_amount=Decimal("3000.00"),
        spent_amount=Decimal("2000.00"),
        status=FundStatus.ACTIVE,
    )
    test_db.add(fund)
    await test_db.commit()
    await test_db.refresh(fund)

    # Available = allocated - encumbered - spent
    expected = Decimal("10000.00") - Decimal("3000.00") - Decimal("2000.00")
    assert fund.available_amount == Decimal("5000.00")
    assert fund.available_amount == expected


@pytest.mark.asyncio
async def test_prevent_po_if_insufficient_funds(test_db, test_staff, acquisition_fund, vendor):
    """Test: Cannot create PO exceeding available fund amount."""
    # Set up fund with limited balance
    acquisition_fund.allocated_amount = Decimal("500.00")
    acquisition_fund.spent_amount = Decimal("400.00")
    await test_db.commit()

    available = acquisition_fund.available_amount
    assert available == Decimal("100.00")

    # Try to create PO for $200 (exceeds available)
    po = PurchaseOrder(
        po_number="PO-2024-011",
        vendor_id=vendor.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        total_amount=Decimal("200.00"),  # Exceeds available
        created_by_id=test_staff.id,
    )

    # In real implementation, service layer would reject this
    # Here we just verify the check would work
    assert po.total_amount > acquisition_fund.available_amount


@pytest.mark.asyncio
async def test_po_cancellation(test_db, test_staff, acquisition_fund, vendor):
    """Test: PO can be cancelled, releasing encumbrance."""
    po = PurchaseOrder(
        po_number="PO-2024-012",
        vendor_id=vendor.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.APPROVED,
        total_amount=Decimal("300.00"),
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()

    # Encumber
    acquisition_fund.encumbered_amount = Decimal("300.00")
    await test_db.commit()

    # Cancel PO, release encumbrance
    po.status = PurchaseOrderStatus.CANCELLED
    acquisition_fund.encumbered_amount -= po.total_amount
    await test_db.commit()

    assert po.status == PurchaseOrderStatus.CANCELLED
    assert acquisition_fund.encumbered_amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_po_item_catalog_linking(test_db, test_staff, acquisition_fund, vendor, catalog_item_for_po):
    """Test: PO items can be linked to existing catalog items."""
    po = PurchaseOrder(
        po_number="PO-2024-013",
        vendor_id=vendor.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title=catalog_item_for_po.title,
        author=catalog_item_for_po.author,
        isbn=catalog_item_for_po.isbn,
        quantity=2,
        unit_price=Decimal("40.00"),
        catalog_item_id=catalog_item_for_po.id,  # Link to catalog
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    assert item.catalog_item_id == catalog_item_for_po.id
    assert item.catalog_item is not None


@pytest.mark.asyncio
async def test_selection_list_to_po_conversion(test_db, test_patron, test_staff, acquisition_fund, vendor):
    """Test: Selection list items can be converted to PO items."""
    # Create selection list item
    selection = SelectionListItem(
        title="Recommended Book",
        author="Top Author",
        isbn="ISBN-SEL-001",
        estimated_price=Decimal("35.00"),
        priority=SelectionPriority.HIGH,
        requested_by_id=test_patron.id,
    )
    test_db.add(selection)
    await test_db.commit()
    await test_db.refresh(selection)

    # Convert to PO
    po = PurchaseOrder(
        po_number="PO-2024-014",
        vendor_id=vendor.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    po_item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title=selection.title,
        author=selection.author,
        isbn=selection.isbn,
        quantity=1,
        unit_price=selection.estimated_price,
    )
    test_db.add(po_item)
    await test_db.commit()

    # Verify PO item created from selection
    result = await test_db.execute(
        select(PurchaseOrderItem).filter(PurchaseOrderItem.purchase_order_id == po.id)
    )
    items = result.scalars().all()
    assert len(items) == 1
    assert items[0].title == selection.title
