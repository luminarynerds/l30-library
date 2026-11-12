# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Slice A: ensure hold-jobs HTML emails escape user + item fields.

The notification builders concatenated ``user.first_name``, ``item.title``,
and ``item.author`` straight into an HTML f-string. Today catalog titles
and author fields are staff-edited, so the attack surface is "compromised
staff + HTML mail client renders the body". But cross-vector sources
(patron-submitted purchase suggestions, MARC ingest with crafted 245$a,
patron full_name in the daily-report) keep this in dual-use territory.

These tests pin the contract: every interpolated user/item field is
HTML-escaped before it enters the email body.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import app.services.hold_jobs as hold_jobs_module
from app.services.hold_jobs import (
    _send_hold_expired_notification,
    _send_hold_expiration_reminder_notification,
    _send_hold_ready_notification,
)


XSS_TITLE = "<script>alert('xss')</script>"
XSS_AUTHOR = "<img src=x onerror=alert(1)>"
XSS_FIRST_NAME = "<svg onload=alert(2)>"


class _CaptureSendEmail:
    """Captures (to, subject, html_content) so tests can inspect the body."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    async def __call__(self, to: str, subject: str, html_content: str) -> bool:
        self.calls.append((to, subject, html_content))
        return True

    @property
    def last_html(self) -> str:
        assert self.calls, "send_email was never invoked"
        return self.calls[-1][2]


@pytest.fixture
def capture_send_email(monkeypatch):
    """Replace ``send_email`` inside ``hold_jobs`` with an in-memory capture.

    Patch the symbol on the importing module (``app.services.hold_jobs``),
    not on ``app.core.email``, so the from-import-bound reference is the
    one being swapped.
    """
    sink = _CaptureSendEmail()
    monkeypatch.setattr(hold_jobs_module, "send_email", sink)
    return sink


def _user() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        email="patron@example.com",
        first_name=XSS_FIRST_NAME,
    )


def _item() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        title=XSS_TITLE,
        author=XSS_AUTHOR,
    )


def _assert_escaped(body: str) -> None:
    """All three XSS payloads must appear escaped, never raw."""
    assert XSS_TITLE not in body, "raw <script> title leaked into HTML body"
    assert XSS_AUTHOR not in body, "raw <img onerror> author leaked into HTML body"
    assert XSS_FIRST_NAME not in body, "raw <svg onload> first_name leaked into HTML body"
    # And the escaped forms must be present (sanity check the substitution
    # didn't simply drop the values).
    assert "&lt;script&gt;alert(" in body
    assert "&lt;img src=x onerror=alert(1)&gt;" in body
    assert "&lt;svg onload=alert(2)&gt;" in body


async def test_hold_expired_email_escapes_xss(capture_send_email):
    ok = await _send_hold_expired_notification(_user(), _item(), db=None)
    assert ok is True
    _assert_escaped(capture_send_email.last_html)


async def test_hold_ready_email_escapes_xss(capture_send_email):
    ok = await _send_hold_ready_notification(_user(), _item(), db=None)
    assert ok is True
    _assert_escaped(capture_send_email.last_html)


async def test_hold_expiration_reminder_email_escapes_xss(capture_send_email):
    expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    ok = await _send_hold_expiration_reminder_notification(
        _user(), _item(), expires_at
    )
    assert ok is True
    _assert_escaped(capture_send_email.last_html)
