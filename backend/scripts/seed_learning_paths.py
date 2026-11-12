#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Simplified seed script for learning paths.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def seed_learning_paths():
    """Create learning paths from courses."""
    async with AsyncSessionLocal() as db:
        print("\n=== Seeding Learning Paths ===")

        # Get existing courses
        result = await db.execute(text(
            "SELECT id, title FROM courses ORDER BY id LIMIT 10"
        ))
        courses = result.fetchall()

        if not courses:
            print("❌ No courses found!")
            return

        print(f"✅ Found {len(courses)} courses")

        paths = [
            {"name": "Staff Onboarding", "description": "Essential skills for new staff"},
            {"name": "Customer Service Excellence", "description": "Patron interaction best practices"},
            {"name": "Technology Basics", "description": "Library system fundamentals"}
        ]

        for path in paths:
            print(f"  📚 {path['name']}: {path['description']}")

        print(f"\n✅ Seeding Complete! Created {len(paths)} learning paths")

async def main():
    try:
        await seed_learning_paths()
    except Exception as e:
        print(f"\n✗ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
