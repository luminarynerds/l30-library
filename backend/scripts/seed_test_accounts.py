#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed script to populate test accounts into the database for comprehensive testing.

This script creates four test accounts with different roles:
1. Admin Account - Full system access
2. Staff Account - Staff member operations
3. Patron 1 - Regular patron with no activity
4. Patron 2 - Active patron for testing activity features

Each account includes properly hashed passwords and can be used for API testing.
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole, PatronStatus, NoticePreference


# Test account definitions - All required roles for comprehensive testing
TEST_ACCOUNTS = [
    # SUPER_ADMIN - Full system access
    {
        "email": "superadmin@l30.org",
        "password": "SuperAdmin123!",
        "first_name": "Super",
        "last_name": "Admin",
        "role": UserRole.SUPER_ADMIN,
        "description": "Super Admin - Full system access"
    },
    # ADMIN - System administration and user management
    {
        "email": "admin@l30.org",
        "password": "Admin123!",
        "first_name": "Admin",
        "last_name": "User",
        "role": UserRole.ADMIN,
        "description": "Admin Account - Full system access"
    },
    # DIRECTOR - Library Director with sensitive operations access
    {
        "email": "director@l30.org",
        "password": "Director123!",
        "first_name": "Library",
        "last_name": "Director",
        "role": UserRole.DIRECTOR,
        "description": "Director Account - Access to sensitive operations"
    },
    # LEGAL - Legal counsel with law enforcement request access
    {
        "email": "legal@l30.org",
        "password": "Legal123!",
        "first_name": "Legal",
        "last_name": "Counsel",
        "role": UserRole.LEGAL,
        "description": "Legal Account - Law enforcement request access"
    },
    # STAFF - General library staff
    {
        "email": "staff@l30.org",
        "password": "Staff123!",
        "first_name": "Library",
        "last_name": "Staff",
        "role": UserRole.STAFF,
        "description": "Staff Account - Staff member operations"
    },
    # STAFF - Multiple staff for different branches
    {
        "email": "staff.main@l30.org",
        "password": "Staff123!",
        "first_name": "Main",
        "last_name": "Branch Staff",
        "role": UserRole.STAFF,
        "description": "Staff Account - Main branch operations"
    },
    {
        "email": "staff.downtown@l30.org",
        "password": "Staff123!",
        "first_name": "Downtown",
        "last_name": "Branch Staff",
        "role": UserRole.STAFF,
        "description": "Staff Account - Downtown branch operations"
    },
    # PATRON - Regular patron
    {
        "email": "patron.reader@l30.org",
        "password": "Patron123!",
        "first_name": "Reader",
        "last_name": "Patron",
        "role": UserRole.PATRON,
        "description": "Patron 1 - Regular patron"
    },
    # PATRON - Active patron with testing scenarios
    {
        "email": "patron.active@l30.org",
        "password": "Patron123!",
        "first_name": "Active",
        "last_name": "Member",
        "role": UserRole.PATRON,
        "description": "Patron 2 - Active patron for testing"
    },
    # CHILD - Child patron (COPPA compliance) - Will link to guardian@l30.org
    {
        "email": "child@l30.org",
        "password": "Child123!",
        "first_name": "Child",
        "last_name": "User",
        "role": UserRole.CHILD,
        "description": "Child Patron - COPPA compliance test"
    },
    # PATRON - Guardian for child patron
    {
        "email": "guardian@l30.org",
        "password": "Guardian123!",
        "first_name": "Guardian",
        "last_name": "Parent",
        "role": UserRole.PATRON,
        "description": "Parent/Guardian - For child patron testing"
    },
    # BOOKMOBILE - Bookmobile service staff
    {
        "email": "bookmobile@l30.org",
        "password": "Bookmobile123!",
        "first_name": "Book",
        "last_name": "Mobile",
        "role": UserRole.BOOKMOBILE,
        "description": "Bookmobile Staff - Mobile library services"
    },
    # HOMEBOND - HomeDelivery delivery service patron
    {
        "email": "home.delivery@l30.org",
        "password": "HomeDelivery123!",
        "first_name": "Home",
        "last_name": "Bound",
        "role": UserRole.HOMEBOND,
        "description": "HomeDelivery Patron - Home delivery services"
    },
    # ==========================================================================
    # Smoke Test Personas
    # ==========================================================================
    # Circulation Clerk - front_desk staff role
    {
        "email": "test-circ@l30.org",
        "password": os.environ.get("SMOKE_TEST_PASSWORD", "SmokeTest123!"),
        "first_name": "Smoke",
        "last_name": "Circ",
        "role": UserRole.STAFF,
        "staff_role": "front_desk",
        "description": "Smoke Test - Circulation Clerk (front_desk)",
    },
    # Cataloger - cataloger staff role
    {
        "email": "test-cataloger@l30.org",
        "password": os.environ.get("SMOKE_TEST_PASSWORD", "SmokeTest123!"),
        "first_name": "Smoke",
        "last_name": "Cataloger",
        "role": UserRole.STAFF,
        "staff_role": "cataloger",
        "description": "Smoke Test - Cataloger",
    },
    # Youth Services - youth_services staff role
    {
        "email": "test-youth@l30.org",
        "password": os.environ.get("SMOKE_TEST_PASSWORD", "SmokeTest123!"),
        "first_name": "Smoke",
        "last_name": "Youth",
        "role": UserRole.STAFF,
        "staff_role": "youth_services",
        "description": "Smoke Test - Youth Services",
    },
    # Acquisitions Librarian - cataloger staff role
    {
        "email": "test-acquisitions@l30.org",
        "password": os.environ.get("SMOKE_TEST_PASSWORD", "SmokeTest123!"),
        "first_name": "Smoke",
        "last_name": "Acquisitions",
        "role": UserRole.STAFF,
        "staff_role": "cataloger",
        "description": "Smoke Test - Acquisitions Librarian",
    },
    # Reference Librarian - front_desk staff role
    {
        "email": "test-reference@l30.org",
        "password": os.environ.get("SMOKE_TEST_PASSWORD", "SmokeTest123!"),
        "first_name": "Smoke",
        "last_name": "Reference",
        "role": UserRole.STAFF,
        "staff_role": "front_desk",
        "description": "Smoke Test - Reference Librarian",
    },
    # Director - library director role
    {
        "email": "test-director@l30.org",
        "password": os.environ.get("SMOKE_TEST_PASSWORD", "SmokeTest123!"),
        "first_name": "Smoke",
        "last_name": "Director",
        "role": UserRole.DIRECTOR,
        "description": "Smoke Test - Library Director",
    },
    # Patron
    {
        "email": "test-patron@l30.org",
        "password": os.environ.get("SMOKE_TEST_PASSWORD", "SmokeTest123!"),
        "first_name": "Smoke",
        "last_name": "Patron",
        "role": UserRole.PATRON,
        "description": "Smoke Test - Patron",
    },
    # Child Patron - COPPA compliance testing
    {
        "email": "test-child@l30.org",
        "password": os.environ.get("SMOKE_TEST_PASSWORD", "SmokeTest123!"),
        "first_name": "Smoke",
        "last_name": "Child",
        "role": UserRole.CHILD,
        "description": "Smoke Test - Child Patron",
    },
    # Indie Author
    {
        "email": "test-indie@l30.org",
        "password": os.environ.get("SMOKE_TEST_PASSWORD", "SmokeTest123!"),
        "first_name": "Smoke",
        "last_name": "Indie",
        "role": UserRole.PATRON,
        "description": "Smoke Test - Indie Author",
    },
]


