# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Security regression: stored-XSS sinks now escape/sanitize untrusted input.

1. Circulation notification emails (app/services/notifications/templates.py):
   user.first_name, item.title, item.author, item.location are patron- or
   catalog-sourced and were interpolated raw into HTML email bodies. They must
   be HTML-escaped. (The email *subject* is a plain-text header and is
   intentionally left un-HTML-escaped.)

2. Knowledge Base entry content (app/api/v1/knowledge_base.py): authored as
   rich-text HTML by staff and served unauthenticated to patrons; must be run
   through the nh3 sanitizer, like blog bodies.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.notifications.templates import (
    render_checkout_receipt_email,
    render_due_date_reminder_email,
    render_overdue_notice_email,
    render_hold_ready_email,
    render_hold_expiring_email,
)
from app.api.v1.knowledge_base import KnowledgeEntryCreate, KnowledgeEntryUpdate

_DT = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
_SCRIPT = "<script>alert(1)</script>"
_IMG = "<img src=x onerror=alert(1)>"


def _checkout():
    return SimpleNamespace(due_date=_DT, checked_out_at=_DT)


def _hold():
    return SimpleNamespace(expires_at=_DT)


def test_checkout_receipt_escapes_name_title_author():
    user = SimpleNamespace(first_name=_SCRIPT)
    item = SimpleNamespace(title=_IMG, author="<b>evil</b>", location=None)
    _subject, body = render_checkout_receipt_email(user, item, _checkout(), lang="en")
    assert "<script>" not in body
    assert "<img src=x" not in body
    assert "<b>evil</b>" not in body
    # escaped forms present -> the values reached the body, just neutralized
    assert "&lt;script&gt;" in body
    assert "&lt;img" in body


def test_due_date_reminder_escapes_title():
    user = SimpleNamespace(first_name="Reg")
    item = SimpleNamespace(title=_SCRIPT, author=None, location=None)
    _subject, body = render_due_date_reminder_email(user, item, _checkout(), days_until_due=2, lang="en")
    assert "<script>" not in body
    assert "&lt;script&gt;" in body


def test_overdue_notice_escapes_title():
    user = SimpleNamespace(first_name="Reg")
    item = SimpleNamespace(title=_SCRIPT, author=None, location=None)
    _subject, body = render_overdue_notice_email(user, item, _checkout(), days_overdue=3, lang="en")
    assert "<script>" not in body
    assert "&lt;script&gt;" in body


def test_hold_ready_escapes_location():
    user = SimpleNamespace(first_name="Reg")
    item = SimpleNamespace(title="Book", author=None, location=_SCRIPT)
    _subject, body = render_hold_ready_email(user, item, _hold(), lang="en")
    assert "<script>" not in body
    assert "&lt;script&gt;" in body


def test_hold_expiring_escapes_title():
    user = SimpleNamespace(first_name="Reg")
    item = SimpleNamespace(title=_SCRIPT, author=None, location=None)
    _subject, body = render_hold_expiring_email(user, item, _hold(), days_until_expiry=1, lang="en")
    assert "<script>" not in body
    assert "&lt;script&gt;" in body


def test_none_name_and_title_do_not_crash():
    """Regression guard: escaping must not turn a None field into a crash."""
    user = SimpleNamespace(first_name=None)
    item = SimpleNamespace(title=None, author=None, location=None)
    _subject, body = render_checkout_receipt_email(user, item, _checkout(), lang="en")
    assert body  # rendered without raising


def test_kb_create_sanitizes_content():
    entry = KnowledgeEntryCreate(
        category="Borrowing",
        title="How to renew",
        content="<script>alert(1)</script><p>Renew online.</p>",
    )
    assert "<script>" not in entry.content
    assert "<p>Renew online.</p>" in entry.content


def test_kb_update_strips_event_handler_attribute():
    entry = KnowledgeEntryUpdate(content='<img src=x onerror=alert(1)><p>hi</p>')
    assert "onerror" not in entry.content
    assert "<p>hi</p>" in entry.content
