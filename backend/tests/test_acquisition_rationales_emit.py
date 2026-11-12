# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests: rationale create/update routes emit to librarian-agent
KB as a non-fatal side effect."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.acquisition_rationale import BehaviorTag
from app.models.catalog import CatalogItem


# Path used by every patch() in this file. Routes call
# LibrarianAgentClient(...).emit_rationale_aku(...), so we patch the
# unbound coroutine method at the module where it's imported.
EMIT_PATH = (
    "app.api.v1.staff.acquisition_rationales."
    "LibrarianAgentClient.emit_rationale_aku"
)


async def _seed_item_and_tags(test_db) -> CatalogItem:
    test_db.add(BehaviorTag(slug="commute", label="Commute", category="use_moment"))
    test_db.add(BehaviorTag(slug="bedtime", label="Bedtime", category="use_moment"))
    item = CatalogItem(title="Emit Test Book", author="A", item_type="book")
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


_CREATE_PAYLOAD = {
    "signal_type": "purchase_request",
    "primary_use_case_slug": "commute",
    "weeding_condition": "current_5yr",
    "public_summary": "Bought because patrons keep asking for cyber-thrillers.",
}
_UPDATE_PAYLOAD = {
    "signal_type": "staff_observation",
    "primary_use_case_slug": "bedtime",
    "weeding_condition": "current_5yr",
    "public_summary": "Reclassified after librarian review.",
}


@pytest.mark.asyncio
async def test_post_rationale_invokes_emit_once(staff_client: AsyncClient, test_db):
    item = await _seed_item_and_tags(test_db)

    with patch(EMIT_PATH, new_callable=AsyncMock) as emit:
        emit.return_value = "aku-created-1"
        resp = await staff_client.post(
            f"/api/v1/staff/catalog-items/{item.id}/acquisition-rationale",
            json=_CREATE_PAYLOAD,
        )

    assert resp.status_code == 201, resp.text
    assert emit.await_count == 1
    # Verify the saved rationale was the one passed to emit
    kwargs = emit.await_args.kwargs
    assert kwargs["catalog_item"].id == item.id
    assert kwargs["rationale"].catalog_item_id == item.id
    assert kwargs["rationale"].primary_use_case_slug == "commute"


@pytest.mark.asyncio
async def test_put_rationale_invokes_emit_once(staff_client: AsyncClient, test_db):
    item = await _seed_item_and_tags(test_db)

    # Seed: create via POST first (we don't care if emit ran here)
    with patch(EMIT_PATH, new_callable=AsyncMock):
        post = await staff_client.post(
            f"/api/v1/staff/catalog-items/{item.id}/acquisition-rationale",
            json=_CREATE_PAYLOAD,
        )
        assert post.status_code == 201, post.text

    # Now PUT and assert emit fires exactly once for the update
    with patch(EMIT_PATH, new_callable=AsyncMock) as emit:
        emit.return_value = "aku-updated-1"
        put = await staff_client.put(
            f"/api/v1/staff/catalog-items/{item.id}/acquisition-rationale",
            json=_UPDATE_PAYLOAD,
        )

    assert put.status_code == 200, put.text
    assert emit.await_count == 1
    kwargs = emit.await_args.kwargs
    assert kwargs["rationale"].primary_use_case_slug == "bedtime"


@pytest.mark.asyncio
async def test_emit_failure_does_not_break_save(
    staff_client: AsyncClient, test_db,
):
    """KB emit raising must NOT roll back the save or surface to the user."""
    item = await _seed_item_and_tags(test_db)

    with patch(EMIT_PATH, new_callable=AsyncMock) as emit:
        emit.side_effect = RuntimeError("librarian-kb is on fire")
        resp = await staff_client.post(
            f"/api/v1/staff/catalog-items/{item.id}/acquisition-rationale",
            json=_CREATE_PAYLOAD,
        )

    # Save still succeeds
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["primary_use_case_slug"] == "commute"
    # Emit was attempted exactly once
    assert emit.await_count == 1

    # Persistence proof: GET returns the row
    get = await staff_client.get(
        f"/api/v1/staff/catalog-items/{item.id}/acquisition-rationale",
    )
    assert get.status_code == 200, get.text


@pytest.mark.asyncio
async def test_emit_not_attempted_when_base_url_unset(
    staff_client: AsyncClient, test_db, monkeypatch,
):
    """When LIBRARIAN_AGENT_BASE_URL is empty, no HTTP call is attempted.

    We assert at the httpx layer (no AsyncClient ever constructed), because
    the *method* emit_rationale_aku is still called — it just short-circuits
    inside on the empty-base-url guard.
    """
    item = await _seed_item_and_tags(test_db)

    # Ensure settings present an empty base_url for this test regardless of
    # ambient env state.
    from app.core import config as config_module

    config_module.get_settings.cache_clear()
    monkeypatch.setenv("LIBRARIAN_AGENT_BASE_URL", "")
    monkeypatch.setenv("LIBRARIAN_AGENT_API_KEY", "")

    httpx_path = "app.services.librarian_agent_client.httpx.AsyncClient"
    with patch(httpx_path) as async_client_cls:
        resp = await staff_client.post(
            f"/api/v1/staff/catalog-items/{item.id}/acquisition-rationale",
            json=_CREATE_PAYLOAD,
        )

    assert resp.status_code == 201, resp.text
    # No httpx call ever attempted
    assert async_client_cls.call_count == 0

    # Cleanup cached settings so other tests aren't poisoned
    config_module.get_settings.cache_clear()
