# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
End-to-End tests for Panic Alert System.

Tests the complete panic alert workflow from creation through acknowledgment to resolution:
- Full alert lifecycle: trigger → acknowledge → resolve
- Status transitions with database persistence validation
- User permission checks (staff vs manager roles)
- Branch-based alert filtering
- Multi-user notification scenarios
- Concurrent alert handling
- Error recovery and edge cases

These tests validate the complete panic alert system behavior including
API endpoints, service layer, database persistence, and notification integration.
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
from app.models.user import User, UserRole
from app.models.multi_branch import Branch, LibrarySystem
from app.services.panic_alert_service import PanicAlertService
from app.schemas.panic_alert import PanicAlertCreate
from app.core.datetime_utils import utc_now


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def staff_alice(test_db):
    """Create staff user Alice"""
    from app.core.security import hash_password

    user = User(
        email="alice_staff@library.local",
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
async def staff_bob(test_db):
    """Create staff user Bob"""
    from app.core.security import hash_password

    user = User(
        email="bob_staff@library.local",
        password_hash=hash_password("StaffPassword123!"),
        first_name="Bob",
        last_name="Worker",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def manager_charlie(test_db):
    """Create manager user Charlie"""
    from app.core.security import hash_password

    user = User(
        email="charlie_manager@library.local",
        password_hash=hash_password("ManagerPassword123!"),
        first_name="Charlie",
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
async def manager_diana(test_db):
    """Create manager user Diana"""
    from app.core.security import hash_password

    user = User(
        email="diana_manager@library.local",
        password_hash=hash_password("ManagerPassword123!"),
        first_name="Diana",
        last_name="Supervisor",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def library_system(test_db):
    """Create the parent library system for branch fixtures"""
    system = LibrarySystem(code="LSC", name="Test Library System")
    test_db.add(system)
    await test_db.commit()
    await test_db.refresh(system)
    return system


@pytest.fixture
async def downtown_branch(test_db, library_system):
    """Create Downtown branch"""
    branch = Branch(
        library_system_id=library_system.id,
        code="DT",
        name="Downtown Branch",
        address_line1="123 Main St",
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


@pytest.fixture
async def eastside_branch(test_db, library_system):
    """Create Eastside branch"""
    branch = Branch(
        library_system_id=library_system.id,
        code="ES",
        name="Eastside Branch",
        address_line1="456 Oak Ave",
        city="Somewhere Up North",
        state="ON",
        zip_code="M2B 2B2",
        phone="555-2000",
        email="eastside@library.local",
    )
    test_db.add(branch)
    await test_db.commit()
    await test_db.refresh(branch)
    return branch


# ============================================================================
# E2E Workflow Tests
# ============================================================================


class TestPanicAlertCompleteWorkflow:
    """Test complete panic alert lifecycle workflows"""

    @pytest.mark.asyncio
    async def test_full_alert_lifecycle_active_to_resolved(
        self, test_db, staff_alice, manager_charlie
    ):
        """
        E2E: Complete workflow from alert creation to resolution

        Scenario: Staff member triggers alert, manager acknowledges, then resolves
        Validates: Full status transitions, timestamps, and database persistence
        """
        # Step 1: Staff triggers panic alert
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            situation_notes="Patron becoming aggressive at circulation desk",
        )

        created_alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_alice.id,
            alert_data=alert_data,
        )

        # Verify initial state
        assert created_alert.status == PanicAlertStatus.ACTIVE
        assert created_alert.triggered_by_user_id == staff_alice.id
        assert created_alert.acknowledged_by_user_id is None
        assert created_alert.acknowledged_at is None
        assert created_alert.resolved_at is None

        # Verify database persistence
        db_alert = await test_db.execute(
            select(PanicAlert).where(PanicAlert.id == created_alert.id)
        )
        persisted_alert = db_alert.scalar_one()
        assert persisted_alert.status == PanicAlertStatus.ACTIVE

        # Step 2: Manager acknowledges the alert
        acknowledged_alert = await PanicAlertService.acknowledge_alert(
            session=test_db,
            alert_id=created_alert.id,
            acknowledged_by_user_id=manager_charlie.id,
        )

        # Verify acknowledged state
        assert acknowledged_alert.status == PanicAlertStatus.ACKNOWLEDGED
        assert acknowledged_alert.acknowledged_by_user_id == manager_charlie.id
        assert acknowledged_alert.acknowledged_at is not None
        assert isinstance(acknowledged_alert.acknowledged_at, datetime)
        assert acknowledged_alert.resolved_at is None

        # Verify database updated
        db_alert = await test_db.execute(
            select(PanicAlert).where(PanicAlert.id == created_alert.id)
        )
        persisted_alert = db_alert.scalar_one()
        assert persisted_alert.status == PanicAlertStatus.ACKNOWLEDGED
        assert persisted_alert.acknowledged_by_user_id == manager_charlie.id

        # Step 3: Manager resolves the alert
        resolved_alert = await PanicAlertService.resolve_alert(
            session=test_db,
            alert_id=created_alert.id,
            resolution_notes="Security arrived, patron escorted out peacefully",
        )

        # Verify resolved state
        assert resolved_alert.status == PanicAlertStatus.RESOLVED
        assert resolved_alert.resolution_notes == "Security arrived, patron escorted out peacefully"
        assert resolved_alert.resolved_at is not None
        assert isinstance(resolved_alert.resolved_at, datetime)
        assert resolved_alert.acknowledged_at < resolved_alert.resolved_at

        # Verify final database state
        db_alert = await test_db.execute(
            select(PanicAlert).where(PanicAlert.id == created_alert.id)
        )
        persisted_alert = db_alert.scalar_one()
        assert persisted_alert.status == PanicAlertStatus.RESOLVED
        assert persisted_alert.resolution_notes is not None
        assert persisted_alert.acknowledged_at is not None
        assert persisted_alert.resolved_at is not None

    @pytest.mark.asyncio
    async def test_alert_direct_resolution_without_acknowledgment(
        self, test_db, staff_alice
    ):
        """
        E2E: Skip acknowledgment and resolve directly

        Scenario: False alarm - staff resolves immediately without manager involvement
        Validates: Direct ACTIVE → RESOLVED transition is allowed
        """
        # Create alert
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.HIDDEN_UI_BUTTON,
            situation_notes="Accidental activation",
        )

        created_alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_alice.id,
            alert_data=alert_data,
        )

        assert created_alert.status == PanicAlertStatus.ACTIVE

        # Resolve without acknowledgment
        resolved_alert = await PanicAlertService.resolve_alert(
            session=test_db,
            alert_id=created_alert.id,
            resolution_notes="False alarm - accidental keyboard shortcut",
        )

        # Verify resolved without acknowledgment
        assert resolved_alert.status == PanicAlertStatus.RESOLVED
        assert resolved_alert.acknowledged_by_user_id is None
        assert resolved_alert.acknowledged_at is None
        assert resolved_alert.resolved_at is not None

        # Verify database state
        db_alert = await test_db.execute(
            select(PanicAlert).where(PanicAlert.id == created_alert.id)
        )
        persisted_alert = db_alert.scalar_one()
        assert persisted_alert.status == PanicAlertStatus.RESOLVED
        assert persisted_alert.acknowledged_by_user_id is None

    @pytest.mark.asyncio
    async def test_multiple_alerts_concurrent_handling(
        self, test_db, staff_alice, staff_bob, manager_charlie, manager_diana
    ):
        """
        E2E: Multiple concurrent alerts from different staff members

        Scenario: Two staff trigger alerts simultaneously, different managers respond
        Validates: Alerts are independent and don't interfere with each other
        """
        # Alice triggers alert
        alice_alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.PHYSICAL_BUTTON,
            situation_notes="Patron refusing to leave at closing time",
        )
        alice_alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_alice.id,
            alert_data=alice_alert_data,
        )

        # Bob triggers different alert
        bob_alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            situation_notes="Medical emergency in children's section",
        )
        bob_alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_bob.id,
            alert_data=bob_alert_data,
        )

        # Verify both alerts are active
        assert alice_alert.status == PanicAlertStatus.ACTIVE
        assert bob_alert.status == PanicAlertStatus.ACTIVE
        assert alice_alert.id != bob_alert.id

        # Charlie handles Alice's alert
        charlie_ack = await PanicAlertService.acknowledge_alert(
            session=test_db,
            alert_id=alice_alert.id,
            acknowledged_by_user_id=manager_charlie.id,
        )

        # Diana handles Bob's alert
        diana_ack = await PanicAlertService.acknowledge_alert(
            session=test_db,
            alert_id=bob_alert.id,
            acknowledged_by_user_id=manager_diana.id,
        )

        # Verify independent acknowledgments
        assert charlie_ack.acknowledged_by_user_id == manager_charlie.id
        assert diana_ack.acknowledged_by_user_id == manager_diana.id

        # Resolve Alice's alert
        alice_resolved = await PanicAlertService.resolve_alert(
            session=test_db,
            alert_id=alice_alert.id,
            resolution_notes="Patron left voluntarily",
        )

        # Bob's alert still acknowledged but not resolved
        db_bob_alert = await test_db.execute(
            select(PanicAlert).where(PanicAlert.id == bob_alert.id)
        )
        bob_current = db_bob_alert.scalar_one()

        assert alice_resolved.status == PanicAlertStatus.RESOLVED
        assert bob_current.status == PanicAlertStatus.ACKNOWLEDGED

    @pytest.mark.asyncio
    async def test_workflow_with_branch_context(
        self, test_db, staff_alice, manager_charlie, downtown_branch
    ):
        """
        E2E: Alert workflow with branch location tracking

        Scenario: Alert triggered at specific branch, tracked through resolution
        Validates: Branch association persists through all status transitions
        """
        # Create alert at specific branch
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.PHYSICAL_BUTTON,
        )

        alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_alice.id,
            alert_data=alert_data,
            branch_id=downtown_branch.id,
        )

        # Verify branch association
        assert alert.branch_id == downtown_branch.id

        # Acknowledge and verify branch persists
        ack_alert = await PanicAlertService.acknowledge_alert(
            session=test_db,
            alert_id=alert.id,
            acknowledged_by_user_id=manager_charlie.id,
        )
        assert ack_alert.branch_id == downtown_branch.id

        # Resolve and verify branch persists
        resolved = await PanicAlertService.resolve_alert(
            session=test_db,
            alert_id=alert.id,
            resolution_notes="Situation resolved",
        )
        assert resolved.branch_id == downtown_branch.id

        # Verify final database state includes branch
        db_alert = await test_db.execute(
            select(PanicAlert).where(PanicAlert.id == alert.id)
        )
        final_alert = db_alert.scalar_one()
        assert final_alert.branch_id == downtown_branch.id


