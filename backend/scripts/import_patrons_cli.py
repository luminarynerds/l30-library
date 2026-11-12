# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Import a patron roster from CSV into the L30 users table.

Each row creates a User with email_verified=True and a one-time reset token.
The token is returned (not stored in plaintext anywhere) so callers can email
a "set your password" link to the patron.

Idempotent on re-run: rows whose email already exists are skipped.

Usage:
    python -m scripts.import_patrons_cli --csv patrons.csv --dry-run
    python -m scripts.import_patrons_cli --csv patrons.csv --send-emails

CSV columns (header row required). Matches backend/app/templates/import_templates/patron_import_template.csv:
    name (required), email (required), barcode, phone, address, patron_type, home_branch

    Legacy alternative: first_name + last_name in place of name -- both forms
    accepted by ImportService._create_patron.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User, email_blind_hash
from app.services.import_service.service import ImportService

logger = logging.getLogger("import_patrons_cli")


@dataclass
class ImportResult:
    created: int = 0
    skipped_existing: int = 0
    failed: int = 0
    tokens: list[tuple[str, str]] = field(default_factory=list)  # (email, plaintext)
    errors: list[str] = field(default_factory=list)


async def import_patrons(db, csv_path: Path, dry_run: bool) -> ImportResult:
    """Import patrons from a CSV file. Returns counts + tokens for emailing."""
    result = ImportResult()

    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    for idx, row in enumerate(rows, start=2):  # row 1 is header
        email = (row.get("email") or "").strip().lower()
        if not email:
            result.failed += 1
            result.errors.append(f"row {idx}: missing email")
            continue

        # Idempotency: skip if user with this email already exists (email is
        # encrypted; dedup via the email_hash blind index).
        existing = await db.execute(select(User.id).where(User.email_hash == email_blind_hash(email)))
        if existing.scalar_one_or_none() is not None:
            result.skipped_existing += 1
            continue

        if dry_run:
            result.created += 1
            continue

        try:
            user_id, _table, reset_token = await ImportService._create_patron(
                db, {**row, "email": email}
            )
            result.created += 1
            result.tokens.append((email, reset_token))
        except Exception as exc:
            result.failed += 1
            result.errors.append(f"row {idx} ({email}): {exc}")
            logger.warning("row %d failed: %s", idx, exc, exc_info=True)

    if not dry_run:
        await db.commit()

    return result


async def send_welcome_emails(
    tokens: list[tuple[str, str]], rate_per_minute: int = 30
) -> int:
    """Email a "set your password" link per token. Throttled to respect the
    Resend daily cap. Returns the number of emails the worker accepted."""
    from app.core.email import send_password_reset_email

    sent = 0
    delay = 60.0 / rate_per_minute
    for email, token in tokens:
        try:
            await send_password_reset_email(email, token, None)
            sent += 1
        except Exception as exc:
            logger.warning("welcome email to %s failed: %s", email, exc)
        await asyncio.sleep(delay)
    return sent


async def _main(args: argparse.Namespace) -> int:
    csv_path = Path(args.csv)
    if not csv_path.is_file():
        print(f"error: {csv_path} not found", file=sys.stderr)
        return 2

    async with AsyncSessionLocal() as db:
        result = await import_patrons(db, csv_path, dry_run=args.dry_run)

    print(f"created={result.created} skipped_existing={result.skipped_existing} "
          f"failed={result.failed}")
    for err in result.errors[:20]:
        print(f"  ERROR: {err}", file=sys.stderr)

    if args.dry_run:
        return 0
    if args.send_emails and result.tokens:
        sent = await send_welcome_emails(result.tokens, rate_per_minute=args.rate)
        print(f"welcome_emails_sent={sent}")
    elif result.tokens:
        # Print the (email, token) pairs to stdout so the operator can email
        # them via their own process. Tokens are single-use + expiring.
        for email, token in result.tokens:
            print(f"TOKEN {email} {token}")
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="Import patrons from CSV")
    parser.add_argument("--csv", required=True, help="Path to patron CSV")
    parser.add_argument("--dry-run", action="store_true", help="Count + skip writes")
    parser.add_argument("--send-emails", action="store_true",
                        help="Send welcome emails after import (throttled)")
    parser.add_argument("--rate", type=int, default=30,
                        help="Max welcome emails per minute (default 30)")
    args = parser.parse_args()
    return asyncio.run(_main(args))


if __name__ == "__main__":
    sys.exit(main())
