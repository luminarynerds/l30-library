# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for patron suspension functionality.

Tests cover:
- PatronStatus enum values
- Suspension/block/unblock operations
- Auto-suspension for overdue items
- Auto-lift of suspensions
- Circulation restrictions for suspended patrons
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.user import User, UserRole, PatronStatus


@pytest.mark.unit
class TestPatronStatusEnum:
    """Test PatronStatus enum."""

    def test_patron_status_values(self):
        """Test PatronStatus has expected values."""
        assert PatronStatus.ACTIVE.value == "active"
        assert PatronStatus.SUSPENDED.value == "suspended"
        assert PatronStatus.BLOCKED.value == "blocked"
        assert PatronStatus.DECEASED.value == "deceased"

    def test_patron_status_order(self):
        """Test PatronStatus enum order matches documentation."""
        statuses = list(PatronStatus)
        assert statuses[0] == PatronStatus.ACTIVE
        assert statuses[1] == PatronStatus.SUSPENDED
        assert statuses[2] == PatronStatus.BLOCKED
        assert statuses[3] == PatronStatus.DECEASED


@pytest.mark.unit
class TestUserSuspensionProperties:
    """Test User model suspension properties."""

    async def test_is_suspended_property(self, test_db, test_patron):
        """Test is_suspended property."""
        assert test_patron.is_suspended is False

        test_patron.patron_status = PatronStatus.SUSPENDED
        assert test_patron.is_suspended is True

    async def test_is_blocked_property(self, test_db, test_patron):
        """Test is_blocked property."""
        assert test_patron.is_blocked is False

        test_patron.patron_status = PatronStatus.BLOCKED
        assert test_patron.is_blocked is True

    async def test_should_lift_suspension_no_date(self, test_db, test_patron):
        """Test should_lift_suspension returns False when no date set."""
        test_patron.patron_status = PatronStatus.SUSPENDED
        test_patron.suspended_until = None

        assert test_patron.should_lift_suspension() is False

    async def test_should_lift_suspension_future_date(self, test_db, test_patron):
        """Test should_lift_suspension returns False for future date."""
        test_patron.patron_status = PatronStatus.SUSPENDED
        test_patron.suspended_until = datetime.now(timezone.utc) + timedelta(days=7)

        assert test_patron.should_lift_suspension() is False

    async def test_should_lift_suspension_past_date(self, test_db, test_patron):
        """Test should_lift_suspension returns True for past date."""
        test_patron.patron_status = PatronStatus.SUSPENDED
        test_patron.suspended_until = datetime.now(timezone.utc) - timedelta(hours=1)

        assert test_patron.should_lift_suspension() is True

    async def test_should_lift_suspension_not_suspended(self, test_db, test_patron):
        """Test should_lift_suspension returns False if not suspended."""
        test_patron.patron_status = PatronStatus.ACTIVE
        test_patron.suspended_until = datetime.now(timezone.utc) - timedelta(hours=1)

        assert test_patron.should_lift_suspension() is False

    async def test_can_circulate_when_active(self, test_db, test_patron):
        """Test can_circulate is True when active."""
        test_patron.patron_status = PatronStatus.ACTIVE
        test_patron.is_active = True

        assert test_patron.can_circulate is True

    async def test_can_circulate_when_suspended(self, test_db, test_patron):
        """Test can_circulate is False when suspended."""
        test_patron.patron_status = PatronStatus.SUSPENDED

        assert test_patron.can_circulate is False

    async def test_can_circulate_when_blocked(self, test_db, test_patron):
        """Test can_circulate is False when blocked."""
        test_patron.patron_status = PatronStatus.BLOCKED

        assert test_patron.can_circulate is False

    async def test_can_circulate_when_deceased(self, test_db, test_patron):
        """Test can_circulate is False when deceased."""
        test_patron.patron_status = PatronStatus.DECEASED

        assert test_patron.can_circulate is False


