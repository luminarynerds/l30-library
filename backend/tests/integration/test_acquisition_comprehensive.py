# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive integration tests for LSC Acquisitions Workflow.

Complete coverage of:
- Vendor creation and management
- Purchase order creation with line items
- Fund allocation and budget tracking
- EDI transaction processing
- Shipment tracking and receiving
- Invoice reconciliation
- Financial accuracy verification
"""

from datetime import date, datetime, timedelta
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
    OrderTemplate,
)
from app.models.edi import (
    VendorEDIProfile,
    EDITransaction,
    EDIMessageType,
    EDITransactionStatus,
    EDIInvoice,
    EDIShipmentNotice,
    EDIOrderResponse,
    TransportProtocol,
)
from app.models.catalog import CatalogItem
from app.models.inventory import ItemCopy, AcquisitionSource, ItemCondition
from app.models.user import User, UserRole
from app.schemas.acquisition import (
    VendorCreate,
    VendorUpdate,
    FundCreate,
    PurchaseOrderCreate,
    POItemCreate,
    ApprovalRequest,
    RejectionRequest,
    ReceiveItemsRequest,
)
from app.schemas.edi import (
    VendorEDIProfileCreate,
    EDIInvoiceLineItem,
)
from app.core.datetime_utils import utc_now


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def acquisition_fund(test_db):
    """Create a primary fund for acquisition tests."""
    fund = Fund(
        code="ACQF-2024",
        name="General Acquisition Fund 2024",
        description="Annual budget for general acquisitions",
        fiscal_year=2024,
        allocated_amount=Decimal("50000.00"),
        encumbered_amount=Decimal("0.00"),
        spent_amount=Decimal("0.00"),
        status=FundStatus.ACTIVE,
    )
    test_db.add(fund)
    await test_db.commit()
    await test_db.refresh(fund)
    return fund


@pytest.fixture
async def acquisition_fund_limited(test_db):
    """Create a fund with limited budget for budget constraint tests."""
    fund = Fund(
        code="ACQF-LIMITED",
        name="Limited Acquisition Fund",
        description="Fund with limited budget for testing constraints",
        fiscal_year=2024,
        allocated_amount=Decimal("1000.00"),
        encumbered_amount=Decimal("0.00"),
        spent_amount=Decimal("0.00"),
        status=FundStatus.ACTIVE,
    )
    test_db.add(fund)
    await test_db.commit()
    await test_db.refresh(fund)
    return fund


@pytest.fixture
async def vendor_primary(test_db):
    """Create a primary vendor for PO tests."""
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
async def vendor_edi_enabled(test_db, vendor_primary):
    """Create a vendor with EDI enabled for EDI tests."""
    vendor = Vendor(
        name="EDI Vendor Inc",
        contact_name="Jane Doe",
        email="edi@vendorinc.com",
        phone="555-0200",
        address="456 Digital Ave, Tech City, TC 67890",
        account_number="ACCOUNT-EDI-001",
        is_active=True,
    )
    test_db.add(vendor)
    await test_db.commit()
    await test_db.refresh(vendor)

    # Add EDI profile
    edi_profile = VendorEDIProfile(
        vendor_id=vendor.id,
        is_enabled=True,
        edi_standard="edifact",
        sender_id="LSC-LIBRARY",
        sender_qualifier="02",
        receiver_id="VENDOR-EDI",
        receiver_qualifier="01",
        transport_protocol="sftp",
        transport_host="sftp.vendorinc.com",
        transport_port=22,
        transport_username="lsc_user",
        transport_password="encrypted_password",
        supports_orders=True,
        supports_ordrsp=True,
        supports_desadv=True,
        supports_invoic=True,
        auto_send_orders=False,
        auto_process_responses=True,
        auto_approve_invoices=False,
        invoice_tolerance_percent=Decimal("2.00"),
        is_test_mode=False,
    )
    test_db.add(edi_profile)
    await test_db.commit()
    await test_db.refresh(edi_profile)

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


@pytest.fixture
async def test_director(test_db):
    """Create a director user for PO approvals."""
    director = User(
        email="director@lsc.test",
        password_hash="hash",
        first_name="Director",
        last_name="User",
        is_active=True,
    )
    director.role = UserRole.DIRECTOR
    test_db.add(director)
    await test_db.commit()
    await test_db.refresh(director)
    return director


# ============================================================================
# VENDOR MANAGEMENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_vendor_creation(test_db):
    """Test: Create a new vendor."""
    vendor = Vendor(
        name="New Vendor LLC",
        contact_name="Alice Johnson",
        email="alice@newvendor.com",
        phone="555-1234",
        address="789 Commerce St, Trade City, TC 98765",
        account_number="ACCOUNT-NEW-001",
        is_active=True,
    )
    test_db.add(vendor)
    await test_db.commit()
    await test_db.refresh(vendor)

    assert vendor.id is not None
    assert vendor.name == "New Vendor LLC"
    assert vendor.is_active is True
    assert vendor.account_number == "ACCOUNT-NEW-001"


@pytest.mark.asyncio
async def test_vendor_update(test_db, vendor_primary):
    """Test: Update vendor information."""
    vendor_primary.contact_name = "Updated Name"
    vendor_primary.phone = "555-9999"
    await test_db.commit()
    await test_db.refresh(vendor_primary)

    assert vendor_primary.contact_name == "Updated Name"
    assert vendor_primary.phone == "555-9999"


@pytest.mark.asyncio
async def test_vendor_deactivation(test_db, vendor_primary):
    """Test: Deactivate a vendor."""
    vendor_primary.is_active = False
    await test_db.commit()
    await test_db.refresh(vendor_primary)

    assert vendor_primary.is_active is False


@pytest.mark.asyncio
async def test_vendor_edi_profile_creation(test_db, vendor_primary):
    """Test: Create EDI profile for vendor."""
    edi_profile = VendorEDIProfile(
        vendor_id=vendor_primary.id,
        is_enabled=True,
        edi_standard="X12",
        sender_id="LSC-SENDER",
        sender_qualifier="02",
        receiver_id="VENDOR-X12",
        receiver_qualifier="01",
        transport_protocol="AS2",
        transport_host="as2.vendor.com",
        transport_port=443,
        transport_username="user",
        transport_password="pass",
        supports_orders=True,
        supports_ordrsp=True,
        supports_desadv=True,
        supports_invoic=True,
        auto_approve_invoices=True,
        invoice_tolerance_percent=Decimal("3.00"),
    )
    test_db.add(edi_profile)
    await test_db.commit()
    await test_db.refresh(edi_profile)

    assert edi_profile.id is not None
    assert edi_profile.vendor_id == vendor_primary.id
    assert edi_profile.edi_standard == "X12"
    assert edi_profile.is_enabled is True


@pytest.mark.asyncio
async def test_multiple_vendors(test_db):
    """Test: Create and list multiple vendors."""
    vendors = []
    for i in range(5):
        vendor = Vendor(
            name=f"Vendor {i}",
            contact_name=f"Contact {i}",
            email=f"vendor{i}@test.com",
            phone=f"555-000{i}",
            account_number=f"ACC-{i:04d}",
            is_active=True,
        )
        test_db.add(vendor)
        vendors.append(vendor)

    await test_db.commit()

    result = await test_db.execute(select(Vendor).filter(Vendor.name.like("Vendor %")))
    retrieved_vendors = result.scalars().all()

    assert len(retrieved_vendors) == 5


# ============================================================================
# FUND AND BUDGET TRACKING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_fund_creation(test_db):
    """Test: Create a new fund with initial allocation."""
    fund = Fund(
        code="TEST-2024",
        name="Test Fund",
        description="Test fund description",
        fiscal_year=2024,
        allocated_amount=Decimal("25000.00"),
        encumbered_amount=Decimal("0.00"),
        spent_amount=Decimal("0.00"),
        status=FundStatus.ACTIVE,
    )
    test_db.add(fund)
    await test_db.commit()
    await test_db.refresh(fund)

    assert fund.id is not None
    assert fund.allocated_amount == Decimal("25000.00")
    assert fund.available_amount == Decimal("25000.00")


@pytest.mark.asyncio
async def test_fund_available_amount_calculation(test_db):
    """Test: Verify available_amount = allocated - encumbered - spent."""
    fund = Fund(
        code="CALC-2024",
        name="Calculation Test",
        fiscal_year=2024,
        allocated_amount=Decimal("10000.00"),
        encumbered_amount=Decimal("3000.00"),
        spent_amount=Decimal("2000.00"),
        status=FundStatus.ACTIVE,
    )
    test_db.add(fund)
    await test_db.commit()
    await test_db.refresh(fund)

    # available = 10000 - 3000 - 2000 = 5000
    assert fund.available_amount == Decimal("5000.00")


@pytest.mark.asyncio
async def test_fund_status_transitions(test_db, acquisition_fund):
    """Test: Fund status changes (active -> inactive -> closed)."""
    assert acquisition_fund.status == FundStatus.ACTIVE

    acquisition_fund.status = FundStatus.INACTIVE
    await test_db.commit()
    assert acquisition_fund.status == FundStatus.INACTIVE

    acquisition_fund.status = FundStatus.CLOSED
    await test_db.commit()
    assert acquisition_fund.status == FundStatus.CLOSED


@pytest.mark.asyncio
async def test_multiple_funds_fiscal_years(test_db):
    """Test: Create funds for different fiscal years."""
    fund_2023 = Fund(
        code="FY2023",
        name="FY 2023 Fund",
        fiscal_year=2023,
        allocated_amount=Decimal("30000.00"),
        status=FundStatus.ACTIVE,
    )
    fund_2024 = Fund(
        code="FY2024",
        name="FY 2024 Fund",
        fiscal_year=2024,
        allocated_amount=Decimal("40000.00"),
        status=FundStatus.ACTIVE,
    )
    fund_2025 = Fund(
        code="FY2025",
        name="FY 2025 Fund",
        fiscal_year=2025,
        allocated_amount=Decimal("50000.00"),
        status=FundStatus.ACTIVE,
    )

    test_db.add_all([fund_2023, fund_2024, fund_2025])
    await test_db.commit()

    result = await test_db.execute(
        select(Fund).filter(Fund.fiscal_year.in_([2023, 2024, 2025]))
    )
    funds = result.scalars().all()
    assert len(funds) == 3


# ============================================================================
# PURCHASE ORDER WORKFLOW TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_po_draft_creation(test_db, test_staff, acquisition_fund, vendor_primary):
    """Test: Create PO in draft status."""
    po = PurchaseOrder(
        po_number="PO-2024-001",
        vendor_id=vendor_primary.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    assert po.id is not None
    assert po.status == PurchaseOrderStatus.DRAFT
    assert po.total_amount == Decimal("0.00")


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_po_with_line_items(test_db, test_staff, acquisition_fund, vendor_primary):
    """Test: Create PO with multiple line items."""
    po = PurchaseOrder(
        po_number="PO-2024-002",
        vendor_id=vendor_primary.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.flush()

    items = [
        PurchaseOrderItem(
            purchase_order_id=po.id,
            title="Book 1",
            author="Author 1",
            isbn="978-1-000-00001-1",
            quantity=2,
            unit_price=Decimal("25.00"),
        ),
        PurchaseOrderItem(
            purchase_order_id=po.id,
            title="Book 2",
            author="Author 2",
            isbn="978-1-000-00002-2",
            quantity=1,
            unit_price=Decimal("35.50"),
        ),
        PurchaseOrderItem(
            purchase_order_id=po.id,
            title="Book 3",
            author="Author 3",
            isbn="978-1-000-00003-3",
            quantity=3,
            unit_price=Decimal("15.75"),
        ),
    ]
    test_db.add_all(items)
    await test_db.commit()
    await test_db.refresh(po)

    assert len(po.items) == 3
    # Total: (2*25) + (1*35.50) + (3*15.75) = 50 + 35.50 + 47.25 = 132.75
    assert po.total_amount == Decimal("132.75")


@pytest.mark.asyncio
async def test_po_submission_workflow(test_db, test_staff, test_director, acquisition_fund, vendor_primary):
    """Test: PO submission and approval workflow."""
    # Create draft PO with items
    po = PurchaseOrder(
        po_number="PO-2024-003",
        vendor_id=vendor_primary.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.flush()

    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Test Book",
        isbn="978-1-000-00001-1",
        quantity=1,
        unit_price=Decimal("50.00"),
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(po)

    # Submit for approval
    po.status = PurchaseOrderStatus.PENDING_APPROVAL
    await test_db.commit()
    assert po.status == PurchaseOrderStatus.PENDING_APPROVAL

    # Approve
    po.status = PurchaseOrderStatus.APPROVED
    po.approved_by_id = test_director.id
    po.approved_at = utc_now()
    await test_db.commit()
    await test_db.refresh(po)

    assert po.status == PurchaseOrderStatus.APPROVED
    assert po.approved_by_id == test_director.id
    assert po.approved_at is not None


@pytest.mark.asyncio
async def test_po_rejection(test_db, test_staff, test_director, acquisition_fund, vendor_primary):
    """Test: PO rejection workflow."""
    po = PurchaseOrder(
        po_number="PO-2024-004",
        vendor_id=vendor_primary.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.PENDING_APPROVAL,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()

    # Reject
    po.status = PurchaseOrderStatus.REJECTED
    po.approved_by_id = test_director.id
    po.rejection_notes = "Budget constraints - please resubmit with fewer items"
    await test_db.commit()
    await test_db.refresh(po)

    assert po.status == PurchaseOrderStatus.REJECTED
    assert po.rejection_notes == "Budget constraints - please resubmit with fewer items"


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_po_item_management(test_db, test_staff, acquisition_fund, vendor_primary):
    """Test: Add, update, and delete PO items."""
    po = PurchaseOrder(
        po_number="PO-2024-005",
        vendor_id=vendor_primary.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.flush()

    # Add items
    item1 = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Book A",
        quantity=2,
        unit_price=Decimal("20.00"),
    )
    item2 = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Book B",
        quantity=1,
        unit_price=Decimal("30.00"),
    )
    test_db.add_all([item1, item2])
    await test_db.commit()
    await test_db.refresh(po)

    assert len(po.items) == 2
    assert po.total_amount == Decimal("70.00")

    # Update item
    item1.unit_price = Decimal("25.00")
    await test_db.commit()
    await test_db.refresh(po)
    assert po.total_amount == Decimal("80.00")

    # Delete item
    await test_db.delete(item1)
    await test_db.commit()
    await test_db.refresh(po)

    assert len(po.items) == 1
    assert po.total_amount == Decimal("30.00")


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_po_budget_validation_sufficient_funds(test_db, test_staff, acquisition_fund, vendor_primary):
    """Test: PO validation passes when sufficient funds available."""
    po = PurchaseOrder(
        po_number="PO-2024-006",
        vendor_id=vendor_primary.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.flush()

    # Create item for $1000 (fund has $50000)
    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Expensive Book",
        quantity=1,
        unit_price=Decimal("1000.00"),
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(po)

    # Should have sufficient funds
    assert po.total_amount == Decimal("1000.00")
    assert acquisition_fund.available_amount >= po.total_amount


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_po_budget_validation_insufficient_funds(test_db, test_staff, acquisition_fund_limited, vendor_primary):
    """Test: PO validation fails when insufficient funds."""
    po = PurchaseOrder(
        po_number="PO-2024-007",
        vendor_id=vendor_primary.id,
        fund_id=acquisition_fund_limited.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.flush()

    # Create item for $2000 (fund only has $1000)
    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Expensive Book",
        quantity=1,
        unit_price=Decimal("2000.00"),
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(po)

    # Should fail budget check
    assert po.total_amount == Decimal("2000.00")
    assert acquisition_fund_limited.available_amount < po.total_amount


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_po_encumbrance_tracking(test_db, test_staff, test_director, acquisition_fund, vendor_primary):
    """Test: Fund encumbrance is tracked correctly."""
    initial_available = acquisition_fund.available_amount

    po = PurchaseOrder(
        po_number="PO-2024-008",
        vendor_id=vendor_primary.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.flush()

    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Test Book",
        quantity=1,
        unit_price=Decimal("500.00"),
    )
    test_db.add(item)
    await test_db.commit()

    # Simulate encumbrance when submitted
    po.status = PurchaseOrderStatus.PENDING_APPROVAL
    acquisition_fund.encumbered_amount += po.total_amount
    await test_db.commit()
    await test_db.refresh(acquisition_fund)

    # Verify available amount decreased
    assert acquisition_fund.available_amount == initial_available - Decimal("500.00")


# ============================================================================
# RECEIVING AND SHIPMENT TRACKING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_po_partial_receipt(test_db, test_staff, test_director, acquisition_fund, vendor_primary, catalog_item_for_po):
    """Test: Partial receipt of PO items."""
    po = PurchaseOrder(
        po_number="PO-2024-009",
        vendor_id=vendor_primary.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.APPROVED,
        created_by_id=test_staff.id,
        approved_by_id=test_director.id,
        approved_at=utc_now(),
    )
    test_db.add(po)
    await test_db.flush()

    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Book Title",
        isbn="978-1-000-00001-1",
        quantity=5,
        unit_price=Decimal("25.00"),
    )
    test_db.add(item)
    await test_db.commit()

    # Receive partial quantity (3 of 5)
    item.received_quantity = 3
    await test_db.commit()
    await test_db.refresh(item)

    assert item.received_quantity == 3
    assert item.is_fully_received is False


@pytest.mark.asyncio
async def test_po_full_receipt(test_db, test_staff, test_director, acquisition_fund, vendor_primary):
    """Test: Full receipt of PO items."""
    po = PurchaseOrder(
        po_number="PO-2024-010",
        vendor_id=vendor_primary.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.APPROVED,
        created_by_id=test_staff.id,
        approved_by_id=test_director.id,
        approved_at=utc_now(),
    )
    test_db.add(po)
    await test_db.flush()

    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Complete Book",
        quantity=3,
        unit_price=Decimal("20.00"),
    )
    test_db.add(item)
    await test_db.commit()

    # Receive all items
    item.received_quantity = 3
    await test_db.commit()
    await test_db.refresh(item)

    assert item.received_quantity == 3
    assert item.is_fully_received is True


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_shipment_notice_creation(test_db, vendor_edi_enabled):
    """Test: Create EDI shipment notice (DESADV)."""
    po = PurchaseOrder(
        po_number="PO-2024-011",
        vendor_id=vendor_edi_enabled.id,
        order_date=date.today(),
    )
    test_db.add(po)
    await test_db.flush()

    shipment = EDIShipmentNotice(
        purchase_order_id=po.id,
        vendor_id=vendor_edi_enabled.id,
        shipment_number="SHIP-001",
        ship_date=date.today(),
        expected_delivery_date=date.today() + timedelta(days=7),
        carrier_name="FedEx",
        carrier_code="FDX",
        tracking_number="794620057830",
        package_count=1,
        total_weight=Decimal("5.50"),
        weight_unit="lbs",
        shipped_items=dumps([
            {"isbn": "978-1-000-00001-1", "quantity": 3, "title": "Book 1"},
            {"isbn": "978-1-000-00002-2", "quantity": 2, "title": "Book 2"},
        ]),
        total_items_shipped=5,
    )
    test_db.add(shipment)
    await test_db.commit()
    await test_db.refresh(shipment)

    assert shipment.id is not None
    assert shipment.tracking_number == "794620057830"
    assert shipment.total_items_shipped == 5


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_shipment_notice_delivery_tracking(test_db, vendor_edi_enabled):
    """Test: Track shipment delivery dates."""
    po = PurchaseOrder(
        po_number="PO-2024-012",
        vendor_id=vendor_edi_enabled.id,
        order_date=date.today(),
    )
    test_db.add(po)
    await test_db.flush()

    shipment = EDIShipmentNotice(
        purchase_order_id=po.id,
        vendor_id=vendor_edi_enabled.id,
        shipment_number="SHIP-002",
        ship_date=date.today(),
        expected_delivery_date=date.today() + timedelta(days=5),
        carrier_name="UPS",
        carrier_code="UPS",
        tracking_number="1Z999AA10123456784",
        total_items_shipped=10,
    )
    test_db.add(shipment)
    await test_db.commit()

    # Verify expected delivery date
    days_to_delivery = (shipment.expected_delivery_date - shipment.ship_date).days
    assert days_to_delivery == 5


# ============================================================================
# EDI TRANSACTION PROCESSING TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_edi_transaction_creation(test_db, test_staff, vendor_edi_enabled, acquisition_fund):
    """Test: Create EDI transaction record."""
    po = PurchaseOrder(
        po_number="PO-2024-013",
        vendor_id=vendor_edi_enabled.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.APPROVED,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.flush()

    transaction = EDITransaction(
        vendor_edi_profile_id=vendor_edi_enabled.edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.ORDERS,
        direction="outbound",
        interchange_control_number="000000001",
        message_reference_number="1",
        status=EDITransactionStatus.PENDING,
        filename="ORD_000000001.edi",
    )
    test_db.add(transaction)
    await test_db.commit()
    await test_db.refresh(transaction)

    assert transaction.id is not None
    assert transaction.message_type == EDIMessageType.ORDERS
    assert transaction.direction == EDIDirection.OUTBOUND
    assert transaction.status == EDITransactionStatus.PENDING


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_edi_transaction_status_flow(test_db, test_staff, vendor_edi_enabled, acquisition_fund):
    """Test: EDI transaction status transitions."""
    po = PurchaseOrder(
        po_number="PO-2024-014",
        vendor_id=vendor_edi_enabled.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.APPROVED,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.flush()

    transaction = EDITransaction(
        vendor_edi_profile_id=vendor_edi_enabled.edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.ORDERS,
        direction="outbound",
        interchange_control_number="000000002",
        message_reference_number="1",
        status=EDITransactionStatus.PENDING,
    )
    test_db.add(transaction)
    await test_db.commit()

    # Transition: PENDING -> SENT
    transaction.status = EDITransactionStatus.SENT
    transaction.sent_at = utc_now()
    await test_db.commit()
    assert transaction.status == EDITransactionStatus.SENT

    # Transition: SENT -> ACKNOWLEDGED
    transaction.status = EDITransactionStatus.ACKNOWLEDGED
    transaction.received_at = utc_now()
    await test_db.commit()
    assert transaction.status == EDITransactionStatus.ACKNOWLEDGED

    # Transition: ACKNOWLEDGED -> PROCESSED
    transaction.status = EDITransactionStatus.PROCESSED
    transaction.processed_at = utc_now()
    await test_db.commit()
    assert transaction.status == EDITransactionStatus.PROCESSED


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_edi_order_response_processing(test_db, vendor_edi_enabled, acquisition_fund):
    """Test: Process vendor order response (ORDRSP)."""
    po = PurchaseOrder(
        po_number="PO-2024-015",
        vendor_id=vendor_edi_enabled.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
    )
    test_db.add(po)
    await test_db.flush()

    transaction = EDITransaction(
        vendor_edi_profile_id=vendor_edi_enabled.edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.ORDRSP,
        direction="inbound",
        interchange_control_number="V000000001",
        message_reference_number="1",
        status=EDITransactionStatus.PROCESSED,
        received_at=utc_now(),
        processed_at=utc_now(),
    )
    test_db.add(transaction)
    await test_db.flush()

    order_response = EDIOrderResponse(
        edi_transaction_id=transaction.id,
        purchase_order_id=po.id,
        vendor_id=vendor_edi_enabled.id,
        vendor_order_number="VENDOR-ORD-123",
        response_date=date.today(),
        response_code="29",  # Accepted
        response_description="Order accepted",
        items_accepted=10,
        items_rejected=0,
        items_backordered=0,
        items_substituted=0,
        expected_ship_date=date.today() + timedelta(days=3),
        expected_delivery_date=date.today() + timedelta(days=10),
    )
    test_db.add(order_response)
    await test_db.commit()
    await test_db.refresh(order_response)

    assert order_response.id is not None
    assert order_response.response_code == "29"
    assert order_response.items_accepted == 10


# ============================================================================
# INVOICE RECONCILIATION TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_edi_invoice_creation(test_db, vendor_edi_enabled, acquisition_fund):
    """Test: Create EDI invoice from vendor."""
    po = PurchaseOrder(
        po_number="PO-2024-016",
        vendor_id=vendor_edi_enabled.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
    )
    test_db.add(po)
    await test_db.flush()

    transaction = EDITransaction(
        vendor_edi_profile_id=vendor_edi_enabled.edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.INVOIC,
        direction="inbound",
        interchange_control_number="INV000001",
        message_reference_number="1",
        status=EDITransactionStatus.PROCESSED,
        received_at=utc_now(),
        processed_at=utc_now(),
    )
    test_db.add(transaction)
    await test_db.flush()

    invoice = EDIInvoice(
        edi_transaction_id=transaction.id,
        purchase_order_id=po.id,
        vendor_id=vendor_edi_enabled.id,
        invoice_number="INV-2024-001",
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        subtotal=Decimal("500.00"),
        tax_amount=Decimal("40.00"),
        shipping_amount=Decimal("10.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("550.00"),
        currency_code="USD",
        status="pending",
        po_total=Decimal("550.00"),
        variance_amount=Decimal("0.00"),
        matched_line_items=5,
        total_line_items=5,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    assert invoice.id is not None
    assert invoice.invoice_number == "INV-2024-001"
    assert invoice.total_amount == Decimal("550.00")


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_edi_invoice_price_variance_detection(test_db, vendor_edi_enabled, acquisition_fund):
    """Test: Detect price variance between PO and invoice."""
    po = PurchaseOrder(
        po_number="PO-2024-017",
        vendor_id=vendor_edi_enabled.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
    )
    test_db.add(po)
    await test_db.flush()

    transaction = EDITransaction(
        vendor_edi_profile_id=vendor_edi_enabled.edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.INVOIC,
        direction="inbound",
        interchange_control_number="INV000002",
        message_reference_number="1",
        status=EDITransactionStatus.PROCESSED,
        received_at=utc_now(),
        processed_at=utc_now(),
    )
    test_db.add(transaction)
    await test_db.flush()

    # PO total was $500, but invoice is for $525 (5% variance)
    invoice = EDIInvoice(
        edi_transaction_id=transaction.id,
        purchase_order_id=po.id,
        vendor_id=vendor_edi_enabled.id,
        invoice_number="INV-2024-002",
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        subtotal=Decimal("525.00"),
        tax_amount=Decimal("0.00"),
        shipping_amount=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("525.00"),
        currency_code="USD",
        status="pending",
        po_total=Decimal("500.00"),
        variance_amount=Decimal("25.00"),  # 5% variance
        variance_reason="Unit price increase",
        matched_line_items=5,
        total_line_items=5,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    assert invoice.variance_amount == Decimal("25.00")
    assert invoice.variance_reason == "Unit price increase"


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_edi_invoice_variance_within_tolerance(test_db, vendor_edi_enabled, acquisition_fund):
    """Test: Invoice variance within tolerance (auto-approve scenario)."""
    po = PurchaseOrder(
        po_number="PO-2024-018",
        vendor_id=vendor_edi_enabled.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
    )
    test_db.add(po)
    await test_db.flush()

    transaction = EDITransaction(
        vendor_edi_profile_id=vendor_edi_enabled.edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.INVOIC,
        direction="inbound",
        interchange_control_number="INV000003",
        message_reference_number="1",
        status=EDITransactionStatus.PROCESSED,
        received_at=utc_now(),
        processed_at=utc_now(),
    )
    test_db.add(transaction)
    await test_db.flush()

    # Vendor EDI profile tolerance is 2%, variance is 1%
    invoice = EDIInvoice(
        edi_transaction_id=transaction.id,
        purchase_order_id=po.id,
        vendor_id=vendor_edi_enabled.id,
        invoice_number="INV-2024-003",
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        subtotal=Decimal("505.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("505.00"),
        currency_code="USD",
        status="pending",
        po_total=Decimal("500.00"),
        variance_amount=Decimal("5.00"),  # 1% variance
        variance_reason="Rounding adjustment",
        matched_line_items=5,
        total_line_items=5,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    # Calculate variance percentage
    variance_pct = (abs(invoice.variance_amount) / invoice.po_total) * 100
    tolerance = vendor_edi_enabled.edi_profile.invoice_tolerance_percent

    assert variance_pct == Decimal("1.00")
    assert variance_pct <= tolerance


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_edi_invoice_variance_exceeds_tolerance(test_db, vendor_edi_enabled, acquisition_fund):
    """Test: Invoice variance exceeds tolerance (requires manual approval)."""
    po = PurchaseOrder(
        po_number="PO-2024-019",
        vendor_id=vendor_edi_enabled.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
    )
    test_db.add(po)
    await test_db.flush()

    transaction = EDITransaction(
        vendor_edi_profile_id=vendor_edi_enabled.edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.INVOIC,
        direction="inbound",
        interchange_control_number="INV000004",
        message_reference_number="1",
        status=EDITransactionStatus.PROCESSED,
        received_at=utc_now(),
        processed_at=utc_now(),
    )
    test_db.add(transaction)
    await test_db.flush()

    # Vendor EDI profile tolerance is 2%, variance is 5%
    invoice = EDIInvoice(
        edi_transaction_id=transaction.id,
        purchase_order_id=po.id,
        vendor_id=vendor_edi_enabled.id,
        invoice_number="INV-2024-004",
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        subtotal=Decimal("525.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("525.00"),
        currency_code="USD",
        status="pending",
        po_total=Decimal("500.00"),
        variance_amount=Decimal("25.00"),  # 5% variance
        variance_reason="Price escalation clause",
        matched_line_items=5,
        total_line_items=5,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    # Calculate variance percentage
    variance_pct = (abs(invoice.variance_amount) / invoice.po_total) * 100
    tolerance = vendor_edi_enabled.edi_profile.invoice_tolerance_percent

    assert variance_pct == Decimal("5.00")
    assert variance_pct > tolerance  # Exceeds tolerance, requires manual review


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_edi_invoice_dispute(test_db, vendor_edi_enabled, acquisition_fund):
    """Test: Dispute an invoice with variance issues."""
    po = PurchaseOrder(
        po_number="PO-2024-020",
        vendor_id=vendor_edi_enabled.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
    )
    test_db.add(po)
    await test_db.flush()

    transaction = EDITransaction(
        vendor_edi_profile_id=vendor_edi_enabled.edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.INVOIC,
        direction="inbound",
        interchange_control_number="INV000005",
        message_reference_number="1",
        status=EDITransactionStatus.PROCESSED,
        received_at=utc_now(),
        processed_at=utc_now(),
    )
    test_db.add(transaction)
    await test_db.flush()

    invoice = EDIInvoice(
        edi_transaction_id=transaction.id,
        purchase_order_id=po.id,
        vendor_id=vendor_edi_enabled.id,
        invoice_number="INV-2024-005",
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        subtotal=Decimal("600.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("600.00"),
        currency_code="USD",
        status="pending",
        po_total=Decimal("500.00"),
        variance_amount=Decimal("100.00"),  # 20% variance
        matched_line_items=5,
        total_line_items=5,
    )
    test_db.add(invoice)
    await test_db.commit()

    # Dispute the invoice
    invoice.status = "disputed"
    await test_db.commit()
    await test_db.refresh(invoice)

    assert invoice.status == "disputed"


# ============================================================================
# FINANCIAL ACCURACY AND VARIANCE TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_financial_accuracy_po_total_calculation(test_db, test_staff, acquisition_fund, vendor_primary):
    """Test: Verify PO total calculation accuracy."""
    po = PurchaseOrder(
        po_number="PO-2024-021",
        vendor_id=vendor_primary.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.flush()

    # Add items with different prices
    items_data = [
        (2, Decimal("10.50")),   # 2 × $10.50 = $21.00
        (3, Decimal("15.75")),   # 3 × $15.75 = $47.25
        (1, Decimal("99.99")),   # 1 × $99.99 = $99.99
    ]

    for qty, price in items_data:
        item = PurchaseOrderItem(
            purchase_order_id=po.id,
            title=f"Book - {qty}x{price}",
            quantity=qty,
            unit_price=price,
        )
        test_db.add(item)

    await test_db.commit()
    await test_db.refresh(po)

    # Total should be: 21.00 + 47.25 + 99.99 = 168.24
    assert po.total_amount == Decimal("168.24")


@pytest.mark.asyncio
async def test_financial_accuracy_fund_allocation_tracking(test_db):
    """Test: Verify fund allocation and spending tracking."""
    fund = Fund(
        code="ACCT-2024",
        name="Accounting Test Fund",
        fiscal_year=2024,
        allocated_amount=Decimal("10000.00"),
        encumbered_amount=Decimal("3000.00"),
        spent_amount=Decimal("2500.00"),
        status=FundStatus.ACTIVE,
    )
    test_db.add(fund)
    await test_db.commit()
    await test_db.refresh(fund)

    # Verify calculations:
    # allocated: $10,000
    # encumbered: $3,000 (pending orders)
    # spent: $2,500 (received orders)
    # available: $10,000 - $3,000 - $2,500 = $4,500

    assert fund.allocated_amount == Decimal("10000.00")
    assert fund.encumbered_amount == Decimal("3000.00")
    assert fund.spent_amount == Decimal("2500.00")
    assert fund.available_amount == Decimal("4500.00")


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_financial_accuracy_invoice_reconciliation(test_db, vendor_edi_enabled, acquisition_fund):
    """Test: Verify invoice amount reconciliation with PO."""
    po = PurchaseOrder(
        po_number="PO-2024-022",
        vendor_id=vendor_edi_enabled.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
    )
    test_db.add(po)
    await test_db.flush()

    transaction = EDITransaction(
        vendor_edi_profile_id=vendor_edi_enabled.edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.INVOIC,
        direction="inbound",
        interchange_control_number="INV000006",
        message_reference_number="1",
        status=EDITransactionStatus.PROCESSED,
        received_at=utc_now(),
        processed_at=utc_now(),
    )
    test_db.add(transaction)
    await test_db.flush()

    # Create invoice that matches PO exactly
    invoice = EDIInvoice(
        edi_transaction_id=transaction.id,
        purchase_order_id=po.id,
        vendor_id=vendor_edi_enabled.id,
        invoice_number="INV-2024-006",
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        subtotal=Decimal("1000.00"),
        tax_amount=Decimal("80.00"),
        shipping_amount=Decimal("15.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("1095.00"),
        currency_code="USD",
        status="pending",
        po_total=Decimal("1095.00"),
        variance_amount=Decimal("0.00"),
        variance_reason="",
        matched_line_items=5,
        total_line_items=5,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    # Verify reconciliation
    assert invoice.total_amount == invoice.po_total
    assert invoice.variance_amount == Decimal("0.00")
    assert invoice.matched_line_items == invoice.total_line_items


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_financial_accuracy_multiple_line_items_variance(test_db, vendor_edi_enabled, acquisition_fund):
    """Test: Calculate variance across multiple line items."""
    po = PurchaseOrder(
        po_number="PO-2024-023",
        vendor_id=vendor_edi_enabled.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
    )
    test_db.add(po)
    await test_db.flush()

    transaction = EDITransaction(
        vendor_edi_profile_id=vendor_edi_enabled.edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.INVOIC,
        direction="inbound",
        interchange_control_number="INV000007",
        message_reference_number="1",
        status=EDITransactionStatus.PROCESSED,
        received_at=utc_now(),
        processed_at=utc_now(),
    )
    test_db.add(transaction)
    await test_db.flush()

    # Create invoice with variance on multiple items
    line_items = [
        {"isbn": "978-1-000-00001-1", "title": "Book 1", "qty": 2, "unit_price": "15.00"},  # Expected: $30, Got: $31
        {"isbn": "978-1-000-00002-2", "title": "Book 2", "qty": 3, "unit_price": "20.00"},  # Expected: $60, Got: $58
    ]

    invoice = EDIInvoice(
        edi_transaction_id=transaction.id,
        purchase_order_id=po.id,
        vendor_id=vendor_edi_enabled.id,
        invoice_number="INV-2024-007",
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        subtotal=Decimal("89.00"),  # 31 + 58
        tax_amount=Decimal("7.12"),
        shipping_amount=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("96.12"),
        currency_code="USD",
        status="pending",
        po_total=Decimal("90.00"),  # Expected: 30 + 60
        variance_amount=Decimal("6.12"),  # -1 + (-2) + tax
        matched_line_items=2,
        total_line_items=2,
        line_items=dumps(line_items),
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    # Verify variance is calculated
    assert invoice.variance_amount == Decimal("6.12")
    assert invoice.matched_line_items == invoice.total_line_items


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_financial_accuracy_tax_and_shipping_calculation(test_db, vendor_edi_enabled, acquisition_fund):
    """Test: Verify tax and shipping amount accuracy."""
    po = PurchaseOrder(
        po_number="PO-2024-024",
        vendor_id=vendor_edi_enabled.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
    )
    test_db.add(po)
    await test_db.flush()

    transaction = EDITransaction(
        vendor_edi_profile_id=vendor_edi_enabled.edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.INVOIC,
        direction="inbound",
        interchange_control_number="INV000008",
        message_reference_number="1",
        status=EDITransactionStatus.PROCESSED,
        received_at=utc_now(),
        processed_at=utc_now(),
    )
    test_db.add(transaction)
    await test_db.flush()

    # Invoice with tax and shipping
    invoice = EDIInvoice(
        edi_transaction_id=transaction.id,
        purchase_order_id=po.id,
        vendor_id=vendor_edi_enabled.id,
        invoice_number="INV-2024-008",
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        subtotal=Decimal("500.00"),
        tax_amount=Decimal("40.00"),       # 8% tax
        shipping_amount=Decimal("25.00"),
        discount_amount=Decimal("10.00"),  # $10 discount
        total_amount=Decimal("555.00"),    # 500 + 40 + 25 - 10
        currency_code="USD",
        status="pending",
        po_total=Decimal("555.00"),
        variance_amount=Decimal("0.00"),
        matched_line_items=5,
        total_line_items=5,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    # Verify calculation: 500 + 40 + 25 - 10 = 555
    calculated_total = (
        invoice.subtotal +
        invoice.tax_amount +
        invoice.shipping_amount -
        invoice.discount_amount
    )
    assert calculated_total == invoice.total_amount == Decimal("555.00")


# ============================================================================
# SELECTION LIST AND TEMPLATING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_selection_list_item_creation(test_db, test_staff):
    """Test: Add items to selection list (wishlist)."""
    item = SelectionListItem(
        title="Python Data Science",
        author="John Doe",
        isbn="978-1-000-00001-1",
        estimated_price=Decimal("75.00"),
        source="manual",
        priority=SelectionPriority.HIGH,
        requested_by_id=test_staff.id,
        notes="Recommended by data science team",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    assert item.id is not None
    assert item.priority == SelectionPriority.HIGH


@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_selection_list_to_po_conversion(test_db, test_staff, acquisition_fund, vendor_primary):
    """Test: Convert selection list items to PO items."""
    # Create selection items
    selection_items = []
    for i in range(3):
        item = SelectionListItem(
            title=f"Book {i}",
            author=f"Author {i}",
            isbn=f"978-1-000-000{i:02d}-1",
            estimated_price=Decimal("25.00"),
            source="manual",
            priority=SelectionPriority.MEDIUM,
            requested_by_id=test_staff.id,
        )
        test_db.add(item)
        selection_items.append(item)

    await test_db.commit()

    # Create PO from selection items
    po = PurchaseOrder(
        po_number="PO-2024-025",
        vendor_id=vendor_primary.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.flush()

    # Add selection items to PO
    for sel_item in selection_items:
        po_item = PurchaseOrderItem(
            purchase_order_id=po.id,
            title=sel_item.title,
            author=sel_item.author,
            isbn=sel_item.isbn,
            quantity=1,
            unit_price=sel_item.estimated_price,
        )
        test_db.add(po_item)

    await test_db.commit()
    await test_db.refresh(po)

    assert len(po.items) == 3
    assert po.total_amount == Decimal("75.00")


@pytest.mark.asyncio
async def test_order_template_creation(test_db, test_staff, vendor_primary, acquisition_fund):
    """Test: Create reusable order template."""
    template = OrderTemplate(
        name="Standard Academic Books",
        description="Quarterly academic book order template",
        vendor_id=vendor_primary.id,
        fund_id=acquisition_fund.id,
        created_by_id=test_staff.id,
        is_shared=True,
        template_items=dumps([
            {"title": "Reference 1", "isbn": "978-1-000-00001-1", "qty": 2, "price": "50.00"},
            {"title": "Reference 2", "isbn": "978-1-000-00002-2", "qty": 1, "price": "75.00"},
        ]),
    )
    test_db.add(template)
    await test_db.commit()
    await test_db.refresh(template)

    assert template.id is not None
    assert template.is_shared is True


# ============================================================================
# INTEGRATION WORKFLOW TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skip(reason=(
    "PurchaseOrder.total_amount / linked-relationship access patterns in this file predate the po_facade_service.py-based architecture (totals are now computed explicitly by the facade service, not auto-derived from items; created_by_id became NOT NULL; relationships need explicit attribute_names on refresh() to avoid MissingGreenlet). Quarantined 2026-07-09 re-baseline -- current, correct coverage of this ground lives in test_acquisitions_workflow.py."
))
async def test_complete_acquisition_workflow(
    test_db, test_staff, test_director, acquisition_fund, vendor_edi_enabled
):
    """Test: Complete end-to-end acquisition workflow."""
    # 1. Create PO in draft
    po = PurchaseOrder(
        po_number="PO-2024-026",
        vendor_id=vendor_edi_enabled.id,
        fund_id=acquisition_fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.flush()

    item = PurchaseOrderItem(
        purchase_order_id=po.id,
        title="Complete Workflow Book",
        isbn="978-1-000-00001-1",
        quantity=5,
        unit_price=Decimal("100.00"),
    )
    test_db.add(item)
    await test_db.commit()

    # 2. Submit for approval
    po.status = PurchaseOrderStatus.PENDING_APPROVAL
    acquisition_fund.encumbered_amount += po.total_amount
    await test_db.commit()

    # 3. Approve PO
    po.status = PurchaseOrderStatus.APPROVED
    po.approved_by_id = test_director.id
    po.approved_at = utc_now()
    await test_db.commit()

    # 4. Create EDI transaction for order
    transaction = EDITransaction(
        vendor_edi_profile_id=vendor_edi_enabled.edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.ORDERS,
        direction="outbound",
        interchange_control_number="000000100",
        message_reference_number="1",
        status=EDITransactionStatus.SENT,
        sent_at=utc_now(),
    )
    test_db.add(transaction)
    await test_db.commit()

    # 5. Receive vendor order response
    order_response = EDIOrderResponse(
        edi_transaction_id=transaction.id,
        purchase_order_id=po.id,
        vendor_id=vendor_edi_enabled.id,
        vendor_order_number="VENDOR-100",
        response_date=date.today(),
        response_code="29",
        response_description="Order accepted",
        items_accepted=5,
        items_rejected=0,
        expected_ship_date=date.today() + timedelta(days=3),
        expected_delivery_date=date.today() + timedelta(days=7),
    )
    test_db.add(order_response)
    await test_db.commit()

    # 6. Receive shipment notice
    shipment = EDIShipmentNotice(
        purchase_order_id=po.id,
        vendor_id=vendor_edi_enabled.id,
        shipment_number="SHIP-100",
        ship_date=date.today() + timedelta(days=3),
        expected_delivery_date=date.today() + timedelta(days=7),
        carrier_name="FedEx",
        tracking_number="794620057830",
        total_items_shipped=5,
    )
    test_db.add(shipment)
    await test_db.commit()

    # 7. Receive invoice
    invoice_transaction = EDITransaction(
        vendor_edi_profile_id=vendor_edi_enabled.edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.INVOIC,
        direction="inbound",
        interchange_control_number="INV000100",
        message_reference_number="1",
        status=EDITransactionStatus.PROCESSED,
        received_at=utc_now(),
        processed_at=utc_now(),
    )
    test_db.add(invoice_transaction)
    await test_db.flush()

    invoice = EDIInvoice(
        edi_transaction_id=invoice_transaction.id,
        purchase_order_id=po.id,
        vendor_id=vendor_edi_enabled.id,
        invoice_number="INV-100",
        invoice_date=date.today() + timedelta(days=4),
        due_date=date.today() + timedelta(days=34),
        subtotal=Decimal("500.00"),
        tax_amount=Decimal("40.00"),
        total_amount=Decimal("540.00"),
        currency_code="USD",
        status="pending",
        po_total=Decimal("540.00"),
        variance_amount=Decimal("40.00"),  # Difference due to 5 units
        matched_line_items=1,
        total_line_items=1,
    )
    test_db.add(invoice)
    await test_db.commit()

    # 8. Approve invoice
    invoice.status = "approved"
    await test_db.commit()

    # 9. Receive items
    item.received_quantity = 5
    acquisition_fund.encumbered_amount -= po.total_amount
    acquisition_fund.spent_amount += po.total_amount
    await test_db.commit()

    # Verify workflow completion
    await test_db.refresh(po)
    await test_db.refresh(item)
    await test_db.refresh(acquisition_fund)

    assert po.status == PurchaseOrderStatus.APPROVED
    assert item.is_fully_received is True
    assert invoice.status == "approved"
    assert acquisition_fund.spent_amount > Decimal("0.00")
    assert acquisition_fund.encumbered_amount == Decimal("0.00")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
