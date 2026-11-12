#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Acquisitions Seed Script for LSC Library System

Seeds realistic staff operational data for acquisitions workflows:
- Funds with fiscal year budgets and allocation tracking
- Multiple vendors with contact information
- Purchase orders in various states (draft, approved, received, cancelled)
- EDI transactions for automated vendor communication
- EDI invoices and shipment notices for received orders

This data is essential for:
- Budget management and reporting
- Vendor performance tracking
- PO workflow testing
- EDI integration validation
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, date
from decimal import Decimal

# Setup path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.acquisition import (
    Fund, FundStatus, Vendor, PurchaseOrder, PurchaseOrderStatus,
    PurchaseOrderItem, SelectionListItem, SelectionPriority, SelectionSource,
    OrderTemplate
)
from app.models.edi import (
    VendorEDIProfile, EDIStandard, TransportProtocol, EDITransaction,
    EDIMessageType, EDITransactionStatus, EDIInvoice, EDIInvoiceStatus,
    EDIShipmentNotice, EDIOrderResponse
)
from app.models.user import User
from app.models.catalog import CatalogItem

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@database:5432/lsc_library"
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def seed_funds(session: AsyncSession) -> list[Fund]:
    """Seed acquisition funds with budgets."""
    print("  Seeding funds...")

    # Check if funds already exist
    result = await session.execute(select(Fund).limit(1))
    if result.scalar_one_or_none():
        print("    Funds already exist, skipping...")
        return []

    funds_data = [
        {
            "code": "ACQF-2026-GEN",
            "name": "General Acquisition Fund 2026",
            "description": "General budget for book and media acquisitions",
            "fiscal_year": 2026,
            "allocated_amount": Decimal("10000.00"),
            "status": FundStatus.ACTIVE,
        },
        {
            "code": "ACQF-2026-REF",
            "name": "Reference Materials Fund 2026",
            "description": "Reference materials, databases, and encyclopedias",
            "fiscal_year": 2026,
            "allocated_amount": Decimal("5000.00"),
            "status": FundStatus.ACTIVE,
        },
        {
            "code": "ACQF-2026-DIGIT",
            "name": "Digital Resources Fund 2026",
            "description": "eBooks, audiobooks, and digital media",
            "fiscal_year": 2026,
            "allocated_amount": Decimal("3000.00"),
            "status": FundStatus.ACTIVE,
        },
        {
            "code": "ACQF-2026-SPEC",
            "name": "Special Collections Fund 2026",
            "description": "Rare books and special collection acquisitions",
            "fiscal_year": 2026,
            "allocated_amount": Decimal("2000.00"),
            "status": FundStatus.ACTIVE,
        },
    ]

    created_funds = []
    for fund_data in funds_data:
        fund = Fund(**fund_data)
        session.add(fund)
        created_funds.append(fund)

    await session.commit()
    print(f"    Created {len(created_funds)} funds")
    return created_funds


async def seed_vendors(session: AsyncSession) -> list[Vendor]:
    """Seed vendor data with contact information."""
    print("  Seeding vendors...")

    # Check if vendors already exist
    result = await session.execute(select(Vendor).limit(1))
    if result.scalar_one_or_none():
        print("    Vendors already exist, skipping...")
        return []

    vendors_data = [
        {
            "name": "Quality Books Supply",
            "contact_name": "John Smith",
            "email": "orders@qualitybooks.com",
            "phone": "+1-555-0100",
            "address": "123 Publisher Way, Book City, BC 12345",
            "account_number": "ACCT-98765",
            "is_active": True,
        },
        {
            "name": "Ingram Book Company",
            "contact_name": "Michael Chen",
            "email": "libraries@ingrambook.com",
            "phone": "+1-555-0300",
            "address": "789 Warehouse Lane, Logistics City, QC 54321",
            "account_number": "INGRAM-LSC-2026",
            "is_active": True,
        },
        {
            "name": "Brodart Library Services",
            "contact_name": "Patricia Williams",
            "email": "sales@brodart.com",
            "phone": "+1-555-0400",
            "address": "321 Service Boulevard, Support City, AB 11111",
            "account_number": "BRODART-1234",
            "is_active": True,
        },
        {
            "name": "Demco Library Supplies",
            "contact_name": "Robert Martinez",
            "email": "ordering@demco.com",
            "phone": "+1-555-0500",
            "address": "654 Supply Street, Equipment Town, MB 22222",
            "account_number": "DEMCO-LSC",
            "is_active": True,
        },
    ]

    created_vendors = []
    for vendor_data in vendors_data:
        vendor = Vendor(**vendor_data)
        session.add(vendor)
        created_vendors.append(vendor)

    await session.commit()
    print(f"    Created {len(created_vendors)} vendors")
    return created_vendors


