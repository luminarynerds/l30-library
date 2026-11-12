# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API tests for /api/v1/card-applications endpoints.

Covers:
- Submit happy path (201 + confirmation email sent)
- Submit duplicate while pending -> 409
- Submit after recent denial -> 409 with reason in detail
- Submit after stale denial (>30 days) -> 201
- Submit after recent approval -> 409 (existing card)
- Staff approve happy path -> card_number assigned + approval email sent
- Staff approve when linked user already has library_card -> 409 with details
- Staff deny -> denial email sent
- List endpoint sort:
    * pending defaults oldest-first
    * approved defaults newest-first
    * explicit `sort` param respected
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.card_application import (
    CardApplicationStatus,
    LibraryCardApplication,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def staff_client(client, test_staff):
    """Client authenticated as a staff user."""
    app.dependency_overrides[get_current_user] = lambda: test_staff
    yield client
    app.dependency_overrides.pop(get_current_user, None)


def _base_payload(**overrides):
    """Build a minimum valid card-application payload."""
    payload = {
        "first_name": "Alex",
        "last_name": "Patron",
        "email": "alex.patron@example.com",
        "phone": "555-0100",
        "date_of_birth": (date.today() - timedelta(days=365 * 30)).isoformat(),
        "address_line1": "123 Main St",
        "city": "Smithville",
        "state": "ON",
        "zip_code": "K0H 1R0",
    }
    payload.update(overrides)
    return payload


async def _insert_application(
    db,
    *,
    email: str,
    status: CardApplicationStatus,
    submitted_at: datetime,
    reviewed_at: datetime | None = None,
    denial_reason: str | None = None,
    assigned_card_number: str | None = None,
) -> LibraryCardApplication:
    """Insert an application directly via the ORM for test setup."""
    app_row = LibraryCardApplication(
        first_name="Existing",
        last_name="Person",
        email=email,
        address_line1="1 Old Rd",
        city="Smithville",
        state="ON",
        zip_code="K0H 1R0",
        status=status,
        submitted_at=submitted_at,
        reviewed_at=reviewed_at,
        denial_reason=denial_reason,
        assigned_card_number=assigned_card_number,
    )
    db.add(app_row)
    await db.commit()
    await db.refresh(app_row)
    return app_row


# ============================================================================
# Submit endpoint
# ============================================================================


class TestSubmitApplication:
    @pytest.mark.asyncio
    async def test_submit_happy_path_sends_confirmation_email(self, client):
        with patch(
            "app.api.v1.card_applications.send_card_application_received",
            new=AsyncMock(return_value=True),
        ) as mock_send:
            resp = await client.post(
                "/api/v1/card-applications", json=_base_payload()
            )

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "pending"
        assert body["email"] == "alex.patron@example.com"
        mock_send.assert_awaited_once()
        kwargs = mock_send.await_args.kwargs
        assert kwargs["to_email"] == "alex.patron@example.com"
        assert kwargs["first_name"] == "Alex"

    @pytest.mark.asyncio
    async def test_submit_does_not_fail_when_email_send_raises(self, client):
        """Email infrastructure problems must not break submission."""
        with patch(
            "app.api.v1.card_applications.send_card_application_received",
            new=AsyncMock(side_effect=RuntimeError("smtp down")),
        ):
            resp = await client.post(
                "/api/v1/card-applications", json=_base_payload()
            )
        assert resp.status_code == 201, resp.text

    @pytest.mark.asyncio
    async def test_submit_duplicate_pending_returns_409(self, client, test_db):
        await _insert_application(
            test_db,
            email="alex.patron@example.com",
            status=CardApplicationStatus.pending,
            submitted_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        with patch(
            "app.api.v1.card_applications.send_card_application_received",
            new=AsyncMock(return_value=True),
        ) as mock_send:
            resp = await client.post(
                "/api/v1/card-applications", json=_base_payload()
            )
        assert resp.status_code == 409
        message = resp.json()["error"]["message"]
        assert "already have an application" in message.lower()
        mock_send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_submit_after_recent_denial_returns_409_with_reason(
        self, client, test_db
    ):
        denied_at = datetime.now(timezone.utc) - timedelta(days=5)
        await _insert_application(
            test_db,
            email="alex.patron@example.com",
            status=CardApplicationStatus.denied,
            submitted_at=denied_at - timedelta(days=1),
            reviewed_at=denied_at,
            denial_reason="Address could not be verified",
        )
        resp = await client.post(
            "/api/v1/card-applications", json=_base_payload()
        )
        assert resp.status_code == 409
        message = resp.json()["error"]["message"]
        assert "Address could not be verified" in message
        assert "previous application was denied" in message.lower()

    @pytest.mark.asyncio
    async def test_submit_after_stale_denial_succeeds(self, client, test_db):
        denied_at = datetime.now(timezone.utc) - timedelta(days=120)
        await _insert_application(
            test_db,
            email="alex.patron@example.com",
            status=CardApplicationStatus.denied,
            submitted_at=denied_at - timedelta(days=1),
            reviewed_at=denied_at,
            denial_reason="Old reason, no longer relevant",
        )
        with patch(
            "app.api.v1.card_applications.send_card_application_received",
            new=AsyncMock(return_value=True),
        ):
            resp = await client.post(
                "/api/v1/card-applications", json=_base_payload()
            )
        assert resp.status_code == 201, resp.text

    @pytest.mark.asyncio
    async def test_submit_after_recent_approval_blocks(self, client, test_db):
        approved_at = datetime.now(timezone.utc) - timedelta(days=10)
        await _insert_application(
            test_db,
            email="alex.patron@example.com",
            status=CardApplicationStatus.approved,
            submitted_at=approved_at - timedelta(days=1),
            reviewed_at=approved_at,
            assigned_card_number="LIB-AAAAAA",
        )
        resp = await client.post(
            "/api/v1/card-applications", json=_base_payload()
        )
        assert resp.status_code == 409
        assert "approved" in resp.json()["error"]["message"].lower()


# ============================================================================
# Review endpoint (staff approve / deny)
# ============================================================================


class TestReviewApplication:
    @pytest.mark.asyncio
    async def test_staff_approve_assigns_card_and_sends_email(
        self, staff_client, test_db
    ):
        app_row = await _insert_application(
            test_db,
            email="alex.patron@example.com",
            status=CardApplicationStatus.pending,
            submitted_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        with patch(
            "app.api.v1.card_applications.send_card_application_approved",
            new=AsyncMock(return_value=True),
        ) as mock_send:
            resp = await staff_client.post(
                f"/api/v1/card-applications/staff/{app_row.id}/review",
                json={"status": "approved", "review_notes": "lgtm"},
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "approved"
        assert body["assigned_card_number"], "card number should be assigned"
        mock_send.assert_awaited_once()
        kwargs = mock_send.await_args.kwargs
        assert kwargs["to_email"] == "alex.patron@example.com"
        assert kwargs["card_number"] == body["assigned_card_number"]

    @pytest.mark.asyncio
    async def test_staff_approve_existing_cardholder_returns_409(
        self, staff_client, test_db, test_patron
    ):
        test_patron.library_card = "LIB-OLDCARD"
        await test_db.commit()

        app_row = LibraryCardApplication(
            user_id=test_patron.id,
            first_name=test_patron.first_name,
            last_name=test_patron.last_name,
            email=test_patron.email,
            address_line1="1 Old Rd",
            city="Smithville",
            state="ON",
            zip_code="K0H 1R0",
            status=CardApplicationStatus.pending,
            submitted_at=datetime.now(timezone.utc),
        )
        test_db.add(app_row)
        await test_db.commit()
        await test_db.refresh(app_row)

        with patch(
            "app.api.v1.card_applications.send_card_application_approved",
            new=AsyncMock(return_value=True),
        ) as mock_send:
            resp = await staff_client.post(
                f"/api/v1/card-applications/staff/{app_row.id}/review",
                json={"status": "approved", "review_notes": "ok"},
            )

        assert resp.status_code == 409, resp.text
        # Global handler unwraps HTTPException(detail=dict) into error.message
        # (a dict), so the structured conflict info is preserved.
        message = resp.json()["error"]["message"]
        assert isinstance(message, dict)
        assert message["existing_card_number"] == "LIB-OLDCARD"
        assert message["user_id"] == test_patron.id
        assert "LIB-OLDCARD" in message["message"]
        mock_send.assert_not_awaited()

        # Confirm state unchanged
        await test_db.refresh(app_row)
        assert app_row.status == CardApplicationStatus.pending
        assert app_row.assigned_card_number is None

    @pytest.mark.asyncio
    async def test_staff_approve_links_anon_application_by_email(
        self, staff_client, test_db, test_user_data
    ):
        """#688: anon-submit application (user_id NULL) must link to the
        existing user account by email at approval time, so the patron's
        TMP card becomes the real assigned card."""
        from app.core.security import hash_password
        from app.models.user import User, UserRole

        user = User(
            email=test_user_data["email"],
            password_hash=hash_password(test_user_data["password"]),
            first_name="Anon",
            last_name="Submitter",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        app_row = await _insert_application(
            test_db,
            email=test_user_data["email"],
            status=CardApplicationStatus.pending,
            submitted_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert app_row.user_id is None

        with patch(
            "app.api.v1.card_applications.send_card_application_approved",
            new=AsyncMock(return_value=True),
        ):
            resp = await staff_client.post(
                f"/api/v1/card-applications/staff/{app_row.id}/review",
                json={"status": "approved", "review_notes": "linked by email"},
            )

        assert resp.status_code == 200, resp.text
        card_number = resp.json()["assigned_card_number"]
        assert card_number

        await test_db.refresh(app_row)
        await test_db.refresh(user)
        assert app_row.user_id == user.id, "application back-linked to user"
        assert user.library_card == card_number, "user's card updated to approved card"

    @pytest.mark.asyncio
    async def test_staff_approve_anon_no_email_match_does_not_link(
        self, staff_client, test_db
    ):
        """#688: when no user exists with the application's email, approval
        proceeds (issues card_number) but leaves the application unlinked."""
        app_row = await _insert_application(
            test_db,
            email="nobody@example.com",
            status=CardApplicationStatus.pending,
            submitted_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        with patch(
            "app.api.v1.card_applications.send_card_application_approved",
            new=AsyncMock(return_value=True),
        ):
            resp = await staff_client.post(
                f"/api/v1/card-applications/staff/{app_row.id}/review",
                json={"status": "approved", "review_notes": "no match"},
            )

        assert resp.status_code == 200, resp.text
        assert resp.json()["assigned_card_number"]

        await test_db.refresh(app_row)
        assert app_row.user_id is None
        assert app_row.assigned_card_number is not None

    @pytest.mark.asyncio
    async def test_staff_approve_anon_email_match_with_existing_card_returns_409(
        self, staff_client, test_db, test_user_data
    ):
        """#688: same overwrite-protection as the user_id path — if the
        email-matched user already has a library_card, refuse with 409."""
        from app.core.security import hash_password
        from app.models.user import User, UserRole

        user = User(
            email=test_user_data["email"],
            password_hash=hash_password(test_user_data["password"]),
            first_name="Has",
            last_name="Card",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            library_card="LIB-EXISTING",
        )
        test_db.add(user)
        await test_db.commit()

        app_row = await _insert_application(
            test_db,
            email=test_user_data["email"],
            status=CardApplicationStatus.pending,
            submitted_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert app_row.user_id is None

        with patch(
            "app.api.v1.card_applications.send_card_application_approved",
            new=AsyncMock(return_value=True),
        ) as mock_send:
            resp = await staff_client.post(
                f"/api/v1/card-applications/staff/{app_row.id}/review",
                json={"status": "approved", "review_notes": "should 409"},
            )

        assert resp.status_code == 409, resp.text
        message = resp.json()["error"]["message"]
        assert isinstance(message, dict)
        assert message["existing_card_number"] == "LIB-EXISTING"
        mock_send.assert_not_awaited()

        await test_db.refresh(app_row)
        assert app_row.status == CardApplicationStatus.pending
        assert app_row.assigned_card_number is None

    @pytest.mark.asyncio
    async def test_staff_deny_sends_denial_email_with_reason(
        self, staff_client, test_db
    ):
        app_row = await _insert_application(
            test_db,
            email="alex.patron@example.com",
            status=CardApplicationStatus.pending,
            submitted_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        with patch(
            "app.api.v1.card_applications.send_card_application_denied",
            new=AsyncMock(return_value=True),
        ) as mock_send:
            resp = await staff_client.post(
                f"/api/v1/card-applications/staff/{app_row.id}/review",
                json={
                    "status": "denied",
                    "denial_reason": "Could not verify address",
                    "review_notes": "ID address didn't match utility bill",
                },
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "denied"
        assert body["denial_reason"] == "Could not verify address"
        mock_send.assert_awaited_once()
        kwargs = mock_send.await_args.kwargs
        assert kwargs["to_email"] == "alex.patron@example.com"
        assert kwargs["denial_reason"] == "Could not verify address"


# ============================================================================
# Staff list endpoint sort behaviour
# ============================================================================


class TestListApplicationsSort:
    """Verify pending defaults oldest-first, approved newest-first, override works."""

    async def _seed_three(self, db, status: CardApplicationStatus):
        now = datetime.now(timezone.utc)
        emails = []
        for idx, offset_hours in enumerate([72, 48, 24]):
            email = f"sort-{status.value}-{idx}@example.com"
            emails.append(email)
            await _insert_application(
                db,
                email=email,
                status=status,
                submitted_at=now - timedelta(hours=offset_hours),
                reviewed_at=(
                    now - timedelta(hours=offset_hours - 1)
                    if status
                    in (
                        CardApplicationStatus.approved,
                        CardApplicationStatus.denied,
                    )
                    else None
                ),
                assigned_card_number=(
                    f"LIB-S{status.value[:3].upper()}{idx}"
                    if status == CardApplicationStatus.approved
                    else None
                ),
                denial_reason=(
                    "Some reason"
                    if status == CardApplicationStatus.denied
                    else None
                ),
            )
        return emails  # emails[0] = oldest, emails[-1] = newest

    @pytest.mark.asyncio
    async def test_pending_defaults_oldest_first(self, staff_client, test_db):
        emails = await self._seed_three(test_db, CardApplicationStatus.pending)
        resp = await staff_client.get(
            "/api/v1/card-applications/staff?status=pending"
        )
        assert resp.status_code == 200
        returned = [app["email"] for app in resp.json()["applications"]]
        assert returned == emails  # oldest first

    @pytest.mark.asyncio
    async def test_approved_defaults_newest_first(self, staff_client, test_db):
        emails = await self._seed_three(test_db, CardApplicationStatus.approved)
        resp = await staff_client.get(
            "/api/v1/card-applications/staff?status=approved"
        )
        assert resp.status_code == 200
        returned = [app["email"] for app in resp.json()["applications"]]
        assert returned == list(reversed(emails))  # newest first

    @pytest.mark.asyncio
    async def test_explicit_sort_override_newest_first_on_pending(
        self, staff_client, test_db
    ):
        emails = await self._seed_three(test_db, CardApplicationStatus.pending)
        resp = await staff_client.get(
            "/api/v1/card-applications/staff"
            "?status=pending&sort=newest_first"
        )
        assert resp.status_code == 200
        returned = [app["email"] for app in resp.json()["applications"]]
        assert returned == list(reversed(emails))

    @pytest.mark.asyncio
    async def test_explicit_sort_override_oldest_first_on_approved(
        self, staff_client, test_db
    ):
        emails = await self._seed_three(test_db, CardApplicationStatus.approved)
        resp = await staff_client.get(
            "/api/v1/card-applications/staff"
            "?status=approved&sort=oldest_first"
        )
        assert resp.status_code == 200
        returned = [app["email"] for app in resp.json()["applications"]]
        assert returned == emails


# ============================================================================
# Public token-gated status endpoint (Issue #1028)
# ============================================================================


# Exact set of keys allowed in the public token response. Treat this as the
# PII guard -- any field added to CardApplicationPublicStatusResponse must be
# added here, after a deliberate review.
_PUBLIC_STATUS_ALLOWED_KEYS = {
    "status",
    "submitted_at",
    "reviewed_at",
}

# Fields we want explicitly confirmed absent. (Belt-and-suspenders for keys
# that would be especially damaging to leak via this anonymous endpoint.)
_PUBLIC_STATUS_FORBIDDEN_KEYS = {
    "first_name",
    "last_name",
    "full_name",
    "email",
    "phone",
    "date_of_birth",
    "address_line1",
    "address_line2",
    "city",
    "state",
    "zip_code",
    "id_type",
    "id_number_last4",
    "review_notes",
    "denial_reason",
    "user_id",
    "reviewed_by_id",
    "reviewed_by_name",
    "assigned_card_number",
    "check_token",
}


class TestCheckByToken:
    @pytest.mark.asyncio
    async def test_submit_generates_check_token_and_passes_to_email(
        self, client, test_db
    ):
        with patch(
            "app.api.v1.card_applications.send_card_application_received",
            new=AsyncMock(return_value=True),
        ) as mock_send:
            resp = await client.post(
                "/api/v1/card-applications", json=_base_payload()
            )
        assert resp.status_code == 201, resp.text
        kwargs = mock_send.await_args.kwargs
        token = kwargs.get("check_token")
        assert token, "expected check_token kwarg on confirmation email"
        # token_urlsafe(32) -> ~43 chars; reject empty/short tokens.
        assert isinstance(token, str) and len(token) >= 40

    @pytest.mark.asyncio
    async def test_check_by_token_returns_status_and_omits_pii(
        self, client, test_db
    ):
        submitted = datetime.now(timezone.utc) - timedelta(hours=1)
        app_row = await _insert_application(
            test_db,
            email="alex.patron@example.com",
            status=CardApplicationStatus.pending,
            submitted_at=submitted,
        )
        # Backfill a token directly (the fixture predates the column).
        app_row.check_token = "tok_test_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        await test_db.commit()

        resp = await client.get(
            f"/api/v1/card-applications/check-by-token/{app_row.check_token}"
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        # Response shape: exactly the allowed keys, nothing else.
        assert set(body.keys()) == _PUBLIC_STATUS_ALLOWED_KEYS

        # Forbidden PII fields explicitly NOT present.
        for forbidden in _PUBLIC_STATUS_FORBIDDEN_KEYS:
            assert forbidden not in body, (
                f"PII leak: {forbidden!r} returned by public token endpoint"
            )

        assert body["status"] == "pending"
        assert body["submitted_at"] is not None
        assert body["reviewed_at"] is None

    @pytest.mark.asyncio
    async def test_check_by_token_unknown_returns_404_not_403(self, client):
        """404 (not 403) so the route is not an email-existence oracle."""
        resp = await client.get(
            "/api/v1/card-applications/check-by-token/"
            "completely-bogus-token-value-that-should-never-match"
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_check_by_token_reviewed_exposes_reviewed_at(
        self, client, test_db
    ):
        """Once reviewed, reviewed_at populates; assigned_card_number stays out."""
        submitted = datetime.now(timezone.utc) - timedelta(days=2)
        reviewed = datetime.now(timezone.utc) - timedelta(hours=1)
        app_row = await _insert_application(
            test_db,
            email="alex.patron@example.com",
            status=CardApplicationStatus.approved,
            submitted_at=submitted,
            reviewed_at=reviewed,
            assigned_card_number="LSC-ABC123",
        )
        app_row.check_token = "tok_reviewed_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        await test_db.commit()

        resp = await client.get(
            f"/api/v1/card-applications/check-by-token/{app_row.check_token}"
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "approved"
        assert body["reviewed_at"] is not None
        # The assigned_card_number is NOT leaked through this endpoint.
        assert "assigned_card_number" not in body
