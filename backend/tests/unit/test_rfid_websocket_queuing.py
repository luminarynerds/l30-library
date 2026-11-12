# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for RFID WebSocket message queuing and reconnection support.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.rfid_websocket import (
    ClientSession,
    QueuedMessage,
    RFIDWebSocketManager,
    MAX_QUEUE_SIZE_PER_CLIENT,
    MESSAGE_TTL_SECONDS,
    SESSION_TTL_SECONDS,
)


class TestQueuedMessage:
    """Tests for QueuedMessage dataclass."""

    def test_create_queued_message(self):
        """Test creating a queued message."""
        message = {"event_type": "scan", "tag_id": "ABC123"}
        channels = ["session:1", "all"]

        queued = QueuedMessage(
            message=message,
            timestamp=time.time(),
            channels=channels
        )

        assert queued.message == message
        assert queued.channels == channels

    def test_message_not_expired_immediately(self):
        """Test that a new message is not expired."""
        queued = QueuedMessage(
            message={"test": "data"},
            timestamp=time.time(),
            channels=["all"]
        )
        assert not queued.is_expired()

    def test_message_expired_after_ttl(self):
        """Test that a message expires after TTL."""
        old_timestamp = time.time() - MESSAGE_TTL_SECONDS - 1
        queued = QueuedMessage(
            message={"test": "data"},
            timestamp=old_timestamp,
            channels=["all"]
        )
        assert queued.is_expired()

    def test_message_custom_ttl(self):
        """Test message expiration with custom TTL."""
        timestamp = time.time() - 10  # 10 seconds ago
        queued = QueuedMessage(
            message={"test": "data"},
            timestamp=timestamp,
            channels=["all"]
        )
        assert not queued.is_expired(ttl_seconds=20)
        assert queued.is_expired(ttl_seconds=5)