async def seed_vendor_edi_profiles(session: AsyncSession, vendors: list[Vendor]) -> None:
    """Seed EDI profiles for vendors supporting automated ordering."""
    print("  Seeding vendor EDI profiles...")

    # Check if profiles already exist
    result = await session.execute(select(VendorEDIProfile).limit(1))
    if result.scalar_one_or_none():
        print("    EDI profiles already exist, skipping...")
        return

    profiles_data = [
        {
            "vendor_id": vendors[0].id,
            "is_enabled": True,
            "edi_standard": EDIStandard.EDIFACT,
            "sender_id": "LSC-LIBRARY",
            "receiver_id": "QUALITY-BOOKS",
            "transport_protocol": TransportProtocol.SFTP,
            "transport_host": "edi.qualitybooks.com",
            "transport_port": 22,
            "supports_orders": True,
            "supports_ordrsp": True,
            "supports_desadv": True,
            "supports_invoic": True,
            "auto_process_responses": True,
            "is_test_mode": False,
        },
        {
            "vendor_id": vendors[1].id,
            "is_enabled": True,
            "edi_standard": EDIStandard.X12,
            "sender_id": "LSC",
            "receiver_id": "INGRAM",
            "transport_protocol": TransportProtocol.AS2,
            "supports_orders": True,
            "supports_ordrsp": True,
            "supports_desadv": True,
            "supports_invoic": True,
            "auto_process_responses": True,
            "is_test_mode": False,
        },
        {
            "vendor_id": vendors[2].id,
            "is_enabled": True,
            "edi_standard": EDIStandard.EDIFACT,
            "sender_id": "LSCLIB",
            "receiver_id": "INGRAM",
            "transport_protocol": TransportProtocol.SFTP,
            "transport_host": "edi.ingrambook.com",
            "transport_port": 22,
            "supports_orders": True,
            "supports_ordrsp": True,
            "supports_desadv": True,
            "supports_invoic": True,
            "auto_process_responses": True,
            "is_test_mode": False,
        },
    ]

    created = 0
    for profile_data in profiles_data:
        profile = VendorEDIProfile(**profile_data)
        session.add(profile)
        created += 1

    await session.commit()
    print(f"    Created {created} EDI profiles")


