# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger

import httpx

from .config import get_settings

logger = get_logger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile(token: str | None, remote_ip: str | None) -> bool:
    settings = get_settings()
    secret = settings.turnstile_secret_key

    if getattr(settings, "turnstile_disabled", False):
        logger.warning(
            "TURNSTILE_DISABLED is set -- bypassing bot verification (self-host "
            "escape hatch). Unset this once a real CF_TURNSTILE_SECRET is configured."
        )
        return True

    if not secret:
        settings_env = getattr(settings, "environment", "development")
        if settings_env == "production":
            logger.error(
                "TURNSTILE_SECRET_KEY is unset in PRODUCTION -- refusing bot "
                "verification (fail-closed). Set CF_TURNSTILE_SECRET to restore login."
            )
            return False
        logger.warning(
            "TURNSTILE_SECRET_KEY is unset; skipping bot verification (fail-open). "
            "Set CF_TURNSTILE_SECRET in production."
        )
        return True

    if not token:
        logger.info("Turnstile verification failed: missing token")
        return False

    payload: dict[str, str] = {"secret": secret, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(TURNSTILE_VERIFY_URL, data=payload)
            data = resp.json()
            success = bool(data.get("success"))
            if not success:
                logger.info(
                    "Turnstile verification failed: %s", data.get("error-codes")
                )
            return success
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("Turnstile verification error: %s", e)
        return False
