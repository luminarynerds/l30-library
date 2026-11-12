# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Setup wizard login-unblock regression tests.

Covers three fresh-install defects characterized in
docs/dist-install-characterization.md:

1. The wizard-created admin (POST /setup/admin) must come out with
   email_verified=True -- a fresh offline install has no mail server, so an
   admin who defaults to unverified can never pass login's verification gate.
2. /setup/demo/load must not be mutually exclusive with a real admin account
   -- both must be able to coexist during the wizard.
3. The example admin email domain used in INSTALL.md/setup.sh must actually
   pass EmailStr, unlike the *.local domain the onboarding brief originally
   suggested (email-validator rejects .local as a reserved/special-use TLD).
"""
import pytest
from httpx import AsyncClient
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from app.models.user import User, email_match_clause

# yourlibrary.example -- the non-reserved stand-in domain documented in
# INSTALL.md and setup.sh in place of a *.local address.
ADMIN_PAYLOAD = {
    "first_name": "Test",
    "last_name": "Admin",
    "email": "admin@yourlibrary.example",
    "password": "securepass123",
}


class TestWizardAdminEmailVerified:
    @pytest.mark.asyncio
    async def test_wizard_admin_is_email_verified(self, client: AsyncClient, db):
        response = await client.post("/api/v1/setup/admin", json=ADMIN_PAYLOAD)
        assert response.status_code == 201

        # User.email is encrypted at rest; == against plaintext can't match the
        # ciphertext, so look up via the email_hash blind index instead.
        result = await db.execute(select(User).where(email_match_clause(ADMIN_PAYLOAD["email"])))
        user = result.scalar_one()
        assert user.email_verified is True


class TestDemoLoadCoexistsWithAdmin:
    @pytest.mark.asyncio
    async def test_demo_load_not_blocked_by_existing_admin(self, client: AsyncClient):
        """Creating the founding admin first must not lock out demo data load.

        Before the fix, /demo/load 409'd once any admin existed (the
        "zero-admin gate"), making demo data and a real admin mutually
        exclusive. A missing seed file (expected in this test environment)
        is fine -- a 409 conflict is the specific bug being guarded against.
        """
        admin_resp = await client.post("/api/v1/setup/admin", json=ADMIN_PAYLOAD)
        assert admin_resp.status_code == 201

        demo_resp = await client.post("/api/v1/setup/demo/load")
        assert demo_resp.status_code != 409, demo_resp.json()


class TestExampleEmailDomainPassesValidation:
    def test_documented_example_domain_passes_emailstr(self):
        class _Model(BaseModel):
            email: EmailStr

        # Must not raise: yourlibrary.example is the domain documented in
        # INSTALL.md/setup.sh as the stand-in for a not-yet-registered domain.
        _Model(email="admin@yourlibrary.example")
