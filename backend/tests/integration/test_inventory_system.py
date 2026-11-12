# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive integration tests for the LSC Inventory System.

Proves that the full inventory lifecycle works correctly:
- Item copy CRUD (create, read, update, list)
- Barcode generation and lookup
- Condition tracking with valid/invalid transitions
- Condition change audit trail
- Repair workflow (only way to improve condition)
- Withdrawal workflow (terminal state)
- Inventory audit sessions (create, scan, misplacement detection, completion)
- Concurrency guards (duplicate barcode, duplicate scan)

Each test exercises the inventory API functions directly with a real
(SQLite-backed) database, using the same code paths as production.
"""

import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.v1.inventory import (
    complete_audit,
    create_audit,
    create_copy,
    get_condition_history,
    get_copy,
    list_copies,
    log_condition_change,
    lookup_barcode,
    repair_copy,
    scan_item,
    update_copy,
    withdraw_copy,
)
from app.core.branding import branding
from app.models.inventory import (
    ConditionChange,
    ItemCondition,
    ItemCopy,
)
from app.schemas.inventory import (
    AuditCreate,
    AuditScanCreate,
    ConditionChangeCreate,
    ItemCopyCreate,
    ItemCopyUpdate,
    RepairRequest,
    WithdrawRequest,
)


# ---------------------------------------------------------------------------
# Helpers: unique emails/barcodes per test to avoid cross-test collisions
# ---------------------------------------------------------------------------

def _uid() -> str:
    return uuid.uuid4().hex[:8]


async def _make_staff(db):
    """Create a staff user with a unique email."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email=f"staff-{_uid()}@test.local",
        password_hash=hash_password("TestPass123!"),
        first_name="Staff",
        last_name="Test",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _make_catalog_item(db):
    """Create a catalog item with a unique ISBN."""
    from app.models.catalog import CatalogItem, ItemStatus

    item = CatalogItem(
        title=f"Test Book {_uid()}",
        author="Test Author",
        isbn=f"978-{_uid()}",
        description="A test book",
        status=ItemStatus.available,
        call_number=f"T-{_uid()}",
        publication_year=2024,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def _make_copy(db, staff, catalog_item, barcode=None, condition=ItemCondition.GOOD, location=None):
    """Shorthand to create a copy via the API."""
    return await create_copy(
        ItemCopyCreate(
            catalog_item_id=catalog_item.id,
            barcode=barcode or f"BC-{_uid()}",
            condition=condition,
            location=location,
        ),
        db=db,
        current_user=staff,
    )


# ===========================================================================
# 1. Item Copy Creation
# ===========================================================================


@pytest.mark.integration
class TestItemCopyCreation:
    """Prove that item copies can be created with correct defaults and validation."""

    async def test_create_copy_with_explicit_barcode(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)

        explicit_barcode = f"EXPLICIT-BC-{_uid()}"
        copy = await create_copy(
            ItemCopyCreate(
                catalog_item_id=cat.id,
                barcode=explicit_barcode,
                condition=ItemCondition.NEW,
                location="Children's Room B-2",
                replacement_cost=Decimal("15.50"),
            ),
            db=test_db,
            current_user=staff,
        )
        assert copy.id is not None
        assert copy.barcode == explicit_barcode
        assert copy.condition == ItemCondition.NEW
        assert copy.location == "Children's Room B-2"
        assert copy.copy_number == 1
        assert copy.catalog_item_id == cat.id

    async def test_create_copy_auto_barcode(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)

        copy = await create_copy(
            ItemCopyCreate(
                catalog_item_id=cat.id,
                barcode="",
                condition=ItemCondition.GOOD,
            ),
            db=test_db,
            current_user=staff,
        )
        assert copy.barcode.startswith(f"{branding.CARD_PREFIX}-")
        assert len(copy.barcode) == len(branding.CARD_PREFIX) + 9  # prefix + "-" + 8 hex

    async def test_create_multiple_copies_increments_copy_number(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)

        c1 = await _make_copy(test_db, staff, cat, barcode=f"M1-{_uid()}")
        c2 = await _make_copy(test_db, staff, cat, barcode=f"M2-{_uid()}")
        c3 = await _make_copy(test_db, staff, cat, barcode=f"M3-{_uid()}")
        assert c1.copy_number == 1
        assert c2.copy_number == 2
        assert c3.copy_number == 3

    async def test_create_copy_duplicate_barcode_rejected(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        bc = f"DUP-{_uid()}"

        await _make_copy(test_db, staff, cat, barcode=bc)

        with pytest.raises(HTTPException) as exc_info:
            await _make_copy(test_db, staff, cat, barcode=bc)
        assert exc_info.value.status_code == 400
        assert "Barcode already exists" in str(exc_info.value.detail)

    async def test_create_copy_nonexistent_catalog_item_rejected(self, test_db):
        staff = await _make_staff(test_db)

        with pytest.raises(HTTPException) as exc_info:
            await create_copy(
                ItemCopyCreate(
                    catalog_item_id=999999,
                    barcode=f"GHOST-{_uid()}",
                    condition=ItemCondition.GOOD,
                ),
                db=test_db,
                current_user=staff,
            )
        assert exc_info.value.status_code == 404


# ===========================================================================
# 2. Item Copy Read & List
# ===========================================================================


@pytest.mark.integration
class TestItemCopyReadAndList:
    """Prove that copies can be retrieved individually and listed with filters."""

    async def test_get_copy_by_id(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat, barcode=f"GET-{_uid()}")

        fetched = await get_copy(copy.id, db=test_db, current_user=staff)
        assert fetched.id == copy.id
        assert fetched.barcode == copy.barcode

    async def test_get_copy_not_found(self, test_db):
        staff = await _make_staff(test_db)

        with pytest.raises(HTTPException) as exc_info:
            await get_copy(999999, db=test_db, current_user=staff)
        assert exc_info.value.status_code == 404

    async def test_list_copies_returns_all(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)

        for _ in range(3):
            await _make_copy(test_db, staff, cat, location="Shelf A")

        result = await list_copies(
            catalog_item_id=None, condition=None, location=None, page=1, per_page=20,
            db=test_db, current_user=staff
        )
        assert result.total >= 3

    async def test_list_copies_filter_by_condition(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)

        bc_new = f"COND-NEW-{_uid()}"
        bc_fair = f"COND-FAIR-{_uid()}"
        await _make_copy(test_db, staff, cat, barcode=bc_new, condition=ItemCondition.NEW)
        await _make_copy(test_db, staff, cat, barcode=bc_fair, condition=ItemCondition.FAIR)

        result = await list_copies(
            catalog_item_id=None, condition=ItemCondition.NEW, location=None, page=1, per_page=20,
            db=test_db, current_user=staff
        )
        barcodes = [item.barcode for item in result.items]
        assert bc_new in barcodes
        assert bc_fair not in barcodes

    async def test_list_copies_filter_by_location(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)

        bc = f"LOC-REF-{_uid()}"
        await _make_copy(test_db, staff, cat, barcode=bc, location="Reference Desk")

        result = await list_copies(
            catalog_item_id=None, condition=None, location="Reference", page=1, per_page=20,
            db=test_db, current_user=staff
        )
        barcodes = [item.barcode for item in result.items]
        assert bc in barcodes


# ===========================================================================
# 3. Barcode Lookup
# ===========================================================================


@pytest.mark.integration
class TestBarcodeLookup:

    async def test_lookup_existing_barcode(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        bc = f"LOOK-{_uid()}"
        copy = await _make_copy(test_db, staff, cat, barcode=bc)

        found = await lookup_barcode(bc, db=test_db, current_user=staff)
        assert found.id == copy.id

    async def test_lookup_nonexistent_barcode(self, test_db):
        staff = await _make_staff(test_db)

        with pytest.raises(HTTPException) as exc_info:
            await lookup_barcode("DOES-NOT-EXIST", db=test_db, current_user=staff)
        assert exc_info.value.status_code == 404


# ===========================================================================
# 4. Item Copy Update
# ===========================================================================


@pytest.mark.integration
class TestItemCopyUpdate:

    async def test_update_location(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat)

        updated = await update_copy(
            copy.id, ItemCopyUpdate(location="Young Adult Section C-3"),
            db=test_db, current_user=staff,
        )
        assert updated.location == "Young Adult Section C-3"

    async def test_update_notes(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat)

        updated = await update_copy(
            copy.id, ItemCopyUpdate(notes="Spine label needs replacement"),
            db=test_db, current_user=staff,
        )
        assert updated.notes == "Spine label needs replacement"

    async def test_update_condition_creates_audit_trail(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat, condition=ItemCondition.GOOD)

        await update_copy(
            copy.id, ItemCopyUpdate(condition=ItemCondition.FAIR),
            db=test_db, current_user=staff,
        )

        result = await test_db.execute(
            select(ConditionChange).where(ConditionChange.item_copy_id == copy.id)
        )
        changes = result.scalars().all()
        assert len(changes) == 1
        assert changes[0].previous_condition == ItemCondition.GOOD
        assert changes[0].new_condition == ItemCondition.FAIR


# ===========================================================================
# 5. Condition Transitions (State Machine)
# ===========================================================================


@pytest.mark.integration
class TestConditionTransitions:

    async def test_valid_degradation_path(self, test_db):
        """NEW -> GOOD -> FAIR -> POOR -> DAMAGED -> WITHDRAWN is the full degradation path."""
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat, condition=ItemCondition.NEW)

        for cond in [ItemCondition.GOOD, ItemCondition.FAIR, ItemCondition.POOR,
                     ItemCondition.DAMAGED, ItemCondition.WITHDRAWN]:
            await log_condition_change(
                copy.id, ConditionChangeCreate(new_condition=cond),
                db=test_db, current_user=staff,
            )

        db_copy = await test_db.get(ItemCopy, copy.id)
        assert db_copy.condition == ItemCondition.WITHDRAWN

    async def test_skip_condition_allowed(self, test_db):
        """Can skip levels (e.g., NEW -> DAMAGED)."""
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat, condition=ItemCondition.NEW)

        result = await log_condition_change(
            copy.id, ConditionChangeCreate(new_condition=ItemCondition.DAMAGED),
            db=test_db, current_user=staff,
        )
        assert result.new_condition == ItemCondition.DAMAGED

    async def test_cannot_improve_condition_without_repair(self, test_db):
        """Condition improvements (FAIR -> GOOD) require the repair endpoint."""
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat, condition=ItemCondition.FAIR)

        with pytest.raises(HTTPException) as exc_info:
            await log_condition_change(
                copy.id, ConditionChangeCreate(new_condition=ItemCondition.GOOD),
                db=test_db, current_user=staff,
            )
        assert exc_info.value.status_code == 400
        assert "repair endpoint" in str(exc_info.value.detail)

    async def test_withdrawn_is_terminal(self, test_db):
        """Withdrawn items cannot transition to any other state."""
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat, condition=ItemCondition.NEW)
        await withdraw_copy(
            copy.id, WithdrawRequest(reason="Beyond repair"),
            db=test_db, current_user=staff,
        )

        with pytest.raises(HTTPException) as exc_info:
            await log_condition_change(
                copy.id, ConditionChangeCreate(new_condition=ItemCondition.GOOD),
                db=test_db, current_user=staff,
            )
        assert exc_info.value.status_code == 400
        assert "withdrawn" in str(exc_info.value.detail).lower()


