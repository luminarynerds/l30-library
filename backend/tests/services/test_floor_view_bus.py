# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for floor_view_bus subscriber connection handling.

Two historical failure modes are pinned here:

1. Connection leak: the loop reconnects on error, and each retry once created
   a fresh ``pubsub`` without closing the previous one, leaking a pooled
   connection per cycle until ``redis.asyncio``'s default ``max_connections=100``
   pool was exhausted and the loop wedged on ``ConnectionError``. Every pubsub
   the loop opens must be released (``__aexit__``) on the way out.

2. Idle-timeout churn: redis-py 8 defaults ``socket_timeout=5``, which made a
   blocking idle ``listen()`` raise every ~5s. The loop treated that as a real
   failure, tore down the subscription, and silently dropped events published
   during each reconnect gap, while ``backoff = 1.0`` reset on every reconnect
   so it churned forever. The loop must poll with ``get_message`` and treat
   read timeouts/empty polls as normal idle, and backoff must escalate across
   consecutive failed connections.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import redis.asyncio as aioredis

from app.services import floor_view_bus


class _FakePubSub:
    """Async-context-manager pubsub driven by a scripted sequence of
    ``get_message`` results. An exhausted script simulates a dropped
    connection. Records whether it was closed via ``__aexit__``."""

    def __init__(self, script: list | None = None) -> None:
        self.subscribe = AsyncMock()
        self.closed = False
        self.script = list(script or [])

    async def __aenter__(self) -> "_FakePubSub":
        return self

    async def __aexit__(self, *exc_info) -> bool:
        self.closed = True
        return False

    async def get_message(self, ignore_subscribe_messages=False, timeout=None):
        if not self.script:
            raise RuntimeError("simulated connection drop")
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def _client_with(pubsub_factory) -> MagicMock:
    fake_client = MagicMock()
    fake_client.pubsub = MagicMock(side_effect=pubsub_factory)
    return fake_client


@pytest.mark.asyncio
async def test_subscriber_releases_pubsub_on_every_retry(monkeypatch):
    """Each retry must close its pubsub (return the connection to the pool)."""
    created: list[_FakePubSub] = []

    def _pubsub_factory():
        ps = _FakePubSub()
        created.append(ps)
        return ps

    monkeypatch.setattr(
        floor_view_bus, "_get_redis", AsyncMock(return_value=_client_with(_pubsub_factory))
    )

    # Break out of the infinite loop after 3 retry cycles by cancelling from
    # within the backoff sleep.
    sleeps = {"n": 0}

    async def _fake_sleep(_seconds):
        sleeps["n"] += 1
        if sleeps["n"] >= 3:
            raise asyncio.CancelledError
    monkeypatch.setattr(floor_view_bus.asyncio, "sleep", _fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await floor_view_bus._subscriber_loop()

    # Three cycles ran; every pubsub opened was closed -> no connection leak.
    assert len(created) == 3
    assert all(ps.closed for ps in created), "a pubsub was not released on retry (connection leak)"
    assert all(ps.subscribe.await_count == 1 for ps in created)


@pytest.mark.asyncio
async def test_subscriber_broadcasts_message_then_releases(monkeypatch):
    """A delivered message is broadcast locally, and the pubsub is still closed."""
    delivered: list[str] = []
    monkeypatch.setattr(
        floor_view_bus, "_broadcast_local",
        AsyncMock(side_effect=lambda data: delivered.append(data)),
    )

    ps = _FakePubSub(script=[{"type": "message", "data": "{\"type\":\"ping\"}"}])
    monkeypatch.setattr(
        floor_view_bus, "_get_redis", AsyncMock(return_value=_client_with(lambda: ps))
    )

    async def _cancel_sleep(_seconds):
        raise asyncio.CancelledError
    monkeypatch.setattr(floor_view_bus.asyncio, "sleep", _cancel_sleep)

    with pytest.raises(asyncio.CancelledError):
        await floor_view_bus._subscriber_loop()

    assert delivered == ["{\"type\":\"ping\"}"]
    assert ps.closed, "pubsub was not released after message delivery"


@pytest.mark.asyncio
async def test_idle_timeout_and_empty_polls_do_not_resubscribe(monkeypatch):
    """A redis read timeout or empty poll while idle must keep the
    subscription intact — no teardown, no resubscribe, no dropped events."""
    delivered: list[str] = []
    monkeypatch.setattr(
        floor_view_bus, "_broadcast_local",
        AsyncMock(side_effect=lambda data: delivered.append(data)),
    )

    ps = _FakePubSub(script=[
        aioredis.TimeoutError("Timeout reading from socket"),
        None,
        {"type": "message", "data": "{\"type\":\"ping\"}"},
        asyncio.CancelledError(),
    ])
    monkeypatch.setattr(
        floor_view_bus, "_get_redis", AsyncMock(return_value=_client_with(lambda: ps))
    )

    async def _cancel_sleep(_seconds):
        raise asyncio.CancelledError
    monkeypatch.setattr(floor_view_bus.asyncio, "sleep", _cancel_sleep)

    with pytest.raises(asyncio.CancelledError):
        await floor_view_bus._subscriber_loop()

    assert ps.subscribe.await_count == 1, "idle timeout tore down the subscription"
    assert delivered == ["{\"type\":\"ping\"}"], "event after an idle timeout was lost"


@pytest.mark.asyncio
async def test_backoff_escalates_for_real_failures(monkeypatch):
    """Consecutive failed connections must escalate backoff, not stay at 1.0s
    (the old loop reset backoff on every reconnect, churning every ~6s)."""
    monkeypatch.setattr(
        floor_view_bus, "_get_redis", AsyncMock(return_value=_client_with(_FakePubSub))
    )

    sleeps: list[float] = []

    async def _fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) >= 3:
            raise asyncio.CancelledError
    monkeypatch.setattr(floor_view_bus.asyncio, "sleep", _fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await floor_view_bus._subscriber_loop()

    assert sleeps == [1.0, 2.0, 4.0]