@pytest.mark.unit
class TestSuspensionService:
    """Test suspension service functions."""

    async def test_suspend_patron(self, test_db, test_patron):
        """Test suspending a patron account."""
        from app.services.suspension_service import suspend_patron

        await suspend_patron(
            patron=test_patron,
            db=test_db,
            reason="Test suspension reason",
            suspended_by_id=None,
            suspended_until=datetime.now(timezone.utc) + timedelta(days=7),
        )

        assert test_patron.patron_status == PatronStatus.SUSPENDED
        assert test_patron.suspension_reason == "Test suspension reason"
        assert test_patron.suspended_until is not None
        assert test_patron.is_active is False

    async def test_suspend_patron_without_expiry(self, test_db, test_patron):
        """Test suspending a patron without an expiry date."""
        from app.services.suspension_service import suspend_patron

        await suspend_patron(
            patron=test_patron,
            db=test_db,
            reason="Indefinite suspension",
            suspended_by_id=None,
            suspended_until=None,
        )

        assert test_patron.patron_status == PatronStatus.SUSPENDED
        assert test_patron.suspended_until is None

    async def test_lift_suspension(self, test_db, test_patron):
        """Test lifting a suspension."""
        from app.services.suspension_service import suspend_patron, lift_suspension

        # First suspend
        await suspend_patron(
            patron=test_patron,
            db=test_db,
            reason="Test suspension",
            suspended_by_id=None,
        )

        # Then lift
        await lift_suspension(
            patron=test_patron,
            db=test_db,
            lifted_by_id=None,
            auto=True,
        )

        assert test_patron.patron_status == PatronStatus.ACTIVE
        assert test_patron.suspension_reason is None
        assert test_patron.suspended_until is None
        assert test_patron.is_active is True

    async def test_block_patron(self, test_db, test_patron, test_staff):
        """Test blocking a patron account."""
        from app.services.suspension_service import block_patron

        await block_patron(
            patron=test_patron,
            db=test_db,
            reason="Policy violation",
            blocked_by_id=test_staff.id,
        )

        assert test_patron.patron_status == PatronStatus.BLOCKED
        assert test_patron.block_reason == "Policy violation"
        assert test_patron.blocked_by_id == test_staff.id
        assert test_patron.is_active is False

    async def test_unblock_patron(self, test_db, test_patron, test_staff):
        """Test unblocking a patron account."""
        from app.services.suspension_service import block_patron, unblock_patron

        # First block
        await block_patron(
            patron=test_patron,
            db=test_db,
            reason="Policy violation",
            blocked_by_id=test_staff.id,
        )

        # Then unblock
        await unblock_patron(
            patron=test_patron,
            db=test_db,
            unblocked_by_id=test_staff.id,
        )

        assert test_patron.patron_status == PatronStatus.ACTIVE
        assert test_patron.block_reason is None
        assert test_patron.is_active is True

    async def test_cannot_suspend_deceased_patron(self, test_db, test_patron):
        """Test that deceased patrons cannot be suspended."""
        from app.services.suspension_service import suspend_patron
        from app.core.exceptions import ConflictError

        test_patron.patron_status = PatronStatus.DECEASED

        with pytest.raises(ConflictError):
            await suspend_patron(
                patron=test_patron,
                db=test_db,
                reason="Test",
                suspended_by_id=None,
            )

    async def test_cannot_block_deceased_patron(self, test_db, test_patron, test_staff):
        """Test that deceased patrons cannot be blocked."""
        from app.services.suspension_service import block_patron
        from app.core.exceptions import ConflictError

        test_patron.patron_status = PatronStatus.DECEASED

        with pytest.raises(ConflictError):
            await block_patron(
                patron=test_patron,
                db=test_db,
                reason="Test",
                blocked_by_id=test_staff.id,
            )


