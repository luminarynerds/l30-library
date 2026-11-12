# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for TOTP key separation + graceful decrypt-failure handling.

Covers finding C2 (2026-07-04 Fernet/PII audit):

- TOTP secrets get a dedicated TOTP_ENCRYPTION_KEY (mirroring
  TOKEN_ENCRYPTION_KEY) instead of deriving from SECRET_KEY.
- Already-enrolled users' secrets (encrypted under the legacy
  SECRET_KEY-derived key before this key existed) keep decrypting and are
  transparently migrated to the new key on next successful decrypt.
- A genuine decrypt failure at any of the 4 account_security.py call sites
  never raises a raw 500 -- it degrades to either "2FA reset, re-enroll"
  (identity already re-verified via password) or "use a recovery code, then
  re-enroll" (bare login step, must fail closed).
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.fernet import Fernet, InvalidToken

pytestmark = pytest.mark.unit


def _settings(
    *,
    secret_key: str = "legacy-secret-key",
    totp_encryption_key: str = "",
    totp_encryption_key_previous: str = "",
):
    return SimpleNamespace(
        secret_key=secret_key,
        totp_encryption_key=totp_encryption_key,
        totp_encryption_key_previous=totp_encryption_key_previous,
    )


class TestTotpKeyDerivation:
    """Pure encrypt/decrypt/migration behavior in app.core.totp."""

    def test_new_key_round_trip(self, monkeypatch):
        import app.core.totp as totp

        monkeypatch.setattr(
            totp, "settings", _settings(totp_encryption_key="dedicated-totp-key")
        )
        secret = "JBSWY3DPEHPK3PXP"
        ciphertext = totp.encrypt_totp_secret(secret)
        assert totp.decrypt_totp_secret(ciphertext) == secret

    def test_dedicated_key_and_legacy_key_are_different_secrets(self, monkeypatch):
        """A secret encrypted under TOTP_ENCRYPTION_KEY must NOT be readable
        via the legacy SECRET_KEY-derived key -- otherwise the split is fake."""
        import app.core.totp as totp

        monkeypatch.setattr(
            totp, "settings", _settings(totp_encryption_key="dedicated-totp-key")
        )
        ciphertext = totp.encrypt_totp_secret("JBSWY3DPEHPK3PXP")

        # No dedicated key configured -> pure legacy derivation.
        monkeypatch.setattr(totp, "settings", _settings())
        with pytest.raises(ValueError, match="Failed to decrypt TOTP secret"):
            totp.decrypt_totp_secret(ciphertext)

    def test_no_regression_when_totp_encryption_key_unset(self, monkeypatch):
        """Unset TOTP_ENCRYPTION_KEY -- behaves exactly like the pre-C2 code
        (secret_key-derived key only, no migration attempted)."""
        import app.core.totp as totp

        monkeypatch.setattr(totp, "settings", _settings())
        secret = "JBSWY3DPEHPK3PXP"
        ciphertext = totp.encrypt_totp_secret(secret)
        assert totp.decrypt_totp_secret(ciphertext) == secret
        plaintext, migrated = totp.decrypt_totp_secret_and_migrate(ciphertext)
        assert plaintext == secret
        assert migrated is None  # already "current" (there's only one key)

    def test_legacy_secret_lazy_migration(self, monkeypatch):
        """A secret encrypted before TOTP_ENCRYPTION_KEY existed (pure
        SECRET_KEY derivation) still decrypts once the key is introduced, and
        decrypt_totp_secret_and_migrate hands back fresh ciphertext under the
        new key for the caller to persist (lazy read-old-write-new)."""
        import app.core.totp as totp

        # Enrolled before TOTP_ENCRYPTION_KEY existed.
        monkeypatch.setattr(totp, "settings", _settings())
        legacy_ciphertext = totp.encrypt_totp_secret("JBSWY3DPEHPK3PXP")

        # TOTP_ENCRYPTION_KEY introduced; legacy secret must still work.
        monkeypatch.setattr(
            totp, "settings", _settings(totp_encryption_key="dedicated-totp-key")
        )
        plaintext, migrated_ciphertext = totp.decrypt_totp_secret_and_migrate(
            legacy_ciphertext
        )
        assert plaintext == "JBSWY3DPEHPK3PXP"
        assert migrated_ciphertext is not None
        assert migrated_ciphertext != legacy_ciphertext

        # The migrated ciphertext decrypts directly under the new key, no
        # legacy fallback needed anymore.
        assert totp.decrypt_totp_secret(migrated_ciphertext) == "JBSWY3DPEHPK3PXP"

    def test_previous_key_rotation_lazy_migration(self, monkeypatch):
        """TOTP_ENCRYPTION_KEY itself gets rotated: old value moves to
        TOTP_ENCRYPTION_KEY_PREVIOUS, still decryptable, and migrates forward."""
        import app.core.totp as totp

        monkeypatch.setattr(totp, "settings", _settings(totp_encryption_key="key-a"))
        old_ciphertext = totp.encrypt_totp_secret("JBSWY3DPEHPK3PXP")

        monkeypatch.setattr(
            totp,
            "settings",
            _settings(totp_encryption_key="key-b", totp_encryption_key_previous="key-a"),
        )
        plaintext, migrated_ciphertext = totp.decrypt_totp_secret_and_migrate(
            old_ciphertext
        )
        assert plaintext == "JBSWY3DPEHPK3PXP"
        assert migrated_ciphertext is not None
        assert totp.decrypt_totp_secret(migrated_ciphertext) == "JBSWY3DPEHPK3PXP"

    def test_decrypt_totp_secret_and_migrate_no_migration_when_already_current(
        self, monkeypatch
    ):
        import app.core.totp as totp

        monkeypatch.setattr(totp, "settings", _settings(totp_encryption_key="key-a"))
        ciphertext = totp.encrypt_totp_secret("JBSWY3DPEHPK3PXP")
        plaintext, migrated = totp.decrypt_totp_secret_and_migrate(ciphertext)
        assert plaintext == "JBSWY3DPEHPK3PXP"
        assert migrated is None

    def test_undecryptable_secret_raises(self, monkeypatch):
        import app.core.totp as totp

        monkeypatch.setattr(totp, "settings", _settings(totp_encryption_key="key-a"))
        garbage = Fernet(Fernet.generate_key()).encrypt(b"x").decode()
        with pytest.raises(ValueError, match="Failed to decrypt TOTP secret"):
            totp.decrypt_totp_secret(garbage)
        with pytest.raises(ValueError, match="Failed to decrypt TOTP secret"):
            totp.decrypt_totp_secret_and_migrate(garbage)


