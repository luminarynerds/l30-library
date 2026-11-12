# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import asyncio
import sys
from datetime import datetime

from app.core.database import AsyncSessionLocal
from app.services.marc_batch_service import MarcBatchService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="export_marc",
        description="Export catalog records as MARC21 or MARCXML to stdout.",
    )
    parser.add_argument(
        "--format",
        choices=["marc21", "marcxml"],
        default="marc21",
        help="Output format (default: marc21).",
    )
    parser.add_argument(
        "--item-type",
        default=None,
        help="Filter by item type (e.g. book, dvd, audiobook).",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="ISO date; only export items updated on/after this date.",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=0,
        help="User id to attribute the export job to (default: 0).",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    incremental_since = (
        datetime.fromisoformat(args.since) if args.since else None
    )

    async with AsyncSessionLocal() as session:
        svc = MarcBatchService(session)
        _, file_bytes = await svc.generate_export(
            file_format=args.format,
            user_id=args.user_id,
            item_type=args.item_type,
            incremental_since=incremental_since,
        )
        await session.commit()

    sys.stdout.buffer.write(file_bytes)


if __name__ == "__main__":
    asyncio.run(main())
