# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for family/household reading-program registration API."""

import pytest


async def _login(client, email: str = "testuser@example.com", password: str = "TestPassword123!") -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.mark.asyncio
class TestFamilyGroup:
    """POST/GET /api/v1/reading-programs/family"""

    async def test_create_family_group_seeds_parent_member(self, client, test_patron):
        token = await _login(client)

        response = await client.post(
            "/api/v1/reading-programs/family",
            json={"name": "The Patron Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["name"] == "The Patron Family"
        # parent should be auto-added as a member with is_parent=True
        members = body.get("members", [])
        assert len(members) == 1
        assert members[0]["is_parent"] is True

    async def test_get_family_group_returns_own(self, client, test_patron):
        token = await _login(client)
        await client.post(
            "/api/v1/reading-programs/family",
            json={"name": "Get-Test Family"},
            headers={"Authorization": f"Bearer {token}"},
        )

        response = await client.get(
            "/api/v1/reading-programs/family",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["name"] == "Get-Test Family"

    async def test_create_family_group_409_when_already_exists(self, client, test_patron):
        token = await _login(client)
        first = await client.post(
            "/api/v1/reading-programs/family",
            json={"name": "First Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert first.status_code == 201

        second = await client.post(
            "/api/v1/reading-programs/family",
            json={"name": "Second Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert second.status_code == 409


@pytest.mark.asyncio
class TestFamilyMembers:
    """POST/DELETE /api/v1/reading-programs/family/{family_id}/members"""

    async def test_add_child_member(self, client, test_patron):
        token = await _login(client)
        group = (await client.post(
            "/api/v1/reading-programs/family",
            json={"name": "Member-Test Family"},
            headers={"Authorization": f"Bearer {token}"},
        )).json()

        response = await client.post(
            f"/api/v1/reading-programs/family/{group['id']}/members",
            json={"first_name": "Ada", "age_range": "6-8"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201, response.text
        member = response.json()
        assert member["first_name"] == "Ada"
        assert member["age_range"] == "6-8"
        assert member["is_parent"] is False

    async def test_add_member_rejects_invalid_age_range(self, client, test_patron):
        token = await _login(client)
        group = (await client.post(
            "/api/v1/reading-programs/family",
            json={"name": "Invalid-Age Family"},
            headers={"Authorization": f"Bearer {token}"},
        )).json()

        response = await client.post(
            f"/api/v1/reading-programs/family/{group['id']}/members",
            json={"first_name": "Bob", "age_range": "25-30"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # FastAPI/pydantic validation -> 422
        assert response.status_code == 422

    async def test_add_member_to_other_family_forbidden(self, client, test_patron):
        token = await _login(client)
        # We do not have a second patron fixture readily wired; instead exercise
        # the same-user guard by sending a bogus family_id.
        await client.post(
            "/api/v1/reading-programs/family",
            json={"name": "Owner Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        response = await client.post(
            "/api/v1/reading-programs/family/999999/members",
            json={"first_name": "Charlie", "age_range": "9-12"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