class TestCallSiteDegradation:
    """app.api.v1.account_security._decrypt_totp_secret_or_degrade"""

    @staticmethod
    def _fake_user(totp_secret: str):
        return SimpleNamespace(
            id=42,
            totp_secret=totp_secret,
            totp_enabled=True,
            totp_confirmed_at="2026-01-01T00:00:00Z",
            recovery_codes="[]",
        )

    @staticmethod
    def _fake_request():
        req = MagicMock()
        req.client.host = "127.0.0.1"
        req.headers.get.return_value = "pytest-agent"
        return req

    @staticmethod
    def _fake_db():
        db = MagicMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        return db

    async def test_returns_secret_on_successful_decrypt(self, monkeypatch):
        import app.core.totp as totp
        from app.api.v1.account_security import _decrypt_totp_secret_or_degrade

        monkeypatch.setattr(totp, "settings", _settings(totp_encryption_key="key-a"))
        user = self._fake_user(totp.encrypt_totp_secret("JBSWY3DPEHPK3PXP"))
        db = self._fake_db()

        secret = await _decrypt_totp_secret_or_degrade(
            db, user, self._fake_request(), reset_totp_on_failure=True
        )
        assert secret == "JBSWY3DPEHPK3PXP"
        db.commit.assert_not_called()  # nothing needed migrating

    async def test_migrates_legacy_secret_and_persists(self, monkeypatch):
        import app.core.totp as totp
        from app.api.v1.account_security import _decrypt_totp_secret_or_degrade

        monkeypatch.setattr(totp, "settings", _settings())  # legacy derivation
        legacy_ciphertext = totp.encrypt_totp_secret("JBSWY3DPEHPK3PXP")

        monkeypatch.setattr(totp, "settings", _settings(totp_encryption_key="key-a"))
        user = self._fake_user(legacy_ciphertext)
        db = self._fake_db()

        secret = await _decrypt_totp_secret_or_degrade(
            db, user, self._fake_request(), reset_totp_on_failure=True
        )
        assert secret == "JBSWY3DPEHPK3PXP"
        # Lazily re-encrypted under the current key and persisted.
        assert user.totp_secret != legacy_ciphertext
        assert totp.decrypt_totp_secret(user.totp_secret) == "JBSWY3DPEHPK3PXP"
        db.commit.assert_awaited_once()

    async def test_reset_on_failure_true_clears_totp_and_prompts_reenroll(
        self, monkeypatch
    ):
        import app.core.totp as totp
        from fastapi import HTTPException
        from app.api.v1.account_security import _decrypt_totp_secret_or_degrade

        monkeypatch.setattr(totp, "settings", _settings(totp_encryption_key="key-a"))
        garbage = Fernet(Fernet.generate_key()).encrypt(b"x").decode()
        user = self._fake_user(garbage)
        db = self._fake_db()

        with pytest.raises(HTTPException) as exc_info:
            await _decrypt_totp_secret_or_degrade(
                db, user, self._fake_request(), reset_totp_on_failure=True
            )

        assert exc_info.value.status_code == 400
        assert "reset" in exc_info.value.detail.lower()
        # Identity was already re-verified (password) by the caller, so it's
        # safe to clear 2FA state rather than lock the user out.
        assert user.totp_secret is None
        assert user.totp_enabled is False
        assert user.totp_confirmed_at is None
        assert user.recovery_codes is None
        db.add.assert_called_once()  # audit log
        db.commit.assert_awaited_once()

    async def test_reset_on_failure_false_fails_closed_without_resetting(
        self, monkeypatch
    ):
        """The bare /2fa/verify login step has no fresher identity check than
        the code itself -- a decrypt failure must NOT silently disable 2FA
        (that would bypass the second factor); it must fail closed and point
        the user at the recovery-code path instead."""
        import app.core.totp as totp
        from fastapi import HTTPException
        from app.api.v1.account_security import _decrypt_totp_secret_or_degrade

        monkeypatch.setattr(totp, "settings", _settings(totp_encryption_key="key-a"))
        garbage = Fernet(Fernet.generate_key()).encrypt(b"x").decode()
        user = self._fake_user(garbage)
        db = self._fake_db()

        with pytest.raises(HTTPException) as exc_info:
            await _decrypt_totp_secret_or_degrade(
                db, user, self._fake_request(), reset_totp_on_failure=False
            )

        assert exc_info.value.status_code == 401
        assert "recovery code" in exc_info.value.detail.lower()
        # 2FA state must be left intact -- no silent bypass/reset from the
        # unauthenticated side of the login flow.
        assert user.totp_secret == garbage
        assert user.totp_enabled is True
        db.add.assert_called_once()  # audit log
        db.commit.assert_awaited_once()
