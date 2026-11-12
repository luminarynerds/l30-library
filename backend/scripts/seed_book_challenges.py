#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed script for book challenges and intellectual freedom resources.

Creates sample book challenge records to demonstrate the library's
commitment to intellectual freedom and transparent handling of
material reconsideration requests.
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.book_challenge import (
    BookChallenge, IntellectualFreedomResource,
    ChallengeStatus, ChallengeOutcome, ChallengeReason
)
from app.core.config import get_settings

settings = get_settings()

# Sample book challenges with various outcomes
CHALLENGES = [
    {
        "title": "Gender Queer: A Memoir",
        "author": "Maia Kobabe",
        "isbn": "9781549304002",
        "primary_reason": ChallengeReason.LGBTQ_CONTENT,
        "status": ChallengeStatus.RESOLVED_RETAINED,
        "outcome": ChallengeOutcome.RETAINED,
        "date_received": datetime.now(timezone.utc) - timedelta(days=365),
        "date_resolved": datetime.now(timezone.utc) - timedelta(days=330),
        "is_public": True,
        "public_title": "Graphic Memoir About Gender Identity",
        "public_summary": "A patron requested this memoir be removed from the young adult section due to its frank discussion of gender identity and sexuality. After review by our reconsideration committee, the book was retained in its current location.",
        "lessons_learned": "This challenge reinforced our commitment to providing diverse perspectives and supporting LGBTQ+ youth who may not find their experiences reflected elsewhere. The committee found the material age-appropriate for the young adult collection and valuable for fostering understanding and empathy.",
    },
    {
        "title": "The Bluest Eye",
        "author": "Toni Morrison",
        "isbn": "9780307278449",
        "primary_reason": ChallengeReason.SEXUAL_CONTENT,
        "status": ChallengeStatus.RESOLVED_RETAINED,
        "outcome": ChallengeOutcome.RETAINED_WITH_CHANGES,
        "date_received": datetime.now(timezone.utc) - timedelta(days=540),
        "date_resolved": datetime.now(timezone.utc) - timedelta(days=500),
        "is_public": True,
        "public_title": "Classic Novel by Toni Morrison",
        "public_summary": "A parent challenged this Pulitzer Prize-winning novel due to a scene depicting child sexual abuse. The committee recognized the difficult content but affirmed the book's literary merit and important themes about racism and trauma.",
        "lessons_learned": "We added content advisories to help readers make informed choices while maintaining access to this important work of American literature. The scene in question, while disturbing, serves to illustrate the devastating effects of racism and abuse.",
    },
    {
        "title": "The Hate U Give",
        "author": "Angie Thomas",
        "isbn": "9780062498533",
        "primary_reason": ChallengeReason.LANGUAGE,
        "status": ChallengeStatus.RESOLVED_RETAINED,
        "outcome": ChallengeOutcome.RETAINED,
        "date_received": datetime.now(timezone.utc) - timedelta(days=280),
        "date_resolved": datetime.now(timezone.utc) - timedelta(days=245),
        "is_public": True,
        "public_title": "Young Adult Novel About Police Violence",
        "public_summary": "Challenged for profanity and portrayal of police officers. The committee unanimously voted to retain the book, noting that the language reflects authentic teen voices and the story addresses critical social justice issues.",
        "lessons_learned": "Authentic representation sometimes means including language that makes some readers uncomfortable. The book's positive messages about activism, family, and speaking truth to power far outweigh concerns about occasional profanity.",
    },
    {
        "title": "Harry Potter and the Sorcerer's Stone",
        "author": "J.K. Rowling",
        "isbn": "9780439708180",
        "primary_reason": ChallengeReason.OCCULT_SUPERNATURAL,
        "status": ChallengeStatus.RESOLVED_RETAINED,
        "outcome": ChallengeOutcome.RETAINED,
        "date_received": datetime.now(timezone.utc) - timedelta(days=820),
        "date_resolved": datetime.now(timezone.utc) - timedelta(days=795),
        "is_public": True,
        "public_title": "Popular Fantasy Series",
        "public_summary": "Challenged for promoting witchcraft and the occult. The committee found that the series uses magic as a literary device in a fantasy setting and promotes positive values like courage, friendship, and standing up against evil.",
        "lessons_learned": "Fantasy literature has a long tradition in children's literature. The committee distinguished between fictional magic in storytelling and promotion of actual occult practices, finding no evidence that the books encourage the latter.",
    },
    {
        "title": "All Boys Aren't Blue",
        "author": "George M. Johnson",
        "isbn": "9780374312718",
        "primary_reason": ChallengeReason.SEXUAL_CONTENT,
        "status": ChallengeStatus.RESOLVED_RESTRICTED,
        "outcome": ChallengeOutcome.RESTRICTED,
        "date_received": datetime.now(timezone.utc) - timedelta(days=180),
        "date_resolved": datetime.now(timezone.utc) - timedelta(days=150),
        "is_public": True,
        "public_title": "Memoir About Black Queer Experience",
        "public_summary": "Challenged for explicit sexual content. After careful review, the committee decided to move the book from the general young adult section to our 16+ collection, requiring parental permission for younger teens.",
        "lessons_learned": "This was a difficult decision. While we value the book's authentic portrayal of Black queer experiences, we recognized community concerns about age-appropriateness. The restricted access balances both perspectives.",
    },
    {
        "title": "Brave New World",
        "author": "Aldous Huxley",
        "isbn": "9780060850524",
        "primary_reason": ChallengeReason.ANTI_FAMILY,
        "status": ChallengeStatus.RESOLVED_RETAINED,
        "outcome": ChallengeOutcome.RETAINED,
        "date_received": datetime.now(timezone.utc) - timedelta(days=650),
        "date_resolved": datetime.now(timezone.utc) - timedelta(days=620),
        "is_public": True,
        "public_title": "Classic Dystopian Novel",
        "public_summary": "Challenged for depicting a society that devalues family structures. The committee retained the book, noting that dystopian literature often depicts troubling societies as a warning, not an endorsement.",
        "lessons_learned": "Classic literature often challenges readers to think critically about society. Huxley's novel is a cautionary tale about the dangers of sacrificing humanity for stability, not a blueprint for living.",
    },
    {
        "title": "Drama",
        "author": "Raina Telgemeier",
        "isbn": "9780545326995",
        "primary_reason": ChallengeReason.LGBTQ_CONTENT,
        "status": ChallengeStatus.WITHDRAWN,
        "outcome": ChallengeOutcome.WITHDRAWN,
        "date_received": datetime.now(timezone.utc) - timedelta(days=90),
        "date_resolved": datetime.now(timezone.utc) - timedelta(days=75),
        "is_public": True,
        "public_title": "Graphic Novel About School Theater",
        "public_summary": "Challenged for including LGBTQ+ characters. The challenger withdrew their complaint after attending an information session about the reconsideration process and reading the book in full.",
        "lessons_learned": "Sometimes concerns arise from partial information. Our open dialogue process allows community members to learn more about challenged materials. The book depicts diverse, age-appropriate friendships in a middle school setting.",
    },
    {
        "title": "Looking for Alaska",
        "author": "John Green",
        "isbn": "9780142402511",
        "primary_reason": ChallengeReason.SEXUAL_CONTENT,
        "status": ChallengeStatus.RESOLVED_RETAINED,
        "outcome": ChallengeOutcome.RETAINED,
        "date_received": datetime.now(timezone.utc) - timedelta(days=420),
        "date_resolved": datetime.now(timezone.utc) - timedelta(days=390),
        "is_public": True,
        "public_title": "Coming-of-Age Novel",
        "public_summary": "Challenged for a sexual scene and underage drinking. The committee found that these elements are integral to the story's exploration of grief, guilt, and the complexities of adolescence.",
        "lessons_learned": "Young adult literature often addresses difficult topics because teens face these realities. The book doesn't glamorize risky behavior but rather shows consequences and emotional complexity.",
    },
]

