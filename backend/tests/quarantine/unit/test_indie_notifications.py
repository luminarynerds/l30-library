# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import sys
import types

import asyncio

import pytest

httpx_stub = types.SimpleNamespace(
    AsyncClient=object,
    TimeoutException=Exception,
    RequestError=Exception,
)
sys.modules.setdefault("httpx", httpx_stub)

config_stub = types.ModuleType("app.core.config")

class SettingsStub:
    resend_api_key = ""
    from_email = "noreply@example.com"
    app_name = "Test Library"
    frontend_url = "https://example.com"

def get_settings():
    return SettingsStub()

config_stub.get_settings = get_settings
sys.modules.setdefault("app.core.config", config_stub)

logging_stub = types.ModuleType("app.core.logging")

def get_logger(name):
    return types.SimpleNamespace(info=lambda *args, **kwargs: None)

logging_stub.get_logger = get_logger
sys.modules.setdefault("app.core.logging", logging_stub)

from app.core import email  # noqa: E402


def test_send_indie_review_notification_includes_status_and_reason(monkeypatch):
    captured = {}

    async def fake_send_email(to_email, subject, html_content, attachment_data=None, attachment_filename=None):
        captured["to_email"] = to_email
        captured["subject"] = subject
        captured["html"] = html_content
        return True

    monkeypatch.setattr(email, "send_email", fake_send_email)

    result = asyncio.run(email.send_indie_review_notification(
        to_email="author@example.com",
        first_name="Riley",
        book_title="Moonlight",
        decision="rejected",
        notes="Please revise",
        rejection_reason="Metadata mismatch",
    ))

    assert result is True
    assert captured["to_email"] == "author@example.com"
    assert "Rejected" in captured["subject"]
    assert "Metadata mismatch" in captured["html"]
    assert "Please revise" in captured["html"]


def test_send_indie_author_verification_notification(monkeypatch):
    captured = {}

    async def fake_send_email(to_email, subject, html_content, attachment_data=None, attachment_filename=None):
        captured["to_email"] = to_email
        captured["subject"] = subject
        captured["html"] = html_content
        return True

    monkeypatch.setattr(email, "send_email", fake_send_email)

    result = asyncio.run(email.send_indie_author_verification_notification(
        to_email="author@example.com",
        first_name="Riley",
        decision="verified",
        notes="Profile approved",
    ))

    assert result is True
    assert captured["to_email"] == "author@example.com"
    assert "Verified" in captured["subject"]
    assert "Profile approved" in captured["html"]