# ===========================================================================
# 6. Condition Change History
# ===========================================================================


@pytest.mark.integration
class TestConditionHistory:

    async def test_condition_history_tracks_all_changes(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat, condition=ItemCondition.NEW)

        await log_condition_change(
            copy.id, ConditionChangeCreate(new_condition=ItemCondition.GOOD),
            db=test_db, current_user=staff,
        )
        await log_condition_change(
            copy.id,
            ConditionChangeCreate(new_condition=ItemCondition.FAIR, damage_description="Minor scuffing"),
            db=test_db, current_user=staff,
        )
        await log_condition_change(
            copy.id,
            ConditionChangeCreate(new_condition=ItemCondition.DAMAGED, damage_description="Water damage"),
            db=test_db, current_user=staff,
        )

        history = await get_condition_history(copy.id, db=test_db, current_user=staff)
        assert len(history) == 3
        conditions = [(h["previous_condition"], h["new_condition"]) for h in history]
        assert (ItemCondition.FAIR, ItemCondition.DAMAGED) in conditions
        assert (ItemCondition.GOOD, ItemCondition.FAIR) in conditions
        assert (ItemCondition.NEW, ItemCondition.GOOD) in conditions

    async def test_condition_history_tolerates_off_enum_damage_type(self, test_db):
        """Regression: a row whose damage_type is outside the DamageType
        enum (legacy/seed data written straight to the free-text column) must
        not 500 the condition-history endpoint."""
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat, condition=ItemCondition.GOOD)

        # Insert directly: the API write path validates against DamageType, but
        # the column is free-text String(50) and seeds can write junk values.
        test_db.add(
            ConditionChange(
                item_copy_id=copy.id,
                previous_condition=ItemCondition.GOOD,
                new_condition=ItemCondition.FAIR,
                damage_type="media",
                reported_by_id=staff.id,
            )
        )
        await test_db.commit()

        history = await get_condition_history(copy.id, db=test_db, current_user=staff)
        assert len(history) == 1
        assert history[0]["damage_type"] is None