# Educational resources about intellectual freedom
RESOURCES = [
    {
        "title": "Library Bill of Rights",
        "description": "The American Library Association's core document on intellectual freedom",
        "url": "https://www.ala.org/advocacy/intfreedom/librarybill",
        "resource_type": "policy",
        "display_order": 1,
        "content": """
The Library Bill of Rights is a core document of the American Library Association (ALA) that affirms that all libraries are forums for information and ideas. It opposes censorship and champions the freedom to read.

Key Principles:
- Books and other library resources should be provided for the interest, information, and enlightenment of all people of the community
- Materials should not be excluded because of the origin, background, or views of those contributing to their creation
- Libraries should challenge censorship in the fulfillment of their responsibility to provide information and enlightenment
- Libraries should cooperate with all persons and groups concerned with resisting abridgment of free expression and free access to ideas
""",
    },
    {
        "title": "Freedom to Read Statement",
        "description": "Joint statement on the importance of the freedom to read",
        "url": "https://www.ala.org/advocacy/intfreedom/freedomreadstatement",
        "resource_type": "policy",
        "display_order": 2,
        "content": """
Originally issued in 1953 by the ALA and the American Book Publishers Council (now the Association of American Publishers), this statement emphasizes that:

- It is in the public interest for publishers and librarians to make available the widest diversity of views and expressions
- It is contrary to the public interest for them to establish their own political, moral, or aesthetic views as a standard for determining what should be published or circulated
- Publishers and librarians serve the educational process by helping to make available knowledge and ideas required for the growth of the mind
- They do not foster education by imposing as mentors the patterns of their own thought
""",
    },
    {
        "title": "Banned Books Week",
        "description": "Annual event celebrating the freedom to read",
        "url": "https://bannedbooksweek.org",
        "resource_type": "external_link",
        "display_order": 3,
        "content": """
Banned Books Week is an annual event celebrating the freedom to read. Typically held during the last week of September, it highlights the value of free and open access to information.

The week draws national attention to the harms of censorship by spotlighting actual or attempted bannings of books across the United States. By focusing on efforts across the country to remove or restrict access to books, Banned Books Week brings together the entire book community - librarians, booksellers, publishers, journalists, teachers, and readers of all types - in shared support of the freedom to seek and to express ideas, even those some consider unorthodox or unpopular.
""",
    },
    {
        "title": "How to Respond to a Challenge",
        "description": "Information about our reconsideration process",
        "resource_type": "article",
        "display_order": 4,
        "content": """
At Bébé Memorial Library, we take all material reconsideration requests seriously. Our process ensures fair and thoughtful review:

## The Process

1. **Formal Request**: Challengers complete a Request for Reconsideration form detailing their concerns
2. **Initial Review**: Library director reviews the request and the material in question
3. **Committee Review**: A diverse committee of staff and community members reads/views the entire work
4. **Evaluation**: The committee evaluates the material based on:
   - Literary or artistic merit
   - Age-appropriateness for the intended audience
   - Accuracy and authority
   - Alignment with collection development policy
5. **Decision**: The committee makes a recommendation to retain, restrict, or remove
6. **Appeal**: Challengers may appeal to the Library Board

## Review Criteria

We evaluate materials in their entirety, not based on isolated passages or scenes. We consider:
- The work's contribution to the collection
- Professional reviews and literary significance
- Representation of diverse viewpoints
- Community needs and interests

All decisions are documented and made public (with challenger privacy protected) to maintain transparency and accountability.
""",
    },
    {
        "title": "Why Diverse Books Matter",
        "description": "The importance of representation in library collections",
        "resource_type": "article",
        "display_order": 5,
        "content": """
Libraries serve everyone in our community, and our collection should reflect that diversity. Research shows that children and teens benefit from both "mirrors" (books that reflect their own experiences) and "windows" (books that show different experiences).

## Benefits of Diverse Collections

**For Young Readers Seeking Mirrors:**
- Validation that their experiences and identities matter
- Role models and positive representation
- Reduced feelings of isolation or "otherness"
- Increased self-esteem and academic engagement

**For Young Readers Seeking Windows:**
- Exposure to different cultures, experiences, and perspectives
- Development of empathy and cultural competency
- Preparation for an increasingly diverse society
- Understanding that difference is normal and valuable

**For All Readers:**
- Critical thinking about different viewpoints
- Broader understanding of human experience
- Recognition of common humanity across differences
- Tools to navigate complex social issues

Our library is committed to providing both mirrors and windows for every member of our community.
""",
    },
]


