# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for LibrarianAgentClient — best-effort HTTP client."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.librarian_agent_client import LibrarianAgentClient


# ---------------- helpers ----------------


def _make_settings(
    base_url: str = "http://librarian-kb.test",
    slug: str = "l30",
    api_key: str = "test-key",
):
    return SimpleNamespace(
        librarian_agent_base_url=base_url,
        librarian_agent_library_slug=slug,
        librarian_agent_api_key=api_key,
    )


def _make_catalog_item(item_id: int = 42, title: str = "Pattern Recognition"):
    return SimpleNamespace(id=item_id, title=title)


def _make_rationale(
    rid: int = 7,
    catalog_item_id: int = 42,
    public_summary: str | None = "Bought because patrons keep asking for cyber-thrillers.",
    primary_use_case_slug: str = "commute",
    signal_type: str = "purchase_request",
    signal_note: str = "Three reference-desk asks this month",
    policy_clause: str = "CDP §3.2 adult fiction",
    anticipated_challenge_reasons: list[str] | None = None,
    secondary_use_case_slugs: list[str] | None = None,
):
    r = SimpleNamespace(
        id=rid,
        catalog_item_id=catalog_item_id,
        public_summary=public_summary,
        primary_use_case_slug=primary_use_case_slug,
        signal_type=signal_type,
        signal_note=signal_note,
        policy_clause=policy_clause,
        anticipated_challenge_reasons=anticipated_challenge_reasons or [],
        secondary_use_case_slugs=secondary_use_case_slugs or ["bedtime"],
    )
    return r


