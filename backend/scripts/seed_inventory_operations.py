#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Inventory Operations Seed Script for LSC Library System

Seeds realistic staff operational data for inventory management:
- Physical item copies with condition tracking
- Recent inventory audit records with results
- Condition change history for items
- Items requiring maintenance or repair
- Inventory discrepancy reports

This data is essential for:
- Item condition assessment and management
- Inventory audit workflows
- Maintenance planning
- Collection health reporting
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, date
from decimal import Decimal
import random

# Setup path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.inventory import (
    ItemCopy, ConditionChange, ItemCondition, DamageType, AcquisitionSource,
    InventoryAudit, AuditScan
)
from app.models.catalog import CatalogItem
from app.models.user import User

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@database:5432/lsc_library"
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def seed_item_copies(session: AsyncSession, catalog_items: list) -> list[ItemCopy]:
    """Seed physical item copies in inventory."""
    print("  Seeding item copies...")

    # Check if copies already exist
    result = await session.execute(select(ItemCopy).limit(1))
    if result.scalar_one_or_none():
        print("    Item copies already exist, skipping...")
        return []

    if not catalog_items:
        print("    No catalog items available, skipping...")
        return []

    created_copies = []
    _ = list(ItemCondition)
    locations = [
        "Adult Fiction A-B",
        "Adult Fiction C-D",
        "Adult Fiction E-F",
        "Adult Nonfiction 000-100",
        "Adult Nonfiction 100-200",
        "Reference A-B",
        "Reference C-D",
        "Children's Books A-B",
        "Children's Books C-D",
        "Young Adult",
        "DVDs",
        "Audiobooks",
    ]

    barcode_counter = 1000

    # Create 3-5 copies of each catalog item
    for item in catalog_items[:15]:  # Limit to first 15 catalog items
        num_copies = random.randint(3, 5)

        for copy_num in range(1, num_copies + 1):
            barcode = f"LSC-{barcode_counter:06d}"
            barcode_counter += 1

            # Vary conditions with more GOOD/FAIR, fewer POOR/DAMAGED
            condition_weights = {
                ItemCondition.NEW: 0.1,
                ItemCondition.GOOD: 0.5,
                ItemCondition.FAIR: 0.25,
                ItemCondition.POOR: 0.1,
                ItemCondition.DAMAGED: 0.05,
                ItemCondition.WITHDRAWN: 0,
            }
            condition = random.choices(
                list(condition_weights.keys()),
                weights=list(condition_weights.values()),
                k=1
            )[0]

            copy = ItemCopy(
                catalog_item_id=item.id,
                barcode=barcode,
                copy_number=copy_num,
                condition=condition,
                acquisition_date=date.today() - timedelta(days=random.randint(30, 730)),
                acquisition_source=random.choice(
                    [AcquisitionSource.PURCHASE, AcquisitionSource.DONATION, AcquisitionSource.GRANT]
                ),
                location=random.choice(locations),
                replacement_cost=Decimal(str(random.uniform(15.00, 45.00))),
                is_fragile=random.random() < 0.1,  # 10% fragile
                handling_instructions=(
                    "Handle with care - rare edition" if copy_num == 1 and random.random() < 0.2
                    else "Check binding before checkout" if random.random() < 0.2
                    else None
                ),
            )
            session.add(copy)
            created_copies.append(copy)

    await session.commit()
    print(f"    Created {len(created_copies)} item copies")
    return created_copies


async def seed_inventory_audits(session: AsyncSession, staff_users: list) -> list[InventoryAudit]:
    """Seed inventory audit records with results."""
    print("  Seeding inventory audits...")

    # Check if audits already exist
    result = await session.execute(select(InventoryAudit).limit(1))
    if result.scalar_one_or_none():
        print("    Inventory audits already exist, skipping...")
        return []

    if not staff_users:
        print("    No staff users available, skipping...")
        return []

    created_audits = []

    # Audit 1: Completed last month - Adult Fiction section
    audit1 = InventoryAudit(
        name="Adult Fiction Section Audit - January 2024",
        description="Complete physical count of Adult Fiction A-L",
        location_filter="Adult Fiction A-L",
        started_at=datetime.now() - timedelta(days=35),
        completed_at=datetime.now() - timedelta(days=30),
        items_expected=145,
        items_found=142,
        items_missing=3,
        items_misplaced=2,
        created_by_id=staff_users[0].id,
    )
    session.add(audit1)
    created_audits.append(audit1)

    # Audit 2: Completed 2 weeks ago - Reference Section
    audit2 = InventoryAudit(
        name="Reference Section Audit - January 2024",
        description="Complete physical count of Reference materials",
        location_filter="Reference",
        started_at=datetime.now() - timedelta(days=20),
        completed_at=datetime.now() - timedelta(days=14),
        items_expected=87,
        items_found=85,
        items_missing=2,
        items_misplaced=1,
        created_by_id=staff_users[0].id if len(staff_users) > 0 else staff_users[0].id,
    )
    session.add(audit2)
    created_audits.append(audit2)

    # Audit 3: In progress - Children's Section (started 3 days ago)
    audit3 = InventoryAudit(
        name="Children's Section Audit - February 2024",
        description="Physical count of Children's books (A-M)",
        location_filter="Children's Books A-M",
        started_at=datetime.now() - timedelta(days=3),
        items_expected=156,
        items_found=142,  # Partial results
        items_missing=0,
        items_misplaced=4,
        created_by_id=staff_users[1].id if len(staff_users) > 1 else staff_users[0].id,
    )
    session.add(audit3)
    created_audits.append(audit3)

    await session.commit()
    print(f"    Created {len(created_audits)} inventory audits")
    return created_audits


