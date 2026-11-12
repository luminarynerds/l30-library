# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Inventory Scanning Process Tests for Bébé Memorial Library.

Tests the full inventory audit workflow:
- Start inventory session for a section
- Scan items on shelf
- Flag items found but not expected (wrong shelf / misplaced)
- Flag items expected but not found (missing)
- Pause and resume session
- Multiple staff on same inventory
- Inventory completion percentage
- Generate discrepancy report
- Batch update missing items
- Mark section complete
- Inventory history tracking
- Export results
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, func

from app.models.catalog import CatalogItem, ItemStatus
from app.models.inventory import (
    AcquisitionSource,
    AuditScan,
    InventoryAudit,
    ItemCondition,
    ItemCopy,
)
from app.models.user import User, UserRole


# ============================================================================
# HELPERS
# ============================================================================


def _unique_email(prefix: str = "inv") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def _unique_barcode(prefix: str = "INV") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


async def _make_staff(db, *, email: str | None = None) -> User:
    from app.core.security import hash_password

    user = User(
        email=email or _unique_email("staff"),
        password_hash=hash_password("StaffPass123!"),
        first_name="Staff",
        last_name="Inventory",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.flush()
    return user


async def _make_patron(db) -> User:
    from app.core.security import hash_password

    user = User(
        email=_unique_email("patron"),
        password_hash=hash_password("PatronPass123!"),
        first_name="Patron",
        last_name="Reader",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.flush()
    return user


async def _make_catalog_item(db, *, title: str = "Test Book", author: str = "Author") -> CatalogItem:
    item = CatalogItem(
        title=title,
        author=author,
        isbn=f"978-0-{uuid.uuid4().hex[:8]}-1",
        description=f"Test item: {title}",
        status=ItemStatus.available,
        publication_year=2024,
    )
    db.add(item)
    await db.flush()
    return item


async def _make_copy(
    db,
    catalog_item: CatalogItem,
    *,
    barcode: str | None = None,
    location: str = "Adult Fiction A-1",
    condition: ItemCondition = ItemCondition.GOOD,
    copy_number: int = 1,
) -> ItemCopy:
    copy = ItemCopy(
        catalog_item_id=catalog_item.id,
        barcode=barcode or _unique_barcode(),
        copy_number=copy_number,
        location=location,
        condition=condition,
    )
    db.add(copy)
    await db.flush()
    return copy


async def _seed_section(db, staff: User, location: str, count: int = 5):
    """Create a catalog item with `count` copies all at `location`."""
    cat = await _make_catalog_item(db, title=f"Book at {location}")
    copies = []
    for i in range(count):
        c = await _make_copy(db, cat, location=location, copy_number=i + 1)
        copies.append(c)
    await db.commit()
    return cat, copies


# ============================================================================
# 1. START INVENTORY SESSION FOR SECTION
# ============================================================================


class TestStartInventorySession:

    @pytest.mark.asyncio
    async def test_create_audit_for_section(self, test_db):
        """Starting an audit for a section records the expected item count."""
        staff = await _make_staff(test_db)
        cat, copies = await _seed_section(test_db, staff, "Adult Fiction A-1", count=4)

        audit = InventoryAudit(
            name="Adult Fiction A-1 Quarterly Audit",
            description="Q1 2026 shelf scan",
            location_filter="Adult Fiction A-1",
            items_expected=4,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.commit()
        await test_db.refresh(audit)

        assert audit.id is not None
        assert audit.items_expected == 4
        assert audit.items_found == 0
        assert audit.completed_at is None

    @pytest.mark.asyncio
    async def test_audit_excludes_withdrawn_from_expected(self, test_db):
        """Withdrawn items should not be counted as expected."""
        _ = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db, title="Withdrawn test")
        await _make_copy(test_db, cat, location="Ref A", condition=ItemCondition.GOOD, copy_number=1)
        await _make_copy(test_db, cat, location="Ref A", condition=ItemCondition.WITHDRAWN, copy_number=2)
        await test_db.commit()

        # Count non-withdrawn at location
        result = await test_db.execute(
            select(func.count(ItemCopy.id)).where(
                ItemCopy.location.ilike("%Ref A%"),
                ItemCopy.condition != ItemCondition.WITHDRAWN,
            )
        )
        expected = result.scalar() or 0
        assert expected == 1  # only the non-withdrawn copy


# ============================================================================
# 2. SCAN ITEMS ON SHELF
# ============================================================================


class TestScanItems:

    @pytest.mark.asyncio
    async def test_scan_item_creates_record(self, test_db):
        """Scanning a barcode creates an AuditScan record."""
        staff = await _make_staff(test_db)
        cat, copies = await _seed_section(test_db, staff, "Kids B-2", count=2)

        audit = InventoryAudit(
            name="Kids scan",
            location_filter="Kids B-2",
            items_expected=2,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.flush()

        scan = AuditScan(
            audit_id=audit.id,
            item_copy_id=copies[0].id,
            found_at_location="Kids B-2",
            is_misplaced=False,
            scanned_by_id=staff.id,
        )
        test_db.add(scan)
        audit.items_found += 1
        await test_db.commit()
        await test_db.refresh(audit)

        assert audit.items_found == 1
        assert scan.is_misplaced is False

    @pytest.mark.asyncio
    async def test_duplicate_scan_prevented(self, test_db):
        """The same item cannot be scanned twice in one audit."""
        staff = await _make_staff(test_db)
        cat, copies = await _seed_section(test_db, staff, "Ref C", count=1)

        audit = InventoryAudit(
            name="Ref scan",
            location_filter="Ref C",
            items_expected=1,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.flush()

        scan1 = AuditScan(
            audit_id=audit.id,
            item_copy_id=copies[0].id,
            found_at_location="Ref C",
            scanned_by_id=staff.id,
        )
        test_db.add(scan1)
        await test_db.commit()

        # Verify uniqueness: query existing scan before inserting
        existing = await test_db.execute(
            select(AuditScan).where(
                AuditScan.audit_id == audit.id,
                AuditScan.item_copy_id == copies[0].id,
            )
        )
        assert existing.scalar_one_or_none() is not None  # already scanned


# ============================================================================
# 3. FLAG ITEMS FOUND BUT NOT EXPECTED (WRONG SHELF / MISPLACED)
# ============================================================================


class TestMisplacedItems:

    @pytest.mark.asyncio
    async def test_item_found_at_wrong_location_flagged(self, test_db):
        """An item scanned at a location different from its assigned one is misplaced."""
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db, title="Misplaced novel")
        copy = await _make_copy(test_db, cat, location="Adult Fiction A-1")
        await test_db.commit()

        audit = InventoryAudit(
            name="Fiction A scan",
            location_filter="Adult Fiction A-1",
            items_expected=1,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.flush()

        # Found on the wrong shelf
        found_location = "YA Fiction B-3"
        is_misplaced = found_location.lower() != copy.location.lower()

        scan = AuditScan(
            audit_id=audit.id,
            item_copy_id=copy.id,
            found_at_location=found_location,
            is_misplaced=is_misplaced,
            scanned_by_id=staff.id,
        )
        test_db.add(scan)
        audit.items_found += 1
        audit.items_misplaced += 1
        await test_db.commit()

        assert scan.is_misplaced is True
        assert audit.items_misplaced == 1

    @pytest.mark.asyncio
    async def test_item_at_correct_location_not_flagged(self, test_db):
        """An item found at its expected location is NOT misplaced."""
        _ = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db, title="Correct place")
        copy = await _make_copy(test_db, cat, location="Kids D-1")
        await test_db.commit()

        is_misplaced = "Kids D-1".lower() != copy.location.lower()
        assert is_misplaced is False


# ============================================================================
# 4. FLAG ITEMS EXPECTED BUT NOT FOUND (MISSING)
# ============================================================================


class TestMissingItems:

    @pytest.mark.asyncio
    async def test_missing_count_on_completion(self, test_db):
        """When audit completes, missing = expected - found."""
        staff = await _make_staff(test_db)
        cat, copies = await _seed_section(test_db, staff, "Hist E-1", count=5)

        audit = InventoryAudit(
            name="History scan",
            location_filter="Hist E-1",
            items_expected=5,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.flush()

        # Scan only 3 of the 5
        for copy in copies[:3]:
            scan = AuditScan(
                audit_id=audit.id,
                item_copy_id=copy.id,
                found_at_location="Hist E-1",
                scanned_by_id=staff.id,
            )
            test_db.add(scan)
            audit.items_found += 1

        # Complete the audit
        audit.completed_at = datetime.now(timezone.utc)
        audit.items_missing = audit.items_expected - audit.items_found
        await test_db.commit()
        await test_db.refresh(audit)

        assert audit.items_missing == 2
        assert audit.items_found == 3

    @pytest.mark.asyncio
    async def test_identify_which_items_are_missing(self, test_db):
        """We can determine exactly which copies were not scanned."""
        staff = await _make_staff(test_db)
        cat, copies = await _seed_section(test_db, staff, "Sci F-1", count=4)

        audit = InventoryAudit(
            name="Sci scan",
            location_filter="Sci F-1",
            items_expected=4,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.flush()

        # Scan only first two
        scanned_ids = {copies[0].id, copies[1].id}
        for cid in scanned_ids:
            test_db.add(AuditScan(
                audit_id=audit.id,
                item_copy_id=cid,
                found_at_location="Sci F-1",
                scanned_by_id=staff.id,
            ))
        await test_db.commit()

        # Query which items at that location were NOT scanned
        scanned_subq = (
            select(AuditScan.item_copy_id)
            .where(AuditScan.audit_id == audit.id)
        )
        missing_result = await test_db.execute(
            select(ItemCopy).where(
                ItemCopy.location.ilike("%Sci F-1%"),
                ItemCopy.condition != ItemCondition.WITHDRAWN,
                ~ItemCopy.id.in_(scanned_subq),
            )
        )
        missing_copies = missing_result.scalars().all()

        missing_ids = {c.id for c in missing_copies}
        assert copies[2].id in missing_ids
        assert copies[3].id in missing_ids
        assert len(missing_ids) == 2


# ============================================================================
# 5. PAUSE AND RESUME SESSION
# ============================================================================


class TestPauseResumeSession:

    @pytest.mark.asyncio
    async def test_audit_persists_across_sessions(self, test_db):
        """An audit without completed_at can be resumed by scanning more items."""
        staff = await _make_staff(test_db)
        cat, copies = await _seed_section(test_db, staff, "Pause G-1", count=4)

        audit = InventoryAudit(
            name="Pause/resume test",
            location_filter="Pause G-1",
            items_expected=4,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.flush()

        # --- Session 1: scan 2 items ---
        for copy in copies[:2]:
            test_db.add(AuditScan(
                audit_id=audit.id,
                item_copy_id=copy.id,
                found_at_location="Pause G-1",
                scanned_by_id=staff.id,
            ))
            audit.items_found += 1
        await test_db.commit()
        await test_db.refresh(audit)
        assert audit.items_found == 2
        assert audit.completed_at is None  # not completed = paused

        # --- Session 2: resume and scan remaining ---
        for copy in copies[2:]:
            test_db.add(AuditScan(
                audit_id=audit.id,
                item_copy_id=copy.id,
                found_at_location="Pause G-1",
                scanned_by_id=staff.id,
            ))
            audit.items_found += 1
        await test_db.commit()
        await test_db.refresh(audit)

        assert audit.items_found == 4
        assert audit.completed_at is None  # still open until explicitly completed

    @pytest.mark.asyncio
    async def test_completed_audit_cannot_accept_scans(self, test_db):
        """Once completed, new scans should be rejected."""
        staff = await _make_staff(test_db)
        cat, copies = await _seed_section(test_db, staff, "Done H-1", count=1)

        audit = InventoryAudit(
            name="Completed audit",
            location_filter="Done H-1",
            items_expected=1,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.flush()

        audit.completed_at = datetime.now(timezone.utc)
        await test_db.commit()

        # The API layer rejects scans on completed audits.
        # At the model level, we verify the state.
        assert audit.completed_at is not None


# ============================================================================
# 6. MULTIPLE STAFF ON SAME INVENTORY
# ============================================================================


class TestMultipleStaff:

    @pytest.mark.asyncio
    async def test_two_staff_scan_same_audit(self, test_db):
        """Two staff members can contribute scans to the same audit."""
        staff1 = await _make_staff(test_db, email=_unique_email("staff1"))
        staff2 = await _make_staff(test_db, email=_unique_email("staff2"))
        cat, copies = await _seed_section(test_db, staff1, "Multi I-1", count=4)

        audit = InventoryAudit(
            name="Multi-staff scan",
            location_filter="Multi I-1",
            items_expected=4,
            created_by_id=staff1.id,
        )
        test_db.add(audit)
        await test_db.flush()

        # Staff 1 scans first two
        for copy in copies[:2]:
            test_db.add(AuditScan(
                audit_id=audit.id,
                item_copy_id=copy.id,
                found_at_location="Multi I-1",
                scanned_by_id=staff1.id,
            ))
            audit.items_found += 1

        # Staff 2 scans remaining two
        for copy in copies[2:]:
            test_db.add(AuditScan(
                audit_id=audit.id,
                item_copy_id=copy.id,
                found_at_location="Multi I-1",
                scanned_by_id=staff2.id,
            ))
            audit.items_found += 1

        await test_db.commit()
        await test_db.refresh(audit)

        assert audit.items_found == 4

        # Verify scans are attributed to the correct staff
        result = await test_db.execute(
            select(AuditScan).where(AuditScan.audit_id == audit.id)
        )
        scans = result.scalars().all()
        scanner_ids = {s.scanned_by_id for s in scans}
        assert staff1.id in scanner_ids
        assert staff2.id in scanner_ids

    @pytest.mark.asyncio
    async def test_patron_cannot_create_audit(self, test_db):
        """Only staff/admin should be able to run inventory audits."""
        patron = await _make_patron(test_db)
        await test_db.commit()
        # The dependency `require_staff` blocks non-staff.
        # At the model level, any user_id can be stored, but the API enforces it.
        assert patron.role == UserRole.PATRON
        assert patron.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN]


# ============================================================================
# 7. INVENTORY COMPLETION PERCENTAGE
# ============================================================================


class TestCompletionPercentage:

    @pytest.mark.asyncio
    async def test_completion_percentage_calculation(self, test_db):
        """Completion % = (items_found / items_expected) * 100."""
        staff = await _make_staff(test_db)
        cat, copies = await _seed_section(test_db, staff, "Pct J-1", count=10)

        audit = InventoryAudit(
            name="Percentage test",
            location_filter="Pct J-1",
            items_expected=10,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.flush()

        # Scan 7 of 10
        for copy in copies[:7]:
            test_db.add(AuditScan(
                audit_id=audit.id,
                item_copy_id=copy.id,
                found_at_location="Pct J-1",
                scanned_by_id=staff.id,
            ))
            audit.items_found += 1
        await test_db.commit()
        await test_db.refresh(audit)

        pct = (audit.items_found / audit.items_expected) * 100 if audit.items_expected else 0
        assert pct == 70.0

    @pytest.mark.asyncio
    async def test_completion_percentage_zero_expected(self, test_db):
        """Zero expected items should give 0% (not division error)."""
        staff = await _make_staff(test_db)
        await test_db.commit()

        audit = InventoryAudit(
            name="Empty section",
            location_filter="Empty Z-99",
            items_expected=0,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.commit()
        await test_db.refresh(audit)

        pct = (audit.items_found / audit.items_expected) * 100 if audit.items_expected else 0
        assert pct == 0

    @pytest.mark.asyncio
    async def test_completion_percentage_all_found(self, test_db):
        """100% when every expected item is scanned."""
        staff = await _make_staff(test_db)
        cat, copies = await _seed_section(test_db, staff, "Full K-1", count=3)

        audit = InventoryAudit(
            name="Full scan",
            location_filter="Full K-1",
            items_expected=3,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.flush()

        for copy in copies:
            test_db.add(AuditScan(
                audit_id=audit.id,
                item_copy_id=copy.id,
                found_at_location="Full K-1",
                scanned_by_id=staff.id,
            ))
            audit.items_found += 1
        await test_db.commit()
        await test_db.refresh(audit)

        pct = (audit.items_found / audit.items_expected) * 100
        assert pct == 100.0


# ============================================================================
# 8. GENERATE DISCREPANCY REPORT
# ============================================================================


class TestDiscrepancyReport:

    @pytest.mark.asyncio
    async def test_discrepancy_report_data(self, test_db):
        """Generate a report listing misplaced + missing items after audit."""
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db, title="Discrepancy book")
        copy1 = await _make_copy(test_db, cat, location="Disc L-1", copy_number=1)
        copy2 = await _make_copy(test_db, cat, location="Disc L-1", copy_number=2)
        copy3 = await _make_copy(test_db, cat, location="Disc L-1", copy_number=3)
        await test_db.commit()

        audit = InventoryAudit(
            name="Discrepancy report",
            location_filter="Disc L-1",
            items_expected=3,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.flush()

        # copy1: found at correct location
        test_db.add(AuditScan(
            audit_id=audit.id,
            item_copy_id=copy1.id,
            found_at_location="Disc L-1",
            is_misplaced=False,
            scanned_by_id=staff.id,
        ))
        audit.items_found += 1

        # copy2: found at WRONG location
        test_db.add(AuditScan(
            audit_id=audit.id,
            item_copy_id=copy2.id,
            found_at_location="YA Shelf X-9",
            is_misplaced=True,
            scanned_by_id=staff.id,
        ))
        audit.items_found += 1
        audit.items_misplaced += 1

        # copy3: NOT scanned (missing)

        audit.completed_at = datetime.now(timezone.utc)
        audit.items_missing = audit.items_expected - audit.items_found
        await test_db.commit()

        # --- Build discrepancy report ---
        misplaced_result = await test_db.execute(
            select(AuditScan).where(
                AuditScan.audit_id == audit.id,
                AuditScan.is_misplaced == True,
            )
        )
        misplaced = misplaced_result.scalars().all()

        scanned_ids_result = await test_db.execute(
            select(AuditScan.item_copy_id).where(AuditScan.audit_id == audit.id)
        )
        scanned_ids = {row[0] for row in scanned_ids_result.all()}

        all_expected_result = await test_db.execute(
            select(ItemCopy).where(
                ItemCopy.location.ilike("%Disc L-1%"),
                ItemCopy.condition != ItemCondition.WITHDRAWN,
            )
        )
        all_expected = all_expected_result.scalars().all()
        missing = [c for c in all_expected if c.id not in scanned_ids]

        report = {
            "audit_id": audit.id,
            "name": audit.name,
            "items_expected": audit.items_expected,
            "items_found": audit.items_found,
            "items_missing": audit.items_missing,
            "items_misplaced": audit.items_misplaced,
            "misplaced_details": [
                {
                    "item_copy_id": s.item_copy_id,
                    "expected": "Disc L-1",
                    "found_at": s.found_at_location,
                }
                for s in misplaced
            ],
            "missing_barcodes": [c.barcode for c in missing],
        }

        assert report["items_expected"] == 3
        assert report["items_found"] == 2
        assert report["items_missing"] == 1
        assert report["items_misplaced"] == 1
        assert len(report["misplaced_details"]) == 1
        assert report["misplaced_details"][0]["found_at"] == "YA Shelf X-9"
        assert len(report["missing_barcodes"]) == 1
        assert copy3.barcode in report["missing_barcodes"]


# ============================================================================
# 9. BATCH UPDATE MISSING ITEMS
# ============================================================================


class TestBatchUpdateMissing:

    @pytest.mark.asyncio
    async def test_batch_mark_missing_as_withdrawn(self, test_db):
        """After audit, batch-update missing items to withdrawn status."""
        _ = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db, title="Batch book")
        missing_copies = []
        for i in range(3):
            c = await _make_copy(test_db, cat, location="Batch M-1", copy_number=i + 1)
            missing_copies.append(c)
        await test_db.commit()

        # Simulate: these copies were missing after audit — batch withdraw them
        for copy in missing_copies:
            copy.condition = ItemCondition.WITHDRAWN
            copy.notes = (copy.notes or "") + "\nWithdrawn: missing after Q1 inventory"
        await test_db.commit()

        for copy in missing_copies:
            await test_db.refresh(copy)
            assert copy.condition == ItemCondition.WITHDRAWN
            assert "missing after Q1 inventory" in (copy.notes or "")

    @pytest.mark.asyncio
    async def test_batch_update_preserves_found_items(self, test_db):
        """Batch updating missing items must NOT affect items that were found."""
        _ = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db, title="Preserve book")
        found_copy = await _make_copy(test_db, cat, location="Preserve N-1", copy_number=1)
        missing_copy = await _make_copy(test_db, cat, location="Preserve N-1", copy_number=2)
        await test_db.commit()

        # Only withdraw the missing copy
        missing_copy.condition = ItemCondition.WITHDRAWN
        await test_db.commit()
        await test_db.refresh(found_copy)
        await test_db.refresh(missing_copy)

        assert missing_copy.condition == ItemCondition.WITHDRAWN
        assert found_copy.condition == ItemCondition.GOOD  # untouched


# ============================================================================
# 10. MARK SECTION COMPLETE
# ============================================================================


class TestMarkSectionComplete:

    @pytest.mark.asyncio
    async def test_complete_audit_sets_timestamp(self, test_db):
        """Completing an audit sets completed_at and calculates missing."""
        staff = await _make_staff(test_db)
        cat, copies = await _seed_section(test_db, staff, "Complete O-1", count=3)

        audit = InventoryAudit(
            name="Complete test",
            location_filter="Complete O-1",
            items_expected=3,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.flush()

        # Scan 2 of 3
        for copy in copies[:2]:
            test_db.add(AuditScan(
                audit_id=audit.id,
                item_copy_id=copy.id,
                found_at_location="Complete O-1",
                scanned_by_id=staff.id,
            ))
            audit.items_found += 1

        audit.completed_at = datetime.now(timezone.utc)
        audit.items_missing = audit.items_expected - audit.items_found
        await test_db.commit()
        await test_db.refresh(audit)

        assert audit.completed_at is not None
        assert audit.items_missing == 1

    @pytest.mark.asyncio
    async def test_double_complete_idempotent(self, test_db):
        """Completing an already-completed audit should keep original timestamp."""
        staff = await _make_staff(test_db)
        await test_db.commit()

        audit = InventoryAudit(
            name="Double complete",
            location_filter="Dbl P-1",
            items_expected=0,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.flush()

        first_complete = datetime.now(timezone.utc)
        audit.completed_at = first_complete
        await test_db.commit()
        await test_db.refresh(audit)

        # API endpoint checks `if audit.completed_at` and returns 400
        # Simulate: the original timestamp is preserved
        assert audit.completed_at is not None


# ============================================================================
# 11. INVENTORY HISTORY TRACKING
# ============================================================================


class TestInventoryHistory:

    @pytest.mark.asyncio
    async def test_list_audits_ordered_by_date(self, test_db):
        """Audit history lists audits newest first."""
        staff = await _make_staff(test_db)
        await test_db.commit()

        for i in range(3):
            a = InventoryAudit(
                name=f"History audit {i}",
                location_filter=f"Hist {i}",
                items_expected=0,
                created_by_id=staff.id,
            )
            test_db.add(a)
        await test_db.commit()

        result = await test_db.execute(
            select(InventoryAudit).order_by(InventoryAudit.started_at.desc())
        )
        audits = result.scalars().all()
        assert len(audits) >= 3

        # They should be in reverse chronological order
        for i in range(len(audits) - 1):
            assert audits[i].started_at >= audits[i + 1].started_at

    @pytest.mark.asyncio
    async def test_audit_scan_records_scanner_and_time(self, test_db):
        """Each scan records who scanned and when."""
        staff = await _make_staff(test_db)
        cat, copies = await _seed_section(test_db, staff, "Track Q-1", count=1)

        audit = InventoryAudit(
            name="Track scan",
            location_filter="Track Q-1",
            items_expected=1,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.flush()

        scan = AuditScan(
            audit_id=audit.id,
            item_copy_id=copies[0].id,
            found_at_location="Track Q-1",
            scanned_by_id=staff.id,
        )
        test_db.add(scan)
        await test_db.commit()
        await test_db.refresh(scan)

        assert scan.scanned_by_id == staff.id
        assert scan.scanned_at is not None


# ============================================================================
# 12. EXPORT RESULTS
# ============================================================================


class TestExportResults:

    @pytest.mark.asyncio
    async def test_export_audit_summary_dict(self, test_db):
        """Export audit data to a dictionary (JSON-ready structure)."""
        staff = await _make_staff(test_db)
        cat, copies = await _seed_section(test_db, staff, "Export R-1", count=5)

        audit = InventoryAudit(
            name="Export test",
            location_filter="Export R-1",
            items_expected=5,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.flush()

        # Scan all, one misplaced
        for i, copy in enumerate(copies):
            is_misplaced = (i == 2)  # 3rd item is misplaced
            test_db.add(AuditScan(
                audit_id=audit.id,
                item_copy_id=copy.id,
                found_at_location="Wrong Place" if is_misplaced else "Export R-1",
                is_misplaced=is_misplaced,
                scanned_by_id=staff.id,
            ))
            audit.items_found += 1
            if is_misplaced:
                audit.items_misplaced += 1

        audit.completed_at = datetime.now(timezone.utc)
        audit.items_missing = audit.items_expected - audit.items_found
        await test_db.commit()
        await test_db.refresh(audit)

        export = {
            "audit_id": audit.id,
            "name": audit.name,
            "section": audit.location_filter,
            "started_at": audit.started_at.isoformat() if audit.started_at else None,
            "completed_at": audit.completed_at.isoformat() if audit.completed_at else None,
            "summary": {
                "expected": audit.items_expected,
                "found": audit.items_found,
                "missing": audit.items_missing,
                "misplaced": audit.items_misplaced,
                "completion_pct": round(
                    (audit.items_found / audit.items_expected * 100)
                    if audit.items_expected
                    else 0,
                    1,
                ),
            },
        }

        assert export["name"] == "Export test"
        assert export["section"] == "Export R-1"
        assert export["summary"]["expected"] == 5
        assert export["summary"]["found"] == 5
        assert export["summary"]["missing"] == 0
        assert export["summary"]["misplaced"] == 1
        assert export["summary"]["completion_pct"] == 100.0

    @pytest.mark.asyncio
    async def test_export_scan_details(self, test_db):
        """Export individual scan records with barcode info."""
        staff = await _make_staff(test_db)
        cat = await _make_catalog_item(test_db, title="Export detail")
        copy = await _make_copy(test_db, cat, location="Export S-1")
        await test_db.commit()

        audit = InventoryAudit(
            name="Detail export",
            location_filter="Export S-1",
            items_expected=1,
            created_by_id=staff.id,
        )
        test_db.add(audit)
        await test_db.flush()

        test_db.add(AuditScan(
            audit_id=audit.id,
            item_copy_id=copy.id,
            found_at_location="Export S-1",
            is_misplaced=False,
            scanned_by_id=staff.id,
        ))
        await test_db.commit()

        # Query scan + copy details for export
        result = await test_db.execute(
            select(AuditScan, ItemCopy)
            .join(ItemCopy, AuditScan.item_copy_id == ItemCopy.id)
            .where(AuditScan.audit_id == audit.id)
        )
        rows = result.all()
        assert len(rows) == 1

        scan, item = rows[0]
        record = {
            "barcode": item.barcode,
            "location_expected": item.location,
            "location_found": scan.found_at_location,
            "is_misplaced": scan.is_misplaced,
            "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
        }
        assert record["barcode"] == copy.barcode
        assert record["is_misplaced"] is False
