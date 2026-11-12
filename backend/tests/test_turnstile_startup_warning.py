# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Startup-time warning for the TURNSTILE_DISABLED self-host escape hatch.

`verify_turnstile` is the single choke point for ~10 public endpoints, not
just login (book challenges, public-records requests, event registration,
card applications, account-security, password/registration flows). If a
library forks this dist template and later exposes their patron portal to
the internet without unsetting TURNSTILE_DISABLED, every one of those forms
loses bot/CAPTCHA protection with only a per-request debug log line as the
tell.

This test asserts a single loud, actionable WARNING is emitted at app
startup (not per-request) when environment=production and
TURNSTILE_DISABLED=true, naming the real scope and telling the operator
what to do about it -- and that the warning does NOT fire when the flag is
false.
"""

import logging

import pytest

# Force app.main to import now, under whatever ambient (non-production) env
# is active at collection time. app.main builds CORSMiddleware at MODULE
# level from the process-global `settings = get_settings()` (app/main.py),
# not a per-request lookup -- if this module were the first thing in the
# session to trigger `from app.main import ...` (module caching means it
# only executes once), and that first import happened AFTER the
# production_env fixture below had already monkeypatched
# ENVIRONMENT=production, the default cors_origins ("http://localhost:...")
# would fail Settings' production CORS validation before the test body ever
# runs. Importing it here, at module load, avoids that ordering hazard.
import app.main  # noqa: F401


def _clear_settings_cache():
    from app.core import config as config_module

    config_module.get_settings.cache_clear()


@pytest.fixture
def production_env(monkeypatch):
    """Minimum env to pass Settings validation with environment=production."""
    from cryptography.fernet import Fernet

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("PII_ENCRYPTION_ENABLED", "true")
    monkeypatch.setenv("PII_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("PII_HASH_KEY", "test-hash-key")
    monkeypatch.setenv("WATERMARK_SECRET_SALT", "test-watermark-salt-not-default")
    monkeypatch.setenv("DOWNLOAD_IP_HASH_SALT", "test-download-salt-not-default")
    _clear_settings_cache()
    yield
    _clear_settings_cache()


def _capture_app_logs(caplog):
    """app.main logs through the "app" logger, which is configured with
    propagate=False (backend/app/core/logging.py) -- caplog's default
    root-attached handler never sees it. Attach directly instead."""
    logger = logging.getLogger("app.main")
    logger.addHandler(caplog.handler)
    logger.setLevel(logging.WARNING)
    return logger


def test_warns_when_turnstile_disabled_in_production(production_env, monkeypatch, caplog):
    """environment=production + TURNSTILE_DISABLED=true -> loud startup warning
    naming the real scope (all public forms, not just login)."""
    from app.main import _validate_turnstile_startup

    monkeypatch.setenv("TURNSTILE_DISABLED", "true")
    monkeypatch.delenv("CF_TURNSTILE_SECRET", raising=False)
    _clear_settings_cache()

    logger = _capture_app_logs(caplog)
    try:
        _validate_turnstile_startup()
    finally:
        logger.removeHandler(caplog.handler)

    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1
    message = warnings[0].message
    assert "TURNSTILE_DISABLED" in message
    assert "production" in message.lower()
    # Must name the real scope, not just login
    assert "login" in message.lower()
    assert "book challenge" in message.lower() or "public records" in message.lower()
    assert "CF_TURNSTILE_SECRET" in message


def test_no_warning_when_turnstile_flag_false(production_env, monkeypatch, caplog):
    """The flag is off (the default) -- no warning should fire."""
    from app.main import _validate_turnstile_startup

    monkeypatch.setenv("TURNSTILE_DISABLED", "false")
    monkeypatch.setenv("CF_TURNSTILE_SECRET", "real-secret-value")
    _clear_settings_cache()

    logger = _capture_app_logs(caplog)
    try:
        _validate_turnstile_startup()
    finally:
        logger.removeHandler(caplog.handler)

    assert not any(r.levelno >= logging.WARNING for r in caplog.records)


def test_no_warning_when_not_production(monkeypatch, caplog):
    """TURNSTILE_DISABLED=true is expected/normal in development -- no warning."""
    from app.main import _validate_turnstile_startup

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("TURNSTILE_DISABLED", "true")
    monkeypatch.setenv("PII_ENCRYPTION_ENABLED", "false")
    monkeypatch.delenv("CF_TURNSTILE_SECRET", raising=False)
    _clear_settings_cache()

    logger = _capture_app_logs(caplog)
    try:
        _validate_turnstile_startup()
    finally:
        logger.removeHandler(caplog.handler)

    assert not any(r.levelno >= logging.WARNING for r in caplog.records)

    _clear_settings_cache()
