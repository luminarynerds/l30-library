# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import asyncio
import contextlib
import json
from app.core.logging import get_logger
from dataclasses import dataclass, field
from typing import Any, Optional

import redis.asyncio as aioredis
from fastapi import WebSocket

from ..core.config import get_settings

logger = get_logger(__name__)

FLOOR_EVENT_CHANNEL = "l30:floor:events"

# Poll interval for pubsub.get_message(); kept under redis-py 8's default
# socket_timeout=5 so an idle subscriber never trips the connection timeout.
_POLL_TIMEOUT_SECONDS = 1.0
# A connection that survived this long was healthy; reset backoff after it
# fails instead of treating it as part of a failure streak.
_STABLE_CONNECTION_SECONDS = 30.0


@dataclass
class _BusState:
    sockets: set[WebSocket] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    subscriber_task: Optional[asyncio.Task] = None
    redis_client: Optional[aioredis.Redis] = None


_state = _BusState()


async def _get_redis() -> aioredis.Redis:
    if _state.redis_client is None:
        settings = get_settings()
        _state.redis_client = aioredis.from_url(
            settings.redis_url, decode_responses=True,
        )
    return _state.redis_client


async def connect(websocket: WebSocket) -> None:
    async with _state.lock:
        _state.sockets.add(websocket)
    logger.info("floor_bus connect total=%d", len(_state.sockets))


async def disconnect(websocket: WebSocket) -> None:
    async with _state.lock:
        _state.sockets.discard(websocket)
    logger.info("floor_bus disconnect total=%d", len(_state.sockets))


async def publish(event_type: str, **payload: Any) -> None:
    try:
        message = json.dumps({"type": event_type, **payload})
        redis_client = await _get_redis()
        await redis_client.publish(FLOOR_EVENT_CHANNEL, message)
    except Exception as exc:  # noqa: BLE001 — never let pub/sub break the API
        logger.warning("floor_bus publish failed type=%s err=%s", event_type, exc)


async def _broadcast_local(message: str) -> None:
    async with _state.lock:
        targets = list(_state.sockets)
    if not targets:
        return
    dead: list[WebSocket] = []
    for ws in targets:
        try:
            await ws.send_text(message)
        except Exception:  # noqa: BLE001
            dead.append(ws)
    if dead:
        async with _state.lock:
            for ws in dead:
                _state.sockets.discard(ws)


async def _subscriber_loop() -> None:
    backoff = 1.0
    while True:
        connected_at: Optional[float] = None
        try:
            redis_client = await _get_redis()
            # ``async with`` guarantees the pubsub connection is returned to
            # the pool on every exit (including errors). Without it, each retry
            # leaked a connection and eventually exhausted the client pool
            # (redis.asyncio default max_connections=100), wedging the loop.
            async with redis_client.pubsub() as pubsub:
                await pubsub.subscribe(FLOOR_EVENT_CHANNEL)
                logger.info("floor_bus subscriber connected channel=%s", FLOOR_EVENT_CHANNEL)
                connected_at = asyncio.get_running_loop().time()
                while True:
                    # Poll with get_message instead of blocking on listen():
                    # redis-py 8 defaults socket_timeout=5, which made an idle
                    # blocking read raise every ~5s, tearing the subscription
                    # down and dropping events published in the reconnect gap.
                    try:
                        message = await pubsub.get_message(
                            ignore_subscribe_messages=True,
                            timeout=_POLL_TIMEOUT_SECONDS,
                        )
                    except (aioredis.TimeoutError, TimeoutError):
                        # Idle read timeout: the subscription is still intact.
                        continue
                    if message is None:
                        continue
                    if message.get("type") != "message":
                        continue
                    data = message.get("data")
                    if not isinstance(data, str):
                        continue
                    await _broadcast_local(data)
        except asyncio.CancelledError:
            logger.info("floor_bus subscriber cancelled")
            raise
        except Exception as exc:  # noqa: BLE001
            if connected_at is not None and (
                asyncio.get_running_loop().time() - connected_at >= _STABLE_CONNECTION_SECONDS
            ):
                backoff = 1.0
            logger.warning(
                "floor_bus subscriber error err=%s backoff=%.1fs; "
                "floor events published before resubscribe are lost",
                exc,
                backoff,
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)


def start_subscriber() -> None:
    if _state.subscriber_task is None or _state.subscriber_task.done():
        loop = asyncio.get_event_loop()
        _state.subscriber_task = loop.create_task(_subscriber_loop())
        logger.info("floor_bus subscriber task started")


async def stop_subscriber() -> None:
    if _state.subscriber_task and not _state.subscriber_task.done():
        _state.subscriber_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):  # noqa: BLE001 - shutdown cleanup: subscriber task ending is the goal
            await _state.subscriber_task
    if _state.redis_client is not None:
        with contextlib.suppress(Exception):  # noqa: BLE001 - shutdown cleanup: best-effort redis close
            await _state.redis_client.close()