def _make_response(status_code: int = 200, json_payload: dict | None = None,
                   text: str = ""):
    """Build a mock httpx.Response shape that the client expects."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value=json_payload or {})
    resp.text = text or (str(json_payload) if json_payload else "")
    return resp


def _patch_async_client(post_mock):
    """Context manager that patches httpx.AsyncClient used by the module."""
    instance = MagicMock()
    instance.post = post_mock
    instance.__aenter__ = AsyncMock(return_value=instance)
    instance.__aexit__ = AsyncMock(return_value=None)
    return patch(
        "app.services.librarian_agent_client.httpx.AsyncClient",
        return_value=instance,
    )


# ---------------- emit_rationale_aku ----------------


@pytest.mark.asyncio
async def test_emit_happy_path_posts_correct_url_headers_payload():
    settings = _make_settings(base_url="http://kb.local", api_key="secret-123")
    client = LibrarianAgentClient(settings)
    item = _make_catalog_item(title="Pattern Recognition")
    rat = _make_rationale()

    post_mock = AsyncMock(return_value=_make_response(
        200, {"aku_id": "aku-abc", "status": "created"},
    ))
    with _patch_async_client(post_mock):
        aku_id = await client.emit_rationale_aku(
            catalog_item=item, rationale=rat,
        )

    assert aku_id == "aku-abc"
    assert post_mock.await_count == 1
    args, kwargs = post_mock.await_args
    # URL is the first positional arg
    assert args[0] == "http://kb.local/v1/akus/emit"
    # API key header present
    assert kwargs["headers"]["X-API-Key"] == "secret-123"
    assert kwargs["headers"]["Content-Type"] == "application/json"
    # Payload shape
    body = kwargs["json"]
    assert body["slug"] == "l30"
    assert body["kind"] == "acquisition_rationale"
    assert body["external_id"] == "rationale-7"
    assert body["title"] == "Acquisition rationale: Pattern Recognition"
    assert body["body"].startswith("Bought because patrons")
    assert body["metadata"]["catalog_item_id"] == 42
    assert body["metadata"]["rationale_id"] == 7
    assert body["metadata"]["primary_use_case"] == "commute"
    assert body["metadata"]["signal_type"] == "purchase_request"
    assert body["metadata"]["signal_note"] == "Three reference-desk asks this month"
    assert body["metadata"]["behavior_tags"] == ["bedtime"]
    assert body["tags"] == ["rationale", "commute"]


@pytest.mark.asyncio
async def test_emit_returns_none_on_connection_error():
    settings = _make_settings()
    client = LibrarianAgentClient(settings)
    item = _make_catalog_item()
    rat = _make_rationale()

    post_mock = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
    with _patch_async_client(post_mock):
        result = await client.emit_rationale_aku(
            catalog_item=item, rationale=rat,
        )

    assert result is None


@pytest.mark.asyncio
async def test_emit_returns_none_on_non_2xx_status():
    settings = _make_settings()
    client = LibrarianAgentClient(settings)
    item = _make_catalog_item()
    rat = _make_rationale()

    post_mock = AsyncMock(return_value=_make_response(
        500, json_payload=None, text="internal server error",
    ))
    with _patch_async_client(post_mock):
        result = await client.emit_rationale_aku(
            catalog_item=item, rationale=rat,
        )

    assert result is None


@pytest.mark.asyncio
async def test_emit_returns_none_when_base_url_empty():
    """Not configured = silent skip, no network attempt."""
    settings = _make_settings(base_url="")
    client = LibrarianAgentClient(settings)
    item = _make_catalog_item()
    rat = _make_rationale()

    post_mock = AsyncMock(return_value=_make_response(200, {"aku_id": "x"}))
    with _patch_async_client(post_mock) as patched:
        result = await client.emit_rationale_aku(
            catalog_item=item, rationale=rat,
        )

    assert result is None
    # httpx.AsyncClient must not even be constructed when unconfigured
    assert patched.call_count == 0
    assert post_mock.await_count == 0


@pytest.mark.asyncio
async def test_emit_skips_api_key_header_when_key_empty():
    settings = _make_settings(api_key="")
    client = LibrarianAgentClient(settings)
    item = _make_catalog_item()
    rat = _make_rationale()

    post_mock = AsyncMock(return_value=_make_response(
        200, {"aku_id": "aku-1"},
    ))
    with _patch_async_client(post_mock):
        await client.emit_rationale_aku(catalog_item=item, rationale=rat)

    _, kwargs = post_mock.await_args
    assert "X-API-Key" not in kwargs["headers"]
    # Other standard headers still present
    assert kwargs["headers"]["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_emit_narrative_fallback_when_public_summary_empty():
    """When public_summary is empty/None, body is composed from
    primary_use_case_slug + signal_type + signal_note + policy_clause."""
    settings = _make_settings()
    client = LibrarianAgentClient(settings)
    item = _make_catalog_item()
    rat = _make_rationale(
        public_summary=None,
        primary_use_case_slug="bedtime",
        signal_type="staff_observation",
        signal_note="Parents requesting calming reads",
        policy_clause="CDP §4.1",
    )

    post_mock = AsyncMock(return_value=_make_response(
        200, {"aku_id": "aku-fb"},
    ))
    with _patch_async_client(post_mock):
        await client.emit_rationale_aku(catalog_item=item, rationale=rat)

    body = post_mock.await_args.kwargs["json"]["body"]
    assert "bedtime" in body
    assert "staff_observation" in body
    assert "Parents requesting calming reads" in body
    assert "CDP §4.1" in body


# ---------------- search_similar_rationales ----------------


@pytest.mark.asyncio
async def test_search_happy_path_returns_hits():
    settings = _make_settings(base_url="http://kb.local")
    client = LibrarianAgentClient(settings)

    hits = [
        {"aku_id": "aku-a", "score": 0.91, "title": "..."},
        {"aku_id": "aku-b", "score": 0.74, "title": "..."},
    ]
    post_mock = AsyncMock(return_value=_make_response(200, {"hits": hits}))
    with _patch_async_client(post_mock):
        result = await client.search_similar_rationales(
            query="comfort reads for new parents", limit=2,
        )

    assert result == hits
    args, kwargs = post_mock.await_args
    assert args[0] == "http://kb.local/v1/search"
    body = kwargs["json"]
    assert body["query"] == "comfort reads for new parents"
    assert body["slugs"] == ["l30"]
    assert body["kind"] == "acquisition_rationale"
    assert body["limit"] == 2


@pytest.mark.asyncio
async def test_search_returns_empty_list_on_failure():
    settings = _make_settings()
    client = LibrarianAgentClient(settings)

    # connection error
    post_mock = AsyncMock(side_effect=httpx.ConnectError("nope"))
    with _patch_async_client(post_mock):
        assert await client.search_similar_rationales(query="x") == []

    # non-2xx
    post_mock = AsyncMock(return_value=_make_response(503, text="unavailable"))
    with _patch_async_client(post_mock):
        assert await client.search_similar_rationales(query="x") == []

    # base_url empty -> short-circuit, no call
    unconfigured = LibrarianAgentClient(_make_settings(base_url=""))
    post_mock = AsyncMock()
    with _patch_async_client(post_mock):
        assert await unconfigured.search_similar_rationales(query="x") == []
    assert post_mock.await_count == 0
