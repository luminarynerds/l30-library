# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from app.core.logging import get_logger
from typing import Optional

import httpx

logger = get_logger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "L30-Library/1.0"

_last_request_time: float = 0.0
_lock = asyncio.Lock()


async def geocode_address(address: str) -> Optional[tuple[float, float]]:
    global _last_request_time

    async with _lock:
        now = asyncio.get_event_loop().time()
        wait = max(0, 1.0 - (now - _last_request_time))
        if wait > 0:
            await asyncio.sleep(wait)
        _last_request_time = asyncio.get_event_loop().time()

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                NOMINATIM_URL,
                params={"q": address, "format": "json", "limit": 1},
                headers={"User-Agent": USER_AGENT},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            if data:
                return (float(data[0]["lat"]), float(data[0]["lon"]))
    except (httpx.HTTPError, asyncio.TimeoutError, ValueError, KeyError, IndexError):
        logger.warning("Geocoding failed for address: %s", address, exc_info=True)

    return None
