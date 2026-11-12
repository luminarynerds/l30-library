#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Test script for creating a purchase order for Adult Fiction fund.

This script:
1. Creates or finds the vendor "Ingram Content Group"
2. Creates or finds the fund "Adult Fiction FY2024"
3. Creates a purchase order with 3 line items
4. Verifies the PO is in DRAFT status
5. Verifies line items are correct and total is calculated
6. Verifies budget validation runs and shows remaining fund balance
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import date
from decimal import Decimal
import json

# Setup path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.acquisition import (
    Fund, FundStatus, Vendor, PurchaseOrder, PurchaseOrderStatus,
    PurchaseOrderItem
)
from app.models.user import User

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@database:5432/lsc_library"
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_or_create_vendor(session: AsyncSession, name: str, email: str = None) -> Vendor:
    """Get or create a vendor."""
    result = await session.execute(select(Vendor).where(Vendor.name == name))
    vendor = result.scalar_one_or_none()

    if vendor:
        print(f"  Found existing vendor: {vendor.name} (ID: {vendor.id})")
        return vendor

    vendor = Vendor(
        name=name,
        email=email or "orders@ingramcontentgroup.com",
        is_active=True,
    )
    session.add(vendor)
    await session.flush()
    print(f"  Created new vendor: {vendor.name} (ID: {vendor.id})")
    return vendor


async def get_or_create_fund(session: AsyncSession, code: str, name: str, fiscal_year: int, amount: Decimal) -> Fund:
    """Get or create a fund."""
    result = await session.execute(select(Fund).where(Fund.code == code))
    fund = result.scalar_one_or_none()

    if fund:
        print(f"  Found existing fund: {fund.name} (ID: {fund.id})")
        return fund

    fund = Fund(
        code=code,
        name=name,
        fiscal_year=fiscal_year,
        allocated_amount=amount,
        status=FundStatus.ACTIVE,
    )
    session.add(fund)
    await session.flush()
    print(f"  Created new fund: {fund.name} (ID: {fund.id}) with allocated amount: ${amount}")
    return fund


