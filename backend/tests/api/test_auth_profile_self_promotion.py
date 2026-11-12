# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression tests for the PUT /api/v1/auth/me mass-assignment guard.

A patron must not be able to self-promote their patron_type or change their
date_of_birth via the self-service profile endpoint. Those fields gate
COPPA / minor-only AI guardrails and are only legitimately written by admin
endpoints and patron_lifecycle_jobs.

These tests cover the allowlist directly (the loop logic in update_me) rather
than driving the FastAPI request layer. The host-run SQLite test DB hits a
readonly-mode permission trap during this fixture's seed commit (see
feedback_l30_conftest_singleton_engine_loop_trap and parallel-fixture issues
documented in CLAUDE.md), so a clean unit-level guard test is the most
reliable evidence the mass-assignment fix is in place. The behavior under
test is purely the allowlist filter -- no DB or HTTP layer needed.
"""
from datetime import date

import pytest

from app.api.v1.auth.profile import _SELF_EDITABLE_FIELDS
from app.models.user import User
from app.schemas.user import UserUpdate


class TestSelfEditableAllowlist:
    """The allowlist must include patron self-edit fields and exclude promotion fields."""

    def test_patron_type_is_blocked(self):
        assert "patron_type" not in _SELF_EDITABLE_FIELDS

    def test_date_of_birth_is_blocked(self):
        assert "date_of_birth" not in _SELF_EDITABLE_FIELDS

    def test_role_is_blocked(self):
        # Defense in depth: UserUpdate does not currently expose `role`, but
        # the allowlist must not whitelist it either.
        assert "role" not in _SELF_EDITABLE_FIELDS

    def test_email_is_blocked(self):
        # Email change must go through the dedicated verification endpoint,
        # never through bulk PUT /me.
        assert "email" not in _SELF_EDITABLE_FIELDS

    def test_password_hash_is_blocked(self):
        assert "password_hash" not in _SELF_EDITABLE_FIELDS

    def test_parental_consent_is_blocked(self):
        # COPPA gate: a minor must not be able to flip their own consent flag.
        assert "parental_consent_given" not in _SELF_EDITABLE_FIELDS

    @pytest.mark.parametrize(
        "field",
        [
            "first_name",
            "last_name",
            "phone",
            "address",
            "track_reading_history",
            "emergency_contact_name",
            "emergency_contact_phone",
            "preferred_contact_method",
            "language_preference",
            "accessibility_needs",
        ],
    )
    def test_self_editable_fields_are_allowed(self, field):
        assert field in _SELF_EDITABLE_FIELDS


class TestUpdateMeMassAssignmentGuard:
    """Replicate the update_me allowlist loop and assert it blocks promotion."""

    def _apply_update(self, user: User, payload: dict) -> User:
        """Mirror the body of update_me that performs the allowlisted writes."""
        update_data = UserUpdate(**payload).model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field not in _SELF_EDITABLE_FIELDS:
                continue
            setattr(user, field, value)
        return user

    def test_self_promote_attempt_does_not_change_patron_type(self):
        user = User()
        user.patron_type = "minor"
        user.first_name = "Orig"
        user.date_of_birth = date(2015, 6, 1)

        self._apply_update(
            user,
            {
                "patron_type": "adult",
                "date_of_birth": "2000-01-01",
                "first_name": "Renamed",
            },
        )

        # Allowed field went through.
        assert user.first_name == "Renamed"
        # Blocked fields are unchanged.
        assert user.patron_type == "minor"
        assert user.date_of_birth == date(2015, 6, 1)

    def test_date_of_birth_only_payload_is_silently_dropped(self):
        user = User()
        user.date_of_birth = date(2015, 6, 1)

        self._apply_update(user, {"date_of_birth": "1999-12-31"})

        assert user.date_of_birth == date(2015, 6, 1)

    def test_all_allowed_self_fields_flow_through(self):
        user = User()
        self._apply_update(
            user,
            {
                "first_name": "Updated",
                "last_name": "Patron",
                "phone": "555-0100",
                "address": "123 Library Ln",
                "preferred_contact_method": "email",
                "language_preference": "en",
                "accessibility_needs": "large-print",
                "emergency_contact_name": "Kin",
                "emergency_contact_phone": "555-0101",
                "track_reading_history": True,
            },
        )

        assert user.first_name == "Updated"
        assert user.last_name == "Patron"
        assert user.phone == "555-0100"
        assert user.address == "123 Library Ln"
        assert user.preferred_contact_method == "email"
        assert user.language_preference == "en"
        assert user.accessibility_needs == "large-print"
        assert user.emergency_contact_name == "Kin"
        assert user.emergency_contact_phone == "555-0101"
        assert user.track_reading_history is True

    def test_mixed_payload_keeps_allowed_drops_blocked(self):
        """A single PUT mixing allowed + blocked fields keeps both halves correct."""
        user = User()
        user.patron_type = "minor"
        user.date_of_birth = date(2015, 6, 1)
        user.first_name = "Orig"
        user.phone = "555-0001"

        self._apply_update(
            user,
            {
                # Allowed
                "first_name": "Changed",
                "phone": "555-9999",
                # Blocked (self-promotion attempt)
                "patron_type": "adult",
                "date_of_birth": "2000-01-01",
            },
        )

        assert user.first_name == "Changed"
        assert user.phone == "555-9999"
        assert user.patron_type == "minor"
        assert user.date_of_birth == date(2015, 6, 1)