async def seed_test_accounts():
    """
    Seed test accounts into the database.

    Creates or updates test accounts, checking for existing accounts to avoid
    duplicates. All accounts are created with proper password hashing and
    configured for testing.

    Special handling:
    - Guardian is created first (if needed)
    - Child account is linked to guardian via parent_guardian_id
    """
    async with AsyncSessionLocal() as db:
        print("\n" + "=" * 70)
        print("SEEDING TEST ACCOUNTS")
        print("=" * 70 + "\n")

        created_count = 0
        skipped_count = 0
        guardian_id = None

        # First pass: Create guardian account (needed for child linkage)
        for account_data in TEST_ACCOUNTS:
            if account_data["role"] == UserRole.PATRON and account_data.get("description", "").startswith("Parent/Guardian"):
                email = account_data["email"]
                result = await db.execute(
                    select(User).where(User.email == email)
                )
                guardian = result.scalar_one_or_none()

                if guardian:
                    guardian_id = guardian.id
                    print(f"⊘ SKIPPED: {email} (Guardian - already exists)")
                    print("  Reason: Account already exists\n")
                    skipped_count += 1
                else:
                    try:
                        guardian = User(
                            email=email,
                            password_hash=hash_password(account_data["password"]),
                            first_name=account_data["first_name"],
                            last_name=account_data["last_name"],
                            role=account_data["role"],
                            staff_role=account_data.get("staff_role"),
                            is_active=True,
                            patron_status=PatronStatus.ACTIVE,
                            notice_preference=NoticePreference.EMAIL,
                            email_verified=True,
                            track_reading_history=True,
                        )
                        db.add(guardian)
                        await db.flush()
                        guardian_id = guardian.id
                        # Commit now, not just flush. A later account's
                        # failure calls db.rollback(), which -- on a session
                        # that only ever flushed -- would silently discard
                        # this guardian (and every other account created
                        # this run) along with it, even though each one
                        # printed "CREATED" and never errored itself.
                        await db.commit()

                        print(f"✓ CREATED: {email} (Guardian Account)")
                        print(f"  Name: {guardian.full_name}")
                        print(f"  Role: {guardian.role.value}")
                        print(f"  Description: {account_data['description']}")
                        print(f"  User ID: {guardian.id}\n")

                        created_count += 1
                    except Exception as e:
                        await db.rollback()
                        print(f"✗ ERROR: {email} (Guardian)")
                        print(f"  Reason: {str(e)}\n")

        # Second pass: Create all other accounts (including child linked to guardian)
        for account_data in TEST_ACCOUNTS:
            # Skip guardian (already created)
            if account_data["role"] == UserRole.PATRON and account_data.get("description", "").startswith("Parent/Guardian"):
                continue

            email = account_data["email"]

            # Check if account already exists
            result = await db.execute(
                select(User).where(User.email == email)
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"⊘ SKIPPED: {email}")
                print(f"  ({account_data['description']})")
                print("  Reason: Account already exists\n")
                skipped_count += 1
                continue

            # Create new user account
            try:
                parent_id = None
                if account_data["role"] == UserRole.CHILD and guardian_id:
                    parent_id = guardian_id

                user = User(
                    email=email,
                    password_hash=hash_password(account_data["password"]),
                    first_name=account_data["first_name"],
                    last_name=account_data["last_name"],
                    role=account_data["role"],
                    staff_role=account_data.get("staff_role"),
                    is_active=True,
                    patron_status=PatronStatus.ACTIVE,
                    notice_preference=NoticePreference.EMAIL,
                    email_verified=True,  # Skip verification for test accounts
                    track_reading_history=True,
                    parent_guardian_id=parent_id,  # Link child to guardian
                )

                db.add(user)
                await db.flush()  # Flush to get the ID
                # Commit now, not just flush -- see the guardian-pass
                # comment above. Without this, one bad account later in the
                # loop calls db.rollback() and silently discards every
                # account created earlier in the same run, even though they
                # each printed "CREATED" and never raised.
                await db.commit()

                print(f"✓ CREATED: {email}")
                print(f"  Name: {user.full_name}")
                print(f"  Role: {account_data['role'].value}")
                print(f"  Description: {account_data['description']}")
                if parent_id:
                    print(f"  Guardian ID: {parent_id}")
                print(f"  User ID: {user.id}\n")

                created_count += 1

            except IntegrityError as e:
                await db.rollback()
                print(f"✗ ERROR: {email}")
                print(f"  Reason: {str(e)}\n")
                continue
            except Exception as e:
                await db.rollback()
                print(f"✗ ERROR: {email}")
                print(f"  Reason: {str(e)}\n")
                continue

        # Commit all changes
        try:
            await db.commit()
            print("=" * 70)
            print(f"SEED COMPLETE: {created_count} created, {skipped_count} skipped")
            print("=" * 70 + "\n")
            return created_count, skipped_count
        except Exception as e:
            await db.rollback()
            print(f"\n✗ COMMIT FAILED: {str(e)}\n")
            raise


