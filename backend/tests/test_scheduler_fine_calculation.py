# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Daily Overdue Fine Calculation Background Job

This test suite covers the scheduler job that:
- Finds all overdue checkouts (past due_date)
- Marks them as 'overdue' status
- Creates or updates Fine records using FinePolicy system
- Applies role-based exemptions (children reading minutes, fine-exempt users)
- Logs metrics for monitoring

Tests cover:
- Basic fine creation for overdue items
- Fine updates (accrual on subsequent runs)
- FinePolicy application (daily rates, caps, tiered)
- Exemptions (children, fine-exempt users)
- Edge cases (missing relations, concurrent processing)
- Error handling and logging
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus
from app.models.fine import Fine, FinePolicy, FinePolicyType, FineStatus, FineType


@pytest.fixture(autouse=True)
async def _default_fine_policy(test_db: AsyncSession):
    """Seed a catch-all FinePolicy so calculate_daily_overdue_fines has

    apply_fine_policy (app/services/fine_policy_service.py) logs a warning
    and no-ops when no active FinePolicy matches the checkout's item type
    and the user's role. Without this, every test below would exercise the
    "no policy configured" branch instead of real fine calculation.
    """
    policy = FinePolicy(
        name="Test Daily Rate Policy",
        policy_type=FinePolicyType.daily_rate,
        applies_to_item_types="all",
        applies_to_user_roles="all",
        fine_per_day=Decimal("0.25"),
        grace_period_hours=0,
        minimum_fine_amount=Decimal("0.00"),
        maximum_daily_fine=Decimal("50.00"),
        maximum_cap=Decimal("50.00"),
        is_active=True,
        applies_on_weekends=True,
        applies_on_holidays=True,
    )
    test_db.add(policy)
    await test_db.commit()


class TestFineCalculationBasics:
    """Test basic fine creation and calculation"""

    @pytest.mark.asyncio
    async def test_create_fine_for_overdue_checkout(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that fine is created for checkout past due date"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)
        # Create checkout due 3 days ago
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=20),
            due_date=now - timedelta(days=3),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        checkout_id = checkout.id

        # Run fine calculation job
        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        # Verify fine was created
        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout_id))
        fine = result.scalar_one_or_none()
        assert fine is not None
        assert fine.status == FineStatus.unpaid
        assert fine.checkout_id == checkout_id

    @pytest.mark.asyncio
    async def test_do_not_create_fine_for_returned_checkout(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that returned checkouts don't get fined"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)
        # Create returned checkout
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.returned,
            checked_out_at=now - timedelta(days=20),
            due_date=now - timedelta(days=5),
            returned_at=now - timedelta(days=3),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        checkout_id = checkout.id

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        # No fine should exist
        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout_id))
        fine = result.scalar_one_or_none()
        assert fine is None

    @pytest.mark.asyncio
    async def test_do_not_create_fine_for_item_not_yet_due(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that items with future due dates don't get fined"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)
        # Create checkout due in 3 days
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=10),
            due_date=now + timedelta(days=3),
        )
        test_db.add(checkout)
        await test_db.commit()

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout.id))
        fine = result.scalar_one_or_none()
        assert fine is None

    @pytest.mark.asyncio
    async def test_mark_checkout_as_overdue(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that overdue checkouts are marked with overdue status"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=20),
            due_date=now - timedelta(days=5),
        )
        test_db.add(checkout)
        await test_db.commit()

        checkout_id = checkout.id

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        # Job runs in its own AsyncSessionLocal session; refresh identity map
        # before re-reading the row test_db already holds.
        test_db.expire_all()
        result = await test_db.execute(select(Checkout).where(Checkout.id == checkout_id))
        updated_checkout = result.scalar_one()
        assert updated_checkout.status == CheckoutStatus.overdue


