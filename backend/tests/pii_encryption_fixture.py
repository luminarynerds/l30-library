# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixture that turns real Fernet PII encryption on for the tests that assert it.

The deploy gate runs the suite with PII_ENCRYPTION_ENABLED=false, because a
worktree with no .env cannot construct Settings otherwise -- a key is required
whenever encryption is enabled. That left the ciphertext-at-rest tests unable to
pass under any setting: disabled stores plaintext, so the assertions fail, and
enabling it without a key fails Settings validation at import.

Supplying a key here lets those tests assert the real thing rather than depend on
ambient config. encrypt_pii() reads settings at call time, so flipping it per-test
is enough; the cached Fernet is reset so it re-initialises against the test key.
"""

import pytest


@pytest.fixture
def pii_encryption_on(monkeypatch):
    from cryptography.fernet import Fernet

    from app.core import encryption
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "pii_encryption_enabled", True)
    monkeypatch.setattr(settings, "pii_encryption_key", Fernet.generate_key().decode())
    monkeypatch.setattr(encryption, "_fernet", None)
    monkeypatch.setattr(encryption, "_fernet_previous", None)
