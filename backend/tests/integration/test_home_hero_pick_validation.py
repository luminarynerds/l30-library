# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hero picks must reference publicly displayable catalog items.

The public home page resolver suppresses heroes whose item is not
cataloged + public (services/home_page.py:_resolve_hero). Before this
guard, the admin endpoints accepted any item_id, so an admin could set
a hero that silently never rendered (prod hero id 2 -> uncataloged
item 137).
"""
import pytest

from app.models.catalog import CatalogingStatus, CatalogItem, SensitivityLevel

HERO_URL = "/api/v1/home/admin/hero-picks"


def _hero_payload(item_id: int) -> dict:
    return {
        "item_id": item_id,
        "annotation_md": "A staff favorite this season.",
        "cta_label": "Place hold",
        "active_from": "2026-01-01T00:00:00Z",
    }


async def _make_item(test_db, *, cataloging_status, sensitivity_level) -> CatalogItem:
    item = CatalogItem(
        title="Braiding Sweetgrass for Young Adults",
        author="Robin Wall Kimmerer",
        cataloging_status=cataloging_status,
        sensitivity_level=sensitivity_level,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def public_item(test_db):
    return await _make_item(
        test_db,
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
    )


@pytest.fixture
async def uncataloged_item(test_db):
    return await _make_item(
        test_db,
        cataloging_status=CatalogingStatus.UNCATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
    )


@pytest.fixture
async def sensitive_item(test_db):
    return await _make_item(
        test_db,
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.SENSITIVE,
    )


@pytest.mark.integration
class TestHeroPickItemValidation:
    async def test_create_with_public_item_succeeds(self, admin_client, public_item):
        resp = await admin_client.post(HERO_URL, json=_hero_payload(public_item.id))
        assert resp.status_code == 201, resp.text
        assert resp.json()["item"]["id"] == public_item.id

    async def test_create_with_uncataloged_item_rejected(
        self, admin_client, uncataloged_item
    ):
        resp = await admin_client.post(HERO_URL, json=_hero_payload(uncataloged_item.id))
        assert resp.status_code == 422, resp.text
        # Global handler wraps HTTPException as {"error": {"message": ...}}.
        assert "cataloged" in resp.json()["error"]["message"]

    async def test_create_with_sensitive_item_rejected(
        self, admin_client, sensitive_item
    ):
        resp = await admin_client.post(HERO_URL, json=_hero_payload(sensitive_item.id))
        assert resp.status_code == 422, resp.text

    async def test_create_with_missing_item_404(self, admin_client):
        resp = await admin_client.post(HERO_URL, json=_hero_payload(99_999_999))
        assert resp.status_code == 404, resp.text

    async def test_update_to_nonpublic_item_rejected(
        self, admin_client, public_item, uncataloged_item
    ):
        created = await admin_client.post(HERO_URL, json=_hero_payload(public_item.id))
        assert created.status_code == 201, created.text
        hero_id = created.json()["id"]

        resp = await admin_client.patch(
            f"{HERO_URL}/{hero_id}", json={"item_id": uncataloged_item.id}
        )
        assert resp.status_code == 422, resp.text
        # Original item untouched on rejected update.
        listed = await admin_client.get(HERO_URL)
        assert listed.json()[0]["item"]["id"] == public_item.id