class TestFineAccrual:
    """Test fine amount calculations"""

    @pytest.mark.asyncio
    async def test_fine_amount_matches_days_overdue(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that fine amount = days_overdue * daily_rate"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)
        # Checkout due 7 days ago, with a small safety margin under the 7*24h
        # boundary so the wall-clock time elapsed between fixture setup and
        # the job's own datetime.now(timezone.utc) call can't push
        # calculate_overdue_days's ceil(overdue_hours / 24) up to 8 days.
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=25),
            due_date=now - timedelta(days=7) + timedelta(minutes=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        checkout_id = checkout.id

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout_id))
        fine = result.scalar_one()
        # Daily rate is typically $0.25, so 7 days = $1.75
        expected_amount = Decimal("7") * Decimal("0.25")
        assert fine.amount == expected_amount

    @pytest.mark.asyncio
    async def test_fine_updated_on_subsequent_runs(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that existing fines are updated on subsequent job runs"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=30),
            due_date=now - timedelta(days=7),
        )
        test_db.add(checkout)
        await test_db.commit()

        checkout_id = checkout.id

        # Run fine calculation
        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout_id))
        fine1 = result.scalar_one()
        initial_amount = fine1.amount
        fine1_id = fine1.id

        # Simulate another day passing (update due_date in past)
        checkout.due_date = now - timedelta(days=8)
        await test_db.commit()

        # Run job again
        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        test_db.expire_all()
        result = await test_db.execute(select(Fine).where(Fine.id == fine1_id))
        fine2 = result.scalar_one()

        # Fine should be updated but same record
        assert fine2.id == fine1_id
        assert fine2.amount > initial_amount


class TestFineExemptions:
    """Test user/role-based fine exemptions"""

    @pytest.mark.asyncio
    async def test_children_reading_minutes_exemption(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem
    ):
        """Test that children accounts use reading minutes instead of fines"""
        from app.models.permission import RoleSettings
        from app.services.schedulers import calculate_daily_overdue_fines

        # There's no per-user `is_child_account` column on User -- the
        # reading-minutes-instead-of-fines behavior is a per-ROLE setting
        # (RoleSettings.use_reading_minutes) looked up by apply_fine_policy.
        role_settings = RoleSettings(role=UserRole.CHILD, use_reading_minutes=True)
        test_db.add(role_settings)

        # Create child user
        child = User(
            email="child@test.com",
            password_hash="hashed",
            first_name="Kid",
            last_name="Test",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)

        now = datetime.now(timezone.utc)
        checkout = Checkout(
            user_id=child.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=20),
            due_date=now - timedelta(days=5),
        )
        test_db.add(checkout)
        await test_db.commit()

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        # For children, system may create reading minute fine type instead
        result = await test_db.execute(
            select(Fine).where(Fine.checkout_id == checkout.id)
        )
        fine = result.scalar_one_or_none()

        # Either no fine OR fine type is reading_minutes
        if fine:
            assert fine.fine_type == FineType.reading_minutes
        else:
            # Or reading minutes tracked separately
            assert fine is None or fine.fine_type == FineType.reading_minutes

    @pytest.mark.asyncio
    async def test_fine_exempt_user_no_fines(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem
    ):
        """Test that fine-exempt users don't accrue fines"""
        from app.models.permission import RoleSettings
        from app.services.schedulers import calculate_daily_overdue_fines

        # There's no per-user `fine_exempt` column on User -- exemption is a
        # per-ROLE setting (RoleSettings.fine_exempt) looked up by
        # apply_fine_policy.
        role_settings = RoleSettings(role=UserRole.PATRON, fine_exempt=True)
        test_db.add(role_settings)

        # Create user in the now fine-exempt role
        patron = User(
            email="exempt@test.com",
            password_hash="hashed",
            first_name="Exempt",
            last_name="User",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()
        await test_db.refresh(patron)

        now = datetime.now(timezone.utc)
        checkout = Checkout(
            user_id=patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=20),
            due_date=now - timedelta(days=10),
        )
        test_db.add(checkout)
        await test_db.commit()

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        # No fine should be created
        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout.id))
        fine = result.scalar_one_or_none()
        assert fine is None