async def seed_condition_changes(session: AsyncSession, item_copies: list[ItemCopy], staff_users: list) -> None:
    """Seed condition change history."""
    print("  Seeding condition changes...")

    # Check if changes already exist
    result = await session.execute(select(ConditionChange).limit(1))
    if result.scalar_one_or_none():
        print("    Condition changes already exist, skipping...")
        return

    if not staff_users or not item_copies:
        print("    Insufficient data (staff or copies), skipping...")
        return

    created = 0

    # Select some copies that are not in perfect condition for change history
    damaged_copies = [c for c in item_copies if c.condition in [ItemCondition.DAMAGED, ItemCondition.POOR, ItemCondition.FAIR]]

    damage_types = [
        DamageType.TORN_PAGES,
        DamageType.WATER_DAMAGE,
        DamageType.SPINE_DAMAGE,
        DamageType.WRITING_MARKS,
        DamageType.STAINS,
        DamageType.BINDING_LOOSE,
    ]

    for copy in damaged_copies[:10]:  # Create history for first 10 damaged items
        # Create a condition change record
        previous_cond = ItemCondition.GOOD
        new_cond = copy.condition

        damage_type = random.choice(damage_types)
        repair_cost = None
        repaired_at = None

        # If currently DAMAGED, assume it's awaiting repair
        if copy.condition == ItemCondition.DAMAGED:
            repair_cost = Decimal(str(random.uniform(10.00, 75.00)))

        change = ConditionChange(
            item_copy_id=copy.id,
            previous_condition=previous_cond,
            new_condition=new_cond,
            damage_type=damage_type,
            damage_description=f"{damage_type.value} reported during circulation",
            repair_cost=repair_cost,
            repair_notes=(
                "Awaiting repair" if repair_cost else
                "Repaired by bindery" if random.random() < 0.5 else None
            ),
            repaired_at=repaired_at,
            reported_by_id=random.choice(staff_users).id,
            created_at=datetime.now() - timedelta(days=random.randint(1, 30)),
        )
        session.add(change)
        created += 1

    # Add some cosmetic damage records
    for copy in random.sample(item_copies[10:], min(5, len(item_copies[10:]))):
        change = ConditionChange(
            item_copy_id=copy.id,
            previous_condition=ItemCondition.GOOD,
            new_condition=ItemCondition.FAIR,
            damage_type=DamageType.WRITING_MARKS,
            damage_description="Pen marks and annotations found",
            reported_by_id=random.choice(staff_users).id,
            created_at=datetime.now() - timedelta(days=random.randint(10, 60)),
        )
        session.add(change)
        created += 1

    await session.commit()
    print(f"    Created {created} condition change records")


