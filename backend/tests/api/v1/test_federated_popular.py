# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""GET /federated-search/popular -- regression for the partner-search 404.

The federated search box fetches popular search suggestions on mount; the
endpoint was never implemented backend-side, so it 404'd on every page load.
"""
import os

# Config validation requires this before app import; conftest sets the rest of
# the test env but not this one. setdefault = no DB-URL pollution of other tests.
os.environ.setdefault("PII_ENCRYPTION_ENABLED", "false")

import pytest


@pytest.mark.asyncio
async def test_popular_endpoint_exists_and_returns_searches_list(client):
    resp = await client.get("/api/v1/federated-search/popular?limit=5")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body.get("searches"), list)


@pytest.mark.asyncio
async def test_popular_returns_linked_subject_labels(client, db_session, test_catalog_item):
    from app.models.subject import CatalogItemSubject, Subject

    mystery = Subject(label="Mystery", slug="mystery")
    cooking = Subject(label="Cooking", slug="cooking")
    db_session.add_all([mystery, cooking])
    await db_session.flush()
    db_session.add_all([
        CatalogItemSubject(catalog_item_id=test_catalog_item.id, subject_id=mystery.id, position=0),
        CatalogItemSubject(catalog_item_id=test_catalog_item.id, subject_id=cooking.id, position=1),
    ])
    await db_session.commit()

    resp = await client.get("/api/v1/federated-search/popular?limit=5")
    assert resp.status_code == 200
    searches = resp.json()["searches"]
    assert "Mystery" in searches
    assert "Cooking" in searches