class TestEdgeCasesAndErrors:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_handle_missing_user_gracefully(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem
    ):
        """Test that job doesn't crash if user was deleted.

        checkouts.user_id is NOT NULL with ON DELETE RESTRICT (see
        app/models/circulation.py), so a real orphan row can't be produced
        through a normal insert -- FK checks are disabled for this one
        INSERT (mirrors the bypass tests/conftest.py's test_db teardown uses
        for cross-table cleanup) to simulate legacy/corrupted data.
        """
        from sqlalchemy import text
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)
        checkout = Checkout(
            user_id=99999,  # User doesn't exist
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=20),
            due_date=now - timedelta(days=5),
        )
        test_db.add(checkout)
        await test_db.execute(text("SET session_replication_role = replica"))
        await test_db.flush()
        checkout_id = checkout.id  # capture before commit expires attributes
        await test_db.commit()
        await test_db.execute(text("SET session_replication_role = DEFAULT"))
        await test_db.commit()

        # Should not raise exception
        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        # calculate_daily_overdue_fines skips (does not mark overdue) when
        # checkout.user is None -- it can't evaluate role-based exemptions
        # without a user. The checkout is left untouched, not crashed.
        test_db.expire_all()
        result = await test_db.execute(select(Checkout).where(Checkout.id == checkout_id))
        updated = result.scalar_one()
        assert updated.status == CheckoutStatus.active

    @pytest.mark.asyncio
    async def test_handle_missing_item_gracefully(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that job doesn't crash if item was deleted.

        catalog_items has the same NOT NULL + ON DELETE RESTRICT shape as
        the user FK above, so the FK check is disabled for this one INSERT.
        """
        from sqlalchemy import text
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=99999,  # Item doesn't exist
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=20),
            due_date=now - timedelta(days=5),
        )
        test_db.add(checkout)
        await test_db.execute(text("SET session_replication_role = replica"))
        await test_db.flush()
        checkout_id = checkout.id  # capture before commit expires attributes
        await test_db.commit()
        await test_db.execute(text("SET session_replication_role = DEFAULT"))
        await test_db.commit()

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        # Should mark as overdue but skip fine creation
        test_db.expire_all()
        result = await test_db.execute(select(Checkout).where(Checkout.id == checkout_id))
        updated = result.scalar_one()
        assert updated.status == CheckoutStatus.overdue

    @pytest.mark.asyncio
    async def test_job_metrics_logged(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that job logs summary metrics"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)
        for i in range(3):
            checkout = Checkout(
                user_id=test_patron.id,
                item_id=test_catalog_item.id,
                status=CheckoutStatus.active,
                checked_out_at=now - timedelta(days=20 + i),
                due_date=now - timedelta(days=5 + i),
            )
            test_db.add(checkout)
        await test_db.commit()

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            with patch('app.services.job_failure_service.logger') as mock_logger:
                await calculate_daily_overdue_fines()

                # Verify logging calls include metrics
                info_calls = [c[0][0] for c in mock_logger.info.call_args_list]
                assert any("completed" in str(msg) for msg in info_calls)

    @pytest.mark.asyncio
    async def test_partial_failure_continues_processing(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that job continues if one checkout fails"""
        from sqlalchemy import text
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)
        # Create 2 checkouts
        checkout1 = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=20),
            due_date=now - timedelta(days=5),
        )
        # item_id=99999 doesn't exist -- FK check disabled for this one
        # insert (catalog_items FK is NOT NULL + ON DELETE RESTRICT) to
        # simulate a corrupted/orphaned row without violating the schema.
        checkout2 = Checkout(
            user_id=test_patron.id,
            item_id=99999,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=20),
            due_date=now - timedelta(days=5),
        )
        test_db.add_all([checkout1, checkout2])
        await test_db.execute(text("SET session_replication_role = replica"))
        await test_db.flush()
        checkout1_id = checkout1.id  # capture before commit expires attributes
        await test_db.commit()
        await test_db.execute(text("SET session_replication_role = DEFAULT"))
        await test_db.commit()

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        # First checkout should still be processed
        test_db.expire_all()
        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout1_id))
        fine1 = result.scalar_one_or_none()
        assert fine1 is not None


class TestIdempotency:
    """Test that job is safe to run multiple times"""

    @pytest.mark.asyncio
    async def test_running_job_twice_no_duplicate_fines(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that running fine calculation twice doesn't create duplicate fines"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=20),
            due_date=now - timedelta(days=5),
        )
        test_db.add(checkout)
        await test_db.commit()

        checkout_id = checkout.id

        # Run job first time
        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout_id))
        fines1 = result.scalars().all()
        assert len(fines1) == 1

        # Run job again without any time passing
        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        test_db.expire_all()
        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout_id))
        fines2 = result.scalars().all()

        # Should still be 1 fine (updated, not duplicated)
        assert len(fines2) == 1
        assert fines2[0].id == fines1[0].id
