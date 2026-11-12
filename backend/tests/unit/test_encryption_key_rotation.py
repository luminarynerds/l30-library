# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for PII encryption key rotation support.

Tests cover:
- Decrypting data encrypted with the previous key after rotation
- Fallback counter increments when previous key is used
- Data encrypted with the current key decrypts directly
- get_decryption_health() returns correct metrics
- Undecryptable data returns as-is when no previous key is configured
"""

from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet


@pytest.mark.unit
class TestEncryptionKeyRotation:
    """Test encryption key rotation behaviour in decrypt_pii."""

    def _reset_encryption_module(self):
        """Reset the module-level globals so each test starts clean."""
        import app.core.encryption as enc

        enc._fernet = None
        enc._fernet_previous = None
        enc._decryption_fallback_count = 0
        enc._decryption_failure_count = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_settings(
        *,
        key: str = "",
        key_previous: str = "",
        enabled: bool = True,
    ):
        """Build a minimal mock settings object."""

        class _Settings:
            pii_encryption_key = key
            pii_encryption_key_previous = key_previous
            pii_encryption_enabled = enabled

        return _Settings()

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_decrypt_with_current_key(self):
        """Data encrypted with the current key decrypts without fallback."""
        self._reset_encryption_module()

        key_a = Fernet.generate_key().decode()
        fernet_a = Fernet(key_a.encode())

        plaintext = "555-867-5309"
        ciphertext = fernet_a.encrypt(plaintext.encode()).decode()

        _ = self._make_settings(key=key_a, key_previous="")

        with patch("app.core.encryption._get_fernet") as mock_get:
            mock_get.return_value = fernet_a
            with patch("app.core.encryption._get_fernet_previous") as mock_prev:
                mock_prev.return_value = None

                from app.core.encryption import decrypt_pii

                result = decrypt_pii(ciphertext)

        assert result == plaintext

    def test_decrypt_with_previous_key_after_rotation(self):
        """Data encrypted with old key A can be decrypted after rotating to key B."""
        self._reset_encryption_module()

        key_a = Fernet.generate_key().decode()
        key_b = Fernet.generate_key().decode()
        fernet_a = Fernet(key_a.encode())
        fernet_b = Fernet(key_b.encode())

        plaintext = "123 Main St, Bébé Memorial"
        ciphertext = fernet_a.encrypt(plaintext.encode()).decode()

        with patch("app.core.encryption._get_fernet") as mock_get:
            mock_get.return_value = fernet_b  # new key (can't decrypt old data)
            with patch("app.core.encryption._get_fernet_previous") as mock_prev:
                mock_prev.return_value = fernet_a  # old key

                from app.core.encryption import decrypt_pii

                result = decrypt_pii(ciphertext)

        assert result == plaintext

    def test_fallback_counter_increments(self):
        """When fallback to previous key is used, the counter increments."""
        self._reset_encryption_module()

        import app.core.encryption as enc

        key_a = Fernet.generate_key().decode()
        key_b = Fernet.generate_key().decode()
        fernet_a = Fernet(key_a.encode())
        fernet_b = Fernet(key_b.encode())

        plaintext = "patron@example.com"
        ciphertext = fernet_a.encrypt(plaintext.encode()).decode()

        assert enc._decryption_fallback_count == 0

        with patch("app.core.encryption._get_fernet") as mock_get:
            mock_get.return_value = fernet_b
            with patch("app.core.encryption._get_fernet_previous") as mock_prev:
                mock_prev.return_value = fernet_a

                enc.decrypt_pii(ciphertext)

        assert enc._decryption_fallback_count == 1

        # Decrypt again — counter should go to 2
        with patch("app.core.encryption._get_fernet") as mock_get:
            mock_get.return_value = fernet_b
            with patch("app.core.encryption._get_fernet_previous") as mock_prev:
                mock_prev.return_value = fernet_a

                enc.decrypt_pii(ciphertext)

        assert enc._decryption_fallback_count == 2

    def test_no_fallback_counter_for_current_key(self):
        """Decrypting with the current key does NOT increment fallback counter."""
        self._reset_encryption_module()

        import app.core.encryption as enc

        key_a = Fernet.generate_key().decode()
        fernet_a = Fernet(key_a.encode())

        plaintext = "555-0100"
        ciphertext = fernet_a.encrypt(plaintext.encode()).decode()

        with patch("app.core.encryption._get_fernet") as mock_get:
            mock_get.return_value = fernet_a
            with patch("app.core.encryption._get_fernet_previous") as mock_prev:
                mock_prev.return_value = None

                enc.decrypt_pii(ciphertext)

        assert enc._decryption_fallback_count == 0

    def test_undecryptable_returns_as_is_no_previous_key(self):
        """With no previous key, undecryptable data is returned as-is."""
        self._reset_encryption_module()

        import app.core.encryption as enc

        key_b = Fernet.generate_key().decode()
        fernet_b = Fernet(key_b.encode())

        # Some string that is NOT valid Fernet ciphertext for key_b
        garbage = "not-a-valid-fernet-token"

        with patch("app.core.encryption._get_fernet") as mock_get:
            mock_get.return_value = fernet_b
            with patch("app.core.encryption._get_fernet_previous") as mock_prev:
                mock_prev.return_value = None

                result = enc.decrypt_pii(garbage)

        assert result == garbage
        assert enc._decryption_failure_count == 1

    def test_undecryptable_returns_as_is_both_keys(self):
        """When neither key can decrypt, data is returned as-is."""
        self._reset_encryption_module()

        import app.core.encryption as enc

        key_a = Fernet.generate_key().decode()
        key_b = Fernet.generate_key().decode()
        fernet_a = Fernet(key_a.encode())
        fernet_b = Fernet(key_b.encode())

        garbage = "totally-not-encrypted"

        with patch("app.core.encryption._get_fernet") as mock_get:
            mock_get.return_value = fernet_b
            with patch("app.core.encryption._get_fernet_previous") as mock_prev:
                mock_prev.return_value = fernet_a

                result = enc.decrypt_pii(garbage)

        assert result == garbage
        assert enc._decryption_failure_count == 1

    def test_decrypt_none_returns_none(self):
        """decrypt_pii(None) always returns None."""
        self._reset_encryption_module()

        from app.core.encryption import decrypt_pii

        assert decrypt_pii(None) is None

    def test_get_decryption_health_initial(self):
        """get_decryption_health() returns correct initial metrics."""
        self._reset_encryption_module()

        import app.core.encryption as enc

        with patch("app.core.encryption._get_fernet") as mock_get:
            mock_get.return_value = None  # encryption disabled
            with patch("app.core.encryption._get_fernet_previous") as mock_prev:
                mock_prev.return_value = None

                health = enc.get_decryption_health()

        assert health["encryption_enabled"] is False
        assert health["previous_key_configured"] is False
        assert health["fallback_decryptions"] == 0
        assert health["failed_decryptions"] == 0

    def test_get_decryption_health_after_operations(self):
        """get_decryption_health() reflects fallback and failure counts."""
        self._reset_encryption_module()

        import app.core.encryption as enc

        key_a = Fernet.generate_key().decode()
        key_b = Fernet.generate_key().decode()
        fernet_a = Fernet(key_a.encode())
        fernet_b = Fernet(key_b.encode())

        # Cause one fallback decryption
        ciphertext_old = fernet_a.encrypt(b"test-data").decode()
        with patch("app.core.encryption._get_fernet") as mock_get:
            mock_get.return_value = fernet_b
            with patch("app.core.encryption._get_fernet_previous") as mock_prev:
                mock_prev.return_value = fernet_a
                enc.decrypt_pii(ciphertext_old)

        # Cause one failure
        with patch("app.core.encryption._get_fernet") as mock_get:
            mock_get.return_value = fernet_b
            with patch("app.core.encryption._get_fernet_previous") as mock_prev:
                mock_prev.return_value = fernet_a
                enc.decrypt_pii("garbage-data")

        with patch("app.core.encryption._get_fernet") as mock_get:
            mock_get.return_value = fernet_b
            with patch("app.core.encryption._get_fernet_previous") as mock_prev:
                mock_prev.return_value = fernet_a

                health = enc.get_decryption_health()

        assert health["encryption_enabled"] is True
        assert health["previous_key_configured"] is True
        assert health["fallback_decryptions"] == 1
        assert health["failed_decryptions"] == 1

    def test_encrypt_then_decrypt_roundtrip(self):
        """encrypt_pii -> decrypt_pii roundtrip returns the original value."""
        self._reset_encryption_module()

        import app.core.encryption as enc

        key = Fernet.generate_key().decode()
        fernet = Fernet(key.encode())

        plaintext = "42 Wallaby Way, Sydney"

        with patch("app.core.encryption._get_fernet") as mock_get:
            mock_get.return_value = fernet

            encrypted = enc.encrypt_pii(plaintext)
            assert encrypted != plaintext

            with patch("app.core.encryption._get_fernet_previous") as mock_prev:
                mock_prev.return_value = None
                decrypted = enc.decrypt_pii(encrypted)

        assert decrypted == plaintext

    def test_encryption_disabled_passthrough(self):
        """When encryption is disabled, encrypt/decrypt pass values through."""
        self._reset_encryption_module()

        import app.core.encryption as enc

        plaintext = "555-1234"

        with patch("app.core.encryption._get_fernet") as mock_get:
            mock_get.return_value = None  # disabled

            encrypted = enc.encrypt_pii(plaintext)
            assert encrypted == plaintext

            decrypted = enc.decrypt_pii(plaintext)
            assert decrypted == plaintext
