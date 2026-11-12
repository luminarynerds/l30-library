# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for scripts/reencrypt_pii.py.

Covers finding C1 (2026-07-04 Fernet/PII audit): the key-rotation script
hardcoded PII_COLUMNS and silently skipped email/first_name/last_name/
date_of_birth, which are encrypted through EncryptedString/EncryptedDate
TypeDecorators rather than the EncryptedPIIField descriptor pattern the
original PII_COLUMNS list was built for.

- TestColumnCoverage is a regression guard: it introspects the actual User
  model for every encrypted attribute and asserts the script's column lists
  stay in sync, so a future PII column added to User can't silently slip
  past rotation again the way email/first_name/last_name/date_of_birth did.
- TestRotationHelpers exercises the pure decrypt/rotate helpers directly
  (no DB) covering: already-current-key (skip), previous-key (rotate),
  and undecryptable (raise -> caller logs + counts as failed).
"""

import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet, InvalidToken

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND / "scripts") not in sys.path:
    sys.path.insert(0, str(BACKEND / "scripts"))

from reencrypt_pii import (  # noqa: E402
    PII_COLUMNS,
    TRANSPARENT_DATE_COLUMN,
    TRANSPARENT_STRING_COLUMNS,
    _needs_rotation,
    _rotate_transparent_date,
    _rotate_transparent_string,
)


@pytest.mark.unit
class TestColumnCoverage:
    """Regression guard: script column lists vs. actual encrypted User columns."""

    def test_pii_columns_cover_every_encrypted_pii_field_descriptor(self):
        from app.core.encryption import EncryptedPIIField
        from app.models.user import User

        expected = {
            attr.storage_attr
            for attr in vars(User).values()
            if isinstance(attr, EncryptedPIIField)
        }
        assert set(PII_COLUMNS) == expected, (
            "scripts/reencrypt_pii.py's PII_COLUMNS is out of sync with "
            "User's EncryptedPIIField columns -- a rotation run would "
            "silently skip whatever's missing here."
        )

    def test_transparent_columns_cover_every_typedecorator_column(self):
        from sqlalchemy import inspect as sa_inspect

        from app.core.encryption import EncryptedDate, EncryptedString
        from app.models.user import User

        mapper = sa_inspect(User)
        string_cols = set()
        date_cols = set()
        for col in mapper.columns:
            if isinstance(col.type, EncryptedString):
                string_cols.add(col.key)
            elif isinstance(col.type, EncryptedDate):
                date_cols.add(col.key)

        assert set(TRANSPARENT_STRING_COLUMNS) == string_cols, (
            "scripts/reencrypt_pii.py's TRANSPARENT_STRING_COLUMNS is out of "
            "sync with User's EncryptedString columns."
        )
        assert date_cols == {TRANSPARENT_DATE_COLUMN}, (
            "scripts/reencrypt_pii.py assumes a single EncryptedDate column "
            "(TRANSPARENT_DATE_COLUMN) -- update the rotation logic if "
            "another one was added."
        )


@pytest.mark.unit
class TestRotationHelpers:
    """Pure decrypt/rotate helpers for the TypeDecorator-backed columns."""

    @pytest.fixture
    def keys(self):
        return Fernet.generate_key(), Fernet.generate_key()

    def test_needs_rotation_false_for_current_key(self, keys):
        new_key, _old_key = keys
        fernet_new = Fernet(new_key)
        ciphertext = fernet_new.encrypt(b"already@current.example").decode()
        assert _needs_rotation(ciphertext, fernet_new) is False

    def test_needs_rotation_true_for_previous_key(self, keys):
        new_key, old_key = keys
        fernet_new = Fernet(new_key)
        fernet_old = Fernet(old_key)
        ciphertext = fernet_old.encrypt(b"stale@previous.example").decode()
        assert _needs_rotation(ciphertext, fernet_new) is True

    def test_rotate_transparent_string_round_trips_plaintext(self, keys):
        _new_key, old_key = keys
        fernet_old = Fernet(old_key)
        ciphertext = fernet_old.encrypt(b"patron@example.org").decode()
        assert _rotate_transparent_string(ciphertext, fernet_old) == "patron@example.org"

    def test_rotate_transparent_string_raises_when_undecryptable(self, keys):
        _new_key, old_key = keys
        fernet_old = Fernet(old_key)
        garbage_ciphertext = Fernet(Fernet.generate_key()).encrypt(b"x").decode()
        with pytest.raises(InvalidToken):
            _rotate_transparent_string(garbage_ciphertext, fernet_old)

    def test_rotate_transparent_date_parses_iso_string(self, keys):
        _new_key, old_key = keys
        fernet_old = Fernet(old_key)
        ciphertext = fernet_old.encrypt(b"2015-03-14").decode()
        result = _rotate_transparent_date(ciphertext, fernet_old)
        from datetime import date

        assert result == date(2015, 3, 14)

    def test_rotate_transparent_date_raises_when_undecryptable(self, keys):
        _new_key, old_key = keys
        fernet_old = Fernet(old_key)
        garbage_ciphertext = Fernet(Fernet.generate_key()).encrypt(b"x").decode()
        with pytest.raises(InvalidToken):
            _rotate_transparent_date(garbage_ciphertext, fernet_old)
