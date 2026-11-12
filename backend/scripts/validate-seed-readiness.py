#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate that database schema is ready for seed scripts."""

import asyncio
from sqlalchemy import text
import sys

# Add parent directory to path
sys.path.insert(0, '/opt/l30/backend')

from app.core.database import engine


async def validate():
    """Validate seed script readiness by checking required tables."""
    try:
        async with engine.begin() as conn:
            # Get list of all tables
            result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
            tables = {row[0] for row in result.fetchall()}

            # Map of seed scripts to required tables
            seeds = {
                'seed_reading_lists.py': ['reading_lists', 'users'],
                'seed_wellness_growth.py': ['wellness_entries', 'users'],
                'seed_perfectionism_antidotes.py': ['perfectionism_antidotes', 'users'],
                'seed_device_lending.py': ['device_lending', 'users', 'catalog_items'],
                'seed_joy_capture.py': ['joy_capture', 'users'],
                'seed_peer_support.py': ['peer_support_entries', 'users'],
            }

            all_ready = True
            print("=== Seed Script Readiness ===\n")

            for script, required in seeds.items():
                missing = [t for t in required if t not in tables]
                if missing:
                    print(f"❌ {script}: missing {missing}")
                    all_ready = False
                else:
                    print(f"✅ {script}: ready")

            if all_ready:
                print("\n✅ SUCCESS: All seed scripts are ready to run")
            else:
                print("\n❌ FAILURE: Some seed scripts cannot run due to missing tables")

            return all_ready
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(validate())
    sys.exit(0 if success else 1)