async def seed_purchase_orders(session: AsyncSession, funds: list[Fund], vendors: list[Vendor], staff_user: User) -> list[PurchaseOrder]:
    """Seed purchase orders in various states."""
    print("  Seeding purchase orders...")

    # Check if POs already exist
    result = await session.execute(select(PurchaseOrder).limit(1))
    if result.scalar_one_or_none():
        print("    Purchase orders already exist, skipping...")
        return []

    _ = datetime.now().__class__(datetime.now().year, datetime.now().month, datetime.now().day)
    created_pos = []

    # Get some catalog items to link to PO items
    items_result = await session.execute(select(CatalogItem).limit(10))
    catalog_items = items_result.scalars().all()

    # PO 1: Active/Approved - waiting for delivery
    po1 = PurchaseOrder(
        po_number="PO-2026-001",
        vendor_id=vendors[0].id,
        fund_id=funds[0].id,
        order_date=date.today() - timedelta(days=15),
        expected_delivery=date.today() + timedelta(days=10),
        status=PurchaseOrderStatus.APPROVED,
        total_amount=Decimal("1250.00"),
        created_by_id=staff_user.id,
        approved_by_id=staff_user.id,
        approved_at=datetime.now() - timedelta(days=14),
        notes="Rush order - needed for upcoming reading program",
    )
    session.add(po1)
    created_pos.append(po1)

    # PO 2: Partially Received
    po2 = PurchaseOrder(
        po_number="PO-2026-002",
        vendor_id=vendors[1].id,
        fund_id=funds[1].id,
        order_date=date.today() - timedelta(days=30),
        expected_delivery=date.today() - timedelta(days=5),
        actual_delivery=date.today() - timedelta(days=5),
        status=PurchaseOrderStatus.PARTIALLY_RECEIVED,
        total_amount=Decimal("2850.75"),
        created_by_id=staff_user.id,
        approved_by_id=staff_user.id,
        approved_at=datetime.now() - timedelta(days=29),
        notes="Reference materials - 15 of 18 items received",
    )
    session.add(po2)
    created_pos.append(po2)

    # PO 3: Fully Received
    po3 = PurchaseOrder(
        po_number="PO-2026-003",
        vendor_id=vendors[2].id,
        fund_id=funds[2].id,
        order_date=date.today() - timedelta(days=45),
        expected_delivery=date.today() - timedelta(days=20),
        actual_delivery=date.today() - timedelta(days=20),
        status=PurchaseOrderStatus.RECEIVED,
        total_amount=Decimal("1950.00"),
        created_by_id=staff_user.id,
        approved_by_id=staff_user.id,
        approved_at=datetime.now() - timedelta(days=44),
        notes="Digital resources subscription invoiced and paid",
    )
    session.add(po3)
    created_pos.append(po3)

    # PO 4: Draft - still being prepared
    po4 = PurchaseOrder(
        po_number="PO-2026-004",
        vendor_id=vendors[3].id,
        fund_id=funds[3].id,
        order_date=date.today() - timedelta(days=3),
        status=PurchaseOrderStatus.DRAFT,
        total_amount=Decimal("0.00"),
        created_by_id=staff_user.id,
        notes="Special collection items - pending approval",
    )
    session.add(po4)
    created_pos.append(po4)

    # PO 5: Pending Approval
    po5 = PurchaseOrder(
        po_number="PO-2026-005",
        vendor_id=vendors[4].id,
        fund_id=funds[0].id,
        order_date=date.today() - timedelta(days=5),
        status=PurchaseOrderStatus.PENDING_APPROVAL,
        total_amount=Decimal("3200.00"),
        created_by_id=staff_user.id,
        notes="Cataloging supplies and equipment",
    )
    session.add(po5)
    created_pos.append(po5)

    await session.flush()  # Flush to get IDs

    # Add items to purchase orders
    print("  Adding items to purchase orders...")

    # Items for PO1
    for i, item in enumerate(catalog_items[:3] if len(catalog_items) >= 3 else catalog_items):
        po_item = PurchaseOrderItem(
            purchase_order_id=po1.id,
            title=item.title,
            author=item.author,
            isbn=item.isbn,
            quantity=2,
            unit_price=Decimal("18.50"),
            catalog_item_id=item.id,
        )
        session.add(po_item)

    # Items for PO2
    for i, item in enumerate(catalog_items[3:6] if len(catalog_items) >= 6 else catalog_items[3:]):
        po_item = PurchaseOrderItem(
            purchase_order_id=po2.id,
            title=item.title,
            author=item.author,
            isbn=item.isbn,
            quantity=1,
            unit_price=Decimal("45.00"),
            received_quantity=i % 3 == 0 and 1 or 0,  # Some received, some not
            catalog_item_id=item.id,
        )
        session.add(po_item)

    # Items for PO3
    for i, item in enumerate(catalog_items[6:] if len(catalog_items) > 6 else []):
        po_item = PurchaseOrderItem(
            purchase_order_id=po3.id,
            title=item.title,
            author=item.author,
            isbn=item.isbn,
            quantity=3,
            unit_price=Decimal("25.00"),
            received_quantity=3,
            catalog_item_id=item.id,
        )
        session.add(po_item)

    # Items for PO4
    if len(catalog_items) > 0:
        po_item = PurchaseOrderItem(
            purchase_order_id=po4.id,
            title="Rare Book Collection Series - Vol 1-5",
            author="Various Authors",
            isbn="RARE-SERIES-001",
            quantity=5,
            unit_price=Decimal("150.00"),
        )
        session.add(po_item)

    # Items for PO5
    po_item = PurchaseOrderItem(
        purchase_order_id=po5.id,
        title="Book Trucks and Carts Equipment",
        author="Equipment Supply",
        isbn="EQUIP-001",
        quantity=2,
        unit_price=Decimal("800.00"),
    )
    session.add(po_item)
    po_item2 = PurchaseOrderItem(
        purchase_order_id=po5.id,
        title="RFID Tags (Box of 1000)",
        author="Tech Supplies",
        isbn="TECH-002",
        quantity=2,
        unit_price=Decimal("400.00"),
    )
    session.add(po_item2)

    await session.commit()
    print(f"    Created {len(created_pos)} purchase orders with items")
    return created_pos