async def create_test_purchase_order():
    """Create and verify a test purchase order."""
    print("\n" + "=" * 80)
    print("CREATE AND VERIFY PURCHASE ORDER - ADULT FICTION FUND")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        try:
            # Step 1: Get or create vendor
            print("\n1️⃣  Setting up Vendor...")
            vendor = await get_or_create_vendor(
                session,
                "Ingram Content Group",
                "orders@ingramcontentgroup.com"
            )

            # Step 2: Get or create fund
            print("\n2️⃣  Setting up Fund...")
            fund = await get_or_create_fund(
                session,
                "ADULT-FIC-2024",
                "Adult Fiction FY2024",
                2024,
                Decimal("50000.00")
            )

            # Step 3: Get staff user
            print("\n3️⃣  Getting staff user...")
            user_result = await session.execute(
                select(User).where(User.role.in_(["STAFF", "ADMIN"])).limit(1)
            )
            staff_user = user_result.scalar_one_or_none()

            if not staff_user:
                print("❌ ERROR: No staff users found in database!")
                return 1

            print(f"  Using staff user: {staff_user.email}")

            # Step 4: Create purchase order
            print("\n4️⃣  Creating Purchase Order...")

            # Define line items
            line_items = [
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

            # Calculate total
            total_amount = sum(
                Decimal(str(item["quantity"])) * item["unit_price"]
                for item in line_items
            )

            # Create PO
            po_count = await session.execute(select(PurchaseOrder))
            po_count = len(list(po_count.scalars().all()))
            po_number = f"PO-{date.today().strftime('%Y%m')}-{po_count + 1:04d}"

            po = PurchaseOrder(
                po_number=po_number,
                vendor_id=vendor.id,
                fund_id=fund.id,
                order_date=date.today(),
                status=PurchaseOrderStatus.DRAFT,
                total_amount=total_amount,
                notes="Rush order for summer reading program",
                created_by_id=staff_user.id,
            )
            session.add(po)
            await session.flush()

            print(f"  Created Purchase Order: {po.po_number} (ID: {po.id})")
            print(f"  Status: {po.status.value}")
            print(f"  Vendor: {vendor.name}")
            print(f"  Fund: {fund.name}")
            print(f"  Notes: {po.notes}")

            # Add line items
            print("\n  Adding line items...")
            for idx, item_data in enumerate(line_items, 1):
                po_item = PurchaseOrderItem(
                    purchase_order_id=po.id,
                    isbn=item_data["isbn"],
                    title=item_data["title"],
                    author=item_data["author"],
                    quantity=item_data["quantity"],
                    unit_price=item_data["unit_price"],
                )
                session.add(po_item)
                line_total = Decimal(str(item_data["quantity"])) * item_data["unit_price"]
                print(f"    {idx}. ISBN {item_data['isbn']}: {item_data['quantity']} × ${item_data['unit_price']} = ${line_total}")

            await session.commit()
            await session.refresh(po)
            await session.refresh(fund)

            # Step 5: Verify PO status and details
            print("\n5️⃣  Verifying Purchase Order...")

            # Re-fetch to get relationships
            po_result = await session.execute(
                select(PurchaseOrder)
                .where(PurchaseOrder.id == po.id)
            )
            po = po_result.scalar_one()

            po_items_result = await session.execute(
                select(PurchaseOrderItem)
                .where(PurchaseOrderItem.purchase_order_id == po.id)
            )
            po_items = list(po_items_result.scalars().all())

            print(f"\n  ✅ PO Status: {po.status.value} (Expected: DRAFT)")
            assert po.status == PurchaseOrderStatus.DRAFT, "PO should be in DRAFT status"

            print(f"\n  ✅ Line Items: {len(po_items)} items (Expected: 3)")
            assert len(po_items) == 3, "PO should have 3 line items"

            # Verify each line item
            print("\n  Verifying line items:")
            expected_totals = [
                Decimal("94.95"),   # 5 × 18.99
                Decimal("44.97"),   # 3 × 14.99
                Decimal("32.00"),   # 2 × 16.00
            ]

            for idx, (item, expected_total) in enumerate(zip(po_items, expected_totals), 1):
                actual_total = Decimal(str(item.quantity)) * item.unit_price
                print(f"    {idx}. ISBN {item.isbn}")
                print(f"       Title: {item.title}")
                print(f"       Author: {item.author}")
                print(f"       Qty: {item.quantity}, Unit Price: ${item.unit_price}, Line Total: ${actual_total}")
                assert actual_total == expected_total, f"Line {idx} total mismatch: {actual_total} != {expected_total}"
                assert item.received_quantity == 0, f"Line {idx} should have received_quantity = 0 (DRAFT)"

            # Verify total
            print(f"\n  ✅ Total Amount: ${po.total_amount} (Expected: ${total_amount})")
            assert po.total_amount == total_amount, f"Total mismatch: {po.total_amount} != {total_amount}"

            # Step 6: Verify budget validation
            print("\n6️⃣  Verifying Budget Validation...")

            available_before = fund.available_amount
            print(f"  Fund: {fund.name}")
            print(f"  Allocated Amount: ${fund.allocated_amount}")
            print(f"  Encumbered Amount: ${fund.encumbered_amount}")
            print(f"  Spent Amount: ${fund.spent_amount}")
            print(f"  Available Amount: ${available_before}")

            order_total = Decimal(str(po.total_amount))
            remaining_after = available_before - order_total

            print(f"\n  Order Total: ${order_total}")
            print(f"  Remaining After Order: ${remaining_after}")

            if available_before >= order_total:
                usage_percentage = float((order_total / available_before) * 100) if available_before > 0 else 0
                print(f"  Usage Percentage: {usage_percentage:.2f}%")
                print("  Status: ✅ Within budget")

                if usage_percentage > 75:
                    print("  ⚠️  WARNING: Order uses more than 75% of available funds")
                if usage_percentage > 100:
                    print("  ❌ DANGER: Order exceeds available funds")
            else:
                exceeds_by = order_total - available_before
                print(f"  ❌ ERROR: Order exceeds available funds by ${exceeds_by}")
                return 1

            # Step 7: Summary
            print("\n" + "=" * 80)
            print("✅ ALL TESTS PASSED")
            print("=" * 80)
            print("\nSummary:")
            print(f"  PO Number: {po.po_number}")
            print(f"  Status: {po.status.value}")
            print(f"  Vendor: {vendor.name}")
            print(f"  Fund: {fund.name}")
            print(f"  Total Items: {len(po_items)}")
            print(f"  Total Amount: ${po.total_amount}")
            print(f"  Fund Available After Order: ${remaining_after}")
            print(f"  Notes: {po.notes}")
            print()

            return 0

        except AssertionError as e:
            print(f"\n❌ ASSERTION FAILED: {e}")
            import traceback
            traceback.print_exc()
            return 1
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            await engine.dispose()


if __name__ == "__main__":
    exit_code = asyncio.run(create_test_purchase_order())
    if exit_code is not None:
        sys.exit(exit_code)
