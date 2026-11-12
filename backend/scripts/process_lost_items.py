#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Lost Item Detection Script

This script identifies items that have been overdue for an extended period
(default 30+ days) and marks them as lost. It can be run manually or
scheduled as a cron job.

When an item is marked lost:
- The checkout status is updated to "lost"
- The catalog item status is updated to "lost"
- A "lost item" fine is created for the patron (replacement cost)
- Optionally, the patron is notified via email

Usage:
    # Preview items that would be marked lost (dry run)
    python scripts/process_lost_items.py --dry-run

    # Process lost items with notifications
    python scripts/process_lost_items.py

    # Process with custom threshold (45 days instead of default 30)
    python scripts/process_lost_items.py --threshold-days 45

    # Process without sending email notifications
    python scripts/process_lost_items.py --no-notifications

    # Process with custom replacement cost
    python scripts/process_lost_items.py --replacement-cost 50.00

Cron Job Setup:
    # Run daily at 2 AM
    0 2 * * * cd /path/to/backend && python scripts/process_lost_items.py >> /var/log/lost_items.log 2>&1

    # Run weekly on Sunday at 3 AM
    0 3 * * 0 cd /path/to/backend && python scripts/process_lost_items.py >> /var/log/lost_items.log 2>&1
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.services.lost_item_service import process_lost_items, get_lost_item_candidates_count

settings = get_settings()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@database:5432/lsc_library"
)

engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def log(message: str):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


async def main(args: argparse.Namespace):
    """Main function to process lost items."""
    log("=" * 60)
    log("Lost Item Detection Script")
    log("=" * 60)

    threshold_days = args.threshold_days or settings.lost_item_threshold_days
    replacement_cost = (
        Decimal(str(args.replacement_cost))
        if args.replacement_cost
        else None
    )
    send_notifications = not args.no_notifications
    dry_run = args.dry_run

    log("Configuration:")
    log(f"  - Threshold days: {threshold_days}")
    log(f"  - Replacement cost: ${replacement_cost or settings.lost_item_default_replacement_cost:.2f}")
    log(f"  - Send notifications: {send_notifications}")
    log(f"  - Dry run: {dry_run}")
    log("")

    async with async_session() as db:
        # First, get a count of candidates
        candidate_count = await get_lost_item_candidates_count(db, threshold_days)

        if candidate_count == 0:
            log("No items found that are overdue beyond the threshold.")
            log("Script completed successfully.")
            return 0

        log(f"Found {candidate_count} item(s) overdue for {threshold_days}+ days.")

        if dry_run:
            log("")
            log("DRY RUN - No changes will be made.")

        log("")
        log("Processing lost items...")

        # Process the lost items
        report = await process_lost_items(
            db=db,
            threshold_days=threshold_days,
            replacement_cost=replacement_cost,
            send_notifications=send_notifications,
            dry_run=dry_run,
        )

        log("")
        log("=" * 60)
        log("Processing Report")
        log("=" * 60)
        log(f"Items processed: {report.processed_count}")
        log(f"Total fines amount: ${report.total_fines_amount:.2f}")

        if send_notifications:
            log(f"Notifications sent: {report.notifications_sent}")
            log(f"Notifications failed: {report.notifications_failed}")

        if report.items:
            log("")
            log("Processed Items:")
            for item in report.items:
                status = "[DRY RUN]" if dry_run else "[PROCESSED]"
                notification_status = ""
                if send_notifications:
                    if item.notification_sent:
                        notification_status = " (notification sent)"
                    elif item.patron_email:
                        notification_status = " (notification failed)"
                    else:
                        notification_status = " (no email on file)"

                log(f"  {status} {item.item_title}")
                log(f"           Patron: {item.patron_name} ({item.patron_email or 'no email'})")
                log(f"           Days overdue: {item.days_overdue}")
                log(f"           Fine: ${item.fine_amount:.2f}{notification_status}")

        if report.errors:
            log("")
            log("Errors:")
            for error in report.errors:
                log(f"  - {error}")

        log("")
        if dry_run:
            log("DRY RUN COMPLETE - No changes were made to the database.")
        else:
            log("Script completed successfully.")

        return 0 if not report.errors else 1


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Process overdue items and mark them as lost.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what would happen (dry run)
  python scripts/process_lost_items.py --dry-run

  # Process with default settings
  python scripts/process_lost_items.py

  # Process with custom threshold (45 days)
  python scripts/process_lost_items.py --threshold-days 45

  # Process without email notifications
  python scripts/process_lost_items.py --no-notifications
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would happen without making changes",
    )

    parser.add_argument(
        "--threshold-days",
        type=int,
        help=f"Days overdue before marking as lost (default: {settings.lost_item_threshold_days})",
    )

    parser.add_argument(
        "--replacement-cost",
        type=float,
        help=f"Override replacement cost (default: ${settings.lost_item_default_replacement_cost:.2f})",
    )

    parser.add_argument(
        "--no-notifications",
        action="store_true",
        help="Skip sending email notifications to patrons",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    exit_code = asyncio.run(main(args))
    sys.exit(exit_code)
