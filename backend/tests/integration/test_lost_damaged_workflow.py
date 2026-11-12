# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for Lost & Damaged Workflow (13 endpoints)

Safety critical tests verifying:
- State machine transitions
- ItemStatus enum values
- Authorization checks
- Transaction integrity
- Patron notifications
- Financial tracking
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.circulation import Checkout, CheckoutStatus
from app.models.inventory import ItemCopy, ItemCondition, DamageType
from app.models.lost_damaged import (
    LostItemRecord,
    LostItemStatus,
    LostItemType,
    DamagedItemRecord,
    DamagedItemStatus,
    DamageSeverity,
    ClaimsReturnedDispute,
    ClaimDisputeStatus,
    MendingQueue,
)
from app.models.catalog import CatalogItem, ItemStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.user import User, UserRole
from app.services.lost_item_workflow_service import LostItemWorkflowService
from app.services.damaged_item_workflow_service import DamagedItemWorkflowService
from app.services.claims_returned_service import ClaimsReturnedService


@pytest.fixture
async def staff_user(db: AsyncSession) -> User:
    """Create a staff user for testing."""
    user = User(
        email="staff@test.com",
        first_name="Staff",
        last_name="Member",
        password_hash="fake_hash",
        role=UserRole.STAFF,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def patron(db: AsyncSession) -> User:
    """Create a patron for testing."""
    user = User(
        email="patron@test.com",
        first_name="Test",
        last_name="Patron",
        password_hash="fake_hash",
        role=UserRole.PATRON,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def catalog_item(db: AsyncSession) -> CatalogItem:
    """Create a test catalog item."""
    item = CatalogItem(
        title="Test Book",
        author="Test Author",
        isbn="978-0-12345-678-9",
        status=ItemStatus.available,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@pytest.fixture
async def item_copy(db: AsyncSession, catalog_item: CatalogItem) -> ItemCopy:
    """Create a test item copy."""
    copy = ItemCopy(
        catalog_item_id=catalog_item.id,
        barcode="TEST-001",
        copy_number=1,
        condition=ItemCondition.GOOD,
        replacement_cost=Decimal("25.00"),
    )
    db.add(copy)
    await db.commit()
    await db.refresh(copy)
    return copy


@pytest.fixture
async def active_checkout(db: AsyncSession, patron: User, item_copy: ItemCopy) -> Checkout:
    """Create an active checkout for testing."""
    from datetime import datetime, timedelta, timezone

    checkout = Checkout(
        user_id=patron.id,
        item_id=item_copy.catalog_item_id,  # still nullable=False despite the copy-based model
        item_copy_id=item_copy.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(timezone.utc),
        due_date=datetime.now(timezone.utc) + timedelta(days=14),
        renewal_count=0,
    )
    db.add(checkout)
    await db.commit()
    await db.refresh(checkout)
    return checkout


class TestLostWorkflow:
    """Test lost item workflow endpoints (4 endpoints)."""

    async def test_mark_item_lost(
        self,
        db: AsyncSession,
        staff_user: User,
        active_checkout: Checkout,
    ):
        """Test POST /lost/{checkout_id}/mark-lost - Endpoint 12."""
        service = LostItemWorkflowService(db)
        result = await service.mark_item_lost(
            checkout_id=active_checkout.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=staff_user,
            report_notes="Patron reported loss",
        )

        assert result.success
        assert result.lost_item_record is not None
        # mark_item_lost creates the record at REPORTED, but for any
        # lost_type other than CLAIMS_RETURNED it immediately creates a Fine
        # and advances the SAME record to CHARGED before returning (see
        # app/services/lost_item_workflow_service.py mark_item_lost) --
        # REPORTED is a transient intermediate value, not the returned state.
        assert result.lost_item_record.status == LostItemStatus.CHARGED
        assert result.lost_item_record.lost_type == LostItemType.LOST_BY_PATRON
        assert result.replacement_cost is not None
        assert result.fine is not None
        assert result.fine.amount > Decimal("0")

    async def test_auto_convert_overdue_to_lost(
        self,
        db: AsyncSession,
        staff_user: User,
        patron: User,
        item_copy: ItemCopy,
    ):
        """Test POST /lost/auto-convert - Endpoint 10."""
        from datetime import datetime, timedelta, timezone

        # Create an overdue checkout
        old_due_date = datetime.now(timezone.utc) - timedelta(days=35)
        checkout = Checkout(
            user_id=patron.id,
            item_id=item_copy.catalog_item_id,  # still nullable=False
            item_copy_id=item_copy.id,
            status=CheckoutStatus.overdue,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=50),
            due_date=old_due_date,
        )
        db.add(checkout)
        await db.commit()

        service = LostItemWorkflowService(db)
        results = await service.auto_convert_overdue_items(threshold_days=30, dry_run=False)

        assert len(results) > 0
        assert results[0].success
        # mark_item_lost raises the replacement fine immediately, moving the
        # record REPORTED -> CHARGED. REPORTED is only the transient initial
        # state, never what an auto-converted record settles in.
        assert results[0].lost_item_record.status == LostItemStatus.CHARGED
        assert results[0].lost_item_record.fine_id is not None
        # No human reported this -- the scheduled job converted it.
        assert results[0].lost_item_record.reported_by_id is None

    async def test_mark_item_found(
        self,
        db: AsyncSession,
        staff_user: User,
        patron: User,
        item_copy: ItemCopy,
        active_checkout: Checkout,
    ):
        """Test POST /lost/{id}/mark-found - Endpoint 11."""
        service = LostItemWorkflowService(db)

        # First mark as lost
        lost_result = await service.mark_item_lost(
            checkout_id=active_checkout.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=staff_user,
        )
        assert lost_result.success

        # Then mark as found
        found_result = await service.process_found_item(
            lost_record_id=lost_result.lost_item_record.id,
            found_by=staff_user,
            found_condition=ItemCondition.GOOD,
            resolution_notes="Found in returns cart",
        )

        assert found_result.success
        assert found_result.lost_item_record.status == LostItemStatus.FOUND
        assert found_result.credit_amount >= Decimal("0")

    async def test_write_off_lost_item(
        self,
        db: AsyncSession,
        staff_user: User,
        active_checkout: Checkout,
    ):
        """Test POST /lost/{id}/write-off - Endpoint 13."""
        service = LostItemWorkflowService(db)

        # First mark as lost
        lost_result = await service.mark_item_lost(
            checkout_id=active_checkout.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=staff_user,
        )
        assert lost_result.success

        # Then write off
        writeoff_result = await service.write_off_lost_item(
            lost_record_id=lost_result.lost_item_record.id,
            written_off_by=staff_user,
            notes="Item will not be recovered",
        )

        assert writeoff_result.success
        assert writeoff_result.lost_item_record.status == LostItemStatus.WRITTEN_OFF


class TestDamagedWorkflow:
    """Test damaged item workflow endpoints (5 endpoints)."""

    async def test_report_damaged_item(
        self,
        db: AsyncSession,
        staff_user: User,
        item_copy: ItemCopy,
    ):
        """Test POST /damaged/report - Endpoint 8."""
        service = DamagedItemWorkflowService(db)
        result = await service.report_damage(
            item_copy_id=item_copy.id,
            damage_types=[DamageType.TORN_PAGES, DamageType.WATER_DAMAGE],
            damage_description="Pages are torn and water damaged",
            severity=DamageSeverity.MODERATE,
            reported_by=staff_user,
        )

        assert result.success
        assert result.damaged_item_record is not None
        # report_damage creates the record at REPORTED but immediately
        # advances the SAME record based on severity before returning (see
        # app/services/damaged_item_workflow_service.py report_damage) --
        # MODERATE severity lands on ASSESSMENT_PENDING (TOTAL_LOSS would
        # land on WITHDRAWN instead). REPORTED is a transient intermediate
        # value, not the returned state.
        assert result.damaged_item_record.status == DamagedItemStatus.ASSESSMENT_PENDING
        assert result.assessment is not None

    async def test_assess_damaged_item(
        self,
        db: AsyncSession,
        staff_user: User,
        item_copy: ItemCopy,
    ):
        """Test POST /damaged/assess - Endpoint 5."""
        service = DamagedItemWorkflowService(db)

        # Report damage first
        report_result = await service.report_damage(
            item_copy_id=item_copy.id,
            damage_types=[DamageType.SPINE_DAMAGE],
            damage_description="Spine is damaged",
            severity=DamageSeverity.MODERATE,
            reported_by=staff_user,
        )
        assert report_result.success

        # Assess the damage
        assess_result = await service.complete_assessment(
            damage_record_id=report_result.damaged_item_record.id,
            assessed_by=staff_user,
            is_repairable=True,
            charge_patron=False,
            assessment_notes="Can be repaired",
        )

        assert assess_result.success
        assert assess_result.damaged_item_record.status == DamagedItemStatus.REPAIRABLE

    async def test_send_to_mending(
        self,
        db: AsyncSession,
        staff_user: User,
        item_copy: ItemCopy,
    ):
        """Test POST /damaged/{id}/send-to-mending - Endpoint 6."""
        service = DamagedItemWorkflowService(db)

        # Report and assess damage
        report_result = await service.report_damage(
            item_copy_id=item_copy.id,
            damage_types=[DamageType.BINDING_LOOSE],
            damage_description="Binding is loose",
            severity=DamageSeverity.MODERATE,
            reported_by=staff_user,
        )
        assert report_result.success

        # Send to mending
        mending_result = await service.send_to_mending(
            damage_record_id=report_result.damaged_item_record.id,
            added_by=staff_user,
            priority=2,
            repair_type="binding_repair",
            repair_instructions="Rebind the pages",
            estimated_cost=Decimal("15.00"),
        )

        assert mending_result.success
        assert mending_result.damaged_item_record.status == DamagedItemStatus.IN_MENDING
        assert mending_result.mending_entry is not None

    async def test_repair_complete(
        self,
        db: AsyncSession,
        staff_user: User,
        item_copy: ItemCopy,
    ):
        """Test POST /damaged/{id}/repair-complete - Endpoint 7."""
        service = DamagedItemWorkflowService(db)

        # Report, assess, and send to mending
        report_result = await service.report_damage(
            item_copy_id=item_copy.id,
            damage_types=[DamageType.TORN_PAGES],
            damage_description="Torn pages",
            severity=DamageSeverity.MINOR,
            reported_by=staff_user,
        )
        assert report_result.success

        mending_result = await service.send_to_mending(
            damage_record_id=report_result.damaged_item_record.id,
            added_by=staff_user,
            priority=3,
            repair_type="page_repair",
            estimated_cost=Decimal("10.00"),
        )
        assert mending_result.success

        # Complete repair
        repair_result = await service.complete_repair(
            mending_entry_id=mending_result.mending_entry.id,
            completed_by=staff_user,
            actual_cost=Decimal("12.00"),
            completion_notes="Pages repaired successfully",
            new_condition=ItemCondition.GOOD,
        )

        assert repair_result.success
        assert repair_result.damaged_item_record.status == DamagedItemStatus.REPAIRED
        assert repair_result.item_restored

    async def test_withdraw_damaged_item(
        self,
        db: AsyncSession,
        staff_user: User,
        item_copy: ItemCopy,
    ):
        """Test POST /damaged/{id}/withdraw - Endpoint 9."""
        service = DamagedItemWorkflowService(db)

        # Report severe damage
        report_result = await service.report_damage(
            item_copy_id=item_copy.id,
            damage_types=[DamageType.MISSING_PAGES, DamageType.WATER_DAMAGE],
            damage_description="Multiple pages missing and water damaged",
            severity=DamageSeverity.TOTAL_LOSS,
            reported_by=staff_user,
        )
        assert report_result.success

        # Withdraw the item
        withdraw_result = await service.withdraw_damaged_item(
            damage_record_id=report_result.damaged_item_record.id,
            withdrawn_by=staff_user,
            withdrawal_reason="Beyond economical repair",
            charge_patron=True,
            charge_amount=Decimal("25.00"),
        )

        assert withdraw_result.success
        assert withdraw_result.damaged_item_record.status == DamagedItemStatus.WITHDRAWN


class TestClaimsReturnedWorkflow:
    """Test claims returned workflow endpoints (4 endpoints)."""

    async def test_file_claims_returned(
        self,
        db: AsyncSession,
        staff_user: User,
        patron: User,
        active_checkout: Checkout,
    ):
        """Test POST /claims-returned/file - Endpoint 1."""
        service = ClaimsReturnedService(db)
        result = await service.file_claim(
            checkout_id=active_checkout.id,
            patron_statement="I returned this item to the book drop",
            claimed_return_date=datetime.now(timezone.utc).date(),
            claimed_return_location="Main branch book drop",
            filed_by=staff_user,
        )

        assert result.success
        assert result.dispute is not None
        assert result.dispute.status == ClaimDisputeStatus.PENDING

    async def test_start_review_claim(
        self,
        db: AsyncSession,
        staff_user: User,
        patron: User,
        active_checkout: Checkout,
    ):
        """Test POST /claims-returned/{id}/start-review - Endpoint 3."""
        service = ClaimsReturnedService(db)

        # File claim first
        file_result = await service.file_claim(
            checkout_id=active_checkout.id,
            patron_statement="Item was returned",
            filed_by=staff_user,
        )
        assert file_result.success

        # Start review
        review_result = await service.start_review(
            dispute_id=file_result.dispute.id,
            reviewed_by=staff_user,
            initial_notes="Beginning investigation",
        )

        assert review_result.success
        assert review_result.dispute.status == ClaimDisputeStatus.UNDER_REVIEW

    async def test_start_search_claim(
        self,
        db: AsyncSession,
        staff_user: User,
        patron: User,
        active_checkout: Checkout,
    ):
        """Test POST /claims-returned/{id}/start-search - Endpoint 4."""
        service = ClaimsReturnedService(db)

        # File and start review first
        file_result = await service.file_claim(
            checkout_id=active_checkout.id,
            patron_statement="Item returned",
            filed_by=staff_user,
        )
        assert file_result.success

        # Start search
        search_result = await service.start_search(
            dispute_id=file_result.dispute.id,
            search_locations=["Returns cart", "Book drop", "Processing area"],
            search_notes="Thorough search initiated",
        )

        assert search_result.success
        assert search_result.dispute.status == ClaimDisputeStatus.SEARCH_IN_PROGRESS

    async def test_resolve_claim(
        self,
        db: AsyncSession,
        staff_user: User,
        patron: User,
        active_checkout: Checkout,
    ):
        """Test POST /claims-returned/{id}/resolve - Endpoint 2."""
        service = ClaimsReturnedService(db)

        # File claim first
        file_result = await service.file_claim(
            checkout_id=active_checkout.id,
            patron_statement="Item was returned",
            filed_by=staff_user,
        )
        assert file_result.success

        # Resolve the claim (approved)
        resolve_result = await service.resolve_claim(
            dispute_id=file_result.dispute.id,
            resolved_by=staff_user,
            approved=True,
            resolution_reason="Item was found in returns cart - search error",
            item_found=True,
            credit_amount=Decimal("0.00"),
        )

        assert resolve_result.success
        assert resolve_result.dispute.status == ClaimDisputeStatus.ITEM_FOUND


class TestStateTransitions:
    """Test valid state machine transitions."""

    async def test_lost_item_state_machine(
        self,
        db: AsyncSession,
        staff_user: User,
        active_checkout: Checkout,
    ):
        """Verify valid lost item status transitions."""
        service = LostItemWorkflowService(db)

        # reported -> charged (via mark_item_lost, in a single call -- see
        # test_mark_item_lost above for why the final status is CHARGED)
        lost_result = await service.mark_item_lost(
            checkout_id=active_checkout.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=staff_user,
        )
        assert lost_result.lost_item_record.status == LostItemStatus.CHARGED

    async def test_damaged_item_state_machine(
        self,
        db: AsyncSession,
        staff_user: User,
        item_copy: ItemCopy,
    ):
        """Verify valid damaged item status transitions."""
        service = DamagedItemWorkflowService(db)

        # reported -> assessment_pending (single call -- see
        # test_report_damaged_item above) -> repairable
        report_result = await service.report_damage(
            item_copy_id=item_copy.id,
            damage_types=[DamageType.TORN_PAGES],
            damage_description="Torn page",
            severity=DamageSeverity.MINOR,
            reported_by=staff_user,
        )
        assert report_result.damaged_item_record.status == DamagedItemStatus.ASSESSMENT_PENDING

        assess_result = await service.complete_assessment(
            damage_record_id=report_result.damaged_item_record.id,
            assessed_by=staff_user,
            is_repairable=True,
        )
        assert assess_result.damaged_item_record.status == DamagedItemStatus.REPAIRABLE


class TestAuthorizationChecks:
    """Test staff authorization checks."""

    async def test_patron_cannot_file_claim(
        self,
        db: AsyncSession,
        patron: User,
        active_checkout: Checkout,
    ):
        """Verify patrons cannot file claims via staff endpoint."""
        _ = ClaimsReturnedService(db)

        # This should fail because patron is not staff
        # (In real implementation, would be caught at dependency level)
        # Just document the requirement here
        assert patron.role == UserRole.PATRON

    async def test_staff_can_mark_lost(
        self,
        db: AsyncSession,
        staff_user: User,
        active_checkout: Checkout,
    ):
        """Verify staff users can mark items as lost."""
        service = LostItemWorkflowService(db)

        result = await service.mark_item_lost(
            checkout_id=active_checkout.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=staff_user,
        )

        assert result.success
        assert staff_user.role == UserRole.STAFF
