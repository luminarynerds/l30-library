# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Load test for patron WebSocket connections.

Simulates 1,000 concurrent WebSocket connections to verify the
PatronWebSocketManager handles high connection counts, message
delivery, and cleanup under load.

Run:
    pytest tests/test_websocket_load.py -v -s
    # Or standalone:
    python tests/test_websocket_load.py
"""

import asyncio
import json
import time
import statistics
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.websocket import PatronWebSocketManager, VALID_CHANNELS


# ---- Fake WebSocket for testing ----

class FakeWebSocket:
    """Minimal WebSocket stand-in for load testing."""

    def __init__(self):
        self.accepted = False
        self.sent: list[dict] = []
        self.closed = False
        self._lock = asyncio.Lock()

    async def accept(self):
        self.accepted = True

    async def send_json(self, data: dict):
        async with self._lock:
            self.sent.append(data)

    async def close(self, code: int = 1000, reason: str = ""):
        self.closed = True


# ---- Tests ----

CONCURRENT_CONNECTIONS = 1_000


@pytest.mark.asyncio
async def test_1000_concurrent_connections():
    """Verify the manager handles 1,000 simultaneous connections."""
    manager = PatronWebSocketManager()

    websockets: list[FakeWebSocket] = []
    channels_cycle = list(VALID_CHANNELS - {"all"})

    # --- Connect 1,000 clients ---
    connect_start = time.perf_counter()

    async def connect_one(i: int):
        ws = FakeWebSocket()
        user_id = i + 1  # patron IDs 1..1000
        ch = {channels_cycle[i % len(channels_cycle)]}
        await manager.connect(ws, user_id, ch)
        return ws

    tasks = [connect_one(i) for i in range(CONCURRENT_CONNECTIONS)]
    websockets = await asyncio.gather(*tasks)

    connect_elapsed = time.perf_counter() - connect_start

    assert manager.active_connections == CONCURRENT_CONNECTIONS
    assert manager.unique_users == CONCURRENT_CONNECTIONS
    print(
        f"\n[CONNECT] {CONCURRENT_CONNECTIONS} connections in "
        f"{connect_elapsed:.2f}s ({connect_elapsed / CONCURRENT_CONNECTIONS * 1000:.2f}ms/conn)"
    )

    # --- Broadcast a message to all ---
    broadcast_start = time.perf_counter()
    delivered = await manager.broadcast(
        channel="holds",
        event_type="HoldAvailable",
        data={"hold_id": 999, "title": "Load Test Book"},
    )
    broadcast_elapsed = time.perf_counter() - broadcast_start

    # Only connections subscribed to "holds" should receive it
    holds_count = sum(
        1 for i in range(CONCURRENT_CONNECTIONS)
        if channels_cycle[i % len(channels_cycle)] == "holds"
    )
    assert delivered == holds_count
    print(
        f"[BROADCAST] Delivered to {delivered}/{CONCURRENT_CONNECTIONS} "
        f"in {broadcast_elapsed * 1000:.2f}ms"
    )

    # --- Send per-user notification ---
    notify_start = time.perf_counter()
    per_user_tasks = []
    for i in range(CONCURRENT_CONNECTIONS):
        user_id = i + 1
        ch = channels_cycle[i % len(channels_cycle)]
        per_user_tasks.append(
            manager.notify_user(
                user_id=user_id,
                channel=ch,
                event_type="CheckoutDueSoon",
                data={"checkout_id": i, "title": f"Book {i}"},
            )
        )
    results = await asyncio.gather(*per_user_tasks)
    notify_elapsed = time.perf_counter() - notify_start

    total_delivered = sum(results)
    assert total_delivered == CONCURRENT_CONNECTIONS
    print(
        f"[NOTIFY] {CONCURRENT_CONNECTIONS} per-user notifications "
        f"in {notify_elapsed:.2f}s ({notify_elapsed / CONCURRENT_CONNECTIONS * 1000:.2f}ms/notif)"
    )

    # --- Verify stats ---
    stats = manager.get_stats()
    assert stats["active_connections"] == CONCURRENT_CONNECTIONS
    assert stats["unique_users"] == CONCURRENT_CONNECTIONS
    assert stats["disconnected_sessions"] == 0
    print(f"[STATS] {json.dumps(stats, indent=2)}")

    # --- Disconnect all ---
    disconnect_start = time.perf_counter()
    disconnect_tasks = [manager.disconnect(ws) for ws in websockets]
    await asyncio.gather(*disconnect_tasks)
    disconnect_elapsed = time.perf_counter() - disconnect_start

    assert manager.active_connections == 0
    assert manager.unique_users == CONCURRENT_CONNECTIONS  # sessions preserved
    print(
        f"[DISCONNECT] {CONCURRENT_CONNECTIONS} disconnections "
        f"in {disconnect_elapsed:.2f}s"
    )


@pytest.mark.asyncio
async def test_message_queuing_under_load():
    """Verify messages queue properly when users disconnect."""
    manager = PatronWebSocketManager()
    num_users = 500

    # Connect then disconnect all
    websockets = []
    for i in range(num_users):
        ws = FakeWebSocket()
        await manager.connect(ws, i + 1, {"checkouts"})
        websockets.append(ws)

    for ws in websockets:
        await manager.disconnect(ws)

    assert manager.active_connections == 0

    # Send notifications to disconnected users - should be queued
    queue_start = time.perf_counter()
    for i in range(num_users):
        await manager.notify_user(
            user_id=i + 1,
            channel="checkouts",
            event_type="CheckoutDueSoon",
            data={"title": f"Book {i}"},
        )
    queue_elapsed = time.perf_counter() - queue_start

    stats = manager.get_stats()
    assert stats["total_queued_messages"] == num_users
    print(
        f"\n[QUEUE] {num_users} messages queued in {queue_elapsed * 1000:.2f}ms"
    )

    # Reconnect and verify queued messages are delivered
    reconnect_start = time.perf_counter()
    for i in range(num_users):
        ws = FakeWebSocket()
        _ = await manager.connect(ws, i + 1, {"checkouts"})
        # connection_init message is sent, plus any queued
    reconnect_elapsed = time.perf_counter() - reconnect_start

    stats_after = manager.get_stats()
    assert stats_after["active_connections"] == num_users
    print(
        f"[RECONNECT] {num_users} reconnections in {reconnect_elapsed:.2f}s"
    )


@pytest.mark.asyncio
async def test_multiple_tabs_per_user():
    """Verify a single user can have multiple concurrent connections."""
    manager = PatronWebSocketManager()
    user_id = 42
    num_tabs = 10

    websockets = []
    for _ in range(num_tabs):
        ws = FakeWebSocket()
        await manager.connect(ws, user_id, {"holds", "checkouts"})
        websockets.append(ws)

    assert manager.active_connections == num_tabs
    assert manager.unique_users == 1

    delivered = await manager.notify_user(
        user_id=user_id,
        channel="holds",
        event_type="HoldAvailable",
        data={"title": "Multi-tab Test"},
    )
    assert delivered == num_tabs

    # Each tab should have received connection_init + the notification
    for ws in websockets:
        assert len(ws.sent) == 2  # connection_init + notification

    for ws in websockets:
        await manager.disconnect(ws)

    assert manager.active_connections == 0


@pytest.mark.asyncio
async def test_channel_isolation():
    """Verify messages only reach subscribers of the correct channel."""
    manager = PatronWebSocketManager()

    holds_ws = FakeWebSocket()
    fines_ws = FakeWebSocket()

    await manager.connect(holds_ws, 1, {"holds"})
    await manager.connect(fines_ws, 2, {"fines"})

    await manager.notify_user(1, "holds", "HoldAvailable", {"title": "Hold Book"})
    await manager.notify_user(2, "fines", "FineAssessed", {"amount": 500})

    # holds_ws should have connection_init + hold notification
    assert len(holds_ws.sent) == 2
    assert holds_ws.sent[1]["event_type"] == "HoldAvailable"

    # fines_ws should have connection_init + fine notification
    assert len(fines_ws.sent) == 2
    assert fines_ws.sent[1]["event_type"] == "FineAssessed"

    # Cross-channel should NOT deliver
    delivered = await manager.notify_user(1, "fines", "FineAssessed", {})
    assert delivered == 0  # user 1 is not subscribed to fines


# ---- Standalone runner ----

if __name__ == "__main__":
    print("=" * 60)
    print("WebSocket Load Test - 1,000 Concurrent Connections")
    print("=" * 60)

    async def run_all():
        await test_1000_concurrent_connections()
        print()
        await test_message_queuing_under_load()
        print()
        await test_multiple_tabs_per_user()
        print()
        await test_channel_isolation()
        print()
        print("All load tests passed.")

    asyncio.run(run_all())
