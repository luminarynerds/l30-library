#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Mark ban-tracker-matched catalog items as CATALOGED.

The ban tracker's "In Our Collection" section exists to show that the library
carries challenged books. The items behind it were created with the model
default cataloging_status=UNCATALOGED (models/catalog.py), which makes
/catalog/{id} 404 for anonymous visitors, so the covers linked nowhere.

get_all_catalog_matches now refuses to offer items the public cannot open, so
without this the section renders almost empty. This promotes exactly the items
a ban report already points at, and nothing else.

Only rows that are currently not CATALOGED are touched. sensitivity_level is
left alone: an item deliberately marked SENSITIVE or CONFIDENTIAL stays hidden,
and the query filter keeps it out of the public list.

Run via:
    docker compose exec backend python scripts/catalog_banned_matches.py --dry-run
    docker compose exec backend python scripts/catalog_banned_matches.py --apply
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import select, update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.models.ban_tracker import BanReport  # noqa: E402
from app.models.catalog import CatalogingStatus, CatalogItem  # noqa: E402


async def find_targets(session: AsyncSession) -> list[tuple[int, str, str]]:
    result = await session.execute(
        select(CatalogItem.id, CatalogItem.title, CatalogItem.cataloging_status)
        .join(BanReport, BanReport.catalog_match_id == CatalogItem.id)
        .where(CatalogItem.cataloging_status != CatalogingStatus.CATALOGED)
        .distinct()
        .order_by(CatalogItem.id)
    )
    return [(r[0], r[1], str(r[2])) for r in result.all()]


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")
    parser.add_argument("--id-log", help="record the ids changed, so this is reversible")
    args = parser.parse_args()

    engine = create_async_engine(get_settings().database_url, echo=False)
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with maker() as session:
        targets = await find_targets(session)
        print(f"catalog items matched by a ban report and not CATALOGED: {len(targets)}")
        for item_id, title, status in targets[:10]:
            print(f"  {item_id}: {title} [{status}]")
        if len(targets) > 10:
            print(f"  ... and {len(targets) - 10} more")

        if args.apply and targets:
            ids = [t[0] for t in targets]
            await session.execute(
                update(CatalogItem)
                .where(CatalogItem.id.in_(ids))
                .values(
                    cataloging_status=CatalogingStatus.CATALOGED,
                    cataloged_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()
            print(f"updated {len(ids)} items to CATALOGED")

        remaining = await find_targets(session)
        print(f"still not CATALOGED after this run: {len(remaining)}")

    await engine.dispose()

    if args.id_log:
        Path(args.id_log).write_text(
            "".join(f"{i},{t},{s}\n" for i, t, s in targets), encoding="utf-8"
        )
        print(f"wrote {len(targets)} ids to {args.id_log}")

    if not args.apply:
        print("\nDRY RUN -- nothing was written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
