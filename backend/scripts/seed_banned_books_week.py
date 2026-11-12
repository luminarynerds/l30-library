#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Seed the Banned Books Week program and booklist. Safe to re-run."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.seeds.banned_books_week import seed_banned_books_week  # noqa: E402


async def main() -> None:
    async with AsyncSessionLocal() as db:
        result = await seed_banned_books_week(db)
    print(
        f"program_created={result['program_created']} "
        f"booklist_added={result['booklist_added']} "
        f"titles_missing={result['titles_missing']}"
    )


if __name__ == "__main__":
    asyncio.run(main())
