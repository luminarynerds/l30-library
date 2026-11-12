#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Debug LSC data visibility issues caused by date filters."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def _extract_filter_lines(path: Path, patterns: list[str]) -> list[str]:
    lines = path.read_text().splitlines()
    out: list[str] = []
    for i, line in enumerate(lines, start=1):
        if any(p in line for p in patterns):
            out.append(f"L{i}: {line.rstrip()}")
    return out


def _scan_hardcoded_dates(path: Path) -> list[str]:
    text = path.read_text()
    matches = re.findall(r"(date\(20\d{2},\s*\d{1,2},\s*\d{1,2}\)|'20\d{2}-\d{2}-\d{2}')", text)
    seen = set()
    uniq = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            uniq.append(m)
    return uniq


async def _run_db_checks(now: datetime) -> None:
    try:
        from sqlalchemy import func, select
        from app.core.database import AsyncSessionLocal
        from app.models.announcements import Announcement
        from app.models.event import Event
        from app.models.reading import ReadingProgram
    except Exception as exc:
        print(f"  WARNING: DB checks unavailable (imports failed: {type(exc).__name__}: {exc})")
        print("  Install backend dependencies / run in backend container to query live missing records.")
        return

    try:
        async with AsyncSessionLocal() as db:
            past_events_q = select(Event.id, Event.title, Event.start_time, Event.created_at, Event.is_published).where(
                Event.is_published == True,
                Event.start_time < now,
            ).order_by(Event.start_time.desc()).limit(10)
            future_events_q = select(func.count(Event.id)).where(Event.start_time > now)

            past_events = (await db.execute(past_events_q)).all()
            future_events = (await db.execute(future_events_q)).scalar() or 0

            print(f"  Future event start_time count: {future_events}")
            print("  Past published events (hidden when upcoming=true):")
            if not past_events:
                print("    - none")
            for row in past_events:
                print(f"    - Event#{row.id} | {row.title} | start_time={row.start_time} | created_at={row.created_at} | is_published={row.is_published}")

            expired_ann_q = select(
                Announcement.id,
                Announcement.title,
                Announcement.starts_at,
                Announcement.ends_at,
                Announcement.created_at,
                Announcement.active,
            ).where(
                Announcement.active == True,
                Announcement.ends_at.is_not(None),
                Announcement.ends_at <= now,
            ).order_by(Announcement.ends_at.desc()).limit(10)
            expired = (await db.execute(expired_ann_q)).all()

            print("  Expired active announcements (ends_at <= now):")
            if not expired:
                print("    - none")
            for row in expired:
                print(f"    - Announcement#{row.id} | {row.title} | starts_at={row.starts_at} | ends_at={row.ends_at} | created_at={row.created_at} | active={row.active}")

            future_programs_q = select(
                ReadingProgram.id,
                ReadingProgram.name,
                ReadingProgram.start_date,
                ReadingProgram.end_date,
                ReadingProgram.created_at,
                ReadingProgram.is_active,
            ).where(ReadingProgram.start_date > now.date()).order_by(ReadingProgram.start_date.asc()).limit(10)
            future_programs = (await db.execute(future_programs_q)).all()
            print("  Future reading programs (start_date > today):")
            if not future_programs:
                print("    - none")
            for row in future_programs:
                print(f"    - Program#{row.id} | {row.name} | start_date={row.start_date} | end_date={row.end_date} | created_at={row.created_at} | is_active={row.is_active}")

            samples_q = select(Event.id, Event.start_time, Event.created_at).limit(20)
            samples = (await db.execute(samples_q)).all()
            naive_start = sum(1 for r in samples if r.start_time and r.start_time.tzinfo is None)
            naive_created = sum(1 for r in samples if r.created_at and r.created_at.tzinfo is None)
            print(f"  Timezone sample check (20 events): naive start_time={naive_start}, naive created_at={naive_created}")
            print("  publish_date field check: No publish_date column found on Event/Announcement/ReadingProgram models.")
            print("  expired_at field check: No expired_at column found on Event/Announcement models (uses ends_at).")

    except Exception as exc:
        print(f"  WARNING: DB checks skipped ({type(exc).__name__}: {exc})")


async def main() -> None:
    now = datetime.now(timezone.utc)
    print("=" * 88)
    print("LSC DATE FILTER DEBUG")
    print(f"Now (UTC): {now.isoformat()}")
    print("=" * 88)

    events_api = ROOT / "backend/app/api/v1/events.py"
    announcements_api = ROOT / "backend/app/api/v1/announcements.py"

    print("\n[4] Current filter logic (upcoming-only / active-only defaults)")
    print("- events.py")
    for line in _extract_filter_lines(events_api, ["upcoming: bool = Query(True", "if upcoming:", "Event.start_time >= now", "Event.is_published == True"]):
        print(f"  {line}")

    print("- announcements.py")
    for line in _extract_filter_lines(announcements_api, ["active_only: bool = Query(", "default=True", "Announcement.starts_at <= now", "Announcement.ends_at > now", "Announcement.active == True"]):
        print(f"  {line}")

    print("\n[5] created_at filters that could hide old seed data")
    created_filters = _extract_filter_lines(events_api, ["created_at >=", "created_at >", "created_at <=", "created_at <"])
    created_filters += _extract_filter_lines(announcements_api, ["created_at >=", "created_at >", "created_at <=", "created_at <"])
    if created_filters:
        for line in created_filters:
            print(f"  {line}")
    else:
        print("  No created_at WHERE filters found in events/announcements list endpoints.")

    print("\n[7] Hardcoded seed dates that may now be stale")
    seed_files = [
        ROOT / "backend/app/seeds/seed_reading_programs_complete.py",
        ROOT / "backend/app/seeds/seed_reading_programs_full.py",
        ROOT / "backend/app/seeds/seed_new_features.py",
    ]
    for sf in seed_files:
        vals = _scan_hardcoded_dates(sf)
        if vals:
            print(f"  {sf.relative_to(ROOT)}")
            for v in vals[:12]:
                print(f"    - {v}")
            if len(vals) > 12:
                print(f"    ... +{len(vals)-12} more")

    print("\n[1][2][3][6] Live record checks (if DB is available)")
    await _run_db_checks(now)


if __name__ == "__main__":
    asyncio.run(main())