class TestClientSession:
    """Tests for ClientSession dataclass."""

    def test_create_session(self):
        """Test creating a client session."""
        session = ClientSession(session_id="test-session-123")

        assert session.session_id == "test-session-123"
        assert session.subscriptions == set()
        assert len(session.message_queue) == 0
        assert session.is_connected is False
        assert session.websocket is None

    def test_session_with_subscriptions(self):
        """Test session with subscriptions."""
        session = ClientSession(
            session_id="test-session",
            subscriptions={"session:1", "security", "all"}
        )

        assert "session:1" in session.subscriptions
        assert "security" in session.subscriptions
        assert "all" in session.subscriptions

    def test_queue_message_relevant_channel(self):
        """Test queuing a message for relevant channel."""
        session = ClientSession(
            session_id="test-session",
            subscriptions={"session:1", "security"}
        )

        result = session.queue_message(
            {"event_type": "scan"},
            ["session:1"]
        )

        assert result is True
        assert len(session.message_queue) == 1

    def test_queue_message_all_subscription(self):
        """Test queuing a message when subscribed to 'all'."""
        session = ClientSession(
            session_id="test-session",
            subscriptions={"all"}
        )

        result = session.queue_message(
            {"event_type": "scan"},
            ["session:5"]  # Different session, but "all" should catch it
        )

        assert result is True
        assert len(session.message_queue) == 1

    def test_queue_message_irrelevant_channel(self):
        """Test that irrelevant messages are not queued."""
        session = ClientSession(
            session_id="test-session",
            subscriptions={"session:1"}
        )

        result = session.queue_message(
            {"event_type": "scan"},
            ["session:2"]  # Different session
        )

        assert result is False
        assert len(session.message_queue) == 0

    def test_queue_message_limit(self):
        """Test that queue respects size limit."""
        session = ClientSession(session_id="test-session", subscriptions={"all"})

        # Queue more than the limit
        for i in range(MAX_QUEUE_SIZE_PER_CLIENT + 10):
            session.queue_message({"index": i}, ["all"])

        assert len(session.message_queue) == MAX_QUEUE_SIZE_PER_CLIENT

    def test_queue_drops_oldest_when_full(self):
        """Test that oldest messages are dropped when queue is full."""
        session = ClientSession(session_id="test-session", subscriptions={"all"})

        # Fill the queue
        for i in range(MAX_QUEUE_SIZE_PER_CLIENT):
            session.queue_message({"index": i}, ["all"])

        # Add one more
        session.queue_message({"index": MAX_QUEUE_SIZE_PER_CLIENT}, ["all"])

        # Check that first message was dropped
        messages = session.get_pending_messages()
        assert messages[0]["index"] == 1  # Index 0 should be dropped

    def test_get_pending_messages_clears_queue(self):
        """Test that getting pending messages clears the queue."""
        session = ClientSession(session_id="test-session", subscriptions={"all"})

        session.queue_message({"msg": 1}, ["all"])
        session.queue_message({"msg": 2}, ["all"])

        messages = session.get_pending_messages()
        assert len(messages) == 2
        assert len(session.message_queue) == 0

    def test_get_pending_messages_filters_expired(self):
        """Test that expired messages are filtered out."""
        session = ClientSession(session_id="test-session", subscriptions={"all"})

        # Add an expired message directly
        expired_msg = QueuedMessage(
            message={"expired": True},
            timestamp=time.time() - MESSAGE_TTL_SECONDS - 10,
            channels=["all"]
        )
        session.message_queue.append(expired_msg)

        # Add a fresh message
        session.queue_message({"fresh": True}, ["all"])

        messages = session.get_pending_messages()
        assert len(messages) == 1
        assert messages[0]["fresh"] is True

    def test_session_is_stale_when_disconnected_long(self):
        """Test session is stale after being disconnected too long."""
        session = ClientSession(
            session_id="test-session",
            is_connected=False,
            last_disconnected_at=time.time() - SESSION_TTL_SECONDS - 10
        )

        assert session.is_stale() is True

    def test_session_not_stale_when_connected(self):
        """Test connected session is not stale."""
        session = ClientSession(
            session_id="test-session",
            is_connected=True,
            last_disconnected_at=time.time() - SESSION_TTL_SECONDS - 10
        )

        assert session.is_stale() is False

    def test_session_not_stale_when_recently_disconnected(self):
        """Test recently disconnected session is not stale."""
        session = ClientSession(
            session_id="test-session",
            is_connected=False,
            last_disconnected_at=time.time() - 60  # 1 minute ago
        )

        assert session.is_stale() is False


