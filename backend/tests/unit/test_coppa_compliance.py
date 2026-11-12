# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for COPPA (Children's Online Privacy Protection Act) compliance.

Tests cover:
- Age calculation utility
- Age gate in the card application endpoint (under-13 rejection)
- Normal flow for applicants aged 13 and over
- Edge cases: exactly 13 today, turning 13 tomorrow
- Verification that no PII is persisted when a child's application is rejected
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.core.coppa import COPPA_AGE_THRESHOLD, calculate_age, is_under_coppa_age


# ============================================================================
# Age calculation utility tests
# ============================================================================


class TestCalculateAge:
    """Tests for the calculate_age utility function."""

    def test_adult_age(self):
        """A person born 30 years ago should be 30."""
        today = date.today()
        dob = today.replace(year=today.year - 30)
        assert calculate_age(dob) == 30

    def test_child_age(self):
        """A person born 5 years ago should be 5."""
        today = date.today()
        dob = today.replace(year=today.year - 5)
        assert calculate_age(dob) == 5

    def test_birthday_today(self):
        """A person whose birthday is today should have already turned."""
        today = date.today()
        dob = today.replace(year=today.year - 13)
        assert calculate_age(dob) == 13

    def test_birthday_tomorrow(self):
        """A person whose birthday is tomorrow has not yet turned."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        # They were born on tomorrow's date N years ago
        try:
            dob = tomorrow.replace(year=tomorrow.year - 13)
        except ValueError:
            # Handle Feb 29 edge: skip this particular case
            pytest.skip("Edge case with leap year date")
        assert calculate_age(dob) == 12

    def test_birthday_yesterday(self):
        """A person whose birthday was yesterday has already turned."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        try:
            dob = yesterday.replace(year=yesterday.year - 13)
        except ValueError:
            pytest.skip("Edge case with leap year date")
        assert calculate_age(dob) == 13

    def test_newborn(self):
        """A person born today is age 0."""
        assert calculate_age(date.today()) == 0

    def test_one_day_old(self):
        """A person born yesterday is still age 0."""
        yesterday = date.today() - timedelta(days=1)
        assert calculate_age(yesterday) == 0

    def test_leap_year_birthday(self):
        """A person born on Feb 29 in a leap year."""
        # Use a known leap year
        dob = date(2012, 2, 29)
        age = calculate_age(dob)
        today = date.today()
        expected = today.year - 2012
        if (today.month, today.day) < (2, 29):
            expected -= 1
        assert age == expected


