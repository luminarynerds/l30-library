# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for the catalog cataloging-workflow fields.

These cover the bug where CatalogItemCreate did not declare `barcode`,
`cataloging_status`, `call_number`, `dewey_decimal`, or `lc_classification`,
so Pydantic silently dropped them on POST and every new item persisted as
barcode=NULL, cataloging_status=uncataloged regardless of payload.
"""
import contextlib
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.catalog import CatalogItem, CatalogingStatus


pytestmark = pytest.mark.asyncio


def _no_cache():
    """Stack the cache/BIBFRAME patches the rest of the catalog API tests use.

    Without these the create/update endpoints try to hit redis (which is None
    in the test container) and crash inside `invalidate_catalog_cache`.
    """
    stack = contextlib.ExitStack()
    targets = [
        "app.api.v1.catalog.crud.invalidate_catalog_cache",
        "app.api.v1.catalog.crud.invalidate_collection_reports",
        "app.api.v1.catalog.helpers.get_cached",
        "app.api.v1.catalog.helpers.set_cached",
    ]
    for t in targets:
        stack.enter_context(patch(t, new=AsyncMock(return_value=None)))
    stack.enter_context(patch(
        "app.api.v1.catalog.crud._sync_to_bibframe_background", new=AsyncMock()
    ))
    stack.enter_context(patch(
        "app.api.v1.catalog.crud._update_bibframe_background", new=AsyncMock()
    ))
    return stack


async def test_create_endpoint_persists_barcode_and_status(staff_client, test_db, test_staff):
    """POST /api/v1/catalog/ with workflow fields persists them on the row."""
    with _no_cache():
        resp = await staff_client.post(
            "/api/v1/catalog/",
            json={
                "title": "Workflow Fields Test",
                "barcode": "WFLD-CRUD-001",
                "cataloging_status": "cataloged",
                "call_number": "813.54 SMI",
                "dewey_decimal": "813.54",
                "lc_classification": "PS3573",
            },
        )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["barcode"] == "WFLD-CRUD-001"
    assert body["cataloging_status"] == "cataloged"
    assert body["call_number"] == "813.54 SMI"
    assert body["dewey_decimal"] == "813.54"
    assert body["lc_classification"] == "PS3573"
    # Stamps populated on transition to cataloged
    assert body["cataloged_at"] is not None
    assert body["cataloged_by_id"] == test_staff.id

    # Confirm against the DB, not just the response payload.
    row = (await test_db.execute(
        select(CatalogItem).where(CatalogItem.id == body["id"])
    )).scalar_one()
    assert row.barcode == "WFLD-CRUD-001"
    assert row.cataloging_status == CatalogingStatus.CATALOGED
    assert row.cataloged_by_id == test_staff.id
    assert row.cataloged_at is not None


async def test_create_uncataloged_does_not_stamp(staff_client, test_db):
    """A create that lands in uncataloged must not set cataloged_at."""
    with _no_cache():
        resp = await staff_client.post(
            "/api/v1/catalog/",
            json={"title": "Still Uncataloged", "barcode": "WFLD-UNC-001"},
        )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["cataloging_status"] == "uncataloged"
    assert body["cataloged_at"] is None
    assert body["cataloged_by_id"] is None


async def test_staff_create_endpoint_persists_workflow_fields(staff_client, test_db, test_staff):
    """POST /api/v1/staff/catalog has the same bug surface; verify the fix."""
    # The staff endpoint doesn't touch the cache, but be defensive.
    with _no_cache():
        resp = await staff_client.post(
            "/api/v1/staff/catalog",
            json={
                "title": "Staff Endpoint Workflow",
                "barcode": "WFLD-STAFF-001",
                "cataloging_status": "cataloged",
            },
        )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["barcode"] == "WFLD-STAFF-001"
    assert body["cataloging_status"] == "cataloged"
    assert body["cataloged_by_id"] == test_staff.id


async def test_update_transition_stamps_cataloged_metadata(staff_client, test_db, test_staff):
    """PATCH that flips cataloging_status to cataloged stamps at + by_id."""
    item = CatalogItem(
        title="Pre-existing Uncataloged",
        cataloging_status=CatalogingStatus.UNCATALOGED,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    with _no_cache():
        resp = await staff_client.patch(
            f"/api/v1/catalog/{item.id}",
            json={"cataloging_status": "cataloged"},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["cataloging_status"] == "cataloged"
    assert body["cataloged_at"] is not None
    assert body["cataloged_by_id"] == test_staff.id


async def test_update_does_not_restamp_already_cataloged(staff_client, test_db, test_staff):
    """A second update on an already-cataloged item must not overwrite stamps."""
    from datetime import datetime, timezone, timedelta

    earlier = datetime.now(timezone.utc) - timedelta(days=30)
    item = CatalogItem(
        title="Already Cataloged",
        cataloging_status=CatalogingStatus.CATALOGED,
        cataloged_at=earlier,
        cataloged_by_id=None,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    with _no_cache():
        resp = await staff_client.patch(
            f"/api/v1/catalog/{item.id}",
            json={"call_number": "NEW-CN"},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Stamps unchanged -- already-stamped items don't get re-stamped.
    assert body["cataloged_by_id"] is None
    returned_at = datetime.fromisoformat(body["cataloged_at"].replace("Z", "+00:00"))
    # Backend round-trips through SQLite-in-test which drops tzinfo; normalise
    # both sides to UTC-aware before diffing so the assertion is portable.
    if returned_at.tzinfo is None:
        returned_at = returned_at.replace(tzinfo=timezone.utc)
    assert abs((returned_at - earlier).total_seconds()) < 1


async def test_duplicate_barcode_returns_409(staff_client, test_db):
    """The catalog_items_barcode_key unique constraint must surface as 409."""
    with _no_cache():
        first = await staff_client.post(
            "/api/v1/catalog/",
            json={"title": "First With Barcode", "barcode": "WFLD-DUP-001"},
        )
        assert first.status_code == 201, first.text

        dup = await staff_client.post(
            "/api/v1/catalog/",
            json={"title": "Second With Same Barcode", "barcode": "WFLD-DUP-001"},
        )
    assert dup.status_code == 409, dup.text
    assert "Barcode already in use" in dup.text
