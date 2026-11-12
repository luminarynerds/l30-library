# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for catalog item creation and MARC export."""

import pytest


async def _staff_auth_header(client, test_staff):
    """Authenticate as staff user and return auth header."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_staff.email, "password": "StaffPassword123!"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
@pytest.mark.asyncio
class TestCatalogItemCreationAndMARC:
    """Validate creating catalog items and exporting MARC records."""

    async def test_staff_can_create_catalog_item(self, client, test_staff):
        auth_header = await _staff_auth_header(client, test_staff)

        payload = {
            "title": "The Testing Catalog Book",
            "author": "QA Librarian",
            "isbn": "9780123456789",
            "publisher": "LSC Test Press",
            "publication_year": 2026,
            "subjects": "Testing; Cataloging",
            "location": "Adult Nonfiction",
        }

        response = await client.post("/api/v1/catalog/", json=payload, headers=auth_header)

        assert response.status_code == 201
        data = response.json()
        assert data["id"] > 0
        assert data["title"] == payload["title"]
        assert data["author"] == payload["author"]
        assert data["isbn"] == payload["isbn"]

    async def test_created_item_can_be_exported_as_marc(self, client, test_staff):
        auth_header = await _staff_auth_header(client, test_staff)

        create_response = await client.post(
            "/api/v1/catalog/",
            json={
                "title": "MARC Export Validation",
                "author": "Metadata Team",
                "isbn": "9780987654321",
                "publication_year": 2025,
                "subjects": "MARC; Metadata",
            },
            headers=auth_header,
        )
        assert create_response.status_code == 201
        item_id = create_response.json()["id"]

        binary_response = await client.get(
            f"/api/v1/catalog/{item_id}/marc",
            params={"format": "binary"},
            headers=auth_header,
        )
        assert binary_response.status_code == 200
        assert binary_response.headers["content-type"].startswith("application/marc")
        assert len(binary_response.content) > 0

        marcxml_response = await client.get(
            f"/api/v1/catalog/{item_id}/marc",
            params={"format": "marcxml"},
            headers=auth_header,
        )
        assert marcxml_response.status_code == 200
        assert marcxml_response.headers["content-type"].startswith("application/xml")
        assert b"<record" in marcxml_response.content

        dc_response = await client.get(
            f"/api/v1/catalog/{item_id}/marc",
            params={"format": "dc"},
            headers=auth_header,
        )
        assert dc_response.status_code == 200
        assert b"xmlns:dc=\"http://purl.org/dc/elements/1.1/\"" in dc_response.content