class TestIsUnderCoppaAge:
    """Tests for the is_under_coppa_age helper."""

    def test_under_13(self):
        today = date.today()
        dob = today.replace(year=today.year - 10)
        assert is_under_coppa_age(dob) is True

    def test_exactly_13(self):
        today = date.today()
        dob = today.replace(year=today.year - 13)
        assert is_under_coppa_age(dob) is False

    def test_over_13(self):
        today = date.today()
        dob = today.replace(year=today.year - 18)
        assert is_under_coppa_age(dob) is False

    def test_12_turning_13_tomorrow(self):
        """Still 12 until their birthday arrives."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        try:
            dob = tomorrow.replace(year=tomorrow.year - 13)
        except ValueError:
            pytest.skip("Edge case with leap year date")
        assert is_under_coppa_age(dob) is True


class TestCoppaThreshold:
    """Verify the threshold constant."""

    def test_threshold_value(self):
        assert COPPA_AGE_THRESHOLD == 13


# ============================================================================
# Card application endpoint COPPA integration tests
# ============================================================================


class TestCardApplicationCoppaGate:
    """Integration-style tests for the COPPA age gate on card applications.

    These tests exercise the endpoint through the ASGI test client so that
    the full request/response cycle (including the COPPA guard) runs.
    """

    def _make_application_payload(self, date_of_birth=None):
        """Build a minimal valid application payload."""
        payload = {
            "first_name": "Test",
            "last_name": "Child",
            "email": "testchild@example.com",
            "address_line1": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "zip_code": "62701",
        }
        if date_of_birth is not None:
            payload["date_of_birth"] = date_of_birth.isoformat()
        return payload

    @pytest.mark.asyncio
    async def test_under_13_rejected_with_403(self, client):
        """Applicants under 13 receive a 403 with consent_required."""
        today = date.today()
        child_dob = today.replace(year=today.year - 10)
        payload = self._make_application_payload(child_dob)

        response = await client.post("/api/v1/card-applications", json=payload)

        assert response.status_code == 403
        body = response.json()
        assert body["consent_required"] is True
        assert body["applicant_age"] == 10
        assert body["minimum_online_age"] == COPPA_AGE_THRESHOLD
        assert "visit" in body["message"].lower() or "in person" in body["message"].lower()

    @pytest.mark.asyncio
    async def test_exactly_13_allowed(self, client):
        """Applicants who are exactly 13 today should be allowed through."""
        today = date.today()
        dob = today.replace(year=today.year - 13)
        payload = self._make_application_payload(dob)

        response = await client.post("/api/v1/card-applications", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body["first_name"] == "Test"
        assert body["status"] == "pending"

    @pytest.mark.asyncio
    async def test_turning_13_tomorrow_rejected(self, client):
        """A 12-year-old turning 13 tomorrow is still under the threshold."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        try:
            dob = tomorrow.replace(year=tomorrow.year - 13)
        except ValueError:
            pytest.skip("Edge case with leap year date")
        payload = self._make_application_payload(dob)

        response = await client.post("/api/v1/card-applications", json=payload)

        assert response.status_code == 403
        body = response.json()
        assert body["consent_required"] is True
        assert body["applicant_age"] == 12

    @pytest.mark.asyncio
    async def test_adult_allowed(self, client):
        """An adult (age 30) should proceed normally."""
        today = date.today()
        dob = today.replace(year=today.year - 30)
        payload = self._make_application_payload(dob)

        response = await client.post("/api/v1/card-applications", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "pending"

    @pytest.mark.asyncio
    async def test_no_dob_allowed(self, client):
        """Applications without a date of birth are allowed (existing behaviour)."""
        payload = self._make_application_payload(date_of_birth=None)

        response = await client.post("/api/v1/card-applications", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "pending"

    @pytest.mark.asyncio
    async def test_no_pii_persisted_for_child(self, client, test_db):
        """When a child is rejected, NO data should be written to the database."""
        from sqlalchemy import select, func
        from app.models.card_application import LibraryCardApplication

        today = date.today()
        child_dob = today.replace(year=today.year - 8)
        payload = self._make_application_payload(child_dob)

        # Count applications before the request
        count_before_result = await test_db.execute(
            select(func.count(LibraryCardApplication.id))
        )
        count_before = count_before_result.scalar() or 0

        response = await client.post("/api/v1/card-applications", json=payload)
        assert response.status_code == 403

        # Count applications after -- should be unchanged
        count_after_result = await test_db.execute(
            select(func.count(LibraryCardApplication.id))
        )
        count_after = count_after_result.scalar() or 0

        assert count_after == count_before, (
            "Child's PII was persisted to the database despite COPPA rejection"
        )

    @pytest.mark.asyncio
    async def test_no_pii_persisted_for_child_email_check(self, client, test_db):
        """Verify the child's email does not appear in the applications table."""
        from sqlalchemy import select
        from app.models.card_application import LibraryCardApplication

        today = date.today()
        child_dob = today.replace(year=today.year - 7)
        child_email = "coppa-child-test@example.com"
        payload = self._make_application_payload(child_dob)
        payload["email"] = child_email

        response = await client.post("/api/v1/card-applications", json=payload)
        assert response.status_code == 403

        # Query for any application with this email
        result = await test_db.execute(
            select(LibraryCardApplication).where(
                LibraryCardApplication.email == child_email
            )
        )
        assert result.scalar_one_or_none() is None, (
            f"Found application record for child email {child_email}"
        )


# ============================================================================
# User model COPPA property tests
# ============================================================================


class TestUserModelCoppaProperties:
    """Test COPPA-related properties on the User model."""

    def test_age_property(self):
        from app.models.user import User, UserRole

        today = date.today()
        user = User(
            id=1,
            email="child@example.com",
            password_hash="hash",
            first_name="Young",
            last_name="Patron",
            role=UserRole.CHILD,
            date_of_birth=today.replace(year=today.year - 10),
        )
        assert user.age == 10

    def test_age_none_when_no_dob(self):
        from app.models.user import User, UserRole

        user = User(
            id=1,
            email="adult@example.com",
            password_hash="hash",
            first_name="Adult",
            last_name="Patron",
            role=UserRole.PATRON,
            date_of_birth=None,
        )
        assert user.age is None

    def test_is_minor_true(self):
        from app.models.user import User, UserRole

        today = date.today()
        user = User(
            id=1,
            email="child@example.com",
            password_hash="hash",
            first_name="Young",
            last_name="Patron",
            role=UserRole.CHILD,
            date_of_birth=today.replace(year=today.year - 10),
        )
        assert user.is_minor is True

    def test_is_minor_false_for_adult(self):
        from app.models.user import User, UserRole

        today = date.today()
        user = User(
            id=1,
            email="adult@example.com",
            password_hash="hash",
            first_name="Adult",
            last_name="Patron",
            role=UserRole.PATRON,
            date_of_birth=today.replace(year=today.year - 25),
        )
        assert user.is_minor is False

    def test_is_minor_false_when_no_dob(self):
        from app.models.user import User, UserRole

        user = User(
            id=1,
            email="unknown@example.com",
            password_hash="hash",
            first_name="Unknown",
            last_name="Age",
            role=UserRole.PATRON,
            date_of_birth=None,
        )
        assert user.is_minor is False

    def test_requires_parental_consent_minor_without_consent(self):
        from app.models.user import User, UserRole

        today = date.today()
        user = User(
            id=1,
            email="child@example.com",
            password_hash="hash",
            first_name="Young",
            last_name="Patron",
            role=UserRole.CHILD,
            date_of_birth=today.replace(year=today.year - 10),
            parental_consent_given=False,
        )
        assert user.requires_parental_consent is True

    def test_requires_parental_consent_minor_with_consent(self):
        from app.models.user import User, UserRole

        today = date.today()
        user = User(
            id=1,
            email="child@example.com",
            password_hash="hash",
            first_name="Young",
            last_name="Patron",
            role=UserRole.CHILD,
            date_of_birth=today.replace(year=today.year - 10),
            parental_consent_given=True,
        )
        assert user.requires_parental_consent is False

    def test_requires_parental_consent_adult(self):
        from app.models.user import User, UserRole

        today = date.today()
        user = User(
            id=1,
            email="adult@example.com",
            password_hash="hash",
            first_name="Adult",
            last_name="Patron",
            role=UserRole.PATRON,
            date_of_birth=today.replace(year=today.year - 25),
            parental_consent_given=False,
        )
        assert user.requires_parental_consent is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
