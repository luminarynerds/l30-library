# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import base64
import hashlib
import hmac
from app.core.logging import get_logger
from typing import Optional

logger = get_logger(__name__)

# Lazy import to avoid circular imports
_fernet = None
_fernet_previous = None

# Metrics tracking for decryption operations
_decryption_fallback_count = 0
_decryption_failure_count = 0


def _get_fernet():
    global _fernet
    if _fernet is None:
        from .config import get_settings

        settings = get_settings()

        if not settings.pii_encryption_enabled:
            return None

        if not settings.pii_encryption_key:
            logger.warning(
                "PII encryption is enabled but PII_ENCRYPTION_KEY is not set. "
                "Encryption will be disabled."
            )
            return None

        try:
            from cryptography.fernet import Fernet

            _fernet = Fernet(settings.pii_encryption_key.encode())
        except (ValueError, TypeError, ImportError) as e:
            logger.error("Failed to initialize Fernet encryption: %s", e)
            return None

    return _fernet


def _get_fernet_previous():
    global _fernet_previous
    if _fernet_previous is None:
        from .config import get_settings

        settings = get_settings()

        if not settings.pii_encryption_key_previous:
            return None

        try:
            from cryptography.fernet import Fernet

            _fernet_previous = Fernet(settings.pii_encryption_key_previous.encode())
        except (ValueError, TypeError, ImportError) as e:
            logger.error("Failed to initialize previous Fernet encryption key: %s", e)
            return None

    return _fernet_previous


def _track_decryption_fallback():
    global _decryption_fallback_count
    _decryption_fallback_count += 1
    try:
        from .metrics import increment

        increment("pii_decryption_fallback_total")
    except Exception:  # noqa: BLE001  # metrics emission must never affect decryption path
        logger.debug("Failed to emit decryption fallback metric", exc_info=True)


def _track_decryption_failure():
    global _decryption_failure_count
    _decryption_failure_count += 1
    try:
        from .metrics import increment

        increment("pii_decryption_failure_total")
    except Exception:  # noqa: BLE001  # metrics emission must never affect decryption path
        logger.debug("Failed to emit decryption failure metric", exc_info=True)


def get_decryption_health() -> dict:
    return {
        "encryption_enabled": is_encryption_enabled(),
        "previous_key_configured": _get_fernet_previous() is not None,
        "fallback_decryptions": _decryption_fallback_count,
        "failed_decryptions": _decryption_failure_count,
    }


def encrypt_pii(plaintext: Optional[str]) -> Optional[str]:
    if plaintext is None:
        return None

    fernet = _get_fernet()
    if fernet is None:
        return plaintext  # Return unencrypted if disabled

    try:
        encrypted = fernet.encrypt(plaintext.encode())
        return encrypted.decode()
    except Exception as e:  # noqa: BLE001  # exception translation boundary — any encrypt failure must refuse plaintext storage
        logger.critical("Failed to encrypt PII -- refusing to store plaintext: %s", e)
        raise ValueError(f"PII encryption failed: {e}") from e


def decrypt_pii(ciphertext: Optional[str]) -> Optional[str]:
    if ciphertext is None:
        return None

    fernet = _get_fernet()
    if fernet is None:
        return ciphertext  # Return as-is if encryption disabled

    from cryptography.fernet import InvalidToken

    # Try current key first
    try:
        decrypted = fernet.decrypt(ciphertext.encode())
        return decrypted.decode()
    except InvalidToken:
        logger.debug("PII decryption failed with current key, trying fallback")

    # Try previous key (key rotation support)
    fernet_prev = _get_fernet_previous()
    if fernet_prev is not None:
        try:
            decrypted = fernet_prev.decrypt(ciphertext.encode())
            logger.warning(
                "PII decrypted with previous key — data needs re-encryption. "
                "Run the re-encryption migration to update all records."
            )
            _track_decryption_fallback()
            return decrypted.decode()
        except InvalidToken:
            logger.debug("PII decryption failed with previous key too")

    # Neither key worked — likely unencrypted legacy data
    logger.warning("Failed to decrypt PII (may be unencrypted or corrupted): returning as-is")
    _track_decryption_failure()
    return ciphertext