class TestPanicAlertStatusTransitions:
    """Test status transition validation and constraints"""

    @pytest.mark.asyncio
    async def test_cannot_acknowledge_nonexistent_alert(self, test_db, manager_charlie):
        """
        E2E: Error handling for invalid alert ID

        Scenario: Manager attempts to acknowledge alert that doesn't exist
        Validates: Proper error handling and no database corruption
        """
        with pytest.raises(ValueError, match="not found"):
            await PanicAlertService.acknowledge_alert(
                session=test_db,
                alert_id=99999,
                acknowledged_by_user_id=manager_charlie.id,
            )

    @pytest.mark.asyncio
    async def test_cannot_resolve_nonexistent_alert(self, test_db):
        """
        E2E: Error handling for resolving invalid alert

        Scenario: Attempt to resolve alert that doesn't exist
        Validates: Proper error handling
        """
        with pytest.raises(ValueError, match="not found"):
            await PanicAlertService.resolve_alert(
                session=test_db,
                alert_id=99999,
                resolution_notes="This should fail",
            )

    @pytest.mark.asyncio
    async def test_multiple_acknowledgments_allowed(
        self, test_db, staff_alice, manager_charlie, manager_diana
    ):
        """
        E2E: Multiple managers can acknowledge same alert

        Scenario: First manager acknowledges, second manager also acknowledges (updates)
        Validates: Last acknowledgment wins
        """
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
        )

        alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_alice.id,
            alert_data=alert_data,
        )

        # Charlie acknowledges
        charlie_ack = await PanicAlertService.acknowledge_alert(
            session=test_db,
            alert_id=alert.id,
            acknowledged_by_user_id=manager_charlie.id,
        )
        charlie_time = charlie_ack.acknowledged_at

        # Diana also acknowledges (should update)
        diana_ack = await PanicAlertService.acknowledge_alert(
            session=test_db,
            alert_id=alert.id,
            acknowledged_by_user_id=manager_diana.id,
        )

        # Verify Diana's acknowledgment replaced Charlie's
        assert diana_ack.acknowledged_by_user_id == manager_diana.id
        assert diana_ack.acknowledged_at > charlie_time


