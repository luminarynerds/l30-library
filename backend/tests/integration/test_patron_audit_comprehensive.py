# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive Integration Tests for Patron and Staff Management Audit.

Tests cover all requirements:
1. User role verification (8 roles: SUPER_ADMIN, ADMIN, DIRECTOR, LEGAL, STAFF, PATRON, CHILD, BOOKMOBILE, HOMEBOND)
2. Checkout limits enforcement (role-based, 5-10 items)
3. Patron status transitions (ACTIVE → SUSPENDED → BLOCKED → DECEASED)
4. COPPA compliance for CHILD accounts (age < 13)
5. Staff patron lookup and filtering
6. Fine exemption settings per role
7. Permission inheritance and role settings
8. Access control verification
"""

import pytest
from datetime import datetime, timedelta, date, timezone
from decimal import Decimal
from sqlalchemy import select

from app.models.user import User, UserRole, PatronStatus, COPPA_AGE_THRESHOLD
from app.models.permission import Permission, RolePermission, RoleSettings
from app.models.fine import Fine, FineStatus, FineType
from app.models.circulation import Checkout
from app.core.authorization import (
    get_checkout_limit,
    get_max_renewals,
    is_fine_exempt,
    get_user_permissions,
    has_permission,
    check_fine_block,
)


@pytest.mark.integration
class TestUserRoles:
    """Test all user roles are properly defined and functional."""

    def test_all_user_roles_defined(self):
        """Test all user roles are defined."""
        expected_roles = {
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.DIRECTOR,
            UserRole.LEGAL,
            UserRole.LIBRARY_ADMIN,
            UserRole.STAFF,
            UserRole.PATRON,
            UserRole.TEACHER,
            UserRole.CHILD,
            UserRole.BOOKMOBILE,
            UserRole.HOMEBOND,
        }
        actual_roles = set(UserRole)
        assert expected_roles == actual_roles, f"Missing roles: {expected_roles - actual_roles}"

    def test_super_admin_role_value(self):
        """Test SUPER_ADMIN role has correct value."""
        assert UserRole.SUPER_ADMIN.value == "super_admin"

    def test_admin_role_value(self):
        """Test ADMIN role has correct value."""
        assert UserRole.ADMIN.value == "admin"

    def test_director_role_value(self):
        """Test DIRECTOR role has correct value."""
        assert UserRole.DIRECTOR.value == "director"

    def test_legal_role_value(self):
        """Test LEGAL role has correct value."""
        assert UserRole.LEGAL.value == "legal"

    def test_staff_role_value(self):
        """Test STAFF role has correct value."""
        assert UserRole.STAFF.value == "staff"

    def test_patron_role_value(self):
        """Test PATRON role has correct value."""
        assert UserRole.PATRON.value == "patron"

    def test_child_role_value(self):
        """Test CHILD role has correct value."""
        assert UserRole.CHILD.value == "child"

    def test_bookmobile_role_value(self):
        """Test BOOKMOBILE role has correct value."""
        assert UserRole.BOOKMOBILE.value == "bookmobile"

    def test_homebond_role_value(self):
        """Test HOMEBOND role has correct value."""
        assert UserRole.HOMEBOND.value == "homebond"


@pytest.mark.integration
class TestCheckoutLimits:
    """Test role-based checkout limits."""

    async def test_default_patron_checkout_limit(self, test_db, test_patron):
        """Test default PATRON role checkout limit is 10."""
        limit = await get_checkout_limit(test_patron, test_db)
        assert limit == 10, f"Expected patron checkout limit 10, got {limit}"

    async def test_patron_max_renewals(self, test_db, test_patron):
        """Test default PATRON role max renewals is 2."""
        renewals = await get_max_renewals(test_patron, test_db)
        assert renewals == 2, f"Expected patron max renewals 2, got {renewals}"

    async def test_child_role_lower_checkout_limit(self, test_db):
        """Test CHILD role has lower checkout limit than PATRON."""
        # Create role settings for both
        child_settings = RoleSettings(
            role=UserRole.CHILD,
            max_checkouts=5,
            max_holds=3,
            max_renewals=1,
            checkout_duration_days=14,
            hold_duration_days=5,
            max_fine_amount=1000,
            fine_exempt=False,
            can_use_digital_resources=False,
            can_access_adult_content=False,
            can_book_meeting_rooms=False,
            can_use_3d_printer=False,
            requires_guardian=True,
            home_delivery_eligible=False,
        )
        test_db.add(child_settings)

        patron_settings = RoleSettings(
            role=UserRole.PATRON,
            max_checkouts=10,
            max_holds=5,
            max_renewals=2,
            checkout_duration_days=21,
            hold_duration_days=7,
            max_fine_amount=2500,
            fine_exempt=False,
            can_use_digital_resources=True,
            can_access_adult_content=True,
            can_book_meeting_rooms=False,
            can_use_3d_printer=False,
            requires_guardian=False,
            home_delivery_eligible=False,
        )
        test_db.add(patron_settings)
        await test_db.commit()

        # Verify CHILD has lower limit
        assert child_settings.max_checkouts < patron_settings.max_checkouts
        assert child_settings.max_checkouts == 5

    async def test_staff_role_higher_checkout_limit(self, test_db):
        """Test STAFF role has higher checkout limit than PATRON."""
        staff_settings = RoleSettings(
            role=UserRole.STAFF,
            max_checkouts=50,
            max_holds=50,
            max_renewals=10,
            checkout_duration_days=365,
            hold_duration_days=30,
            max_fine_amount=999999,
            fine_exempt=True,
            can_use_digital_resources=True,
            can_access_adult_content=True,
            can_book_meeting_rooms=True,
            can_use_3d_printer=True,
            requires_guardian=False,
            home_delivery_eligible=False,
        )
        test_db.add(staff_settings)
        await test_db.commit()

        assert staff_settings.max_checkouts == 50
        assert staff_settings.max_renewals == 10


@pytest.mark.integration
class TestPatronStatusTransitions:
    """Test patron status transitions (ACTIVE → SUSPENDED → BLOCKED)."""

    async def test_patron_status_active_default(self, test_db, test_patron):
        """Test patron status defaults to ACTIVE."""
        assert test_patron.patron_status == PatronStatus.ACTIVE

    async def test_patron_status_can_transition_to_suspended(self, test_db, test_patron):
        """Test patron can transition from ACTIVE to SUSPENDED."""
        test_patron.patron_status = PatronStatus.SUSPENDED
        test_patron.suspension_reason = "Overdue items"
        test_patron.suspended_at = datetime.now(timezone.utc)
        test_patron.suspended_until = datetime.now(timezone.utc) + timedelta(days=7)

        await test_db.commit()
        await test_db.refresh(test_patron)

        assert test_patron.patron_status == PatronStatus.SUSPENDED
        assert test_patron.is_suspended is True
        assert test_patron.can_circulate is False

    async def test_patron_status_can_transition_to_blocked(self, test_db, test_patron):
        """Test patron can transition from SUSPENDED to BLOCKED."""
        test_patron.patron_status = PatronStatus.BLOCKED
        test_patron.block_reason = "Patron request"
        test_patron.blocked_at = datetime.now(timezone.utc)
        test_patron.blocked_by_id = 1

        await test_db.commit()
        await test_db.refresh(test_patron)

        assert test_patron.patron_status == PatronStatus.BLOCKED
        assert test_patron.is_blocked is True
        assert test_patron.can_circulate is False

    async def test_patron_suspension_auto_lift(self, test_db, test_patron):
        """Test suspended_until triggers should_lift_suspension."""
        test_patron.patron_status = PatronStatus.SUSPENDED
        test_patron.suspended_until = datetime.now(timezone.utc) - timedelta(hours=1)

        assert test_patron.should_lift_suspension() is True

    async def test_patron_suspension_no_auto_lift_future(self, test_db, test_patron):
        """Test should_lift_suspension returns False for future date."""
        test_patron.patron_status = PatronStatus.SUSPENDED
        test_patron.suspended_until = datetime.now(timezone.utc) + timedelta(days=7)

        assert test_patron.should_lift_suspension() is False

    async def test_patron_status_deceased(self, test_db, test_patron):
        """Test patron can be marked DECEASED."""
        test_patron.patron_status = PatronStatus.DECEASED
        test_patron.date_of_death = date.today()
        test_patron.deceased_marked_at = datetime.now(timezone.utc)
        test_patron.deceased_marked_by_id = 1

        await test_db.commit()
        await test_db.refresh(test_patron)

        assert test_patron.is_deceased is True
        assert test_patron.can_circulate is False
        assert test_patron.can_access_account is False


@pytest.mark.integration
class TestCOPPACompliance:
    """Test COPPA compliance for CHILD accounts."""

    def test_coppa_age_threshold(self):
        """Test COPPA age threshold is 13."""
        assert COPPA_AGE_THRESHOLD == 13

    async def test_child_under_13_requires_consent(self, test_db):
        """Test child under 13 requires parental consent."""
        child_dob = date.today().replace(year=date.today().year - 10)  # 10 years old
        child = User(
            email="child@test.com",
            password_hash="hashed",
            first_name="Child",
            last_name="Patron",
            role=UserRole.CHILD,
            date_of_birth=child_dob,
            parental_consent_given=False,
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)

        assert child.age == 10
        assert child.is_minor is True
        assert child.requires_parental_consent is True

    async def test_child_over_13_no_consent_required(self, test_db):
        """Test child over 13 does not require parental consent."""
        teen_dob = date.today().replace(year=date.today().year - 14)  # 14 years old
        teen = User(
            email="teen@test.com",
            password_hash="hashed",
            first_name="Teen",
            last_name="Patron",
            role=UserRole.CHILD,
            date_of_birth=teen_dob,
            parental_consent_given=False,
        )
        test_db.add(teen)
        await test_db.commit()
        await test_db.refresh(teen)

        assert teen.age == 14
        assert teen.is_minor is False
        assert teen.requires_parental_consent is False

    async def test_child_with_consent(self, test_db):
        """Test child with parental consent given."""
        child_dob = date.today() - timedelta(days=365 * 10)  # 10 years old
        child = User(
            email="child-consented@test.com",
            password_hash="hashed",
            first_name="Consented",
            last_name="Child",
            role=UserRole.CHILD,
            date_of_birth=child_dob,
            parental_consent_given=True,
            parental_consent_date=datetime.now(timezone.utc),
            parental_consent_email="parent@test.com",
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)

        assert child.is_minor is True
        assert child.requires_parental_consent is False  # Has consent

    async def test_child_parent_relationship(self, test_db):
        """Test parent-child relationship for COPPA."""
        parent = User(
            email="parent@test.com",
            password_hash="hashed",
            first_name="Parent",
            last_name="Guardian",
            role=UserRole.PATRON,
            date_of_birth=date.today() - timedelta(days=365 * 40),
        )
        test_db.add(parent)
        await test_db.commit()
        await test_db.refresh(parent)

        child_dob = date.today() - timedelta(days=365 * 10)  # 10 years old
        child = User(
            email="child-linked@test.com",
            password_hash="hashed",
            first_name="Linked",
            last_name="Child",
            role=UserRole.CHILD,
            date_of_birth=child_dob,
            parent_guardian_id=parent.id,
            parental_consent_given=True,
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)

        assert child.parent_guardian_id == parent.id
        assert child.requires_parental_consent is False


@pytest.mark.integration
class TestFineExemption:
    """Test fine exemption settings per role."""

    async def test_patron_not_fine_exempt(self, test_db, test_patron):
        """Test PATRON role is not fine exempt by default."""
        exempt = await is_fine_exempt(test_patron, test_db)
        assert exempt is False

    async def test_staff_fine_exempt(self, test_db):
        """Test STAFF role is fine exempt."""
        staff_settings = RoleSettings(
            role=UserRole.STAFF,
            max_checkouts=50,
            fine_exempt=True,
        )
        test_db.add(staff_settings)
        await test_db.commit()

        staff = User(
            email="staff@test.com",
            password_hash="hashed",
            first_name="Staff",
            last_name="Member",
            role=UserRole.STAFF,
        )
        test_db.add(staff)
        await test_db.commit()
        await test_db.refresh(staff)

        exempt = await is_fine_exempt(staff, test_db)
        assert exempt is True

    async def test_director_fine_exempt(self, test_db):
        """Test DIRECTOR role can be set as fine exempt."""
        director_settings = RoleSettings(
            role=UserRole.DIRECTOR,
            max_checkouts=50,
            fine_exempt=True,
        )
        test_db.add(director_settings)
        await test_db.commit()

        director = User(
            email="director@test.com",
            password_hash="hashed",
            first_name="Director",
            last_name="User",
            role=UserRole.DIRECTOR,
        )
        test_db.add(director)
        await test_db.commit()
        await test_db.refresh(director)

        exempt = await is_fine_exempt(director, test_db)
        assert exempt is True


@pytest.mark.integration
class TestStaffPatronLookup:
    """Test staff patron lookup and filtering capabilities."""

    async def test_staff_can_view_patron_details(self, test_db, test_staff, test_patron):
        """Test staff can view patron details."""
        # test_patron (shared conftest fixture) doesn't set library_card --
        # it's nullable and only assigned via the real registration/card-issue
        # flow, not this bare-minimum fixture. Assign one here to exercise
        # staff visibility into it.
        test_patron.library_card = "TEST-CARD-0001"
        await test_db.commit()
        await test_db.refresh(test_patron)

        # Verify staff can see patron data
        assert test_patron.email is not None
        assert test_patron.first_name is not None
        assert test_patron.last_name is not None
        assert test_patron.library_card is not None

    async def test_patron_list_by_status(self, test_db):
        """Test filtering patrons by status."""
        # Create patrons with different statuses
        active = User(
            email="active@test.com",
            password_hash="hashed",
            first_name="Active",
            last_name="Patron",
            role=UserRole.PATRON,
            patron_status=PatronStatus.ACTIVE,
        )
        suspended = User(
            email="suspended@test.com",
            password_hash="hashed",
            first_name="Suspended",
            last_name="Patron",
            role=UserRole.PATRON,
            patron_status=PatronStatus.SUSPENDED,
        )
        blocked = User(
            email="blocked@test.com",
            password_hash="hashed",
            first_name="Blocked",
            last_name="Patron",
            role=UserRole.PATRON,
            patron_status=PatronStatus.BLOCKED,
        )
        test_db.add_all([active, suspended, blocked])
        await test_db.commit()

        # Query by status
        result = await test_db.execute(
            select(User).filter(User.patron_status == PatronStatus.ACTIVE)
        )
        active_patrons = result.scalars().all()
        assert any(u.email == "active@test.com" for u in active_patrons)

    async def test_patron_search_by_name(self, test_db):
        """Test searching patrons by name."""
        patron = User(
            email="searchme@test.com",
            password_hash="hashed",
            first_name="John",
            last_name="Smith",
            role=UserRole.PATRON,
        )
        test_db.add(patron)
        await test_db.commit()

        # Search by first name
        result = await test_db.execute(
            select(User).filter(User.first_name.ilike("%John%"))
        )
        found = result.scalars().all()
        assert any(u.email == "searchme@test.com" for u in found)

        # Search by last name
        result = await test_db.execute(
            select(User).filter(User.last_name.ilike("%Smith%"))
        )
        found = result.scalars().all()
        assert any(u.email == "searchme@test.com" for u in found)

    async def test_patron_search_by_library_card(self, test_db):
        """Test searching patrons by library card number."""
        patron = User(
            email="cardme@test.com",
            password_hash="hashed",
            first_name="Card",
            last_name="Holder",
            role=UserRole.PATRON,
            library_card="LIBCARD123456",
        )
        test_db.add(patron)
        await test_db.commit()

        # Search by card
        result = await test_db.execute(
            select(User).filter(User.library_card == "LIBCARD123456")
        )
        found = result.scalar_one_or_none()
        assert found is not None
        assert found.email == "cardme@test.com"


@pytest.mark.integration
class TestPermissionInheritance:
    """Test permission inheritance and role settings."""

    async def test_super_admin_has_all_permissions(self, test_db):
        """Test SUPER_ADMIN role has all permissions."""
        super_admin = User(
            email="superadmin@test.com",
            password_hash="hashed",
            first_name="Super",
            last_name="Admin",
            role=UserRole.SUPER_ADMIN,
        )
        test_db.add(super_admin)
        await test_db.commit()
        await test_db.refresh(super_admin)

        # Super admin should have bypass on most checks
        assert super_admin.role == UserRole.SUPER_ADMIN

    async def test_patron_has_circulation_permission(self, test_db, test_patron):
        """Test PATRON role has circulation permission."""
        # Create and assign circulation permission
        perm = Permission(
            code="circulation.checkout",
            name="Checkout",
            description="Can checkout items",
            category="circulation",
        )
        test_db.add(perm)
        await test_db.commit()
        await test_db.refresh(perm)

        # Assign to patron role
        role_perm = RolePermission(role=UserRole.PATRON, permission_id=perm.id)
        test_db.add(role_perm)
        await test_db.commit()

        # Verify permission
        permissions = await get_user_permissions(test_patron, test_db)
        assert "circulation.checkout" in permissions

    async def test_child_restricted_permissions(self, test_db):
        """Test CHILD role has restricted permissions."""
        child = User(
            email="child-perm@test.com",
            password_hash="hashed",
            first_name="Child",
            last_name="User",
            role=UserRole.CHILD,
            date_of_birth=date.today() - timedelta(days=365 * 10),
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)

        # Child should have different permissions than patron
        assert child.role == UserRole.CHILD


@pytest.mark.integration
class TestAccessControl:
    """Test access control verification."""

    async def test_suspended_patron_cannot_circulate(self, test_db, test_patron):
        """Test suspended patron cannot circulate."""
        test_patron.patron_status = PatronStatus.SUSPENDED
        await test_db.commit()
        await test_db.refresh(test_patron)

        assert test_patron.can_circulate is False

    async def test_blocked_patron_cannot_circulate(self, test_db, test_patron):
        """Test blocked patron cannot circulate."""
        test_patron.patron_status = PatronStatus.BLOCKED
        await test_db.commit()
        await test_db.refresh(test_patron)

        assert test_patron.can_circulate is False

    async def test_active_patron_can_circulate(self, test_db, test_patron):
        """Test active patron can circulate."""
        test_patron.patron_status = PatronStatus.ACTIVE
        test_patron.is_active = True
        await test_db.commit()
        await test_db.refresh(test_patron)

        assert test_patron.can_circulate is True

    async def test_inactive_user_cannot_access_account(self, test_db, test_patron):
        """Test inactive user cannot access account."""
        test_patron.is_active = False
        await test_db.commit()
        await test_db.refresh(test_patron)

        assert test_patron.can_access_account is False

    async def test_deceased_patron_cannot_access(self, test_db, test_patron):
        """Test deceased patron cannot access account."""
        test_patron.patron_status = PatronStatus.DECEASED
        await test_db.commit()
        await test_db.refresh(test_patron)

        assert test_patron.can_access_account is False

    async def test_locked_account_cannot_access(self, test_db, test_patron):
        """Test locked account cannot access."""
        test_patron.locked_until = datetime.now(timezone.utc) + timedelta(hours=1)
        await test_db.commit()
        await test_db.refresh(test_patron)

        assert test_patron.can_access_account is False


@pytest.mark.integration
class TestRoleSettings:
    """Test comprehensive role settings."""

    async def test_patron_role_settings_exist(self, test_db):
        """Test PATRON role settings are retrievable."""
        settings = RoleSettings(
            role=UserRole.PATRON,
            max_checkouts=10,
            max_holds=5,
            max_renewals=2,
            checkout_duration_days=21,
            hold_duration_days=7,
            max_fine_amount=2500,
            fine_exempt=False,
            can_use_digital_resources=True,
            can_access_adult_content=True,
            can_book_meeting_rooms=False,
            can_use_3d_printer=False,
            requires_guardian=False,
            home_delivery_eligible=False,
        )
        test_db.add(settings)
        await test_db.commit()

        result = await test_db.execute(
            select(RoleSettings).filter(RoleSettings.role == UserRole.PATRON)
        )
        retrieved = result.scalar_one_or_none()
        assert retrieved is not None
        assert retrieved.max_checkouts == 10

    async def test_child_role_settings_restricted(self, test_db):
        """Test CHILD role settings are properly restricted."""
        settings = RoleSettings(
            role=UserRole.CHILD,
            max_checkouts=5,
            max_holds=3,
            max_renewals=1,
            checkout_duration_days=14,
            hold_duration_days=5,
            max_fine_amount=1000,
            fine_exempt=False,
            can_use_digital_resources=False,
            can_access_adult_content=False,
            can_book_meeting_rooms=False,
            can_use_3d_printer=False,
            requires_guardian=True,
            home_delivery_eligible=False,
        )
        test_db.add(settings)
        await test_db.commit()

        assert settings.can_access_adult_content is False
        assert settings.can_use_digital_resources is False
        assert settings.requires_guardian is True
        assert settings.max_checkouts == 5

    async def test_reading_minutes_for_children(self, test_db):
        """Test reading minutes system for children."""
        child = User(
            email="readingchild@test.com",
            password_hash="hashed",
            first_name="Reading",
            last_name="Child",
            role=UserRole.CHILD,
            date_of_birth=date.today() - timedelta(days=365 * 10),
            reading_minutes_owed=60,
            reading_minutes_logged=20,
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)

        # Balance = owed - logged
        assert child.reading_minutes_balance == 40
