# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""SMS seam: no provider is wired; sends must fail loudly, never AttributeError."""

import types

import pytest

from app.core import sms as sms_core
from app.core.sms import SMSConfigurationError, send_sms, send_verification_sms


async def test_send_sms_disabled_returns_disabled_dict(monkeypatch):
    monkeypatch.setattr(
        sms_core,
        "settings",
        types.SimpleNamespace(sms_enabled=False),
    )
    result = await send_sms("+15555550100", "hello")
    assert result["status"] == "disabled"
    assert result["sid"] == "disabled"
    assert result["cost_cents"] == 0


async def test_send_sms_enabled_without_provider_raises_config_error(monkeypatch):
    monkeypatch.setattr(
        sms_core,
        "settings",
        types.SimpleNamespace(sms_enabled=True),
    )
    with pytest.raises(SMSConfigurationError):
        await send_sms("+15555550100", "hello")


async def test_send_verification_sms_works_without_provider_settings(monkeypatch):
    # Regression: used to AttributeError on settings.sms_verification_expiry_minutes
    monkeypatch.setattr(
        sms_core,
        "settings",
        types.SimpleNamespace(sms_enabled=False),
    )
    result = await send_verification_sms("+15555550100", "123456")
    assert result["status"] == "disabled"