async def seed_audit_scans(session: AsyncSession, audits: list[InventoryAudit], item_copies: list[ItemCopy], staff_users: list) -> None:
    """Seed audit scan records."""
    print("  Seeding audit scan records...")

    # Check if scans already exist
    result = await session.execute(select(AuditScan).limit(1))
    if result.scalar_one_or_none():
        print("    Audit scans already exist, skipping...")
        return

    if not audits or not item_copies or not staff_users:
        print("    Insufficient data, skipping...")
        return

    created = 0

    # Audit 1: 142 items found (3 missing, 2 misplaced)
    if len(audits) > 0:
        for copy in item_copies[:140]:
            scan = AuditScan(
                audit_id=audits[0].id,
                item_copy_id=copy.id,
                found_at_location=copy.location,
                is_misplaced=False,
                scanned_at=audits[0].started_at + timedelta(hours=random.randint(1, 100)),
                scanned_by_id=random.choice(staff_users).id,
            )
            session.add(scan)
            created += 1

        # Add 2 misplaced items
        for copy in random.sample(item_copies[140:], min(2, len(item_copies[140:]))):
            scan = AuditScan(
                audit_id=audits[0].id,
                item_copy_id=copy.id,
                found_at_location="Adult Fiction M-Z",  # Wrong location
                is_misplaced=True,
                scanned_at=audits[0].started_at + timedelta(hours=random.randint(1, 100)),
                scanned_by_id=random.choice(staff_users).id,
            )
            session.add(scan)
            created += 1

    # Audit 2: 85 items found (2 missing, 1 misplaced)
    if len(audits) > 1:
        for copy in item_copies[30:115]:
            scan = AuditScan(
                audit_id=audits[1].id,
                item_copy_id=copy.id,
                found_at_location=copy.location,
                is_misplaced=False,
                scanned_at=audits[1].started_at + timedelta(hours=random.randint(1, 100)),
                scanned_by_id=random.choice(staff_users).id,
            )
            session.add(scan)
            created += 1

        # Add 1 misplaced
        if len(item_copies) > 115:
            scan = AuditScan(
                audit_id=audits[1].id,
                item_copy_id=item_copies[115].id,
                found_at_location="Reference E-F",
                is_misplaced=True,
                scanned_at=audits[1].started_at + timedelta(hours=80),
                scanned_by_id=random.choice(staff_users).id,
            )
            session.add(scan)
            created += 1

    # Audit 3: In progress - 142 items found so far
    if len(audits) > 2:
        for copy in item_copies[:140]:
            scan = AuditScan(
                audit_id=audits[2].id,
                item_copy_id=copy.id,
                found_at_location=copy.location,
                is_misplaced=False,
                scanned_at=audits[2].started_at + timedelta(hours=random.randint(1, 70)),
                scanned_by_id=random.choice(staff_users).id,
            )
            session.add(scan)
            created += 1

        # Add 4 misplaced (in progress)
        for copy in random.sample(item_copies[140:], min(4, len(item_copies[140:]))):
            scan = AuditScan(
                audit_id=audits[2].id,
                item_copy_id=copy.id,
                found_at_location="Children's Books N-Z",
                is_misplaced=True,
                scanned_at=audits[2].started_at + timedelta(hours=random.randint(1, 70)),
                scanned_by_id=random.choice(staff_users).id,
            )
            session.add(scan)
            created += 1

    await session.commit()
    print(f"    Created {created} audit scan records")


async def main():
    """Main seeding function."""
    print("\n" + "=" * 70)
    print("LSC INVENTORY OPERATIONS DATA SEEDING")
    print("=" * 70)

    async with AsyncSessionLocal() as session:
        try:
            # Get catalog items
            items_result = await session.execute(select(CatalogItem).limit(30))
            catalog_items = items_result.scalars().all()

            if not catalog_items:
                print("⚠️  No catalog items found in database!")
                print("   Run seed_comprehensive.py first to create catalog items.")
                return 1

            # Get staff users. UserRole is a StrEnum with lowercase wire
            # values ("staff", "admin"); the uppercase member-name literals
            # never matched, so this always came back empty.
            users_result = await session.execute(
                select(User).where(User.role.in_(["staff", "admin"])).limit(5)
            )
            staff_users = users_result.scalars().all()

            if not staff_users:
                print("⚠️  No staff users found in database!")
                print("   Run seed_test_accounts.py first to create users.")
                return 1

            print(f"\n📋 Using {len(catalog_items)} catalog items and {len(staff_users)} staff users\n")

            # Seed item copies
            item_copies = await seed_item_copies(session, catalog_items)

            # Seed inventory audits
            audits = await seed_inventory_audits(session, staff_users)

            # Seed condition changes
            if item_copies:
                await seed_condition_changes(session, item_copies, staff_users)

            # Seed audit scans
            if audits and item_copies:
                await seed_audit_scans(session, audits, item_copies, staff_users)

            print("\n" + "=" * 70)
            print("✅ INVENTORY OPERATIONS SEED COMPLETED SUCCESSFULLY")
            print("=" * 70)
            print("\n📊 Summary:")
            print(f"  ✓ Item copies created: {len(item_copies)}")
            print(f"  ✓ Inventory audits created: {len(audits)}")
            print("  ✓ Condition changes recorded: Multiple")
            print("  ✓ Audit scans recorded: Multiple")
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
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
