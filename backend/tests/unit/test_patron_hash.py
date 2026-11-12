# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for patron hash generation."""
import hashlib
import hmac

from app.utils.patron_hash import generate_patron_hash


def test_patron_hash_is_deterministic():
    """Same user_id always produces the same hash."""
    h1 = generate_patron_hash(42)
    h2 = generate_patron_hash(42)
    assert h1 == h2


def test_patron_hash_differs_per_user():
    """Different user_ids produce different hashes."""
    h1 = generate_patron_hash(1)
    h2 = generate_patron_hash(2)
    assert h1 != h2


def test_patron_hash_is_16_chars():
    """Hash is truncated to 16 hex characters."""
    h = generate_patron_hash(1)
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)


def test_patron_hash_not_plain_sha256():
    """Hash must NOT be plain sha256 of the user_id (insecure)."""
    plain = hashlib.sha256(b"42").hexdigest()[:16]
    actual = generate_patron_hash(42)
    assert actual != plain, "patron_hash should use HMAC, not plain sha256"


def test_patron_hash_accepts_string():
    """Should accept string user_id too."""
    h1 = generate_patron_hash(42)
    h2 = generate_patron_hash("42")
    assert h1 == h2
