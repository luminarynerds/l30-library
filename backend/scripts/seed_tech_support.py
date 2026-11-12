#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed script for Tech Support resources.

This script populates:
- Tech help resources (guides, videos, worksheets)
- Tech classes with future dates
- Tech help options (drop-in, appointments, hotline)
- Tech quick links grouped by section
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports - must be before app imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.tech_support import (
    TechHelpResource, TechClass, TechHelpOption, TechQuickLink, TechFacility,
    TechResourceCategory, TechClassLevel, TechFacilityKind,
)
from datetime import datetime, timedelta


def _next_monday() -> datetime:
    """Return the next Monday at midnight."""
    now = datetime.now()
    days_ahead = (7 - now.weekday()) % 7  # 0 = Monday
    if days_ahead == 0:
        days_ahead = 7
    return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)


async def seed_resources(db):
    """Seed tech help resources."""
    print("Seeding tech help resources...")

    # Check for existing data
    result = await db.execute(select(TechHelpResource).limit(1))
    if result.scalar_one_or_none():
        print("  Tech help resources already seeded, skipping.")
        return

    resources = [
        TechHelpResource(
            title="Computer Basics: Getting Started",
            description="Learn the fundamentals of using a computer, including mouse and keyboard skills, navigating the desktop, and managing files and folders.",
            category=TechResourceCategory.basics,
            format="Self-paced guide",
            duration="20 min",
            href="/guides/computer-basics",
            difficulty_level="beginner",
            sort_order=1,
        ),
        TechHelpResource(
            title="Internet Safety Checklist",
            description="Protect yourself online with this printable checklist covering passwords, phishing scams, safe browsing habits, and privacy settings.",
            category=TechResourceCategory.safety,
            format="Printable PDF",
            duration="10 min",
            href="/guides/scam-recognition",
            difficulty_level="beginner",
            sort_order=2,
        ),
        TechHelpResource(
            title="Email Essentials",
            description="Step-by-step lessons on creating an email account, sending and receiving messages, managing attachments, and avoiding spam.",
            category=TechResourceCategory.internet,
            format="Interactive lesson",
            duration="30 min",
            href="/guides/email-account",
            difficulty_level="beginner",
            sort_order=3,
        ),
        TechHelpResource(
            title="Smartphone Basics for Android & iPhone",
            description="Get comfortable with your smartphone. Covers making calls, sending texts, installing apps, taking photos, and adjusting settings.",
            category=TechResourceCategory.mobile,
            format="Video + worksheet",
            duration="25 min",
            href="/guides/smartphone-basics",
            difficulty_level="beginner",
            sort_order=4,
        ),
        TechHelpResource(
            title="Job Search with Library Computers",
            description="Use library computers and resources to search for jobs, create accounts on job boards, and submit applications online.",
            category=TechResourceCategory.apps,
            format="Step-by-step guide",
            duration="35 min",
            href="/guides/job-search",
            difficulty_level="beginner",
            sort_order=5,
        ),
        TechHelpResource(
            title="Printing & Scanning Help",
            description="Quick reference for using the library's printers and scanners, including wireless printing from your device.",
            category=TechResourceCategory.printing,
            format="Quick reference",
            duration="15 min",
            href="/guides/printing",
            difficulty_level="beginner",
            sort_order=6,
        ),
        TechHelpResource(
            title="Video Calling Made Easy",
            description="Learn how to make video calls using Zoom, FaceTime, and Google Meet. Covers setup, joining meetings, and troubleshooting audio/video.",
            category=TechResourceCategory.internet,
            format="Video tutorial",
            duration="20 min",
            href="/guides/video-calling",
            difficulty_level="beginner",
            sort_order=7,
        ),
        TechHelpResource(
            title="Streaming Music & Audiobooks",
            description="Discover how to stream music and audiobooks using the library's free digital services including Libby, hoopla, and Spotify.",
            category=TechResourceCategory.digital,
            format="Self-paced guide",
            duration="15 min",
            href="/guides/streaming",
            difficulty_level="beginner",
            sort_order=8,
        ),
    ]

    for r in resources:
        db.add(r)
        print(f"  Created resource: {r.title}")

    await db.commit()
    print(f"  Seeded {len(resources)} tech help resources.")