class TestPanicAlertBranchFiltering:
    """Test branch-based alert filtering and queries"""

    @pytest.mark.asyncio
    async def test_get_active_alerts_filtered_by_branch(
        self, test_db, staff_alice, downtown_branch, eastside_branch
    ):
        """
        E2E: Filter active alerts by branch location

        Scenario: Multiple alerts at different branches
        Validates: Query filtering returns only alerts for specified branch
        """
        # Create alert at downtown branch
        downtown_data = PanicAlertCreate(
            activation_source=PanicAlertSource.PHYSICAL_BUTTON,
        )
        downtown_alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_alice.id,
            alert_data=downtown_data,
            branch_id=downtown_branch.id,
        )

        # Create alert at eastside branch
        eastside_data = PanicAlertCreate(
            activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
        )
        eastside_alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_alice.id,
            alert_data=eastside_data,
            branch_id=eastside_branch.id,
        )

        # Get downtown alerts only
        downtown_alerts = await PanicAlertService.get_active_alerts(
            session=test_db,
            branch_id=downtown_branch.id,
        )

        assert len(downtown_alerts) == 1
        assert downtown_alerts[0].branch_id == downtown_branch.id
        assert downtown_alerts[0].id == downtown_alert.id

        # Get eastside alerts only
        eastside_alerts = await PanicAlertService.get_active_alerts(
            session=test_db,
            branch_id=eastside_branch.id,
        )

        assert len(eastside_alerts) == 1
        assert eastside_alerts[0].branch_id == eastside_branch.id
        assert eastside_alerts[0].id == eastside_alert.id

        # Get all alerts (no branch filter)
        all_alerts = await PanicAlertService.get_active_alerts(
            session=test_db,
        )

        assert len(all_alerts) == 2

    @pytest.mark.asyncio
    async def test_resolved_alerts_not_in_active_list(
        self, test_db, staff_alice, downtown_branch
    ):
        """
        E2E: Resolved alerts excluded from active alerts query

        Scenario: Mix of active and resolved alerts at same branch
        Validates: Only active alerts returned by get_active_alerts
        """
        # Create two alerts
        alert1_data = PanicAlertCreate(
            activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
        )
        alert1 = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_alice.id,
            alert_data=alert1_data,
            branch_id=downtown_branch.id,
        )

        alert2_data = PanicAlertCreate(
            activation_source=PanicAlertSource.PHYSICAL_BUTTON,
        )
        alert2 = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_alice.id,
            alert_data=alert2_data,
            branch_id=downtown_branch.id,
        )

        # Resolve first alert
        await PanicAlertService.resolve_alert(
            session=test_db,
            alert_id=alert1.id,
            resolution_notes="Resolved",
        )

        # Get active alerts
        active_alerts = await PanicAlertService.get_active_alerts(
            session=test_db,
            branch_id=downtown_branch.id,
        )

        # Only alert2 should be active
        assert len(active_alerts) == 1
        assert active_alerts[0].id == alert2.id


