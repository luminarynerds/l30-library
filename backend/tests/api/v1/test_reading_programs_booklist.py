# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for program booklist endpoints (Recommended Reads per program)."""

from datetime import date, timedelta

import pytest

from app.models.catalog import CatalogItem, ItemStatus
from app.models.organization_features import OrganizationFeatures
from app.models.reading import (
    ProgramBooklistItem,
    ReadingProgram,
    ReadingProgramType,
)
from app.services.organization_features_service import OrganizationFeaturesService


@pytest.fixture
async def features_booklist_on(test_db):
    feat = OrganizationFeatures(
        reading_programs_enabled=True,
        reading_programs_booklist_enabled=True,
    )
    test_db.add(feat)
    await test_db.commit()
    await test_db.refresh(feat)
    # Redis caches an org-features snapshot across tests; invalidate so
    # this test's DB row is what gets read/re-cached.
    await OrganizationFeaturesService.invalidate_cache()
    return feat


@pytest.fixture
async def features_booklist_off(test_db):
    feat = OrganizationFeatures(
        reading_programs_enabled=True,
        reading_programs_booklist_enabled=False,
    )
    test_db.add(feat)
    await test_db.commit()
    await test_db.refresh(feat)
    await OrganizationFeaturesService.invalidate_cache()
    return feat


@pytest.fixture
async def program(test_db):
    p = ReadingProgram(
        name="Summer Booklist Test",
        description="x",
        program_type=ReadingProgramType.summer,
        start_date=date.today() - timedelta(days=1),
        end_date=date.today() + timedelta(days=30),
        is_active=True,
    )
    test_db.add(p)
    await test_db.commit()
    await test_db.refresh(p)
    return p


@pytest.fixture
async def catalog_items(test_db):
    items = [
        CatalogItem(
            title=f"Booklist Title {i}",
            author=f"Author {i}",
            isbn=f"978-1-000000-0{i}-1",
            status=ItemStatus.available,
            call_number=f"BL-{i}",
        )
        for i in range(3)
    ]
    for it in items:
        test_db.add(it)
    await test_db.commit()
    for it in items:
        await test_db.refresh(it)
    return items


