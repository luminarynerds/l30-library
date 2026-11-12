#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive Circulation Scenarios Seed Data

Creates test data covering ALL circulation scenarios needed for testing:
- Checkouts at various due dates (today, tomorrow, overdue by 1/7/30+ days)
- Renewed items with various renewal counts
- Items at max renewals
- Holds in queue at different positions
- Holds ready for pickup
- Holds expiring today/expired
- Fines with all statuses (paid, unpaid, waived, partial)
- Claims returned disputes
- Lost item charges
- Damaged item charges

Each scenario includes the specific patron and item involved for reference.
"""

import asyncio
import sys
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole, PatronStatus
from app.models.circulation import Checkout, Hold, CheckoutStatus, HoldStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.catalog import CatalogItem, ItemStatus
from app.models.inventory import ItemCopy, ItemCondition, AcquisitionSource


# Scenario patrons with descriptive names
SCENARIO_PATRONS = [
    # Checkout due date scenarios
    {
        "email": "patron.due-today@l30.org",
        "password": "Patron123!",
        "first_name": "Today",
        "last_name": "Due",
        "scenario": "Item due TODAY",
    },
    {
        "email": "patron.due-tomorrow@l30.org",
        "password": "Patron123!",
        "first_name": "Tomorrow",
        "last_name": "Due",
        "scenario": "Item due TOMORROW",
    },
    {
        "email": "patron.overdue-1day@l30.org",
        "password": "Patron123!",
        "first_name": "Overdue",
        "last_name": "One",
        "scenario": "Overdue by 1 DAY",
    },
    {
        "email": "patron.overdue-7days@l30.org",
        "password": "Patron123!",
        "first_name": "Overdue",
        "last_name": "Week",
        "scenario": "Overdue by 7 DAYS",
    },
    {
        "email": "patron.overdue-30days@l30.org",
        "password": "Patron123!",
        "first_name": "Overdue",
        "last_name": "Month",
        "scenario": "Overdue by 30+ DAYS (long overdue)",
    },
    # Renewal scenarios
    {
        "email": "patron.renewed-once@l30.org",
        "password": "Patron123!",
        "first_name": "Renewed",
        "last_name": "Once",
        "scenario": "Item with 1 RENEWAL used",
    },
    {
        "email": "patron.renewed-twice@l30.org",
        "password": "Patron123!",
        "first_name": "Renewed",
        "last_name": "Twice",
        "scenario": "Item with 2 RENEWALS used",
    },
    {
        "email": "patron.at-max-renewals@l30.org",
        "password": "Patron123!",
        "first_name": "Renewed",
        "last_name": "Max",
        "scenario": "Item at MAX RENEWALS (3/3)",
    },
    # Hold scenarios
    {
        "email": "patron.holds-queue-pos1@l30.org",
        "password": "Patron123!",
        "first_name": "Queue",
        "last_name": "First",
        "scenario": "Hold in queue - POSITION 1",
    },
    {
        "email": "patron.holds-queue-pos2@l30.org",
        "password": "Patron123!",
        "first_name": "Queue",
        "last_name": "Second",
        "scenario": "Hold in queue - POSITION 2",
    },
    {
        "email": "patron.holds-queue-pos3@l30.org",
        "password": "Patron123!",
        "first_name": "Queue",
        "last_name": "Third",
        "scenario": "Hold in queue - POSITION 3+",
    },
    {
        "email": "patron.hold-ready@l30.org",
        "password": "Patron123!",
        "first_name": "Ready",
        "last_name": "Pickup",
        "scenario": "Hold READY FOR PICKUP",
    },
    {
        "email": "patron.hold-expiring-today@l30.org",
        "password": "Patron123!",
        "first_name": "Hold",
        "last_name": "Expiring",
        "scenario": "Hold EXPIRING TODAY",
    },
    # Fine scenarios
    {
        "email": "patron.fine-paid@l30.org",
        "password": "Patron123!",
        "first_name": "Fine",
        "last_name": "Paid",
        "scenario": "PAID FINES",
    },
    {
        "email": "patron.fine-waived@l30.org",
        "password": "Patron123!",
        "first_name": "Fine",
        "last_name": "Waived",
        "scenario": "WAIVED FINES",
    },
    {
        "email": "patron.fine-partial@l30.org",
        "password": "Patron123!",
        "first_name": "Fine",
        "last_name": "Partial",
        "scenario": "PARTIALLY PAID FINES",
    },
    # Dispute scenarios
    {
        "email": "patron.claims-returned@l30.org",
        "password": "Patron123!",
        "first_name": "Claims",
        "last_name": "Returned",
        "scenario": "CLAIMS RETURNED dispute",
    },
    {
        "email": "patron.lost-item@l30.org",
        "password": "Patron123!",
        "first_name": "Lost",
        "last_name": "Item",
        "scenario": "LOST ITEM CHARGE",
    },
    {
        "email": "patron.damaged-item@l30.org",
        "password": "Patron123!",
        "first_name": "Damaged",
        "last_name": "Item",
        "scenario": "DAMAGED ITEM CHARGE",
    },
]


async def get_or_create_patron(db, patron_data):
    """Get existing patron or create new one."""
    email = patron_data["email"]

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        return user, False  # Existing user

    # Create new patron
    user = User(
        email=email,
        password_hash=hash_password(patron_data["password"]),
        first_name=patron_data["first_name"],
        last_name=patron_data["last_name"],
        role=UserRole.PATRON,
        is_active=True,
        patron_status=PatronStatus.ACTIVE,
        email_verified=True,
    )
    db.add(user)
    await db.flush()

    return user, True  # New user


async def get_or_create_sample_items(db, count: int = 25):
    """Get or create sample catalog items."""
    result = await db.execute(select(CatalogItem).limit(count))
    items = result.scalars().all()

    if len(items) >= count:
        return items[:count]

    # Create additional items if needed
    existing_count = len(items)
    titles = [
        "The Odyssey", "Moby Dick", "War and Peace", "Anna Karenina",
        "Crime and Punishment", "The Brothers Karamazov", "Don Quixote",
        "Les Misérables", "The Count of Monte Cristo", "Frankenstein",
        "Dracula", "Jane Eyre", "Wuthering Heights", "The Scarlet Letter",
        "Beloved", "The Handmaid's Tale", "Oryx and Crake", "Year of the Flood",
    ]

    for i in range(count - existing_count):
        title_idx = (existing_count + i) % len(titles)
        title = titles[title_idx] + f" (Copy {existing_count + i + 1})"

        item = CatalogItem(
            title=title,
            author=f"Author {existing_count + i}",
            isbn=f"978-{1000000 + existing_count + i:07d}",
            description=f"Test item {existing_count + i + 1}",
            status=ItemStatus.available,
            call_number=f"SCENARIO-{existing_count + i + 1:03d}",
            language="en",
            published_year=2024,
            total_copies=5,
        )
        db.add(item)
        items.append(item)

    if len(items) > existing_count:
        await db.flush()

    return items[:count]


async def get_or_create_item_copies(db, catalog_item, count: int = 3):
    """Get or create item copies for a catalog item."""
    result = await db.execute(
        select(ItemCopy).where(ItemCopy.catalog_item_id == catalog_item.id).limit(count)
    )
    copies = result.scalars().all()

    if len(copies) >= count:
        return copies[:count]

    # Create additional copies if needed
    existing_count = len(copies)
    for copy_num in range(existing_count + 1, count + 1):
        barcode = f"{catalog_item.id:05d}-{copy_num:02d}-{datetime.now(timezone.utc).timestamp():.0f}"

        copy = ItemCopy(
            catalog_item_id=catalog_item.id,
            barcode=barcode,
            copy_number=copy_num,
            condition=ItemCondition.GOOD,
            location="Main Library - Circulation",
            acquisition_source=AcquisitionSource.PURCHASE,
        )
        db.add(copy)
        copies.append(copy)

    if len(copies) > existing_count:
        await db.flush()

    return copies[:count]


async def seed_circulation_scenarios():
    """Seed all circulation scenarios."""
    async with AsyncSessionLocal() as db:
        print("\n" + "=" * 90)
        print("SEEDING COMPREHENSIVE CIRCULATION SCENARIOS")
        print("=" * 90 + "\n")

        # Get sample items
        items = await get_or_create_sample_items(db, 25)
        if not items:
            print("❌ ERROR: Could not get or create catalog items")
            return False

        # Get item copies for first few items
        item_copies_map = {}
        for item in items[:20]:
            copies = await get_or_create_item_copies(db, item, 3)
            item_copies_map[item.id] = copies

        now = datetime.now(timezone.utc)
        item_idx = 0
        created_count = 0

        for patron_data in SCENARIO_PATRONS:
            patron, is_new = await get_or_create_patron(db, patron_data)

            status_marker = "✓ CREATED" if is_new else "⊘ SKIPPED"
            print(f"{status_marker}: {patron.email}")
            print(f"  Scenario: {patron_data['scenario']}\n")

            if is_new:
                created_count += 1

            # Get an item for this patron
            if item_idx < len(items):
                catalog_item = items[item_idx]
                copies = item_copies_map.get(catalog_item.id, [])
                if copies:
                    item_copy = copies[0]

                    # === CHECKOUT SCENARIOS ===
                    if "due-today" in patron.email:
                        existing = await db.execute(select(Checkout).where(Checkout.item_id == catalog_item.id, Checkout.status == CheckoutStatus.active))
                        if existing.scalar_one_or_none():
                            item_idx += 1
                            continue
                        checkout = Checkout(
                            user_id=patron.id,
                            item_copy_id=item_copy.id,
                            item_id=catalog_item.id,
                            status=CheckoutStatus.active,
                            checked_out_at=now - timedelta(days=20),
                            due_date=now.replace(hour=23, minute=59, second=59),
                            renewal_count=0,
                            last_overdue_days_processed=0,
                        )
                        db.add(checkout)
                        item_copy.status = "checked_out"
                        print(f"  📚 Checkout: Due TODAY at {now.strftime('%Y-%m-%d')}")
                        print(f"     Item: {catalog_item.title}")
                        print(f"     Barcode: {item_copy.barcode}\n")

                    elif "due-tomorrow" in patron.email:
                        existing = await db.execute(select(Checkout).where(Checkout.item_id == catalog_item.id, Checkout.status == CheckoutStatus.active))
                        if existing.scalar_one_or_none():
                            item_idx += 1
                            continue
                        checkout = Checkout(
                            user_id=patron.id,
                            item_copy_id=item_copy.id,
                            item_id=catalog_item.id,
                            status=CheckoutStatus.active,
                            checked_out_at=now - timedelta(days=19),
                            due_date=(now + timedelta(days=1)).replace(hour=23, minute=59, second=59),
                            renewal_count=0,
                            last_overdue_days_processed=0,
                        )
                        db.add(checkout)
                        item_copy.status = "checked_out"
                        print(f"  📚 Checkout: Due TOMORROW at {(now + timedelta(days=1)).strftime('%Y-%m-%d')}")
                        print(f"     Item: {catalog_item.title}")
                        print(f"     Barcode: {item_copy.barcode}\n")

                    elif "overdue-1day" in patron.email:
                        existing = await db.execute(select(Checkout).where(Checkout.item_id == catalog_item.id, Checkout.status == CheckoutStatus.active))
                        if existing.scalar_one_or_none():
                            item_idx += 1
                            continue
                        due_date = now - timedelta(days=1)
                        checkout = Checkout(
                            user_id=patron.id,
                            item_copy_id=item_copy.id,
                            item_id=catalog_item.id,
                            status=CheckoutStatus.active,
                            checked_out_at=now - timedelta(days=22),
                            due_date=due_date,
                            renewal_count=0,
                            last_overdue_days_processed=0,
                        )
                        db.add(checkout)
                        item_copy.status = "checked_out"
                        print(f"  📚 Checkout: OVERDUE by 1 DAY (due {due_date.strftime('%Y-%m-%d')})")
                        print(f"     Item: {catalog_item.title}")
                        print(f"     Barcode: {item_copy.barcode}\n")

                    elif "overdue-7days" in patron.email:
                        existing = await db.execute(select(Checkout).where(Checkout.item_id == catalog_item.id, Checkout.status == CheckoutStatus.active))
                        if existing.scalar_one_or_none():
                            item_idx += 1
                            continue
                        due_date = now - timedelta(days=7)
                        checkout = Checkout(
                            user_id=patron.id,
                            item_copy_id=item_copy.id,
                            item_id=catalog_item.id,
                            status=CheckoutStatus.active,
                            checked_out_at=now - timedelta(days=28),
                            due_date=due_date,
                            renewal_count=0,
                            last_overdue_days_processed=0,
                        )
                        db.add(checkout)
                        item_copy.status = "checked_out"
                        print(f"  📚 Checkout: OVERDUE by 7 DAYS (due {due_date.strftime('%Y-%m-%d')})")
                        print(f"     Item: {catalog_item.title}")
                        print(f"     Barcode: {item_copy.barcode}\n")

                    elif "overdue-30days" in patron.email:
                        existing = await db.execute(select(Checkout).where(Checkout.item_id == catalog_item.id, Checkout.status == CheckoutStatus.active))
                        if existing.scalar_one_or_none():
                            item_idx += 1
                            continue
                        due_date = now - timedelta(days=32)
                        checkout = Checkout(
                            user_id=patron.id,
                            item_copy_id=item_copy.id,
                            item_id=catalog_item.id,
                            status=CheckoutStatus.active,
                            checked_out_at=now - timedelta(days=52),
                            due_date=due_date,
                            renewal_count=0,
                            last_overdue_days_processed=0,
                        )
                        db.add(checkout)
                        item_copy.status = "checked_out"
                        print(f"  📚 Checkout: OVERDUE by 32+ DAYS (due {due_date.strftime('%Y-%m-%d')})")
                        print(f"     Item: {catalog_item.title}")
                        print(f"     Barcode: {item_copy.barcode}\n")

                    # === RENEWAL SCENARIOS ===
                    elif "renewed-once" in patron.email:
                        existing = await db.execute(select(Checkout).where(Checkout.item_id == catalog_item.id, Checkout.status == CheckoutStatus.active))
                        if existing.scalar_one_or_none():
                            item_idx += 1
                            continue
                        checkout = Checkout(
                            user_id=patron.id,
                            item_copy_id=item_copy.id,
                            item_id=catalog_item.id,
                            status=CheckoutStatus.active,
                            checked_out_at=now - timedelta(days=25),
                            due_date=now + timedelta(days=10),
                            renewal_count=1,
                            last_overdue_days_processed=0,
                        )
                        db.add(checkout)
                        item_copy.status = "checked_out"
                        print("  📚 Checkout: 1 RENEWAL used (2 remaining)")
                        print(f"     Item: {catalog_item.title}")
                        print(f"     Barcode: {item_copy.barcode}\n")

                    elif "renewed-twice" in patron.email:
                        existing = await db.execute(select(Checkout).where(Checkout.item_id == catalog_item.id, Checkout.status == CheckoutStatus.active))
                        if existing.scalar_one_or_none():
                            item_idx += 1
                            continue
                        checkout = Checkout(
                            user_id=patron.id,
                            item_copy_id=item_copy.id,
                            item_id=catalog_item.id,
                            status=CheckoutStatus.active,
                            checked_out_at=now - timedelta(days=45),
                            due_date=now + timedelta(days=5),
                            renewal_count=2,
                            last_overdue_days_processed=0,
                        )
                        db.add(checkout)
                        item_copy.status = "checked_out"
                        print("  📚 Checkout: 2 RENEWALS used (1 remaining)")
                        print(f"     Item: {catalog_item.title}")
                        print(f"     Barcode: {item_copy.barcode}\n")

                    elif "at-max-renewals" in patron.email:
                        existing = await db.execute(select(Checkout).where(Checkout.item_id == catalog_item.id, Checkout.status == CheckoutStatus.active))
                        if existing.scalar_one_or_none():
                            item_idx += 1
                            continue
                        checkout = Checkout(
                            user_id=patron.id,
                            item_copy_id=item_copy.id,
                            item_id=catalog_item.id,
                            status=CheckoutStatus.active,
                            checked_out_at=now - timedelta(days=65),
                            due_date=now + timedelta(days=8),
                            renewal_count=3,  # Max renewals reached
                            last_overdue_days_processed=0,
                        )
                        db.add(checkout)
                        item_copy.status = "checked_out"
                        print("  📚 Checkout: AT MAX RENEWALS (3/3 used)")
                        print(f"     Item: {catalog_item.title}")
                        print(f"     Barcode: {item_copy.barcode}\n")

            item_idx += 1

        # === HOLD SCENARIOS - Need to create separate holds ===

        async def has_active_hold(db, user_id, item_id):
            """Check if user already has a pending/ready hold on this item."""
            result = await db.execute(
                select(Hold).where(
                    Hold.user_id == user_id,
                    Hold.item_id == item_id,
                    Hold.status.in_([HoldStatus.pending, HoldStatus.ready])
                )
            )
            return result.scalar_one_or_none() is not None

        # Get remaining items for holds
        if len(items) > item_idx:
            hold_items = items[item_idx:]

            # Hold Position 1
            result = await db.execute(select(User).where(User.email == "patron.holds-queue-pos1@l30.org"))
            patron = result.scalar_one()

            if not await has_active_hold(db, patron.id, hold_items[0].id):
                hold = Hold(
                    user_id=patron.id,
                    item_id=hold_items[0].id,
                    status=HoldStatus.pending,
                    position=1,
                    created_at=now - timedelta(days=10),
                )
                db.add(hold)
            print(f"✓ Hold Position 1: {patron.email}")
            print(f"  Item: {hold_items[0].title}")
            print("  Position: 1 (first in queue)\n")

            # Hold Position 2
            result = await db.execute(select(User).where(User.email == "patron.holds-queue-pos2@l30.org"))
            patron = result.scalar_one()

            if not await has_active_hold(db, patron.id, hold_items[0].id):
                hold = Hold(
                    user_id=patron.id,
                    item_id=hold_items[0].id,  # Same item
                    status=HoldStatus.pending,
                    position=2,
                    created_at=now - timedelta(days=8),
                )
                db.add(hold)
            print(f"✓ Hold Position 2: {patron.email}")
            print(f"  Item: {hold_items[0].title}")
            print("  Position: 2 (second in queue)\n")

            # Hold Position 3+
            result = await db.execute(select(User).where(User.email == "patron.holds-queue-pos3@l30.org"))
            patron = result.scalar_one()

            if not await has_active_hold(db, patron.id, hold_items[0].id):
                hold = Hold(
                    user_id=patron.id,
                    item_id=hold_items[0].id,  # Same item
                    status=HoldStatus.pending,
                    position=3,
                    created_at=now - timedelta(days=5),
                )
                db.add(hold)
            print(f"✓ Hold Position 3: {patron.email}")
            print(f"  Item: {hold_items[0].title}")
            print("  Position: 3+ (third+ in queue)\n")

            # Hold Ready for Pickup
            result = await db.execute(select(User).where(User.email == "patron.hold-ready@l30.org"))
            patron = result.scalar_one()

            if not await has_active_hold(db, patron.id, hold_items[1].id):
                hold = Hold(
                    user_id=patron.id,
                    item_id=hold_items[1].id,
                    status=HoldStatus.ready,
                    position=1,
                    created_at=now - timedelta(days=15),
                    notified_at=now - timedelta(days=2),
                )
                db.add(hold)
            print(f"✓ Hold Ready for Pickup: {patron.email}")
            print(f"  Item: {hold_items[1].title}")
            print("  Status: READY FOR PICKUP\n")

            # Hold Expiring Today
            result = await db.execute(select(User).where(User.email == "patron.hold-expiring-today@l30.org"))
            patron = result.scalar_one()

            if not await has_active_hold(db, patron.id, hold_items[2].id):
                hold = Hold(
                    user_id=patron.id,
                    item_id=hold_items[2].id,
                    status=HoldStatus.pending,
                    position=1,
                    created_at=now - timedelta(days=20),
                    expires_at=now.replace(hour=23, minute=59, second=59),  # Today
                )
                db.add(hold)
            print(f"✓ Hold Expiring Today: {patron.email}")
            print(f"  Item: {hold_items[2].title}")
            print(f"  Expires: TODAY at {now.strftime('%Y-%m-%d')}\n")

        # === FINE SCENARIOS ===

        # Paid Fines
        result = await db.execute(select(User).where(User.email == "patron.fine-paid@l30.org"))
        patron = result.scalar_one()

        fine = Fine(
            user_id=patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.paid,
            amount=Decimal("25.00"),
            amount_paid=Decimal("25.00"),
            description="Overdue fine - 15 days late",
            created_at=now - timedelta(days=16),
            paid_at=now - timedelta(days=5),
        )
        db.add(fine)
        print(f"✓ Paid Fine: {patron.email}")
        print("  Amount: $25.00 | Status: PAID")
        print(f"  Paid on: {(now - timedelta(days=5)).strftime('%Y-%m-%d')}\n")

        # Waived Fines
        result = await db.execute(select(User).where(User.email == "patron.fine-waived@l30.org"))
        patron = result.scalar_one()

        fine = Fine(
            user_id=patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.waived,
            amount=Decimal("18.50"),
            amount_paid=Decimal("0.00"),
            description="Overdue fine - waived per library policy",
            created_at=now - timedelta(days=14),
            waived_at=now - timedelta(days=3),
        )
        db.add(fine)
        print(f"✓ Waived Fine: {patron.email}")
        print("  Amount: $18.50 | Status: WAIVED")
        print(f"  Waived on: {(now - timedelta(days=3)).strftime('%Y-%m-%d')}\n")

        # Partially Paid Fines
        result = await db.execute(select(User).where(User.email == "patron.fine-partial@l30.org"))
        patron = result.scalar_one()

        fine = Fine(
            user_id=patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.partial,
            amount=Decimal("30.00"),
            amount_paid=Decimal("15.00"),
            description="Overdue fine - payment plan",
            created_at=now - timedelta(days=20),
        )
        db.add(fine)
        print(f"✓ Partially Paid Fine: {patron.email}")
        print("  Amount: $30.00 | Paid: $15.00 | Balance: $15.00")
        print("  Status: PARTIAL (payment plan)\n")

        # === DISPUTE SCENARIOS ===

        # Claims Returned
        result = await db.execute(select(User).where(User.email == "patron.claims-returned@l30.org"))
        patron = result.scalar_one()

        if item_idx < len(items):
            item = items[item_idx]
            copies = await get_or_create_item_copies(db, item, 1)

            existing = await db.execute(select(Checkout).where(Checkout.item_id == item.id, Checkout.status == CheckoutStatus.active))
            if not existing.scalar_one_or_none():
                checkout = Checkout(
                    user_id=patron.id,
                    item_copy_id=copies[0].id,
                    item_id=item.id,
                    status=CheckoutStatus.claims_returned,
                    checked_out_at=now - timedelta(days=45),
                    due_date=now - timedelta(days=20),
                    renewal_count=0,
                    last_overdue_days_processed=0,
                )
                db.add(checkout)
            print(f"✓ Claims Returned Dispute: {patron.email}")
            print(f"  Item: {item.title}")
            print(f"  Barcode: {copies[0].barcode}")
            print("  Status: CLAIMS_RETURNED\n")
            item_idx += 1

        # Lost Item
        result = await db.execute(select(User).where(User.email == "patron.lost-item@l30.org"))
        patron = result.scalar_one()

        fine = Fine(
            user_id=patron.id,
            fine_type=FineType.lost_item,
            status=FineStatus.unpaid,
            amount=Decimal("45.00"),
            description="Lost item charge - replacement cost",
            created_at=now - timedelta(days=30),
        )
        db.add(fine)
        print(f"✓ Lost Item Charge: {patron.email}")
        print("  Fine Type: LOST_ITEM")
        print("  Amount: $45.00 (replacement cost)\n")

        # Damaged Item
        result = await db.execute(select(User).where(User.email == "patron.damaged-item@l30.org"))
        patron = result.scalar_one()

        fine = Fine(
            user_id=patron.id,
            fine_type=FineType.damaged_item,
            status=FineStatus.unpaid,
            amount=Decimal("12.50"),
            description="Damaged item charge - repair costs",
            created_at=now - timedelta(days=10),
        )
        db.add(fine)
        print(f"✓ Damaged Item Charge: {patron.email}")
        print("  Fine Type: DAMAGED_ITEM")
        print("  Amount: $12.50 (repair costs)\n")

        # Commit all changes
        try:
            await db.commit()
            print("=" * 90)
            print(f"✅ SEEDING COMPLETE - {created_count} new patrons created")
            print("=" * 90 + "\n")
            return True
        except Exception as e:
            await db.rollback()
            print(f"\n❌ COMMIT FAILED: {str(e)}\n")
            raise


async def main():
    """Main entry point."""
    try:
        success = await seed_circulation_scenarios()
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Error during seeding: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