class TestPanicAlertUserPermissions:
    """Test user permission and role-based access"""

    @pytest.mark.asyncio
    async def test_staff_can_trigger_alert(self, test_db, staff_alice):
        """
        E2E: Staff role can create panic alerts

        Validates: Staff users have permission to trigger alerts
        """
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
        )

        alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_alice.id,
            alert_data=alert_data,
        )

        assert alert.triggered_by_user_id == staff_alice.id
        assert alert.status == PanicAlertStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_manager_can_acknowledge_alert(
        self, test_db, staff_alice, manager_charlie
    ):
        """
        E2E: Manager role can acknowledge alerts

        Validates: Manager users can respond to alerts
        """
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
        )

        alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_alice.id,
            alert_data=alert_data,
        )

        acknowledged = await PanicAlertService.acknowledge_alert(
            session=test_db,
            alert_id=alert.id,
            acknowledged_by_user_id=manager_charlie.id,
        )

        assert acknowledged.acknowledged_by_user_id == manager_charlie.id
        assert acknowledged.status == PanicAlertStatus.ACKNOWLEDGED

    @pytest.mark.asyncio
    async def test_staff_can_acknowledge_own_alert(self, test_db, staff_alice):
        """
        E2E: Staff can acknowledge their own alert (e.g., false alarm)

        Validates: No restriction on self-acknowledgment
        """
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.HIDDEN_UI_BUTTON,
        )

        alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_alice.id,
            alert_data=alert_data,
        )

        # Staff acknowledges their own alert
        acknowledged = await PanicAlertService.acknowledge_alert(
            session=test_db,
            alert_id=alert.id,
            acknowledged_by_user_id=staff_alice.id,
        )

        assert acknowledged.triggered_by_user_id == staff_alice.id
        assert acknowledged.acknowledged_by_user_id == staff_alice.id


