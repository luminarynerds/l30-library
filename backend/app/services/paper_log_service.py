# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.reading import (
    ReadingLogEntry,
    ReadingProgram,
    ReadingRegistration,
)


CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # avoid 0/O/1/I confusion
CODE_LEN = 8


def _generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LEN))


async def generate_or_get_code(
    db: AsyncSession, registration: ReadingRegistration
) -> str:
    if (
        registration.paper_log_code
        and registration.paper_log_code_redeemed_at is None
    ):
        return registration.paper_log_code

    # Retry-on-collision; partial unique index enforces uniqueness across
    # all unredeemed codes.
    for _ in range(8):
        candidate = _generate_code()
        registration.paper_log_code = candidate
        registration.paper_log_code_generated_at = datetime.now(timezone.utc)
        registration.paper_log_code_redeemed_at = None
        try:
            await db.commit()
            await db.refresh(registration)
            return candidate
        except IntegrityError:
            await db.rollback()
            # re-fetch to keep session clean
            await db.refresh(registration)
    raise RuntimeError("Failed to allocate unique paper log code after 8 attempts")


async def force_regenerate_code(
    db: AsyncSession, registration: ReadingRegistration
) -> str:
    registration.paper_log_code = None
    registration.paper_log_code_generated_at = None
    registration.paper_log_code_redeemed_at = None
    await db.commit()
    await db.refresh(registration)
    return await generate_or_get_code(db, registration)


async def redeem_code(
    db: AsyncSession,
    code: str,
    entries: List[dict],
) -> Tuple[ReadingRegistration, ReadingProgram, List[ReadingLogEntry]]:
    code_norm = (code or "").strip().upper()
    if len(code_norm) != CODE_LEN:
        raise ValueError("not_found")

    result = await db.execute(
        select(ReadingRegistration).where(
            ReadingRegistration.paper_log_code == code_norm
        )
    )
    registration = result.scalar_one_or_none()
    if registration is None:
        raise ValueError("not_found")

    if registration.paper_log_code_redeemed_at is not None:
        raise ValueError("already_redeemed")

    program = await db.get(ReadingProgram, registration.program_id)
    if program is None:
        raise ValueError("not_found")

    # Expiry: program end + 30d.
    from datetime import date as _date, timedelta

    expiry_cutoff = program.end_date + timedelta(days=30)
    if _date.today() > expiry_cutoff:
        raise ValueError("expired")

    # Validate entry dates against program window.
    for e in entries:
        d = e["entry_date"]
        if d < program.start_date or d > program.end_date:
            raise ValueError("invalid_entry")
        if e.get("minutes_read", 0) > 120:
            raise ValueError("invalid_entry")

    created: List[ReadingLogEntry] = []
    for e in entries:
        row = ReadingLogEntry(
            registration_id=registration.id,
            books_read=e.get("books_read", 0) or 0,
            minutes_read=e.get("minutes_read", 0) or 0,
            pages_read=e.get("pages_read", 0) or 0,
            title=e.get("title"),
            author=e.get("author"),
            notes=e.get("notes"),
            source="paper_log",
            # logged_at defaults via server_default (redemption time);
            # entry_date preserves the date the patron wrote on paper
            # so daily-progress analytics reflect actual reading days.
            entry_date=e["entry_date"],
        )
        db.add(row)
        created.append(row)

    registration.paper_log_code_redeemed_at = datetime.now(timezone.utc)
    await db.commit()
    for row in created:
        await db.refresh(row)
    await db.refresh(registration)
    return registration, program, created
