# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for Staff Panic Alert System.

Tests cover:
- Creating panic alerts with various sources
- Status transitions (active -> acknowledged -> resolved)
- Notification integration
- Metadata storage
- Timestamp validation
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from app.models.panic_alert import (
    PanicAlert,
    PanicAlertStatus,
    PanicAlertSource,
    PanicAlertNotificationPreferences,
)
from app.models.notification import Notification, NotificationType
from app.services.panic_alert_service import PanicAlertService
from app.schemas.panic_alert import PanicAlertCreate
from app.core.datetime_utils import utc_now


@pytest.fixture
async def staff_user(test_db):
    """Create a staff user for panic alert tests"""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="panic_staff@library.local",
        password_hash=hash_password("StaffPassword123!"),
        first_name="Alice",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def manager_user(test_db):
    """Create a manager user for panic alert responses"""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="panic_manager@library.local",
        password_hash=hash_password("ManagerPassword123!"),
        first_name="Bob",
        last_name="Manager",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_branch(test_db):
    """Create a test branch for location-based alerts"""
    from app.models.multi_branch import Branch, LibrarySystem

    system = LibrarySystem(code="LSC", name="Test Library System")
    test_db.add(system)
    await test_db.flush()
    branch = Branch(
        library_system_id=system.id,
        code="DT",
        name="Downtown Branch",
        address_line1="456 Main St",
        city="Somewhere Up North",
        state="ON",
        zip_code="M1A 1A1",
        phone="555-1000",
        email="downtown@library.local",
    )
    test_db.add(branch)
    await test_db.commit()
    await test_db.refresh(branch)
    return branch


class TestPanicAlertCreation:
    """Test creating panic alerts with various configurations"""

    @pytest.mark.asyncio
    async def test_create_basic_panic_alert(self, test_db, staff_user):
        """Should create a panic alert with minimum required fields"""
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.KEYBOARD_SHORTCUT
        )

        alert_response = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_user.id,
            alert_data=alert_data
        )

        assert alert_response.id is not None
        assert alert_response.triggered_by_user_id == staff_user.id
        assert alert_response.status == PanicAlertStatus.ACTIVE
        assert alert_response.activation_source == PanicAlertSource.KEYBOARD_SHORTCUT

    @pytest.mark.asyncio
    async def test_alert_has_timestamps(self, test_db, staff_user):
        """Should automatically set created_at and updated_at timestamps"""
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.PHYSICAL_BUTTON
        )

        alert_response = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_user.id,
            alert_data=alert_data
        )
        after_creation = utc_now()

        assert alert_response.created_at is not None
        assert alert_response.updated_at is not None
        assert isinstance(alert_response.created_at, datetime)
        # created_at is DB-side (server_default=func.now()), which returns the
        # transaction-start time — in the shared-session test harness that can
        # predate a Python timestamp captured mid-transaction. Assert it is set
        # and recent rather than strictly bounded by a client-side capture.
        assert alert_response.created_at <= after_creation
        assert after_creation - alert_response.created_at < timedelta(minutes=5)

    @pytest.mark.asyncio
    async def test_alert_with_all_sources(self, test_db, staff_user):
        """Should accept all panic alert activation sources"""
        sources = [
            PanicAlertSource.KEYBOARD_SHORTCUT,
            PanicAlertSource.PHYSICAL_BUTTON,
            PanicAlertSource.MOBILE_GESTURE,
            PanicAlertSource.HIDDEN_UI_BUTTON,
        ]

        for source in sources:
            alert_data = PanicAlertCreate(activation_source=source)
            alert_response = await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=staff_user.id,
                alert_data=alert_data
            )
            assert alert_response.activation_source == source

    @pytest.mark.asyncio
    async def test_alert_with_situation_notes(self, test_db, staff_user):
        """Should store optional situation notes"""
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            situation_notes="Patron escalating at reference desk"
        )

        alert_response = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_user.id,
            alert_data=alert_data
        )

        assert alert_response.situation_notes == "Patron escalating at reference desk"

    @pytest.mark.asyncio
    async def test_alert_with_branch_location(self, test_db, staff_user, test_branch):
        """Should associate alert with specific branch location"""
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.PHYSICAL_BUTTON
        )

        alert_response = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_user.id,
            alert_data=alert_data,
            branch_id=test_branch.id
        )

        assert alert_response.branch_id == test_branch.id

    @pytest.mark.asyncio
    async def test_alert_with_metadata(self, test_db, staff_user):
        """Should store alert metadata like device info and location"""
        metadata = {
            "device_type": "mobile",
            "gps_coordinates": {"lat": 43.6532, "lon": -79.3832},
            "app_version": "2.1.0",
            "battery_level": 45
        }

        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.MOBILE_GESTURE,
            metadata=metadata
        )

        alert_response = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_user.id,
            alert_data=alert_data
        )

        assert alert_response.metadata == metadata
        assert alert_response.metadata["device_type"] == "mobile"