class TestRFIDWebSocketManager:
    """Tests for RFIDWebSocketManager."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return RFIDWebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock websocket."""
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        ws.accept = AsyncMock()
        return ws

    def test_generate_session_id(self, manager):
        """Test session ID generation."""
        session_id = manager.generate_session_id()
        assert len(session_id) > 20
        assert isinstance(session_id, str)

        # Ensure uniqueness
        session_id2 = manager.generate_session_id()
        assert session_id != session_id2

    @pytest.mark.asyncio
    async def test_connect_creates_session(self, manager, mock_websocket):
        """Test that connecting creates a new session."""
        session_id = await manager.connect(mock_websocket, ["all"])

        assert session_id is not None
        assert manager.total_sessions == 1
        assert manager.active_connections == 1

    @pytest.mark.asyncio
    async def test_connect_sends_session_init(self, manager, mock_websocket):
        """Test that connect sends session_init message."""
        session_id = await manager.connect(mock_websocket, ["all"])

        # Check that session_init was sent
        calls = mock_websocket.send_json.call_args_list
        assert len(calls) >= 1

        init_msg = calls[0][0][0]
        assert init_msg["event_type"] == "session_init"
        assert init_msg["session_id"] == session_id
        assert init_msg["is_reconnection"] is False

    @pytest.mark.asyncio
    async def test_reconnect_with_session_id(self, manager, mock_websocket):
        """Test reconnecting with existing session ID."""
        # First connection
        session_id = await manager.connect(mock_websocket, ["session:1"])
        await manager.disconnect(mock_websocket)

        # Queue a message while disconnected
        async with manager._lock:
            session = manager._sessions[session_id]
            session.queue_message({"test": "queued"}, ["session:1"])

        # Reconnect with same session ID
        mock_websocket2 = AsyncMock()
        mock_websocket2.send_json = AsyncMock()
        mock_websocket2.accept = AsyncMock()

        returned_session_id = await manager.connect(
            mock_websocket2, ["session:1"], session_id=session_id
        )

        assert returned_session_id == session_id
        # Check that session_init indicates reconnection
        calls = mock_websocket2.send_json.call_args_list
        init_msg = calls[0][0][0]
        assert init_msg["is_reconnection"] is True
        assert init_msg["queued_message_count"] == 1

    @pytest.mark.asyncio
    async def test_reconnect_delivers_queued_messages(self, manager, mock_websocket):
        """Test that queued messages are delivered on reconnect."""
        # First connection
        session_id = await manager.connect(mock_websocket, ["all"])
        await manager.disconnect(mock_websocket)

        # Queue messages while disconnected
        async with manager._lock:
            session = manager._sessions[session_id]
            session.queue_message({"msg": 1}, ["all"])
            session.queue_message({"msg": 2}, ["all"])

        # Reconnect
        mock_websocket2 = AsyncMock()
        mock_websocket2.send_json = AsyncMock()
        mock_websocket2.accept = AsyncMock()

        await manager.connect(mock_websocket2, ["all"], session_id=session_id)

        # Check messages were sent
        calls = mock_websocket2.send_json.call_args_list
        # session_init + 2 queued messages + queue_delivered
        assert len(calls) == 4

        # Verify queued messages
        msg1 = calls[1][0][0]
        msg2 = calls[2][0][0]
        assert msg1["msg"] == 1
        assert msg2["msg"] == 2

        # Verify queue_delivered confirmation
        delivered_msg = calls[3][0][0]
        assert delivered_msg["event_type"] == "queue_delivered"
        assert delivered_msg["messages_delivered"] == 2

    @pytest.mark.asyncio
    async def test_disconnect_preserves_session(self, manager, mock_websocket):
        """Test that disconnect preserves session for reconnection."""
        _ = await manager.connect(mock_websocket, ["all"])
        await manager.disconnect(mock_websocket)

        assert manager.total_sessions == 1
        assert manager.disconnected_sessions == 1
        assert manager.active_connections == 0

    @pytest.mark.asyncio
    async def test_terminate_session_removes_session(self, manager, mock_websocket):
        """Test that terminate_session removes session completely."""
        session_id = await manager.connect(mock_websocket, ["all"])
        await manager.terminate_session(session_id)

        assert manager.total_sessions == 0

    @pytest.mark.asyncio
    async def test_broadcast_queues_for_disconnected(self, manager, mock_websocket):
        """Test that broadcast queues messages for disconnected sessions."""
        # Connect and disconnect
        _ = await manager.connect(mock_websocket, ["security"])
        await manager.disconnect(mock_websocket)

        # Import event type
        from app.services.rfid_websocket import SecurityAlertEvent, utc_now_iso

        # Broadcast a security alert
        event = SecurityAlertEvent(
            alert_id=1,
            reader_id=1,
            alert_type="unauthorized_exit",
            timestamp=utc_now_iso()
        )
        await manager.broadcast_security_alert(event)

        # Check message was queued
        assert manager.total_queued_messages == 1

    @pytest.mark.asyncio
    async def test_subscribe_updates_session(self, manager, mock_websocket):
        """Test that subscribe updates session subscriptions."""
        session_id = await manager.connect(mock_websocket, ["all"])

        await manager.subscribe(mock_websocket, "session:5")

        session_info = manager.get_session_info(session_id)
        assert "session:5" in session_info["subscriptions"]

    @pytest.mark.asyncio
    async def test_unsubscribe_updates_session(self, manager, mock_websocket):
        """Test that unsubscribe updates session subscriptions."""
        session_id = await manager.connect(mock_websocket, ["all", "security"])

        await manager.unsubscribe(mock_websocket, "security")

        session_info = manager.get_session_info(session_id)
        assert "security" not in session_info["subscriptions"]

    @pytest.mark.asyncio
    async def test_cleanup_stale_sessions(self, manager, mock_websocket):
        """Test cleanup of stale sessions."""
        session_id = await manager.connect(mock_websocket, ["all"])
        await manager.disconnect(mock_websocket)

        # Make session stale
        async with manager._lock:
            session = manager._sessions[session_id]
            session.last_disconnected_at = time.time() - SESSION_TTL_SECONDS - 100

        # Run cleanup
        await manager._cleanup_stale_sessions()

        assert manager.total_sessions == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_messages(self, manager, mock_websocket):
        """Test cleanup of expired messages."""
        session_id = await manager.connect(mock_websocket, ["all"])
        await manager.disconnect(mock_websocket)

        # Add an expired message directly
        async with manager._lock:
            session = manager._sessions[session_id]
            expired_msg = QueuedMessage(
                message={"expired": True},
                timestamp=time.time() - MESSAGE_TTL_SECONDS - 100,
                channels=["all"]
            )
            session.message_queue.append(expired_msg)

        # Run cleanup
        await manager._cleanup_stale_sessions()

        assert manager.total_queued_messages == 0

    @pytest.mark.asyncio
    async def test_get_subscription_stats(self, manager, mock_websocket):
        """Test getting subscription statistics."""
        await manager.connect(mock_websocket, ["session:1", "security"])

        stats = manager.get_subscription_stats()

        assert stats["total_connections"] == 1
        assert stats["total_sessions"] == 1
        assert stats["disconnected_sessions"] == 0
        assert "queue_config" in stats
        assert stats["queue_config"]["max_queue_size_per_client"] == MAX_QUEUE_SIZE_PER_CLIENT

    @pytest.mark.asyncio
    async def test_get_session_info_not_found(self, manager):
        """Test getting info for non-existent session."""
        info = manager.get_session_info("non-existent-session")
        assert info is None

    @pytest.mark.asyncio
    async def test_start_stop_cleanup_task(self, manager):
        """Test starting and stopping cleanup task."""
        await manager.start_cleanup_task()
        assert manager._running is True
        assert manager._cleanup_task is not None

        await manager.stop_cleanup_task()
        assert manager._running is False

    @pytest.mark.asyncio
    async def test_connect_with_invalid_session_id_creates_new(self, manager, mock_websocket):
        """Test that connecting with invalid session ID creates new session."""
        session_id = await manager.connect(
            mock_websocket,
            ["all"],
            session_id="invalid-session-id-that-does-not-exist"
        )

        # Should create a new session, not use the invalid one
        assert session_id != "invalid-session-id-that-does-not-exist"
        assert manager.total_sessions == 1


class TestMessageQueueGracefulDegradation:
    """Tests for graceful degradation when queue is full."""

    @pytest.fixture
    def session_with_full_queue(self):
        """Create a session with a full message queue."""
        session = ClientSession(session_id="test", subscriptions={"all"})
        for i in range(MAX_QUEUE_SIZE_PER_CLIENT):
            session.queue_message({"index": i}, ["all"])
        return session

    def test_full_queue_drops_oldest(self, session_with_full_queue):
        """Test that full queue drops oldest message."""
        session = session_with_full_queue

        # Add one more message
        session.queue_message({"new": True}, ["all"])

        messages = session.get_pending_messages()
        assert len(messages) == MAX_QUEUE_SIZE_PER_CLIENT
        assert messages[-1]["new"] is True
        assert messages[0]["index"] == 1  # Original index 0 was dropped

    def test_queue_returns_true_even_when_dropping(self, session_with_full_queue):
        """Test that queue_message returns True even when dropping old messages."""
        session = session_with_full_queue

        result = session.queue_message({"new": True}, ["all"])
        assert result is True