# ===========================================================================
# 7. Repair Workflow
# ===========================================================================


@pytest.mark.integration
class TestRepairWorkflow:

    async def test_repair_damaged_to_good(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat, condition=ItemCondition.DAMAGED)

        repaired = await repair_copy(
            copy.id,
            RepairRequest(new_condition=ItemCondition.GOOD, repair_notes="Rebound spine", repair_cost=Decimal("12.50")),
            db=test_db, current_user=staff,
        )
        assert repaired.condition == ItemCondition.GOOD

    async def test_repair_poor_to_fair(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat, condition=ItemCondition.POOR)

        repaired = await repair_copy(
            copy.id,
            RepairRequest(new_condition=ItemCondition.FAIR, repair_notes="Cleaned pages"),
            db=test_db, current_user=staff,
        )
        assert repaired.condition == ItemCondition.FAIR

    async def test_repair_creates_condition_change_record(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat, condition=ItemCondition.DAMAGED)

        await repair_copy(
            copy.id,
            RepairRequest(new_condition=ItemCondition.GOOD, repair_notes="Full restoration", repair_cost=Decimal("25.00")),
            db=test_db, current_user=staff,
        )

        result = await test_db.execute(
            select(ConditionChange).where(ConditionChange.item_copy_id == copy.id)
        )
        changes = result.scalars().all()
        assert len(changes) == 1
        assert changes[0].previous_condition == ItemCondition.DAMAGED
        assert changes[0].new_condition == ItemCondition.GOOD
        assert changes[0].repair_notes == "Full restoration"
        assert changes[0].repair_cost == Decimal("25.00")
        assert changes[0].repaired_at is not None

    async def test_repair_cannot_worsen_condition(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat, condition=ItemCondition.FAIR)

        with pytest.raises(HTTPException) as exc_info:
            await repair_copy(
                copy.id,
                RepairRequest(new_condition=ItemCondition.POOR, repair_notes="This should fail"),
                db=test_db, current_user=staff,
            )
        assert exc_info.value.status_code == 400