class TestPanicAlertStatusTransitions:
    """Test panic alert status lifecycle transitions"""

    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, test_db, staff_user, manager_user):
        """Should transition from ACTIVE to ACKNOWLEDGED status"""
        # Create alert
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.KEYBOARD_SHORTCUT
        )
        alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_user.id,
            alert_data=alert_data
        )

        # Acknowledge alert
        before_ack = utc_now()
        acknowledged = await PanicAlertService.acknowledge_alert(
            session=test_db,
            alert_id=alert.id,
            acknowledged_by_user_id=manager_user.id
        )
        after_ack = utc_now()

        assert acknowledged.status == PanicAlertStatus.ACKNOWLEDGED
        assert acknowledged.acknowledged_by_user_id == manager_user.id
        assert acknowledged.acknowledged_at is not None
        assert before_ack <= acknowledged.acknowledged_at <= after_ack

    @pytest.mark.asyncio
    async def test_resolve_alert(self, test_db, staff_user):
        """Should transition to RESOLVED status with resolution notes"""
        # Create alert
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.PHYSICAL_BUTTON
        )
        alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_user.id,
            alert_data=alert_data
        )

        # Resolve alert
        before_resolve = utc_now()
        resolved = await PanicAlertService.resolve_alert(
            session=test_db,
            alert_id=alert.id,
            resolution_notes="Security arrived, situation under control"
        )
        after_resolve = utc_now()

        assert resolved.status == PanicAlertStatus.RESOLVED
        assert resolved.resolution_notes == "Security arrived, situation under control"
        assert resolved.resolved_at is not None
        assert before_resolve <= resolved.resolved_at <= after_resolve

    @pytest.mark.asyncio
    async def test_full_alert_lifecycle(self, test_db, staff_user, manager_user):
        """Should support complete lifecycle: ACTIVE -> ACKNOWLEDGED -> RESOLVED"""
        # Create alert
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            situation_notes="Patron refusing to leave at closing time"
        )
        alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_user.id,
            alert_data=alert_data
        )
        assert alert.status == PanicAlertStatus.ACTIVE

        # Acknowledge
        acknowledged = await PanicAlertService.acknowledge_alert(
            session=test_db,
            alert_id=alert.id,
            acknowledged_by_user_id=manager_user.id
        )
        assert acknowledged.status == PanicAlertStatus.ACKNOWLEDGED

        # Resolve
        resolved = await PanicAlertService.resolve_alert(
            session=test_db,
            alert_id=alert.id,
            resolution_notes="Patron escorted out by security"
        )

        assert resolved.status == PanicAlertStatus.RESOLVED
        assert resolved.acknowledged_by_user_id == manager_user.id
        assert resolved.acknowledged_at is not None
        assert resolved.resolved_at is not None
        assert resolved.resolution_notes == "Patron escorted out by security"

    @pytest.mark.asyncio
    async def test_resolve_without_acknowledge(self, test_db, staff_user):
        """Should allow resolving alert without explicit acknowledgment step"""
        # Create alert
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.HIDDEN_UI_BUTTON
        )
        alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_user.id,
            alert_data=alert_data
        )

        # Resolve directly
        resolved = await PanicAlertService.resolve_alert(
            session=test_db,
            alert_id=alert.id,
            resolution_notes="False alarm - accidental activation"
        )

        assert resolved.status == PanicAlertStatus.RESOLVED
        assert resolved.acknowledged_by_user_id is None
        assert resolved.acknowledged_at is None


