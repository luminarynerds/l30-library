# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import asyncio
import contextlib
import json
from app.core.logging import get_logger
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import WebSocket

logger = get_logger(__name__)

SENSITIVE_WS_QUERY_PARAMS = {"token", "access_token", "auth", "authorization", "jwt"}

# --- Configuration ---
MAX_QUEUE_SIZE = 100
MESSAGE_TTL_SECONDS = 300  # 5 min
SESSION_TTL_SECONDS = 600  # 10 min
CLEANUP_INTERVAL_SECONDS = 60
VALID_CHANNELS = {"holds", "checkouts", "fines", "programs", "catalog", "all"}


@dataclass
class PatronConnection:

    user_id: int
    websocket: Optional[WebSocket] = None
    channels: set[str] = field(default_factory=lambda: {"all"})
    message_queue: deque = field(
        default_factory=lambda: deque(maxlen=MAX_QUEUE_SIZE)
    )
    connected_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    disconnected_at: Optional[float] = None
    is_connected: bool = False

    def queue_message(self, message: dict, channel: str) -> bool:
        if channel not in self.channels and "all" not in self.channels:
            return False
        entry = {"message": message, "queued_at": time.time(), "channel": channel}
        was_full = len(self.message_queue) >= MAX_QUEUE_SIZE
        self.message_queue.append(entry)
        if was_full:
            logger.warning(
                f"Patron {self.user_id}: queue full, oldest message dropped"
            )
        return True

    def drain_queue(self) -> list[dict]:
        now = time.time()
        messages = []
        while self.message_queue:
            entry = self.message_queue.popleft()
            if now - entry["queued_at"] < MESSAGE_TTL_SECONDS:
                messages.append(entry["message"])
        return messages

    def is_stale(self) -> bool:
        if self.is_connected:
            return False
        if self.disconnected_at is None:
            return False
        return (time.time() - self.disconnected_at) > SESSION_TTL_SECONDS