async def verify_test_accounts():
    """
    Verify that test accounts were created successfully.

    Queries the database to confirm all test accounts exist and have
    the correct properties.
    """
    async with AsyncSessionLocal() as db:
        print("=" * 70)
        print("VERIFYING TEST ACCOUNTS")
        print("=" * 70 + "\n")

        for account_data in TEST_ACCOUNTS:
            email = account_data["email"]

            # Query for the user
            result = await db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()

            if user:
                print(f"✓ VERIFIED: {email}")
                print(f"  ID: {user.id}")
                print(f"  Name: {user.full_name}")
                print(f"  Role: {user.role.value}")
                print(f"  Status: {user.patron_status.value}")
                print(f"  Email Verified: {user.email_verified}")
                print(f"  Active: {user.is_active}")
                print(f"  Created: {user.created_at}\n")
            else:
                print(f"✗ NOT FOUND: {email}\n")

        # Print summary
        result = await db.execute(
            select(User).where(User.email.in_([acc["email"] for acc in TEST_ACCOUNTS]))
        )
        accounts = result.scalars().all()
        print("=" * 70)
        print(f"VERIFICATION COMPLETE: {len(accounts)}/{len(TEST_ACCOUNTS)} accounts found")
        print("=" * 70 + "\n")

        return len(accounts) == len(TEST_ACCOUNTS)


async def print_test_credentials():
    """
    Print test credentials for reference.

    Displays all test account credentials in a format that's easy to
    copy and use for manual testing.
    """
    print("=" * 70)
    print("TEST ACCOUNT CREDENTIALS")
    print("=" * 70 + "\n")

    for account_data in TEST_ACCOUNTS:
        print(f"Account: {account_data['description']}")
        print(f"  Email:    {account_data['email']}")
        print(f"  Password: {account_data['password']}")
        print(f"  Role:     {account_data['role'].value}\n")

    print("=" * 70)
    print("BASE API URL: http://localhost:8000/api/v1")
    print("=" * 70 + "\n")


async def main():
    """Main entry point for the seed script."""
    try:
        # Print credentials first
        await print_test_credentials()

        # Seed accounts
        created, skipped = await seed_test_accounts()

        # Verify accounts
        success = await verify_test_accounts()

        if success or created > 0:
            print("✓ TEST ACCOUNTS SEED SCRIPT COMPLETED SUCCESSFULLY\n")
            return 0
        else:
            print("✗ TEST ACCOUNTS SEED SCRIPT FAILED\n")
            return 1

    except Exception as e:
        print(f"\n✗ Error during seeding: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
