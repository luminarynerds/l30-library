#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed data for patron notifications.
Creates sample notifications for testing the live notification system.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.models.user import User

settings = get_settings()


async def seed_patron_notifications():
    """Seed patron notifications with realistic data."""
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("🌱 Creating patron notifications...")

        try:
            # Get first patron user
            result = await session.execute(select(User).where(User.role == "PATRON").limit(1))
            user = result.scalar_one_or_none()

            if not user:
                # Try any user if no patron found
                result = await session.execute(select(User).limit(1))
                user = result.scalar_one_or_none()

            if not user:
                print("❌ No users found. Run bootstrap seed first.")
                return

            patron_id = user.id
            print(f"   Using patron ID: {patron_id}")

            # Check if notifications already exist
            result = await session.execute(
                text("SELECT COUNT(*) FROM patron_notifications WHERE patron_id = :patron_id"),
                {"patron_id": patron_id}
            )
            count = result.scalar()

            if count > 0:
                print(f"✓ Patron notifications already exist ({count} notifications)")
                return

            now = datetime.now(timezone.utc)

            # Define notification data - mix of types, ages, and read states
            notifications = [
                # UNREAD (60%)
                {
                    "category": "HOLD_AVAILABLE",
                    "title": "Your hold is ready for pickup",
                    "message": "The item 'The Midnight Library' is now available. Please pick it up within 7 days.",
                    "source_event_type": "HoldReady",
                    "source_event_id": "hold_ready_001",
                    "is_read": False,
                    "created_at": now - timedelta(hours=2),
                },
                {
                    "category": "FINE_ASSESSED",
                    "title": "Fine assessed on your account",
                    "message": "A fine of $2.50 has been added for overdue item 'Project Hail Mary'.",
                    "source_event_type": "FineAssessed",
                    "source_event_id": "fine_assessed_001",
                    "is_read": False,
                    "created_at": now - timedelta(hours=5),
                },
                {
                    "category": "DUE_DATE_REMINDER",
                    "title": "Items due soon",
                    "message": "You have 2 items due in 2 days. Please return or renew them.",
                    "source_event_type": "DueDateReminder",
                    "source_event_id": "due_reminder_001",
                    "is_read": False,
                    "created_at": now - timedelta(hours=8),
                },
                {
                    "category": "CHECKOUT_RECEIPT",
                    "title": "Items checked out",
                    "message": "You checked out 3 items today. Due in 14 days.",
                    "source_event_type": "CheckoutCompleted",
                    "source_event_id": "checkout_001",
                    "is_read": False,
                    "created_at": now - timedelta(days=1, hours=3),
                },
                {
                    "category": "OVERDUE_NOTICE",
                    "title": "Overdue items on your account",
                    "message": "You have 1 overdue item: 'The Thursday Murder Club'. Please return it.",
                    "source_event_type": "LoanBecameOverdue",
                    "source_event_id": "overdue_001",
                    "is_read": False,
                    "created_at": now - timedelta(days=1, hours=10),
                },
                {
                    "category": "HOLD_EXPIRING",
                    "title": "Your hold expires soon",
                    "message": "The hold for 'Lessons in Chemistry' will expire in 2 days.",
                    "source_event_type": "HoldExpiring",
                    "source_event_id": "hold_expiring_001",
                    "is_read": False,
                    "created_at": now - timedelta(days=7, hours=2),
                },
                {
                    "category": "HOLD_AVAILABLE",
                    "title": "Your hold is ready for pickup",
                    "message": "The item 'Atomic Habits' is available at Northern Branch.",
                    "source_event_type": "HoldReady",
                    "source_event_id": "hold_ready_002",
                    "is_read": False,
                    "created_at": now - timedelta(days=7, hours=8),
                },
                {
                    "category": "FINE_ASSESSED",
                    "title": "Fine assessed on your account",
                    "message": "A fine of $1.00 has been added for overdue item.",
                    "source_event_type": "FineAssessed",
                    "source_event_id": "fine_assessed_002",
                    "is_read": False,
                    "created_at": now - timedelta(days=14, hours=2),
                },
                {
                    "category": "CHECKOUT_RECEIPT",
                    "title": "Items checked out",
                    "message": "You checked out 2 items today.",
                    "source_event_type": "CheckoutCompleted",
                    "source_event_id": "checkout_002",
                    "is_read": False,
                    "created_at": now - timedelta(days=14, hours=9),
                },
                {
                    "category": "OVERDUE_NOTICE",
                    "title": "Overdue items on your account",
                    "message": "You have 2 overdue items. Please return them.",
                    "source_event_type": "LoanBecameOverdue",
                    "source_event_id": "overdue_002",
                    "is_read": False,
                    "created_at": now - timedelta(days=14, hours=16),
                },
                {
                    "category": "HOLD_AVAILABLE",
                    "title": "Your hold is ready for pickup",
                    "message": "The item 'Tomorrow, and Tomorrow, and Tomorrow' is available.",
                    "source_event_type": "HoldReady",
                    "source_event_id": "hold_ready_003",
                    "is_read": False,
                    "created_at": now - timedelta(days=21, hours=5),
                },
                {
                    "category": "DUE_DATE_REMINDER",
                    "title": "Items due in 3 days",
                    "message": "You have 1 item due soon: 'Book Lovers'.",
                    "source_event_type": "DueDateReminder",
                    "source_event_id": "due_reminder_002",
                    "is_read": False,
                    "created_at": now - timedelta(days=21, hours=8),
                },
                # READ (40%)
                {
                    "category": "FINE_PAID",
                    "title": "Fine payment received",
                    "message": "Thank you for your payment of $5.00.",
                    "source_event_type": "FinePaymentReceived",
                    "source_event_id": "fine_paid_001",
                    "is_read": True,
                    "read_at": now - timedelta(hours=1),
                    "created_at": now - timedelta(hours=3),
                },
                {
                    "category": "CHECKOUT_RECEIPT",
                    "title": "Items checked out",
                    "message": "You checked out 1 item today.",
                    "source_event_type": "CheckoutCompleted",
                    "source_event_id": "checkout_003",
                    "is_read": True,
                    "read_at": now - timedelta(hours=4),
                    "created_at": now - timedelta(hours=6),
                },
                {
                    "category": "HOLD_CANCELLED",
                    "title": "Hold cancelled",
                    "message": "Your hold on 'The Invisible Life of Addie LaRue' has been cancelled.",
                    "source_event_type": "HoldCancelled",
                    "source_event_id": "hold_cancelled_001",
                    "is_read": True,
                    "read_at": now - timedelta(days=1, hours=2),
                    "created_at": now - timedelta(days=1, hours=5),
                },
                {
                    "category": "FINE_PAID",
                    "title": "Fine payment received",
                    "message": "Thank you for your payment of $3.50.",
                    "source_event_type": "FinePaymentReceived",
                    "source_event_id": "fine_paid_002",
                    "is_read": True,
                    "read_at": now - timedelta(days=7, hours=1),
                    "created_at": now - timedelta(days=7, hours=4),
                },
                {
                    "category": "CHECKOUT_RECEIPT",
                    "title": "Items checked out",
                    "message": "You checked out 4 items today.",
                    "source_event_type": "CheckoutCompleted",
                    "source_event_id": "checkout_004",
                    "is_read": True,
                    "read_at": now - timedelta(days=7, hours=3),
                    "created_at": now - timedelta(days=7, hours=10),
                },
                {
                    "category": "HOLD_AVAILABLE",
                    "title": "Your hold is ready",
                    "message": "The item 'Fairy Tale' is available at Main Branch.",
                    "source_event_type": "HoldReady",
                    "source_event_id": "hold_ready_004",
                    "is_read": True,
                    "read_at": now - timedelta(days=14, hours=2),
                    "created_at": now - timedelta(days=14, hours=6),
                },
            ]

            # Insert notifications
            for notif in notifications:
                await session.execute(
                    text("""
                        INSERT INTO patron_notifications (
                            patron_id, category, title, message,
                            source_event_type, source_event_id,
                            is_read, read_at, is_dismissed, created_at, updated_at
                        ) VALUES (
                            :patron_id, :category, :title, :message,
                            :source_event_type, :source_event_id,
                            :is_read, :read_at, :is_dismissed, :created_at, :created_at
                        )
                    """),
                    {
                        "patron_id": patron_id,
                        "category": notif["category"],
                        "title": notif["title"],
                        "message": notif["message"],
                        "source_event_type": notif["source_event_type"],
                        "source_event_id": notif["source_event_id"],
                        "is_read": notif["is_read"],
                        "read_at": notif.get("read_at"),
                        "is_dismissed": False,
                        "created_at": notif["created_at"],
                    },
                )

            await session.commit()
            unread = sum(1 for n in notifications if not n["is_read"])
            read = sum(1 for n in notifications if n["is_read"])
            print(f"✅ Created {len(notifications)} patron notifications")
            print(f"   - {unread} unread (60%)")
            print(f"   - {read} read (40%)\n")

        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()
            raise


async def main():
    """Standalone execution for testing."""
    await seed_patron_notifications()


if __name__ == "__main__":
    asyncio.run(main())
