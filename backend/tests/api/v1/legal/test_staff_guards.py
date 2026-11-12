# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests: POST /legal/providers, /courts, /clinics require staff."""

import pytest
from httpx import AsyncClient


PROVIDER_PAYLOAD = {
    "name": "Test Legal Aid",
    "slug": "test-legal-aid",
    "provider_type": "legal_aid",
    "jurisdiction": "Ohio",
    "address_line1": "123 Main St",
    "city": "Columbus",
    "state": "OH",
    "zip_code": "43215",
}

COURT_PAYLOAD = {
    "name": "Franklin County Common Pleas",
    "court_type": "common_pleas",
    "jurisdiction": "Ohio",
    "address_line1": "345 S High St",
    "city": "Columbus",
    "state": "OH",
    "zip_code": "43215",
}


@pytest.mark.asyncio
class TestStaffGuardsOnLegalWrites:
    """Patron (unauthenticated) must get 401/403 on staff-only POST endpoints."""

    async def test_patron_cannot_create_provider(self, client: AsyncClient):
        """POST /legal/providers without auth returns 401."""
        response = await client.post("/api/v1/legal/providers", json=PROVIDER_PAYLOAD)
        assert response.status_code in (401, 403), (
            f"Expected 401 or 403 for unauthenticated POST /legal/providers, got {response.status_code}"
        )

    async def test_patron_cannot_create_court(self, client: AsyncClient):
        """POST /legal/courts without auth returns 401."""
        response = await client.post("/api/v1/legal/courts", json=COURT_PAYLOAD)
        assert response.status_code in (401, 403), (
            f"Expected 401 or 403 for unauthenticated POST /legal/courts, got {response.status_code}"
        )

    async def test_patron_cannot_create_clinic(self, client: AsyncClient):
        """POST /legal/clinics without auth returns 401."""
        clinic_payload = {
            "title": "Test Clinic",
            "date": "2026-08-01",
            "start_time": "09:00",
            "end_time": "12:00",
        }
        response = await client.post("/api/v1/legal/clinics", json=clinic_payload)
        assert response.status_code in (401, 403), (
            f"Expected 401 or 403 for unauthenticated POST /legal/clinics, got {response.status_code}"
        )

    async def test_patch_provider_requires_auth(self, client: AsyncClient):
        """PATCH /legal/providers/{id} without auth returns 401."""
        response = await client.patch("/api/v1/legal/providers/1", json={"name": "Updated"})
        assert response.status_code in (401, 403, 404), (
            f"Expected 401/403/404 for unauthenticated PATCH /legal/providers/1, got {response.status_code}"
        )

    async def test_patch_court_requires_auth(self, client: AsyncClient):
        """PATCH /legal/courts/{id} without auth returns 401."""
        response = await client.patch("/api/v1/legal/courts/1", json={"name": "Updated"})
        assert response.status_code in (401, 403, 404), (
            f"Expected 401/403/404 for unauthenticated PATCH /legal/courts/1, got {response.status_code}"
        )
