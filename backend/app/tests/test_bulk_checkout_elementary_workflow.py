# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Test suite for bulk checkout workflow at Somewhere Up North Elementary.

Tests the complete lifecycle:
1. Create bulk checkout for 3rd grade classroom (30 books, 6-week loan)
2. Add items with condition_out assessment
3. Process individual returns with condition_in
4. Verify condition changes are flagged
5. Close bulk checkout when all items returned
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem, ItemStatus
from app.models.inventory import ItemCopy, ItemCondition
from app.models.outreach import (
    OutreachPartner, BulkCheckout, BulkCheckoutItem,
    PartnerType, OutreachPartnerStatus, PartnershipTier, SchoolLevel,
    BulkCheckoutStatus,
)
from app.models.user import User, UserRole


@pytest.mark.asyncio
class TestBulkCheckoutElementaryWorkflow:
    """Test the complete bulk checkout workflow for Somewhere Up North Elementary 3rd grade."""

    @pytest.fixture
    async def staff_user(self, db: AsyncSession) -> User:
        """Create the staff user who registers the partner.

        outreach_partners.created_by_id is a real FK to users.id; this used
        to hardcode created_by_id=1, which only worked when a seed user
        happened to occupy that row. The shared app/tests/conftest.py `db`
        fixture starts from an empty database, so that FK now fails.
        """
        user = User(
            email="staff@example.com",
            password_hash="hashed_password",
            first_name="Library",
            last_name="Staff",
            role=UserRole.STAFF,
        )
        db.add(user)
        await db.flush()
        return user

    @pytest.fixture
    async def partner(self, db: AsyncSession, staff_user: User):
        """Create the Somewhere Up North Elementary partner."""
        partner = OutreachPartner(
            name="Somewhere Up North Elementary",
            partner_type=PartnerType.SCHOOL.value,
            status=OutreachPartnerStatus.ACTIVE.value,
            partnership_tier=PartnershipTier.SILVER.value,
            school_level=SchoolLevel.ELEMENTARY.value,
            school_district="Somewhere Up North School District",
            primary_contact_name="Mrs. Thompson",
            primary_contact_title="3rd Grade Teacher",
            primary_contact_email="thompson@sce.edu",
            allows_bulk_checkout=True,
            checkout_limit=100,
            loan_period_days=42,
            created_by_id=staff_user.id,
        )
        db.add(partner)
        await db.flush()
        return partner

    @pytest.fixture
    async def catalog_items(self, db: AsyncSession):
        """Create 30 catalog items for the classroom checkout."""
        items = []
        book_titles = [
            "Charlotte's Web", "James and the Giant Peach",
            "The BFG", "Matilda", "Charlie and the Chocolate Factory",
            "The Phantom Tollbooth", "Where the Red Fern Grows",
            "Bridge to Terabithia", "Island of the Blue Dolphins",
            "Number the Stars", "Sarah Plain and Tall",
            "Shiloh", "Hatchet", "My Side of the Mountain",
            "The Indian in the Cupboard", "Stuart Little",
            "The Cricket in Times Square", "Ramona Quimby Age 8",
            "Tales of a Fourth Grade Nothing", "Frindle",
            "The Lemonade War", "The One and Only Ivan",
            "Flora and Ulysses", "The Wild Robot",
            "Pax", "Hello Universe", "Merci Suarez Changes Gears",
            "Front Desk", "New Kid", "The Year of the Dog",
        ]
        for i, title in enumerate(book_titles):
            catalog_item = CatalogItem(
                title=title,
                author=f"Author {i+1}",
                isbn=f"978-0-{i+1:06d}-00-{i%10}",
                description="A wonderful book for 3rd graders",
                status=ItemStatus.available,
                call_number=f"JF {title[:3].upper()} {i+1:03d}",
                publication_year=2020 + (i % 5),
            )
            db.add(catalog_item)
            items.append(catalog_item)
        await db.flush()
        return items

    @pytest.fixture
    async def item_copies(self, db: AsyncSession, catalog_items):
        """Create physical copies (with barcodes) for each catalog item."""
        copies = []
        # Assign varied conditions to simulate real library items
        conditions = [
            ItemCondition.NEW, ItemCondition.NEW, ItemCondition.NEW,
            ItemCondition.GOOD, ItemCondition.GOOD, ItemCondition.GOOD,
            ItemCondition.GOOD, ItemCondition.GOOD, ItemCondition.GOOD,
            ItemCondition.GOOD, ItemCondition.GOOD, ItemCondition.GOOD,
            ItemCondition.GOOD, ItemCondition.GOOD, ItemCondition.GOOD,
            ItemCondition.FAIR, ItemCondition.FAIR, ItemCondition.FAIR,
            ItemCondition.FAIR, ItemCondition.FAIR, ItemCondition.FAIR,
            ItemCondition.GOOD, ItemCondition.GOOD, ItemCondition.GOOD,
            ItemCondition.NEW, ItemCondition.GOOD, ItemCondition.FAIR,
            ItemCondition.GOOD, ItemCondition.GOOD, ItemCondition.NEW,
        ]
        for i, catalog_item in enumerate(catalog_items):
            copy = ItemCopy(
                catalog_item_id=catalog_item.id,
                barcode=f"SCE-3RD-{i+1:04d}",
                copy_number=1,
                condition=conditions[i],
                replacement_cost=Decimal("12.99"),
                location="Children's Fiction A-2",
            )
            db.add(copy)
            copies.append(copy)
        await db.flush()
        return copies

    async def test_01_create_bulk_checkout_for_3rd_grade(
        self, db: AsyncSession, partner, item_copies
    ):
        """Step 1: Create a bulk checkout for 30 books, 6-week loan period."""
        today = date.today()
        due = today + timedelta(weeks=6)

        bulk_checkout = BulkCheckout(
            partner_id=partner.id,
            checkout_name="Mrs. Thompson's 3rd Grade - Spring Reading",
            status=BulkCheckoutStatus.ACTIVE.value,
            requestor_name="Mrs. Thompson",
            requestor_email="thompson@sce.edu",
            classroom_name="Room 204",
            grade_level="3",
            checkout_date=today,
            due_date=due,
            total_items=0,
            items_returned=0,
            items_lost=0,
            items_damaged=0,
            topic_requests=["fiction", "adventure", "animals"],
            reading_level_min="3.0",
            reading_level_max="5.0",
            delivery_method="pickup",
            pickup_location="Main Branch - Children's Desk",
            notes="Spring semester classroom library. 30 books for 25 students.",
            # bulk_checkouts.processed_by_id is a real FK to users.id; this
            # (and the other 5 occurrences below) used to hardcode 1, which
            # only worked when a seed user happened to occupy that row.
            # Reuse the same staff user that created `partner` (also a real
            # FK) rather than adding a redundant fixture dependency.
            processed_by_id=partner.created_by_id,
        )
        db.add(bulk_checkout)
        await db.flush()

        assert bulk_checkout.id is not None
        assert bulk_checkout.status == BulkCheckoutStatus.ACTIVE.value
        assert bulk_checkout.checkout_name == "Mrs. Thompson's 3rd Grade - Spring Reading"
        assert bulk_checkout.grade_level == "3"
        assert bulk_checkout.due_date == due
        assert (bulk_checkout.due_date - bulk_checkout.checkout_date).days == 42

        await db.commit()
        return bulk_checkout

    async def test_02_add_items_with_condition_out(
        self, db: AsyncSession, partner, catalog_items, item_copies
    ):
        """Step 2: Add 30 items to the bulk checkout with condition_out assessment."""
        today = date.today()
        due = today + timedelta(weeks=6)

        # Create checkout
        bulk_checkout = BulkCheckout(
            partner_id=partner.id,
            checkout_name="Mrs. Thompson's 3rd Grade - Spring Reading",
            status=BulkCheckoutStatus.ACTIVE.value,
            requestor_name="Mrs. Thompson",
            requestor_email="thompson@sce.edu",
            classroom_name="Room 204",
            grade_level="3",
            checkout_date=today,
            due_date=due,
            total_items=0,
            items_returned=0,
            items_lost=0,
            items_damaged=0,
            processed_by_id=partner.created_by_id,
        )
        db.add(bulk_checkout)
        await db.flush()
        checkout_id = bulk_checkout.id

        # Add all 30 items with condition_out assessment
        condition_map = {
            ItemCondition.NEW: "new",
            ItemCondition.GOOD: "good",
            ItemCondition.FAIR: "fair",
        }
        added_items = []
        for copy in item_copies:
            item = BulkCheckoutItem(
                bulk_checkout_id=checkout_id,
                item_copy_id=copy.id,
                barcode=copy.barcode,
                title=copy.catalog_item.title if copy.catalog_item else None,
                call_number=copy.catalog_item.call_number if copy.catalog_item else None,
                # dict.get() evaluates its default arg eagerly even when the
                # key is found, so `.value` must be safe for every branch.
                # ItemCondition is a StrEnum, so `copy.condition` sometimes
                # comes back as the enum member and sometimes as a plain
                # str depending on whether it was reloaded from the DB
                # (String(50) column, not a mapped SQLEnum, so there's no
                # ORM-level coercion back to the enum type on refresh).
                # str() on either gives the same wire value; .value doesn't
                # exist on a plain str.
                condition_out=condition_map.get(copy.condition, str(copy.condition)),
                replacement_cost=float(copy.replacement_cost) if copy.replacement_cost else None,
                status="checked_out",
            )
            db.add(item)
            added_items.append(item)

        bulk_checkout.total_items = len(added_items)
        await db.flush()

        # Verify
        assert len(added_items) == 30
        assert bulk_checkout.total_items == 30

        # Verify condition_out recorded for all items
        for item in added_items:
            assert item.condition_out is not None
            assert item.condition_out in ["new", "good", "fair"]
            assert item.status == "checked_out"

        await db.commit()

    async def test_03_process_individual_returns_with_condition_in(
        self, db: AsyncSession, partner, catalog_items, item_copies
    ):
        """Step 3: Process returns individually, recording condition_in."""
        today = date.today()
        due = today + timedelta(weeks=6)

        # Setup: create checkout with items
        bulk_checkout = BulkCheckout(
            partner_id=partner.id,
            checkout_name="Mrs. Thompson's 3rd Grade - Spring Reading",
            status=BulkCheckoutStatus.ACTIVE.value,
            requestor_name="Mrs. Thompson",
            checkout_date=today,
            due_date=due,
            total_items=0,
            items_returned=0,
            items_lost=0,
            items_damaged=0,
            processed_by_id=partner.created_by_id,
        )
        db.add(bulk_checkout)
        await db.flush()
        checkout_id = bulk_checkout.id

        # Add all 30 items
        bulk_items = []
        conditions_out = ["good"] * 20 + ["new"] * 5 + ["fair"] * 5
        for i, copy in enumerate(item_copies):
            item = BulkCheckoutItem(
                bulk_checkout_id=checkout_id,
                item_copy_id=copy.id,
                barcode=copy.barcode,
                title=copy.catalog_item.title if copy.catalog_item else None,
                condition_out=conditions_out[i],
                replacement_cost=float(copy.replacement_cost) if copy.replacement_cost else None,
                status="checked_out",
            )
            db.add(item)
            bulk_items.append(item)

        bulk_checkout.total_items = 30
        await db.flush()

        # Return first 10 items in same condition
        for i in range(10):
            bulk_items[i].status = "returned"
            bulk_items[i].condition_in = bulk_items[i].condition_out
            bulk_items[i].returned_at = db.info.get("now") or None
            bulk_checkout.items_returned += 1

        await db.flush()

        assert bulk_checkout.items_returned == 10
        assert bulk_checkout.total_items == 30

        # Verify partially-returned status
        bulk_checkout.status = BulkCheckoutStatus.PARTIALLY_RETURNED.value
        await db.flush()
        assert bulk_checkout.status == BulkCheckoutStatus.PARTIALLY_RETURNED.value

        await db.commit()

    async def test_04_verify_condition_changes_are_flagged(
        self, db: AsyncSession, partner, catalog_items, item_copies
    ):
        """Step 4: Verify items with condition changes are flagged."""
        today = date.today()
        due = today + timedelta(weeks=6)

        # Setup checkout
        bulk_checkout = BulkCheckout(
            partner_id=partner.id,
            checkout_name="Mrs. Thompson's 3rd Grade - Condition Test",
            status=BulkCheckoutStatus.ACTIVE.value,
            requestor_name="Mrs. Thompson",
            checkout_date=today,
            due_date=due,
            total_items=0,
            items_returned=0,
            items_lost=0,
            items_damaged=0,
            processed_by_id=partner.created_by_id,
        )
        db.add(bulk_checkout)
        await db.flush()
        checkout_id = bulk_checkout.id

        # Add 30 items with known conditions
        bulk_items = []
        for i, copy in enumerate(item_copies):
            condition_out = "good" if i < 20 else "new" if i < 25 else "fair"
            item = BulkCheckoutItem(
                bulk_checkout_id=checkout_id,
                item_copy_id=copy.id,
                barcode=copy.barcode,
                condition_out=condition_out,
                replacement_cost=float(copy.replacement_cost) if copy.replacement_cost else None,
                status="checked_out",
            )
            db.add(item)
            bulk_items.append(item)
        bulk_checkout.total_items = 30
        await db.flush()

        # Return items with mixed condition changes:
        # Items 0-19: checked out "good"
        #   - Items 0-14: returned "good" (no change)
        #   - Item 15: returned "fair" (DEGRADED)
        #   - Item 16: returned "poor" (DEGRADED)
        #   - Item 17: returned "damaged" (DEGRADED) with damage notes
        #   - Items 18-19: returned "good" (no change)
        # Items 20-24: checked out "new"
        #   - Item 20: returned "new" (no change)
        #   - Item 21: returned "good" (DEGRADED)
        #   - Items 22-24: returned "new" (no change)
        # Items 25-29: checked out "fair"
        #   - Item 25: returned "poor" (DEGRADED)
        #   - Items 26-29: returned "fair" (no change)

        returns_data = []
        for i in range(30):
            item = bulk_items[i]
            if i < 15:
                condition_in = "good"
            elif i == 15:
                condition_in = "fair"
            elif i == 16:
                condition_in = "poor"
            elif i == 17:
                condition_in = "damaged"
            elif i < 20:
                condition_in = "good"
            elif i == 20:
                condition_in = "new"
            elif i == 21:
                condition_in = "good"
            elif i < 25:
                condition_in = "new"
            elif i == 25:
                condition_in = "poor"
            else:
                condition_in = "fair"

            item.status = "returned"
            item.condition_in = condition_in
            if i == 17:
                item.damage_notes = "Cover torn, water stain on pages 12-15"
                bulk_checkout.items_damaged += 1

            returns_data.append({
                "barcode": item.barcode,
                "condition_out": item.condition_out,
                "condition_in": condition_in,
            })
            bulk_checkout.items_returned += 1

        await db.flush()

        # Verify condition change detection
        condition_changed_items = []
        for item in bulk_items:
            if item.condition_out and item.condition_in and item.condition_out != item.condition_in:
                condition_changed_items.append(item)

        # Should be exactly 5 items with condition changes:
        # Item 15: good -> fair
        # Item 16: good -> poor
        # Item 17: good -> damaged
        # Item 21: new -> good
        # Item 25: fair -> poor
        assert len(condition_changed_items) == 5

        # Verify each flagged item
        flagged_barcodes = {item.barcode for item in condition_changed_items}
        assert bulk_items[15].barcode in flagged_barcodes
        assert bulk_items[16].barcode in flagged_barcodes
        assert bulk_items[17].barcode in flagged_barcodes
        assert bulk_items[21].barcode in flagged_barcodes
        assert bulk_items[25].barcode in flagged_barcodes

        # Verify specific transitions
        assert bulk_items[15].condition_out == "good"
        assert bulk_items[15].condition_in == "fair"
        assert bulk_items[17].condition_out == "good"
        assert bulk_items[17].condition_in == "damaged"
        assert bulk_items[17].damage_notes is not None
        assert bulk_items[21].condition_out == "new"
        assert bulk_items[21].condition_in == "good"

        # Verify damage count
        assert bulk_checkout.items_damaged == 1

        await db.commit()

    async def test_05_close_bulk_checkout_when_all_returned(
        self, db: AsyncSession, partner, catalog_items, item_copies
    ):
        """Step 5: Close the bulk checkout when all items are returned."""
        today = date.today()
        due = today + timedelta(weeks=6)

        # Setup checkout
        bulk_checkout = BulkCheckout(
            partner_id=partner.id,
            checkout_name="Mrs. Thompson's 3rd Grade - Full Return Test",
            status=BulkCheckoutStatus.ACTIVE.value,
            requestor_name="Mrs. Thompson",
            checkout_date=today,
            due_date=due,
            total_items=0,
            items_returned=0,
            items_lost=0,
            items_damaged=0,
            processed_by_id=partner.created_by_id,
        )
        db.add(bulk_checkout)
        await db.flush()
        checkout_id = bulk_checkout.id

        # Add all 30 items
        bulk_items = []
        for i, copy in enumerate(item_copies):
            item = BulkCheckoutItem(
                bulk_checkout_id=checkout_id,
                item_copy_id=copy.id,
                barcode=copy.barcode,
                condition_out="good",
                status="checked_out",
            )
            db.add(item)
            bulk_items.append(item)
        bulk_checkout.total_items = 30
        await db.flush()

        # Return items in batches (simulating real-world returns)
        # Batch 1: return first 15 items
        for i in range(15):
            bulk_items[i].status = "returned"
            bulk_items[i].condition_in = "good"
            bulk_checkout.items_returned += 1

        # After partial return, should be partially returned
        bulk_checkout.status = BulkCheckoutStatus.PARTIALLY_RETURNED.value
        await db.flush()
        assert bulk_checkout.status == BulkCheckoutStatus.PARTIALLY_RETURNED.value
        assert bulk_checkout.items_returned == 15

        # Batch 2: return next 10 items
        for i in range(15, 25):
            bulk_items[i].status = "returned"
            bulk_items[i].condition_in = "good"
            bulk_checkout.items_returned += 1

        await db.flush()
        assert bulk_checkout.items_returned == 25
        assert bulk_checkout.status == BulkCheckoutStatus.PARTIALLY_RETURNED.value

        # Batch 3: return final 5 items
        for i in range(25, 30):
            bulk_items[i].status = "returned"
            bulk_items[i].condition_in = "good"
            bulk_checkout.items_returned += 1

        # All items returned - close the checkout
        assert bulk_checkout.items_returned + bulk_checkout.items_lost >= bulk_checkout.total_items
        bulk_checkout.status = BulkCheckoutStatus.RETURNED.value
        bulk_checkout.returned_date = date.today()
        await db.flush()

        # Verify final state
        assert bulk_checkout.status == BulkCheckoutStatus.RETURNED.value
        assert bulk_checkout.items_returned == 30
        assert bulk_checkout.total_items == 30
        assert bulk_checkout.returned_date is not None
        assert bulk_checkout.items_lost == 0
        assert bulk_checkout.items_damaged == 0

        # Verify all items show as returned
        for item in bulk_items:
            assert item.status == "returned"
            assert item.condition_in is not None

        await db.commit()

        # Verify persistence
        query = select(BulkCheckout).where(BulkCheckout.id == checkout_id)
        result = await db.execute(query)
        saved_checkout = result.scalar_one()
        assert saved_checkout.status == BulkCheckoutStatus.RETURNED.value
        assert saved_checkout.items_returned == 30

    async def test_06_complete_end_to_end_workflow(
        self, db: AsyncSession, partner, catalog_items, item_copies
    ):
        """Complete end-to-end workflow: create, add items, return with condition tracking, close."""
        today = date.today()
        due = today + timedelta(weeks=6)

        # --- STEP 1: Create bulk checkout ---
        bulk_checkout = BulkCheckout(
            partner_id=partner.id,
            checkout_name="Mrs. Thompson's 3rd Grade - E2E Test",
            status=BulkCheckoutStatus.ACTIVE.value,
            requestor_name="Mrs. Thompson",
            requestor_email="thompson@sce.edu",
            classroom_name="Room 204",
            grade_level="3",
            checkout_date=today,
            due_date=due,
            total_items=0,
            items_returned=0,
            items_lost=0,
            items_damaged=0,
            topic_requests=["fiction", "adventure"],
            delivery_method="pickup",
            pickup_location="Main Branch",
            processed_by_id=partner.created_by_id,
        )
        db.add(bulk_checkout)
        await db.flush()
        checkout_id = bulk_checkout.id
        assert bulk_checkout.status == BulkCheckoutStatus.ACTIVE.value

        # --- STEP 2: Add 30 items with condition_out ---
        bulk_items = []
        for i, copy in enumerate(item_copies):
            cond = "new" if i < 5 else "good" if i < 22 else "fair"
            item = BulkCheckoutItem(
                bulk_checkout_id=checkout_id,
                item_copy_id=copy.id,
                barcode=copy.barcode,
                title=copy.catalog_item.title if copy.catalog_item else None,
                call_number=copy.catalog_item.call_number if copy.catalog_item else None,
                condition_out=cond,
                replacement_cost=float(copy.replacement_cost) if copy.replacement_cost else None,
                status="checked_out",
            )
            db.add(item)
            bulk_items.append(item)

        bulk_checkout.total_items = 30
        await db.flush()
        assert bulk_checkout.total_items == 30
        assert all(item.condition_out is not None for item in bulk_items)

        # --- STEP 3: Return items individually with condition_in ---
        # Most come back same condition, a few degraded
        condition_changes_expected = 0
        damaged_count = 0
        for i, item in enumerate(bulk_items):
            item.status = "returned"
            if i == 3:
                # new -> good (wear from classroom use)
                item.condition_in = "good"
                condition_changes_expected += 1
            elif i == 10:
                # good -> fair (dog-eared, worn spine)
                item.condition_in = "fair"
                condition_changes_expected += 1
            elif i == 18:
                # good -> damaged (spilled juice)
                item.condition_in = "damaged"
                item.damage_notes = "Juice spill on pages 30-45, warped binding"
                condition_changes_expected += 1
                damaged_count += 1
            elif i == 24:
                # fair -> poor (torn pages)
                item.condition_in = "poor"
                condition_changes_expected += 1
            else:
                item.condition_in = item.condition_out  # same condition

            bulk_checkout.items_returned += 1

        bulk_checkout.items_damaged = damaged_count
        await db.flush()

        # --- STEP 4: Verify condition changes are flagged ---
        changed = [
            item for item in bulk_items
            if item.condition_out and item.condition_in
            and item.condition_out != item.condition_in
        ]
        assert len(changed) == condition_changes_expected
        assert len(changed) == 4

        # Verify specific items that changed
        assert bulk_items[3].condition_out == "new"
        assert bulk_items[3].condition_in == "good"
        assert bulk_items[10].condition_out == "good"
        assert bulk_items[10].condition_in == "fair"
        assert bulk_items[18].condition_out == "good"
        assert bulk_items[18].condition_in == "damaged"
        assert bulk_items[18].damage_notes is not None
        assert bulk_items[24].condition_out == "fair"
        assert bulk_items[24].condition_in == "poor"

        # Items without condition changes should NOT be flagged
        assert bulk_items[0].condition_out == bulk_items[0].condition_in
        assert bulk_items[5].condition_out == bulk_items[5].condition_in
        assert bulk_items[29].condition_out == bulk_items[29].condition_in

        # --- STEP 5: Close when all returned ---
        assert bulk_checkout.items_returned == 30
        assert bulk_checkout.items_returned + bulk_checkout.items_lost >= bulk_checkout.total_items

        bulk_checkout.status = BulkCheckoutStatus.RETURNED.value
        bulk_checkout.returned_date = date.today()
        await db.flush()

        assert bulk_checkout.status == BulkCheckoutStatus.RETURNED.value
        assert bulk_checkout.returned_date is not None
        assert bulk_checkout.items_returned == 30
        assert bulk_checkout.items_damaged == 1
        assert bulk_checkout.items_lost == 0

        await db.commit()

        # Final verification from database
        query = select(BulkCheckout).where(BulkCheckout.id == checkout_id)
        result = await db.execute(query)
        final = result.scalar_one()
        assert final.status == BulkCheckoutStatus.RETURNED.value
        assert final.total_items == 30
        assert final.items_returned == 30
        assert final.items_damaged == 1

        # Verify items in database
        items_query = select(BulkCheckoutItem).where(
            BulkCheckoutItem.bulk_checkout_id == checkout_id
        )
        items_result = await db.execute(items_query)
        saved_items = items_result.scalars().all()
        assert len(saved_items) == 30

        all_returned = all(i.status == "returned" for i in saved_items)
        assert all_returned

        flagged = [
            i for i in saved_items
            if i.condition_out and i.condition_in and i.condition_out != i.condition_in
        ]
        assert len(flagged) == 4


