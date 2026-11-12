#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Debug LSC Database Queries

This script demonstrates:
1. Capturing SQLAlchemy queries before execution
2. Printing compiled SQL with parameters bound
3. Running the same query with filters removed
4. Comparing expected vs actual results
5. Identifying which WHERE clauses filter out data
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, and_, or_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

# Import models
from app.models.circulation import Checkout, CheckoutStatus
from app.models.catalog import CatalogItem
from app.models.user import User
from app.models.fine import Fine, FineStatus

# Import database setup
from app.core.database import AsyncSessionLocal, engine
from app.core.query_debugger import setup_query_debugging, get_debugger, DebugSelectBuilder


async def test_checkout_history_query(db: AsyncSession, user_id: int):
    """Test the checkout history query with various filters."""
    print("\n" + "=" * 100)
    print("TEST 1: CHECKOUT HISTORY QUERY")
    print("=" * 100)

    debugger = get_debugger()
    debugger.enable()

    # Query 1: Full query with user_id filter (this is what gets executed)
    print("\n--- FULL QUERY (with user_id filter) ---")
    debugger.clear()

    query_full = (
        select(Checkout, CatalogItem)
        .join(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(Checkout.user_id == user_id)
        .order_by(Checkout.checked_out_at.desc())
        .limit(50)
        .offset(0)
    )

    print("Building query...")
    result = await db.execute(query_full)
    rows_with_filter = result.all()
    print(f"Result: {len(rows_with_filter)} rows")

    if debugger.captured_queries:
        last_query = debugger.captured_queries[-1]
        print("\nCOMPILED SQL WITH PARAMETERS:")
        print(last_query["compiled_sql"])

    # Query 2: Same query but without user_id filter
    print("\n--- SAME QUERY WITHOUT user_id FILTER ---")
    debugger.clear()

    query_no_filter = (
        select(Checkout, CatalogItem)
        .join(CatalogItem, Checkout.item_id == CatalogItem.id)
        # No WHERE clause
        .order_by(Checkout.checked_out_at.desc())
        .limit(50)
        .offset(0)
    )

    result = await db.execute(query_no_filter)
    rows_without_filter = result.all()
    print(f"Result: {len(rows_without_filter)} rows")

    if debugger.captured_queries:
        last_query = debugger.captured_queries[-1]
        print("\nCOMPILED SQL:")
        print(last_query["compiled_sql"])

    # Analysis
    print("\n--- FILTER ANALYSIS ---")
    print(f"Rows WITHOUT filter: {len(rows_without_filter)}")
    print(f"Rows WITH filter: {len(rows_with_filter)}")
    print(f"Filtered out: {len(rows_without_filter) - len(rows_with_filter)} rows")
    if len(rows_without_filter) > 0:
        percent_filtered = 100 * (len(rows_without_filter) - len(rows_with_filter)) / len(rows_without_filter)
        print(f"Filtering impact: {percent_filtered:.1f}%")


async def test_fines_query(db: AsyncSession, user_id: int):
    """Test the fines query with various filters."""
    print("\n" + "=" * 100)
    print("TEST 2: USER FINES QUERY")
    print("=" * 100)

    debugger = get_debugger()
    debugger.enable()

    # Query 1: Full query with user_id and status filters
    print("\n--- FULL QUERY (with user_id and status filters) ---")
    debugger.clear()

    query_full = (
        select(Fine, Checkout, CatalogItem)
        .outerjoin(Checkout, Fine.checkout_id == Checkout.id)
        .outerjoin(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(Fine.user_id == user_id)
        .where(Fine.status == FineStatus.unpaid)
        .order_by(Fine.created_at.desc())
        .offset(0)
        .limit(50)
    )

    result = await db.execute(query_full)
    rows_with_filters = result.all()
    print(f"Result: {len(rows_with_filters)} rows")

    if debugger.captured_queries:
        last_query = debugger.captured_queries[-1]
        print("\nCOMPILED SQL WITH PARAMETERS:")
        print(last_query["compiled_sql"])

    # Query 2: Same query but only user_id filter
    print("\n--- SAME QUERY WITHOUT status FILTER ---")
    debugger.clear()

    query_no_status = (
        select(Fine, Checkout, CatalogItem)
        .outerjoin(Checkout, Fine.checkout_id == Checkout.id)
        .outerjoin(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(Fine.user_id == user_id)
        # No status filter
        .order_by(Fine.created_at.desc())
        .offset(0)
        .limit(50)
    )

    result = await db.execute(query_no_status)
    rows_no_status = result.all()
    print(f"Result: {len(rows_no_status)} rows")

    if debugger.captured_queries:
        last_query = debugger.captured_queries[-1]
        print("\nCOMPILED SQL:")
        print(last_query["compiled_sql"])

    # Query 3: No filters at all
    print("\n--- SAME QUERY WITHOUT ANY FILTERS ---")
    debugger.clear()

    query_no_filters = (
        select(Fine, Checkout, CatalogItem)
        .outerjoin(Checkout, Fine.checkout_id == Checkout.id)
        .outerjoin(CatalogItem, Checkout.item_id == CatalogItem.id)
        .order_by(Fine.created_at.desc())
        .offset(0)
        .limit(50)
    )

    result = await db.execute(query_no_filters)
    rows_no_filters = result.all()
    print(f"Result: {len(rows_no_filters)} rows")

    if debugger.captured_queries:
        last_query = debugger.captured_queries[-1]
        print("\nCOMPILED SQL:")
        print(last_query["compiled_sql"])

    # Analysis
    print("\n--- FILTER ANALYSIS ---")
    print(f"Rows WITHOUT any filters: {len(rows_no_filters)}")
    print(f"Rows WITH user_id filter only: {len(rows_with_filters)}")  # Note: will also have status
    print(f"Rows WITH user_id + status filters: {len(rows_with_filters)}")
    print("\nBreakdown:")
    print(f"  user_id filter removes: {len(rows_no_filters) - len(rows_no_status)} rows")
    print(f"  status filter removes: {len(rows_no_status) - len(rows_with_filters)} rows")


async def test_reading_history_flag(db: AsyncSession):
    """Test the effect of track_reading_history flag."""
    print("\n" + "=" * 100)
    print("TEST 3: READING HISTORY FLAG ANALYSIS")
    print("=" * 100)

    # Find users with and without reading history enabled
    users_result = await db.execute(select(User).limit(10))
    users = users_result.scalars().all()

    print(f"\nUsers in database: {len(users)}")

    tracked_users = [u for u in users if u.track_reading_history]
    untracked_users = [u for u in users if not u.track_reading_history]

    print(f"Users with tracking enabled: {len(tracked_users)}")
    print(f"Users with tracking DISABLED: {len(untracked_users)}")

    if untracked_users:
        test_user = untracked_users[0]
        print("\n--- Testing with user who has tracking DISABLED ---")
        print(f"User ID: {test_user.id}")
        print(f"Username: {test_user.username}")
        print(f"track_reading_history: {test_user.track_reading_history}")

        debugger = get_debugger()
        debugger.enable()
        debugger.clear()

        # This query would be executed IF the flag were enabled
        query = (
            select(Checkout, CatalogItem)
            .join(CatalogItem, Checkout.item_id == CatalogItem.id)
            .where(Checkout.user_id == test_user.id)
            .order_by(Checkout.checked_out_at.desc())
            .limit(50)
        )

        result = await db.execute(query)
        rows = result.all()

        print(f"\nQuery that WOULD execute if flag were enabled: {len(rows)} rows")

        if debugger.captured_queries:
            print("\nSQL that would execute:")
            print(debugger.captured_queries[-1]["compiled_sql"])

        print("\nBUT in the actual code (circulation.py:398-399):")
        print("  if not current_user.track_reading_history:")
        print("      return []  # RETURNS EMPTY IMMEDIATELY")
        print("\nSo user sees: 0 rows (silent filtering)")

    if tracked_users:
        test_user = tracked_users[0]
        print("\n--- Testing with user who has tracking ENABLED ---")
        print(f"User ID: {test_user.id}")
        print(f"Username: {test_user.username}")
        print(f"track_reading_history: {test_user.track_reading_history}")

        debugger = get_debugger()
        debugger.enable()
        debugger.clear()

        query = (
            select(Checkout, CatalogItem)
            .join(CatalogItem, Checkout.item_id == CatalogItem.id)
            .where(Checkout.user_id == test_user.id)
            .order_by(Checkout.checked_out_at.desc())
            .limit(50)
        )

        result = await db.execute(query)
        rows = result.all()

        print(f"\nQuery executes: {len(rows)} rows returned")


async def test_join_exclusions(db: AsyncSession):
    """Test how JOINs might exclude records."""
    print("\n" + "=" * 100)
    print("TEST 4: JOIN-BASED FILTERING ANALYSIS")
    print("=" * 100)

    debugger = get_debugger()
    debugger.enable()

    # Case 1: INNER JOIN (excludes records without matches)
    print("\n--- INNER JOIN (excludes non-matching records) ---")
    debugger.clear()

    inner_query = (
        select(Checkout, CatalogItem)
        .join(CatalogItem, Checkout.item_id == CatalogItem.id)  # INNER JOIN
        .limit(10)
    )

    result = await db.execute(inner_query)
    inner_rows = result.all()
    print(f"INNER JOIN result: {len(inner_rows)} rows")

    if debugger.captured_queries:
        print("\nSQL:")
        print(debugger.captured_queries[-1]["compiled_sql"])

    # Case 2: Count without JOIN
    print("\n--- SELECT without JOIN (total checkouts) ---")
    debugger.clear()

    total_query = select(func.count(Checkout.id))
    result = await db.execute(total_query)
    total = result.scalar()
    print(f"Total checkouts in database: {total}")

    # Case 3: OUTER JOIN
    print("\n--- OUTER JOIN (includes non-matching records) ---")
    debugger.clear()

    outer_query = (
        select(Checkout, CatalogItem)
        .outerjoin(CatalogItem, Checkout.item_id == CatalogItem.id)  # OUTER JOIN
        .limit(10)
    )

    result = await db.execute(outer_query)
    outer_rows = result.all()
    print(f"OUTER JOIN result: {len(outer_rows)} rows")

    if total and len(inner_rows) < total:
        print("\n--- IMPACT ANALYSIS ---")
        print(f"Total records: {total}")
        print(f"INNER JOIN returns: {len(inner_rows)} rows")
        print(f"Excluded by INNER JOIN: {total - len(inner_rows)} rows")


async def main():
    """Run all debug tests."""
    print("\n" + "=" * 100)
    print("LSC DATABASE QUERY DEBUGGING")
    print("=" * 100)
    print(f"Started: {datetime.now().isoformat()}")

    # Setup query debugging
    if engine is None:
        print("ERROR: Engine not initialized. Make sure database is configured.")
        return

    setup_query_debugging(engine, enable=True)
    debugger = get_debugger()

    async with AsyncSessionLocal() as db:
        # Find a test user
        users_result = await db.execute(select(User).limit(1))
        users = users_result.scalars().all()

        if not users:
            print("ERROR: No users found in database. Please populate test data first.")
            return

        test_user = users[0]
        print(f"\nUsing test user: {test_user.id} ({test_user.username})")

        # Run all tests
        try:
            await test_checkout_history_query(db, test_user.id)
            await test_fines_query(db, test_user.id)
            await test_reading_history_flag(db)
            await test_join_exclusions(db)
        except Exception as e:
            print(f"ERROR during tests: {e}")
            import traceback
            traceback.print_exc()

    # Export all queries to file
    debugger.export_queries_sql("/tmp/lsc_queries_debug.sql")
    print("\nAll queries exported to: /tmp/lsc_queries_debug.sql")

    print("\n" + "=" * 100)
    print(f"Completed: {datetime.now().isoformat()}")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
