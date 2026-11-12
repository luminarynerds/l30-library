# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Self-host escape hatch for Turnstile.

A fresh self-host install has no Cloudflare account, so `CF_TURNSTILE_SECRET`
is unset. `verify_turnstile` fails CLOSED in production when the secret is
missing (see test_sec_med_low_batch.py's
test_turnstile_fails_closed_in_production_when_secret_unset) -- correct for a
hosted deployment, but it means nobody can ever log in on a fresh self-host.

`TURNSTILE_DISABLED` is an explicit, opt-in escape hatch: set it and
verification short-circuits to True even in production. Default is False, so
an install that does NOT set it keeps the existing fail-closed behavior.
"""

from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.asyncio


async def test_turnstile_bypassed_when_self_host_flag_set():
    """TURNSTILE_DISABLED=true bypasses verification, even in production."""
    from app.core.turnstile import verify_turnstile

    fake = SimpleNamespace(
        turnstile_secret_key=None,
        environment="production",
        turnstile_disabled=True,
    )
    from unittest.mock import patch

    with patch("app.core.turnstile.get_settings", return_value=fake):
        assert await verify_turnstile(token=None, remote_ip=None) is True


async def test_turnstile_still_fails_closed_when_flag_absent():
    """Without TURNSTILE_DISABLED (the default), production still fails
    closed when no secret is configured -- the escape hatch must not weaken
    the default hosted behavior."""
    from app.core.turnstile import verify_turnstile

    fake = SimpleNamespace(
        turnstile_secret_key=None,
        environment="production",
        turnstile_disabled=False,
    )
    from unittest.mock import patch

    with patch("app.core.turnstile.get_settings", return_value=fake):
        assert await verify_turnstile(token="token", remote_ip=None) is False


async def test_turnstile_flag_via_real_settings_env(monkeypatch):
    """End-to-end through the real Settings/env wiring, not just a fake:
    TURNSTILE_DISABLED=true in the environment reaches verify_turnstile."""
    from app.core import config as config_module
    from app.core.turnstile import verify_turnstile

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("TURNSTILE_DISABLED", "true")
    from cryptography.fernet import Fernet

    monkeypatch.setenv("PII_ENCRYPTION_ENABLED", "true")
    monkeypatch.setenv("PII_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("PII_HASH_KEY", "test-hash-key")
    monkeypatch.setenv("WATERMARK_SECRET_SALT", "test-watermark-salt-not-default")
    monkeypatch.setenv("DOWNLOAD_IP_HASH_SALT", "test-download-salt-not-default")
    monkeypatch.delenv("CF_TURNSTILE_SECRET", raising=False)
    config_module.get_settings.cache_clear()
    try:
        assert await verify_turnstile(token=None, remote_ip=None) is True
    finally:
        config_module.get_settings.cache_clear()
