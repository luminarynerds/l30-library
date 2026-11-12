# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import contextlib
import json
from app.core.logging import get_logger
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime

from typing import Optional
from collections import defaultdict, deque

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


# Queue configuration constants
MAX_QUEUE_SIZE_PER_CLIENT = 100  # Maximum messages to queue per client
MESSAGE_TTL_SECONDS = 300  # 5 minutes TTL for queued messages
SESSION_TTL_SECONDS = 600  # 10 minutes before session is considered stale
CLEANUP_INTERVAL_SECONDS = 60  # Run cleanup every minute


@dataclass
class QueuedMessage:
    message: dict
    timestamp: float
    channels: list[str]

    def is_expired(self, ttl_seconds: float = MESSAGE_TTL_SECONDS) -> bool:
        return (time.time() - self.timestamp) > ttl_seconds


@dataclass
class ClientSession:
    session_id: str
    subscriptions: set[str] = field(default_factory=set)
    message_queue: deque = field(default_factory=lambda: deque(maxlen=MAX_QUEUE_SIZE_PER_CLIENT))
    created_at: float = field(default_factory=time.time)
    last_connected_at: float = field(default_factory=time.time)
    last_disconnected_at: Optional[float] = None
    is_connected: bool = False
    websocket: Optional[WebSocket] = None

    def queue_message(self, message: dict, channels: list[str]) -> bool:
        # Check if this message is relevant to this session's subscriptions
        relevant_channels = set(channels) & self.subscriptions
        if not relevant_channels and "all" not in self.subscriptions:
            return False

        queued = QueuedMessage(
            message=message,
            timestamp=time.time(),
            channels=channels
        )

        # deque with maxlen automatically drops oldest when full
        # Check if we're at capacity to log graceful degradation
        was_full = len(self.message_queue) >= MAX_QUEUE_SIZE_PER_CLIENT
        self.message_queue.append(queued)

        if was_full:
            logger.warning(
                f"Session {self.session_id}: Queue full, oldest message dropped "
                f"(graceful degradation)"
            )

        return True

    def get_pending_messages(self) -> list[dict]:
        messages = []
        expired_count = 0

        while self.message_queue:
            queued = self.message_queue.popleft()
            if not queued.is_expired():
                messages.append(queued.message)
            else:
                expired_count += 1

        if expired_count > 0:
            logger.debug(
                f"Session {self.session_id}: Dropped {expired_count} expired messages"
            )

        return messages

    def is_stale(self, stale_seconds: float = SESSION_TTL_SECONDS) -> bool:
        if self.is_connected:
            return False

        if self.last_disconnected_at is None:
            return False

        return (time.time() - self.last_disconnected_at) > stale_seconds


class RFIDScanEvent(BaseModel):
    event_type: str = "scan"
    session_id: int
    tag_id: str
    item_barcode: Optional[str] = None
    item_title: Optional[str] = None
    is_registered: bool = False
    is_misplaced: bool = False
    expected_location: Optional[str] = None
    found_at_location: Optional[str] = None
    signal_strength: Optional[float] = None
    timestamp: str


class SecurityAlertEvent(BaseModel):
    event_type: str = "security_alert"
    alert_id: int
    reader_id: int
    reader_name: Optional[str] = None
    reader_location: Optional[str] = None
    alert_type: str
    tag_id: Optional[str] = None
    item_barcode: Optional[str] = None
    item_title: Optional[str] = None
    timestamp: str


class SessionStatusEvent(BaseModel):
    event_type: str = "session_status"
    session_id: int
    status: str  # started, ended, updated
    tags_scanned: int = 0
    tags_processed: int = 0
    tags_failed: int = 0
    timestamp: str


class ReaderStatusEvent(BaseModel):
    event_type: str = "reader_status"
    reader_id: int
    reader_name: str
    status: str  # online, offline, error
    last_error: Optional[str] = None
    timestamp: str


class BatchProgressEvent(BaseModel):
    event_type: str = "batch_progress"
    session_id: int
    operation: str  # checkout, checkin
    total_items: int
    processed: int
    successful: int
    failed: int
    current_item: Optional[dict] = None
    timestamp: str


