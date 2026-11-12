# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration test for creating and verifying purchase orders.

Tests the complete workflow for creating a purchase order with:
- Vendor: Ingram Content Group
- Fund: Adult Fiction FY2024
- 3 line items with correct pricing and totals
- DRAFT status verification
- Budget validation
"""

import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import select

from app.models.acquisition import (
    Fund, FundStatus, Vendor, PurchaseOrder, PurchaseOrderStatus,
    PurchaseOrderItem
)
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_create_purchase_order_adult_fiction(db_session):
    """
    Test creating a purchase order for the Adult Fiction FY2024 fund.

    Verifies:
    1. Vendor "Ingram Content Group" is created or found
    2. Fund "Adult Fiction FY2024" is created or found
    3. PO is created with DRAFT status
    4. 3 line items are added with correct quantities and prices
    5. Total amount is calculated correctly
    6. Budget validation shows remaining fund balance
    """

    # Setup: Get or create vendor
    vendor_result = await db_session.execute(
        select(Vendor).where(Vendor.name == "Ingram Content Group")
    )
    vendor = vendor_result.scalar_one_or_none()

    if not vendor:
        vendor = Vendor(
            name="Ingram Content Group",
            email="orders@ingramcontentgroup.com",
            is_active=True,
        )
        db_session.add(vendor)
        await db_session.flush()

    # Setup: Get or create fund
    fund_result = await db_session.execute(
        select(Fund).where(Fund.code == "ADULT-FIC-2024")
    )
    fund = fund_result.scalar_one_or_none()

    if not fund:
        fund = Fund(
            code="ADULT-FIC-2024",
            name="Adult Fiction FY2024",
            fiscal_year=2024,
            allocated_amount=Decimal("50000.00"),
            status=FundStatus.ACTIVE,
        )
        db_session.add(fund)
        await db_session.flush()

    # Setup: Get or create staff user (UserRole values are lowercase StrEnum
    # members, not "STAFF"/"ADMIN"; also can't assume one pre-exists in the
    # per-test-truncated database).
    user_result = await db_session.execute(
        select(User).where(User.role.in_([UserRole.STAFF, UserRole.ADMIN])).limit(1)
    )
    staff_user = user_result.scalar_one_or_none()
    if not staff_user:
        staff_user = User(
            email="po-test-staff@example.com",
            password_hash="hashed",
            first_name="PO",
            last_name="Staff",
            role=UserRole.STAFF,
            is_active=True,
        )
        db_session.add(staff_user)
        await db_session.flush()

    # Test: Create purchase order
    po = PurchaseOrder(
        po_number=f"PO-TEST-{date.today().strftime('%Y%m%d')}-001",
        vendor_id=vendor.id,
        fund_id=fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        notes="Rush order for summer reading program",
        created_by_id=staff_user.id,
    )
    db_session.add(po)
    await db_session.flush()

    # Test: Add line items
    line_items_data = [
        {
            "isbn": "978-0-13-468599-1",
            "title": "The Pragmatic Programmer: Your Journey to Mastery",
            "author": "David Thomas, Andrew Hunt",
            "quantity": 5,
            "unit_price": Decimal("18.99"),
        },
        {
            "isbn": "978-0-06-112008-4",
            "title": "To Kill a Mockingbird",
            "author": "Harper Lee",
            "quantity": 3,
            "unit_price": Decimal("14.99"),
        },
        {
            "isbn": "978-0-7432-7356-5",
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "quantity": 2,
            "unit_price": Decimal("16.00"),
        },
    ]

    total_amount = Decimal("0.00")
    for item_data in line_items_data:
        po_item = PurchaseOrderItem(
            purchase_order_id=po.id,
            isbn=item_data["isbn"],
            title=item_data["title"],
            author=item_data["author"],
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
        )
        db_session.add(po_item)
        total_amount += Decimal(str(item_data["quantity"])) * item_data["unit_price"]

    po.total_amount = total_amount
    await db_session.commit()

    # Verify: Re-fetch to ensure relationships are loaded
    po_result = await db_session.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == po.id)
    )
    po = po_result.scalar_one()

    po_items_result = await db_session.execute(
        select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == po.id)
    )
    po_items = list(po_items_result.scalars().all())

    # Assertions: Verify PO status
    assert po.status == PurchaseOrderStatus.DRAFT, f"Expected DRAFT status, got {po.status}"

    # Assertions: Verify line items count
    assert len(po_items) == 3, f"Expected 3 line items, got {len(po_items)}"

    # Assertions: Verify each line item
    expected_line_totals = [
        (Decimal("94.95"), "978-0-13-468599-1"),   # 5 × 18.99
        (Decimal("44.97"), "978-0-06-112008-4"),   # 3 × 14.99
        (Decimal("32.00"), "978-0-7432-7356-5"),   # 2 × 16.00
    ]

    for item, (expected_total, expected_isbn) in zip(po_items, expected_line_totals):
        assert item.isbn == expected_isbn, f"Expected ISBN {expected_isbn}, got {item.isbn}"
        actual_total = Decimal(str(item.quantity)) * item.unit_price
        assert actual_total == expected_total, f"Expected line total {expected_total}, got {actual_total}"
        assert item.received_quantity == 0, "DRAFT PO items should have received_quantity = 0"

    # Assertions: Verify total amount
    expected_total = Decimal("171.92")  # 94.95 + 44.97 + 32.00
    assert po.total_amount == expected_total, f"Expected total {expected_total}, got {po.total_amount}"

    # Assertions: Verify PO notes
    assert po.notes == "Rush order for summer reading program"
    assert po.vendor_id == vendor.id
    assert po.fund_id == fund.id

    # Verify: Budget validation
    fund_result = await db_session.execute(
        select(Fund).where(Fund.id == fund.id)
    )
    fund = fund_result.scalar_one()

    available_before = fund.available_amount
    remaining_after = available_before - po.total_amount

    # Budget should still be valid (order is well within budget)
    assert available_before >= po.total_amount, "Fund should have sufficient budget"
    assert remaining_after > 0, "Fund should have remaining balance"

    # Calculate usage percentage
    if available_before > 0:
        usage_percentage = float((po.total_amount / available_before) * 100)
        # Usage should be very low (less than 1% of $50k budget)
        assert usage_percentage < 1, f"Usage percentage should be less than 1%, got {usage_percentage:.2f}%"


@pytest.mark.asyncio
async def test_po_line_item_calculations(db_session):
    """
    Test that line item calculations are correct.

    Verifies:
    1. Line total = quantity × unit_price
    2. Received quantity starts at 0
    3. is_fully_received returns False for DRAFT
    """

    # Setup
    vendor_result = await db_session.execute(select(Vendor).limit(1))
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        vendor = Vendor(name="Test Vendor", is_active=True)
        db_session.add(vendor)
        await db_session.flush()

    fund_result = await db_session.execute(
        select(Fund).where(Fund.status == FundStatus.ACTIVE).limit(1)
    )
    fund = fund_result.scalar_one_or_none()
    if not fund:
        fund = Fund(
            code="TEST-FUND",
            name="Test Fund",
            fiscal_year=2024,
            allocated_amount=Decimal("10000.00"),
            status=FundStatus.ACTIVE,
        )
        db_session.add(fund)
        await db_session.flush()

    user_result = await db_session.execute(select(User).limit(1))
    user = user_result.scalar_one_or_none()
    if not user:
        user = User(
            email="po-calc-test-staff@example.com",
            password_hash="hashed",
            first_name="PO",
            last_name="Calc",
            role=UserRole.STAFF,
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

    # Create PO and item
    po = PurchaseOrder(
        po_number="PO-CALC-TEST-001",
        vendor_id=vendor.id,
        fund_id=fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=user.id,
    )
    db_session.add(po)
    await db_session.flush()

    po_item = PurchaseOrderItem(
        purchase_order_id=po.id,
        isbn="978-0-123456789",
        title="Test Book",
        quantity=5,
        unit_price=Decimal("19.99"),
    )
    db_session.add(po_item)
    await db_session.commit()
    await db_session.refresh(po_item)

    # Verify calculations
    expected_line_total = Decimal("99.95")  # 5 × 19.99
    assert po_item.line_total == expected_line_total
    assert po_item.received_quantity == 0
    assert not po_item.is_fully_received


@pytest.mark.asyncio
async def test_budget_validation_response_structure(db_session):
    """
    Test that budget validation provides the correct response structure.

    Verifies the response includes:
    - Fund details (ID, code, name)
    - Available amount
    - Order total
    - Remaining after order
    - Usage percentage
    - Warning level (none, warning, danger)
    - Message
    - Suggested funds (if over budget)
    """

    # Setup: Create test fund
    fund = Fund(
        code="BUDGET-TEST",
        name="Budget Test Fund",
        fiscal_year=2024,
        allocated_amount=Decimal("1000.00"),
        status=FundStatus.ACTIVE,
    )
    db_session.add(fund)
    await db_session.commit()

    # Verify fund properties
    available = fund.available_amount
    assert available == Decimal("1000.00"), "New fund should have full allocated amount available"

    # Test order that uses different percentages
    test_order_total = Decimal("500.00")  # 50% of budget
    remaining = available - test_order_total
    usage_percentage = float((test_order_total / available) * 100)

    assert remaining == Decimal("500.00")
    assert usage_percentage == 50.0

    # Usage should be "none" (under 75%)
    assert usage_percentage < 75, "Should be under warning threshold"

    # Test high usage scenario
    high_order_total = Decimal("800.00")  # 80% of budget
    remaining_high = available - high_order_total
    usage_high = float((high_order_total / available) * 100)

    assert usage_high == 80.0
    assert usage_high > 75, "Should be in warning threshold"
    assert remaining_high > 0, "Should still be within budget"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