async def seed_classes(db):
    """Seed tech classes with future dates."""
    print("Seeding tech classes...")

    result = await db.execute(select(TechClass).limit(1))
    if result.scalar_one_or_none():
        print("  Tech classes already seeded, skipping.")
        return

    next_mon = _next_monday()

    classes = [
        TechClass(
            title="Computer Basics for Beginners",
            description="A hands-on introduction to using a computer. Learn mouse and keyboard skills, how to navigate Windows, and basic file management. No experience necessary.",
            date=next_mon.replace(hour=14),
            location="Main Meeting Room",
            level=TechClassLevel.beginner,
            instructor="Sarah Chen",
            capacity=12,
            enrolled=8,
        ),
        TechClass(
            title="Email & Internet Safety",
            description="Learn how to create and use an email account safely. We'll cover recognizing scams, creating strong passwords, and browsing the internet securely.",
            date=(next_mon + timedelta(days=3)).replace(hour=15),
            location="Computer Lab",
            level=TechClassLevel.beginner,
            instructor="Marcus Rivera",
            capacity=10,
            enrolled=6,
        ),
        TechClass(
            title="Smartphone Essentials",
            description="Bring your Android or iPhone and learn the basics: making calls, sending texts, downloading apps, taking photos, and adjusting settings.",
            date=(next_mon + timedelta(days=7)).replace(hour=10),
            location="Main Meeting Room",
            level=TechClassLevel.beginner,
            instructor="Library Staff",
            capacity=15,
            enrolled=3,
        ),
        TechClass(
            title="Resume Building Workshop",
            description="Use library computers to create a professional resume. We'll cover formatting, content tips, and how to save and email your finished resume.",
            date=(next_mon + timedelta(days=10)).replace(hour=13),
            location="Computer Lab",
            level=TechClassLevel.beginner,
            instructor="Marcus Rivera",
            capacity=10,
            enrolled=4,
        ),
        TechClass(
            title="Online Banking & Bill Pay",
            description="Learn how to safely manage your finances online. Covers setting up online banking, paying bills, and recognizing financial scams.",
            date=(next_mon + timedelta(days=14)).replace(hour=14),
            location="Main Meeting Room",
            level=TechClassLevel.intermediate,
            instructor="Sarah Chen",
            capacity=12,
            enrolled=2,
        ),
        TechClass(
            title="Video Calling for Beginners",
            description="Learn how to make video calls to family and friends using Zoom, FaceTime, and Google Meet. We'll practice joining and starting calls.",
            date=(next_mon + timedelta(days=17)).replace(hour=11),
            location="Computer Lab",
            level=TechClassLevel.beginner,
            instructor="Library Staff",
            capacity=8,
            enrolled=1,
        ),
    ]

    for c in classes:
        db.add(c)
        print(f"  Created class: {c.title} ({c.date.strftime('%b %d at %I %p')})")

    await db.commit()
    print(f"  Seeded {len(classes)} tech classes.")


async def seed_help_options(db):
    """Seed tech help options."""
    print("Seeding tech help options...")

    result = await db.execute(select(TechHelpOption).limit(1))
    if result.scalar_one_or_none():
        print("  Tech help options already seeded, skipping.")
        return

    options = [
        TechHelpOption(
            title="Drop-In Tech Help",
            description="Walk in anytime during open hours for help with computers, phones, tablets, printing, or other technology questions. No appointment needed.",
            schedule="Mon\u2013Fri 10 AM\u20135 PM, Sat 11 AM\u20133 PM",
            location="Computer Lab",
            icon="help-circle",
            sort_order=1,
        ),
        TechHelpOption(
            title="Tech Appointments",
            description="Book a free one-on-one session with a tech helper for personalized assistance. Sessions are 30 minutes and can be in person or by phone.",
            schedule="By appointment",
            location="Tech Help Desk",
            phone="(555) 555-0100",
            icon="calendar",
            sort_order=2,
        ),
        TechHelpOption(
            title="Tech Help Hotline",
            description="Call our tech help hotline to get answers to quick technology questions over the phone. Our staff can walk you through common issues.",
            schedule="Tue\u2013Thu 2\u20134 PM",
            phone="(555) 555-0101",
            icon="phone",
            sort_order=3,
        ),
    ]

    for o in options:
        db.add(o)
        print(f"  Created help option: {o.title}")

    await db.commit()
    print(f"  Seeded {len(options)} tech help options.")