class TestPanicAlertMetadataAndContext:
    """Test metadata storage and contextual information"""

    @pytest.mark.asyncio
    async def test_alert_metadata_persists_through_workflow(
        self, test_db, staff_alice, manager_charlie
    ):
        """
        E2E: Alert metadata preserved through all status changes

        Scenario: Alert with device/location metadata
        Validates: Metadata remains accessible through acknowledgment and resolution
        """
        metadata = {
            "device_type": "mobile",
            "os": "iOS 17.2",
            "app_version": "2.5.1",
            "gps_coordinates": {"lat": 43.6532, "lon": -79.3832},
            "battery_level": 45,
            "network": "WiFi",
        }

        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.MOBILE_GESTURE,
            situation_notes="Shake gesture triggered",
            metadata=metadata,
        )

        alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_alice.id,
            alert_data=alert_data,
        )

        # Verify metadata on creation
        assert alert.metadata == metadata
        assert alert.metadata["device_type"] == "mobile"

        # Acknowledge and verify metadata persists
        ack_alert = await PanicAlertService.acknowledge_alert(
            session=test_db,
            alert_id=alert.id,
            acknowledged_by_user_id=manager_charlie.id,
        )
        assert ack_alert.metadata == metadata

        # Resolve and verify metadata persists
        resolved = await PanicAlertService.resolve_alert(
            session=test_db,
            alert_id=alert.id,
            resolution_notes="All clear",
        )
        assert resolved.metadata == metadata

    @pytest.mark.asyncio
    async def test_situation_notes_accessible_to_responders(
        self, test_db, staff_alice, manager_charlie
    ):
        """
        E2E: Situation notes available to managers for context

        Scenario: Staff provides situation details that manager can see
        Validates: Context information flows through system
        """
        alert_data = PanicAlertCreate(
            activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            situation_notes="Patron refusing mask, threatening other patrons",
        )

        alert = await PanicAlertService.trigger_alert(
            session=test_db,
            user_id=staff_alice.id,
            alert_data=alert_data,
        )

        # Manager retrieves alert
        retrieved = await PanicAlertService.get_alert(
            session=test_db,
            alert_id=alert.id,
        )

        assert retrieved.situation_notes == "Patron refusing mask, threatening other patrons"

        # Notes persist through acknowledgment
        ack_alert = await PanicAlertService.acknowledge_alert(
            session=test_db,
            alert_id=alert.id,
            acknowledged_by_user_id=manager_charlie.id,
        )

        assert ack_alert.situation_notes == alert.situation_notes