async def seed_book_challenges():
    """Seed the database with book challenges and intellectual freedom resources."""
    DATABASE_URL = settings.database_url

    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("=" * 70)
        print("📚 Seeding Book Challenges & Intellectual Freedom Resources")
        print("=" * 70)
        print()

        # Check if challenges already exist
        result = await session.execute(select(BookChallenge))
        existing_challenges = result.scalars().all()

        if existing_challenges:
            print(f"⚠️  Found {len(existing_challenges)} existing challenges")
            print("   Skipping challenge seeding to avoid duplicates")
        else:
            print("📖 Creating book challenges...")
            created_count = 0

            for challenge_data in CHALLENGES:
                challenge = BookChallenge(**challenge_data)
                session.add(challenge)
                created_count += 1
                print(f"  ✓ {challenge.title} by {challenge.author}")

            print(f"\n✅ Created {created_count} book challenges")

        print()

        # Check if resources already exist
        result = await session.execute(select(IntellectualFreedomResource))
        existing_resources = result.scalars().all()

        if existing_resources:
            print(f"⚠️  Found {len(existing_resources)} existing resources")
            print("   Skipping resource seeding to avoid duplicates")
        else:
            print("📚 Creating intellectual freedom resources...")
            created_count = 0

            for resource_data in RESOURCES:
                resource = IntellectualFreedomResource(**resource_data)
                session.add(resource)
                created_count += 1
                print(f"  ✓ {resource.title}")

            print(f"\n✅ Created {created_count} educational resources")

        await session.commit()

    await engine.dispose()

    print()
    print("=" * 70)
    print("✨ Book Challenges Seeding Complete!")
    print("=" * 70)
    print()
    print("📊 Summary:")
    print(f"  • {len(CHALLENGES)} book challenges with diverse outcomes")
    print(f"  • {len(RESOURCES)} educational resources about intellectual freedom")
    print()
    print("View at: /banned-books or /intellectual-freedom")
    print()


if __name__ == "__main__":
    asyncio.run(seed_book_challenges())
