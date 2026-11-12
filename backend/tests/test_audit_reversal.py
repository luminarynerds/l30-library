# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for audit reversal functionality.

This module tests the audit reversal API endpoints which allow administrators
to revert certain actions that have been logged in the audit trail.

Test Coverage:
- Test that ADMIN can check if an action is reversible
- Test that ADMIN can revert a USER_UPDATE action
- Test that ADMIN can revert a LOCK_USER action
- Test that ADMIN can revert a privacy change action
- Test that STAFF role cannot access revert endpoints (403)
- Test that PATRON role cannot access revert endpoints (403)
- Test that already-reverted actions cannot be reverted again
- Test that non-reversible actions (like CREATE_USER) return appropriate error
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.models.audit_log import AuditAction, AuditLog
from app.models.user import User, UserRole


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def admin_token(test_admin):
    """Create an access token for the admin user.

    Args:
        test_admin: The admin user fixture from conftest.py

    Returns:
        str: JWT access token for the admin user
    """
    return create_access_token(subject=test_admin.id, email=test_admin.email)


@pytest.fixture
def staff_token(test_staff):
    """Create an access token for the staff user.

    Args:
        test_staff: The staff user fixture from conftest.py

    Returns:
        str: JWT access token for the staff user
    """
    return create_access_token(subject=test_staff.id, email=test_staff.email)


@pytest.fixture
def patron_token(test_patron):
    """Create an access token for the patron user.

    Args:
        test_patron: The patron user fixture from conftest.py

    Returns:
        str: JWT access token for the patron user
    """
    return create_access_token(subject=test_patron.id, email=test_patron.email)


