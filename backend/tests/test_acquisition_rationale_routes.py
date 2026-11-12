# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API tests for staff acquisition_rationale routes."""

import pytest
from httpx import AsyncClient

from app.models.acquisition_rationale import BehaviorTag
from app.models.catalog import CatalogItem


@pytest.mark.asyncio
async def test_post_rationale_creates(staff_client: AsyncClient, test_db):
    test_db.add(BehaviorTag(slug="new_parent", label="New parent", category="life_stage"))
    item = CatalogItem(title="Test", author="A", item_type="book")
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    resp = await staff_client.post(
        f"/api/v1/staff/catalog-items/{item.id}/acquisition-rationale",
        json={
            "signal_type": "gap_in_collection",
            "primary_use_case_slug": "new_parent",
            "weeding_condition": "current_5yr",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["catalog_item_id"] == item.id
    assert body["signal_type"] == "gap_in_collection"
    assert body["primary_use_case_slug"] == "new_parent"


@pytest.mark.asyncio
async def test_get_rationale_returns_404_when_missing(
    staff_client: AsyncClient, test_db
):
    item = CatalogItem(title="No rationale", author="A", item_type="book")
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    resp = await staff_client.get(
        f"/api/v1/staff/catalog-items/{item.id}/acquisition-rationale",
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_post_then_put_updates_rationale(staff_client: AsyncClient, test_db):
    test_db.add(BehaviorTag(slug="bedtime", label="Bedtime", category="use_moment"))
    test_db.add(BehaviorTag(slug="commute", label="Commute", category="use_moment"))
    item = CatalogItem(title="Updatable", author="A", item_type="book")
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    post = await staff_client.post(
        f"/api/v1/staff/catalog-items/{item.id}/acquisition-rationale",
        json={
            "signal_type": "staff_observation",
            "primary_use_case_slug": "bedtime",
            "weeding_condition": "current_5yr",
        },
    )
    assert post.status_code == 201, post.text

    put = await staff_client.put(
        f"/api/v1/staff/catalog-items/{item.id}/acquisition-rationale",
        json={
            "signal_type": "staff_observation",
            "primary_use_case_slug": "commute",
            "weeding_condition": "current_5yr",
        },
    )
    assert put.status_code == 200, put.text
    assert put.json()["primary_use_case_slug"] == "commute"


@pytest.mark.asyncio
async def test_post_rationale_conflict_when_exists(
    staff_client: AsyncClient, test_db
):
    test_db.add(BehaviorTag(slug="conflict_tag", label="Conflict", category="life_stage"))
    item = CatalogItem(title="Conflicting", author="A", item_type="book")
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    payload = {
        "signal_type": "purchase_request",
        "primary_use_case_slug": "conflict_tag",
        "weeding_condition": "current_5yr",
    }
    first = await staff_client.post(
        f"/api/v1/staff/catalog-items/{item.id}/acquisition-rationale",
        json=payload,
    )
    assert first.status_code == 201, first.text

    second = await staff_client.post(
        f"/api/v1/staff/catalog-items/{item.id}/acquisition-rationale",
        json=payload,
    )
    assert second.status_code == 409, second.text


@pytest.mark.asyncio
async def test_list_behavior_tags(staff_client: AsyncClient, test_db):
    test_db.add(BehaviorTag(slug="abc_test", label="Abc", category="life_stage"))
    await test_db.commit()

    resp = await staff_client.get("/api/v1/staff/behavior-tags")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    slugs = {t["slug"] for t in body["tags"]}
    assert "abc_test" in slugs


@pytest.mark.asyncio
async def test_signal_candidates_endpoint(staff_client: AsyncClient, test_db):
    item = CatalogItem(title="UniqueXYZ7777", author="A", item_type="book")
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    resp = await staff_client.get(
        f"/api/v1/staff/catalog-items/{item.id}/signal-candidates",
    )
    assert resp.status_code == 200, resp.text
    assert "candidates" in resp.json()


@pytest.mark.asyncio
async def test_list_missing_rationale_returns_ids(
    staff_client: AsyncClient, test_db
):
    item = CatalogItem(
        title="Missing rationale item", author="A", item_type="book"
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    resp = await staff_client.get(
        "/api/v1/staff/catalog-items/missing-rationale?limit=200",
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert item.id in body["catalog_item_ids"]


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access(client: AsyncClient, test_db):
    """An unauthenticated client (no auth header) is rejected by require_staff."""
    item = CatalogItem(title="Patron forbidden", author="A", item_type="book")
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    resp = await client.get(
        f"/api/v1/staff/catalog-items/{item.id}/acquisition-rationale",
    )
    assert resp.status_code in (401, 403)