# ===========================================================================
# 8. Withdrawal Workflow
# ===========================================================================


@pytest.mark.integration
class TestWithdrawalWorkflow:

    async def test_withdraw_sets_condition_to_withdrawn(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat, condition=ItemCondition.POOR)

        withdrawn = await withdraw_copy(
            copy.id, WithdrawRequest(reason="Outdated content"),
            db=test_db, current_user=staff,
        )
        assert withdrawn.condition == ItemCondition.WITHDRAWN
        assert "Withdrawn: Outdated content" in (withdrawn.notes or "")

    async def test_withdraw_creates_condition_change(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat, condition=ItemCondition.DAMAGED)

        await withdraw_copy(
            copy.id, WithdrawRequest(reason="Damaged beyond repair"),
            db=test_db, current_user=staff,
        )

        result = await test_db.execute(
            select(ConditionChange).where(ConditionChange.item_copy_id == copy.id)
        )
        changes = result.scalars().all()
        assert len(changes) == 1
        assert changes[0].new_condition == ItemCondition.WITHDRAWN

    async def test_withdraw_twice_rejected(self, test_db):
        """Withdrawing an already-withdrawn item is rejected (no duplicate records)."""
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        copy = await _make_copy(test_db, staff, cat, condition=ItemCondition.GOOD)

        await withdraw_copy(
            copy.id, WithdrawRequest(reason="First withdrawal"),
            db=test_db, current_user=staff,
        )

        changes_before = (await test_db.execute(
            select(ConditionChange).where(ConditionChange.item_copy_id == copy.id)
        )).scalars().all()
        count_before = len(changes_before)

        # Second withdrawal is blocked by the already-withdrawn guard.
        with pytest.raises(HTTPException) as exc_info:
            await withdraw_copy(
                copy.id, WithdrawRequest(reason="Second attempt"),
                db=test_db, current_user=staff,
            )
        assert exc_info.value.status_code == 400
        assert "already withdrawn" in str(exc_info.value.detail).lower()

        changes_after = (await test_db.execute(
            select(ConditionChange).where(ConditionChange.item_copy_id == copy.id)
        )).scalars().all()
        assert len(changes_after) == count_before, (
            "Rejected withdrawal must not add a ConditionChange record"
        )


