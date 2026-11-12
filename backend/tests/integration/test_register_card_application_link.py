# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration test for the anon-submit -> register linkage on library card
applications.

When a patron submits a card application without an account (user_id NULL),
then registers an account with the same email, the application must be
re-linked to the new user_id so staff approval can write the assigned
card back to the user. Without this, the patron ends up with a temp card
on their user row AND an orphan approved application with the real card.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.card_application import (
    CardApplicationStatus,
    LibraryCardApplication,
)
from app.models.user import User


@pytest.fixture(autouse=True)
def _test_env_setup():
    """Test-env stubs: in-memory rate limiter, fake Redis, email-validator
    DNS bypass. Routers are registered at app-import time in main.py."""
    from app.core.rate_limit import limiter
    limiter.enabled = False

    import app.core.security as sec_module
    sec_module._redis_available = True
    if not hasattr(sec_module, "_fake_redis_store"):
        sec_module._fake_redis_store = {}

    class _FakeRedis:
        def exists(self, key):
            return 1 if key in sec_module._fake_redis_store else 0

        def ping(self):
            return True

        def setex(self, key, time, value):
            sec_module._fake_redis_store[key] = value

    sec_module._redis_client = _FakeRedis()

    import email_validator
    email_validator.TEST_ENVIRONMENT = True


async def _insert_anon_application(
    db, *, email: str, status: CardApplicationStatus = CardApplicationStatus.pending
) -> LibraryCardApplication:
    """Insert an anonymous (user_id NULL) application directly."""
    row = LibraryCardApplication(
        first_name="Anon",
        last_name="Applicant",
        email=email,
        address_line1="1 Test St",
        city="Smithville",
        state="ON",
        zip_code="K0H 1R0",
        status=status,
        submitted_at=datetime.now(timezone.utc) - timedelta(hours=1),
        user_id=None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    assert row.user_id is None
    return row


@pytest.mark.integration
class TestAnonApplicationLinkedOnRegister:
    async def test_pending_anon_application_gets_user_id_on_register(
        self, client, test_db
    ):
        """Happy path: anon submits, then registers -> application.user_id set."""
        email = "anon.link@l30.org"
        anon_app = await _insert_anon_application(test_db, email=email)

        payload = {
            "email": email,
            "password": "StrongP@ss1word",
            "first_name": "Anon",
            "last_name": "Applicant",
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 201, resp.text

        new_user = (
            await test_db.execute(select(User).where(User.email == email))
        ).scalar_one()

        await test_db.refresh(anon_app)
        assert anon_app.user_id == new_user.id, (
            "anonymous pending application must be re-linked to the new user "
            "or staff approval will orphan the assigned card"
        )

    async def test_under_review_anon_application_also_links(self, client, test_db):
        """An application already pulled into under_review must also link."""
        email = "anon.review@l30.org"
        anon_app = await _insert_anon_application(
            test_db,
            email=email,
            status=CardApplicationStatus.under_review,
        )

        payload = {
            "email": email,
            "password": "StrongP@ss1word",
            "first_name": "Anon",
            "last_name": "Review",
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 201, resp.text

        new_user = (
            await test_db.execute(select(User).where(User.email == email))
        ).scalar_one()
        await test_db.refresh(anon_app)
        assert anon_app.user_id == new_user.id

    async def test_linkage_is_case_insensitive(self, client, test_db):
        """Email match must be case-insensitive.

        CardApplicationCreate.email is plain EmailStr (only normalizes the
        domain); UserCreate.email is TestableEmail (normalizes via
        email-validator). If the application was submitted with a
        differently-cased local-part than the eventual registration, an
        exact equality match would silently fail and the orphan-card bug
        would reappear.
        """
        anon_app = await _insert_anon_application(
            test_db, email="Anon.Mixed@l30.org"
        )

        payload = {
            "email": "anon.mixed@l30.org",
            "password": "StrongP@ss1word",
            "first_name": "Anon",
            "last_name": "Mixed",
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 201, resp.text

        new_user = (
            await test_db.execute(
                select(User).where(User.email == "anon.mixed@l30.org")
            )
        ).scalar_one()
        await test_db.refresh(anon_app)
        assert anon_app.user_id == new_user.id

    async def test_other_email_application_is_not_touched(self, client, test_db):
        """Linkage must match on email; do not steal someone else's pending app."""
        other_email = "someone.else@l30.org"
        other_app = await _insert_anon_application(test_db, email=other_email)

        register_email = "fresh.user@l30.org"
        payload = {
            "email": register_email,
            "password": "StrongP@ss1word",
            "first_name": "Fresh",
            "last_name": "User",
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 201, resp.text

        await test_db.refresh(other_app)
        assert other_app.user_id is None, (
            "registration must only link applications matching the new user's "
            "email"
        )

    async def test_approved_anon_application_is_not_relinked(self, client, test_db):
        """A previously-decided application (approved/denied) is out of scope.

        Linking it would also need to backfill user.library_card from
        application.assigned_card_number; that's a separate workflow we are
        deliberately not handling in the registration path.
        """
        email = "anon.approved@l30.org"
        approved_app = LibraryCardApplication(
            first_name="Anon",
            last_name="Approved",
            email=email,
            address_line1="1 Test St",
            city="Smithville",
            state="ON",
            zip_code="K0H 1R0",
            status=CardApplicationStatus.approved,
            submitted_at=datetime.now(timezone.utc) - timedelta(days=10),
            reviewed_at=datetime.now(timezone.utc) - timedelta(days=5),
            assigned_card_number="LSC-OLDCRD",
            user_id=None,
        )
        test_db.add(approved_app)
        await test_db.commit()
        await test_db.refresh(approved_app)

        payload = {
            "email": email,
            "password": "StrongP@ss1word",
            "first_name": "Anon",
            "last_name": "Approved",
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        # The submit-side guard rejects re-applies after recent approval, but
        # /auth/register has no such guard; registration should succeed.
        assert resp.status_code == 201, resp.text

        await test_db.refresh(approved_app)
        assert approved_app.user_id is None, (
            "approved applications must not be auto-relinked on register "
            "(would need to backfill user.library_card; out of scope)"
        )


@pytest.mark.integration
class TestCheckEndpointStaffGated:
    """Regression: GET /card-applications/check/{email} is staff-only.

    The patron-facing 'Check Status' tab was hidden in the same PR as this
    test because that tab called this endpoint unauthenticated and 403'd.
    Follow-up issue #1028 will introduce a token-based patron-callable
    route; until then this assertion locks in that the existing route
    stays gated.
    """

    async def test_unauthenticated_check_by_email_is_forbidden(
        self, client, test_db
    ):
        email = "anon.gate@l30.org"
        await _insert_anon_application(test_db, email=email)

        resp = await client.get(f"/api/v1/card-applications/check/{email}")
        assert resp.status_code in (401, 403), (
            f"expected staff-gated 401/403, got {resp.status_code}: {resp.text}"
        )
