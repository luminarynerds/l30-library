# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for lost and damaged item workflows.

Tests the complete workflow for:
- Lost item processing (mark lost, found item credit, write off)
- Damaged item processing (report, assess, mending, repair, withdraw)
- Claims returned disputes
- Reports and analytics
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def test_item_copy_with_price(test_db, test_catalog_item):
    """Create an item copy with a replacement cost set."""
    from app.models.inventory import ItemCopy, ItemCondition

    copy = ItemCopy(
        catalog_item_id=test_catalog_item.id,
        barcode="COPY-LOST-001",
        condition=ItemCondition.GOOD,
        replacement_cost=Decimal("29.95"),
        location="Main Branch",
    )
    test_db.add(copy)
    await test_db.commit()
    await test_db.refresh(copy)
    return copy


@pytest.fixture
async def test_overdue_checkout(test_db, test_patron, test_catalog_item, test_item_copy_with_price):
    """Create an overdue checkout for lost item testing."""
    from app.models.circulation import Checkout, CheckoutStatus

    checkout = Checkout(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        item_copy_id=test_item_copy_with_price.id,
        status=CheckoutStatus.overdue,
        checked_out_at=datetime.now() - timedelta(days=45),
        due_date=datetime.now() - timedelta(days=31),
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


@pytest.fixture
async def test_damaged_item_copy(test_db, test_catalog_item):
    """Create an item copy for damage testing."""
    from app.models.inventory import ItemCopy, ItemCondition

    copy = ItemCopy(
        catalog_item_id=test_catalog_item.id,
        barcode="COPY-DAMAGE-001",
        condition=ItemCondition.GOOD,
        replacement_cost=Decimal("35.00"),
        location="Main Branch",
    )
    test_db.add(copy)
    await test_db.commit()
    await test_db.refresh(copy)
    return copy


@pytest.fixture
async def test_workflow_settings(test_db):
    """Create LostDamagedSettings with notify_staff_on_claims enabled."""
    from app.models.lost_damaged import LostDamagedSettings

    # Create new settings with notify_staff_on_claims=True
    settings = LostDamagedSettings(
        notify_staff_on_claims=True,
    )
    test_db.add(settings)
    await test_db.commit()
    await test_db.refresh(settings)
    return settings


# ============================================================================
# Lost Item Workflow Tests
# ============================================================================

class TestLostItemWorkflow:
    """Tests for the lost item workflow."""

    @pytest.mark.asyncio
    async def test_mark_item_lost_by_patron(self, test_db, test_overdue_checkout, test_staff):
        """Test marking an item as lost by patron."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType, LostItemStatus
        from app.models.circulation import CheckoutStatus

        service = LostItemWorkflowService(test_db)
        result = await service.mark_item_lost(
            checkout_id=test_overdue_checkout.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            report_notes="Patron reported item lost",
            send_notification=False,
        )

        assert result.success is True
        assert result.lost_item_record is not None
        assert result.lost_item_record.status == LostItemStatus.CHARGED
        assert result.lost_item_record.lost_type == LostItemType.LOST_BY_PATRON
        assert result.replacement_cost is not None
        assert result.replacement_cost.total > 0
        assert result.fine is not None

        # Verify checkout status updated
        await test_db.refresh(test_overdue_checkout)
        assert test_overdue_checkout.status == CheckoutStatus.lost_by_patron

    @pytest.mark.asyncio
    async def test_replacement_cost_calculation(self, test_db, test_overdue_checkout, test_staff):
        """Test that replacement cost includes item price and processing fee."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType
        from app.core.config import get_settings

        settings = get_settings()
        service = LostItemWorkflowService(test_db)
        result = await service.mark_item_lost(
            checkout_id=test_overdue_checkout.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        assert result.success is True
        cost = result.replacement_cost
        # Item price should be from item copy (29.95)
        assert cost.item_price == Decimal("29.95")
        # Processing fee from settings
        assert cost.processing_fee == Decimal(str(settings.lost_item_processing_fee))
        # Total should be sum
        assert cost.total == cost.item_price + cost.processing_fee

    @pytest.mark.asyncio
    async def test_process_found_item(self, test_db, test_overdue_checkout, test_staff):
        """Test processing a found item that was previously lost."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType, LostItemStatus
        from app.models.inventory import ItemCondition
        from app.models.catalog import ItemStatus

        service = LostItemWorkflowService(test_db)

        # First mark as lost
        lost_result = await service.mark_item_lost(
            checkout_id=test_overdue_checkout.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )
        assert lost_result.success is True

        # Now process as found
        found_result = await service.process_found_item(
            lost_record_id=lost_result.lost_item_record.id,
            found_by=test_staff,
            found_condition=ItemCondition.GOOD,
            resolution_notes="Found in book drop",
            send_notification=False,
        )

        assert found_result.success is True
        assert found_result.lost_item_record.status == LostItemStatus.FOUND
        assert found_result.credit_amount > 0  # Should credit the patron
        assert found_result.item_restored is True

        # Verify item is back to available
        await test_db.refresh(test_overdue_checkout)
        await test_db.refresh(test_overdue_checkout.item)
        assert test_overdue_checkout.item.status == ItemStatus.available

    @pytest.mark.asyncio
    async def test_write_off_lost_item(self, test_db, test_overdue_checkout, test_staff):
        """Test writing off a lost item."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType, LostItemStatus

        service = LostItemWorkflowService(test_db)

        # Mark as lost
        lost_result = await service.mark_item_lost(
            checkout_id=test_overdue_checkout.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        # Write off
        write_off_result = await service.write_off_lost_item(
            lost_record_id=lost_result.lost_item_record.id,
            written_off_by=test_staff,
            notes="Item has been missing for over 6 months",
        )

        assert write_off_result.success is True
        assert write_off_result.lost_item_record.status == LostItemStatus.WRITTEN_OFF
        assert write_off_result.lost_item_record.written_off_at is not None

    @pytest.mark.asyncio
    async def test_cannot_mark_lost_twice(self, test_db, test_overdue_checkout, test_staff):
        """Test that an item cannot be marked lost twice."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)

        # Mark as lost first time
        result1 = await service.mark_item_lost(
            checkout_id=test_overdue_checkout.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )
        assert result1.success is True

        # Try to mark as lost again
        result2 = await service.mark_item_lost(
            checkout_id=test_overdue_checkout.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )
        assert result2.success is False
        assert "already marked as lost" in result2.message.lower()


# ============================================================================
# Damaged Item Workflow Tests
# ============================================================================

class TestDamagedItemWorkflow:
    """Tests for the damaged item workflow."""

    @pytest.mark.asyncio
    async def test_report_damage(self, test_db, test_damaged_item_copy, test_staff):
        """Test reporting damage to an item."""
        from app.services.damaged_item_workflow_service import DamagedItemWorkflowService
        from app.models.lost_damaged import DamageSeverity, DamagedItemStatus
        from app.models.inventory import DamageType

        service = DamagedItemWorkflowService(test_db)
        result = await service.report_damage(
            item_copy_id=test_damaged_item_copy.id,
            damage_types=[DamageType.TORN_PAGES, DamageType.WATER_DAMAGE],
            damage_description="Multiple pages torn, water damage on cover",
            severity=DamageSeverity.MODERATE,
            reported_by=test_staff,
            is_patron_responsible=True,
            send_notification=False,
        )

        assert result.success is True
        assert result.damaged_item_record is not None
        assert result.damaged_item_record.severity == DamageSeverity.MODERATE
        assert result.assessment is not None
        assert result.assessment.recommended_action in ["repair", "withdraw", "no_action"]

    @pytest.mark.asyncio
    async def test_damage_assessment(self, test_db, test_damaged_item_copy, test_staff):
        """Test completing a damage assessment."""
        from app.services.damaged_item_workflow_service import DamagedItemWorkflowService
        from app.models.lost_damaged import DamageSeverity, DamagedItemStatus
        from app.models.inventory import DamageType

        service = DamagedItemWorkflowService(test_db)

        # Report damage
        report_result = await service.report_damage(
            item_copy_id=test_damaged_item_copy.id,
            damage_types=[DamageType.SPINE_DAMAGE],
            damage_description="Spine is loose but repairable",
            severity=DamageSeverity.MODERATE,
            reported_by=test_staff,
            send_notification=False,
        )

        # Complete assessment
        assess_result = await service.complete_assessment(
            damage_record_id=report_result.damaged_item_record.id,
            assessed_by=test_staff,
            is_repairable=True,
            charge_patron=False,
            assessment_notes="Can be repaired with rebinding",
            send_notification=False,
        )

        assert assess_result.success is True
        assert assess_result.damaged_item_record.status == DamagedItemStatus.REPAIRABLE
        assert assess_result.damaged_item_record.assessed_at is not None

    @pytest.mark.asyncio
    async def test_send_to_mending(self, test_db, test_damaged_item_copy, test_staff):
        """Test sending a damaged item to the mending queue."""
        from app.services.damaged_item_workflow_service import DamagedItemWorkflowService
        from app.models.lost_damaged import DamageSeverity, DamagedItemStatus
        from app.models.inventory import DamageType
        from app.models.catalog import ItemStatus

        service = DamagedItemWorkflowService(test_db)

        # Report and assess
        report_result = await service.report_damage(
            item_copy_id=test_damaged_item_copy.id,
            damage_types=[DamageType.BINDING_LOOSE],
            damage_description="Binding is coming apart",
            severity=DamageSeverity.MODERATE,
            reported_by=test_staff,
            send_notification=False,
        )
        await service.complete_assessment(
            damage_record_id=report_result.damaged_item_record.id,
            assessed_by=test_staff,
            is_repairable=True,
            send_notification=False,
        )

        # Send to mending
        mending_result = await service.send_to_mending(
            damage_record_id=report_result.damaged_item_record.id,
            added_by=test_staff,
            priority=2,
            repair_type="rebinding",
            repair_instructions="Glue spine, reinforce binding",
            estimated_time_hours=Decimal("2.5"),
        )

        assert mending_result.success is True
        assert mending_result.mending_entry is not None
        assert mending_result.damaged_item_record.status == DamagedItemStatus.IN_MENDING

        # Verify item status
        await test_db.refresh(test_damaged_item_copy.catalog_item)
        assert test_damaged_item_copy.catalog_item.status == ItemStatus.in_mending

    @pytest.mark.asyncio
    async def test_complete_repair(self, test_db, test_damaged_item_copy, test_staff):
        """Test completing a repair."""
        from app.services.damaged_item_workflow_service import DamagedItemWorkflowService
        from app.models.lost_damaged import DamageSeverity, DamagedItemStatus
        from app.models.inventory import DamageType, ItemCondition
        from app.models.catalog import ItemStatus

        service = DamagedItemWorkflowService(test_db)

        # Report, assess, send to mending
        report_result = await service.report_damage(
            item_copy_id=test_damaged_item_copy.id,
            damage_types=[DamageType.TORN_PAGES],
            damage_description="Several torn pages",
            severity=DamageSeverity.MINOR,
            reported_by=test_staff,
            send_notification=False,
        )
        await service.complete_assessment(
            damage_record_id=report_result.damaged_item_record.id,
            assessed_by=test_staff,
            is_repairable=True,
            send_notification=False,
        )
        mending_result = await service.send_to_mending(
            damage_record_id=report_result.damaged_item_record.id,
            added_by=test_staff,
            priority=3,
        )

        # Complete repair
        repair_result = await service.complete_repair(
            mending_entry_id=mending_result.mending_entry.id,
            completed_by=test_staff,
            actual_cost=Decimal("8.50"),
            completion_notes="Pages repaired with tape",
            new_condition=ItemCondition.GOOD,
        )

        assert repair_result.success is True
        assert repair_result.item_restored is True
        assert repair_result.actual_cost == Decimal("8.50")

        # Verify statuses
        await test_db.refresh(report_result.damaged_item_record)
        assert report_result.damaged_item_record.status == DamagedItemStatus.REPAIRED

        await test_db.refresh(test_damaged_item_copy.catalog_item)
        assert test_damaged_item_copy.catalog_item.status == ItemStatus.available

    @pytest.mark.asyncio
    async def test_withdraw_damaged_item(self, test_db, test_damaged_item_copy, test_staff, test_patron):
        """Test withdrawing a damaged item beyond repair."""
        from app.services.damaged_item_workflow_service import DamagedItemWorkflowService
        from app.models.lost_damaged import DamageSeverity, DamagedItemStatus
        from app.models.inventory import DamageType
        from app.models.catalog import ItemStatus

        service = DamagedItemWorkflowService(test_db)

        # Report severe damage
        report_result = await service.report_damage(
            item_copy_id=test_damaged_item_copy.id,
            damage_types=[DamageType.WATER_DAMAGE, DamageType.MISSING_PAGES],
            damage_description="Extensive water damage, multiple pages missing",
            severity=DamageSeverity.TOTAL_LOSS,
            reported_by=test_staff,
            patron_id=test_patron.id,
            is_patron_responsible=True,
            send_notification=False,
        )

        # Withdraw with charge
        withdraw_result = await service.withdraw_damaged_item(
            damage_record_id=report_result.damaged_item_record.id,
            withdrawn_by=test_staff,
            withdrawal_reason="Beyond repair due to water damage",
            charge_patron=True,
            charge_amount=Decimal("35.00"),
            send_notification=False,
        )

        assert withdraw_result.success is True
        assert withdraw_result.damaged_item_record.status == DamagedItemStatus.WITHDRAWN
        assert withdraw_result.fine is not None
        assert withdraw_result.fine.amount == Decimal("35.00")

        # Verify item status
        await test_db.refresh(test_damaged_item_copy.catalog_item)
        assert test_damaged_item_copy.catalog_item.status == ItemStatus.damaged_withdrawn


# ============================================================================
# Claims Returned Workflow Tests
# ============================================================================

class TestClaimsReturnedWorkflow:
    """Tests for the claims returned dispute workflow."""

    @pytest.mark.asyncio
    async def test_file_claim(self, test_db, test_overdue_checkout, test_staff):
        """Test filing a claims returned dispute."""
        from app.services.claims_returned_service import ClaimsReturnedService
        from app.models.lost_damaged import ClaimDisputeStatus
        from app.models.circulation import CheckoutStatus
        from datetime import date

        service = ClaimsReturnedService(test_db)
        result = await service.file_claim(
            checkout_id=test_overdue_checkout.id,
            patron_statement="I returned this book in the book drop last Tuesday",
            claimed_return_date=date.today() - timedelta(days=7),
            claimed_return_location="Main Branch book drop",
            filed_by=test_staff,
            send_notification=False,
        )

        assert result.success is True
        assert result.dispute is not None
        assert result.dispute.status == ClaimDisputeStatus.PENDING

        # Verify checkout status
        await test_db.refresh(test_overdue_checkout)
        assert test_overdue_checkout.status == CheckoutStatus.claims_returned

    @pytest.mark.asyncio
    async def test_review_claim(self, test_db, test_overdue_checkout, test_staff):
        """Test starting review of a claims returned dispute."""
        from app.services.claims_returned_service import ClaimsReturnedService
        from app.models.lost_damaged import ClaimDisputeStatus

        service = ClaimsReturnedService(test_db)

        # File claim
        file_result = await service.file_claim(
            checkout_id=test_overdue_checkout.id,
            patron_statement="I definitely returned this",
            filed_by=test_staff,
            send_notification=False,
        )

        # Start review
        review_result = await service.start_review(
            dispute_id=file_result.dispute.id,
            reviewed_by=test_staff,
            initial_notes="Checking shelf and book drop records",
        )

        assert review_result.success is True
        assert review_result.dispute.status == ClaimDisputeStatus.UNDER_REVIEW
        assert review_result.dispute.reviewed_at is not None

    @pytest.mark.asyncio
    async def test_approve_claim(self, test_db, test_overdue_checkout, test_staff):
        """Test approving a claims returned dispute."""
        from app.services.claims_returned_service import ClaimsReturnedService
        from app.models.lost_damaged import ClaimDisputeStatus

        service = ClaimsReturnedService(test_db)

        # File and review
        file_result = await service.file_claim(
            checkout_id=test_overdue_checkout.id,
            patron_statement="I returned this item",
            filed_by=test_staff,
            send_notification=False,
        )
        await service.start_review(
            dispute_id=file_result.dispute.id,
            reviewed_by=test_staff,
        )

        # Approve
        resolve_result = await service.resolve_claim(
            dispute_id=file_result.dispute.id,
            resolved_by=test_staff,
            approved=True,
            resolution_reason="Patron has good history, item may be misshelved",
            send_notification=False,
        )

        assert resolve_result.success is True
        assert resolve_result.dispute.status == ClaimDisputeStatus.APPROVED

    @pytest.mark.asyncio
    async def test_deny_claim(self, test_db, test_overdue_checkout, test_staff):
        """Test denying a claims returned dispute."""
        from app.services.claims_returned_service import ClaimsReturnedService
        from app.models.lost_damaged import ClaimDisputeStatus

        service = ClaimsReturnedService(test_db)

        # File and review
        file_result = await service.file_claim(
            checkout_id=test_overdue_checkout.id,
            patron_statement="I think I returned it",
            filed_by=test_staff,
            send_notification=False,
        )
        await service.start_review(
            dispute_id=file_result.dispute.id,
            reviewed_by=test_staff,
        )

        # Deny
        resolve_result = await service.resolve_claim(
            dispute_id=file_result.dispute.id,
            resolved_by=test_staff,
            approved=False,
            resolution_reason="Thorough search completed, item not found. Patron has multiple previous claims.",
            send_notification=False,
        )

        assert resolve_result.success is True
        assert resolve_result.dispute.status == ClaimDisputeStatus.DENIED
        assert resolve_result.credit_amount == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_item_found_during_search(self, test_db, test_overdue_checkout, test_staff):
        """Test resolving dispute when item is found during search."""
        from app.services.claims_returned_service import ClaimsReturnedService
        from app.models.lost_damaged import ClaimDisputeStatus

        service = ClaimsReturnedService(test_db)

        # File claim
        file_result = await service.file_claim(
            checkout_id=test_overdue_checkout.id,
            patron_statement="I returned it to the circulation desk",
            filed_by=test_staff,
            send_notification=False,
        )

        # Start search
        await service.start_search(
            dispute_id=file_result.dispute.id,
            search_locations=["Circulation desk", "Reshelving cart", "Returns bin"],
        )

        # Resolve - item found
        resolve_result = await service.resolve_claim(
            dispute_id=file_result.dispute.id,
            resolved_by=test_staff,
            approved=True,
            resolution_reason="Item found misshelved in fiction section",
            item_found=True,
            send_notification=False,
        )

        assert resolve_result.success is True
        assert resolve_result.dispute.status == ClaimDisputeStatus.ITEM_FOUND
        assert resolve_result.item_found is True

    @pytest.mark.asyncio
    async def test_patron_claims_history(self, test_db, test_overdue_checkout, test_staff, test_patron):
        """Test tracking patron's claims history."""
        from app.services.claims_returned_service import ClaimsReturnedService

        service = ClaimsReturnedService(test_db)

        # Check initial history
        history = await service.get_patron_claims_history(test_patron.id)
        initial_count = history.total_claims

        # File a claim
        await service.file_claim(
            checkout_id=test_overdue_checkout.id,
            patron_statement="Test claim",
            filed_by=test_staff,
            send_notification=False,
        )

        # Check updated history
        updated_history = await service.get_patron_claims_history(test_patron.id)
        assert updated_history.total_claims == initial_count + 1
        assert updated_history.pending_claims >= 1

    @pytest.mark.asyncio
    async def test_file_claim_sends_unified_notification(self, test_db, test_overdue_checkout, test_staff, test_workflow_settings):
        """Test that filing a claim sends notifications via UnifiedNotificationService."""
        from unittest.mock import AsyncMock, patch
        from app.services.claims_returned_service import ClaimsReturnedService
        from app.services.unified_notification_service import NotificationType
        from app.models.user import UserRole

        service = ClaimsReturnedService(test_db)

        # Mock UnifiedNotificationService
        with patch('app.services.claims_returned_service.UnifiedNotificationService') as MockNotificationService:
            mock_service_instance = MockNotificationService.return_value
            mock_service_instance.send_templated = AsyncMock(return_value=True)

            # File a claim with notification enabled
            result = await service.file_claim(
                checkout_id=test_overdue_checkout.id,
                patron_statement="I returned this book in the book drop last Tuesday",
                filed_by=test_staff,
                send_notification=True,
            )

            # Assert dispute was created successfully
            assert result.success is True
            assert result.dispute is not None
            assert result.notification_sent is True

            # Assert UnifiedNotificationService.send_templated was called
            assert mock_service_instance.send_templated.called

            # Get all calls to send_templated
            calls = mock_service_instance.send_templated.call_args_list
            assert len(calls) > 0  # At least one staff member should be notified

            # Verify the first call has the correct parameters
            first_call = calls[0]
            call_kwargs = first_call[1]

            assert call_kwargs['notification_type'] == NotificationType.CLAIMS_RETURNED
            assert 'recipient_email' in call_kwargs
            assert call_kwargs['user_id'] is not None
            assert call_kwargs['db'] == test_db

            # Verify context_data contains required fields
            context_data = call_kwargs['context_data']
            assert context_data['dispute_id'] == result.dispute.id
            assert context_data['patron_id'] == test_overdue_checkout.user_id
            assert 'patron_name' in context_data
            assert 'item_title' in context_data
            assert context_data['checkout_id'] == test_overdue_checkout.id
            assert 'dispute_url' in context_data
            assert context_data['patron_statement'] == "I returned this book in the book drop last Tuesday"


# ============================================================================
# Reports Tests
# ============================================================================

class TestLostDamagedReports:
    """Tests for lost/damaged item reports."""

    @pytest.mark.asyncio
    async def test_financial_summary(self, test_db, test_overdue_checkout, test_staff):
        """Test financial summary report."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.services.lost_damaged_reports_service import LostDamagedReportsService
        from app.models.lost_damaged import LostItemType

        # Create some lost items with charges
        lost_service = LostItemWorkflowService(test_db)
        await lost_service.mark_item_lost(
            checkout_id=test_overdue_checkout.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        # Get financial summary
        report_service = LostDamagedReportsService(test_db)
        summary = await report_service.get_financial_summary()

        assert summary.total_charges >= 0
        assert summary.period_start is not None
        assert summary.period_end is not None

    @pytest.mark.asyncio
    async def test_inventory_summary(self, test_db, test_overdue_checkout, test_staff):
        """Test inventory summary report."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.services.lost_damaged_reports_service import LostDamagedReportsService
        from app.models.lost_damaged import LostItemType

        # Create a lost item
        lost_service = LostItemWorkflowService(test_db)
        await lost_service.mark_item_lost(
            checkout_id=test_overdue_checkout.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        # Get inventory summary
        report_service = LostDamagedReportsService(test_db)
        summary = await report_service.get_inventory_summary()

        assert summary.total_lost >= 1
        assert summary.lost_by_patron >= 1

    @pytest.mark.asyncio
    async def test_monthly_trend(self, test_db):
        """Test monthly trend report."""
        from app.services.lost_damaged_reports_service import LostDamagedReportsService

        report_service = LostDamagedReportsService(test_db)
        trends = await report_service.get_monthly_trend(months=6)

        # Should return 6 months of data
        assert len(trends) >= 1
        for trend in trends:
            assert trend.period is not None
            assert trend.lost_count >= 0
            assert trend.damaged_count >= 0
