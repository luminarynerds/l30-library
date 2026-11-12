# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for GET /staff/acquisition-rationale/similar.

The endpoint is a thin proxy over LibrarianAgentClient.search_similar_rationales,
which is itself best-effort and never raises. These tests assert the route
wiring (auth gate, query forwarding, response shape) by mocking the client
method at the route module path.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


# Patched at the import site (routes import LibrarianAgentClient from
# app.services.librarian_agent_client into the route module).
SEARCH_PATH = (
    "app.api.v1.staff.acquisition_rationales."
    "LibrarianAgentClient.search_similar_rationales"
)


@pytest.mark.asyncio
async def test_similar_returns_hits_from_client(staff_client: AsyncClient):
    fake_hits = [
        {
            "aku_id": "rationale-1",
            "title": "Acquisition rationale: Cyber-thriller A",
            "body": "Bought because patrons keep asking for cyber-thrillers.",
            "tags": ["rationale", "commute"],
            "score": 0.92,
        },
        {
            "aku_id": "rationale-2",
            "title": "Acquisition rationale: Cyber-thriller B",
            "body": "Gap in collection identified.",
            "tags": ["rationale", "commute"],
            "score": 0.81,
        },
    ]
    with patch(SEARCH_PATH, new_callable=AsyncMock) as search:
        search.return_value = fake_hits
        resp = await staff_client.get(
            "/api/v1/staff/acquisition-rationale/similar",
            params={"query": "cyber thriller", "limit": 5},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["query"] == "cyber thriller"
    assert body["hits"] == fake_hits
    assert search.await_count == 1
    kwargs = search.await_args.kwargs
    assert kwargs["query"] == "cyber thriller"
    assert kwargs["limit"] == 5


@pytest.mark.asyncio
async def test_similar_returns_empty_hits_when_client_empty(staff_client: AsyncClient):
    """When librarian-agent is unreachable or has no matches, route returns
    an empty hits list (the client returns [] in those cases)."""
    with patch(SEARCH_PATH, new_callable=AsyncMock) as search:
        search.return_value = []
        resp = await staff_client.get(
            "/api/v1/staff/acquisition-rationale/similar",
            params={"query": "no matches"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["hits"] == []
    assert body["query"] == "no matches"


@pytest.mark.asyncio
async def test_similar_requires_auth(client: AsyncClient):
    """Unauthenticated requests get 401 (no auth override on this fixture)."""
    resp = await client.get(
        "/api/v1/staff/acquisition-rationale/similar",
        params={"query": "anything"},
    )
    assert resp.status_code == 401, resp.text
