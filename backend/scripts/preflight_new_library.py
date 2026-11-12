# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Verify a fresh import landed correctly before public cutover.

Checks:
  1. Catalog count >= --min-items (default 100)
  2. Unified search for a known title returns at least 1 result
  3. A sample patron exists, has email_verified=True, and has a non-null
     reset_token + future-dated reset_token_expires

Exit codes:
  0  all green
  1  catalog gate failed
  2  search gate failed
  3  patron gate failed
  4+ multiple gates failed (sum of above codes printed)

Usage:
    python -m scripts.preflight_new_library --sample-title "Gatsby" \
        --sample-email ada@example.org --min-items 100
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.catalog import CatalogItem
from app.models.user import User


async def _check_catalog_count(db, min_items: int) -> tuple[bool, str]:
    total = (await db.execute(select(func.count(CatalogItem.id)))).scalar() or 0
    if total < min_items:
        return False, f"catalog has {total} items, expected >= {min_items}"
    return True, f"catalog OK: {total} items"


async def _check_unified_search(db, sample_title: str) -> tuple[bool, str]:
    from app.services.unified_search_service import UnifiedSearchService
    svc = UnifiedSearchService(db)
    results = await svc.search(query=sample_title)
    total = getattr(results, "total_results", None) or getattr(results, "total", 0)
    if not total:
        return False, f"search for {sample_title!r} returned 0 results"
    return True, f"search OK: {total} results for {sample_title!r}"


async def _check_sample_patron(db, sample_email: str) -> tuple[bool, str]:
    user = (await db.execute(
        select(User).where(User.email == sample_email)
    )).scalar_one_or_none()
    if user is None:
        return False, f"sample patron {sample_email!r} not found"
    if not user.email_verified:
        return False, f"sample patron {sample_email!r} email_verified=False"
    if not user.reset_token:
        return False, f"sample patron {sample_email!r} has no reset_token"
    expires = user.reset_token_expires
    if expires is None or expires <= datetime.now(timezone.utc):
        return False, f"sample patron {sample_email!r} reset_token already expired"
    return True, f"sample patron OK: {sample_email}"


async def main(args: argparse.Namespace) -> int:
    failures = 0
    async with AsyncSessionLocal() as db:
        for code, (ok, msg) in [
            (1, await _check_catalog_count(db, args.min_items)),
            (2, await _check_unified_search(db, args.sample_title)),
            (3, await _check_sample_patron(db, args.sample_email)),
        ]:
            print(("PASS " if ok else "FAIL ") + msg)
            if not ok:
                failures += code
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-items", type=int, default=100)
    parser.add_argument("--sample-title", required=True)
    parser.add_argument("--sample-email", required=True)
    a = parser.parse_args()
    sys.exit(asyncio.run(main(a)))