async def seed_edi_transactions(session: AsyncSession, pos: list[PurchaseOrder]) -> None:
    """Seed EDI transactions for PO communication."""
    print("  Seeding EDI transactions...")

    # Check if transactions already exist
    result = await session.execute(select(EDITransaction).limit(1))
    if result.scalar_one_or_none():
        print("    EDI transactions already exist, skipping...")
        return

    created = 0

    # Get EDI profiles
    profiles_result = await session.execute(select(VendorEDIProfile))
    profiles = profiles_result.scalars().all()

    if not profiles:
        print("    No EDI profiles found, skipping transaction creation...")
        return

    # Transaction 1: Outbound ORDERS message for PO1
    if len(pos) > 0 and len(profiles) > 0:
        trans1 = EDITransaction(
            vendor_edi_profile_id=profiles[0].id,
            purchase_order_id=pos[0].id,
            message_type=EDIMessageType.ORDERS,
            direction="outbound",
            interchange_control_number="000000001",
            status=EDITransactionStatus.SENT,
            sent_at=datetime.now() - timedelta(days=14),
        )
        session.add(trans1)
        created += 1

    # Transaction 2: Inbound ORDRSP for PO1
    if len(pos) > 0 and len(profiles) > 0:
        trans2 = EDITransaction(
            vendor_edi_profile_id=profiles[0].id,
            purchase_order_id=pos[0].id,
            message_type=EDIMessageType.ORDRSP,
            direction="inbound",
            interchange_control_number="000000002",
            status=EDITransactionStatus.PROCESSED,
            received_at=datetime.now() - timedelta(days=12),
            processed_at=datetime.now() - timedelta(days=12),
        )
        session.add(trans2)
        created += 1

    # Transaction 3: Inbound DESADV for PO2
    if len(pos) > 1 and len(profiles) > 1:
        trans3 = EDITransaction(
            vendor_edi_profile_id=profiles[1].id,
            purchase_order_id=pos[1].id,
            message_type=EDIMessageType.DESADV,
            direction="inbound",
            interchange_control_number="000000003",
            status=EDITransactionStatus.PROCESSED,
            received_at=datetime.now() - timedelta(days=5),
            processed_at=datetime.now() - timedelta(days=5),
        )
        session.add(trans3)
        created += 1

    # Transaction 4: Inbound INVOIC for PO2
    if len(pos) > 1 and len(profiles) > 1:
        trans4 = EDITransaction(
            vendor_edi_profile_id=profiles[1].id,
            purchase_order_id=pos[1].id,
            message_type=EDIMessageType.INVOIC,
            direction="inbound",
            interchange_control_number="000000004",
            status=EDITransactionStatus.PROCESSED,
            received_at=datetime.now() - timedelta(days=4),
            processed_at=datetime.now() - timedelta(days=4),
        )
        session.add(trans4)
        created += 1

    # Transaction 5: DESADV and INVOIC for PO3
    if len(pos) > 2 and len(profiles) > 2:
        trans5 = EDITransaction(
            vendor_edi_profile_id=profiles[2].id,
            purchase_order_id=pos[2].id,
            message_type=EDIMessageType.DESADV,
            direction="inbound",
            interchange_control_number="000000005",
            status=EDITransactionStatus.PROCESSED,
            received_at=datetime.now() - timedelta(days=20),
            processed_at=datetime.now() - timedelta(days=20),
        )
        session.add(trans5)
        created += 1

    await session.commit()
    print(f"    Created {created} EDI transactions")