def is_encryption_enabled() -> bool:
    return _get_fernet() is not None


def generate_encryption_key() -> str:
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()


class EncryptedPIIField:
    def __init__(self, storage_attr: str):
        self.storage_attr = storage_attr

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        encrypted = getattr(obj, self.storage_attr, None)
        return decrypt_pii(encrypted)

    def __set__(self, obj, value):
        encrypted = encrypt_pii(value)
        setattr(obj, self.storage_attr, encrypted)


def _sqlalchemy_types():
    from sqlalchemy.types import String, Text, TypeDecorator

    return String, Text, TypeDecorator


_String, _Text, _TypeDecorator = _sqlalchemy_types()


class EncryptedString(_TypeDecorator):
    """Transparent column-level Fernet encryption.

    Encrypts on write (bind param) and decrypts on read (result value), so the
    mapped attribute keeps its name and ordinary reads -- including
    ``select(User.first_name)`` and instance access -- return plaintext without
    touching call sites. Equality/substring/ORDER BY in SQL operate on
    ciphertext and are intentionally NOT supported for encrypted columns; use a
    blind-index hash for lookup and sort/concat app-side.
    """

    impl = _String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt_pii(value)

    def process_result_value(self, value, dialect):
        return decrypt_pii(value)


class EncryptedText(_TypeDecorator):
    """EncryptedString for a TEXT column.

    Same behaviour; the only difference is the underlying type, so a free-text
    column stays TEXT in the database instead of becoming an unbounded VARCHAR
    when it gains encryption. Keeping the declared type and the real column in
    step is what stops a later schema-drift check reporting a change nobody
    made. Ciphertext is longer than plaintext, and TEXT has no length to widen.
    """

    impl = _Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt_pii(value)

    def process_result_value(self, value, dialect):
        return decrypt_pii(value)


class EncryptedDate(_TypeDecorator):
    """Transparent Fernet encryption for a date column.

    Stored as the Fernet ciphertext of the ISO date string; reads return a
    datetime.date. Equality/ordering/extract in SQL operate on ciphertext and
    are not supported -- derive a boolean column (e.g. under_18) for filtering.
    """

    impl = _String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        iso = value.isoformat() if hasattr(value, "isoformat") else str(value)
        return encrypt_pii(iso)

    def process_result_value(self, value, dialect):
        plain = decrypt_pii(value)
        if not plain:
            return None
        from datetime import date

        try:
            return date.fromisoformat(plain)
        except ValueError:
            return None


def hash_pii(value: str, *, field: str = "") -> str:
    from .config import get_settings

    settings = get_settings()
    # PII_HASH_KEY is required whenever PII encryption is enabled (enforced in
    # Settings.validate_pii_encryption_config), so in production the blind index
    # always keys on the dedicated hash secret. The secret_key fallback only
    # applies in dev/test, where PII encryption is disabled.
    hash_key = settings.pii_hash_key or settings.secret_key
    key = f"{hash_key}:pii:{field}".encode()
    return hmac.new(key, value.lower().strip().encode(), hashlib.sha256).hexdigest()


def _get_token_fernet():
    from cryptography.fernet import Fernet
    from .config import get_settings

    settings = get_settings()
    # Dedicated token-encryption key so stored vendor API credentials are not
    # encrypted under the same secret that signs sessions. Falls back to
    # secret_key only in dev/test (TOKEN_ENCRYPTION_KEY unset); no tokens were
    # ever encrypted under the old secret_key derivation.
    key_material = settings.token_encryption_key or settings.secret_key
    key_bytes = hashlib.sha256(key_material.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_token(plaintext: str) -> str:
    f = _get_token_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    from cryptography.fernet import InvalidToken

    try:
        f = _get_token_fernet()
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return ciphertext
