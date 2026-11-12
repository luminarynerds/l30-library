# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Write-path smoke tests -- real DB state transitions through the API.

Deeper than test_smoke.py's read happy-paths: each test drives a full
mutation round-trip (checkout -> checkin, place hold -> cancel) so a broken
write path goes red, not just a down read surface. Uses the project
test_catalog_item fixture and the patron client. Checkouts here are
catalog-item-level (item_copy_id is optional), so no ItemCopy is needed.
"""
import pytest

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestSmokeCheckoutCheckin:
    async def test_checkout_then_checkin(self, patron_client, test_catalog_item, system_settings):
        co = await patron_client.post(
            "/api/v1/circulation/checkout", json={"item_id": test_catalog_item.id}
        )
        assert co.status_code == 201, co.text
        checkout_id = co.json()["id"]

        ci = await patron_client.post(
            "/api/v1/circulation/checkin", params={"checkout_id": checkout_id}
        )
        assert ci.status_code == 200, ci.text
        assert ci.json()["status"] == "returned"


class TestSmokeHoldPlaceCancel:
    async def test_place_then_cancel_hold(self, patron_client, test_catalog_item):
        h = await patron_client.post(
            "/api/v1/circulation/holds", json={"item_id": test_catalog_item.id}
        )
        assert h.status_code == 201, h.text
        hold_id = h.json()["id"]

        c = await patron_client.delete(f"/api/v1/circulation/holds/{hold_id}")
        assert c.status_code == 204, c.text
