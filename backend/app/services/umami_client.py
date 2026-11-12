# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

import httpx

from ..core.config import get_settings

logger = get_logger(__name__)

_token_cache: dict = {"token": None, "expires": 0}


class UmamiUnavailable(Exception):
    pass


async def get_umami_token() -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc).timestamp()
    if _token_cache["token"] and _token_cache["expires"] > now:
        return _token_cache["token"]

    if not settings.umami_url or not settings.umami_username or not settings.umami_password:
        raise UmamiUnavailable("Umami credentials not configured")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.umami_url}/api/auth/login",
                json={
                    "username": settings.umami_username,
                    "password": settings.umami_password,
                },
            )
    except httpx.HTTPError as exc:
        raise UmamiUnavailable(f"Umami login transport error: {exc}") from exc

    if resp.status_code != 200:
        raise UmamiUnavailable(f"Umami login returned {resp.status_code}")

    data = resp.json()
    _token_cache["token"] = data["token"]
    _token_cache["expires"] = now + 3600
    return data["token"]


async def umami_get(path: str, params: Optional[dict] = None) -> dict:
    settings = get_settings()
    token = await get_umami_token()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{settings.umami_url}/api{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError as exc:
        raise UmamiUnavailable(f"Umami request transport error: {exc}") from exc

    if resp.status_code != 200:
        raise UmamiUnavailable(
            f"Umami GET {path} returned {resp.status_code}"
        )

    return resp.json()
