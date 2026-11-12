#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Enhanced Seeded Data Verification - API Endpoint Testing

This script performs comprehensive testing that seeded data:
1. Exists in the database (table counts)
2. Is accessible via API endpoints
3. Contains expected fields and values
4. Is properly formatted and complete

Usage:
    python scripts/verify_seeded_data_endpoints.py
    python scripts/verify_seeded_data_endpoints.py --verbose  # Show detailed response data
    python scripts/verify_seeded_data_endpoints.py --test-endpoints  # Only test endpoints
    python scripts/verify_seeded_data_endpoints.py --test-db  # Only test database
"""

import sys
import os
import asyncio
import json
import httpx
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models import (
    User, CatalogItem, Event, ReadingProgram, Room, RoomAmenity,
    StaffBio, BoardMember, Collection, DatabaseSubscription,
    Checkout, Hold, AnnouncementBanner
)

DATABASE_URL = os.environ["DATABASE_URL"]  # Required - no hardcoded credentials
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Define expected seeded data checklist
SEEDED_DATA_CHECKLIST = {
    "catalog_items": {
        "table": CatalogItem,
        "min_count": 20,
        "endpoint": f"{API_BASE_URL}/catalog",
        "description": "Library catalog items (books, audiobooks, DVDs, etc.)",
        "seed_scripts": ["seed_comprehensive.py"],
        "required_fields": ["id", "title", "item_type", "status"],
    },
    "events": {
        "table": Event,
        "min_count": 5,
        "endpoint": f"{API_BASE_URL}/events",
        "description": "Upcoming library events",
        "seed_scripts": ["seed_events.py", "seed_comprehensive.py"],
        "required_fields": ["id", "title", "start_time", "description"],
    },
    "reading_programs": {
        "table": ReadingProgram,
        "min_count": 3,
        "endpoint": f"{API_BASE_URL}/reading-programs",
        "description": "Reading programs and challenges",
        "seed_scripts": ["seed_reading_programs.py"],
        "required_fields": ["id", "name"],
    },
    "rooms": {
        "table": Room,
        "min_count": 4,
        "endpoint": f"{API_BASE_URL}/rooms",
        "description": "Study rooms and meeting spaces",
        "seed_scripts": ["room_seed_data.py"],
        "required_fields": ["id", "name", "capacity", "room_type"],
    },
    "staff_bios": {
        "table": StaffBio,
        "min_count": 1,
        "endpoint": f"{API_BASE_URL}/staff",
        "description": "Staff biography entries",
        "seed_scripts": ["seed_comprehensive.py"],
        "required_fields": ["id", "name"],
    },
    "board_members": {
        "table": BoardMember,
        "min_count": 3,
        "endpoint": f"{API_BASE_URL}/board",
        "description": "Board member information",
        "seed_scripts": ["seed_board_members.py"],
        "required_fields": ["id", "name", "title"],
    },
    "collections": {
        "table": Collection,
        "min_count": 3,
        "endpoint": f"{API_BASE_URL}/collections",
        "description": "Curated catalog collections",
        "seed_scripts": ["seed_collections.py"],
        "required_fields": ["id", "name"],
    },
    "database_subscriptions": {
        "table": DatabaseSubscription,
        "min_count": 5,
        "endpoint": f"{API_BASE_URL}/databases",
        "description": "Database subscriptions",
        "seed_scripts": ["seed_databases_new.py"],
        "required_fields": ["id", "name"],
    },
    "users": {
        "table": User,
        "min_count": 5,
        "endpoint": None,  # No direct endpoint for all users
        "description": "Test user accounts",
        "seed_scripts": ["seed_test_accounts.py"],
        "required_fields": ["id", "email", "role"],
    },
    "announcements": {
        "table": AnnouncementBanner,
        "min_count": 1,
        "endpoint": f"{API_BASE_URL}/announcements",
        "description": "Announcement banners",
        "seed_scripts": ["seed_comprehensive.py"],
        "required_fields": ["id", "title"],
    },
}


class SeedDataVerifier:
    """Comprehensive seeded data verification tool."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = {
            "database_checks": {},
            "endpoint_checks": {},
            "summary": {},
        }

    async def check_database_counts(self) -> bool:
        """Verify all expected seeded data exists in the database."""
        print("\n" + "=" * 80)
        print("DATABASE TABLE VERIFICATION")
        print("=" * 80)

        all_good = True
        async with async_session() as session:
            for name, config in SEEDED_DATA_CHECKLIST.items():
                table = config.get("table")
                if table is None:
                    continue

                try:
                    stmt = select(func.count(table.id))
                    result = await session.execute(stmt)
                    count = result.scalar() or 0
                    min_count = config["min_count"]

                    status = "✓ OK" if count >= min_count else "✗ LOW"
                    print(f"\n  {name:30} {status:10} ({count}/{min_count} expected)")

                    if count < min_count:
                        all_good = False
                        print(f"     → Missing {min_count - count} items")
                        print(f"     → Re-run: {', '.join(config['seed_scripts'])}")

                    self.results["database_checks"][name] = {
                        "count": count,
                        "expected": min_count,
                        "status": "pass" if count >= min_count else "fail",
                    }

                except Exception as e:
                    print(f"\n  {name:30} ✗ ERROR")
                    print(f"     → {str(e)}")
                    all_good = False
                    self.results["database_checks"][name] = {
                        "error": str(e),
                        "status": "error",
                    }

        return all_good

    async def check_api_endpoints(self) -> bool:
        """Verify seeded data is accessible via API endpoints."""
        print("\n" + "=" * 80)
        print("API ENDPOINT VERIFICATION")
        print("=" * 80)

        all_good = True

        async with httpx.AsyncClient(timeout=10.0) as client:
            for name, config in SEEDED_DATA_CHECKLIST.items():
                endpoint = config.get("endpoint")
                if endpoint is None:
                    continue

                print(f"\n  {name:30} Testing {endpoint}")

                try:
                    response = await client.get(endpoint)

                    if response.status_code != 200:
                        print(f"     ✗ HTTP {response.status_code}")
                        all_good = False
                        self.results["endpoint_checks"][name] = {
                            "status": "fail",
                            "http_code": response.status_code,
                        }
                        continue

                    data = response.json()
                    items = data.get("items", []) or data.get("data", [])

                    if not isinstance(items, list):
                        items = [data] if isinstance(data, dict) else []

                    count = len(items)
                    min_count = config["min_count"]
                    status = "✓ OK" if count >= min_count else "✗ LOW"

                    print(f"     {status} {count} items received ({min_count} expected)")

                    # Validate required fields
                    if items:
                        required = config.get("required_fields", [])
                        first_item = items[0]
                        missing_fields = [f for f in required if f not in first_item]

                        if missing_fields:
                            print(f"     ✗ Missing fields: {', '.join(missing_fields)}")
                            all_good = False
                        else:
                            print("     ✓ All required fields present")

                        if self.verbose and items:
                            print(f"     Sample item: {json.dumps(first_item, indent=8, default=str)}")

                    if count < min_count:
                        all_good = False

                    self.results["endpoint_checks"][name] = {
                        "status": "pass" if (count >= min_count and not missing_fields) else "fail",
                        "count": count,
                        "expected": min_count,
                        "http_code": 200,
                    }

                except httpx.ConnectError:
                    print(f"     ✗ CONNECT ERROR (API not running at {API_BASE_URL})")
                    all_good = False
                    self.results["endpoint_checks"][name] = {
                        "status": "error",
                        "error": "Connection failed",
                    }
                except Exception as e:
                    print(f"     ✗ ERROR: {str(e)}")
                    all_good = False
                    self.results["endpoint_checks"][name] = {
                        "status": "error",
                        "error": str(e),
                    }

        return all_good

    async def check_data_integrity(self) -> bool:
        """Verify data integrity and relationships."""
        print("\n" + "=" * 80)
        print("DATA INTEGRITY CHECKS")
        print("=" * 80)

        all_good = True
        async with async_session() as session:
            # Check for duplicate ISBNs in catalog
            try:
                duplicates = await session.execute(
                    select(CatalogItem.isbn, func.count()).group_by(
                        CatalogItem.isbn
                    ).having(func.count() > 1)
                )
                dup_count = len(duplicates.all())
                if dup_count > 0:
                    print(f"\n  ✗ Found {dup_count} duplicate ISBNs")
                    all_good = False
                else:
                    print("\n  ✓ No duplicate ISBNs")
            except Exception as e:
                print(f"\n  ⚠ Could not check duplicates: {e}")

            # Check for items with invalid status
            try:
                invalid = await session.execute(
                    select(func.count(CatalogItem.id)).where(
                        CatalogItem.status.notin_(["available", "checked_out", "in_repair", "missing"])
                    )
                )
                invalid_count = invalid.scalar() or 0
                if invalid_count > 0:
                    print(f"  ✗ Found {invalid_count} items with invalid status")
                    all_good = False
                else:
                    print("  ✓ All catalog items have valid status")
            except Exception as e:
                print(f"  ⚠ Could not validate statuses: {e}")

            # Check rooms have capacity
            try:
                no_capacity = await session.execute(
                    select(func.count(Room.id)).where(Room.capacity == None)
                )
                count = no_capacity.scalar() or 0
                if count > 0:
                    print(f"  ✗ Found {count} rooms without capacity configured")
                    all_good = False
                else:
                    print("  ✓ All rooms have capacity configured")
            except Exception as e:
                print(f"  ⚠ Could not check rooms: {e}")

        return all_good

    def generate_report(self) -> str:
        """Generate a detailed verification report."""
        report = []
        report.append("\n" + "=" * 80)
        report.append("SEEDED DATA VERIFICATION REPORT")
        report.append("=" * 80)
        report.append(f"\nGenerated: {datetime.now().isoformat()}")

        # Summary counts
        db_results = self.results.get("database_checks", {})
        ep_results = self.results.get("endpoint_checks", {})

        db_pass = sum(1 for r in db_results.values() if r.get("status") == "pass")
        db_fail = sum(1 for r in db_results.values() if r.get("status") == "fail")
        db_error = sum(1 for r in db_results.values() if r.get("status") == "error")

        ep_pass = sum(1 for r in ep_results.values() if r.get("status") == "pass")
        ep_fail = sum(1 for r in ep_results.values() if r.get("status") == "fail")
        ep_error = sum(1 for r in ep_results.values() if r.get("status") == "error")

        report.append(f"\nDatabase Checks:  {db_pass} passed, {db_fail} failed, {db_error} errors")
        report.append(f"API Endpoint:     {ep_pass} passed, {ep_fail} failed, {ep_error} errors")

        # Detailed results
        report.append("\n" + "-" * 80)
        report.append("DETAILED RESULTS")
        report.append("-" * 80)

        for name in sorted(SEEDED_DATA_CHECKLIST.keys()):
            if name in db_results:
                db = db_results[name]
                print_status = "PASS" if db.get("status") == "pass" else "FAIL" if db.get("status") == "fail" else "ERROR"
                report.append(f"\n{name:30} [{print_status}]")
                if "count" in db:
                    report.append(f"  Database: {db['count']}/{db['expected']} rows")
                if "error" in db:
                    report.append(f"  Error: {db['error']}")

            if name in ep_results:
                ep = ep_results[name]
                print_status = "PASS" if ep.get("status") == "pass" else "FAIL" if ep.get("status") == "fail" else "ERROR"
                if "status" in ep:
                    report.append(f"  Endpoint: {print_status}")
                if "count" in ep:
                    report.append(f"    → {ep['count']} items returned")
                if "error" in ep:
                    report.append(f"    → Error: {ep['error']}")

        report.append("\n" + "=" * 80)
        return "\n".join(report)

    async def run_all_checks(self, check_db: bool = True, check_endpoints: bool = True) -> bool:
        """Run all verification checks."""
        all_good = True

        if check_db:
            db_good = await self.check_database_counts()
            all_good = all_good and db_good

        if check_endpoints:
            ep_good = await self.check_api_endpoints()
            all_good = all_good and ep_good

        if check_db and check_endpoints:
            integrity_good = await self.check_data_integrity()
            all_good = all_good and integrity_good

        report = self.generate_report()
        print(report)

        if all_good:
            print("\n✓ All seeded data verification checks PASSED")
        else:
            print("\n✗ Some seeded data verification checks FAILED")
            print("\nRecommended actions:")
            print("  1. Review the failures above")
            print("  2. Re-run relevant seed scripts")
            print("  3. Verify API is running and accessible")
            print("  4. Check database connectivity")

        return all_good


async def main():
    verbose = "--verbose" in sys.argv
    test_endpoints_only = "--test-endpoints" in sys.argv
    test_db_only = "--test-db" in sys.argv

    check_db = not test_endpoints_only
    check_endpoints = not test_db_only

    verifier = SeedDataVerifier(verbose=verbose)

    try:
        success = await verifier.run_all_checks(
            check_db=check_db,
            check_endpoints=check_endpoints
        )
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
