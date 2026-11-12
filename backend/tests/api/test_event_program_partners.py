# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API tests for /api/v1/program-partners (events Phase 2)."""

import pytest

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.event_program_partner import EventProgramPartner
from app.models.user import User


@pytest.fixture
def authed_client_factory(client):
    def _auth(user: User):
        app.dependency_overrides[get_current_user] = lambda: user
        return client

    yield _auth
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_list_program_partners_returns_active_by_default(
    test_db, client
):
    """Soft-deleted partners MUST NOT appear in the default listing."""
    active = EventProgramPartner(
        name="Active Partner", slug="active_partner", is_active=True
    )
    inactive = EventProgramPartner(
        name="Retired Partner", slug="retired_partner", is_active=False
    )
    test_db.add_all([active, inactive])
    await test_db.commit()

    resp = await client.get("/api/v1/program-partners")
    assert resp.status_code == 200, resp.text
    names = [row["name"] for row in resp.json()["data"]]
    assert "Active Partner" in names
    assert "Retired Partner" not in names

    # include_inactive=true surfaces soft-deleted rows.
    resp2 = await client.get("/api/v1/program-partners?include_inactive=true")
    assert resp2.status_code == 200
    names2 = [row["name"] for row in resp2.json()["data"]]
    assert "Retired Partner" in names2


@pytest.mark.asyncio
async def test_create_program_partner_admin_only(
    test_db, authed_client_factory, test_patron, test_admin
):
    """Patron POST → 403; admin POST → 201."""
    c = authed_client_factory(test_patron)
    resp = await c.post(
        "/api/v1/program-partners",
        json={"name": "Friends of the Library"},
    )
    assert resp.status_code == 403, resp.text

    c2 = authed_client_factory(test_admin)
    resp2 = await c2.post(
        "/api/v1/program-partners",
        json={"name": "Friends of the Library"},
    )
    assert resp2.status_code == 201, resp2.text


@pytest.mark.asyncio
async def test_create_program_partner_generates_slug_from_name(
    test_db, authed_client_factory, test_admin
):
    """Server derives slug from name; client cannot override on POST."""
    c = authed_client_factory(test_admin)
    resp = await c.post(
        "/api/v1/program-partners",
        json={"name": "Friends of the Library"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["slug"] == "friends_of_the_library"

    # Different name that slugs to the same base — server must append a
    # unique suffix to the slug while preserving the distinct name.
    resp3 = await c.post(
        "/api/v1/program-partners",
        json={"name": "Friends, of the Library!"},
    )
    assert resp3.status_code == 201, resp3.text
    assert resp3.json()["slug"].startswith("friends_of_the_library")
    assert resp3.json()["slug"] != "friends_of_the_library"


@pytest.mark.asyncio
async def test_delete_program_partner_soft_deletes(
    test_db, authed_client_factory, test_admin
):
    """Default DELETE flips is_active=false, leaves row in DB."""
    partner = EventProgramPartner(
        name="To Be Retired", slug="to_be_retired", is_active=True
    )
    test_db.add(partner)
    await test_db.commit()
    await test_db.refresh(partner)
    partner_id = partner.id

    c = authed_client_factory(test_admin)
    resp = await c.delete(f"/api/v1/program-partners/{partner_id}")
    assert resp.status_code == 204, resp.text

    # Row still exists, just inactive.
    await test_db.refresh(partner)
    assert partner.is_active is False


@pytest.mark.asyncio
async def test_old_partner_organizations_url_returns_404(client):
    """Clean break: the old /api/v1/partner-organizations URL is no longer served.

    No backward-compat alias in this PR — callers (frontend, scripts) MUST
    migrate to /api/v1/program-partners.
    """
    resp = await client.get("/api/v1/partner-organizations")
    assert resp.status_code == 404, resp.text
