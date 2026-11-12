# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for navigation service.

Tests the role-based navigation filtering logic without requiring full app startup.
Location: tests/unit/test_navigation_service.py
"""

import pytest
from app.models.user import User, UserRole
from app.services.navigation_service import (
    get_navigation_for_user,
    can_access_admin_pages,
    can_access_staff_pages,
    is_super_admin,
    check_route_access,
    get_role_level,
)


class TestRoleHierarchy:
    """Tests for role hierarchy and level checking."""

    def test_role_level_patron(self):
        """Test that PATRON has level 0."""
        assert get_role_level(UserRole.PATRON) == 0

    def test_role_level_staff(self):
        """Test that STAFF has level 1."""
        assert get_role_level(UserRole.STAFF) == 1

    def test_role_level_admin(self):
        """Test that ADMIN has level 2."""
        assert get_role_level(UserRole.ADMIN) == 2

    def test_role_level_super_admin(self):
        """Test that SUPER_ADMIN has level 3."""
        assert get_role_level(UserRole.SUPER_ADMIN) == 3


class TestAccessControl:
    """Tests for access control functions."""

    def test_staff_can_access_staff_pages(self):
        """Test that staff can access staff pages."""
        user = User(
            id=1,
            email="staff@test.com",
            password_hash="hashed",
            first_name="Staff",
            last_name="User",
            role=UserRole.STAFF,
            is_active=True,
        )
        assert can_access_staff_pages(user) is True

    def test_admin_can_access_staff_pages(self):
        """Test that admin can access staff pages."""
        user = User(
            id=1,
            email="admin@test.com",
            password_hash="hashed",
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
            is_active=True,
        )
        assert can_access_staff_pages(user) is True

    def test_patron_cannot_access_staff_pages(self):
        """Test that patrons cannot access staff pages."""
        user = User(
            id=1,
            email="patron@test.com",
            password_hash="hashed",
            first_name="Patron",
            last_name="User",
            role=UserRole.PATRON,
            is_active=True,
        )
        assert can_access_staff_pages(user) is False

    def test_admin_can_access_admin_pages(self):
        """Test that admin can access admin pages."""
        user = User(
            id=1,
            email="admin@test.com",
            password_hash="hashed",
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
            is_active=True,
        )
        assert can_access_admin_pages(user) is True

    def test_staff_cannot_access_admin_pages(self):
        """Test that staff cannot access admin pages."""
        user = User(
            id=1,
            email="staff@test.com",
            password_hash="hashed",
            first_name="Staff",
            last_name="User",
            role=UserRole.STAFF,
            is_active=True,
        )
        assert can_access_admin_pages(user) is False

    def test_super_admin_can_access_all_pages(self):
        """Test that super admin can access all pages."""
        user = User(
            id=1,
            email="super@test.com",
            password_hash="hashed",
            first_name="Super",
            last_name="Admin",
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        assert can_access_staff_pages(user) is True
        assert can_access_admin_pages(user) is True
        assert is_super_admin(user) is True


class TestNavigationGeneration:
    """Tests for navigation generation based on role."""

    def test_staff_navigation(self):
        """Test that staff users get correct navigation."""
        user = User(
            id=1,
            email="staff@test.com",
            password_hash="hashed",
            first_name="Staff",
            last_name="User",
            role=UserRole.STAFF,
            is_active=True,
        )
        nav = get_navigation_for_user(user)

        # nav.role is str(user.role); StrEnum's str() returns the lowercase
        # wire value ("staff"), not the member name -- same convention as
        # UserRole.STAFF.value everywhere else in this codebase.
        assert nav.role == "staff"
        assert nav.canAccessStaff is True
        assert nav.canAccessAdmin is False
        assert len(nav.sections) > 0

        # Should have staff sections
        section_ids = [s.id for s in nav.sections]
        assert any("staff" in sid for sid in section_ids)

    def test_admin_navigation(self):
        """Test that admin users get correct navigation."""
        user = User(
            id=1,
            email="admin@test.com",
            password_hash="hashed",
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
            is_active=True,
        )
        nav = get_navigation_for_user(user)

        assert nav.role == "admin"
        assert nav.canAccessStaff is True
        assert nav.canAccessAdmin is True
        assert len(nav.sections) > 0

        # Should have both staff and admin sections
        section_ids = [s.id for s in nav.sections]
        assert any("staff" in sid for sid in section_ids)
        assert any("admin" in sid for sid in section_ids)

    def test_super_admin_navigation(self):
        """Test that super admin users get all navigation."""
        user = User(
            id=1,
            email="super@test.com",
            password_hash="hashed",
            first_name="Super",
            last_name="Admin",
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        nav = get_navigation_for_user(user)

        assert nav.role == "super_admin"
        assert nav.canAccessStaff is True
        assert nav.canAccessAdmin is True
        assert len(nav.sections) > 0

        # Should have all sections
        section_ids = [s.id for s in nav.sections]
        assert any("staff" in sid for sid in section_ids)
        assert any("admin" in sid for sid in section_ids)
        assert any("super_admin" in sid for sid in section_ids)

    def test_patron_navigation(self):
        """Test that patron users get empty navigation."""
        user = User(
            id=1,
            email="patron@test.com",
            password_hash="hashed",
            first_name="Patron",
            last_name="User",
            role=UserRole.PATRON,
            is_active=True,
        )
        nav = get_navigation_for_user(user)

        assert nav.role == "patron"
        assert nav.canAccessStaff is False
        assert nav.canAccessAdmin is False
        assert nav.sections == []


class TestRouteAccess:
    """Tests for route access checking."""

    def test_staff_can_access_staff_route(self):
        """Test that staff can access staff routes."""
        user = User(
            id=1,
            email="staff@test.com",
            password_hash="hashed",
            first_name="Staff",
            last_name="User",
            role=UserRole.STAFF,
            is_active=True,
        )
        assert check_route_access(user, UserRole.STAFF) is True

    def test_admin_can_access_staff_route(self):
        """Test that admin can access staff routes."""
        user = User(
            id=1,
            email="admin@test.com",
            password_hash="hashed",
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
            is_active=True,
        )
        assert check_route_access(user, UserRole.STAFF) is True

    def test_staff_cannot_access_admin_route(self):
        """Test that staff cannot access admin routes."""
        user = User(
            id=1,
            email="staff@test.com",
            password_hash="hashed",
            first_name="Staff",
            last_name="User",
            role=UserRole.STAFF,
            is_active=True,
        )
        assert check_route_access(user, UserRole.ADMIN) is False
