#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Master seeding script for LSC Library System.
Runs all seed scripts in the correct dependency order to fully populate the database.
"""
import subprocess
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
# Don't change directory - use absolute paths instead

# Define seeding scripts in dependency order
# Scripts that don't have dependencies can be run in parallel
SEED_SCRIPTS = [
    # Phase 1: Core data (users, catalog, rooms, events)
    ("seed_test_accounts.py", "Test user accounts (admin, staff, patrons)"),
    ("seed_comprehensive.py", "Comprehensive catalog items, events, announcements"),

    # Phase 2: Collections and relationships
    ("seed_collections.py", "Collections and featured items"),
    ("seed_board_members.py", "Board members"),
    ("seed_board_meetings.py", "Board meeting schedule (past and upcoming)"),
    ("seed_board_governance.py", "Board governance (agendas, minutes, documents, votes, strategic plan, audit logs)"),
    ("seed_staff_training.py", "Staff training materials"),

    # Phase 3: Circulation and holds (depends on users + catalog)
    ("seed_active_checkouts.py", "Checkouts, holds, and circulation data"),
    ("seed_diverse_patrons.py", "Diverse patron scenarios (suspended, blocked, with holds, etc)"),

    # Phase 4: Acquisitions and Inventory (depends on users + catalog)
    ("seed_acquisitions.py", "Purchase orders, vendors, funds, and EDI transactions"),
    ("seed_inventory_operations.py", "Physical item copies, inventory audits, and condition tracking"),

    # Phase 5: Additional resources
    ("seed_databases_new.py", "Database subscriptions"),
    ("seed_reading_lists.py", "Reading lists"),
    ("seed_reading_programs.py", "Reading programs"),

    # Phase 6: Specialized content
    ("seed_indie_reading_lists.py", "Indie author reading lists"),
    ("seed_legal_resources.py", "Legal resource collections"),
    ("seed_learning_paths.py", "Learning paths and educational content"),

    # Phase 7: Additional features
    ("seed_book_challenges.py", "Book challenge workflows"),
    ("seed_featured_books.py", "Featured books"),
    ("seed_author_follows.py", "Author follow relationships"),
    ("seed_patron_courses.py", "Patron courses and lessons"),

    # Phase 8: Specialized Services
    ("seed_home_delivery.py", "HomeDelivery patron delivery services"),
    ("seed_makerspace.py", "Makerspace equipment and certifications"),
    ("seed_rooms.py", "Library room reservations and bookings"),
    ("seed_tech_support.py", "Tech support resources, classes, and help options"),
]


def run_script(script_name: str) -> bool:
    """Run a seed script and return True if successful."""
    script_path = Path(__file__).parent / script_name
    if not script_path.exists():
        print(f"  ⚠️  Script not found: {script_path}")
        return False

    try:
        print(f"  Running {script_name}...", end=" ", flush=True)
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per script
        )

        if result.returncode == 0:
            print("✓")
            return True
        else:
            print("✗")
            print(f"    STDOUT: {result.stdout}")
            print(f"    STDERR: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("✗ (TIMEOUT)")
        return False
    except Exception as e:
        print(f"✗ ({e})")
        return False


def main():
    """Main seeding function."""
    print("\n" + "="*80)
    print("LSC LIBRARY - MASTER SEEDING SCRIPT")
    print("="*80)

    # Check environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("\n❌ ERROR: DATABASE_URL environment variable not set!")
        print("   Set it with: export DATABASE_URL='postgresql+asyncpg://...'")
        return 1

    print(f"\n📊 Database: {db_url.rsplit('@', 1)[1]}")
    script_dir = Path(__file__).parent
    print(f"📝 Scripts location: {script_dir.absolute()}")

    # Verify scripts exist
    missing_scripts = []
    for script_name, _ in SEED_SCRIPTS:
        if not (script_dir / script_name).exists():
            missing_scripts.append(script_name)

    if missing_scripts:
        print("\n⚠️  Missing scripts:")
        for script in missing_scripts:
            print(f"   - {script}")

    print(f"\n⏱️  Starting seed process ({len(SEED_SCRIPTS)} scripts)...\n")

    successful = 0
    failed = 0
    skipped = 0

    for i, (script_name, description) in enumerate(SEED_SCRIPTS, 1):
        print(f"[{i}/{len(SEED_SCRIPTS)}] {description}")

        if not (Path("scripts") / script_name).exists():
            print("  ⚠️  Skipped (not found)")
            skipped += 1
        elif run_script(script_name):
            successful += 1
        else:
            failed += 1

    # Print summary
    print("\n" + "="*80)
    print("SEEDING SUMMARY")
    print("="*80)
    print(f"✓ Successful: {successful}")
    print(f"✗ Failed:     {failed}")
    print(f"⚠️  Skipped:    {skipped}")
    print(f"Total:      {len(SEED_SCRIPTS)}")

    if failed > 0:
        print(f"\n❌ {failed} seed script(s) failed!")
        print("\nNext steps:")
        print("  1. Check the error messages above")
        print("  2. Verify database connection: DATABASE_URL")
        print("  3. Verify migrations are up-to-date: alembic upgrade head")
        print("  4. Check database logs for constraint violations")
        return 1

    print("\n✅ All seed scripts completed successfully!")
    print("\nNext steps:")
    print("  1. Verify data: python debug_seeded_data.py")
    print("  2. Run SQL queries: psql -f verify_seeded_data.sql")
    print("  3. Check API: curl http://localhost:8000/api/v1/catalog/items")
    print("  4. View frontend: http://localhost:3000")
    return 0


if __name__ == "__main__":
    sys.exit(main())
