# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive verification tests for LSC Acquisitions Workflow.

Covers all six workflow areas:
1. Vendor creation and management (CRUD, search, deactivation)
2. Purchase order creation with line items
3. Fund allocation and budget tracking (multi-fund, identity)
4. EDI transaction processing (profiles, transactions, order responses)
5. Shipment tracking and receiving (DESADV notices, partial/full receipt)
6. Invoice reconciliation (matching, variance, auto-approve, dispute, batch)

Also verifies:
- Financial accuracy (penny-level Decimal arithmetic)
- Complete acquisition lifecycle with EDI
"""

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.acquisition import (
    Fund,
    FundStatus,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    SelectionListItem,
    SelectionPriority,
    SelectionSource,
    Vendor,
)
from app.models.catalog import CatalogItem
from app.models.edi import (
    EDIInvoice,
    EDIInvoiceStatus,
    EDIMessageType,
    EDIOrderResponse,
    EDIShipmentNotice,
    EDIStandard,
    EDITransaction,
    EDITransactionStatus,
    TransportProtocol,
    VendorEDIProfile,
)
from app.models.inventory import AcquisitionSource, ItemCondition, ItemCopy
from app.models.user import User, UserRole
from app.services.edi.edi_reconciliation import EDIReconciliation


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
async def staff_user(test_db):
    """Staff user for acquisitions operations."""
    from app.core.security import hash_password

    user = User(
        email="acq_staff@lsc.example.com",
        password_hash=hash_password("AcqStaff123!"),
        first_name="Acq",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def admin_user(test_db):
    """Admin user for approval operations."""
    from app.core.security import hash_password

    user = User(
        email="acq_admin@lsc.example.com",
        password_hash=hash_password("AcqAdmin123!"),
        first_name="Acq",
        last_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user




@pytest.fixture
async def fund_general(test_db):
    """General acquisitions fund with $10,000."""
    f = Fund(
        code="VER-2026-GEN",
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
async def fund_ya(test_db):
    """Young Adult acquisitions fund with $5,000."""
    f = Fund(
        code="VER-2026-YA",
        name="YA Acquisitions 2026",
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
async def vendor_alpha(test_db):
    """Primary vendor: Midwest Library Supply."""
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
async def vendor_beta(test_db):
    """Secondary vendor: Pacific Book Distributors."""
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
async def catalog_item_rust(test_db):
    """Catalog item for linking on receipt."""
    item = CatalogItem(
        title="The Rust Programming Language",
        author="Steve Klabnik",
        isbn="978-1-7185-0044-0",
        description="Official Rust language guide",
        call_number="005.133 KLA",
        barcode="CAT-RUST-V001",
        publication_year=2023,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def edi_profile(test_db, vendor_alpha):
    """EDI profile for vendor_alpha with EDIFACT/SFTP."""
    profile = VendorEDIProfile(
        vendor_id=vendor_alpha.id,
        is_enabled=True,
        edi_standard=EDIStandard.EDIFACT,
        sender_id="LSC-LIB-001",
        sender_qualifier="ZZ",
        receiver_id="MLS-VENDOR-001",
        receiver_qualifier="ZZ",
        transport_protocol=TransportProtocol.SFTP,
        transport_host="edi.midwestlibrary.example.com",
        transport_port=22,
        transport_username="lsc_edi",
        transport_directory_outbound="/outbound",
        transport_directory_inbound="/inbound",
        supports_orders=True,
        supports_ordrsp=True,
        supports_desadv=True,
        supports_invoic=True,
        auto_approve_invoices=True,
        invoice_tolerance_percent=Decimal("5.00"),
        is_test_mode=True,
    )
    test_db.add(profile)
    await test_db.commit()
    await test_db.refresh(profile)
    return profile


# Helper to build a PO with items for reuse in multiple tests
async def _create_po_with_items(test_db, staff_user, fund, vendor, po_number, items_data, status=PurchaseOrderStatus.DRAFT):
    """Create a PO with line items and correct total.

    items_data: list of (title, author, isbn, qty, unit_price)
    Returns: (po, [items])
    """
    po = PurchaseOrder(
        po_number=po_number,
        vendor_id=vendor.id,
        fund_id=fund.id,
        order_date=date(2026, 2, 25),
        status=status,
        total_amount=Decimal("0.00"),
        created_by_id=staff_user.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)

    total = Decimal("0.00")
    items = []
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
        total += Decimal(str(qty)) * price
        items.append(item)

    po.total_amount = total
    await test_db.commit()
    for item in items:
        await test_db.refresh(item)
    await test_db.refresh(po)
    return po, items


# ============================================================================
# 1. VENDOR CREATION AND MANAGEMENT
# ============================================================================


@pytest.mark.asyncio
async def test_vendor_create_and_persist(test_db):
    """Create a vendor and verify all fields persist correctly."""
    vendor = Vendor(
        name="API Test Vendor",
        contact_name="Jane Doe",
        email="jane@apivendor.example.com",
        phone="555-9999",
        address="123 API St, Test City, TS 00000",
        account_number="ATV-001",
        is_active=True,
    )
    test_db.add(vendor)
    await test_db.commit()
    await test_db.refresh(vendor)

    assert vendor.id is not None
    assert vendor.name == "API Test Vendor"
    assert vendor.contact_name == "Jane Doe"
    assert vendor.email == "jane@apivendor.example.com"
    assert vendor.is_active is True


@pytest.mark.asyncio
async def test_vendor_retrieve_by_id(test_db, vendor_alpha):
    """Retrieve a specific vendor by ID from the database."""
    result = await test_db.execute(select(Vendor).where(Vendor.id == vendor_alpha.id))
    v = result.scalar_one()
    assert v.id == vendor_alpha.id
    assert v.name == "Midwest Library Supply"
    assert v.account_number == "MLS-9001"


@pytest.mark.asyncio
async def test_vendor_update_fields(test_db, vendor_alpha):
    """Update vendor fields and verify changes persist."""
    vendor_alpha.contact_name = "Alice Smith"
    vendor_alpha.phone = "555-1234"
    await test_db.commit()
    await test_db.refresh(vendor_alpha)

    assert vendor_alpha.contact_name == "Alice Smith"
    assert vendor_alpha.phone == "555-1234"
    # Unchanged fields remain
    assert vendor_alpha.name == "Midwest Library Supply"


@pytest.mark.asyncio
async def test_vendor_search_by_name(test_db, vendor_alpha, vendor_beta):
    """Search vendors by name using ilike query."""
    from sqlalchemy import or_
    search = "%Pacific%"
    result = await test_db.execute(
        select(Vendor).where(Vendor.name.ilike(search))
    )
    found = result.scalars().all()
    names = [v.name for v in found]
    assert "Pacific Book Distributors" in names
    assert "Midwest Library Supply" not in names


@pytest.mark.asyncio
async def test_vendor_filter_by_active_status(test_db, vendor_alpha, vendor_beta):
    """Filter vendors by active/inactive status."""
    # Deactivate vendor_alpha
    vendor_alpha.is_active = False
    await test_db.commit()

    active_result = await test_db.execute(
        select(Vendor).where(Vendor.is_active == True)
    )
    active_ids = [v.id for v in active_result.scalars().all()]
    assert vendor_alpha.id not in active_ids
    assert vendor_beta.id in active_ids

    inactive_result = await test_db.execute(
        select(Vendor).where(Vendor.is_active == False)
    )
    inactive_ids = [v.id for v in inactive_result.scalars().all()]
    assert vendor_alpha.id in inactive_ids


@pytest.mark.asyncio
async def test_vendor_deactivation_preserves_data(test_db, vendor_alpha):
    """Deactivating a vendor preserves all its data."""
    vendor_alpha.is_active = False
    await test_db.commit()
    await test_db.refresh(vendor_alpha)

    assert vendor_alpha.is_active is False
    assert vendor_alpha.name == "Midwest Library Supply"
    assert vendor_alpha.email == "orders@midwestlibrary.example.com"
    assert vendor_alpha.account_number == "MLS-9001"


@pytest.mark.asyncio
async def test_vendor_not_found_returns_none(test_db):
    """Querying a non-existent vendor returns None."""
    result = await test_db.execute(select(Vendor).where(Vendor.id == 99999))
    v = result.scalar_one_or_none()
    assert v is None


# ============================================================================
# 2. PURCHASE ORDER CREATION WITH LINE ITEMS
# ============================================================================


@pytest.mark.asyncio
async def test_po_creation_with_multiple_line_items(test_db, staff_user, fund_general, vendor_alpha):
    """Create PO with multiple items and verify line_total and po total."""
    items_data = [
        ("Pragmatic Programmer", "David Thomas", "978-0-13-595705-9", 2, Decimal("49.99")),
        ("Clean Code", "Robert Martin", "978-0-13-235088-4", 3, Decimal("39.99")),
        ("DDIA", "Martin Kleppmann", "978-1-4493-7332-0", 1, Decimal("55.00")),
    ]
    po, items = await _create_po_with_items(test_db, staff_user, fund_general, vendor_alpha, "PO-VER-001", items_data)

    # 2*49.99 + 3*39.99 + 1*55.00 = 99.98 + 119.97 + 55.00 = 274.95
    assert po.total_amount == Decimal("274.95")
    assert po.status == PurchaseOrderStatus.DRAFT
    assert len(items) == 3
    assert items[0].line_total == Decimal("99.98")
    assert items[1].line_total == Decimal("119.97")
    assert items[2].line_total == Decimal("55.00")


@pytest.mark.asyncio
async def test_po_status_transitions_full_workflow(test_db, staff_user, admin_user, fund_general, vendor_alpha):
    """Verify all status transitions: DRAFT → PENDING_APPROVAL → APPROVED → SUBMITTED."""
    items_data = [("Test Book", "Author", "978-0-00-000000-0", 1, Decimal("25.00"))]
    po, _ = await _create_po_with_items(test_db, staff_user, fund_general, vendor_alpha, "PO-VER-002", items_data)

    # DRAFT → PENDING_APPROVAL
    po.status = PurchaseOrderStatus.PENDING_APPROVAL
    await test_db.commit()
    assert po.status == PurchaseOrderStatus.PENDING_APPROVAL

    # PENDING_APPROVAL → APPROVED
    po.status = PurchaseOrderStatus.APPROVED
    po.approved_by_id = admin_user.id
    po.approved_at = datetime.now(tz=timezone.utc)
    await test_db.commit()
    assert po.status == PurchaseOrderStatus.APPROVED
    assert po.approved_by_id == admin_user.id

    # APPROVED → SUBMITTED (encumber budget)
    fund_general.encumbered_amount += po.total_amount
    po.status = PurchaseOrderStatus.SUBMITTED
    await test_db.commit()
    await test_db.refresh(fund_general)
    assert po.status == PurchaseOrderStatus.SUBMITTED
    assert fund_general.encumbered_amount == Decimal("25.00")


@pytest.mark.asyncio
async def test_po_rejection_with_notes(test_db, staff_user, admin_user, fund_general, vendor_alpha):
    """Reject a PO and verify rejection notes are stored."""
    items_data = [("Rejected Book", "Author", None, 1, Decimal("100.00"))]
    po, _ = await _create_po_with_items(test_db, staff_user, fund_general, vendor_alpha, "PO-VER-REJ", items_data)

    po.status = PurchaseOrderStatus.PENDING_APPROVAL
    await test_db.commit()

    po.status = PurchaseOrderStatus.REJECTED
    po.rejection_notes = "Budget constraints - defer to next quarter"
    po.approved_by_id = admin_user.id
    await test_db.commit()
    await test_db.refresh(po)

    assert po.status == PurchaseOrderStatus.REJECTED
    assert "Budget constraints" in po.rejection_notes


@pytest.mark.asyncio
async def test_po_item_is_fully_received_property(test_db, staff_user, fund_general, vendor_alpha):
    """Verify is_fully_received toggles at the right boundary."""
    items_data = [("Boundary Book", "Author", None, 5, Decimal("10.00"))]
    po, items = await _create_po_with_items(test_db, staff_user, fund_general, vendor_alpha, "PO-VER-RCV", items_data)
    item = items[0]

    assert not item.is_fully_received

    item.received_quantity = 4
    await test_db.commit()
    await test_db.refresh(item)
    assert not item.is_fully_received

    item.received_quantity = 5
    await test_db.commit()
    await test_db.refresh(item)
    assert item.is_fully_received

    # Over-receipt still counts as fully received
    item.received_quantity = 6
    await test_db.commit()
    await test_db.refresh(item)
    assert item.is_fully_received


# ============================================================================
# 3. FUND ALLOCATION AND BUDGET TRACKING
# ============================================================================


@pytest.mark.asyncio
async def test_fund_no_encumbrance_on_draft(test_db, staff_user, fund_general, vendor_alpha):
    """Draft PO should NOT encumber fund."""
    items_data = [("Draft Book", "Author", None, 2, Decimal("50.00"))]
    await _create_po_with_items(test_db, staff_user, fund_general, vendor_alpha, "PO-VER-DRAFT", items_data)

    await test_db.refresh(fund_general)
    assert fund_general.encumbered_amount == Decimal("0.00")
    assert fund_general.available_amount == Decimal("10000.00")


@pytest.mark.asyncio
async def test_fund_encumbrance_on_submit(test_db, staff_user, fund_general, vendor_alpha):
    """Submitting PO encumbers the fund by the PO total."""
    items_data = [("Submit Book", "Author", None, 4, Decimal("25.00"))]
    po, _ = await _create_po_with_items(test_db, staff_user, fund_general, vendor_alpha, "PO-VER-SUB", items_data)

    fund_general.encumbered_amount += po.total_amount  # 100.00
    po.status = PurchaseOrderStatus.SUBMITTED
    await test_db.commit()
    await test_db.refresh(fund_general)

    assert fund_general.encumbered_amount == Decimal("100.00")
    assert fund_general.available_amount == Decimal("9900.00")


@pytest.mark.asyncio
async def test_fund_accounting_identity_multi_operations(test_db, staff_user, fund_general, vendor_alpha, vendor_beta):
    """Fund accounting identity holds through multiple encumber/spend operations."""
    # PO1: $200 submitted
    items1 = [("Book A", "A", None, 4, Decimal("50.00"))]
    po1, _ = await _create_po_with_items(test_db, staff_user, fund_general, vendor_alpha, "PO-VER-ID-1", items1)
    fund_general.encumbered_amount += po1.total_amount
    po1.status = PurchaseOrderStatus.SUBMITTED
    await test_db.commit()

    # PO2: $350 submitted
    items2 = [("Book B", "B", None, 7, Decimal("50.00"))]
    po2, _ = await _create_po_with_items(test_db, staff_user, fund_general, vendor_beta, "PO-VER-ID-2", items2)
    fund_general.encumbered_amount += po2.total_amount
    po2.status = PurchaseOrderStatus.SUBMITTED
    await test_db.commit()
    await test_db.refresh(fund_general)

    assert fund_general.encumbered_amount == Decimal("550.00")
    # Identity: allocated = encumbered + spent + available
    assert fund_general.allocated_amount == (
        fund_general.encumbered_amount + fund_general.spent_amount + fund_general.available_amount
    )

    # Receive PO1 fully: move $200 from encumbered to spent
    fund_general.encumbered_amount -= po1.total_amount
    fund_general.spent_amount += po1.total_amount
    po1.status = PurchaseOrderStatus.RECEIVED
    await test_db.commit()
    await test_db.refresh(fund_general)

    assert fund_general.encumbered_amount == Decimal("350.00")
    assert fund_general.spent_amount == Decimal("200.00")
    assert fund_general.available_amount == Decimal("9450.00")
    # Identity still holds
    assert fund_general.allocated_amount == (
        fund_general.encumbered_amount + fund_general.spent_amount + fund_general.available_amount
    )


@pytest.mark.asyncio
async def test_fund_cancellation_releases_encumbrance(test_db, staff_user, fund_general, vendor_alpha):
    """Cancelling a submitted PO releases encumbered amount back to available."""
    items_data = [("Cancel Book", "Author", None, 3, Decimal("40.00"))]
    po, _ = await _create_po_with_items(test_db, staff_user, fund_general, vendor_alpha, "PO-VER-CAN", items_data)

    fund_general.encumbered_amount += po.total_amount  # 120.00
    po.status = PurchaseOrderStatus.SUBMITTED
    await test_db.commit()
    await test_db.refresh(fund_general)
    assert fund_general.available_amount == Decimal("9880.00")

    # Cancel
    fund_general.encumbered_amount -= po.total_amount
    po.status = PurchaseOrderStatus.CANCELLED
    await test_db.commit()
    await test_db.refresh(fund_general)

    assert fund_general.encumbered_amount == Decimal("0.00")
    assert fund_general.available_amount == Decimal("10000.00")


@pytest.mark.asyncio
async def test_fund_insufficient_budget_detection(test_db, staff_user, fund_ya, vendor_alpha):
    """Detect when PO total exceeds available fund balance."""
    items_data = [("Expensive Set", "Author", None, 10, Decimal("600.00"))]
    po, _ = await _create_po_with_items(test_db, staff_user, fund_ya, vendor_alpha, "PO-VER-INSUF", items_data)

    # PO total = $6,000 but fund only has $5,000
    assert po.total_amount == Decimal("6000.00")
    assert fund_ya.available_amount == Decimal("5000.00")
    assert po.total_amount > fund_ya.available_amount


@pytest.mark.asyncio
async def test_closed_fund_blocks_encumbrance(test_db):
    """Closed fund prevents any encumbrance modification."""
    f = Fund(
        code="VER-CLOSED",
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

    with pytest.raises(ValueError, match="Cannot reopen closed fund"):
        f.status = FundStatus.ACTIVE


@pytest.mark.asyncio
async def test_fund_create_and_verify(test_db):
    """Create fund and verify all fields including computed available_amount."""
    f = Fund(
        code="API-FUND-2026",
        name="API Test Fund",
        description="Fund created via test",
        fiscal_year=2026,
        allocated_amount=Decimal("7500.00"),
        encumbered_amount=Decimal("0.00"),
        spent_amount=Decimal("0.00"),
        status=FundStatus.ACTIVE,
    )
    test_db.add(f)
    await test_db.commit()
    await test_db.refresh(f)

    assert f.code == "API-FUND-2026"
    assert f.allocated_amount == Decimal("7500.00")
    assert f.available_amount == Decimal("7500.00")
    assert f.status == FundStatus.ACTIVE


@pytest.mark.asyncio
async def test_fund_list_query(test_db, fund_general, fund_ya):
    """Query multiple funds and verify both exist."""
    result = await test_db.execute(
        select(Fund).where(Fund.fiscal_year == 2026).order_by(Fund.code)
    )
    funds = result.scalars().all()
    assert len(funds) >= 2
    codes = [f.code for f in funds]
    assert "VER-2026-GEN" in codes
    assert "VER-2026-YA" in codes


# ============================================================================
# 4. EDI TRANSACTION PROCESSING
# ============================================================================


@pytest.mark.asyncio
async def test_edi_profile_creation(test_db, vendor_beta):
    """Create an EDI profile for a vendor with X12 standard."""
    profile = VendorEDIProfile(
        vendor_id=vendor_beta.id,
        is_enabled=True,
        edi_standard=EDIStandard.X12,
        sender_id="LSC-LIB-002",
        receiver_id="PBD-VENDOR-002",
        transport_protocol=TransportProtocol.FTPS,
        transport_host="edi.pacificbooks.example.com",
        transport_port=990,
        supports_orders=True,
        supports_ordrsp=True,
        supports_desadv=False,
        supports_invoic=True,
        auto_approve_invoices=False,
        invoice_tolerance_percent=Decimal("3.00"),
        is_test_mode=True,
    )
    test_db.add(profile)
    await test_db.commit()
    await test_db.refresh(profile)

    assert profile.edi_standard == EDIStandard.X12
    assert profile.transport_protocol == TransportProtocol.FTPS
    assert profile.supports_desadv is False
    assert profile.auto_approve_invoices is False
    assert profile.invoice_tolerance_percent == Decimal("3.00")


@pytest.mark.asyncio
async def test_edi_transaction_outbound_order(test_db, staff_user, fund_general, vendor_alpha, edi_profile):
    """Record an outbound EDI ORDERS transaction."""
    items_data = [("EDI Book", "Author", "978-0-00-111111-1", 2, Decimal("30.00"))]
    po, _ = await _create_po_with_items(test_db, staff_user, fund_general, vendor_alpha, "PO-VER-EDI-OUT", items_data)

    txn = EDITransaction(
        vendor_edi_profile_id=edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.ORDERS,
        direction="outbound",
        interchange_control_number="ICN-OUT-001",
        status=EDITransactionStatus.PENDING,
        raw_message="UNH+1+ORDERS:D:96A:UN'...",
        filename="orders_001.edi",
    )
    test_db.add(txn)
    await test_db.commit()
    await test_db.refresh(txn)

    assert txn.message_type == EDIMessageType.ORDERS
    assert txn.direction == "outbound"
    assert txn.status == EDITransactionStatus.PENDING

    # Mark as sent
    txn.status = EDITransactionStatus.SENT
    txn.sent_at = datetime.now(tz=timezone.utc)
    await test_db.commit()
    await test_db.refresh(txn)
    assert txn.status == EDITransactionStatus.SENT
    assert txn.sent_at is not None


@pytest.mark.asyncio
async def test_edi_transaction_retry_tracking(test_db, staff_user, fund_general, vendor_alpha, edi_profile):
    """Track retry count and next retry for failed transactions."""
    items_data = [("Retry Book", "Author", None, 1, Decimal("20.00"))]
    po, _ = await _create_po_with_items(test_db, staff_user, fund_general, vendor_alpha, "PO-VER-EDI-RETRY", items_data)

    txn = EDITransaction(
        vendor_edi_profile_id=edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.ORDERS,
        direction="outbound",
        interchange_control_number="ICN-RETRY-001",
        status=EDITransactionStatus.FAILED,
        retry_count=0,
        last_error="Connection timeout",
    )
    test_db.add(txn)
    await test_db.commit()
    await test_db.refresh(txn)

    # Simulate retries
    txn.retry_count = 1
    txn.status = EDITransactionStatus.RETRY
    txn.next_retry_at = datetime.now(tz=timezone.utc) + timedelta(minutes=60)
    await test_db.commit()
    await test_db.refresh(txn)

    assert txn.retry_count == 1
    assert txn.status == EDITransactionStatus.RETRY
    assert txn.next_retry_at is not None
    assert txn.last_error == "Connection timeout"


@pytest.mark.asyncio
async def test_edi_order_response_processing(test_db, staff_user, fund_general, vendor_alpha, edi_profile):
    """Process an inbound ORDRSP (order response) from vendor."""
    items_data = [
        ("Accepted Book", "Author A", "978-0-00-222222-2", 3, Decimal("25.00")),
        ("Backordered Book", "Author B", "978-0-00-333333-3", 2, Decimal("30.00")),
    ]
    po, _ = await _create_po_with_items(
        test_db, staff_user, fund_general, vendor_alpha, "PO-VER-ORDRSP", items_data,
        status=PurchaseOrderStatus.SUBMITTED,
    )

    # Create inbound transaction
    txn = EDITransaction(
        vendor_edi_profile_id=edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.ORDRSP,
        direction="inbound",
        interchange_control_number="ICN-ORDRSP-001",
        status=EDITransactionStatus.PROCESSED,
        received_at=datetime.now(tz=timezone.utc),
        processed_at=datetime.now(tz=timezone.utc),
    )
    test_db.add(txn)
    await test_db.commit()
    await test_db.refresh(txn)

    # Create order response
    ordrsp = EDIOrderResponse(
        edi_transaction_id=txn.id,
        purchase_order_id=po.id,
        vendor_id=vendor_alpha.id,
        vendor_order_number="MLS-ORD-2026-0042",
        response_date=datetime.now(tz=timezone.utc),
        response_code="4",  # Changed (partial acceptance)
        response_description="Partial acceptance - 1 item backordered",
        items_accepted=3,
        items_rejected=0,
        items_backordered=2,
        items_substituted=0,
        expected_ship_date=datetime.now(tz=timezone.utc) + timedelta(days=5),
        expected_delivery_date=datetime.now(tz=timezone.utc) + timedelta(days=10),
        is_processed=True,
        processed_at=datetime.now(tz=timezone.utc),
    )
    test_db.add(ordrsp)
    await test_db.commit()
    await test_db.refresh(ordrsp)

    assert ordrsp.response_code == "4"
    assert ordrsp.items_accepted == 3
    assert ordrsp.items_backordered == 2
    assert ordrsp.vendor_order_number == "MLS-ORD-2026-0042"
    assert ordrsp.is_processed is True


@pytest.mark.asyncio
async def test_edi_profile_message_type_support(test_db, vendor_alpha, edi_profile):
    """Verify EDI profile message type flags."""
    assert edi_profile.supports_orders is True
    assert edi_profile.supports_ordrsp is True
    assert edi_profile.supports_desadv is True
    assert edi_profile.supports_invoic is True

    # Disable DESADV support
    edi_profile.supports_desadv = False
    await test_db.commit()
    await test_db.refresh(edi_profile)
    assert edi_profile.supports_desadv is False


# ============================================================================
# 5. SHIPMENT TRACKING AND RECEIVING
# ============================================================================


@pytest.mark.asyncio
async def test_shipment_notice_creation(test_db, staff_user, fund_general, vendor_alpha, edi_profile):
    """Create and verify a shipment notice (DESADV)."""
    items_data = [("Shipped Book", "Author", "978-0-00-444444-4", 5, Decimal("20.00"))]
    po, po_items = await _create_po_with_items(
        test_db, staff_user, fund_general, vendor_alpha, "PO-VER-SHIP", items_data,
        status=PurchaseOrderStatus.SUBMITTED,
    )
    fund_general.encumbered_amount += po.total_amount
    await test_db.commit()

    # Create transaction for the shipment notice
    txn = EDITransaction(
        vendor_edi_profile_id=edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.DESADV,
        direction="inbound",
        interchange_control_number="ICN-DESADV-001",
        status=EDITransactionStatus.PROCESSED,
        received_at=datetime.now(tz=timezone.utc),
    )
    test_db.add(txn)
    await test_db.commit()
    await test_db.refresh(txn)

    # Create shipment notice
    shipped_items_json = json.dumps([{
        "isbn": "978-0-00-444444-4",
        "title": "Shipped Book",
        "quantity": 3,
        "po_item_id": po_items[0].id,
    }])

    notice = EDIShipmentNotice(
        edi_transaction_id=txn.id,
        purchase_order_id=po.id,
        vendor_id=vendor_alpha.id,
        shipment_number="SHIP-MLS-2026-001",
        ship_date=datetime.now(tz=timezone.utc),
        expected_delivery_date=datetime.now(tz=timezone.utc) + timedelta(days=5),
        carrier_name="FedEx",
        carrier_code="FEDX",
        tracking_number="794644790132",
        package_count=1,
        total_weight=Decimal("5.50"),
        weight_unit="LB",
        shipped_items=shipped_items_json,
        total_items_shipped=3,
        is_processed=False,
    )
    test_db.add(notice)
    await test_db.commit()
    await test_db.refresh(notice)

    assert notice.shipment_number == "SHIP-MLS-2026-001"
    assert notice.carrier_name == "FedEx"
    assert notice.tracking_number == "794644790132"
    assert notice.total_items_shipped == 3
    assert notice.is_processed is False

    # Parse shipped items
    items = json.loads(notice.shipped_items)
    assert len(items) == 1
    assert items[0]["quantity"] == 3


@pytest.mark.asyncio
async def test_partial_receive_updates_fund(test_db, staff_user, fund_general, vendor_alpha):
    """Partial receive moves proportional amount from encumbered to spent."""
    items_data = [("Partial Book", "Author", None, 10, Decimal("15.00"))]
    po, items = await _create_po_with_items(
        test_db, staff_user, fund_general, vendor_alpha, "PO-VER-PARTIAL", items_data,
        status=PurchaseOrderStatus.SUBMITTED,
    )
    fund_general.encumbered_amount = po.total_amount  # 150.00
    await test_db.commit()

    # Receive 4 of 10
    item = items[0]
    recv_value = Decimal("4") * item.unit_price  # 60.00
    item.received_quantity = 4
    fund_general.encumbered_amount -= recv_value
    fund_general.spent_amount += recv_value
    po.status = PurchaseOrderStatus.PARTIALLY_RECEIVED
    await test_db.commit()
    await test_db.refresh(fund_general)

    assert fund_general.encumbered_amount == Decimal("90.00")
    assert fund_general.spent_amount == Decimal("60.00")
    assert fund_general.available_amount == Decimal("9850.00")
    assert not item.is_fully_received

    # Receive remaining 6
    recv_remaining = Decimal("6") * item.unit_price  # 90.00
    item.received_quantity = 10
    fund_general.encumbered_amount -= recv_remaining
    fund_general.spent_amount += recv_remaining
    po.status = PurchaseOrderStatus.RECEIVED
    await test_db.commit()
    await test_db.refresh(fund_general)
    await test_db.refresh(item)

    assert fund_general.encumbered_amount == Decimal("0.00")
    assert fund_general.spent_amount == Decimal("150.00")
    assert fund_general.available_amount == Decimal("9850.00")
    assert item.is_fully_received
    # Identity
    assert fund_general.allocated_amount == (
        fund_general.encumbered_amount + fund_general.spent_amount + fund_general.available_amount
    )


@pytest.mark.asyncio
async def test_receive_creates_item_copies(test_db, staff_user, fund_general, vendor_alpha, catalog_item_rust):
    """Receiving items creates ItemCopy records linked to catalog and PO."""
    items_data = [
        (catalog_item_rust.title, catalog_item_rust.author, catalog_item_rust.isbn, 3, Decimal("45.00")),
    ]
    po, po_items = await _create_po_with_items(
        test_db, staff_user, fund_general, vendor_alpha, "PO-VER-COPIES", items_data,
        status=PurchaseOrderStatus.SUBMITTED,
    )
    po_items[0].catalog_item_id = catalog_item_rust.id
    await test_db.commit()
    await test_db.refresh(po_items[0])

    # Receive all 3 and create copies
    po_items[0].received_quantity = 3
    copies = []
    for n in range(1, 4):
        copy = ItemCopy(
            catalog_item_id=catalog_item_rust.id,
            barcode=f"VER-COPY-{n:04d}",
            copy_number=n,
            condition=ItemCondition.NEW,
            acquisition_source=AcquisitionSource.PURCHASE,
            purchase_order_item_id=po_items[0].id,
            location="Receiving",
            replacement_cost=po_items[0].unit_price,
        )
        copies.append(copy)
    test_db.add_all(copies)
    po.status = PurchaseOrderStatus.RECEIVED
    await test_db.commit()

    result = await test_db.execute(
        select(ItemCopy).where(ItemCopy.purchase_order_item_id == po_items[0].id)
    )
    created = result.scalars().all()
    assert len(created) == 3
    assert all(c.catalog_item_id == catalog_item_rust.id for c in created)
    assert all(c.condition == ItemCondition.NEW for c in created)
    assert all(c.acquisition_source == AcquisitionSource.PURCHASE for c in created)
    assert all(c.replacement_cost == Decimal("45.00") for c in created)


@pytest.mark.asyncio
async def test_shipment_processing_marks_processed(test_db, staff_user, fund_general, vendor_alpha, edi_profile):
    """Processing a shipment notice marks it as processed."""
    items_data = [("Process Book", "Author", None, 2, Decimal("25.00"))]
    po, _ = await _create_po_with_items(
        test_db, staff_user, fund_general, vendor_alpha, "PO-VER-PROC", items_data,
        status=PurchaseOrderStatus.SUBMITTED,
    )

    notice = EDIShipmentNotice(
        purchase_order_id=po.id,
        vendor_id=vendor_alpha.id,
        shipment_number="SHIP-PROC-001",
        ship_date=datetime.now(tz=timezone.utc),
        total_items_shipped=2,
        is_processed=False,
    )
    test_db.add(notice)
    await test_db.commit()
    await test_db.refresh(notice)

    assert notice.is_processed is False

    # Process it
    notice.is_processed = True
    notice.processed_at = datetime.now(tz=timezone.utc)
    await test_db.commit()
    await test_db.refresh(notice)

    assert notice.is_processed is True
    assert notice.processed_at is not None


# ============================================================================
# 6. INVOICE RECONCILIATION
# ============================================================================


@pytest.mark.asyncio
async def test_invoice_exact_match_reconciliation(test_db, staff_user, fund_general, vendor_alpha):
    """Invoice matching PO exactly results in MATCHED status."""
    items_data = [
        ("Match Book A", "Author A", "978-0-00-555555-5", 2, Decimal("30.00")),
        ("Match Book B", "Author B", "978-0-00-666666-6", 1, Decimal("40.00")),
    ]
    po, po_items = await _create_po_with_items(
        test_db, staff_user, fund_general, vendor_alpha, "PO-VER-MATCH", items_data,
        status=PurchaseOrderStatus.RECEIVED,
    )

    # Create invoice with exact same items
    invoice_line_items = json.dumps([
        {
            "line_number": 1,
            "isbn": "978-0-00-555555-5",
            "title": "Match Book A",
            "quantity": 2,
            "unit_price": "30.00",
            "line_total": "60.00",
        },
        {
            "line_number": 2,
            "isbn": "978-0-00-666666-6",
            "title": "Match Book B",
            "quantity": 1,
            "unit_price": "40.00",
            "line_total": "40.00",
        },
    ])

    invoice = EDIInvoice(
        purchase_order_id=po.id,
        vendor_id=vendor_alpha.id,
        invoice_number="INV-MATCH-001",
        invoice_date=datetime.now(tz=timezone.utc),
        due_date=datetime.now(tz=timezone.utc) + timedelta(days=30),
        subtotal=Decimal("100.00"),
        total_amount=Decimal("100.00"),
        status=EDIInvoiceStatus.PENDING,
        line_items=invoice_line_items,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    # Run reconciliation
    reconciler = EDIReconciliation(test_db)
    result = await reconciler.reconcile_invoice(invoice.id)

    assert result.status == "matched"
    assert result.matched_items == 2
    assert result.total_items == 2
    assert result.variance_amount == Decimal("0.00")
    assert len(result.discrepancies) == 0

    # Invoice status updated
    await test_db.refresh(invoice)
    assert invoice.status == EDIInvoiceStatus.MATCHED


@pytest.mark.asyncio
async def test_invoice_price_variance_detection(test_db, staff_user, fund_general, vendor_alpha):
    """Detect price variance when invoice price differs from PO."""
    items_data = [
        ("Price Var Book", "Author", "978-0-00-777777-7", 2, Decimal("25.00")),
    ]
    po, _ = await _create_po_with_items(
        test_db, staff_user, fund_general, vendor_alpha, "PO-VER-PRICEVAR", items_data,
        status=PurchaseOrderStatus.RECEIVED,
    )

    # Invoice has different unit price ($27.50 vs $25.00)
    invoice_line_items = json.dumps([{
        "line_number": 1,
        "isbn": "978-0-00-777777-7",
        "title": "Price Var Book",
        "quantity": 2,
        "unit_price": "27.50",
        "line_total": "55.00",
    }])

    invoice = EDIInvoice(
        purchase_order_id=po.id,
        vendor_id=vendor_alpha.id,
        invoice_number="INV-PRICEVAR-001",
        invoice_date=datetime.now(tz=timezone.utc),
        subtotal=Decimal("55.00"),
        total_amount=Decimal("55.00"),
        status=EDIInvoiceStatus.PENDING,
        line_items=invoice_line_items,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    reconciler = EDIReconciliation(test_db)
    result = await reconciler.reconcile_invoice(invoice.id)

    # Items with price variance are not counted as "matched", so with 0 matched
    # items and discrepancies present, status is "disputed"
    assert result.status == "disputed"
    assert result.matched_items == 0
    assert len(result.discrepancies) > 0
    # Check overall variance: invoice $55 vs PO $50
    assert result.variance_amount == Decimal("5.00")


@pytest.mark.asyncio
async def test_invoice_quantity_variance_detection(test_db, staff_user, fund_general, vendor_alpha):
    """Detect quantity variance when invoice qty differs from PO."""
    items_data = [
        ("Qty Var Book", "Author", "978-0-00-888888-8", 5, Decimal("20.00")),
    ]
    po, _ = await _create_po_with_items(
        test_db, staff_user, fund_general, vendor_alpha, "PO-VER-QTYVAR", items_data,
        status=PurchaseOrderStatus.RECEIVED,
    )

    # Invoice has different quantity (4 instead of 5)
    invoice_line_items = json.dumps([{
        "line_number": 1,
        "isbn": "978-0-00-888888-8",
        "title": "Qty Var Book",
        "quantity": 4,
        "unit_price": "20.00",
        "line_total": "80.00",
    }])

    invoice = EDIInvoice(
        purchase_order_id=po.id,
        vendor_id=vendor_alpha.id,
        invoice_number="INV-QTYVAR-001",
        invoice_date=datetime.now(tz=timezone.utc),
        subtotal=Decimal("80.00"),
        total_amount=Decimal("80.00"),
        status=EDIInvoiceStatus.PENDING,
        line_items=invoice_line_items,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    reconciler = EDIReconciliation(test_db)
    result = await reconciler.reconcile_invoice(invoice.id)

    # Quantity variance means item not counted as "matched", so with 0 matched
    # and discrepancies present, status is "disputed"
    assert result.status == "disputed"
    assert len(result.discrepancies) > 0
    # At least one discrepancy should mention quantity
    qty_disc = [d for d in result.discrepancies if d.get("type") == "quantity_variance"]
    assert len(qty_disc) >= 1


@pytest.mark.asyncio
async def test_invoice_manual_approval(test_db, staff_user, admin_user, fund_general, vendor_alpha):
    """Manually approve an invoice through the reconciliation service."""
    invoice = EDIInvoice(
        vendor_id=vendor_alpha.id,
        invoice_number="INV-APPROVE-001",
        invoice_date=datetime.now(tz=timezone.utc),
        total_amount=Decimal("200.00"),
        status=EDIInvoiceStatus.MATCHED,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    reconciler = EDIReconciliation(test_db)
    success, msg = await reconciler.approve_invoice(invoice.id, admin_user, notes="Approved after review")

    assert success is True
    assert msg == "Invoice approved"

    await test_db.refresh(invoice)
    assert invoice.status == EDIInvoiceStatus.APPROVED
    assert invoice.approved_by_id == admin_user.id
    assert invoice.approved_at is not None
    assert invoice.notes == "Approved after review"


@pytest.mark.asyncio
async def test_invoice_already_approved_cannot_reapprove(test_db, admin_user, vendor_alpha):
    """Cannot approve an already-approved invoice."""
    invoice = EDIInvoice(
        vendor_id=vendor_alpha.id,
        invoice_number="INV-REAPPROVE-001",
        invoice_date=datetime.now(tz=timezone.utc),
        total_amount=Decimal("100.00"),
        status=EDIInvoiceStatus.APPROVED,
        approved_by_id=admin_user.id,
        approved_at=datetime.now(tz=timezone.utc),
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    reconciler = EDIReconciliation(test_db)
    success, msg = await reconciler.approve_invoice(invoice.id, admin_user)

    assert success is False
    assert "already approved" in msg.lower()


@pytest.mark.asyncio
async def test_invoice_dispute(test_db, vendor_alpha):
    """Dispute an invoice and verify status change."""
    invoice = EDIInvoice(
        vendor_id=vendor_alpha.id,
        invoice_number="INV-DISPUTE-001",
        invoice_date=datetime.now(tz=timezone.utc),
        total_amount=Decimal("500.00"),
        status=EDIInvoiceStatus.PARTIAL_MATCH,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    reconciler = EDIReconciliation(test_db)
    success, msg = await reconciler.dispute_invoice(invoice.id, "Items not received - shipment damaged")

    assert success is True
    assert "disputed" in msg.lower()

    await test_db.refresh(invoice)
    assert invoice.status == EDIInvoiceStatus.DISPUTED
    assert invoice.rejection_reason == "Items not received - shipment damaged"


@pytest.mark.asyncio
async def test_invoice_cannot_dispute_approved(test_db, admin_user, vendor_alpha):
    """Cannot dispute an already-approved invoice."""
    invoice = EDIInvoice(
        vendor_id=vendor_alpha.id,
        invoice_number="INV-CANTDISPUTE-001",
        invoice_date=datetime.now(tz=timezone.utc),
        total_amount=Decimal("300.00"),
        status=EDIInvoiceStatus.APPROVED,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    reconciler = EDIReconciliation(test_db)
    success, msg = await reconciler.dispute_invoice(invoice.id, "Late dispute attempt")

    assert success is False
    assert "approved" in msg.lower()


@pytest.mark.asyncio
async def test_batch_reconciliation(test_db, staff_user, fund_general, vendor_alpha):
    """Batch reconcile multiple pending invoices."""
    # Create two POs with items
    items1 = [("Batch Book A", "AA", "978-0-00-999999-9", 1, Decimal("50.00"))]
    po1, _ = await _create_po_with_items(
        test_db, staff_user, fund_general, vendor_alpha, "PO-VER-BATCH-1", items1,
        status=PurchaseOrderStatus.RECEIVED,
    )

    items2 = [("Batch Book B", "BB", "978-0-01-000000-0", 2, Decimal("35.00"))]
    po2, _ = await _create_po_with_items(
        test_db, staff_user, fund_general, vendor_alpha, "PO-VER-BATCH-2", items2,
        status=PurchaseOrderStatus.RECEIVED,
    )

    # Create matching invoices
    inv1 = EDIInvoice(
        purchase_order_id=po1.id,
        vendor_id=vendor_alpha.id,
        invoice_number="INV-BATCH-001",
        invoice_date=datetime.now(tz=timezone.utc),
        total_amount=Decimal("50.00"),
        status=EDIInvoiceStatus.PENDING,
        line_items=json.dumps([{
            "line_number": 1, "isbn": "978-0-00-999999-9",
            "title": "Batch Book A", "quantity": 1,
            "unit_price": "50.00", "line_total": "50.00",
        }]),
    )
    inv2 = EDIInvoice(
        purchase_order_id=po2.id,
        vendor_id=vendor_alpha.id,
        invoice_number="INV-BATCH-002",
        invoice_date=datetime.now(tz=timezone.utc),
        total_amount=Decimal("70.00"),
        status=EDIInvoiceStatus.PENDING,
        line_items=json.dumps([{
            "line_number": 1, "isbn": "978-0-01-000000-0",
            "title": "Batch Book B", "quantity": 2,
            "unit_price": "35.00", "line_total": "70.00",
        }]),
    )
    test_db.add_all([inv1, inv2])
    await test_db.commit()
    await test_db.refresh(inv1)
    await test_db.refresh(inv2)

    reconciler = EDIReconciliation(test_db)
    results = await reconciler.batch_reconcile(invoice_ids=[inv1.id, inv2.id])

    assert results["total_processed"] == 2
    assert results["matched"] == 2
    assert results["disputed"] == 0
    assert results["errors"] == 0


@pytest.mark.asyncio
async def test_auto_approve_within_tolerance(test_db, staff_user, fund_general, vendor_alpha, edi_profile):
    """Auto-approve invoice within vendor's configured tolerance."""
    items_data = [("Auto Book", "Author", "978-0-01-111111-1", 4, Decimal("25.00"))]
    po, _ = await _create_po_with_items(
        test_db, staff_user, fund_general, vendor_alpha, "PO-VER-AUTO", items_data,
        status=PurchaseOrderStatus.RECEIVED,
    )

    # Invoice slightly higher but within 5% tolerance: $102 vs $100 = 2%
    invoice = EDIInvoice(
        purchase_order_id=po.id,
        vendor_id=vendor_alpha.id,
        invoice_number="INV-AUTO-001",
        invoice_date=datetime.now(tz=timezone.utc),
        total_amount=Decimal("102.00"),
        po_total=Decimal("100.00"),
        variance_amount=Decimal("2.00"),
        status=EDIInvoiceStatus.MATCHED,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    reconciler = EDIReconciliation(test_db)
    results = await reconciler.auto_approve_invoices(vendor_id=vendor_alpha.id)

    assert results["processed"] >= 1
    assert results["approved"] >= 1

    await test_db.refresh(invoice)
    assert invoice.status == EDIInvoiceStatus.APPROVED


@pytest.mark.asyncio
async def test_auto_approve_exceeds_tolerance_skipped(test_db, staff_user, fund_general, vendor_alpha, edi_profile):
    """Invoice exceeding tolerance is NOT auto-approved."""
    items_data = [("Skip Book", "Author", "978-0-01-222222-2", 2, Decimal("50.00"))]
    po, _ = await _create_po_with_items(
        test_db, staff_user, fund_general, vendor_alpha, "PO-VER-SKIP", items_data,
        status=PurchaseOrderStatus.RECEIVED,
    )

    # Invoice 10% higher: $110 vs $100 — exceeds 5% tolerance
    invoice = EDIInvoice(
        purchase_order_id=po.id,
        vendor_id=vendor_alpha.id,
        invoice_number="INV-SKIP-001",
        invoice_date=datetime.now(tz=timezone.utc),
        total_amount=Decimal("110.00"),
        po_total=Decimal("100.00"),
        variance_amount=Decimal("10.00"),
        status=EDIInvoiceStatus.MATCHED,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    reconciler = EDIReconciliation(test_db)
    results = await reconciler.auto_approve_invoices(vendor_id=vendor_alpha.id)

    assert results["skipped"] >= 1

    await test_db.refresh(invoice)
    assert invoice.status == EDIInvoiceStatus.MATCHED  # Still matched, not approved


@pytest.mark.asyncio
async def test_invoice_not_found_returns_error(test_db):
    """Reconciling a non-existent invoice returns error status."""
    reconciler = EDIReconciliation(test_db)
    result = await reconciler.reconcile_invoice(99999)

    assert result.status == "error"
    assert any("not found" in str(d.get("error", "")).lower() for d in result.discrepancies)


@pytest.mark.asyncio
async def test_invoice_no_po_linked_unmatched(test_db, vendor_alpha):
    """Invoice with no linked PO and no matching PO is unmatched."""
    invoice = EDIInvoice(
        vendor_id=vendor_alpha.id,
        invoice_number="INV-ORPHAN-001",
        invoice_date=datetime.now(tz=timezone.utc),
        total_amount=Decimal("999.99"),
        status=EDIInvoiceStatus.PENDING,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    reconciler = EDIReconciliation(test_db)
    result = await reconciler.reconcile_invoice(invoice.id)

    assert result.status == "unmatched"
    assert any("no matching" in str(d.get("message", "")).lower() or "no_po" in d.get("type", "") for d in result.discrepancies)


# ============================================================================
# FINANCIAL ACCURACY VERIFICATION
# ============================================================================


@pytest.mark.asyncio
async def test_penny_accuracy_awkward_decimals(test_db, staff_user, fund_general, vendor_alpha):
    """Verify exact-penny accuracy with awkward decimal prices through full lifecycle."""
    items_data = [
        ("Book Alpha", "A", None, 3, Decimal("19.99")),   # 59.97
        ("Book Beta", "B", None, 7, Decimal("12.49")),    # 87.43
        ("Book Gamma", "C", None, 1, Decimal("33.33")),   # 33.33
        ("Book Delta", "D", None, 2, Decimal("7.01")),    # 14.02
    ]
    po, _ = await _create_po_with_items(
        test_db, staff_user, fund_general, vendor_alpha, "PO-VER-PENNY", items_data,
    )

    expected = Decimal("194.75")
    assert po.total_amount == expected

    # Submit → encumber
    fund_general.encumbered_amount = po.total_amount
    po.status = PurchaseOrderStatus.SUBMITTED
    await test_db.commit()
    await test_db.refresh(fund_general)

    assert fund_general.encumbered_amount == expected
    assert fund_general.available_amount == Decimal("10000.00") - expected

    # Receive → move to spent
    fund_general.encumbered_amount -= po.total_amount
    fund_general.spent_amount += po.total_amount
    po.status = PurchaseOrderStatus.RECEIVED
    await test_db.commit()
    await test_db.refresh(fund_general)

    assert fund_general.encumbered_amount == Decimal("0.00")
    assert fund_general.spent_amount == expected
    # Accounting identity
    assert fund_general.allocated_amount == (
        fund_general.encumbered_amount + fund_general.spent_amount + fund_general.available_amount
    )


@pytest.mark.asyncio
async def test_multi_fund_isolation(test_db, staff_user, fund_general, fund_ya, vendor_alpha):
    """Operations on one fund do not affect another fund."""
    items1 = [("Gen Book", "A", None, 2, Decimal("50.00"))]
    po1, _ = await _create_po_with_items(
        test_db, staff_user, fund_general, vendor_alpha, "PO-VER-ISO-1", items1,
    )
    fund_general.encumbered_amount += po1.total_amount
    po1.status = PurchaseOrderStatus.SUBMITTED
    await test_db.commit()

    items2 = [("YA Book", "B", None, 3, Decimal("20.00"))]
    po2, _ = await _create_po_with_items(
        test_db, staff_user, fund_ya, vendor_alpha, "PO-VER-ISO-2", items2,
    )
    fund_ya.encumbered_amount += po2.total_amount
    po2.status = PurchaseOrderStatus.SUBMITTED
    await test_db.commit()

    await test_db.refresh(fund_general)
    await test_db.refresh(fund_ya)

    assert fund_general.encumbered_amount == Decimal("100.00")
    assert fund_ya.encumbered_amount == Decimal("60.00")

    # Receive PO1 only
    fund_general.encumbered_amount -= po1.total_amount
    fund_general.spent_amount += po1.total_amount
    await test_db.commit()
    await test_db.refresh(fund_general)
    await test_db.refresh(fund_ya)

    assert fund_general.spent_amount == Decimal("100.00")
    assert fund_general.encumbered_amount == Decimal("0.00")
    # YA fund untouched
    assert fund_ya.encumbered_amount == Decimal("60.00")
    assert fund_ya.spent_amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_selection_list_item_creation(test_db, staff_user):
    """Create a selection list item with priority and source."""
    item = SelectionListItem(
        title="Recommended Title",
        author="Popular Author",
        isbn="978-0-01-333333-3",
        estimated_price=Decimal("29.99"),
        priority=SelectionPriority.HIGH,
        source=SelectionSource.MANUAL,
        requested_by_id=staff_user.id,
        notes="Highly requested by patrons",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    assert item.title == "Recommended Title"
    assert item.priority == SelectionPriority.HIGH
    assert item.source == SelectionSource.MANUAL
    assert item.estimated_price == Decimal("29.99")
    assert item.requested_by_id == staff_user.id


# ============================================================================
# END-TO-END: COMPLETE ACQUISITION LIFECYCLE WITH EDI
# ============================================================================


@pytest.mark.asyncio
async def test_complete_acquisition_lifecycle_with_edi(
    test_db, staff_user, admin_user, fund_general, vendor_alpha, edi_profile, catalog_item_rust,
):
    """Full lifecycle: create PO → submit → EDI order → order response →
    shipment notice → receive → invoice reconciliation → approve → verify finances."""

    # 1. Create PO with items
    items_data = [
        (catalog_item_rust.title, catalog_item_rust.author, catalog_item_rust.isbn, 4, Decimal("45.00")),
        ("Database Internals", "Alex Petrov", "978-1-4920-4034-7", 2, Decimal("55.00")),
    ]
    po, po_items = await _create_po_with_items(
        test_db, staff_user, fund_general, vendor_alpha, "PO-VER-E2E", items_data,
    )
    expected_total = Decimal("4") * Decimal("45.00") + Decimal("2") * Decimal("55.00")
    assert po.total_amount == Decimal("290.00")
    assert po.total_amount == expected_total

    # 2. Submit for approval → approve → submit to vendor
    po.status = PurchaseOrderStatus.PENDING_APPROVAL
    await test_db.commit()

    po.status = PurchaseOrderStatus.APPROVED
    po.approved_by_id = admin_user.id
    po.approved_at = datetime.now(tz=timezone.utc)
    await test_db.commit()

    fund_general.encumbered_amount += po.total_amount
    po.status = PurchaseOrderStatus.SUBMITTED
    await test_db.commit()
    await test_db.refresh(fund_general)
    assert fund_general.encumbered_amount == Decimal("290.00")
    assert fund_general.available_amount == Decimal("9710.00")

    # 3. EDI outbound ORDERS transaction
    edi_txn = EDITransaction(
        vendor_edi_profile_id=edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.ORDERS,
        direction="outbound",
        interchange_control_number="ICN-E2E-001",
        status=EDITransactionStatus.SENT,
        sent_at=datetime.now(tz=timezone.utc),
    )
    test_db.add(edi_txn)
    await test_db.commit()

    # 4. Vendor sends ORDRSP (all accepted)
    ordrsp_txn = EDITransaction(
        vendor_edi_profile_id=edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.ORDRSP,
        direction="inbound",
        interchange_control_number="ICN-E2E-RESP",
        status=EDITransactionStatus.PROCESSED,
        received_at=datetime.now(tz=timezone.utc),
    )
    test_db.add(ordrsp_txn)
    await test_db.commit()
    await test_db.refresh(ordrsp_txn)

    ordrsp = EDIOrderResponse(
        edi_transaction_id=ordrsp_txn.id,
        purchase_order_id=po.id,
        vendor_id=vendor_alpha.id,
        vendor_order_number="MLS-E2E-001",
        response_code="29",  # Accepted
        items_accepted=6,
        items_rejected=0,
        expected_ship_date=datetime.now(tz=timezone.utc) + timedelta(days=3),
        is_processed=True,
    )
    test_db.add(ordrsp)
    await test_db.commit()

    # 5. Shipment notice (DESADV) - partial: 2 of 4 first item
    desadv_txn = EDITransaction(
        vendor_edi_profile_id=edi_profile.id,
        purchase_order_id=po.id,
        message_type=EDIMessageType.DESADV,
        direction="inbound",
        interchange_control_number="ICN-E2E-SHIP",
        status=EDITransactionStatus.PROCESSED,
        received_at=datetime.now(tz=timezone.utc),
    )
    test_db.add(desadv_txn)
    await test_db.commit()

    notice = EDIShipmentNotice(
        edi_transaction_id=desadv_txn.id,
        purchase_order_id=po.id,
        vendor_id=vendor_alpha.id,
        shipment_number="SHIP-E2E-001",
        ship_date=datetime.now(tz=timezone.utc),
        carrier_name="UPS",
        tracking_number="1Z999AA10123456784",
        total_items_shipped=2,
        is_processed=True,
    )
    test_db.add(notice)
    await test_db.commit()

    # 6. Partial receive: 2 of item1
    recv_value = Decimal("2") * Decimal("45.00")  # 90
    po_items[0].received_quantity = 2
    fund_general.encumbered_amount -= recv_value
    fund_general.spent_amount += recv_value
    po.status = PurchaseOrderStatus.PARTIALLY_RECEIVED
    await test_db.commit()
    await test_db.refresh(fund_general)

    assert fund_general.encumbered_amount == Decimal("200.00")
    assert fund_general.spent_amount == Decimal("90.00")

    # 7. Full receive: remaining items
    remaining_value = (
        Decimal("2") * Decimal("45.00") + Decimal("2") * Decimal("55.00")
    )  # 90 + 110 = 200
    po_items[0].received_quantity = 4
    po_items[1].received_quantity = 2
    fund_general.encumbered_amount -= remaining_value
    fund_general.spent_amount += remaining_value
    po.status = PurchaseOrderStatus.RECEIVED
    po.actual_delivery = date(2026, 3, 10)
    await test_db.commit()
    await test_db.refresh(fund_general)

    assert fund_general.encumbered_amount == Decimal("0.00")
    assert fund_general.spent_amount == Decimal("290.00")
    assert po_items[0].is_fully_received
    assert po_items[1].is_fully_received

    # 8. Invoice reconciliation
    invoice_line_items = json.dumps([
        {
            "line_number": 1,
            "isbn": catalog_item_rust.isbn,
            "title": catalog_item_rust.title,
            "quantity": 4,
            "unit_price": "45.00",
            "line_total": "180.00",
        },
        {
            "line_number": 2,
            "isbn": "978-1-4920-4034-7",
            "title": "Database Internals",
            "quantity": 2,
            "unit_price": "55.00",
            "line_total": "110.00",
        },
    ])

    invoice = EDIInvoice(
        purchase_order_id=po.id,
        vendor_id=vendor_alpha.id,
        invoice_number="INV-E2E-001",
        invoice_date=datetime.now(tz=timezone.utc),
        due_date=datetime.now(tz=timezone.utc) + timedelta(days=30),
        subtotal=Decimal("290.00"),
        total_amount=Decimal("290.00"),
        status=EDIInvoiceStatus.PENDING,
        line_items=invoice_line_items,
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    reconciler = EDIReconciliation(test_db)
    rec_result = await reconciler.reconcile_invoice(invoice.id)

    assert rec_result.status == "matched"
    assert rec_result.matched_items == 2
    assert rec_result.variance_amount == Decimal("0.00")

    # 9. Approve invoice
    success, msg = await reconciler.approve_invoice(invoice.id, admin_user)
    assert success is True

    await test_db.refresh(invoice)
    assert invoice.status == EDIInvoiceStatus.APPROVED

    # 10. Final financial verification
    await test_db.refresh(fund_general)
    assert fund_general.spent_amount == Decimal("290.00")
    assert fund_general.encumbered_amount == Decimal("0.00")
    assert fund_general.available_amount == Decimal("9710.00")
    # Accounting identity
    assert fund_general.allocated_amount == (
        fund_general.encumbered_amount + fund_general.spent_amount + fund_general.available_amount
    )