class RFIDWebSocketManager:

    def __init__(self):
        # Map of subscription_key -> set of websockets
        self._subscriptions: dict[str, set[WebSocket]] = defaultdict(set)
        # Map of websocket -> set of subscriptions
        self._websocket_subscriptions: dict[WebSocket, set[str]] = defaultdict(set)
        # Map of session_id -> ClientSession for reconnection support
        self._sessions: dict[str, ClientSession] = {}
        # Map of websocket -> session_id for reverse lookup
        self._websocket_sessions: dict[WebSocket, str] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        # Cleanup task reference
        self._cleanup_task: Optional[asyncio.Task] = None
        # Flag to control cleanup loop
        self._running = False

    def generate_session_id(self) -> str:
        return secrets.token_urlsafe(32)

    async def start_cleanup_task(self):
        if self._cleanup_task is None or self._cleanup_task.done():
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Started WebSocket session cleanup task")

    async def stop_cleanup_task(self):
        self._running = False
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            logger.info("Stopped WebSocket session cleanup task")

    async def _cleanup_loop(self):
        while self._running:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                await self._cleanup_stale_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:  # noqa: BLE001 - per-iteration boundary — must not crash cleanup loop
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_stale_sessions(self):
        async with self._lock:
            stale_sessions = [
                session_id
                for session_id, session in self._sessions.items()
                if session.is_stale()
            ]

            for session_id in stale_sessions:
                session = self._sessions.pop(session_id)
                queue_size = len(session.message_queue)
                logger.info(
                    f"Cleaned up stale session {session_id} "
                    f"(had {queue_size} queued messages)"
                )

            if stale_sessions:
                logger.info(f"Cleaned up {len(stale_sessions)} stale sessions")

            # Also clean up expired messages in active disconnected sessions
            for session in self._sessions.values():
                if not session.is_connected and session.message_queue:
                    original_size = len(session.message_queue)
                    # Filter out expired messages
                    valid_messages = deque(maxlen=MAX_QUEUE_SIZE_PER_CLIENT)
                    for msg in session.message_queue:
                        if not msg.is_expired():
                            valid_messages.append(msg)
                    session.message_queue = valid_messages
                    removed = original_size - len(valid_messages)
                    if removed > 0:
                        logger.debug(
                            f"Session {session.session_id}: Removed {removed} "
                            f"expired messages during cleanup"
                        )

    async def connect(
        self,
        websocket: WebSocket,
        subscriptions: list[str] | None = None,
        session_id: str | None = None
    ) -> str:
        await websocket.accept()

        async with self._lock:
            # Default to "all" if no subscriptions specified
            if not subscriptions:
                subscriptions = ["all"]

            is_reconnection = False
            queued_messages = []

            # Check if this is a reconnection with a valid session
            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                is_reconnection = True

                # Get queued messages before updating state
                queued_messages = session.get_pending_messages()

                # Update session state
                session.websocket = websocket
                session.is_connected = True
                session.last_connected_at = time.time()

                # Merge new subscriptions with existing ones
                for sub in subscriptions:
                    session.subscriptions.add(sub)

                logger.info(
                    f"Client reconnected with session {session_id}, "
                    f"delivering {len(queued_messages)} queued messages"
                )
            else:
                # New connection - create new session
                session_id = self.generate_session_id()
                session = ClientSession(
                    session_id=session_id,
                    subscriptions=set(subscriptions),
                    is_connected=True,
                    websocket=websocket
                )
                self._sessions[session_id] = session
                logger.info(f"New WebSocket session created: {session_id[:16]}...")

            # Update subscription mappings
            for sub in session.subscriptions:
                self._subscriptions[sub].add(websocket)
                self._websocket_subscriptions[websocket].add(sub)

            self._websocket_sessions[websocket] = session_id

        # Send session info to client (outside of lock)
        await websocket.send_json({
            "event_type": "session_init",
            "session_id": session_id,
            "subscriptions": list(session.subscriptions),
            "is_reconnection": is_reconnection,
            "queued_message_count": len(queued_messages),
            "timestamp": utc_now_iso()
        })

        # Deliver queued messages (outside of lock)
        for message in queued_messages:
            try:
                await websocket.send_json(message)
            except Exception as e:  # noqa: BLE001 - protocol boundary — websocket send failure must not crash reconnection delivery
                logger.warning(f"Failed to deliver queued message: {e}")
                break

        if queued_messages:
            # Send delivery confirmation
            await websocket.send_json({
                "event_type": "queue_delivered",
                "messages_delivered": len(queued_messages),
                "timestamp": utc_now_iso()
            })

        return session_id

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            session_id = self._websocket_sessions.get(websocket)

            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                session.websocket = None
                session.is_connected = False
                session.last_disconnected_at = time.time()
                logger.info(
                    f"WebSocket disconnected, session {session_id[:16]}... "
                    f"preserved for reconnection"
                )
            else:
                logger.info("WebSocket disconnected (no session)")

            # Clean up subscription mappings for this websocket
            subs = self._websocket_subscriptions.get(websocket, set())
            for sub in subs:
                self._subscriptions[sub].discard(websocket)
                # Clean up empty subscription sets
                if not self._subscriptions[sub]:
                    del self._subscriptions[sub]

            if websocket in self._websocket_subscriptions:
                del self._websocket_subscriptions[websocket]

            if websocket in self._websocket_sessions:
                del self._websocket_sessions[websocket]

    async def terminate_session(self, session_id: str):
        async with self._lock:
            if session_id in self._sessions:
                session = self._sessions.pop(session_id)
                if session.websocket:
                    # Also clean up websocket mappings
                    if session.websocket in self._websocket_sessions:
                        del self._websocket_sessions[session.websocket]
                    if session.websocket in self._websocket_subscriptions:
                        del self._websocket_subscriptions[session.websocket]
                logger.info(f"Session {session_id[:16]}... terminated")

    async def subscribe(self, websocket: WebSocket, channel: str):
        async with self._lock:
            self._subscriptions[channel].add(websocket)
            self._websocket_subscriptions[websocket].add(channel)

            # Also update session subscriptions
            session_id = self._websocket_sessions.get(websocket)
            if session_id and session_id in self._sessions:
                self._sessions[session_id].subscriptions.add(channel)

        logger.debug(f"WebSocket subscribed to: {channel}")

    async def unsubscribe(self, websocket: WebSocket, channel: str):
        async with self._lock:
            self._subscriptions[channel].discard(websocket)
            self._websocket_subscriptions[websocket].discard(channel)
            if not self._subscriptions[channel]:
                del self._subscriptions[channel]

            # Also update session subscriptions
            session_id = self._websocket_sessions.get(websocket)
            if session_id and session_id in self._sessions:
                self._sessions[session_id].subscriptions.discard(channel)

        logger.debug(f"WebSocket unsubscribed from: {channel}")

    async def _broadcast_to_channels(self, channels: list[str], message: dict):
        websockets_to_notify = set()
        sessions_to_queue: list[ClientSession] = []

        async with self._lock:
            # Collect connected websockets
            for channel in channels:
                websockets_to_notify.update(self._subscriptions.get(channel, set()))

            # Collect disconnected sessions that should receive this message
            for session in self._sessions.values():
                if not session.is_connected:
                    # Check if session is subscribed to any of the channels
                    if session.subscriptions & set(channels) or "all" in session.subscriptions:
                        sessions_to_queue.append(session)

        # Send to all connected websockets
        disconnected = []
        for websocket in websockets_to_notify:
            try:
                await websocket.send_json(message)
            except Exception as e:  # noqa: BLE001 - per-iteration boundary — single websocket failure must not drop other broadcast targets
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(websocket)

        # Clean up disconnected websockets
        for ws in disconnected:
            await self.disconnect(ws)

        # Queue message for disconnected sessions
        async with self._lock:
            queued_count = 0
            for session in sessions_to_queue:
                if session.queue_message(message, channels):
                    queued_count += 1

            if queued_count > 0:
                logger.debug(
                    f"Queued message for {queued_count} disconnected session(s)"
                )

    async def broadcast_scan(self, event: RFIDScanEvent):
        channels = [
            f"session:{event.session_id}",
            "all",
        ]
        await self._broadcast_to_channels(channels, event.model_dump())

    async def broadcast_security_alert(self, event: SecurityAlertEvent):
        channels = [
            f"reader:{event.reader_id}",
            "security",
            "all",
        ]
        await self._broadcast_to_channels(channels, event.model_dump())

    async def broadcast_session_status(self, event: SessionStatusEvent):
        channels = [
            f"session:{event.session_id}",
            "all",
        ]
        await self._broadcast_to_channels(channels, event.model_dump())

    async def broadcast_reader_status(self, event: ReaderStatusEvent):
        channels = [
            f"reader:{event.reader_id}",
            "all",
        ]
        await self._broadcast_to_channels(channels, event.model_dump())

    async def broadcast_batch_progress(self, event: BatchProgressEvent):
        channels = [
            f"session:{event.session_id}",
            "all",
        ]
        await self._broadcast_to_channels(channels, event.model_dump())

    @property
    def active_connections(self) -> int:
        return len(self._websocket_subscriptions)

    @property
    def total_sessions(self) -> int:
        return len(self._sessions)

    @property
    def disconnected_sessions(self) -> int:
        return sum(1 for s in self._sessions.values() if not s.is_connected)

    @property
    def total_queued_messages(self) -> int:
        return sum(len(s.message_queue) for s in self._sessions.values())

    def get_subscription_stats(self) -> dict:
        session_stats = []
        for session_id, session in self._sessions.items():
            session_stats.append({
                "session_id": session_id[:16] + "...",  # Truncate for display
                "is_connected": session.is_connected,
                "subscriptions": list(session.subscriptions),
                "queued_messages": len(session.message_queue),
                "created_at": session.created_at,
                "last_connected_at": session.last_connected_at,
                "last_disconnected_at": session.last_disconnected_at,
            })

        return {
            "total_connections": self.active_connections,
            "total_sessions": self.total_sessions,
            "disconnected_sessions": self.disconnected_sessions,
            "total_queued_messages": self.total_queued_messages,
            "subscriptions": {
                channel: len(sockets)
                for channel, sockets in self._subscriptions.items()
            },
            "sessions": session_stats,
            "queue_config": {
                "max_queue_size_per_client": MAX_QUEUE_SIZE_PER_CLIENT,
                "message_ttl_seconds": MESSAGE_TTL_SECONDS,
                "session_ttl_seconds": SESSION_TTL_SECONDS,
                "cleanup_interval_seconds": CLEANUP_INTERVAL_SECONDS,
            }
        }

    def get_session_info(self, session_id: str) -> dict | None:
        session = self._sessions.get(session_id)
        if not session:
            return None

        return {
            "session_id": session_id,
            "is_connected": session.is_connected,
            "subscriptions": list(session.subscriptions),
            "queued_messages": len(session.message_queue),
            "created_at": session.created_at,
            "last_connected_at": session.last_connected_at,
            "last_disconnected_at": session.last_disconnected_at,
            "is_stale": session.is_stale(),
        }


