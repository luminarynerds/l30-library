#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Master Demo Seeding Script for LSC Library System.

Orchestrates all seed scripts to create a complete, polished demo environment
for stakeholder presentations. Extends run_all_seeds.py with additional
demo-critical scripts and creates named demo personas for the walkthrough.

Usage:
    python scripts/seed_demo_master.py              # Full seed (all phases)
    python scripts/seed_demo_master.py --skip-core   # Skip phases 1-8, run 9-10 only
"""
import asyncio
import subprocess
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Phase 1-8: Core scripts (same as run_all_seeds.py)
# ---------------------------------------------------------------------------
CORE_SCRIPTS = [
    # Phase 1: Core data (users, catalog, rooms, events)
    ("seed_test_accounts.py", "Test user accounts (admin, staff, patrons)"),
    ("seed_comprehensive.py", "Comprehensive catalog items, events, announcements"),

    # Phase 2: Collections and relationships
    ("seed_collections.py", "Collections and featured items"),
    ("seed_board_members.py", "Board members"),
    ("seed_board_meetings.py", "Board meeting schedule (past and upcoming)"),
    ("seed_board_governance.py", "Board governance (agendas, minutes, documents, votes)"),
    ("seed_staff_training.py", "Staff training materials"),

    # Phase 3: Circulation and holds
    ("seed_active_checkouts.py", "Checkouts, holds, and circulation data"),
    ("seed_diverse_patrons.py", "Diverse patron scenarios"),

    # Phase 4: Acquisitions and Inventory
    ("seed_acquisitions.py", "Purchase orders, vendors, funds"),
    ("seed_inventory_operations.py", "Physical item copies and inventory audits"),

    # Phase 5: Additional resources
    ("seed_databases_new.py", "Database subscriptions"),
    ("seed_reading_lists.py", "Reading lists"),
    ("seed_reading_programs.py", "Reading programs"),

    # Phase 6: Specialized content
    ("seed_indie_reading_lists.py", "Indie author reading lists"),
    ("seed_legal_resources.py", "Legal resource collections"),
    ("seed_learning_paths.py", "Learning paths"),

    # Phase 7: Additional features
    ("seed_book_challenges.py", "Book challenge workflows"),
    ("seed_featured_books.py", "Featured books"),
    ("seed_author_follows.py", "Author follow relationships"),
    ("seed_patron_courses.py", "Patron courses and lessons"),

    # Phase 8: Specialized Services
    ("seed_home_delivery.py", "HomeDelivery patron delivery services"),
    ("seed_makerspace.py", "Makerspace equipment and certifications"),
    ("seed_rooms.py", "Library room reservations and bookings"),
]

# ---------------------------------------------------------------------------
# Phase 9: Demo-critical additions (not in run_all_seeds.py)
# ---------------------------------------------------------------------------
DEMO_SCRIPTS = [
    ("seed_branches.py", "Library branches and locations"),
    ("seed_learning_journeys.py", "Learning journey personas (Carmen, Amir, Sofia)"),
    ("seed_indie_content.py", "Indie author content"),
    ("seed_indie_audiobooks.py", "Indie audiobooks with narrators"),
    ("seed_circulation_scenarios.py", "Rich checkout/hold/fine scenarios"),
    ("seed_financial_data.py", "Fines, payments, fund management"),
    ("seed_learning_platform_comprehensive.py", "Learning platform (milestones, badges)"),
    ("seed_strategic_leadership.py", "Strategic plan with KPIs and milestones"),
    ("seed_programs.py", "Library programs (storytime, book clubs)"),
    ("seed_i18n_extended.py", "Multilingual catalog items"),
    ("seed_authentic_circulation.py", "6 months of circulation history (for charts)"),
    ("seed_community_engagement.py", "Reviews and community ratings"),
    ("seed_notifications.py", "Patron notifications"),
]


def run_script(script_name: str, scripts_dir: Path) -> bool:
    """Run a seed script and return True if successful."""
    script_path = scripts_dir / script_name
    if not script_path.exists():
        print(f"  Skipped (not found): {script_path.name}")
        return False

    try:
        print(f"  Running {script_name}...", end=" ", flush=True)
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300,
            env=os.environ.copy(),
        )

        if result.returncode == 0:
            print("OK")
            return True
        else:
            print("FAILED")
            # Show last few lines of error output
            stderr_lines = result.stderr.strip().splitlines()
            for line in stderr_lines[-3:]:
                print(f"    {line}")
            return False

    except subprocess.TimeoutExpired:
        print("TIMEOUT")
        return False
    except Exception as e:
        print(f"ERROR ({e})")
        return False


def run_phase(phase_name: str, scripts: list, scripts_dir: Path) -> tuple:
    """Run a phase of seed scripts. Returns (successful, failed, skipped) counts."""
    print(f"\n{'='*70}")
    print(f"  {phase_name}")
    print(f"{'='*70}\n")

    successful = 0
    failed = 0
    skipped = 0

    for i, (script_name, description) in enumerate(scripts, 1):
        print(f"  [{i}/{len(scripts)}] {description}")
        script_path = scripts_dir / script_name

        if not script_path.exists():
            print("    Skipped (file not found)")
            skipped += 1
        elif run_script(script_name, scripts_dir):
            successful += 1
        else:
            failed += 1

    return successful, failed, skipped


# ---------------------------------------------------------------------------
# Phase 10: Demo persona creation (inline)
# ---------------------------------------------------------------------------

DEMO_PERSONAS = [
    {
        "email": "margaret.chen@l30.org",
        "password": "DemoPatron1!",
        "first_name": "Margaret",
        "last_name": "Chen",
        "role": "PATRON",
        "description": "Power reader - active checkouts, holds, learning courses",
        "preferred_language": "en",
    },
    {
        "email": "david.jackson@l30.org",
        "password": "DemoPatron2!",
        "first_name": "David",
        "last_name": "Jackson",
        "role": "PATRON",
        "description": "Casual patron and parent, uses makerspace",
        "preferred_language": "en",
    },
    {
        "email": "elena.garcia@l30.org",
        "password": "DemoPatron3!",
        "first_name": "Elena",
        "last_name": "Garcia",
        "role": "PATRON",
        "description": "Spanish-speaking patron (i18n demo)",
        "preferred_language": "es",
    },
    {
        "email": "sarah.librarian@l30.org",
        "password": "DemoStaff1!",
        "first_name": "Sarah",
        "last_name": "Mitchell",
        "role": "STAFF",
        "description": "Head librarian - staff demo persona",
        "preferred_language": "en",
    },
]


async def seed_demo_personas():
    """Create named demo personas with onboarding pre-completed."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.core.security import hash_password
    from app.models.user import User, UserRole, PatronStatus, NoticePreference
    from app.core.datetime_utils import utc_now

    print(f"\n{'='*70}")
    print("  PHASE 10: Demo Persona Creation")
    print(f"{'='*70}\n")

    role_map = {
        "PATRON": UserRole.PATRON,
        "STAFF": UserRole.STAFF,
        "ADMIN": UserRole.ADMIN,
    }

    created = 0
    skipped = 0

    async with AsyncSessionLocal() as db:
        for persona in DEMO_PERSONAS:
            result = await db.execute(
                select(User).where(User.email == persona["email"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update onboarding_completed_at if not set
                if not existing.onboarding_completed_at:
                    existing.onboarding_completed_at = utc_now()
                    print(f"  Updated onboarding for: {persona['email']}")
                else:
                    print(f"  Already exists: {persona['email']}")
                skipped += 1
                continue

            try:
                user = User(
                    email=persona["email"],
                    password_hash=hash_password(persona["password"]),
                    first_name=persona["first_name"],
                    last_name=persona["last_name"],
                    role=role_map[persona["role"]],
                    is_active=True,
                    patron_status=PatronStatus.ACTIVE,
                    notice_preference=NoticePreference.EMAIL,
                    email_verified=True,
                    track_reading_history=True,
                    onboarding_completed_at=utc_now(),
                    # preferred_language not in User model yet
                )
                db.add(user)
                await db.flush()
                print(f"  Created: {persona['first_name']} {persona['last_name']} ({persona['email']})")
                created += 1
            except Exception as e:
                print(f"  Error creating {persona['email']}: {e}")

        await db.commit()

    print(f"\n  Personas: {created} created, {skipped} existing")
    return created, skipped


def print_demo_credentials():
    """Print all demo credentials for quick reference."""
    print(f"\n{'='*70}")
    print("  DEMO CREDENTIALS")
    print(f"{'='*70}\n")

    print("  Patron Accounts:")
    print("  ----------------------------------------------------------------")
    for p in DEMO_PERSONAS:
        if p["role"] == "PATRON":
            print(f"  {p['first_name']:10s} {p['last_name']:12s}  {p['email']:40s}  {p['password']}")

    print("\n  Staff / Admin Accounts:")
    print("  ----------------------------------------------------------------")
    for p in DEMO_PERSONAS:
        if p["role"] != "PATRON":
            print(f"  {p['first_name']:10s} {p['last_name']:12s}  {p['email']:40s}  {p['password']}")

    print(f"  {'Staff':10s} {'(built-in)':12s}  {'staff@l30.org':40s}  Staff123!")
    print(f"  {'Admin':10s} {'(built-in)':12s}  {'admin@l30.org':40s}  Admin123!")

    print("\n  URLs:")
    print("  ----------------------------------------------------------------")
    print("  Frontend:  http://localhost:5173")
    print("  Backend:   http://localhost:8000")
    print("  API Docs:  http://localhost:8000/docs")
    print(f"\n{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="LSC Demo Master Seed Script")
    parser.add_argument(
        "--skip-core",
        action="store_true",
        help="Skip phases 1-8 (core data) and only run demo additions + personas",
    )
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  LSC LIBRARY - DEMO MASTER SEED SCRIPT")
    print("=" * 70)

    # Verify DATABASE_URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("\n  ERROR: DATABASE_URL environment variable not set!")
        print("  Set it with: export DATABASE_URL='postgresql+asyncpg://...'")
        return 1

    db_host = db_url.rsplit("@", 1)[1] if "@" in db_url else db_url
    print(f"\n  Database: {db_host}")

    scripts_dir = Path(__file__).parent
    print(f"  Scripts:  {scripts_dir.absolute()}")

    total_ok = 0
    total_fail = 0
    total_skip = 0

    # Phase 1-8: Core data
    if not args.skip_core:
        ok, fail, skip = run_phase(
            "PHASES 1-8: Core Data", CORE_SCRIPTS, scripts_dir
        )
        total_ok += ok
        total_fail += fail
        total_skip += skip
    else:
        print("\n  Skipping phases 1-8 (--skip-core flag)")

    # Phase 9: Demo additions
    ok, fail, skip = run_phase(
        "PHASE 9: Demo Additions", DEMO_SCRIPTS, scripts_dir
    )
    total_ok += ok
    total_fail += fail
    total_skip += skip

    # Phase 10: Demo personas
    try:
        created, skipped = asyncio.run(seed_demo_personas())
        total_ok += created
        total_skip += skipped
    except Exception as e:
        print(f"\n  Phase 10 error: {e}")
        total_fail += 1

    # Summary
    print(f"\n{'='*70}")
    print("  SEEDING SUMMARY")
    print(f"{'='*70}")
    print(f"  Successful: {total_ok}")
    print(f"  Failed:     {total_fail}")
    print(f"  Skipped:    {total_skip}")

    if total_fail > 0:
        print(f"\n  {total_fail} item(s) failed. Check output above for details.")
        print("  Common fixes:")
        print("    1. Verify DATABASE_URL is correct")
        print("    2. Run: alembic upgrade head")
        print("    3. Check for constraint violations in failed scripts")

    # Print credentials
    print_demo_credentials()

    print("  Next steps:")
    print("    1. Start backend:  cd backend && uvicorn app.main:app --reload")
    print("    2. Start frontend: cd frontend && npm run dev")
    print("    3. Open walkthrough: docs/DEMO_WALKTHROUGH.md")
    print("")

    return 1 if total_fail > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
