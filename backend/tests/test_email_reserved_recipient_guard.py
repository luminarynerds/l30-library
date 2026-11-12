# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the reserved-recipient guard in app.core.email.

These exercise the pure ``_is_reserved_recipient`` helper directly: no
network, no DB, no Resend call. The guard exists to stop seed/demo/test
fixture addresses (e.g. the example.invalid teacher fan-out on 2026-06-07
that tripped Resend's >200/day alert) from ever reaching the provider.
"""
import pytest

from app.core.email import _is_reserved_recipient


@pytest.mark.parametrize(
    "addr",
    [
        "a@example.invalid",  # .invalid TLD
        "b@example.test",  # .test TLD
        "c@foo.example",  # .example TLD
        "e@host.localhost",  # .localhost TLD (subdomain)
        "d@localhost",  # bare localhost (reserved domain)
        "f@example.com",  # reserved domain
        "g@example.org",  # reserved domain
        "h@example.net",  # reserved domain
    ],
)
def test_reserved_recipients_are_blocked(addr):
    assert _is_reserved_recipient(addr) is True


@pytest.mark.parametrize(
    "addr",
    [
        "real@gmail.com",
        "patron@l30.org",
        "x@school.edu",
    ],
)
def test_real_recipients_are_allowed(addr):
    assert _is_reserved_recipient(addr) is False


def test_reserved_recipient_is_case_insensitive():
    # Helper lowercases input, so uppercase reserved addresses are still caught.
    assert _is_reserved_recipient("A@EXAMPLE.INVALID") is True


def test_bare_localhost_is_blocked():
    # Bare "localhost" is in _RESERVED_EMAIL_DOMAINS; "*.localhost" is caught by
    # the .localhost TLD check. Both are blocked.
    assert _is_reserved_recipient("d@localhost") is True
    assert _is_reserved_recipient("e@host.localhost") is True
