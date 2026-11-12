#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Re-encrypt PII fields after encryption key rotation.

Usage:
    # Dry run (shows what would be updated):
    python scripts/reencrypt_pii.py --dry-run

    # Execute re-encryption:
    python scripts/reencrypt_pii.py --execute

Requires PII_ENCRYPTION_KEY (new) and PII_ENCRYPTION_KEY_PREVIOUS (old) to be set.

This script:
1. Connects to the database using the app's async engine.
2. Iterates over every User record, covering all encrypted PII columns:
   phone, addresses, parental/recovery email (EncryptedPIIField descriptor
   columns) plus email, first_name, last_name, date_of_birth (EncryptedString/
   EncryptedDate TypeDecorator columns).
3. For each record, attempts to decrypt with the previous (old) key and
   re-encrypt with the current (new) key.
4. In dry-run mode, just counts records that need re-encryption.
5. In execute mode, updates records in batches of 100 with a commit after
   each batch.
6. Prints a summary of records processed, re-encrypted, already-current,
   and failed.
"""

import argparse
import asyncio
import logging
import re
import sys
from datetime import date
from pathlib import Path

# Ensure the backend package is importable
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 100

# PII columns backed by the EncryptedPIIField descriptor pattern: the raw
# Column stores ciphertext under a "_"-prefixed attribute name, and
# encryption/decryption happens manually in Python (not at the SQLAlchemy
# type level), so getattr(user, col) returns raw ciphertext even after a
# normal ORM load.
PII_COLUMNS = [
    "_phone",
    "_emergency_contact_phone",
    "_estate_contact_phone",
    "_address",
    "_address_line1",
    "_address_line2",
    "_parental_consent_email",
    "_recovery_email",
]

# Columns backed by the EncryptedString/EncryptedDate TypeDecorator instead:
# the ORM transparently decrypts on load and encrypts on write, so
# getattr(user, col) after a normal ORM load already returns PLAINTEXT --
# there is no raw-ciphertext attribute to read via the ORM. Rotation for
# these reads raw ciphertext via an untyped SQL query (`_fetch_transparent_raw`)
# and writes back PLAINTEXT through a Core UPDATE, letting the TypeDecorator
# re-encrypt it under the current key on flush.
TRANSPARENT_STRING_COLUMNS = ["email", "first_name", "last_name"]
TRANSPARENT_DATE_COLUMN = "date_of_birth"


def _needs_rotation(raw_ciphertext: str, fernet_new) -> bool:
    """True if `raw_ciphertext` does NOT already decrypt under the current key."""
    try:
        fernet_new.decrypt(raw_ciphertext.encode())
        return False
    except Exception:
        return True


def _rotate_transparent_string(raw_ciphertext: str, fernet_old) -> str:
    """Decrypt a TRANSPARENT_STRING_COLUMNS value with the previous key.

    Returns plaintext for the caller to write back via a Core-level
    `update().values()` (see `_flush_batch`), NOT an ORM attribute
    assignment -- the EncryptedString TypeDecorator re-encrypts it under the
    current key when that UPDATE is flushed. Do not substitute an ORM
    attribute assignment here: if the decrypted plaintext happens to match
    the in-memory value SQLAlchemy already has loaded, dirty-tracking would
    treat the assignment as a no-op and silently skip the re-encrypt. The
    Core UPDATE always executes regardless of the value. Raises (InvalidToken
    or similar) if the previous key can't decrypt it either.
    """
    return fernet_old.decrypt(raw_ciphertext.encode()).decode()


def _rotate_transparent_date(raw_ciphertext: str, fernet_old) -> date:
    """Same as `_rotate_transparent_string` but for the EncryptedDate
    ISO-string path (date_of_birth): decrypts to an ISO date string with the
    previous key, then parses it to a `date` for the caller to write back
    (same Core-UPDATE path, same ORM-assignment caveat -- see
    `_rotate_transparent_string`).
    """
    iso_plain = fernet_old.decrypt(raw_ciphertext.encode()).decode()
    return date.fromisoformat(iso_plain)


async def reencrypt(dry_run: bool) -> None:
    """Run the re-encryption migration."""
    from cryptography.fernet import Fernet, InvalidToken

    from app.core.config import get_settings

    settings = get_settings()

    if not settings.pii_encryption_key:
        logger.error("PII_ENCRYPTION_KEY is not set. Cannot proceed.")
        sys.exit(1)

    if not settings.pii_encryption_key_previous:
        logger.error(
            "PII_ENCRYPTION_KEY_PREVIOUS is not set. "
            "Set it to the old key so existing data can be decrypted."
        )
        sys.exit(1)

    try:
        fernet_new = Fernet(settings.pii_encryption_key.encode())
    except Exception as e:
        logger.error("Invalid PII_ENCRYPTION_KEY: %s", e)
        sys.exit(1)

    try:
        fernet_old = Fernet(settings.pii_encryption_key_previous.encode())
    except Exception as e:
        logger.error("Invalid PII_ENCRYPTION_KEY_PREVIOUS: %s", e)
        sys.exit(1)

    # Import DB machinery after path setup
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.user import User

    total_processed = 0
    total_reencrypted = 0
    total_already_current = 0
    total_failed = 0

    async with AsyncSessionLocal() as session:
        # email/first_name/last_name are NOT NULL on every User row, so a
        # rotation-complete run has to cover every user, not just the subset
        # with legacy phone/address fields populated.
        result = await session.execute(select(User).order_by(User.id))
        users = result.scalars().all()
        logger.info("Found %d user records to inspect.", len(users))

        transparent_raw = await _fetch_transparent_raw(session)

        batch_updates: list[dict] = []

        for user in users:
            total_processed += 1
            record_changed = False
            failed_columns: list[str] = []
            updates: dict = {}

            for col in PII_COLUMNS:
                value = getattr(user, col, None)
                if value is None:
                    continue

                # 1. Try decrypting with the NEW key -- already current
                try:
                    fernet_new.decrypt(value.encode())
                    continue  # Already encrypted with the new key
                except (InvalidToken, Exception):
                    pass

                # 2. Try decrypting with the OLD key -- needs re-encryption
                try:
                    plaintext = fernet_old.decrypt(value.encode()).decode()
                    new_ciphertext = fernet_new.encrypt(plaintext.encode()).decode()
                    updates[col] = new_ciphertext
                    record_changed = True
                except (InvalidToken, Exception) as e:
                    logger.warning(
                        "User %d: failed to decrypt '%s' with either key: %s",
                        user.id,
                        col,
                        e,
                    )
                    failed_columns.append(col)

            # Populate phone_hash and phone_last4 from decrypted phone
            raw_phone = getattr(user, '_phone', None)
            if raw_phone:
                try:
                    plain_phone = fernet_new.decrypt(raw_phone.encode()).decode() if '_phone' not in updates else fernet_new.decrypt(updates['_phone'].encode()).decode()
                except Exception:
                    try:
                        plain_phone = fernet_old.decrypt(raw_phone.encode()).decode()
                    except Exception:
                        plain_phone = raw_phone  # Unencrypted legacy
                stripped = re.sub(r'\D', '', plain_phone)
                from app.core.encryption import hash_pii
                new_hash = hash_pii(stripped, field='phone')
                new_last4 = stripped[-4:] if len(stripped) >= 4 else stripped
                if user.phone_hash != new_hash or user.phone_last4 != new_last4:
                    updates['phone_hash'] = new_hash
                    updates['phone_last4'] = new_last4
                    record_changed = True

            # email/first_name/last_name: TypeDecorator columns, raw ciphertext
            # came from the separate untyped fetch, not from the ORM object.
            raw_cols = transparent_raw.get(user.id, {})
            for col in TRANSPARENT_STRING_COLUMNS:
                value = raw_cols.get(col)
                if value is None or not _needs_rotation(value, fernet_new):
                    continue

                try:
                    updates[col] = _rotate_transparent_string(value, fernet_old)
                    record_changed = True
                except Exception as e:
                    logger.warning(
                        "User %d: failed to decrypt '%s' with either key: %s",
                        user.id,
                        col,
                        e,
                    )
                    failed_columns.append(col)

            # date_of_birth: EncryptedDate TypeDecorator -- ISO-string handling,
            # not the raw string path the phone/address columns use above.
            dob_value = raw_cols.get(TRANSPARENT_DATE_COLUMN)
            if dob_value is not None and _needs_rotation(dob_value, fernet_new):
                try:
                    updates[TRANSPARENT_DATE_COLUMN] = _rotate_transparent_date(dob_value, fernet_old)
                    record_changed = True
                except Exception as e:
                    logger.warning(
                        "User %d: failed to decrypt '%s' with either key: %s",
                        user.id,
                        TRANSPARENT_DATE_COLUMN,
                        e,
                    )
                    failed_columns.append(TRANSPARENT_DATE_COLUMN)

            if failed_columns:
                # Any column failing means the row is not fully rotated, even
                # if other columns on it succeeded -- those successes are
                # still real and get written back so re-runs converge, but
                # the row must not be counted as clean.
                total_failed += 1
                if not dry_run:
                    batch_updates.append({"user_id": user.id, **updates})
                logger.error(
                    "User %d: PARTIAL rotation, columns %s still on old key "
                    "-- counted as FAILED",
                    user.id,
                    failed_columns,
                )
            elif record_changed:
                total_reencrypted += 1
                if not dry_run:
                    batch_updates.append({"user_id": user.id, **updates})
            else:
                total_already_current += 1

            # Flush batch
            if not dry_run and len(batch_updates) >= BATCH_SIZE:
                await _flush_batch(session, batch_updates)
                batch_updates = []

        # Flush remaining
        if not dry_run and batch_updates:
            await _flush_batch(session, batch_updates)

    mode_label = "DRY RUN" if dry_run else "EXECUTED"
    logger.info("--- Re-encryption summary (%s) ---", mode_label)
    logger.info("  Total records inspected : %d", total_processed)
    logger.info("  Re-encrypted            : %d", total_reencrypted)
    logger.info("  Already on current key  : %d", total_already_current)
    logger.info("  Failed (undecryptable)  : %d", total_failed)

    if dry_run and total_reencrypted > 0:
        logger.info(
            "Run with --execute to apply re-encryption to %d records.",
            total_reencrypted,
        )

    if not dry_run and total_failed > 0:
        logger.error(
            "%d record(s) failed to fully rotate -- do NOT decommission the "
            "old key. See ERROR lines above for the affected users/columns.",
            total_failed,
        )
        sys.exit(1)


async def _fetch_transparent_raw(session) -> dict:
    """Fetch raw (still-encrypted) values for the TypeDecorator-backed columns.

    A plain `select(User)` auto-decrypts these via `process_result_value`, so
    getting the actual ciphertext requires an untyped SQL query that bypasses
    the column's SQLAlchemy type entirely.
    """
    from sqlalchemy import text

    cols = ", ".join(["id", *TRANSPARENT_STRING_COLUMNS, TRANSPARENT_DATE_COLUMN])
    result = await session.execute(text(f"SELECT {cols} FROM users"))
    raw: dict = {}
    for row in result.mappings():
        raw[row["id"]] = dict(row)
    return raw


async def _flush_batch(
    session,
    batch_updates: list[dict],
) -> None:
    """Update a batch of user records and commit."""
    from sqlalchemy import update

    from app.models.user import User

    for entry in batch_updates:
        user_id = entry.pop("user_id")
        if entry:
            stmt = update(User).where(User.id == user_id).values(**entry)
            await session.execute(stmt)

    await session.commit()
    logger.info("  Committed batch of %d records.", len(batch_updates))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-encrypt PII fields after encryption key rotation."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes.",
    )
    group.add_argument(
        "--execute",
        action="store_true",
        help="Execute the re-encryption migration.",
    )
    args = parser.parse_args()

    asyncio.run(reencrypt(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
