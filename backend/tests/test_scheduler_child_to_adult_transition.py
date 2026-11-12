# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Child-to-Adult Account Transition Background Job

This test suite covers the scheduler job that:
- Finds all users with role=CHILD who have reached the transition age threshold
- Transitions them to PATRON role
- Clears parental consent requirements
- Optionally forgives reading minutes owed
- Sends notifications to patrons and parents/guardians
- Creates audit log entries

Tests cover:
- Basic transition for users at threshold age
- Users below threshold not transitioned
- Parental consent fields cleared
- Reading minutes handling (forgive vs. keep)
- Audit log creation
- Notification sending (patron and parent)
- Configurable transition age
- Disabled transitions via settings
- Edge cases (missing date of birth, inactive users)
- Idempotency (running twice doesn't double-process)
"""

import pytest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.audit_log import AuditLog, AuditAction
from app.models.multi_branch import SystemSettings, LibrarySystem
from app.models.permission import RoleSettings


class TestChildToAdultTransitionBasics:
    """Test basic transition functionality"""

    @pytest.mark.asyncio
    async def test_transition_user_at_18(self, test_db: AsyncSession):
        """Test that a CHILD user who turned 18 gets transitioned to PATRON"""
        from app.services.schedulers import process_child_to_adult_transitions

        # Create a child user who turned 18 today
        today = date.today()
        birth_date = date(today.year - 18, today.month, today.day)

        child = User(
            email="child18@test.com",
            password_hash="hashed",
            first_name="Eighteen",
            last_name="Today",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            date_of_birth=birth_date,
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)
        child_id = child.id

        # Run transition job
        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True):
            await process_child_to_adult_transitions()

        # Verify transition (job runs in its own session; refresh identity map)
        test_db.expire_all()
        result = await test_db.execute(select(User).where(User.id == child_id))
        updated_user = result.scalar_one()
        assert updated_user.role == UserRole.PATRON

    @pytest.mark.asyncio
    async def test_no_transition_user_under_18(self, test_db: AsyncSession):
        """Test that a CHILD user under 18 is not transitioned"""
        from app.services.schedulers import process_child_to_adult_transitions

        # Create a child user who is 17
        today = date.today()
        birth_date = date(today.year - 17, today.month, today.day)

        child = User(
            email="child17@test.com",
            password_hash="hashed",
            first_name="Seventeen",
            last_name="Years",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            date_of_birth=birth_date,
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)
        child_id = child.id

        # Run transition job
        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True):
            await process_child_to_adult_transitions()

        # Verify no transition
        result = await test_db.execute(select(User).where(User.id == child_id))
        user = result.scalar_one()
        assert user.role == UserRole.CHILD

    @pytest.mark.asyncio
    async def test_transition_user_already_over_18(self, test_db: AsyncSession):
        """Test that a CHILD user who is 19 gets transitioned (catch-up)"""
        from app.services.schedulers import process_child_to_adult_transitions

        # Create a child user who is 19 (missed previous transitions)
        today = date.today()
        birth_date = date(today.year - 19, today.month, today.day)

        child = User(
            email="child19@test.com",
            password_hash="hashed",
            first_name="Nineteen",
            last_name="Years",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            date_of_birth=birth_date,
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)
        child_id = child.id

        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True):
            await process_child_to_adult_transitions()

        test_db.expire_all()
        result = await test_db.execute(select(User).where(User.id == child_id))
        updated_user = result.scalar_one()
        assert updated_user.role == UserRole.PATRON


class TestParentalConsentClearing:
    """Test that parental consent fields are properly cleared"""

    @pytest.mark.asyncio
    async def test_parental_consent_fields_cleared(self, test_db: AsyncSession):
        """Test that all parental consent fields are cleared on transition"""
        from app.services.schedulers import process_child_to_adult_transitions

        today = date.today()
        birth_date = date(today.year - 18, today.month, today.day)

        child = User(
            email="consent_clear@test.com",
            password_hash="hashed",
            first_name="Consent",
            last_name="Clear",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            date_of_birth=birth_date,
            # Set parental consent fields
            parental_consent_given=True,
            parental_consent_date=datetime.now(timezone.utc),
            parental_consent_email="parent@test.com",
            parental_consent_token="sometoken",
            parental_consent_token_expires=datetime.now(timezone.utc) + timedelta(days=7),
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)
        child_id = child.id

        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True):
            await process_child_to_adult_transitions()

        test_db.expire_all()
        result = await test_db.execute(select(User).where(User.id == child_id))
        updated_user = result.scalar_one()

        # All parental consent fields should be cleared
        assert updated_user.parental_consent_given == False
        assert updated_user.parental_consent_date is None
        assert updated_user.parental_consent_email is None
        assert updated_user.parental_consent_token is None
        assert updated_user.parental_consent_token_expires is None


class TestReadingMinutesHandling:
    """Test reading minutes handling during transition"""

    @pytest.mark.asyncio
    async def test_reading_minutes_forgiven_by_default(self, test_db: AsyncSession):
        """Test that reading minutes are forgiven on transition (default behavior)"""
        from app.services.schedulers import process_child_to_adult_transitions

        today = date.today()
        birth_date = date(today.year - 18, today.month, today.day)

        child = User(
            email="reading_forgive@test.com",
            password_hash="hashed",
            first_name="Reading",
            last_name="Forgive",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            date_of_birth=birth_date,
            reading_minutes_owed=60,
            reading_minutes_logged=30,
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)
        child_id = child.id

        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True):
            await process_child_to_adult_transitions()

        test_db.expire_all()
        result = await test_db.execute(select(User).where(User.id == child_id))
        updated_user = result.scalar_one()

        # Reading minutes should be cleared
        assert updated_user.reading_minutes_owed == 0
        assert updated_user.reading_minutes_logged == 0

    @pytest.mark.asyncio
    async def test_reading_minutes_kept_when_configured(self, test_db: AsyncSession):
        """Test that reading minutes are kept when configured not to forgive"""
        from app.services.schedulers import process_child_to_adult_transitions

        # Create system settings with forgive_reading_minutes=False
        library_system = LibrarySystem(
            code="TEST_SYS",
            name="Test Library System",
            is_active=True,
        )
        test_db.add(library_system)
        await test_db.flush()

        system_settings = SystemSettings(
            library_system_id=library_system.id,
            age_transition_threshold=18,
            auto_transition_enabled=True,
            forgive_reading_minutes_on_transition=False,
        )
        test_db.add(system_settings)
        await test_db.commit()

        today = date.today()
        birth_date = date(today.year - 18, today.month, today.day)

        child = User(
            email="reading_keep@test.com",
            password_hash="hashed",
            first_name="Reading",
            last_name="Keep",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            date_of_birth=birth_date,
            reading_minutes_owed=60,
            reading_minutes_logged=30,
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)
        child_id = child.id

        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True):
            await process_child_to_adult_transitions()

        test_db.expire_all()
        result = await test_db.execute(select(User).where(User.id == child_id))
        updated_user = result.scalar_one()

        # Reading minutes should be preserved
        assert updated_user.reading_minutes_owed == 60
        assert updated_user.reading_minutes_logged == 30


class TestAuditLogging:
    """Test audit log creation during transition"""

    @pytest.mark.asyncio
    async def test_audit_log_created(self, test_db: AsyncSession):
        """Test that an audit log entry is created for each transition"""
        from app.services.schedulers import process_child_to_adult_transitions

        today = date.today()
        birth_date = date(today.year - 18, today.month, today.day)

        child = User(
            email="audit_log@test.com",
            password_hash="hashed",
            first_name="Audit",
            last_name="Log",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            date_of_birth=birth_date,
            reading_minutes_owed=30,
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)
        child_id = child.id

        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True):
            await process_child_to_adult_transitions()

        # Check audit log
        result = await test_db.execute(
            select(AuditLog).where(
                AuditLog.target_user_id == child_id,
                AuditLog.action == AuditAction.CHILD_TO_ADULT_TRANSITION,
            )
        )
        audit_log = result.scalar_one_or_none()

        assert audit_log is not None
        assert audit_log.admin_id is None  # System automated
        assert audit_log.details["previous_role"] == "child"
        assert audit_log.details["new_role"] == "patron"
        assert audit_log.details["reading_minutes_forgiven"] == 30
        assert audit_log.details["parental_consent_cleared"] == True


class TestNotifications:
    """Test notification sending during transition"""

    @pytest.mark.asyncio
    async def test_notification_sent_to_transitioned_user(self, test_db: AsyncSession):
        """Test that notification is sent to the transitioned user"""
        from app.services.schedulers import process_child_to_adult_transitions

        today = date.today()
        birth_date = date(today.year - 18, today.month, today.day)

        child = User(
            email="notify_patron@test.com",
            password_hash="hashed",
            first_name="Notify",
            last_name="Patron",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            date_of_birth=birth_date,
        )
        test_db.add(child)
        await test_db.commit()

        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True) as mock_email:
            await process_child_to_adult_transitions()

            # Verify email was sent to the patron
            patron_email_sent = any(
                call[0][0] == "notify_patron@test.com" and "Adult Library Account" in call[0][1]
                for call in mock_email.call_args_list
            )
            assert patron_email_sent

    @pytest.mark.asyncio
    async def test_notification_sent_to_parent(self, test_db: AsyncSession):
        """Test that notification is sent to parent/guardian"""
        from app.services.schedulers import process_child_to_adult_transitions

        today = date.today()
        birth_date = date(today.year - 18, today.month, today.day)

        # Create parent
        parent = User(
            email="parent_notify@test.com",
            password_hash="hashed",
            first_name="Parent",
            last_name="Guardian",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(parent)
        await test_db.flush()

        # Create child with parent link
        child = User(
            email="notify_child@test.com",
            password_hash="hashed",
            first_name="Notify",
            last_name="Child",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            date_of_birth=birth_date,
            parent_guardian_id=parent.id,
        )
        test_db.add(child)
        await test_db.commit()

        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True) as mock_email:
            await process_child_to_adult_transitions()

            # Verify email was sent to parent
            parent_email_sent = any(
                call[0][0] == "parent_notify@test.com" and "Account Has Transitioned" in call[0][1]
                for call in mock_email.call_args_list
            )
            assert parent_email_sent


class TestConfigurableTransitionAge:
    """Test configurable transition age"""

    @pytest.mark.asyncio
    async def test_custom_transition_age(self, test_db: AsyncSession):
        """Test transition with custom age threshold (e.g., 21)"""
        from app.services.schedulers import process_child_to_adult_transitions

        # Create system settings with age threshold of 21
        library_system = LibrarySystem(
            code="CUSTOM_AGE",
            name="Custom Age Library",
            is_active=True,
        )
        test_db.add(library_system)
        await test_db.flush()

        system_settings = SystemSettings(
            library_system_id=library_system.id,
            age_transition_threshold=21,
            auto_transition_enabled=True,
            forgive_reading_minutes_on_transition=True,
        )
        test_db.add(system_settings)
        await test_db.commit()

        today = date.today()

        # Create 18-year-old (should NOT transition)
        child18 = User(
            email="age18_custom@test.com",
            password_hash="hashed",
            first_name="Eighteen",
            last_name="Custom",
            role=UserRole.CHILD,
            is_active=True,
            date_of_birth=date(today.year - 18, today.month, today.day),
        )

        # Create 21-year-old (should transition)
        child21 = User(
            email="age21_custom@test.com",
            password_hash="hashed",
            first_name="Twentyone",
            last_name="Custom",
            role=UserRole.CHILD,
            is_active=True,
            date_of_birth=date(today.year - 21, today.month, today.day),
        )

        test_db.add_all([child18, child21])
        await test_db.commit()
        await test_db.refresh(child18)
        await test_db.refresh(child21)
        child18_id = child18.id
        child21_id = child21.id

        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True):
            await process_child_to_adult_transitions()

        test_db.expire_all()
        # Check 18-year-old still CHILD
        result18 = await test_db.execute(select(User).where(User.id == child18_id))
        user18 = result18.scalar_one()
        assert user18.role == UserRole.CHILD

        # Check 21-year-old is now PATRON
        result21 = await test_db.execute(select(User).where(User.id == child21_id))
        user21 = result21.scalar_one()
        assert user21.role == UserRole.PATRON


class TestDisabledTransitions:
    """Test behavior when transitions are disabled"""

    @pytest.mark.asyncio
    async def test_no_transitions_when_disabled(self, test_db: AsyncSession):
        """Test that no transitions occur when auto_transition_enabled=False"""
        from app.services.schedulers import process_child_to_adult_transitions

        # Create system settings with transitions disabled
        library_system = LibrarySystem(
            code="DISABLED",
            name="Disabled Library",
            is_active=True,
        )
        test_db.add(library_system)
        await test_db.flush()

        system_settings = SystemSettings(
            library_system_id=library_system.id,
            age_transition_threshold=18,
            auto_transition_enabled=False,  # Disabled
            forgive_reading_minutes_on_transition=True,
        )
        test_db.add(system_settings)
        await test_db.commit()

        today = date.today()
        child = User(
            email="no_transition@test.com",
            password_hash="hashed",
            first_name="No",
            last_name="Transition",
            role=UserRole.CHILD,
            is_active=True,
            date_of_birth=date(today.year - 18, today.month, today.day),
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)
        child_id = child.id

        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True):
            await process_child_to_adult_transitions()

        # User should still be CHILD
        result = await test_db.execute(select(User).where(User.id == child_id))
        user = result.scalar_one()
        assert user.role == UserRole.CHILD


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_no_transition_without_date_of_birth(self, test_db: AsyncSession):
        """Test that users without date_of_birth are not transitioned"""
        from app.services.schedulers import process_child_to_adult_transitions

        child = User(
            email="no_dob@test.com",
            password_hash="hashed",
            first_name="No",
            last_name="DOB",
            role=UserRole.CHILD,
            is_active=True,
            date_of_birth=None,  # No date of birth
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)
        child_id = child.id

        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True):
            await process_child_to_adult_transitions()

        result = await test_db.execute(select(User).where(User.id == child_id))
        user = result.scalar_one()
        assert user.role == UserRole.CHILD

    @pytest.mark.asyncio
    async def test_no_transition_for_inactive_users(self, test_db: AsyncSession):
        """Test that inactive users are not transitioned"""
        from app.services.schedulers import process_child_to_adult_transitions

        today = date.today()
        child = User(
            email="inactive@test.com",
            password_hash="hashed",
            first_name="Inactive",
            last_name="User",
            role=UserRole.CHILD,
            is_active=False,  # Inactive
            date_of_birth=date(today.year - 18, today.month, today.day),
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)
        child_id = child.id

        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True):
            await process_child_to_adult_transitions()

        result = await test_db.execute(select(User).where(User.id == child_id))
        user = result.scalar_one()
        assert user.role == UserRole.CHILD

    @pytest.mark.asyncio
    async def test_patron_type_updated(self, test_db: AsyncSession):
        """Test that patron_type is updated from 'child' to 'adult'"""
        from app.services.schedulers import process_child_to_adult_transitions

        today = date.today()
        child = User(
            email="patron_type@test.com",
            password_hash="hashed",
            first_name="Patron",
            last_name="Type",
            role=UserRole.CHILD,
            is_active=True,
            date_of_birth=date(today.year - 18, today.month, today.day),
            patron_type="child",
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)
        child_id = child.id

        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True):
            await process_child_to_adult_transitions()

        test_db.expire_all()
        result = await test_db.execute(select(User).where(User.id == child_id))
        user = result.scalar_one()
        assert user.patron_type == "adult"


class TestIdempotency:
    """Test that job is safe to run multiple times"""

    @pytest.mark.asyncio
    async def test_running_job_twice_no_double_processing(self, test_db: AsyncSession):
        """Test that running transition twice doesn't create duplicate audit logs"""
        from app.services.schedulers import process_child_to_adult_transitions

        today = date.today()
        child = User(
            email="idempotent@test.com",
            password_hash="hashed",
            first_name="Idempotent",
            last_name="Test",
            role=UserRole.CHILD,
            is_active=True,
            date_of_birth=date(today.year - 18, today.month, today.day),
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)
        child_id = child.id

        # Run first time
        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True):
            await process_child_to_adult_transitions()

        # Check user is now PATRON
        test_db.expire_all()
        result = await test_db.execute(select(User).where(User.id == child_id))
        user = result.scalar_one()
        assert user.role == UserRole.PATRON

        # Run second time
        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True):
            await process_child_to_adult_transitions()

        # Should still be PATRON (no CHILD -> PATRON -> PATRON transition)
        test_db.expire_all()
        result = await test_db.execute(select(User).where(User.id == child_id))
        user = result.scalar_one()
        assert user.role == UserRole.PATRON

        # Should only have 1 audit log entry
        audit_result = await test_db.execute(
            select(AuditLog).where(
                AuditLog.target_user_id == child_id,
                AuditLog.action == AuditAction.CHILD_TO_ADULT_TRANSITION,
            )
        )
        audit_logs = audit_result.scalars().all()
        assert len(audit_logs) == 1


class TestLogging:
    """Test logging behavior"""

    @pytest.mark.asyncio
    async def test_job_logs_summary_metrics(self, test_db: AsyncSession):
        """Test that job logs summary metrics on completion"""
        from app.services.schedulers import process_child_to_adult_transitions

        today = date.today()
        for i in range(3):
            child = User(
                email=f"logging_test_{i}@test.com",
                password_hash="hashed",
                first_name=f"Log{i}",
                last_name="Test",
                role=UserRole.CHILD,
                is_active=True,
                date_of_birth=date(today.year - 18, today.month, today.day),
            )
            test_db.add(child)
        await test_db.commit()

        with patch('app.services.schedulers.patron_lifecycle_jobs.send_email', new_callable=AsyncMock, return_value=True):
            with patch('app.services.job_failure_service.logger') as mock_logger:
                await process_child_to_adult_transitions()

                # Check that info logs contain completion message
                info_calls = [str(call) for call in mock_logger.info.call_args_list]
                assert any("completed" in call for call in info_calls)