# Global WebSocket manager instance
rfid_ws_manager = RFIDWebSocketManager()


def utc_now_iso() -> str:
    return utc_now().isoformat()


# Helper functions for creating events

def create_scan_event(
    session_id: int,
    tag_id: str,
    item_barcode: str | None = None,
    item_title: str | None = None,
    is_registered: bool = False,
    is_misplaced: bool = False,
    expected_location: str | None = None,
    found_at_location: str | None = None,
    signal_strength: float | None = None,
) -> RFIDScanEvent:
    return RFIDScanEvent(
        session_id=session_id,
        tag_id=tag_id,
        item_barcode=item_barcode,
        item_title=item_title,
        is_registered=is_registered,
        is_misplaced=is_misplaced,
        expected_location=expected_location,
        found_at_location=found_at_location,
        signal_strength=signal_strength,
        timestamp=utc_now_iso(),
    )


def create_security_alert_event(
    alert_id: int,
    reader_id: int,
    alert_type: str,
    reader_name: str | None = None,
    reader_location: str | None = None,
    tag_id: str | None = None,
    item_barcode: str | None = None,
    item_title: str | None = None,
) -> SecurityAlertEvent:
    return SecurityAlertEvent(
        alert_id=alert_id,
        reader_id=reader_id,
        reader_name=reader_name,
        reader_location=reader_location,
        alert_type=alert_type,
        tag_id=tag_id,
        item_barcode=item_barcode,
        item_title=item_title,
        timestamp=utc_now_iso(),
    )


def create_session_status_event(
    session_id: int,
    status: str,
    tags_scanned: int = 0,
    tags_processed: int = 0,
    tags_failed: int = 0,
) -> SessionStatusEvent:
    return SessionStatusEvent(
        session_id=session_id,
        status=status,
        tags_scanned=tags_scanned,
        tags_processed=tags_processed,
        tags_failed=tags_failed,
        timestamp=utc_now_iso(),
    )


def create_reader_status_event(
    reader_id: int,
    reader_name: str,
    status: str,
    last_error: str | None = None,
) -> ReaderStatusEvent:
    return ReaderStatusEvent(
        reader_id=reader_id,
        reader_name=reader_name,
        status=status,
        last_error=last_error,
        timestamp=utc_now_iso(),
    )


def create_batch_progress_event(
    session_id: int,
    operation: str,
    total_items: int,
    processed: int,
    successful: int,
    failed: int,
    current_item: dict | None = None,
) -> BatchProgressEvent:
    return BatchProgressEvent(
        session_id=session_id,
        operation=operation,
        total_items=total_items,
        processed=processed,
        successful=successful,
        failed=failed,
        current_item=current_item,
        timestamp=utc_now_iso(),
    )
