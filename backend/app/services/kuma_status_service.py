# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Live system status fed by the Uptime Kuma monitor.

Reads Kuma's public status-page API and maps the raw monitors onto the
patron-facing services shown on /status. This is what makes the page honest:
the indicators come from real automated checks (every 60s), not hand-entered
incidents. Staff-logged incidents are layered on top by the caller.

If Kuma is unreachable the caller falls back to the incident board, so a
monitoring outage never takes the status page down.
"""
import time
from typing import Any, Optional

import httpx

from ..core.config import get_settings
from ..core.logging import get_logger

logger = get_logger(__name__)

# Patron-facing service -> the Kuma monitor(s) that prove it is working.
# Keyed by monitor NAME (stable; set when the monitors were created) so the
# mapping survives monitor-id changes.
SERVICE_MAP: list[dict[str, Any]] = [
    {
        "id": "library_site",
        "name": "Library site",
        "description": "Catalog, account, events, and the main website",
        "monitors": ["L30 Library"],
    },
    {
        "id": "digital",
        "name": "Digital collection",
        "description": "eBooks and audiobooks",
        "monitors": ["MetisLib"],
    },
    {
        "id": "infrastructure",
        "name": "Servers & network",
        "description": "The servers and network behind everything above",
        "monitors": ["VPS host (stacks)"],
    },
]

# Kuma heartbeat status codes -> our vocabulary.
_KUMA_STATUS = {0: "outage", 1: "operational", 2: "degraded", 3: "maintenance"}

_CACHE_TTL_SECONDS = 20.0
_cache: dict[str, Any] = {"at": 0.0, "data": None}


def _unavailable() -> dict[str, Any]:
    return {
        "source": "kuma",
        "available": False,
        "overall_status": "unknown",
        "services": [],
        "checked_at": None,
    }


async def _fetch_kuma() -> tuple[dict, dict]:
    settings = get_settings()
    base = settings.kuma_base_url.rstrip("/")
    slug = settings.kuma_status_slug
    async with httpx.AsyncClient(timeout=5.0) as client:
        config_resp = await client.get(f"{base}/api/status-page/{slug}")
        config_resp.raise_for_status()
        heartbeat_resp = await client.get(f"{base}/api/status-page/heartbeat/{slug}")
        heartbeat_resp.raise_for_status()
    return config_resp.json(), heartbeat_resp.json()


def _worst(statuses: list[str]) -> str:
    for level in ("outage", "maintenance", "degraded"):
        if level in statuses:
            return level
    if "operational" in statuses:
        return "operational"
    return "unknown"


def _build(config: dict, heartbeat: dict) -> dict[str, Any]:
    name_to_id: dict[str, str] = {}
    for group in config.get("publicGroupList", []):
        for monitor in group.get("monitorList", []):
            name_to_id[monitor.get("name")] = str(monitor.get("id"))

    heartbeat_list = heartbeat.get("heartbeatList", {})
    uptime_list = heartbeat.get("uptimeList", {})

    services = []
    checked_at: Optional[str] = None

    for spec in SERVICE_MAP:
        statuses: list[int] = []
        pings: list[float] = []
        uptimes: list[float] = []
        last_time: Optional[str] = None

        for monitor_name in spec["monitors"]:
            monitor_id = name_to_id.get(monitor_name)
            if not monitor_id:
                continue
            beats = heartbeat_list.get(monitor_id) or []
            if beats:
                last = beats[-1]
                statuses.append(last.get("status"))
                if last.get("ping") is not None:
                    pings.append(last["ping"])
                last_time = last.get("time")
            uptime = uptime_list.get(f"{monitor_id}_24")
            if uptime is not None:
                uptimes.append(uptime)

        service_status = _worst([_KUMA_STATUS.get(s, "unknown") for s in statuses])
        services.append({
            "id": spec["id"],
            "name": spec["name"],
            "description": spec["description"],
            "status": service_status,
            "uptime_24h": round(min(uptimes) * 100, 3) if uptimes else None,
            "ping_ms": round(max(pings)) if pings else None,
            "last_checked": last_time,
        })
        if last_time and (checked_at is None or last_time > checked_at):
            checked_at = last_time

    return {
        "source": "kuma",
        "available": True,
        "overall_status": _worst([s["status"] for s in services]),
        "services": services,
        "checked_at": checked_at,
    }


async def get_live_status() -> dict[str, Any]:
    """Return the live status snapshot, cached briefly to spare the monitor."""
    now = time.monotonic()
    if _cache["data"] is not None and now - _cache["at"] < _CACHE_TTL_SECONDS:
        return _cache["data"]

    try:
        config, heartbeat = await _fetch_kuma()
    except Exception as exc:  # noqa: BLE001 - any failure means "fall back to incidents"
        logger.warning("Live status fetch from uptime monitor failed: %s", exc)
        return _unavailable()

    result = _build(config, heartbeat)
    _cache["data"] = result
    _cache["at"] = now
    return result