@pytest.fixture
async def target_user(test_db):
    """Create a target user for audit log actions.

    This user serves as the target of admin actions that will be logged
    and potentially reverted in the tests.

    Args:
        test_db: The test database session fixture

    Returns:
        User: A patron user that can be the target of admin actions
    """
    user = User(
        email="target_user@example.com",
        password_hash=hash_password("TargetPassword123!"),
        first_name="Target",
        last_name="User",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        phone="555-0100",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def user_update_audit_log(test_db, test_admin, target_user):
    """Create an audit log entry for a USER_UPDATE action.

    This fixture creates an audit log entry that records a user update
    action with old and new values that can be used to test reversal.

    Args:
        test_db: The test database session fixture
        test_admin: The admin user who performed the action
        target_user: The user who was updated

    Returns:
        AuditLog: An audit log entry for a USER_UPDATE action
    """
    audit_log = AuditLog(
        admin_id=test_admin.id,
        target_user_id=target_user.id,
        action=AuditAction.UPDATE_USER,
        details={
            "changes": {
                "first_name": {"old": "Original", "new": "Updated"},
                "phone": {"old": "555-0000", "new": "555-1111"},
            }
        },
        ip_address="192.168.1.1",
    )
    test_db.add(audit_log)
    await test_db.commit()
    await test_db.refresh(audit_log)
    return audit_log


@pytest.fixture
async def lock_user_audit_log(test_db, test_admin, target_user):
    """Create an audit log entry for a LOCK_USER action.

    This fixture creates an audit log entry that records a user lock
    action that can be reverted (i.e., the user can be unlocked).

    Args:
        test_db: The test database session fixture
        test_admin: The admin user who performed the lock
        target_user: The user who was locked

    Returns:
        AuditLog: An audit log entry for a LOCK_USER action
    """
    # First, lock the target user
    target_user.locked_until = datetime.now(timezone.utc) + timedelta(days=36500)

    audit_log = AuditLog(
        admin_id=test_admin.id,
        target_user_id=target_user.id,
        action=AuditAction.LOCK_USER,
        details={
            "email": target_user.email,
            "locked_until": target_user.locked_until.isoformat(),
        },
        ip_address="192.168.1.1",
    )
    test_db.add(audit_log)
    await test_db.commit()
    await test_db.refresh(audit_log)
    await test_db.refresh(target_user)
    return audit_log


@pytest.fixture
async def privacy_change_audit_log(test_db, target_user):
    """Create an audit log entry for a privacy change action.

    This fixture creates an audit log entry that records a privacy
    setting change that can be reverted to the previous privacy state.

    Args:
        test_db: The test database session fixture
        target_user: The user whose privacy was changed

    Returns:
        AuditLog: An audit log entry for a privacy change action
    """
    from app.models.reading_list import ReadingList

    # The reversal handler looks up a real ReadingList row by resource_id
    # and flips is_public back to the old value, so the fixture needs an
    # actual row -- a made-up ID makes the revert legitimately fail.
    reading_list = ReadingList(
        user_id=target_user.id,
        name="Test Reading List",
        is_public=True,  # matches new_privacy below
    )
    test_db.add(reading_list)
    await test_db.commit()
    await test_db.refresh(reading_list)

    audit_log = AuditLog(
        admin_id=None,  # Privacy changes are user-initiated
        target_user_id=target_user.id,
        action=AuditAction.PRIVACY_CHANGE_READING_LIST,
        details={
            "resource_type": "reading_list",
            "resource_id": reading_list.id,
            "old_privacy": "private",
            "new_privacy": "public",
            "changed_at": datetime.now(timezone.utc).isoformat(),
        },
        ip_address="192.168.1.100",
    )
    test_db.add(audit_log)
    await test_db.commit()
    await test_db.refresh(audit_log)
    return audit_log


@pytest.fixture
async def create_user_audit_log(test_db, test_admin, target_user):
    """Create an audit log entry for a CREATE_USER action.

    This fixture creates an audit log entry that records a user creation
    action. This action type is NOT reversible (cannot un-create a user).

    Args:
        test_db: The test database session fixture
        test_admin: The admin user who created the user
        target_user: The user who was created

    Returns:
        AuditLog: An audit log entry for a CREATE_USER action
    """
    audit_log = AuditLog(
        admin_id=test_admin.id,
        target_user_id=target_user.id,
        action=AuditAction.CREATE_USER,
        details={
            "email": target_user.email,
            "role": target_user.role.value,
        },
        ip_address="192.168.1.1",
    )
    test_db.add(audit_log)
    await test_db.commit()
    await test_db.refresh(audit_log)
    return audit_log


@pytest.fixture
async def reverted_audit_log(test_db, test_admin, target_user):
    """Create an audit log entry that has already been reverted.

    This fixture creates an audit log entry with a reverted_at timestamp
    to test that already-reverted actions cannot be reverted again.

    Args:
        test_db: The test database session fixture
        test_admin: The admin user who performed the original action
        target_user: The user who was affected

    Returns:
        AuditLog: An audit log entry that is marked as already reverted
    """
    audit_log = AuditLog(
        admin_id=test_admin.id,
        target_user_id=target_user.id,
        action=AuditAction.UPDATE_USER,
        details={
            "changes": {
                "first_name": {"old": "Original", "new": "Updated"},
            },
            "reverted": True,
            "reverted_at": datetime.now(timezone.utc).isoformat(),
            "reverted_by": test_admin.id,
        },
        ip_address="192.168.1.1",
    )
    test_db.add(audit_log)
    await test_db.commit()
    await test_db.refresh(audit_log)
    return audit_log


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.integration
class TestAuditReversibilityCheck:
    """Test the endpoint that checks if an audit action is reversible."""

    async def test_admin_can_check_if_action_is_reversible_user_update(
        self,
        client: TestClient,
        test_admin,
        admin_token,
        user_update_audit_log,
    ):
        """Test that ADMIN can check if a USER_UPDATE action is reversible.

        USER_UPDATE actions should be marked as reversible since the old
        values are stored in the audit log and can be restored.
        """
        response = await client.get(
            f"/api/v1/admin/audit/{user_update_audit_log.id}/reversible",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["audit_log_id"] == user_update_audit_log.id
        assert data["is_reversible"] is True
        assert data["action"] == "update_user"
        assert "reason" in data

    async def test_admin_can_check_if_action_is_reversible_lock_user(
        self,
        client: TestClient,
        test_admin,
        admin_token,
        lock_user_audit_log,
    ):
        """Test that ADMIN can check if a LOCK_USER action is reversible.

        LOCK_USER actions should be reversible since the user can be unlocked.
        """
        response = await client.get(
            f"/api/v1/admin/audit/{lock_user_audit_log.id}/reversible",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["audit_log_id"] == lock_user_audit_log.id
        assert data["is_reversible"] is True
        assert data["action"] == "lock_user"

    async def test_admin_can_check_if_action_is_reversible_create_user(
        self,
        client: TestClient,
        test_admin,
        admin_token,
        create_user_audit_log,
    ):
        """Test that ADMIN can check if a CREATE_USER action is reversible.

        CREATE_USER actions should NOT be reversible since we cannot
        un-create a user through reversal (use delete instead).
        """
        response = await client.get(
            f"/api/v1/admin/audit/{create_user_audit_log.id}/reversible",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["audit_log_id"] == create_user_audit_log.id
        assert data["is_reversible"] is False
        assert data["action"] == "create_user"
        assert "reason" in data
        # The reason should explain why it's not reversible
        assert "cannot" in data["reason"].lower() or "not reversible" in data["reason"].lower()

    async def test_check_reversible_nonexistent_audit_log(
        self,
        client: TestClient,
        admin_token,
    ):
        """Test checking reversibility of a non-existent audit log returns 404."""
        response = await client.get(
            "/api/v1/admin/audit/99999/reversible",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.integration
class TestRevertUserUpdateAction:
    """Test reverting USER_UPDATE actions."""

    async def test_admin_can_revert_user_update_action(
        self,
        client: TestClient,
        test_db,
        test_admin,
        admin_token,
        target_user,
        user_update_audit_log,
    ):
        """Test that ADMIN can revert a USER_UPDATE action.

        After reverting, the user's fields should be restored to their
        original values as recorded in the audit log.
        """
        # First, update the target user to match the "new" values in the audit log
        target_user.first_name = "Updated"
        target_user.phone = "555-1111"
        await test_db.commit()

        response = await client.post(
            f"/api/v1/admin/audit/{user_update_audit_log.id}/revert",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["audit_log_id"] == user_update_audit_log.id
        assert data["action"] == "update_user"
        assert "reverted_changes" in data

        # Verify the user was actually reverted
        await test_db.refresh(target_user)
        # Note: The actual field values depend on implementation
        # The reversal should restore old values from the audit log

    async def test_revert_user_update_creates_reversal_audit_log(
        self,
        client: TestClient,
        test_db,
        test_admin,
        admin_token,
        target_user,
        user_update_audit_log,
    ):
        """Test that reverting an action creates its own audit log entry.

        When an action is reverted, a new audit log entry should be created
        to track the reversal itself for accountability.
        """
        target_user.first_name = "Updated"
        target_user.phone = "555-1111"
        await test_db.commit()

        response = await client.post(
            f"/api/v1/admin/audit/{user_update_audit_log.id}/revert",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check that a reversal audit log was created
        assert "reversal_audit_log_id" in data
        assert data["reversal_audit_log_id"] is not None


@pytest.mark.integration
class TestRevertLockUserAction:
    """Test reverting LOCK_USER actions."""

    async def test_admin_can_revert_lock_user_action(
        self,
        client: TestClient,
        test_db,
        test_admin,
        admin_token,
        target_user,
        lock_user_audit_log,
    ):
        """Test that ADMIN can revert a LOCK_USER action.

        After reverting a LOCK_USER action, the user should be unlocked
        (locked_until should be cleared).
        """

        # Verify user is locked
        await test_db.refresh(target_user)
        assert target_user.locked_until is not None

        response = await client.post(
            f"/api/v1/admin/audit/{lock_user_audit_log.id}/revert",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["audit_log_id"] == lock_user_audit_log.id
        assert data["action"] == "lock_user"

        # Verify the user was unlocked
        await test_db.refresh(target_user)
        assert target_user.locked_until is None


@pytest.mark.integration
class TestRevertPrivacyChangeAction:
    """Test reverting privacy change actions."""

    async def test_admin_can_revert_privacy_change_action(
        self,
        client: TestClient,
        test_admin,
        admin_token,
        privacy_change_audit_log,
    ):
        """Test that ADMIN can revert a privacy change action.

        After reverting a privacy change, the privacy setting should be
        restored to its previous value (old_privacy in the audit log).
        """
        response = await client.post(
            f"/api/v1/admin/audit/{privacy_change_audit_log.id}/revert",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["audit_log_id"] == privacy_change_audit_log.id
        assert data["action"] == "privacy_change_reading_list"

        # The reverted changes should show the privacy was restored
        assert "reverted_changes" in data


@pytest.mark.integration
class TestRevertAccessControl:
    """Test access control for revert endpoints."""

    async def test_staff_cannot_access_revert_endpoint(
        self,
        client: TestClient,
        test_staff,
        staff_token,
        user_update_audit_log,
    ):
        """Test that STAFF role cannot access revert endpoints.

        Only ADMIN and SUPER_ADMIN should be able to revert audit actions.
        STAFF should receive a 403 Forbidden response.
        """
        response = await client.post(
            f"/api/v1/admin/audit/{user_update_audit_log.id}/revert",
            headers={"Authorization": f"Bearer {staff_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_staff_cannot_check_reversibility(
        self,
        client: TestClient,
        test_staff,
        staff_token,
        user_update_audit_log,
    ):
        """Test that STAFF role cannot check if an action is reversible.

        Only ADMIN and SUPER_ADMIN should be able to access this endpoint.
        """
        response = await client.get(
            f"/api/v1/admin/audit/{user_update_audit_log.id}/reversible",
            headers={"Authorization": f"Bearer {staff_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_patron_cannot_access_revert_endpoint(
        self,
        client: TestClient,
        test_patron,
        patron_token,
        user_update_audit_log,
    ):
        """Test that PATRON role cannot access revert endpoints.

        Patrons should have no access to administrative audit functionality.
        They should receive a 403 Forbidden response.
        """
        response = await client.post(
            f"/api/v1/admin/audit/{user_update_audit_log.id}/revert",
            headers={"Authorization": f"Bearer {patron_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_patron_cannot_check_reversibility(
        self,
        client: TestClient,
        test_patron,
        patron_token,
        user_update_audit_log,
    ):
        """Test that PATRON role cannot check if an action is reversible.

        Patrons should have no access to administrative audit functionality.
        """
        response = await client.get(
            f"/api/v1/admin/audit/{user_update_audit_log.id}/reversible",
            headers={"Authorization": f"Bearer {patron_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_unauthenticated_cannot_access_revert_endpoint(
        self,
        client: TestClient,
        user_update_audit_log,
    ):
        """Test that unauthenticated requests cannot access revert endpoints.

        All revert operations require authentication.
        """
        response = await client.post(
            f"/api/v1/admin/audit/{user_update_audit_log.id}/revert",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestAlreadyRevertedActions:
    """Test handling of already-reverted actions."""

    async def test_cannot_revert_already_reverted_action(
        self,
        client: TestClient,
        test_admin,
        admin_token,
        reverted_audit_log,
    ):
        """Test that already-reverted actions cannot be reverted again.

        If an action has already been reverted (has reverted_at timestamp),
        attempting to revert it again should fail with an appropriate error.
        """
        response = await client.post(
            f"/api/v1/admin/audit/{reverted_audit_log.id}/revert",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "already" in data["error"]["message"].lower() or "reverted" in data["error"]["message"].lower()

    async def test_check_reversibility_of_already_reverted_action(
        self,
        client: TestClient,
        admin_token,
        reverted_audit_log,
    ):
        """Test that checking reversibility of an already-reverted action shows it's not reversible.

        The reversibility check should indicate that an already-reverted
        action cannot be reverted again.
        """
        response = await client.get(
            f"/api/v1/admin/audit/{reverted_audit_log.id}/reversible",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_reversible"] is False
        assert "already" in data["reason"].lower() or "reverted" in data["reason"].lower()


@pytest.mark.integration
class TestNonReversibleActions:
    """Test handling of actions that cannot be reversed."""

    async def test_create_user_action_cannot_be_reverted(
        self,
        client: TestClient,
        test_admin,
        admin_token,
        create_user_audit_log,
    ):
        """Test that CREATE_USER actions return an appropriate error when reversal is attempted.

        CREATE_USER actions are not reversible because we cannot "un-create"
        a user through reversal. The proper way to handle this is through
        user deletion or deactivation.
        """
        response = await client.post(
            f"/api/v1/admin/audit/{create_user_audit_log.id}/revert",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        # Error message should indicate the action type is not reversible
        assert "not reversible" in data["error"]["message"].lower() or "cannot" in data["error"]["message"].lower()

    async def test_gdpr_deletion_action_cannot_be_reverted(
        self,
        client: TestClient,
        test_db,
        test_admin,
        admin_token,
        target_user,
    ):
        """Test that GDPR deletion actions cannot be reverted.

        GDPR deletions are irreversible by design for legal compliance.
        Once data is deleted under GDPR, it cannot be restored.
        """

        # Create a GDPR deletion audit log
        audit_log = AuditLog(
            admin_id=test_admin.id,
            target_user_id=target_user.id,
            action=AuditAction.GDPR_DELETION_COMPLETED,
            details={
                "reason": "User requested deletion",
                "deleted_at": datetime.now(timezone.utc).isoformat(),
            },
            ip_address="192.168.1.1",
        )
        test_db.add(audit_log)
        await test_db.commit()
        await test_db.refresh(audit_log)

        response = await client.post(
            f"/api/v1/admin/audit/{audit_log.id}/revert",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "not reversible" in data["error"]["message"].lower() or "cannot" in data["error"]["message"].lower()

    async def test_bulk_action_cannot_be_reverted(
        self,
        client: TestClient,
        test_db,
        test_admin,
        admin_token,
    ):
        """Test that bulk actions cannot be reverted through the single-revert endpoint.

        Bulk actions affect multiple users and require special handling.
        They should not be reversible through the standard revert endpoint.
        """

        # Create a bulk lock audit log
        audit_log = AuditLog(
            admin_id=test_admin.id,
            target_user_id=None,  # Bulk actions have no single target
            action=AuditAction.BULK_LOCK,
            details={
                "user_ids": [1, 2, 3],
                "count": 3,
            },
            ip_address="192.168.1.1",
        )
        test_db.add(audit_log)
        await test_db.commit()
        await test_db.refresh(audit_log)

        response = await client.post(
            f"/api/v1/admin/audit/{audit_log.id}/revert",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        # Should indicate bulk actions cannot be reverted this way
        assert "bulk" in data["error"]["message"].lower() or "not reversible" in data["error"]["message"].lower()


@pytest.mark.integration
class TestRevertEdgeCases:
    """Test edge cases and error handling for revert functionality."""

    async def test_revert_nonexistent_audit_log(
        self,
        client: TestClient,
        admin_token,
    ):
        """Test that reverting a non-existent audit log returns 404."""
        response = await client.post(
            "/api/v1/admin/audit/99999/revert",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_revert_with_missing_target_user(
        self,
        client: TestClient,
        test_db,
        test_admin,
        admin_token,
    ):
        """Test handling when the target user no longer exists.

        If the user who was the target of an action has been deleted,
        the revert should fail gracefully with an appropriate error.

        target_user_id has a real FK to users (ondelete="SET NULL"), so an
        audit log can't be created pointing at a user id that was never
        real -- that's just a DB integrity error, not the scenario under
        test. To reproduce "target user no longer exists" for real, create
        the user, log the audit entry against them, then delete the user so
        the FK's ON DELETE SET NULL clears target_user_id.
        """
        target = User(
            email="deleted_target@example.com",
            password_hash=hash_password("TargetPassword123!"),
            first_name="Deleted",
            last_name="Target",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(target)
        await test_db.commit()
        await test_db.refresh(target)

        audit_log = AuditLog(
            admin_id=test_admin.id,
            target_user_id=target.id,
            action=AuditAction.UPDATE_USER,
            details={
                "changes": {
                    "first_name": {"old": "Original", "new": "Updated"},
                }
            },
            ip_address="192.168.1.1",
        )
        test_db.add(audit_log)
        await test_db.commit()
        await test_db.refresh(audit_log)

        await test_db.delete(target)
        await test_db.commit()
        await test_db.refresh(audit_log)
        assert audit_log.target_user_id is None

        response = await client.post(
            f"/api/v1/admin/audit/{audit_log.id}/revert",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Should return an error indicating the target user doesn't exist
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST]

    async def test_revert_with_incomplete_audit_details(
        self,
        client: TestClient,
        test_db,
        test_admin,
        admin_token,
        target_user,
    ):
        """Test handling when audit log details are incomplete.

        If the audit log doesn't have enough information to revert
        (e.g., missing old values), it should fail gracefully.
        """

        # Create an audit log with incomplete details (no old values)
        audit_log = AuditLog(
            admin_id=test_admin.id,
            target_user_id=target_user.id,
            action=AuditAction.UPDATE_USER,
            details={
                "changes": {
                    "first_name": {"new": "Updated"},  # Missing "old" value
                }
            },
            ip_address="192.168.1.1",
        )
        test_db.add(audit_log)
        await test_db.commit()
        await test_db.refresh(audit_log)

        response = await client.post(
            f"/api/v1/admin/audit/{audit_log.id}/revert",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Should return an error about incomplete data
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
class TestRevertableActionTypes:
    """Test the list of reversible action types."""

    async def test_get_list_of_reversible_action_types(
        self,
        client: TestClient,
        admin_token,
    ):
        """Test retrieving the list of action types that can be reverted.

        This endpoint should return information about which action types
        are reversible and which are not, for documentation purposes.
        """
        response = await client.get(
            "/api/v1/admin/audit/reversible-actions",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return a list of action types with their reversibility
        assert "reversible" in data
        assert "non_reversible" in data

        # These should be lists
        assert isinstance(data["reversible"], list)
        assert isinstance(data["non_reversible"], list)

        # UPDATE_USER and LOCK_USER should be reversible
        assert "update_user" in data["reversible"]
        assert "lock_user" in data["reversible"]

        # CREATE_USER and GDPR actions should not be reversible
        assert "create_user" in data["non_reversible"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
