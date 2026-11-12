#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed script for performance testing.

Generates realistic test data at production-like volumes:
- 100,000 patrons
- 500,000 catalog items (with item copies)
- 1,000,000 circulation records (checkouts, holds, fines)

Usage:
    python -m tests.performance.seed_data [--patrons N] [--items N] [--circulations N]

The script uses batch inserts for performance and can seed a PostgreSQL
database in a few minutes. It is idempotent - running it again will skip
seeding if data already exists.
"""

import argparse
import asyncio
import hashlib
import os
import random
import sys
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://lsc:lsc_dev_pwd@localhost:5432/lsc_test")
os.environ.setdefault("SECRET_KEY", "perf-test-secret-key")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("CORS_ORIGINS", "http://localhost")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("LOG_FORMAT", "text")
os.environ.setdefault("SENTRY_DSN", "")

from faker import Faker
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

fake = Faker()
Faker.seed(42)
random.seed(42)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_PATRONS = 100_000
DEFAULT_CATALOG_ITEMS = 500_000
DEFAULT_CIRCULATIONS = 1_000_000

BATCH_SIZE = 5_000  # Rows per INSERT

# Pre-hashed password for all test users: "password123"
# Using bcrypt - computed once to avoid re-hashing 100k times.
PASSWORD_HASH = "$2b$12$LJ3m4ys3Lk0TSwHiPPfXxOQHMcizfAanz0e4fGqKKMc7msTqEf0V2"

ITEM_TYPES = ["book", "audiobook", "ebook", "dvd", "bluray", "cd", "magazine", "game"]
ITEM_STATUSES = ["available", "checked_out", "on_hold", "in_transit", "missing"]
CHECKOUT_STATUSES = ["active", "returned", "overdue"]
HOLD_STATUSES = ["pending", "ready", "fulfilled", "cancelled", "expired"]
FINE_TYPES = ["overdue", "lost_item", "damaged_item", "other"]
FINE_STATUSES = ["unpaid", "paid", "waived", "partial"]
CONDITIONS = ["new", "good", "fair", "poor"]
SENSITIVITY_LEVELS = ["public", "sensitive", "confidential"]

SUBJECTS = [
    "Fiction", "Science Fiction", "Mystery", "Romance", "History",
    "Biography", "Science", "Technology", "Art", "Music",
    "Philosophy", "Psychology", "Mathematics", "Children",
    "Young Adult", "Travel", "Cooking", "Health", "Business",
    "Self-Help", "Poetry", "Drama", "Horror", "Fantasy",
    "True Crime", "Education", "Religion", "Sports", "Nature",
    "Politics",
]

PUBLISHERS = [
    "Penguin Random House", "HarperCollins", "Simon & Schuster",
    "Hachette Book Group", "Macmillan Publishers",
    "Scholastic", "Wiley", "Oxford University Press",
    "Cambridge University Press", "McGraw-Hill",
]


def _generate_isbn() -> str:
    """Generate a realistic ISBN-13."""
    prefix = random.choice(["978", "979"])
    group = str(random.randint(0, 9))
    publisher = str(random.randint(10, 99999)).zfill(5)
    title_part = str(random.randint(10, 999)).zfill(3)
    body = f"{prefix}{group}{publisher}{title_part}"
    # Compute check digit
    total = sum(
        int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(body)
    )
    check = (10 - (total % 10)) % 10
    return f"{body}{check}"


def _generate_call_number() -> str:
    """Generate a realistic Dewey-style call number."""
    dewey = random.randint(0, 999)
    cutter = fake.last_name()[:3].upper()
    return f"{dewey:03d}.{random.randint(1, 99)} {cutter}"


def _generate_barcode(prefix: str, idx: int) -> str:
    """Generate a barcode for items/copies."""
    return f"{prefix}-{idx:08d}"


# ---------------------------------------------------------------------------
# Seeding functions
# ---------------------------------------------------------------------------

async def seed_patrons(session: AsyncSession, count: int) -> list[int]:
    """Insert patron users and return their IDs."""
    print(f"  Seeding {count:,} patrons...")
    start = time.monotonic()

    # Check if patrons already exist
    result = await session.execute(text("SELECT COUNT(*) FROM users WHERE role = 'PATRON'"))
    existing = result.scalar()
    if existing and existing >= count:
        print(f"    Already have {existing:,} patrons, skipping.")
        result = await session.execute(
            text("SELECT id FROM users WHERE role = 'PATRON' ORDER BY id LIMIT :limit"),
            {"limit": count},
        )
        return [row[0] for row in result.fetchall()]

    # Also create staff and admin accounts for auth tests
    special_users = [
        ("patron@test.com", "Test", "Patron", "PATRON"),
        ("staff@test.com", "Test", "Staff", "STAFF"),
        ("admin@test.com", "Test", "Admin", "ADMIN"),
    ]
    for email, first, last, role in special_users:
        await session.execute(
            text(
                "INSERT INTO users (email, password_hash, first_name, last_name, role, "
                "is_active, email_verified, patron_status, notice_preference, address_status, "
                "parental_consent_given, estate_followup_required, reading_minutes_owed, "
                "reading_minutes_logged, failed_login_attempts, track_reading_history, "
                "discreet_receipts, allow_staff_access_to_history, notification_frequency, "
                "onboarding_skipped, show_tooltips, show_feature_highlights, "
                "address_returned_mail_count) "
                "VALUES (:email, :pw, :first, :last, :role, true, true, 'active', 'email', "
                "'unverified', false, false, 0, 0, 0, false, true, false, 'instant', "
                "false, true, true, 0) "
                "ON CONFLICT (email) DO NOTHING"
            ),
            {"email": email, "pw": PASSWORD_HASH, "first": first, "last": last, "role": role},
        )

    patron_ids = []
    for batch_start in range(0, count, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, count)
        values = []
        params = {}
        for i in range(batch_start, batch_end):
            idx = i
            p = f"p{idx}"
            email = f"patron{idx}@perftest.local"
            first = fake.first_name()
            last = fake.last_name()
            card = f"LC-{idx:08d}"
            phone = fake.phone_number()[:20]
            city = fake.city()
            state = fake.state_abbr()
            zip_code = fake.zipcode()
            values.append(
                f"(:{p}_e, :pw, :{p}_f, :{p}_l, 'PATRON', true, true, :{p}_c, :{p}_ph, "
                f"'active', 'email', 'unverified', false, false, 0, 0, 0, false, true, "
                f"false, 'instant', false, true, true, :{p}_ci, :{p}_st, :{p}_z, 0)"
            )
            params[f"{p}_e"] = email
            params[f"{p}_f"] = first
            params[f"{p}_l"] = last
            params[f"{p}_c"] = card
            params[f"{p}_ph"] = phone
            params[f"{p}_ci"] = city
            params[f"{p}_st"] = state
            params[f"{p}_z"] = zip_code

        params["pw"] = PASSWORD_HASH

        if values:
            sql = (
                "INSERT INTO users (email, password_hash, first_name, last_name, role, "
                "is_active, email_verified, library_card, phone, patron_status, "
                "notice_preference, address_status, parental_consent_given, "
                "estate_followup_required, reading_minutes_owed, reading_minutes_logged, "
                "failed_login_attempts, track_reading_history, discreet_receipts, "
                "allow_staff_access_to_history, notification_frequency, onboarding_skipped, "
                "show_tooltips, show_feature_highlights, city, state, zip_code, "
                "address_returned_mail_count) VALUES "
                + ", ".join(values)
                + " ON CONFLICT (email) DO NOTHING"
            )
            await session.execute(text(sql), params)

        if (batch_end % 20_000) == 0 or batch_end == count:
            await session.commit()
            elapsed = time.monotonic() - start
            print(f"    {batch_end:,}/{count:,} patrons ({elapsed:.1f}s)")

    await session.commit()

    result = await session.execute(
        text("SELECT id FROM users WHERE role = 'PATRON' ORDER BY id LIMIT :limit"),
        {"limit": count},
    )
    patron_ids = [row[0] for row in result.fetchall()]
    elapsed = time.monotonic() - start
    print(f"    Done: {len(patron_ids):,} patrons in {elapsed:.1f}s")
    return patron_ids


async def seed_catalog_items(session: AsyncSession, count: int) -> list[int]:
    """Insert catalog items with item copies and return item IDs."""
    print(f"  Seeding {count:,} catalog items with copies...")
    start = time.monotonic()

    result = await session.execute(text("SELECT COUNT(*) FROM catalog_items"))
    existing = result.scalar()
    if existing and existing >= count:
        print(f"    Already have {existing:,} items, skipping.")
        result = await session.execute(
            text("SELECT id FROM catalog_items ORDER BY id LIMIT :limit"),
            {"limit": count},
        )
        return [row[0] for row in result.fetchall()]

    for batch_start in range(0, count, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, count)
        values = []
        params = {}
        for i in range(batch_start, batch_end):
            idx = i
            p = f"i{idx}"
            title = fake.sentence(nb_words=random.randint(2, 8)).rstrip(".")
            author = fake.name()
            isbn = _generate_isbn()
            item_type = random.choice(ITEM_TYPES)
            status = random.choices(
                ITEM_STATUSES,
                weights=[60, 20, 10, 5, 5],
                k=1,
            )[0]
            publisher = random.choice(PUBLISHERS)
            pub_year = random.randint(1950, 2025)
            description = fake.paragraph(nb_sentences=3)
            subjects = ", ".join(random.sample(SUBJECTS, k=random.randint(1, 3)))
            call_number = _generate_call_number()
            barcode = _generate_barcode("CAT", idx)
            sensitivity = random.choices(
                SENSITIVITY_LEVELS, weights=[85, 10, 5], k=1
            )[0]

            values.append(
                f"(:{p}_t, :{p}_a, :{p}_isbn, :{p}_it, :{p}_s, :{p}_pub, :{p}_py, "
                f":{p}_d, :{p}_sub, :{p}_cn, :{p}_bc, :{p}_sl)"
            )
            params[f"{p}_t"] = title
            params[f"{p}_a"] = author
            params[f"{p}_isbn"] = isbn
            params[f"{p}_it"] = item_type
            params[f"{p}_s"] = status
            params[f"{p}_pub"] = publisher
            params[f"{p}_py"] = pub_year
            params[f"{p}_d"] = description
            params[f"{p}_sub"] = subjects
            params[f"{p}_cn"] = call_number
            params[f"{p}_bc"] = barcode
            params[f"{p}_sl"] = sensitivity

        if values:
            sql = (
                "INSERT INTO catalog_items (title, author, isbn, item_type, status, "
                "publisher, publication_year, description, subjects, call_number, "
                "barcode, sensitivity_level) VALUES "
                + ", ".join(values)
                + " ON CONFLICT (barcode) DO NOTHING"
            )
            await session.execute(text(sql), params)

        if (batch_end % 50_000) == 0 or batch_end == count:
            await session.commit()
            elapsed = time.monotonic() - start
            print(f"    {batch_end:,}/{count:,} catalog items ({elapsed:.1f}s)")

    await session.commit()

    # Seed item copies (1-3 copies per item)
    print("    Seeding item copies...")
    result = await session.execute(
        text("SELECT id FROM catalog_items ORDER BY id LIMIT :limit"),
        {"limit": count},
    )
    item_ids = [row[0] for row in result.fetchall()]

    result = await session.execute(text("SELECT COUNT(*) FROM item_copies"))
    existing_copies = result.scalar()
    if not existing_copies or existing_copies < len(item_ids):
        copy_batch = []
        copy_params = {}
        copy_idx = 0
        for item_id in item_ids:
            num_copies = random.choices([1, 2, 3], weights=[60, 30, 10], k=1)[0]
            for copy_num in range(1, num_copies + 1):
                p = f"c{copy_idx}"
                copy_batch.append(
                    f"(:{p}_cid, :{p}_bc, :{p}_cn, :{p}_cond)"
                )
                copy_params[f"{p}_cid"] = item_id
                copy_params[f"{p}_bc"] = _generate_barcode("COPY", copy_idx)
                copy_params[f"{p}_cn"] = copy_num
                copy_params[f"{p}_cond"] = random.choice(CONDITIONS)
                copy_idx += 1

                if len(copy_batch) >= BATCH_SIZE:
                    sql = (
                        "INSERT INTO item_copies (catalog_item_id, barcode, copy_number, "
                        "condition) VALUES "
                        + ", ".join(copy_batch)
                        + " ON CONFLICT (barcode) DO NOTHING"
                    )
                    await session.execute(text(sql), copy_params)
                    await session.commit()
                    copy_batch = []
                    copy_params = {}

        if copy_batch:
            sql = (
                "INSERT INTO item_copies (catalog_item_id, barcode, copy_number, "
                "condition) VALUES "
                + ", ".join(copy_batch)
                + " ON CONFLICT (barcode) DO NOTHING"
            )
            await session.execute(text(sql), copy_params)
            await session.commit()

        print(f"    {copy_idx:,} item copies seeded.")

    elapsed = time.monotonic() - start
    print(f"    Done: {len(item_ids):,} items in {elapsed:.1f}s")
    return item_ids


async def seed_circulation_records(
    session: AsyncSession,
    patron_ids: list[int],
    item_ids: list[int],
    count: int,
) -> None:
    """Insert checkouts, holds, and fines."""
    print(f"  Seeding {count:,} circulation records...")
    start = time.monotonic()

    result = await session.execute(text("SELECT COUNT(*) FROM checkouts"))
    existing = result.scalar()
    if existing and existing >= count // 2:
        print(f"    Already have {existing:,} checkouts, skipping.")
        return

    now = datetime.now(timezone.utc)
    checkout_count = count // 2  # 500k checkouts
    hold_count = count // 4  # 250k holds
    fine_count = count // 4  # 250k fines

    # --- Checkouts ---
    print(f"    Seeding {checkout_count:,} checkouts...")
    for batch_start in range(0, checkout_count, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, checkout_count)
        values = []
        params = {}
        for i in range(batch_start, batch_end):
            p = f"co{i}"
            user_id = random.choice(patron_ids)
            item_id = random.choice(item_ids)
            status = random.choices(
                CHECKOUT_STATUSES, weights=[30, 60, 10], k=1
            )[0]
            days_ago = random.randint(0, 365)
            checked_out = now - timedelta(days=days_ago)
            due = checked_out + timedelta(days=random.choice([7, 14, 21, 28]))
            returned_at = None
            if status == "returned":
                returned_at = due - timedelta(days=random.randint(-5, 10))

            values.append(
                f"(:{p}_u, :{p}_i, :{p}_s, :{p}_co, :{p}_d, :{p}_r, 0, 0)"
            )
            params[f"{p}_u"] = user_id
            params[f"{p}_i"] = item_id
            params[f"{p}_s"] = status
            params[f"{p}_co"] = checked_out
            params[f"{p}_d"] = due
            params[f"{p}_r"] = returned_at

        if values:
            sql = (
                "INSERT INTO checkouts (user_id, item_id, status, checked_out_at, "
                "due_date, returned_at, renewal_count, last_overdue_days_processed) VALUES "
                + ", ".join(values)
            )
            await session.execute(text(sql), params)

        if (batch_end % 50_000) == 0 or batch_end == checkout_count:
            await session.commit()
            elapsed = time.monotonic() - start
            print(f"      {batch_end:,}/{checkout_count:,} checkouts ({elapsed:.1f}s)")

    # --- Holds ---
    print(f"    Seeding {hold_count:,} holds...")
    for batch_start in range(0, hold_count, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, hold_count)
        values = []
        params = {}
        for i in range(batch_start, batch_end):
            p = f"h{i}"
            user_id = random.choice(patron_ids)
            item_id = random.choice(item_ids)
            status = random.choices(
                HOLD_STATUSES, weights=[30, 15, 30, 15, 10], k=1
            )[0]
            position = random.randint(1, 10)
            days_ago = random.randint(0, 180)
            created = now - timedelta(days=days_ago)

            values.append(
                f"(:{p}_u, :{p}_i, :{p}_s, :{p}_pos, :{p}_ca)"
            )
            params[f"{p}_u"] = user_id
            params[f"{p}_i"] = item_id
            params[f"{p}_s"] = status
            params[f"{p}_pos"] = position
            params[f"{p}_ca"] = created

        if values:
            sql = (
                "INSERT INTO holds (user_id, item_id, status, position, created_at) VALUES "
                + ", ".join(values)
            )
            await session.execute(text(sql), params)

        if (batch_end % 50_000) == 0 or batch_end == hold_count:
            await session.commit()
            elapsed = time.monotonic() - start
            print(f"      {batch_end:,}/{hold_count:,} holds ({elapsed:.1f}s)")

    # --- Fines ---
    print(f"    Seeding {fine_count:,} fines...")
    # Get checkout IDs for linking
    result = await session.execute(
        text("SELECT id FROM checkouts ORDER BY id LIMIT :limit"),
        {"limit": fine_count},
    )
    checkout_ids = [row[0] for row in result.fetchall()]

    for batch_start in range(0, fine_count, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, fine_count)
        values = []
        params = {}
        for i in range(batch_start, batch_end):
            p = f"f{i}"
            user_id = random.choice(patron_ids)
            checkout_id = checkout_ids[i] if i < len(checkout_ids) else None
            fine_type = random.choice(FINE_TYPES)
            status = random.choices(
                FINE_STATUSES, weights=[40, 35, 15, 10], k=1
            )[0]
            amount = Decimal(str(round(random.uniform(0.25, 50.00), 2)))
            amount_paid = Decimal("0.00")
            if status == "paid":
                amount_paid = amount
            elif status == "partial":
                amount_paid = Decimal(str(round(float(amount) * random.uniform(0.1, 0.9), 2)))
            description = f"Performance test fine #{i}"

            values.append(
                f"(:{p}_u, :{p}_co, :{p}_ft, :{p}_s, :{p}_a, :{p}_ap, :{p}_d)"
            )
            params[f"{p}_u"] = user_id
            params[f"{p}_co"] = checkout_id
            params[f"{p}_ft"] = fine_type
            params[f"{p}_s"] = status
            params[f"{p}_a"] = str(amount)
            params[f"{p}_ap"] = str(amount_paid)
            params[f"{p}_d"] = description

        if values:
            sql = (
                "INSERT INTO fines (user_id, checkout_id, fine_type, status, amount, "
                "amount_paid, description) VALUES "
                + ", ".join(values)
            )
            await session.execute(text(sql), params)

        if (batch_end % 50_000) == 0 or batch_end == fine_count:
            await session.commit()
            elapsed = time.monotonic() - start
            print(f"      {batch_end:,}/{fine_count:,} fines ({elapsed:.1f}s)")

    await session.commit()
    elapsed = time.monotonic() - start
    print(f"    Done: circulation records in {elapsed:.1f}s")


async def verify_counts(session: AsyncSession) -> dict:
    """Print summary of seeded data."""
    tables = ["users", "catalog_items", "item_copies", "checkouts", "holds", "fines"]
    counts = {}
    for table in tables:
        result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
        counts[table] = result.scalar()

    print("\n  Data Summary:")
    for table, count in counts.items():
        print(f"    {table:<20s} {count:>12,}")
    return counts


async def main(
    patron_count: int = DEFAULT_PATRONS,
    item_count: int = DEFAULT_CATALOG_ITEMS,
    circulation_count: int = DEFAULT_CIRCULATIONS,
) -> None:
    """Run the full seeding pipeline."""
    db_url = os.environ["DATABASE_URL"]
    print("\nPerformance Test Data Seeder")
    print(f"  Database: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    print(f"  Target: {patron_count:,} patrons, {item_count:,} items, "
          f"{circulation_count:,} circulation records\n")

    engine_kwargs = {"echo": False}
    if "postgresql" in db_url:
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20
        engine_kwargs["pool_pre_ping"] = True
    elif "sqlite" in db_url:
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_async_engine(db_url, **engine_kwargs)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        patron_ids = await seed_patrons(session, patron_count)
        item_ids = await seed_catalog_items(session, item_count)
        await seed_circulation_records(session, patron_ids, item_ids, circulation_count)
        await verify_counts(session)

    await engine.dispose()
    print("\nSeeding complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed performance test data")
    parser.add_argument("--patrons", type=int, default=DEFAULT_PATRONS,
                        help=f"Number of patrons (default: {DEFAULT_PATRONS:,})")
    parser.add_argument("--items", type=int, default=DEFAULT_CATALOG_ITEMS,
                        help=f"Number of catalog items (default: {DEFAULT_CATALOG_ITEMS:,})")
    parser.add_argument("--circulations", type=int, default=DEFAULT_CIRCULATIONS,
                        help=f"Number of circulation records (default: {DEFAULT_CIRCULATIONS:,})")

    args = parser.parse_args()
    asyncio.run(main(args.patrons, args.items, args.circulations))
