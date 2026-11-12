# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for marking items as lost by patron.

Tests the complete workflow for:
- Applying lost fees (item price + processing fee)
- Updating item status (checkout, catalog item, item copy)
- Notifying patron via email
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy import select


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def patron_with_email(test_db):
    """Create a patron with a valid email address for notification testing."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="patron_with_email@example.com",
        password_hash=hash_password("PatronPassword123!"),
        first_name="Jane",
        last_name="Doe",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def item_copy_with_replacement_cost(test_db, test_catalog_item):
    """Create an item copy with a specific replacement cost."""
    from app.models.inventory import ItemCopy, ItemCondition

    copy = ItemCopy(
        catalog_item_id=test_catalog_item.id,
        barcode="COPY-LOST-PATRON-001",
        condition=ItemCondition.GOOD,
        replacement_cost=Decimal("45.99"),
        location="Main Branch",
    )
    test_db.add(copy)
    await test_db.commit()
    await test_db.refresh(copy)
    return copy


@pytest.fixture
async def overdue_checkout_for_lost(
    test_db, patron_with_email, test_catalog_item, item_copy_with_replacement_cost
):
    """Create an overdue checkout eligible for marking as lost."""
    from app.models.circulation import Checkout, CheckoutStatus

    checkout = Checkout(
        user_id=patron_with_email.id,
        item_id=test_catalog_item.id,
        item_copy_id=item_copy_with_replacement_cost.id,
        status=CheckoutStatus.overdue,
        checked_out_at=datetime.now(timezone.utc) - timedelta(days=60),
        due_date=datetime.now(timezone.utc) - timedelta(days=45),
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


@pytest.fixture
async def active_checkout_for_lost(
    test_db, patron_with_email, test_catalog_item, item_copy_with_replacement_cost
):
    """Create an active checkout that can be marked lost by patron."""
    from app.models.circulation import Checkout, CheckoutStatus

    checkout = Checkout(
        user_id=patron_with_email.id,
        item_id=test_catalog_item.id,
        item_copy_id=item_copy_with_replacement_cost.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(timezone.utc) - timedelta(days=10),
        due_date=datetime.now(timezone.utc) + timedelta(days=11),
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


# ============================================================================
# Lost Fee Application Tests
# ============================================================================


class TestLostFeeApplication:
    """Tests for lost fee calculation and application."""

    @pytest.mark.asyncio
    async def test_lost_fee_includes_item_price_and_processing_fee(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that lost fee includes both item price and processing fee."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType
        from app.core.config import get_settings

        settings = get_settings()
        service = LostItemWorkflowService(test_db)

        result = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            report_notes="Patron reported item lost",
            send_notification=False,
        )

        assert result.success is True
        assert result.replacement_cost is not None

        # Verify item price comes from item copy replacement cost
        assert result.replacement_cost.item_price == Decimal("45.99")

        # Verify processing fee from settings
        expected_processing_fee = Decimal(str(settings.lost_item_processing_fee))
        assert result.replacement_cost.processing_fee == expected_processing_fee

        # Verify total is the sum
        expected_total = Decimal("45.99") + expected_processing_fee
        assert result.replacement_cost.total == expected_total

        # Verify fine amount matches total
        assert result.fine is not None
        assert result.fine.amount == expected_total

    @pytest.mark.asyncio
    async def test_lost_fee_creates_unpaid_fine(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that marking item lost creates an unpaid fine for the patron."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType
        from app.models.fine import FineType, FineStatus

        service = LostItemWorkflowService(test_db)

        result = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        assert result.success is True
        assert result.fine is not None

        # Verify fine attributes
        assert result.fine.fine_type == FineType.lost_item
        assert result.fine.status == FineStatus.unpaid
        assert result.fine.user_id == overdue_checkout_for_lost.user_id
        assert result.fine.checkout_id == overdue_checkout_for_lost.id
        assert result.fine.amount > Decimal("0.00")
        assert result.fine.amount_paid == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_lost_fee_description_includes_item_title(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that fine description includes the item title."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)

        result = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        assert result.success is True
        assert result.fine is not None
        assert "Lost item replacement" in result.fine.description
        assert "Test Book" in result.fine.description

    @pytest.mark.asyncio
    async def test_custom_replacement_cost_overrides_calculated(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that custom replacement cost overrides the calculated amount."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)
        custom_cost = Decimal("75.00")

        result = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            custom_replacement_cost=custom_cost,
            send_notification=False,
        )

        assert result.success is True
        assert result.replacement_cost is not None
        assert result.replacement_cost.item_price == custom_cost
        assert result.replacement_cost.processing_fee == Decimal("0.00")
        assert result.replacement_cost.total == custom_cost
        assert result.replacement_cost.source == "custom"
        assert result.fine.amount == custom_cost

    @pytest.mark.asyncio
    async def test_lost_fee_uses_default_when_no_item_price(
        self, test_db, test_staff, patron_with_email, test_catalog_item
    ):
        """Test that default replacement cost is used when item has no price set."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType
        from app.models.circulation import Checkout, CheckoutStatus
        from app.models.inventory import ItemCopy, ItemCondition
        from app.core.config import get_settings

        settings = get_settings()

        # Create item copy without replacement cost
        copy = ItemCopy(
            catalog_item_id=test_catalog_item.id,
            barcode="COPY-NO-PRICE-001",
            condition=ItemCondition.GOOD,
            replacement_cost=None,  # No price set
            location="Main Branch",
        )
        test_db.add(copy)
        await test_db.flush()

        checkout = Checkout(
            user_id=patron_with_email.id,
            item_id=test_catalog_item.id,
            item_copy_id=copy.id,
            status=CheckoutStatus.overdue,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=45),
            due_date=datetime.now(timezone.utc) - timedelta(days=31),
        )
        test_db.add(checkout)
        await test_db.commit()

        service = LostItemWorkflowService(test_db)

        result = await service.mark_item_lost(
            checkout_id=checkout.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        assert result.success is True
        assert result.replacement_cost is not None
        # Should use default replacement cost from settings
        expected_default = Decimal(str(settings.lost_item_default_replacement_cost))
        assert result.replacement_cost.item_price == expected_default
        assert result.replacement_cost.source == "default"

    @pytest.mark.asyncio
    async def test_lost_record_stores_fee_breakdown(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that lost item record stores complete fee breakdown."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)

        result = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        assert result.success is True
        record = result.lost_item_record

        # Verify fee breakdown stored in record
        assert record.item_price == result.replacement_cost.item_price
        assert record.processing_fee == result.replacement_cost.processing_fee
        assert record.replacement_cost == result.replacement_cost.total
        assert record.fine_id == result.fine.id


# ============================================================================
# Item Status Update Tests
# ============================================================================


class TestItemStatusUpdates:
    """Tests for item status updates when marking lost."""

    @pytest.mark.asyncio
    async def test_checkout_status_updated_to_lost_by_patron(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that checkout status is updated to lost_by_patron."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType
        from app.models.circulation import CheckoutStatus

        service = LostItemWorkflowService(test_db)

        result = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        assert result.success is True

        # Verify checkout status updated
        await test_db.refresh(overdue_checkout_for_lost)
        assert overdue_checkout_for_lost.status == CheckoutStatus.lost_by_patron

    @pytest.mark.asyncio
    async def test_catalog_item_status_updated_to_lost_by_patron(
        self, test_db, overdue_checkout_for_lost, test_staff, test_catalog_item
    ):
        """Test that catalog item status is updated to lost_by_patron."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType
        from app.models.catalog import ItemStatus

        service = LostItemWorkflowService(test_db)

        result = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        assert result.success is True

        # Verify catalog item status updated
        await test_db.refresh(test_catalog_item)
        assert test_catalog_item.status == ItemStatus.lost_by_patron

    @pytest.mark.asyncio
    async def test_item_copy_condition_set_to_withdrawn(
        self, test_db, overdue_checkout_for_lost, test_staff, item_copy_with_replacement_cost
    ):
        """Test that item copy condition is set to WITHDRAWN."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType
        from app.models.inventory import ItemCondition

        service = LostItemWorkflowService(test_db)

        result = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        assert result.success is True

        # Verify item copy condition updated
        await test_db.refresh(item_copy_with_replacement_cost)
        assert item_copy_with_replacement_cost.condition == ItemCondition.WITHDRAWN

    @pytest.mark.asyncio
    async def test_lost_record_status_set_to_charged(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that lost item record status is set to CHARGED."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType, LostItemStatus

        service = LostItemWorkflowService(test_db)

        result = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        assert result.success is True
        assert result.lost_item_record is not None
        assert result.lost_item_record.status == LostItemStatus.CHARGED
        assert result.lost_item_record.charged_at is not None

    @pytest.mark.asyncio
    async def test_lost_record_type_set_correctly(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that lost item record type is set to LOST_BY_PATRON."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)

        result = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        assert result.success is True
        assert result.lost_item_record.lost_type == LostItemType.LOST_BY_PATRON

    @pytest.mark.asyncio
    async def test_lost_record_stores_days_overdue(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that lost item record stores days overdue at time of marking."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)

        result = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        assert result.success is True
        # Checkout was due 45 days ago
        assert result.lost_item_record.days_overdue_at_loss >= 44

    @pytest.mark.asyncio
    async def test_active_checkout_can_be_marked_lost_by_patron(
        self, test_db, active_checkout_for_lost, test_staff
    ):
        """Test that active (not yet overdue) checkout can be marked lost by patron."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType
        from app.models.circulation import CheckoutStatus

        service = LostItemWorkflowService(test_db)

        result = await service.mark_item_lost(
            checkout_id=active_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            report_notes="Patron proactively reported item lost",
            send_notification=False,
        )

        assert result.success is True
        await test_db.refresh(active_checkout_for_lost)
        assert active_checkout_for_lost.status == CheckoutStatus.lost_by_patron

    @pytest.mark.asyncio
    async def test_lost_record_stores_report_notes(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that lost item record stores report notes."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)
        notes = "Patron called to report book was damaged in a house fire"

        result = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            report_notes=notes,
            send_notification=False,
        )

        assert result.success is True
        assert result.lost_item_record.report_notes == notes

    @pytest.mark.asyncio
    async def test_lost_record_stores_reported_by_staff(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that lost item record stores who reported it."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)

        result = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        assert result.success is True
        assert result.lost_item_record.reported_by_id == test_staff.id
        assert result.lost_item_record.reported_at is not None

    @pytest.mark.asyncio
    async def test_lost_record_stores_last_known_location(
        self, test_db, overdue_checkout_for_lost, test_staff, item_copy_with_replacement_cost
    ):
        """Test that lost item record stores last known location."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)

        result = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        assert result.success is True
        assert (
            result.lost_item_record.last_known_location == item_copy_with_replacement_cost.location
        )


# ============================================================================
# Patron Notification Tests
# ============================================================================


class TestPatronNotification:
    """Tests for patron notification when marking item lost."""

    @pytest.mark.asyncio
    async def test_notification_sent_when_enabled(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that notification is sent when send_notification=True."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)

        with patch(
            "app.services.lost_item_workflow_service.send_email", new_callable=AsyncMock
        ) as mock_send_email:
            mock_send_email.return_value = True

            result = await service.mark_item_lost(
                checkout_id=overdue_checkout_for_lost.id,
                lost_type=LostItemType.LOST_BY_PATRON,
                reported_by=test_staff,
                send_notification=True,
            )

            assert result.success is True
            assert result.notification_sent is True
            mock_send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_notification_not_sent_when_disabled(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that notification is not sent when send_notification=False."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)

        with patch(
            "app.services.lost_item_workflow_service.send_email", new_callable=AsyncMock
        ) as mock_send_email:
            result = await service.mark_item_lost(
                checkout_id=overdue_checkout_for_lost.id,
                lost_type=LostItemType.LOST_BY_PATRON,
                reported_by=test_staff,
                send_notification=False,
            )

            assert result.success is True
            assert result.notification_sent is False
            mock_send_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_notification_includes_patron_email(
        self, test_db, overdue_checkout_for_lost, test_staff, patron_with_email
    ):
        """Test that notification is sent to patron's email address."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)

        with patch(
            "app.services.lost_item_workflow_service.send_email", new_callable=AsyncMock
        ) as mock_send_email:
            mock_send_email.return_value = True

            result = await service.mark_item_lost(
                checkout_id=overdue_checkout_for_lost.id,
                lost_type=LostItemType.LOST_BY_PATRON,
                reported_by=test_staff,
                send_notification=True,
            )

            assert result.success is True
            mock_send_email.assert_called_once()
            call_args = mock_send_email.call_args
            # First argument should be the patron's email
            assert call_args[0][0] == patron_with_email.email

    @pytest.mark.asyncio
    async def test_notification_includes_item_title_in_subject(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that notification subject includes the item title."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)

        with patch(
            "app.services.lost_item_workflow_service.send_email", new_callable=AsyncMock
        ) as mock_send_email:
            mock_send_email.return_value = True

            result = await service.mark_item_lost(
                checkout_id=overdue_checkout_for_lost.id,
                lost_type=LostItemType.LOST_BY_PATRON,
                reported_by=test_staff,
                send_notification=True,
            )

            assert result.success is True
            call_args = mock_send_email.call_args
            # Second argument should be the subject
            subject = call_args[0][1]
            assert "Item Marked as Lost" in subject
            assert "Test Book" in subject

    @pytest.mark.asyncio
    async def test_notification_body_contains_cost_breakdown(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that notification body contains cost breakdown."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)

        with patch(
            "app.services.lost_item_workflow_service.send_email", new_callable=AsyncMock
        ) as mock_send_email:
            mock_send_email.return_value = True

            result = await service.mark_item_lost(
                checkout_id=overdue_checkout_for_lost.id,
                lost_type=LostItemType.LOST_BY_PATRON,
                reported_by=test_staff,
                send_notification=True,
            )

            assert result.success is True
            call_args = mock_send_email.call_args
            # Third argument should be the HTML body
            html_body = call_args[0][2]

            # Verify cost elements are in body
            assert "Item Value" in html_body
            assert "Processing Fee" in html_body
            assert "Total Due" in html_body
            assert "$45.99" in html_body  # Item price

    @pytest.mark.asyncio
    async def test_notification_body_contains_found_item_message(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that notification body contains 'found the item' recovery message."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)

        with patch(
            "app.services.lost_item_workflow_service.send_email", new_callable=AsyncMock
        ) as mock_send_email:
            mock_send_email.return_value = True

            result = await service.mark_item_lost(
                checkout_id=overdue_checkout_for_lost.id,
                lost_type=LostItemType.LOST_BY_PATRON,
                reported_by=test_staff,
                send_notification=True,
            )

            assert result.success is True
            call_args = mock_send_email.call_args
            html_body = call_args[0][2]

            # Verify recovery message is in body
            assert "Found the item?" in html_body
            assert "waive or reduce" in html_body

    @pytest.mark.asyncio
    async def test_notification_handles_email_failure_gracefully(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that email failure doesn't prevent marking item lost."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)

        with patch(
            "app.services.lost_item_workflow_service.send_email", new_callable=AsyncMock
        ) as mock_send_email:
            mock_send_email.return_value = False  # Email failed

            result = await service.mark_item_lost(
                checkout_id=overdue_checkout_for_lost.id,
                lost_type=LostItemType.LOST_BY_PATRON,
                reported_by=test_staff,
                send_notification=True,
            )

            # Item should still be marked lost successfully
            assert result.success is True
            assert result.notification_sent is False
            assert result.lost_item_record is not None
            assert result.fine is not None


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling in lost item marking."""

    @pytest.mark.asyncio
    async def test_cannot_mark_nonexistent_checkout_lost(self, test_db, test_staff):
        """Test that marking nonexistent checkout returns error."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)

        result = await service.mark_item_lost(
            checkout_id=99999,  # Nonexistent
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        assert result.success is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_cannot_mark_already_lost_item_lost_again(
        self, test_db, overdue_checkout_for_lost, test_staff
    ):
        """Test that already lost item cannot be marked lost again."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType

        service = LostItemWorkflowService(test_db)

        # Mark lost first time
        result1 = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )
        assert result1.success is True

        # Try to mark lost again
        result2 = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        assert result2.success is False
        assert "already marked as lost" in result2.message.lower()

    @pytest.mark.asyncio
    async def test_fine_linked_to_checkout_and_patron(
        self, test_db, overdue_checkout_for_lost, test_staff, patron_with_email
    ):
        """Test that fine is correctly linked to checkout and patron."""
        from app.services.lost_item_workflow_service import LostItemWorkflowService
        from app.models.lost_damaged import LostItemType
        from app.models.fine import Fine
        from sqlalchemy import select

        service = LostItemWorkflowService(test_db)

        result = await service.mark_item_lost(
            checkout_id=overdue_checkout_for_lost.id,
            lost_type=LostItemType.LOST_BY_PATRON,
            reported_by=test_staff,
            send_notification=False,
        )

        assert result.success is True

        # Verify fine exists in database with correct links
        query = select(Fine).where(Fine.id == result.fine.id)
        db_result = await test_db.execute(query)
        fine = db_result.scalar_one()

        assert fine.user_id == patron_with_email.id
        assert fine.checkout_id == overdue_checkout_for_lost.id
