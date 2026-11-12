# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Hold Expiration Logic

This test suite covers the hold expiration service functions which:
- Find expired holds (ready past expires_at)
- Mark them as expired
- Advance the hold queue
- Update item availability

Tests cover:
- Basic hold expiration
- Queue advancement when holds expire
- Item release when no more holds
- Edge cases (null fields, missing relations)
- Helper functions (get_effective_expiration, is_hold_expired)
- Legacy data cleanup (fix_null_expires_at_holds)
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Hold, HoldStatus


class TestHoldExpiration:
    """Test hold expiration functionality via service-layer functions"""

    @pytest.mark.asyncio
    async def test_expire_ready_hold_past_expiry_date(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that ready holds past expiry date are marked as expired"""
        from app.services.hold_service import process_expired_holds

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=8),
            notified_at=now - timedelta(days=1),
            expires_at=now - timedelta(days=1),
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        hold_id = hold.id
        count = await process_expired_holds(test_db)
        await test_db.commit()

        assert count == 1
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        expired_hold = result.scalar_one()
        assert expired_hold.status == HoldStatus.expired

    @pytest.mark.asyncio
    async def test_do_not_expire_hold_before_expiry_date(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that holds before expiry date are NOT marked as expired"""
        from app.services.hold_service import process_expired_holds

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=6),
            notified_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=1),
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        hold_id = hold.id
        count = await process_expired_holds(test_db)
        await test_db.commit()

        assert count == 0
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        hold_after = result.scalar_one()
        assert hold_after.status == HoldStatus.ready

    @pytest.mark.asyncio
    async def test_advance_queue_when_ready_hold_expires(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that next pending hold is promoted when ready hold expires"""
        from app.services.hold_service import process_expired_holds

        patron1 = test_patron
        now = datetime.now(timezone.utc)

        hold1 = Hold(
            user_id=patron1.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=8),
            notified_at=now - timedelta(days=1),
            expires_at=now - timedelta(days=1),
        )
        test_db.add(hold1)
        await test_db.commit()

        patron2 = User(
            email="patron2@example.com",
            password_hash="hashed_password",
            first_name="Patron",
            last_name="Two",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron2)
        await test_db.commit()
        await test_db.refresh(patron2)

        hold2 = Hold(
            user_id=patron2.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=2,
            created_at=now - timedelta(days=7),
        )
        test_db.add(hold2)
        await test_db.commit()
        await test_db.refresh(hold1)
        await test_db.refresh(hold2)

        hold1_id = hold1.id
        hold2_id = hold2.id

        count = await process_expired_holds(test_db)
        await test_db.commit()

        assert count == 1

        result1 = await test_db.execute(select(Hold).where(Hold.id == hold1_id))
        expired_hold = result1.scalar_one()
        assert expired_hold.status == HoldStatus.expired

        result2 = await test_db.execute(select(Hold).where(Hold.id == hold2_id))
        promoted_hold = result2.scalar_one()
        assert promoted_hold.status == HoldStatus.ready
        assert promoted_hold.notified_at is not None
        assert promoted_hold.expires_at is not None

    @pytest.mark.asyncio
    async def test_release_item_when_last_hold_expires(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that item is released to available when last hold in queue expires"""
        from app.services.hold_service import process_expired_holds

        test_catalog_item.status = ItemStatus.on_hold
        test_db.add(test_catalog_item)
        await test_db.commit()

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=8),
            notified_at=now - timedelta(days=1),
            expires_at=now - timedelta(days=1),
        )
        test_db.add(hold)
        await test_db.commit()

        item_id = test_catalog_item.id

        count = await process_expired_holds(test_db)
        await test_db.commit()

        assert count == 1
        result = await test_db.execute(
            select(CatalogItem).where(CatalogItem.id == item_id)
        )
        item = result.scalar_one()
        assert item.status == ItemStatus.available

    @pytest.mark.asyncio
    async def test_skip_already_expired_holds(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that already expired holds are not reprocessed"""
        from app.services.hold_service import process_expired_holds

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.expired,
            position=1,
            created_at=now - timedelta(days=10),
            expires_at=now - timedelta(days=3),
        )
        test_db.add(hold)
        await test_db.commit()

        hold_id = hold.id
        count = await process_expired_holds(test_db)
        await test_db.commit()

        assert count == 0
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        hold_after = result.scalar_one()
        assert hold_after.status == HoldStatus.expired

    @pytest.mark.asyncio
    async def test_expire_hold_with_null_expires_at_but_old_notified_at(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that holds with NULL expires_at but old notified_at ARE expired"""
        from app.services.hold_service import process_expired_holds, HOLD_EXPIRY_DAYS

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=30),
            notified_at=now - timedelta(days=HOLD_EXPIRY_DAYS + 1),
            expires_at=None,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        hold_id = hold.id
        count = await process_expired_holds(test_db)
        await test_db.commit()

        assert count == 1
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        hold_after = result.scalar_one()
        assert hold_after.status == HoldStatus.expired

    @pytest.mark.asyncio
    async def test_skip_holds_without_expires_at_and_recent_notified_at(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that holds with NULL expires_at but recent notified_at are not expired"""
        from app.services.hold_service import process_expired_holds

        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
            notified_at=datetime.now(timezone.utc),
            expires_at=None,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        hold_id = hold.id
        count = await process_expired_holds(test_db)
        await test_db.commit()

        assert count == 0
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        hold_after = result.scalar_one()
        assert hold_after.status == HoldStatus.ready

    @pytest.mark.asyncio
    async def test_skip_holds_without_expires_at_and_notified_at(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that holds with NULL expires_at AND NULL notified_at are skipped"""
        from app.services.hold_service import process_expired_holds

        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
            notified_at=None,
            expires_at=None,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        hold_id = hold.id
        count = await process_expired_holds(test_db)
        await test_db.commit()

        assert count == 0
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        hold_after = result.scalar_one()
        assert hold_after.status == HoldStatus.ready

    @pytest.mark.asyncio
    async def test_skip_fulfilled_holds(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that fulfilled holds are not reprocessed"""
        from app.services.hold_service import process_expired_holds

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.fulfilled,
            position=1,
            created_at=now - timedelta(days=10),
            expires_at=now - timedelta(days=3),
        )
        test_db.add(hold)
        await test_db.commit()

        hold_id = hold.id
        count = await process_expired_holds(test_db)
        await test_db.commit()

        assert count == 0
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        hold_after = result.scalar_one()
        assert hold_after.status == HoldStatus.fulfilled

    @pytest.mark.asyncio
    async def test_skip_cancelled_holds(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that cancelled holds are not reprocessed"""
        from app.services.hold_service import process_expired_holds

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.cancelled,
            position=1,
            created_at=now - timedelta(days=10),
            expires_at=now - timedelta(days=3),
        )
        test_db.add(hold)
        await test_db.commit()

        hold_id = hold.id
        count = await process_expired_holds(test_db)
        await test_db.commit()

        assert count == 0
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        hold_after = result.scalar_one()
        assert hold_after.status == HoldStatus.cancelled

    @pytest.mark.asyncio
    async def test_multiple_holds_on_same_item(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem
    ):
        """Test queue advancement with multiple holds on same item"""
        from app.services.hold_service import process_expired_holds

        now = datetime.now(timezone.utc)

        patrons = []
        for i in range(3):
            patron = User(
                email=f"patron{i}@example.com",
                password_hash="hashed_password",
                first_name=f"Patron{i}",
                last_name="Test",
                role=UserRole.PATRON,
                is_active=True,
                email_verified=True,
            )
            test_db.add(patron)
            patrons.append(patron)
        await test_db.commit()

        for p in patrons:
            await test_db.refresh(p)

        hold1 = Hold(
            user_id=patrons[0].id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=8),
            notified_at=now - timedelta(days=1),
            expires_at=now - timedelta(days=1),
        )
        hold2 = Hold(
            user_id=patrons[1].id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=2,
            created_at=now - timedelta(days=7),
        )
        hold3 = Hold(
            user_id=patrons[2].id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=3,
            created_at=now - timedelta(days=6),
        )

        test_db.add_all([hold1, hold2, hold3])
        await test_db.commit()

        hold1_id, hold2_id, hold3_id = hold1.id, hold2.id, hold3.id

        count = await process_expired_holds(test_db)
        await test_db.commit()

        assert count == 1

        result1 = await test_db.execute(select(Hold).where(Hold.id == hold1_id))
        h1 = result1.scalar_one()
        assert h1.status == HoldStatus.expired

        result2 = await test_db.execute(select(Hold).where(Hold.id == hold2_id))
        h2 = result2.scalar_one()
        assert h2.status == HoldStatus.ready

        result3 = await test_db.execute(select(Hold).where(Hold.id == hold3_id))
        h3 = result3.scalar_one()
        assert h3.status == HoldStatus.pending

    @pytest.mark.asyncio
    async def test_process_expired_holds_for_specific_item(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test processing expired holds for a specific item only"""
        from app.services.hold_service import process_expired_holds

        now = datetime.now(timezone.utc)

        # Create another item
        other_item = CatalogItem(
            title="Other Book",
            author="Other Author",
            isbn="978-0-987654-32-1",
            description="Another test book",
            status=ItemStatus.on_hold,
            call_number="TEST-002",
            publication_year=2024,
        )
        test_db.add(other_item)
        await test_db.commit()
        await test_db.refresh(other_item)

        # Create expired hold on target item
        hold1 = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=8),
            notified_at=now - timedelta(days=1),
            expires_at=now - timedelta(days=1),
        )

        # Create another patron for the other item
        patron2 = User(
            email="patron2@example.com",
            password_hash="hashed_password",
            first_name="Patron",
            last_name="Two",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron2)
        await test_db.commit()
        await test_db.refresh(patron2)

        # Create expired hold on other item
        hold2 = Hold(
            user_id=patron2.id,
            item_id=other_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=8),
            notified_at=now - timedelta(days=1),
            expires_at=now - timedelta(days=1),
        )
        test_db.add_all([hold1, hold2])
        await test_db.commit()

        hold1_id = hold1.id
        hold2_id = hold2.id

        # Process only for test_catalog_item
        count = await process_expired_holds(test_db, item_id=test_catalog_item.id)
        await test_db.commit()

        assert count == 1

        result1 = await test_db.execute(select(Hold).where(Hold.id == hold1_id))
        assert result1.scalar_one().status == HoldStatus.expired

        result2 = await test_db.execute(select(Hold).where(Hold.id == hold2_id))
        assert result2.scalar_one().status == HoldStatus.ready  # Untouched

    @pytest.mark.asyncio
    async def test_check_and_expire_single_hold(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test single hold expiration check"""
        from app.services.hold_service import check_and_expire_hold

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=8),
            notified_at=now - timedelta(days=1),
            expires_at=now - timedelta(days=1),
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        hold_id = hold.id
        was_expired = await check_and_expire_hold(hold, test_db)
        await test_db.commit()

        assert was_expired is True
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        assert result.scalar_one().status == HoldStatus.expired

    @pytest.mark.asyncio
    async def test_check_and_expire_hold_not_expired(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that non-expired hold is not changed"""
        from app.services.hold_service import check_and_expire_hold

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=6),
            notified_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=6),
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        was_expired = await check_and_expire_hold(hold, test_db)
        await test_db.commit()

        assert was_expired is False
        assert hold.status == HoldStatus.ready


class TestHoldExpirationHelpers:
    """Test helper functions for hold expiration logic"""

    def test_get_effective_expiration_with_expires_at(self):
        """Test that expires_at is returned when set"""
        from app.services.hold_service import get_effective_expiration

        now = datetime.now(timezone.utc)
        hold = Hold(
            status=HoldStatus.ready,
            expires_at=now + timedelta(days=3),
            notified_at=now - timedelta(days=4),
        )
        result = get_effective_expiration(hold)
        assert result == hold.expires_at

    def test_get_effective_expiration_with_null_expires_at_uses_notified_at(self):
        """Test that notified_at + HOLD_EXPIRY_DAYS is used when expires_at is NULL"""
        from app.services.hold_service import get_effective_expiration, HOLD_EXPIRY_DAYS

        now = datetime.now(timezone.utc)
        notified_time = now - timedelta(days=5)
        hold = Hold(
            status=HoldStatus.ready,
            expires_at=None,
            notified_at=notified_time,
        )
        result = get_effective_expiration(hold)
        expected = notified_time + timedelta(days=HOLD_EXPIRY_DAYS)
        assert result == expected

    def test_get_effective_expiration_with_both_null(self):
        """Test that None is returned when both expires_at and notified_at are NULL"""
        from app.services.hold_service import get_effective_expiration

        hold = Hold(
            status=HoldStatus.ready,
            expires_at=None,
            notified_at=None,
        )
        result = get_effective_expiration(hold)
        assert result is None

    def test_is_hold_expired_with_past_expiration(self):
        """Test that hold is expired when expiration is in the past"""
        from app.services.hold_service import is_hold_expired

        now = datetime.now(timezone.utc)
        hold = Hold(
            status=HoldStatus.ready,
            expires_at=now - timedelta(hours=1),
        )
        assert is_hold_expired(hold, now) is True

    def test_is_hold_expired_with_future_expiration(self):
        """Test that hold is not expired when expiration is in the future"""
        from app.services.hold_service import is_hold_expired

        now = datetime.now(timezone.utc)
        hold = Hold(
            status=HoldStatus.ready,
            expires_at=now + timedelta(hours=1),
        )
        assert is_hold_expired(hold, now) is False

    def test_is_hold_expired_with_non_ready_status(self):
        """Test that non-ready holds are never considered expired"""
        from app.services.hold_service import is_hold_expired

        now = datetime.now(timezone.utc)
        for status in [HoldStatus.pending, HoldStatus.fulfilled, HoldStatus.cancelled, HoldStatus.expired]:
            hold = Hold(
                status=status,
                expires_at=now - timedelta(days=10),
            )
            assert is_hold_expired(hold, now) is False

    def test_is_hold_expired_with_null_expires_at_and_old_notified_at(self):
        """Test that hold with NULL expires_at but old notified_at is expired"""
        from app.services.hold_service import is_hold_expired, HOLD_EXPIRY_DAYS

        now = datetime.now(timezone.utc)
        hold = Hold(
            status=HoldStatus.ready,
            expires_at=None,
            notified_at=now - timedelta(days=HOLD_EXPIRY_DAYS + 1),
        )
        assert is_hold_expired(hold, now) is True

    def test_is_hold_expired_with_null_expires_at_and_recent_notified_at(self):
        """Test that hold with NULL expires_at but recent notified_at is not expired"""
        from app.services.hold_service import is_hold_expired

        now = datetime.now(timezone.utc)
        hold = Hold(
            status=HoldStatus.ready,
            expires_at=None,
            notified_at=now - timedelta(days=3),
        )
        assert is_hold_expired(hold, now) is False

    @pytest.mark.asyncio
    async def test_fix_null_expires_at_holds_with_notified_at(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that fix_null_expires_at_holds sets expires_at based on notified_at"""
        from app.services.hold_service import fix_null_expires_at_holds, HOLD_EXPIRY_DAYS

        now = datetime.now(timezone.utc)
        notified_time = now - timedelta(days=3)

        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            notified_at=notified_time,
            expires_at=None,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        hold_id = hold.id
        fixed_count = await fix_null_expires_at_holds(test_db)
        await test_db.commit()

        assert fixed_count == 1
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        fixed_hold = result.scalar_one()
        expected_expiration = notified_time + timedelta(days=HOLD_EXPIRY_DAYS)
        # Compare without timezone info since SQLite strips it
        actual = fixed_hold.expires_at.replace(tzinfo=None) if fixed_hold.expires_at else None
        expected = expected_expiration.replace(tzinfo=None) if expected_expiration else None
        assert actual == expected

    @pytest.mark.asyncio
    async def test_fix_null_expires_at_holds_with_null_notified_at(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that fix_null_expires_at_holds sets both notified_at and expires_at when both are NULL"""
        from app.services.hold_service import fix_null_expires_at_holds, HOLD_EXPIRY_DAYS

        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            notified_at=None,
            expires_at=None,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        hold_id = hold.id
        fixed_count = await fix_null_expires_at_holds(test_db)
        await test_db.commit()

        assert fixed_count == 1
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        fixed_hold = result.scalar_one()
        assert fixed_hold.notified_at is not None
        assert fixed_hold.expires_at is not None
        # Compare without timezone info since SQLite strips it
        exp_at = fixed_hold.expires_at.replace(tzinfo=None) if fixed_hold.expires_at else None
        not_at = fixed_hold.notified_at.replace(tzinfo=None) if fixed_hold.notified_at else None
        assert exp_at == not_at + timedelta(days=HOLD_EXPIRY_DAYS)

    @pytest.mark.asyncio
    async def test_fix_null_expires_at_holds_skips_non_ready(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that fix_null_expires_at_holds only fixes ready holds"""
        from app.services.hold_service import fix_null_expires_at_holds

        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
            notified_at=None,
            expires_at=None,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        hold_id = hold.id
        fixed_count = await fix_null_expires_at_holds(test_db)
        await test_db.commit()

        assert fixed_count == 0
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        unfixed_hold = result.scalar_one()
        assert unfixed_hold.expires_at is None