@pytest.mark.asyncio
class TestProgramBooklist:
    async def test_get_empty_returns_items_not_404(
        self, public_client, features_booklist_on, program
    ):
        r = await public_client.get(f"/api/v1/reading-programs/programs/{program.id}/booklist")
        assert r.status_code == 200
        assert r.json() == {"items": []}

    async def test_post_then_get_sorted_by_display_order(
        self, staff_client, features_booklist_on, program, catalog_items
    ):
        # Add items in reverse order
        for offset, item in enumerate(catalog_items):
            r = await staff_client.post(
                f"/api/v1/reading-programs/programs/{program.id}/booklist",
                json={
                    "catalog_item_id": item.id,
                    "display_order": 10 - offset,
                    "note": f"Pick {offset}",
                },
            )
            assert r.status_code == 201, r.text

        r = await staff_client.get(
            f"/api/v1/reading-programs/programs/{program.id}/booklist"
        )
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) == 3
        orders = [i["display_order"] for i in items]
        assert orders == sorted(orders)
        # selectinload populates catalog_item — no MissingGreenlet
        for i in items:
            assert i["catalog_item"]["id"]
            assert "available_for_hold" in i["catalog_item"]
            assert "status" in i["catalog_item"]

    async def test_duplicate_returns_409(
        self, staff_client, features_booklist_on, program, catalog_items
    ):
        r1 = await staff_client.post(
            f"/api/v1/reading-programs/programs/{program.id}/booklist",
            json={"catalog_item_id": catalog_items[0].id, "display_order": 0},
        )
        assert r1.status_code == 201
        r2 = await staff_client.post(
            f"/api/v1/reading-programs/programs/{program.id}/booklist",
            json={"catalog_item_id": catalog_items[0].id, "display_order": 1},
        )
        assert r2.status_code == 409

    async def test_patch_updates_note_and_order(
        self, staff_client, features_booklist_on, program, catalog_items
    ):
        r = await staff_client.post(
            f"/api/v1/reading-programs/programs/{program.id}/booklist",
            json={"catalog_item_id": catalog_items[0].id, "display_order": 0},
        )
        item_id = r.json()["id"]
        r2 = await staff_client.patch(
            f"/api/v1/reading-programs/programs/{program.id}/booklist/{item_id}",
            json={"note": "updated", "display_order": 5},
        )
        assert r2.status_code == 200
        body = r2.json()
        assert body["note"] == "updated"
        assert body["display_order"] == 5

    async def test_delete_removes_item(
        self, staff_client, features_booklist_on, program, catalog_items
    ):
        r = await staff_client.post(
            f"/api/v1/reading-programs/programs/{program.id}/booklist",
            json={"catalog_item_id": catalog_items[0].id, "display_order": 0},
        )
        item_id = r.json()["id"]
        d = await staff_client.delete(
            f"/api/v1/reading-programs/programs/{program.id}/booklist/{item_id}"
        )
        assert d.status_code == 204
        g = await staff_client.get(
            f"/api/v1/reading-programs/programs/{program.id}/booklist"
        )
        assert g.json()["items"] == []

    async def test_reorder_bulk_updates(
        self, staff_client, features_booklist_on, program, catalog_items
    ):
        ids = []
        for i, item in enumerate(catalog_items):
            r = await staff_client.post(
                f"/api/v1/reading-programs/programs/{program.id}/booklist",
                json={"catalog_item_id": item.id, "display_order": i},
            )
            ids.append(r.json()["id"])
        # Reverse order
        r = await staff_client.put(
            f"/api/v1/reading-programs/programs/{program.id}/booklist/reorder",
            json={
                "order": [
                    {"item_id": ids[0], "display_order": 2},
                    {"item_id": ids[1], "display_order": 1},
                    {"item_id": ids[2], "display_order": 0},
                ]
            },
        )
        assert r.status_code == 200
        items = r.json()["items"]
        assert [i["id"] for i in items] == [ids[2], ids[1], ids[0]]

    async def test_patron_get_ok_non_staff_post_forbidden(
        self, public_client, features_booklist_on, program, catalog_items
    ):
        # Patron-equivalent (no auth) can GET
        r = await public_client.get(
            f"/api/v1/reading-programs/programs/{program.id}/booklist"
        )
        assert r.status_code == 200
        # Public POST should be unauthorized/forbidden
        rp = await public_client.post(
            f"/api/v1/reading-programs/programs/{program.id}/booklist",
            json={"catalog_item_id": catalog_items[0].id, "display_order": 0},
        )
        assert rp.status_code in (401, 403)

    async def test_flag_off_returns_404_on_all_endpoints(
        self, staff_client, features_booklist_off, program, catalog_items
    ):
        # GET
        r = await staff_client.get(
            f"/api/v1/reading-programs/programs/{program.id}/booklist"
        )
        assert r.status_code == 404
        # POST
        r = await staff_client.post(
            f"/api/v1/reading-programs/programs/{program.id}/booklist",
            json={"catalog_item_id": catalog_items[0].id, "display_order": 0},
        )
        assert r.status_code == 404
        # PATCH
        r = await staff_client.patch(
            f"/api/v1/reading-programs/programs/{program.id}/booklist/1",
            json={"note": "x"},
        )
        assert r.status_code == 404
        # DELETE
        r = await staff_client.delete(
            f"/api/v1/reading-programs/programs/{program.id}/booklist/1"
        )
        assert r.status_code == 404
        # PUT reorder
        r = await staff_client.put(
            f"/api/v1/reading-programs/programs/{program.id}/booklist/reorder",
            json={"order": []},
        )
        assert r.status_code == 404

    async def test_selectinload_no_missing_greenlet(
        self, staff_client, features_booklist_on, program, catalog_items, test_db
    ):
        # Create row directly via ORM to ensure GET path eager-loads cleanly.
        row = ProgramBooklistItem(
            program_id=program.id,
            catalog_item_id=catalog_items[0].id,
            display_order=0,
            note="direct",
        )
        test_db.add(row)
        await test_db.commit()
        r = await staff_client.get(
            f"/api/v1/reading-programs/programs/{program.id}/booklist"
        )
        assert r.status_code == 200
        body = r.json()
        assert body["items"][0]["catalog_item"]["title"].startswith("Booklist Title")
