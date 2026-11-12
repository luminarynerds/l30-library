#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Post-migration verification script to check schema integrity."""

import asyncio
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine
import sys

# Add parent directory to path
sys.path.insert(0, '/opt/l30/backend')

from app.core.database import engine


async def verify():
    """Verify all critical tables exist after migration."""
    try:
        async with engine.begin() as conn:
            # Get list of all tables
            result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
            tables = {row[0] for row in result.fetchall()}

            # Critical tables that must exist
            critical = [
                'branches', 'device_lending', 'joy_capture',
                'peer_support_entries', 'user_personalization',
                'catalog_items', 'users', 'checkouts', 'holds',
                'board_audit_logs', 'board_documents', 'board_document_versions',
                'law_enforcement_audit_logs'
            ]

            missing = [t for t in critical if t not in tables]

            if missing:
                print(f"❌ FAILURE: Missing critical tables: {missing}")
                return False

            print(f"✅ SUCCESS: All {len(critical)} critical tables present")
            print(f"   Total tables in schema: {len(tables)}")

            # List all tables for verification
            print("\n   All tables:")
            for table in sorted(tables):
                print(f"     - {table}")

            return True
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(verify())
    sys.exit(0 if success else 1)