# ===========================================================================
# 9. Inventory Audit Sessions
# ===========================================================================


@pytest.mark.integration
class TestInventoryAudit:

    async def test_create_audit(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)

        for _ in range(3):
            await _make_copy(test_db, staff, cat, location="Main Floor")

        audit = await create_audit(
            AuditCreate(name="Q1 2026 Audit", location_filter="Main Floor"),
            db=test_db, current_user=staff,
        )
        assert audit.id is not None
        assert audit.name == "Q1 2026 Audit"
        assert audit.items_expected >= 3
        assert audit.items_found == 0
        assert audit.completed_at is None

    async def test_scan_item_increments_count(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        bc = f"SCAN-{_uid()}"
        copy = await _make_copy(test_db, staff, cat, barcode=bc, location="Shelf A")

        audit = await create_audit(
            AuditCreate(name="Scan Test"), db=test_db, current_user=staff,
        )
        scan = await scan_item(
            audit.id, AuditScanCreate(barcode=bc, found_at_location="Shelf A"),
            db=test_db, current_user=staff,
        )
        assert scan.item_copy_id == copy.id
        assert scan.is_misplaced is False

        await test_db.refresh(audit)
        assert audit.items_found == 1

    async def test_scan_detects_misplaced_item(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        bc = f"MIS-{_uid()}"
        await _make_copy(test_db, staff, cat, barcode=bc, location="Shelf A")

        audit = await create_audit(
            AuditCreate(name="Misplace Audit"), db=test_db, current_user=staff,
        )
        scan = await scan_item(
            audit.id, AuditScanCreate(barcode=bc, found_at_location="Shelf Z"),
            db=test_db, current_user=staff,
        )
        assert scan.is_misplaced is True
        await test_db.refresh(audit)
        assert audit.items_misplaced == 1

    async def test_duplicate_scan_rejected(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        bc = f"DSCAN-{_uid()}"
        await _make_copy(test_db, staff, cat, barcode=bc)

        audit = await create_audit(
            AuditCreate(name="Dup Scan"), db=test_db, current_user=staff,
        )
        await scan_item(
            audit.id, AuditScanCreate(barcode=bc), db=test_db, current_user=staff,
        )

        with pytest.raises(HTTPException) as exc_info:
            await scan_item(
                audit.id, AuditScanCreate(barcode=bc), db=test_db, current_user=staff,
            )
        assert exc_info.value.status_code == 400
        assert "already scanned" in str(exc_info.value.detail).lower()

    async def test_complete_audit_calculates_missing(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)

        barcodes = [f"COMP-{_uid()}" for _ in range(3)]
        for bc in barcodes:
            await _make_copy(test_db, staff, cat, barcode=bc)

        audit = await create_audit(
            AuditCreate(name="Completion Audit"), db=test_db, current_user=staff,
        )

        # Scan only first 2
        for bc in barcodes[:2]:
            await scan_item(
                audit.id, AuditScanCreate(barcode=bc), db=test_db, current_user=staff,
            )

        completed = await complete_audit(audit.id, db=test_db, current_user=staff)
        assert completed.completed_at is not None
        assert completed.items_found == 2
        assert completed.items_missing == completed.items_expected - 2

    async def test_cannot_scan_completed_audit(self, test_db):
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)
        bc = f"CLOSED-{_uid()}"
        await _make_copy(test_db, staff, cat, barcode=bc)

        audit = await create_audit(
            AuditCreate(name="Closed Audit"), db=test_db, current_user=staff,
        )
        await complete_audit(audit.id, db=test_db, current_user=staff)

        with pytest.raises(HTTPException) as exc_info:
            await scan_item(
                audit.id, AuditScanCreate(barcode=bc), db=test_db, current_user=staff,
            )
        assert exc_info.value.status_code == 400
        assert "completed" in str(exc_info.value.detail).lower()

    async def test_cannot_complete_audit_twice(self, test_db):
        staff = await _make_staff(test_db)

        audit = await create_audit(
            AuditCreate(name="Double Complete"), db=test_db, current_user=staff,
        )
        await complete_audit(audit.id, db=test_db, current_user=staff)

        with pytest.raises(HTTPException) as exc_info:
            await complete_audit(audit.id, db=test_db, current_user=staff)
        assert exc_info.value.status_code == 400


# ===========================================================================
# 10. End-to-End: Full Lifecycle
# ===========================================================================


@pytest.mark.integration
class TestFullInventoryLifecycle:

    async def test_full_lifecycle(self, test_db):
        """
        Simulate a complete item lifecycle:
        1. Create copy (NEW condition)
        2. Move to shelf (update location)
        3. Wear: NEW -> GOOD -> FAIR -> POOR -> DAMAGED
        4. Repair: DAMAGED -> GOOD
        5. More wear: GOOD -> FAIR
        6. Withdraw from circulation
        7. Add replacement copy
        8. Audit scans replacement
        9. Verify full history preserved
        """
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db)

        # 1. Create a new copy
        bc1 = f"LIFE-{_uid()}"
        copy = await create_copy(
            ItemCopyCreate(
                catalog_item_id=cat.id,
                barcode=bc1,
                condition=ItemCondition.NEW,
                location="New Arrivals Display",
                replacement_cost=Decimal("29.99"),
            ),
            db=test_db, current_user=staff,
        )
        assert copy.condition == ItemCondition.NEW
        assert copy.is_available is True

        # 2. Move to shelf
        await update_copy(
            copy.id, ItemCopyUpdate(location="Fiction Section F-7"),
            db=test_db, current_user=staff,
        )

        # 3. Wear and tear: NEW -> GOOD -> FAIR -> POOR -> DAMAGED
        for cond, desc in [
            (ItemCondition.GOOD, None),
            (ItemCondition.FAIR, "Minor cover scuffing"),
            (ItemCondition.POOR, "Pages yellowing, binding loose"),
            (ItemCondition.DAMAGED, "Spine broken, pages falling out"),
        ]:
            await log_condition_change(
                copy.id,
                ConditionChangeCreate(new_condition=cond, damage_description=desc),
                db=test_db, current_user=staff,
            )

        db_copy = await test_db.get(ItemCopy, copy.id)
        assert db_copy.is_available is False  # DAMAGED items not available

        # 4. Repair: DAMAGED -> GOOD
        repaired = await repair_copy(
            copy.id,
            RepairRequest(
                new_condition=ItemCondition.GOOD,
                repair_notes="Professional rebinding",
                repair_cost=Decimal("18.50"),
            ),
            db=test_db, current_user=staff,
        )
        assert repaired.condition == ItemCondition.GOOD
        assert repaired.is_available is True

        # 5. More wear: GOOD -> FAIR
        await log_condition_change(
            copy.id,
            ConditionChangeCreate(new_condition=ItemCondition.FAIR, damage_description="Normal wear"),
            db=test_db, current_user=staff,
        )

        # 6. Withdraw
        withdrawn = await withdraw_copy(
            copy.id, WithdrawRequest(reason="End of useful life"),
            db=test_db, current_user=staff,
        )
        assert withdrawn.condition == ItemCondition.WITHDRAWN
        assert withdrawn.is_available is False

        # 7. Add replacement
        bc2 = f"LIFE-{_uid()}"
        replacement = await create_copy(
            ItemCopyCreate(
                catalog_item_id=cat.id,
                barcode=bc2,
                condition=ItemCondition.NEW,
                location="Fiction Section F-7",
                replacement_cost=Decimal("32.99"),
            ),
            db=test_db, current_user=staff,
        )
        assert replacement.catalog_item_id == cat.id
        assert replacement.copy_number == 2

        # 8. Audit scans replacement
        audit = await create_audit(
            AuditCreate(name="Lifecycle Verification Audit"),
            db=test_db, current_user=staff,
        )
        scan = await scan_item(
            audit.id,
            AuditScanCreate(barcode=bc2, found_at_location="Fiction Section F-7"),
            db=test_db, current_user=staff,
        )
        assert scan.is_misplaced is False

        # 9. Verify full condition history on original copy
        history = await get_condition_history(copy.id, db=test_db, current_user=staff)
        # NEW->GOOD, GOOD->FAIR, FAIR->POOR, POOR->DAMAGED,
        # DAMAGED->GOOD (repair), GOOD->FAIR, FAIR->WITHDRAWN (withdraw)
        assert len(history) >= 7

        # Verify both copies exist with correct final states
        all_copies = await test_db.execute(
            select(ItemCopy)
            .where(ItemCopy.catalog_item_id == cat.id)
            .order_by(ItemCopy.copy_number)
        )
        copies = all_copies.scalars().all()
        assert len(copies) == 2
        assert copies[0].barcode == bc1
        assert copies[0].condition == ItemCondition.WITHDRAWN
        assert copies[1].barcode == bc2
        assert copies[1].condition == ItemCondition.NEW
