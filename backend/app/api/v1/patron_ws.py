# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Patron WebSocket endpoint for real-time notifications.

Authenticates via JWT token passed as a query parameter during the
WebSocket handshake (browsers cannot set Authorization headers on WS).

Endpoint: /api/v1/ws/patron?token=<jwt>&channels=holds,checkouts

Supports the same action-based protocol as the RFID WebSocket:
  - subscribe / unsubscribe (channel management)
  - ping / pong (keepalive)
"""

from app.core.logging import get_logger
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.security import verify_token
from app.core.websocket import (
    VALID_CHANNELS,
    patron_ws_manager,
    redact_websocket_url,
)

logger = get_logger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/patron")
async def patron_websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token for authentication"),
    channels: str = Query(
        "all",
        description="Comma-separated channels: holds,checkouts,fines,programs,catalog,all",
    ),
):
    # --- Authenticate via JWT ---
    try:
        payload = verify_token(token, check_revocation=True)
        user_id_str = payload.get("sub")
        if not user_id_str:
            await websocket.close(code=4001, reason="Invalid token: missing subject")
            return
        user_id = int(user_id_str)
    except Exception as e:  # noqa: BLE001  # WebSocket auth — close on any token decode failure
        logger.warning(
            "WebSocket auth failed for %s (%s)",
            redact_websocket_url(str(websocket.url)),
            type(e).__name__,
        )
        # Must accept before close in some ASGI servers
        await websocket.accept()
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # --- Parse channels ---
    requested_channels = {
        ch.strip() for ch in channels.split(",") if ch.strip()
    }
    valid = requested_channels & VALID_CHANNELS
    if not valid:
        valid = {"all"}

    # --- Connect ---
    await patron_ws_manager.connect(websocket, user_id, valid)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                import json as _json
                msg = _json.loads(raw)
            except (ValueError, TypeError):
                await websocket.send_json(
                    {"event_type": "error", "message": "Invalid JSON"}
                )
                continue

            action = msg.get("action", "")

            if action == "ping":
                await websocket.send_json(
                    {
                        "event_type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

            elif action == "subscribe":
                channel = msg.get("channel", "")
                ok = await patron_ws_manager.subscribe(websocket, channel)
                await websocket.send_json(
                    {
                        "event_type": "subscribed" if ok else "error",
                        "channel": channel,
                        "message": None if ok else f"Invalid channel: {channel}",
                    }
                )

            elif action == "unsubscribe":
                channel = msg.get("channel", "")
                await patron_ws_manager.unsubscribe(websocket, channel)
                await websocket.send_json(
                    {"event_type": "unsubscribed", "channel": channel}
                )

            else:
                await websocket.send_json(
                    {
                        "event_type": "error",
                        "message": f"Unknown action: {action}",
                    }
                )

    except WebSocketDisconnect:
        logger.debug(f"Patron {user_id} WebSocket disconnected normally")
    except Exception as e:
        logger.error(f"Patron {user_id} WebSocket error: {e}", exc_info=True)
    finally:
        await patron_ws_manager.disconnect(websocket)


# --- Staff health endpoint ---

@router.get(
    "/ws/patron/health",
    tags=["websocket", "staff"],
    summary="WebSocket connection health stats",
)
async def websocket_health():
    """
    Returns WebSocket connection statistics for the staff system status dashboard.

    No authentication required - data is aggregate only, no PII.
    """
    return patron_ws_manager.get_stats()