@pytest.mark.unit
class TestSuspensionStatusCheck:
    """Test patron suspension status checking."""

    async def test_check_active_patron(self, test_db, test_patron):
        """Test checking status of active patron."""
        from app.services.suspension_service import check_patron_suspension_status

        can_circulate, reason, error_code = await check_patron_suspension_status(
            test_patron, test_db
        )

        assert can_circulate is True
        assert reason is None
        assert error_code is None

    async def test_check_suspended_patron(self, test_db, test_patron):
        """Test checking status of suspended patron."""
        from app.services.suspension_service import check_patron_suspension_status
        from app.core.error_codes import ErrorCode

        test_patron.patron_status = PatronStatus.SUSPENDED
        test_patron.suspension_reason = "Overdue items"

        can_circulate, reason, error_code = await check_patron_suspension_status(
            test_patron, test_db
        )

        assert can_circulate is False
        assert "Overdue items" in reason
        assert error_code == ErrorCode.PATRON_ACCOUNT_SUSPENDED

    async def test_check_blocked_patron(self, test_db, test_patron):
        """Test checking status of blocked patron."""
        from app.services.suspension_service import check_patron_suspension_status
        from app.core.error_codes import ErrorCode

        test_patron.patron_status = PatronStatus.BLOCKED
        test_patron.block_reason = "Policy violation"

        can_circulate, reason, error_code = await check_patron_suspension_status(
            test_patron, test_db
        )

        assert can_circulate is False
        assert "Policy violation" in reason
        assert error_code == ErrorCode.PATRON_BLOCKED

    async def test_check_deceased_patron(self, test_db, test_patron):
        """Test checking status of deceased patron."""
        from app.services.suspension_service import check_patron_suspension_status
        from app.core.error_codes import ErrorCode

        test_patron.patron_status = PatronStatus.DECEASED

        can_circulate, reason, error_code = await check_patron_suspension_status(
            test_patron, test_db
        )

        assert can_circulate is False
        assert "deceased" in reason.lower()
        assert error_code == ErrorCode.PATRON_DECEASED

    async def test_auto_lift_expired_suspension(self, test_db, test_patron):
        """Test that expired suspensions are auto-lifted during status check."""
        from app.services.suspension_service import check_patron_suspension_status

        # suspend_patron() always sets suspended_at=now, so it can't produce a
        # suspended_until in the past without violating
        # ck_user_suspended_until_after_suspended_at. Construct the
        # already-expired state directly instead.
        test_patron.patron_status = PatronStatus.SUSPENDED
        test_patron.suspension_reason = "Test suspension"
        test_patron.suspended_at = datetime.now(timezone.utc) - timedelta(hours=2)
        test_patron.suspended_until = datetime.now(timezone.utc) - timedelta(hours=1)
        test_patron.is_active = False
        test_db.add(test_patron)
        await test_db.flush()

        # Check status should auto-lift
        can_circulate, reason, error_code = await check_patron_suspension_status(
            test_patron, test_db
        )

        assert can_circulate is True
        assert test_patron.patron_status == PatronStatus.ACTIVE


@pytest.mark.unit
class TestProcessExpiredSuspensions:
    """Test scheduled job for processing expired suspensions."""

    async def test_process_expired_suspensions(self, test_db, test_patron):
        """Test processing expired suspensions."""
        from app.services.suspension_service import (
            suspend_patron,
            process_expired_suspensions,
        )

        # Suspend with past expiry date
        test_patron.patron_status = PatronStatus.SUSPENDED
        test_patron.suspension_reason = "Test"
        test_patron.suspended_until = datetime.now(timezone.utc) - timedelta(hours=1)
        test_patron.is_active = False
        await test_db.commit()

        # Process expired suspensions
        lifted_count = await process_expired_suspensions(test_db)

        await test_db.refresh(test_patron)

        assert lifted_count >= 1
        assert test_patron.patron_status == PatronStatus.ACTIVE
        assert test_patron.is_active is True

    async def test_does_not_lift_unexpired_suspensions(self, test_db, test_patron):
        """Test that unexpired suspensions are not lifted."""
        from app.services.suspension_service import (
            suspend_patron,
            process_expired_suspensions,
        )

        # Suspend with future expiry date
        test_patron.patron_status = PatronStatus.SUSPENDED
        test_patron.suspension_reason = "Test"
        test_patron.suspended_until = datetime.now(timezone.utc) + timedelta(days=7)
        test_patron.is_active = False
        await test_db.commit()

        # Process expired suspensions
        await process_expired_suspensions(test_db)

        await test_db.refresh(test_patron)

        # Should still be suspended
        assert test_patron.patron_status == PatronStatus.SUSPENDED