class TestNotificationIntegration:
    """Test panic alert notification system integration"""

    @pytest.mark.asyncio
    async def test_notification_type_exists(self):
        """Should have PANIC_ALERT notification type defined"""
        assert hasattr(NotificationType, 'PANIC_ALERT')
        assert NotificationType.PANIC_ALERT == "panic_alert"

    @pytest.mark.asyncio
    async def test_notification_preferences_creation(self, test_db, manager_user):
        """Should create notification preferences for receiving panic alerts"""
        from app.schemas.panic_alert import PanicAlertNotificationPreferencesCreate

        prefs_data = PanicAlertNotificationPreferencesCreate(
            receive_panic_alerts=True,
            notify_via_email=True,
            notify_via_sms=False,
            notify_via_in_app=True,
            notify_for_all_branches=True,
            sound_enabled=True,
            vibration_enabled=True,
        )

        prefs = await PanicAlertService.set_notification_preferences(
            session=test_db,
            user_id=manager_user.id,
            preferences=prefs_data
        )

        assert prefs.user_id == manager_user.id
        assert prefs.receive_panic_alerts is True
        assert prefs.notify_via_email is True
        assert prefs.notify_via_in_app is True

    @pytest.mark.asyncio
    async def test_branch_specific_notifications(self, test_db, manager_user, test_branch):
        """Should support branch-specific notification preferences"""
        from app.schemas.panic_alert import PanicAlertNotificationPreferencesCreate

        prefs_data = PanicAlertNotificationPreferencesCreate(
            receive_panic_alerts=True,
            notify_via_email=True,
            notify_for_all_branches=False,
            branch_ids=[test_branch.id]
        )

        prefs = await PanicAlertService.set_notification_preferences(
            session=test_db,
            user_id=manager_user.id,
            preferences=prefs_data
        )

        assert prefs.notify_for_all_branches is False
        assert test_branch.id in prefs.branch_ids

    @pytest.mark.asyncio
    async def test_update_notification_preferences(self, test_db, manager_user):
        """Should update existing notification preferences"""
        from app.schemas.panic_alert import PanicAlertNotificationPreferencesCreate

        # Create initial preferences
        initial_prefs = PanicAlertNotificationPreferencesCreate(
            receive_panic_alerts=False,
            notify_via_email=False
        )
        await PanicAlertService.set_notification_preferences(
            session=test_db,
            user_id=manager_user.id,
            preferences=initial_prefs
        )

        # Update preferences
        updated_prefs = PanicAlertNotificationPreferencesCreate(
            receive_panic_alerts=True,
            notify_via_email=True,
            notify_via_sms=True
        )
        result = await PanicAlertService.set_notification_preferences(
            session=test_db,
            user_id=manager_user.id,
            preferences=updated_prefs
        )

        assert result.receive_panic_alerts is True
        assert result.notify_via_email is True
        assert result.notify_via_sms is True


class TestPanicAlertQueries:
    """Test querying and retrieving panic alerts"""

    @pytest.mark.asyncio
    async def test_get_active_alerts(self, test_db, staff_user):
        """Should retrieve only active panic alerts"""
        # Create mix of alerts
        active_data = PanicAlertCreate(activation_source=PanicAlertSource.KEYBOARD_SHORTCUT)
        active_alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_user.id,
            alert_data=active_data
        )

        resolved_data = PanicAlertCreate(activation_source=PanicAlertSource.PHYSICAL_BUTTON)
        resolved_alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_user.id,
            alert_data=resolved_data
        )
        await PanicAlertService.resolve_alert(
            session=test_db,
            alert_id=resolved_alert.id
        )

        # Get only active alerts
        active_alerts = await PanicAlertService.get_active_alerts(session=test_db)

        assert len(active_alerts) == 1
        assert active_alerts[0].id == active_alert.id
        assert active_alerts[0].status == PanicAlertStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_get_alert_by_id(self, test_db, staff_user):
        """Should retrieve specific alert by ID"""
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.HIDDEN_UI_BUTTON,
            situation_notes="Test retrieval"
        )
        created_alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_user.id,
            alert_data=alert_data
        )

        retrieved = await PanicAlertService.get_alert(
            session=test_db,
            alert_id=created_alert.id
        )

        assert retrieved is not None
        assert retrieved.id == created_alert.id
        assert retrieved.situation_notes == "Test retrieval"

    @pytest.mark.asyncio
    async def test_get_recent_alerts_for_user(self, test_db, staff_user):
        """Should retrieve recent alerts for specific user"""
        # Create multiple alerts
        for _ in range(3):
            alert_data = PanicAlertCreate(activation_source=PanicAlertSource.KEYBOARD_SHORTCUT)
            await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=staff_user.id,
                alert_data=alert_data
            )

        recent = await PanicAlertService.get_recent_alerts(
            session=test_db,
            user_id=staff_user.id,
            hours=24
        )

        assert len(recent) == 3
        for alert in recent:
            assert alert.triggered_by_user_id == staff_user.id

    @pytest.mark.asyncio
    async def test_get_active_alerts_by_branch(self, test_db, staff_user, test_branch):
        """Should filter active alerts by branch"""
        # Create alerts at different locations
        with_branch = PanicAlertCreate(activation_source=PanicAlertSource.PHYSICAL_BUTTON)
        _ = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_user.id,
            alert_data=with_branch,
            branch_id=test_branch.id
        )

        without_branch = PanicAlertCreate(activation_source=PanicAlertSource.KEYBOARD_SHORTCUT)
        await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_user.id,
            alert_data=without_branch
        )

        # Query by branch
        branch_alerts = await PanicAlertService.get_active_alerts(
            session=test_db,
            branch_id=test_branch.id
        )

        assert len(branch_alerts) == 1
        assert branch_alerts[0].branch_id == test_branch.id