async def seed_edi_invoices(session: AsyncSession, pos: list[PurchaseOrder]) -> None:
    """Seed EDI invoices from vendors."""
    print("  Seeding EDI invoices...")

    # Check if invoices already exist
    result = await session.execute(select(EDIInvoice).limit(1))
    if result.scalar_one_or_none():
        print("    EDI invoices already exist, skipping...")
        return

    created = 0

    # Invoice for PO2 (partial)
    if len(pos) > 1:
        inv1 = EDIInvoice(
            purchase_order_id=pos[1].id,
            vendor_id=pos[1].vendor_id,
            invoice_number="INV-QBS-2026-001234",
            invoice_date=datetime.now() - timedelta(days=4),
            due_date=datetime.now() + timedelta(days=26),
            subtotal=Decimal("1500.00"),
            tax_amount=Decimal("150.00"),
            shipping_amount=Decimal("50.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("1700.00"),
            status=EDIInvoiceStatus.MATCHED,
            po_total=Decimal("2850.75"),
            variance_amount=Decimal("0.00"),
            matched_line_items=15,
            total_line_items=18,
            notes="Partial shipment invoice - 15 of 18 items received",
        )
        session.add(inv1)
        created += 1

    # Invoice for PO3 (complete)
    if len(pos) > 2:
        inv2 = EDIInvoice(
            purchase_order_id=pos[2].id,
            vendor_id=pos[2].vendor_id,
            invoice_number="INV-INGR-2026-005678",
            invoice_date=datetime.now() - timedelta(days=19),
            due_date=datetime.now() - timedelta(days=5),  # Already due
            subtotal=Decimal("1950.00"),
            tax_amount=Decimal("0.00"),
            shipping_amount=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("1950.00"),
            status=EDIInvoiceStatus.APPROVED,
            po_total=Decimal("1950.00"),
            variance_amount=Decimal("0.00"),
            matched_line_items=10,
            total_line_items=10,
            notes="Complete invoice - fully received and approved for payment",
        )
        session.add(inv2)
        created += 1

    await session.commit()
    print(f"    Created {created} EDI invoices")


async def seed_edi_shipment_notices(session: AsyncSession, pos: list[PurchaseOrder]) -> None:
    """Seed EDI shipment notices."""
    print("  Seeding EDI shipment notices...")

    # Check if shipment notices already exist
    result = await session.execute(select(EDIShipmentNotice).limit(1))
    if result.scalar_one_or_none():
        print("    EDI shipment notices already exist, skipping...")
        return

    created = 0

    # Shipment for PO2
    if len(pos) > 1:
        ship1 = EDIShipmentNotice(
            purchase_order_id=pos[1].id,
            vendor_id=pos[1].vendor_id,
            shipment_number="SHIP-BT-2026-98765",
            ship_date=datetime.now() - timedelta(days=8),
            expected_delivery_date=datetime.now() - timedelta(days=5),
            carrier_name="FedEx",
            carrier_code="FDX",
            tracking_number="794620847361",
            package_count=3,
            total_weight=Decimal("45.5"),
            total_items_shipped=15,
            is_processed=True,
            processed_at=datetime.now() - timedelta(days=5),
        )
        session.add(ship1)
        created += 1

    # Shipment for PO3
    if len(pos) > 2:
        ship2 = EDIShipmentNotice(
            purchase_order_id=pos[2].id,
            vendor_id=pos[2].vendor_id,
            shipment_number="SHIP-INGR-2026-45321",
            ship_date=datetime.now() - timedelta(days=21),
            expected_delivery_date=datetime.now() - timedelta(days=20),
            carrier_name="UPS",
            carrier_code="UPS",
            tracking_number="1Z999AA10123456784",
            package_count=5,
            total_weight=Decimal("125.0"),
            total_items_shipped=30,
            is_processed=True,
            processed_at=datetime.now() - timedelta(days=20),
        )
        session.add(ship2)
        created += 1

    await session.commit()
    print(f"    Created {created} EDI shipment notices")


async def main():
    """Main seeding function."""
    print("\n" + "=" * 70)
    print("LSC ACQUISITIONS DATA SEEDING")
    print("=" * 70)

    async with AsyncSessionLocal() as session:
        try:
            # Get or create a staff user for created_by references
            user_result = await session.execute(
                select(User).where(User.role.in_(["STAFF", "ADMIN"])).limit(1)
            )
            staff_user = user_result.scalar_one_or_none()

            if not staff_user:
                print("⚠️  No staff users found in database!")
                print("   Run seed_test_accounts.py first to create users.")
                return 1

            print(f"\n📋 Using staff user: {staff_user.email}\n")

            # Seed funds (or fetch existing)
            funds = await seed_funds(session)
            if not funds:
                result = await session.execute(select(Fund))
                funds = list(result.scalars().all())

            # Seed vendors (or fetch existing)
            vendors = await seed_vendors(session)
            if not vendors:
                result = await session.execute(select(Vendor))
                vendors = list(result.scalars().all())

            # Seed EDI profiles
            if vendors:
                await seed_vendor_edi_profiles(session, vendors)

            # Seed purchase orders (or fetch existing)
            if funds and vendors:
                pos = await seed_purchase_orders(session, funds, vendors, staff_user)
                if not pos:
                    result = await session.execute(select(PurchaseOrder))
                    pos = list(result.scalars().all())
            else:
                pos = []

            # Seed EDI transactions
            if pos:
                await seed_edi_transactions(session, pos)

            # Seed EDI invoices
            if pos:
                await seed_edi_invoices(session, pos)

            # Seed EDI shipment notices
            if pos:
                await seed_edi_shipment_notices(session, pos)

            print("\n" + "=" * 70)
            print("✅ ACQUISITIONS SEED COMPLETED SUCCESSFULLY")
            print("=" * 70)
            print("\n📊 Summary:")
            print(f"  ✓ Funds created: {len(funds)}")
            print(f"  ✓ Vendors created: {len(vendors)}")
            print(f"  ✓ Purchase Orders created: {len(pos)}")
            print(f"  ✓ EDI profiles configured: {len(vendors)}")
            print("  ✓ EDI transactions recorded")
            print("  ✓ EDI invoices recorded")
            print("  ✓ EDI shipment notices recorded")
            print()

            return 0

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            await engine.dispose()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    if exit_code is not None:
        sys.exit(exit_code)
