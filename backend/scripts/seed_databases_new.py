#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed research databases with corrected models.

Usage:
  python scripts/seed_databases_new.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import date, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.database_subscription import (
    DatabaseVendor,
    DatabaseSubscription,
    ProxyConfiguration,
    SubscriptionStatus,
    DatabaseCategory,
    ProxyType,
)


async def seed_proxy_config(session: AsyncSession):
    """Create EZproxy configuration if it doesn't already exist."""
    # Check if proxy config already exists
    result = await session.execute(
        select(ProxyConfiguration).where(ProxyConfiguration.name == "Primary EZproxy").limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing:
        print("  Proxy configuration already exists, skipping...")
        return existing.id

    proxy_config = ProxyConfiguration(
        name="Primary EZproxy",
        proxy_type=ProxyType.EZPROXY.value,
        ezproxy_base_url="https://proxy.library2030.org",
        ezproxy_login_path="/login",
        ezproxy_url_param="url",
        requires_library_card=True,
        is_active=True,
        is_default=True,
    )
    session.add(proxy_config)
    await session.flush()
    return proxy_config.id


async def seed_vendors(session: AsyncSession):
    """Create sample database vendors, skipping any that already exist."""
    vendors_data = [
        {
            "name": "Gale/Cengage Learning",
            "short_name": "Gale",
            "website": "https://www.gale.cengage.com",
            "support_email": "support@gale.cengage.com",
            "support_phone": "(800) 877-4253",
            "account_rep_name": "John Smith",
            "account_rep_email": "john.smith@gale.cengage.com",
        },
        {
            "name": "EBSCO Information Services",
            "short_name": "EBSCO",
            "website": "https://www.ebsco.com",
            "support_email": "techsupport@ebscohost.com",
            "support_phone": "(800) 653-2726",
            "account_rep_name": "Sarah Johnson",
            "account_rep_email": "sjohnson@ebsco.com",
        },
        {
            "name": "ProQuest",
            "short_name": "ProQuest",
            "website": "https://www.proquest.com",
            "support_email": "support@proquest.com",
            "support_phone": "(734) 761-4700",
            "account_rep_name": "Michael Chen",
            "account_rep_email": "mchen@proquest.com",
        },
        {
            "name": "JSTOR",
            "short_name": "JSTOR",
            "website": "https://www.jstor.org",
            "support_email": "support@jstor.org",
            "support_phone": "(609) 258-4900",
            "account_rep_name": "Emily Davis",
            "account_rep_email": "edavis@jstor.org",
        },
    ]

    vendors = []
    created_count = 0
    for vendor_data in vendors_data:
        # Check if vendor already exists by name (unique constraint)
        result = await session.execute(
            select(DatabaseVendor).where(DatabaseVendor.name == vendor_data["name"]).limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            vendors.append(existing)
            print(f"  Vendor already exists: {vendor_data['name']}")
        else:
            vendor = DatabaseVendor(**vendor_data)
            session.add(vendor)
            vendors.append(vendor)
            created_count += 1

    await session.flush()
    print(f"  Created {created_count} new vendors ({len(vendors) - created_count} already existed)")
    return vendors


async def seed_databases(session: AsyncSession, proxy_config_id: int, vendors: list):
    """Create sample database subscriptions, skipping any that already exist."""
    today = date.today()
    one_year_from_now = today + timedelta(days=365)

    databases_data = [
        {
            "name": "Academic Complete",
            "short_name": "Academic Complete",
            "description": "Comprehensive academic database with thousands of full-text journals, magazines, and research publications",
            "category": DatabaseCategory.ACADEMIC.value,
            "subjects": ["General", "Science", "Technology", "Business", "Health"],
            "keywords": ["academic", "research", "journals", "full-text"],
            "vendor_id": vendors[1].id,  # EBSCO
            "access_url": "https://search.ebscohost.com",
            "auth_method": "barcode",
            "subscription_start": today,
            "subscription_end": one_year_from_now,
            "status": SubscriptionStatus.ACTIVE.value,
            "proxy_config_id": proxy_config_id,
            "requires_proxy": True,
        },
        {
            "name": "JSTOR",
            "short_name": "JSTOR",
            "description": "Digital library of academic journals, books, and primary sources across humanities and social sciences",
            "category": DatabaseCategory.ACADEMIC.value,
            "subjects": ["History", "Literature", "Science", "Social Sciences"],
            "keywords": ["jstor", "academic", "journals", "archives"],
            "vendor_id": vendors[3].id,  # JSTOR
            "access_url": "https://www.jstor.org",
            "auth_method": "username",
            "subscription_start": today,
            "subscription_end": one_year_from_now,
            "status": SubscriptionStatus.ACTIVE.value,
            "proxy_config_id": proxy_config_id,
            "requires_proxy": True,
        },
        {
            "name": "ProQuest Dissertations & Theses",
            "short_name": "ProQuest Dissertations",
            "description": "Comprehensive collection of dissertations and theses from universities worldwide",
            "category": DatabaseCategory.ACADEMIC.value,
            "subjects": ["Education", "Research", "Academic"],
            "keywords": ["dissertations", "theses", "academic", "research"],
            "vendor_id": vendors[2].id,  # ProQuest
            "access_url": "https://www.proquest.com/dissertations",
            "auth_method": "barcode",
            "subscription_start": today,
            "subscription_end": one_year_from_now,
            "status": SubscriptionStatus.ACTIVE.value,
            "proxy_config_id": proxy_config_id,
            "requires_proxy": True,
        },
        {
            "name": "Ancestry.com Library Edition",
            "short_name": "Ancestry",
            "description": "Genealogy research database with billions of names and historical records",
            "category": DatabaseCategory.GENEALOGY.value,
            "subjects": ["Genealogy", "Family History", "Records"],
            "keywords": ["genealogy", "family", "ancestry", "records"],
            "vendor_id": vendors[0].id,  # Gale
            "access_url": "https://www.ancestrylibrary.com",
            "auth_method": "ip",
            "subscription_start": today,
            "subscription_end": one_year_from_now,
            "status": SubscriptionStatus.ACTIVE.value,
            "proxy_config_id": proxy_config_id,
            "requires_proxy": False,
        },
        {
            "name": "Business Source Complete",
            "short_name": "Business Source",
            "description": "Leading business research database with coverage of business disciplines, economics, and industry data",
            "category": DatabaseCategory.BUSINESS.value,
            "subjects": ["Business", "Economics", "Management"],
            "keywords": ["business", "economics", "management", "finance"],
            "vendor_id": vendors[1].id,  # EBSCO
            "access_url": "https://search.ebscohost.com/login.aspx",
            "auth_method": "barcode",
            "subscription_start": today,
            "subscription_end": one_year_from_now,
            "status": SubscriptionStatus.ACTIVE.value,
            "proxy_config_id": proxy_config_id,
            "requires_proxy": True,
        },
        {
            "name": "Consumer Health Complete",
            "short_name": "Consumer Health",
            "description": "Health information database for consumer health topics, wellness, and medical conditions",
            "category": DatabaseCategory.HEALTH.value,
            "subjects": ["Health", "Medicine", "Wellness"],
            "keywords": ["health", "medical", "wellness", "fitness"],
            "vendor_id": vendors[1].id,  # EBSCO
            "access_url": "https://search.ebscohost.com/login.aspx",
            "auth_method": "barcode",
            "subscription_start": today,
            "subscription_end": one_year_from_now,
            "status": SubscriptionStatus.ACTIVE.value,
            "proxy_config_id": proxy_config_id,
            "requires_proxy": True,
        },
        {
            "name": "LexisNexis Academic",
            "short_name": "LexisNexis",
            "description": "Legal and news research database with comprehensive coverage of laws, cases, and news articles",
            "category": DatabaseCategory.LEGAL.value,
            "subjects": ["Law", "News", "Government"],
            "keywords": ["legal", "law", "news", "cases"],
            "vendor_id": vendors[0].id,  # Gale
            "access_url": "https://www.lexisnexis.com/en-us/products/lexis-nexis-academic.page",
            "auth_method": "username",
            "subscription_start": today,
            "subscription_end": one_year_from_now,
            "status": SubscriptionStatus.ACTIVE.value,
            "proxy_config_id": proxy_config_id,
            "requires_proxy": True,
        },
        {
            "name": "Hoopla",
            "short_name": "Hoopla",
            "description": "Digital media collection with movies, TV shows, music, ebooks, and audiobooks for instant streaming",
            "category": DatabaseCategory.STREAMING_VIDEO.value,
            "subjects": ["Entertainment", "Movies", "Music", "Books"],
            "keywords": ["streaming", "movies", "music", "ebooks", "audiobooks"],
            "vendor_id": vendors[0].id,  # Gale
            "access_url": "https://www.hoopladigital.com",
            "auth_method": "barcode",
            "subscription_start": today,
            "subscription_end": one_year_from_now,
            "status": SubscriptionStatus.ACTIVE.value,
            "proxy_config_id": proxy_config_id,
            "requires_proxy": False,
        },
        {
            "name": "Kanopy",
            "short_name": "Kanopy",
            "description": "Streaming video platform with documentaries, films, and educational content",
            "category": DatabaseCategory.STREAMING_VIDEO.value,
            "subjects": ["Films", "Documentaries", "Education"],
            "keywords": ["streaming", "video", "documentaries", "films"],
            "vendor_id": vendors[0].id,  # Gale
            "access_url": "https://www.kanopy.com",
            "auth_method": "barcode",
            "subscription_start": today,
            "subscription_end": one_year_from_now,
            "status": SubscriptionStatus.ACTIVE.value,
            "proxy_config_id": proxy_config_id,
            "requires_proxy": False,
        },
    ]

    databases = []
    created_count = 0
    for db_data in databases_data:
        # Check if database subscription already exists by name
        result = await session.execute(
            select(DatabaseSubscription).where(DatabaseSubscription.name == db_data["name"]).limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            databases.append(existing)
            print(f"  Database already exists: {db_data['name']}")
        else:
            database = DatabaseSubscription(**db_data)
            session.add(database)
            databases.append(database)
            created_count += 1

    await session.flush()
    print(f"  Created {created_count} new databases ({len(databases) - created_count} already existed)")
    return databases


async def main():
    """Run the seed operation."""
    async with AsyncSessionLocal() as session:
        try:
            print("\n" + "=" * 70)
            print("🗄️  LSC Library Database Seeder")
            print("=" * 70 + "\n")

            # Seed proxy configuration
            print("📡 Setting up proxy configuration...")
            proxy_config_id = await seed_proxy_config(session)
            print("  ✅ Proxy configuration ready\n")

            # Seed vendors
            print("🏢 Seeding database vendors...")
            vendors = await seed_vendors(session)
            print(f"  ✅ {len(vendors)} vendors ready\n")

            # Seed databases
            print("📚 Seeding databases...")
            databases = await seed_databases(session, proxy_config_id, vendors)
            print(f"  ✅ {len(databases)} databases ready\n")

            # Commit
            await session.commit()

            print("=" * 70)
            print("✅ Database seeding complete!")
            print("=" * 70)
            print("\n📊 Summary:")
            print(f"   • {len(vendors)} vendors ready")
            print(f"   • {len(databases)} databases ready")
            print("\nAvailable databases:")
            for db in databases:
                print(f"   • {db.name}")

            print("\n💡 Next: Test the /api/v1/databases endpoint\n")

        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