@pytest.mark.asyncio
class TestBulkCheckoutSchemaConditionTracking:
    """Test the enhanced schema supports condition_out in add items."""

    async def test_bulk_checkout_item_add_with_items_field(self, db: AsyncSession):
        """Test using the new 'items' field with condition_out per item."""
        from app.schemas.outreach import BulkCheckoutItemAdd, BulkCheckoutItemAddEntry

        # Test using the new items field
        add_data = BulkCheckoutItemAdd(
            items=[
                BulkCheckoutItemAddEntry(barcode="TEST-001", condition_out="good"),
                BulkCheckoutItemAddEntry(barcode="TEST-002", condition_out="new"),
                BulkCheckoutItemAddEntry(barcode="TEST-003", condition_out="fair"),
            ]
        )

        entries = add_data.get_entries()
        assert len(entries) == 3
        assert entries[0].barcode == "TEST-001"
        assert entries[0].condition_out == "good"
        assert entries[1].condition_out == "new"
        assert entries[2].condition_out == "fair"

    async def test_bulk_checkout_item_add_backwards_compatible(self, db: AsyncSession):
        """Test that legacy 'barcodes' field still works."""
        from app.schemas.outreach import BulkCheckoutItemAdd

        add_data = BulkCheckoutItemAdd(
            barcodes=["TEST-001", "TEST-002", "TEST-003"]
        )

        entries = add_data.get_entries()
        assert len(entries) == 3
        assert entries[0].barcode == "TEST-001"
        assert entries[0].condition_out is None  # No condition when using legacy field

    async def test_condition_changed_flag_in_response(self, db: AsyncSession):
        """Test that condition_changed is properly computed in response."""
        from app.schemas.outreach import BulkCheckoutItemResponse

        # Item with condition change
        response_changed = BulkCheckoutItemResponse(
            id=1,
            bulk_checkout_id=1,
            barcode="TEST-001",
            status="returned",
            condition_out="good",
            condition_in="fair",
            condition_changed=True,
            fine_amount=0.0,
            created_at="2026-02-26T00:00:00",
        )
        assert response_changed.condition_changed is True

        # Item without condition change
        response_same = BulkCheckoutItemResponse(
            id=2,
            bulk_checkout_id=1,
            barcode="TEST-002",
            status="returned",
            condition_out="good",
            condition_in="good",
            condition_changed=False,
            fine_amount=0.0,
            created_at="2026-02-26T00:00:00",
        )
        assert response_same.condition_changed is False