class PatronWebSocketManager:

    def __init__(self) -> None:
        # user_id → list of PatronConnection (one user can have multiple tabs)
        self._connections: dict[int, list[PatronConnection]] = defaultdict(list)
        # websocket → PatronConnection (reverse lookup)
        self._ws_map: dict[WebSocket, PatronConnection] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        # Metrics
        self._total_messages_sent = 0
        self._total_connections_accepted = 0

    # --- Lifecycle ---

    async def start(self) -> None:
        if self._cleanup_task is None or self._cleanup_task.done():
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("PatronWebSocketManager cleanup task started")

    async def stop(self) -> None:
        self._running = False
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            logger.info("PatronWebSocketManager cleanup task stopped")

    async def _cleanup_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                await self._cleanup_stale()
            except asyncio.CancelledError:
                break
            except Exception as e:  # noqa: BLE001  # long-running task boundary — loop must survive transient errors
                logger.error("Cleanup loop error: %s", e)

    async def _cleanup_stale(self) -> None:
        async with self._lock:
            removed = 0
            for user_id in list(self._connections.keys()):
                conns = self._connections[user_id]
                active = [c for c in conns if not c.is_stale()]
                stale_count = len(conns) - len(active)
                if stale_count:
                    removed += stale_count
                    self._connections[user_id] = active
                if not active:
                    del self._connections[user_id]
            if removed:
                logger.info("Cleaned up %s stale patron connection(s)", removed)

    # --- Connection management ---

    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        channels: set[str] | None = None,
    ) -> PatronConnection:
        await websocket.accept()

        effective_channels = (channels or {"all"}) & VALID_CHANNELS
        if not effective_channels:
            effective_channels = {"all"}

        conn = PatronConnection(
            user_id=user_id,
            websocket=websocket,
            channels=effective_channels,
            is_connected=True,
        )

        async with self._lock:
            self._connections[user_id].append(conn)
            self._ws_map[websocket] = conn
            self._total_connections_accepted += 1

        # Deliver any queued messages from a previous connection
        queued = conn.drain_queue()

        await websocket.send_json(
            {
                "event_type": "connection_init",
                "channels": sorted(effective_channels),
                "queued_count": len(queued),
                "timestamp": _utc_now_iso(),
            }
        )

        for msg in queued:
            try:
                await websocket.send_json(msg)
            except Exception:  # noqa: BLE001  # WebSocket send boundary — any send failure aborts drain, peer is gone
                break

        logger.info(
            f"Patron {user_id} connected to channels {effective_channels} "
            f"(total connections for user: {len(self._connections[user_id])})"
        )
        return conn

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            conn = self._ws_map.pop(websocket, None)
            if conn:
                conn.websocket = None
                conn.is_connected = False
                conn.disconnected_at = time.time()
                logger.info(
                    f"Patron {conn.user_id} disconnected, session preserved"
                )

    async def subscribe(self, websocket: WebSocket, channel: str) -> bool:
        if channel not in VALID_CHANNELS:
            return False
        async with self._lock:
            conn = self._ws_map.get(websocket)
            if conn:
                conn.channels.add(channel)
                return True
        return False

    async def unsubscribe(self, websocket: WebSocket, channel: str) -> bool:
        async with self._lock:
            conn = self._ws_map.get(websocket)
            if conn:
                conn.channels.discard(channel)
                return True
        return False

    # --- Message dispatch ---

    async def notify_user(
        self,
        user_id: int,
        channel: str,
        event_type: str,
        data: dict[str, Any],
    ) -> int:
        message = {
            "channel": channel,
            "event_type": event_type,
            "data": data,
            "timestamp": _utc_now_iso(),
        }

        delivered = 0
        failed_ws: list[WebSocket] = []

        async with self._lock:
            connections = self._connections.get(user_id, [])

        for conn in connections:
            if channel not in conn.channels and "all" not in conn.channels:
                continue

            if conn.is_connected and conn.websocket:
                try:
                    await conn.websocket.send_json(message)
                    self._total_messages_sent += 1
                    delivered += 1
                except Exception:  # noqa: BLE001  # WebSocket send boundary — disconnect on any send failure
                    failed_ws.append(conn.websocket)
            else:
                conn.queue_message(message, channel)
                delivered += 1

        for ws in failed_ws:
            await self.disconnect(ws)

        return delivered

    async def broadcast(
        self,
        channel: str,
        event_type: str,
        data: dict[str, Any],
    ) -> int:
        message = {
            "channel": channel,
            "event_type": event_type,
            "data": data,
            "timestamp": _utc_now_iso(),
        }

        failed_ws: list[WebSocket] = []

        async with self._lock:
            all_connections = [
                conn
                for conns in self._connections.values()
                for conn in conns
            ]

        # Separate connected (need async send) from disconnected (queue locally)
        to_send: list[PatronConnection] = []
        queued = 0
        for conn in all_connections:
            if channel not in conn.channels and "all" not in conn.channels:
                continue
            if conn.is_connected and conn.websocket:
                to_send.append(conn)
            else:
                conn.queue_message(message, channel)
                queued += 1

        # Send to all connected clients concurrently
        async def _send(conn: PatronConnection) -> bool:
            try:
                await conn.websocket.send_json(message)
                return True
            except Exception:  # noqa: BLE001  # WebSocket send boundary — disconnect on any send failure
                failed_ws.append(conn.websocket)
                return False

        results = await asyncio.gather(
            *[_send(conn) for conn in to_send],
            return_exceptions=True,
        )
        sent = sum(1 for r in results if r is True)
        self._total_messages_sent += sent

        for ws in failed_ws:
            await self.disconnect(ws)

        return sent + queued

    # --- Stats ---

    @property
    def active_connections(self) -> int:
        return len(self._ws_map)

    @property
    def unique_users(self) -> int:
        return len(self._connections)

    def get_stats(self) -> dict[str, Any]:
        per_channel: dict[str, int] = defaultdict(int)
        disconnected_count = 0
        total_queued = 0

        for conns in self._connections.values():
            for conn in conns:
                if not conn.is_connected:
                    disconnected_count += 1
                total_queued += len(conn.message_queue)
                for ch in conn.channels:
                    per_channel[ch] += 1

        return {
            "active_connections": self.active_connections,
            "unique_users": self.unique_users,
            "disconnected_sessions": disconnected_count,
            "total_queued_messages": total_queued,
            "total_messages_sent": self._total_messages_sent,
            "total_connections_accepted": self._total_connections_accepted,
            "channel_subscriptions": dict(per_channel),
        }


# --- Global instance ---
patron_ws_manager = PatronWebSocketManager()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact_websocket_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
        if not parsed.query:
            return url

        redacted_pairs = []
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            if key.lower() in SENSITIVE_WS_QUERY_PARAMS and value:
                redacted_pairs.append((key, "[REDACTED]"))
            else:
                redacted_pairs.append((key, value))

        redacted_query = urlencode(redacted_pairs, doseq=True)
        return urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, redacted_query, parsed.fragment)
        )
    except Exception:  # noqa: BLE001  # logging boundary — URL sanitization must never raise
        # Never fail logging due to URL sanitization issues.
        return url
