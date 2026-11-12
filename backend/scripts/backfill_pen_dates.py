#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Backfill date_reported on PEN America ban reports imported before the
month-precision date fix.

PEN publishes the challenge date at month granularity ("August 2023"). The
parser accepted only day-precision formats, so every imported row landed with
date_reported NULL -- 10,046 of 10,091 rows in production. Fixing the parser
does not repair those rows: PenAmericaSyncService._deduplicate skips any record
whose (title, author, state, district) already exists and never updates it, so
without this backfill the existing rows stay NULL forever.

Rows are matched on the same key _deduplicate uses. In PEN's published 2023-24
sheet that key is unique across all 10,046 rows and each key carries exactly one
date, so the match is unambiguous (verified 2026-08-04).

Only rows where date_reported IS NULL are touched. Nothing else is modified.

Run via:
    docker compose exec backend python scripts/backfill_pen_dates.py --dry-run
    docker compose exec backend python scripts/backfill_pen_dates.py --apply
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import select, update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.services.pen_america_sync_service as pen_svc  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.models.ban_tracker import BanReport, BanSource  # noqa: E402
from app.services.pen_america_sync_service import (  # noqa: E402
    PenAmericaSyncService,
    parse_csv_records,
)


def _install_month_precision_compat() -> bool:
    """Teach an unpatched running image to read PEN's month-precision dates.

    This backfill has to be runnable against a backend image built before the
    parser fix, because scripts/ is bind-mounted into the container while the
    application code is baked in. Against an old image the imported _parse_date
    returns None for every PEN date and the backfill would silently update
    nothing.

    parse_csv_records resolves _parse_date as a module global, so replacing the
    module attribute is enough. Once the fixed parser is deployed the wrapped
    call already succeeds and this shim never fires.

    Returns True if the shim is doing real work (i.e. the image is unpatched).
    """
    original = pen_svc._parse_date
    if original("August 2023") is not None:
        return False

    def _with_month_precision(raw: str):
        parsed = original(raw)
        if parsed is not None:
            return parsed
        raw = raw.strip()
        for fmt in ("%B %Y", "%b %Y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        return None

    pen_svc._parse_date = _with_month_precision
    return True


async def load_records(csv_path: str | None) -> list[dict]:
    if csv_path:
        text = Path(csv_path).read_text(encoding="utf-8", errors="replace")
        return parse_csv_records(text)
    return await PenAmericaSyncService._fetch_data()


async def backfill(
    session: AsyncSession,
    records: list[dict],
    apply: bool,
    touched: list[tuple[int, str]] | None = None,
) -> dict:
    """Set date_reported on PEN rows that have none.

    touched, if given, collects (row id, ISO date) for every row this would
    write, so an --apply run leaves a record precise enough to reverse.
    """
    stats = {
        "records_with_date": 0,
        "records_without_date": 0,
        "matched_null_rows": 0,
        "no_match": 0,
        "already_dated": 0,
        "updated": 0,
    }

    for record in records:
        parsed = record.get("date_reported")
        if parsed is None:
            stats["records_without_date"] += 1
            continue
        stats["records_with_date"] += 1

        result = await session.execute(
            select(BanReport.id, BanReport.date_reported).where(
                BanReport.source == BanSource.PEN_AMERICA,
                BanReport.title == record.get("title", ""),
                BanReport.author == record.get("author", "Unknown"),
                BanReport.state == (record.get("state") or None),
                BanReport.district == (record.get("district") or None),
            )
        )
        rows = result.all()
        if not rows:
            stats["no_match"] += 1
            continue

        null_ids = [r.id for r in rows if r.date_reported is None]
        if not null_ids:
            stats["already_dated"] += 1
            continue

        stats["matched_null_rows"] += len(null_ids)
        if touched is not None:
            touched.extend((row_id, parsed.isoformat()) for row_id in null_ids)
        if apply:
            await session.execute(
                update(BanReport).where(BanReport.id.in_(null_ids)).values(date_reported=parsed)
            )
            stats["updated"] += len(null_ids)

    if apply:
        await session.commit()
    return stats


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    group.add_argument("--apply", action="store_true", help="write the dates")
    parser.add_argument("--csv", help="read a local CSV instead of fetching the sheet")
    parser.add_argument(
        "--id-log",
        help="write every (id,date) this run would set, so an --apply is reversible",
    )
    args = parser.parse_args()

    if _install_month_precision_compat():
        print("running against an unpatched image: month-precision compat shim active")

    records = await load_records(args.csv)
    print(f"parsed {len(records)} records from source")
    if not records:
        print("no records parsed -- refusing to proceed")
        return 1

    engine = create_async_engine(get_settings().database_url, echo=False)
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with maker() as session:
        before = await session.execute(
            select(BanReport.id).where(
                BanReport.source == BanSource.PEN_AMERICA,
                BanReport.date_reported.is_(None),
            )
        )
        null_before = len(before.all())
        print(f"pen_america rows with NULL date_reported before: {null_before}")

        touched: list[tuple[int, str]] = []
        stats = await backfill(session, records, apply=args.apply, touched=touched)

        after = await session.execute(
            select(BanReport.id).where(
                BanReport.source == BanSource.PEN_AMERICA,
                BanReport.date_reported.is_(None),
            )
        )
        null_after = len(after.all())

    await engine.dispose()

    if args.id_log:
        Path(args.id_log).write_text(
            "".join(f"{row_id},{iso}\n" for row_id, iso in touched), encoding="utf-8"
        )
        print(f"wrote {len(touched)} affected row ids to {args.id_log}")

    for key, value in stats.items():
        print(f"  {key}: {value}")
    print(f"pen_america rows with NULL date_reported after: {null_after}")
    if not args.apply:
        print("\nDRY RUN -- nothing was written. Re-run with --apply to commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
