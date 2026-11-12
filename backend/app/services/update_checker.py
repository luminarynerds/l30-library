# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import httpx
from packaging.version import Version, InvalidVersion
from app.core.config import get_settings

GITHUB_RELEASES_URL = "https://api.github.com/repos/luminarynerds/l30/releases/latest"

# Module-level cache -- refreshed by scheduler
_cached_update: dict | None = None


async def check_for_updates() -> dict | None:
    settings = get_settings()
    if not settings.update_check:
        return None

    current = settings.l30_version
    if current == "0.0.0-dev":
        return None

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                GITHUB_RELEASES_URL,
                headers={"Accept": "application/vnd.github+json"},
                timeout=10.0,
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            latest_tag = data.get("tag_name", "").lstrip("v")
            if not latest_tag:
                return None

            if Version(latest_tag) > Version(current):
                return {
                    "current_version": current,
                    "latest_version": latest_tag,
                    "release_name": data.get("name", ""),
                    "changelog": (data.get("body", "") or "")[:500],
                    "release_url": data.get("html_url", ""),
                    "update_commands": "docker compose pull && docker compose up -d",
                }
    except (httpx.HTTPError, InvalidVersion, ValueError, KeyError):
        return None  # Never crash on update check failure

    return None


async def run_scheduled_check():
    global _cached_update
    _cached_update = await check_for_updates()


def get_cached_update_info() -> dict | None:
    return _cached_update