async def seed_quick_links(db):
    """Seed tech quick links grouped by section."""
    print("Seeding tech quick links...")

    result = await db.execute(select(TechQuickLink).limit(1))
    if result.scalar_one_or_none():
        print("  Tech quick links already seeded, skipping.")
        return

    sections = [
        {
            "section_title": "Internet & WiFi",
            "section_icon": "wifi",
            "links": [
                ("Connect to Library WiFi", "/wifi"),
                ("WiFi Hotspot Lending", "/catalog?q=hotspot"),
                ("Internet Safety Guide", "/guides/scam-recognition"),
            ],
        },
        {
            "section_title": "Devices",
            "section_icon": "laptop",
            "links": [
                ("Phone Setup Help", "/guides/smartphone-basics"),
                ("Tablet & iPad Guide", "/guides/tablet-basics"),
                ("Laptop Basics", "/guides/computer-basics"),
            ],
        },
        {
            "section_title": "Learning",
            "section_icon": "book-open",
            "links": [
                ("Free Online Courses", "/databases?category=learning"),
                ("LinkedIn Learning Access", "/databases?q=linkedin"),
                ("Job Search Resources", "/guides/job-search"),
            ],
        },
        {
            "section_title": "Printing & Scanning",
            "section_icon": "printer",
            "links": [
                ("Wireless Printing Setup", "/guides/printing"),
                ("Check Print Jobs", "/print-jobs"),
                ("Scan Documents", "/guides/scanning"),
            ],
        },
    ]

    order = 1
    for section in sections:
        for name, url in section["links"]:
            link = TechQuickLink(
                section_title=section["section_title"],
                section_icon=section["section_icon"],
                name=name,
                url=url,
                sort_order=order,
            )
            db.add(link)
            print(f"  Created quick link: [{section['section_title']}] {name}")
            order += 1

    await db.commit()
    print(f"  Seeded {order - 1} tech quick links.")


async def seed_facilities(db):
    """Seed tech facility facts (computer-lab stats, printers).

    Idempotent: no-ops if rows already exist. The tech_facilities_001
    migration also seeds these rows; this guard keeps both paths safe.
    """
    print("Seeding tech facilities...")

    result = await db.execute(select(TechFacility).limit(1))
    if result.scalar_one_or_none():
        print("  Tech facilities already seeded, skipping.")
        return

    facilities = [
        TechFacility(kind=TechFacilityKind.computer_lab, label="Computers available",
                     value="12", sort_order=1),
        TechFacility(kind=TechFacilityKind.computer_lab, label="B&W printing",
                     value="$0.10/page", sort_order=2),
        TechFacility(kind=TechFacilityKind.computer_lab, label="Color printing",
                     value="$0.25/page", sort_order=3),
        TechFacility(kind=TechFacilityKind.computer_lab, label="WiFi",
                     value="Free throughout building", sort_order=4),
        TechFacility(kind=TechFacilityKind.printer, label="Main Floor Computer Lab",
                     value="B&W and color printing available. Use library computers or "
                           "bring your own device via WiFi.",
                     sort_order=1),
        TechFacility(kind=TechFacilityKind.printer, label="Second Floor Reference Area",
                     value="B&W printing only.", sort_order=2),
    ]

    for f in facilities:
        db.add(f)
        print(f"  Created facility: [{f.kind.value}] {f.label}")

    await db.commit()
    print(f"  Seeded {len(facilities)} tech facilities.")


async def main():
    """Main seed function."""
    print("=" * 60)
    print("Seeding Tech Support Data")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        try:
            # Check if tech support tables exist
            from sqlalchemy import text as sa_text
            try:
                await db.execute(sa_text("SELECT 1 FROM tech_help_resources LIMIT 0"))
            except Exception:
                await db.rollback()
                print("  Tech support tables not yet created, skipping.")
                return

            await seed_resources(db)
            await seed_classes(db)
            await seed_help_options(db)
            await seed_quick_links(db)
            await seed_facilities(db)

            print("\n" + "=" * 60)
            print("Tech support data seeded successfully!")
            print("=" * 60)

        except Exception as e:
            print(f"\nERROR during seeding: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
