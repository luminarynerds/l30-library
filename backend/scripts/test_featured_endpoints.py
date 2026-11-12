#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Test script to verify the featured books and staff picks endpoints.

This script demonstrates the usage of the new endpoints:
- GET /indie/featured - Public endpoint for featured books
- GET /indie/staff-picks - Public endpoint for staff picks
- PATCH /indie/admin/ebooks/{id}/feature - Admin endpoint to feature books
- PATCH /indie/admin/ebooks/{id}/staff-pick - Admin endpoint to mark staff picks

Note: This is a verification/testing script. The actual endpoints require
a running FastAPI server and database connection.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.indie_author import IndieEbook, EbookSubmissionStatus


async def test_query_featured_books(db: AsyncSession):
    """Test the query logic for featured books endpoint."""
    print("\n=== Testing Featured Books Query ===")

    now = datetime.now(timezone.utc)

    # This is the query used in GET /indie/featured
    base_filter = and_(
        IndieEbook.submission_status == EbookSubmissionStatus.approved,
        IndieEbook.lending_enabled == True,
        IndieEbook.is_featured == True,
        or_(
            IndieEbook.featured_until.is_(None),
            IndieEbook.featured_until > now
        )
    )

    query = (
        select(IndieEbook)
        .where(base_filter)
        .order_by(
            IndieEbook.featured_order.asc().nullslast(),
            IndieEbook.featured_at.desc()
        )
    )

    result = await db.execute(query)
    featured_books = result.scalars().all()

    print(f"Found {len(featured_books)} currently featured books:")
    for book in featured_books:
        expiry = f"until {book.featured_until.date()}" if book.featured_until else "indefinite"
        print(f"  - [{book.featured_order or 'N/A'}] {book.title} (featured {expiry})")

    return featured_books


async def test_query_staff_picks(db: AsyncSession):
    """Test the query logic for staff picks endpoint."""
    print("\n=== Testing Staff Picks Query ===")

    # This is the query used in GET /indie/staff-picks
    base_filter = and_(
        IndieEbook.submission_status == EbookSubmissionStatus.approved,
        IndieEbook.lending_enabled == True,
        IndieEbook.is_staff_pick == True
    )

    query = (
        select(IndieEbook)
        .where(base_filter)
        .order_by(IndieEbook.staff_pick_at.desc())
    )

    result = await db.execute(query)
    staff_picks = result.scalars().all()

    print(f"Found {len(staff_picks)} staff pick books:")
    for book in staff_picks:
        picked_date = book.staff_pick_at.date() if book.staff_pick_at else "unknown"
        print(f"  - {book.title} (picked: {picked_date})")

    return staff_picks


async def test_is_currently_featured_property(db: AsyncSession):
    """Test the is_currently_featured property."""
    print("\n=== Testing is_currently_featured Property ===")

    result = await db.execute(
        select(IndieEbook).where(IndieEbook.is_featured == True)
    )
    featured_books = result.scalars().all()

    print(f"Testing {len(featured_books)} featured books:")
    for book in featured_books:
        is_currently = book.is_currently_featured
        status = "✓ Currently featured" if is_currently else "✗ Not currently featured (expired)"
        if book.featured_until:
            print(f"  {book.title}: {status} (expires: {book.featured_until.date()})")
        else:
            print(f"  {book.title}: {status} (indefinite)")


async def test_feature_book_logic(db: AsyncSession):
    """Test the logic for featuring a book."""
    print("\n=== Testing Feature Book Logic ===")

    # Get first approved book
    result = await db.execute(
        select(IndieEbook)
        .where(
            IndieEbook.submission_status == EbookSubmissionStatus.approved,
            IndieEbook.is_featured == False
        )
        .limit(1)
    )
    test_book = result.scalar_one_or_none()

    if not test_book:
        print("No unfeatured approved books available for testing.")
        return

    print(f"Testing with book: '{test_book.title}'")
    print(f"  Current status: is_featured={test_book.is_featured}")

    # Simulate featuring (without committing)
    print("\nSimulating feature operation...")
    test_book.is_featured = True
    test_book.featured_at = datetime.now(timezone.utc)
    test_book.featured_until = datetime.now(timezone.utc) + timedelta(days=30)
    test_book.featured_order = 0

    print("  After featuring:")
    print(f"    - is_featured: {test_book.is_featured}")
    print(f"    - featured_at: {test_book.featured_at}")
    print(f"    - featured_until: {test_book.featured_until}")
    print(f"    - featured_order: {test_book.featured_order}")
    print(f"    - is_currently_featured: {test_book.is_currently_featured}")

    # Rollback to not change data
    await db.rollback()
    print("\n  (Changes rolled back - no data modified)")


async def main():
    """Main test function."""
    print("=" * 60)
    print("Featured Books & Staff Picks Endpoint Testing")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        try:
            # Test featured books query
            await test_query_featured_books(db)

            # Test staff picks query
            await test_query_staff_picks(db)

            # Test is_currently_featured property
            await test_is_currently_featured_property(db)

            # Test feature book logic
            await test_feature_book_logic(db)

            print("\n" + "=" * 60)
            print("✓ All tests completed successfully!")
            print("=" * 60)

            print("\nAPI Endpoint Summary:")
            print("  Public Endpoints:")
            print("    - GET  /api/v1/indie/featured")
            print("    - GET  /api/v1/indie/staff-picks")
            print("\n  Admin Endpoints (requires STAFF/ADMIN role):")
            print("    - PATCH /api/v1/indie/admin/ebooks/{id}/feature")
            print("    - PATCH /api/v1/indie/admin/ebooks/{id}/staff-pick")

        except Exception as e:
            print(f"\n✗ Error during testing: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
