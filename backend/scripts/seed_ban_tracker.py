#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed script for the Book Ban Tracker feature.

Creates advocacy letter templates and real-world ban reports based on
commonly challenged/banned books documented by PEN America and the ALA.

Run via:
    docker-compose exec backend python scripts/seed_ban_tracker.py
"""
import asyncio
import sys
from datetime import date
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.ban_tracker import (
    AdvocacyLetterTemplate,
    BanReport,
    BanSource,
    BanType,
)
from app.core.config import get_settings

settings = get_settings()


ADVOCACY_TEMPLATES = [
    {
        "title": "Oppose Book Bans",
        "subject_line": "Oppose Efforts to Restrict Library Materials",
        "target_level": "state",
        "is_active": True,
        "body_template": """Dear Representative {rep_name},

My name is {your_name} and I am a resident of {your_address}. I am writing to urge you to oppose any legislation that would restrict access to library materials or mandate the removal of books from public and school libraries.

Access to a wide range of books and ideas is fundamental to a free and educated society. Libraries serve as cornerstones of our communities — places where people of all backgrounds can explore diverse perspectives, develop critical thinking skills, and find themselves reflected in the stories they read.

Book bans do not protect our children. Research consistently shows that broad book restrictions deny young people access to stories that help them understand the world, navigate difficult experiences, and build empathy for others. Parents already have the right to guide their own children's reading choices. Legislation that removes books for everyone in order to impose one set of values on an entire community is not protection — it is censorship.

Restricting access to {library_name} and libraries across our state sends a damaging message to students, educators, and families: that some voices and experiences do not deserve to be heard. I urge you to stand with readers, educators, and librarians who work every day to ensure that all members of our community have access to information and ideas.

Please oppose any legislation that would restrict library materials or penalize librarians and educators for providing access to diverse books.

Sincerely,
{your_name}
{your_address}""",
    },
    {
        "title": "Support Library Funding",
        "subject_line": "Support Continued Federal Funding for Libraries",
        "target_level": "federal",
        "is_active": True,
        "body_template": """Dear Representative {rep_name},

I am writing as a constituent from {your_address} to urge your strong support for continued federal funding for libraries, including full appropriations for the Institute of Museum and Library Services (IMLS) and reauthorization of the Library Services and Technology Act (LSTA).

Libraries are among the most cost-effective public investments our government makes. For every dollar invested in public libraries, communities receive returns in workforce development, literacy, digital access, and civic engagement that far exceed the initial cost. Libraries like {library_name} serve as vital community anchors — providing free internet access, job search assistance, early childhood literacy programs, and resources for small businesses.

Federal library funding through IMLS and LSTA supports programs in every congressional district that would not otherwise exist. Cutting this funding disproportionately harms rural communities, low-income families, and underserved populations who rely on public libraries as their primary access point to information and technology.

At a time when book bans are rising and access to information is increasingly contested, strong federal support for libraries is more important than ever. I urge you to champion full funding for IMLS and to support the Library Services and Technology Act, ensuring that every American — regardless of zip code — has access to the resources they need to thrive.

Thank you for your consideration.

Sincerely,
{your_name}
{your_address}""",
    },
    {
        "title": "Protect Student Access",
        "subject_line": "Protect Students' Right to Read in Our Schools",
        "target_level": "local",
        "is_active": True,
        "body_template": """Dear {rep_name},

I am a community member writing to urge you to oppose blanket book removal policies in our school district and to protect students' right to read.

Parents absolutely have the right to make decisions about what their own children read. I fully support that right. However, banning a book from a school library or classroom removes the choice not just from one family, but from every family in the district. That is not parental rights — that is one group imposing its values on all other parents and students.

School libraries play a critical role in student development. Books in school collections are selected by trained educators and librarians using established professional standards. When books are removed based on complaints from a small number of community members, students lose access to stories that may reflect their own experiences, help them understand peers different from themselves, or spark a lifelong love of reading.

I ask that our school district commit to the following:
- Maintain a transparent, fair, and professionally grounded review process for book challenges
- Reject wholesale removal of books without full committee review
- Ensure that no single complaint results in a book being pulled from shelves
- Affirm that all students deserve to see themselves in the books available to them

Students in our district deserve a school environment that respects intellectual curiosity and the diversity of our community. I urge you to stand up for students' right to read.

Sincerely,
{your_name}
{your_address}""",
    },
]


BAN_REPORTS = [
    {
        "isbn": "9781549304002",
        "title": "Gender Queer: A Memoir",
        "author": "Maia Kobabe",
        "state": "VA",
        "district": "Spotsylvania County Public Schools",
        "ban_type": BanType.BANNED,
        "reason_category": "lgbtq",
        "reason": "Challenged for LGBTQ+ content and sexually explicit illustrations.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2021, 11, 8),
    },
    {
        "isbn": "9780062498533",
        "title": "The Hate U Give",
        "author": "Angie Thomas",
        "state": "TX",
        "district": "Katy Independent School District",
        "ban_type": BanType.RESTRICTED,
        "reason_category": "race",
        "reason": "Challenged for anti-police messaging and language deemed inappropriate.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2017, 9, 20),
    },
    {
        "isbn": "9780374312718",
        "title": "All Boys Aren't Blue",
        "author": "George M. Johnson",
        "state": "FL",
        "district": "Duval County Public Schools",
        "ban_type": BanType.BANNED,
        "reason_category": "lgbtq",
        "reason": "Removed for sexually explicit content and LGBTQ+ themes.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2022, 3, 15),
    },
    {
        "isbn": "9781250301697",
        "title": "Lawn Boy",
        "author": "Jonathan Evison",
        "state": "TX",
        "district": "Leander Independent School District",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed for sexually explicit content involving a minor.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2021, 10, 26),
    },
    {
        "isbn": "9780307278449",
        "title": "The Bluest Eye",
        "author": "Toni Morrison",
        "state": "MO",
        "district": "Wentzville School District",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed for sexually explicit content depicting abuse.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 1, 9),
    },
    {
        "isbn": "9780763673628",
        "title": "Beyond Magenta",
        "author": "Susan Kuklin",
        "state": "FL",
        "district": "Brevard County Public Schools",
        "ban_type": BanType.BANNED,
        "reason_category": "lgbtq",
        "reason": "Removed for LGBTQ+ content and sexually explicit passages.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2022, 7, 18),
    },
    {
        "isbn": "9781623161194",
        "title": "This Book Is Gay",
        "author": "Juno Dawson",
        "state": "UT",
        "district": "Alpine School District",
        "ban_type": BanType.RESTRICTED,
        "reason_category": "lgbtq",
        "reason": "Restricted to parental permission request for LGBTQ+ content.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 3, 2),
    },
    {
        "isbn": "9781594480003",
        "title": "The Kite Runner",
        "author": "Khaled Hosseini",
        "state": "TX",
        "district": "Spring Branch Independent School District",
        "ban_type": BanType.CHALLENGED,
        "reason_category": "sexual_content",
        "reason": "Challenged for a scene depicting sexual assault and language.",
        "source": BanSource.NEWS,
        "date_reported": date(2023, 9, 14),
    },
    {
        "isbn": "9780316013697",
        "title": "The Absolutely True Diary of a Part-Time Indian",
        "author": "Sherman Alexie",
        "state": "IA",
        "district": "Iowa City Community School District",
        "ban_type": BanType.BANNED,
        "reason_category": "race",
        "reason": "Removed for language, sexual content, and depictions of bullying.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2022, 11, 3),
    },
    {
        "isbn": "9780316536318",
        "title": "Stamped: Racism, Antiracism, and You",
        "author": "Ibram X. Kendi and Jason Reynolds",
        "state": "TN",
        "district": "Williamson County Schools",
        "ban_type": BanType.BANNED,
        "reason_category": "race",
        "reason": "Removed for alleged political content and critical race theory.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2021, 8, 10),
    },
    {
        "isbn": "9781250074522",
        "title": "Out of Darkness",
        "author": "Ashley Hope Pérez",
        "state": "TX",
        "district": "Keller Independent School District",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed for sexually explicit content and racial themes.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2021, 10, 26),
    },
    {
        "isbn": "9781635575569",
        "title": "A Court of Mist and Fury",
        "author": "Sarah J. Maas",
        "state": "FL",
        "district": "Brevard County Public Schools",
        "ban_type": BanType.RESTRICTED,
        "reason_category": "sexual_content",
        "reason": "Restricted from school library due to explicit sexual content.",
        "source": BanSource.NEWS,
        "date_reported": date(2023, 10, 5),
    },
    {
        "isbn": "9780525425892",
        "title": "Me and Earl and the Dying Girl",
        "author": "Jesse Andrews",
        "state": "OK",
        "district": "Tulsa Public Schools",
        "ban_type": BanType.CHALLENGED,
        "reason_category": "sexual_content",
        "reason": "Challenged for crude humor and sexual references.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2024, 2, 20),
    },
    {
        "isbn": "9781982110994",
        "title": "The Perks of Being a Wallflower",
        "author": "Stephen Chbosky",
        "state": "SC",
        "district": "Pickens County School District",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed for sexual content, drug use, and homosexuality.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2022, 5, 12),
    },
    {
        "isbn": "9780451478290",
        "title": "Thirteen Reasons Why",
        "author": "Jay Asher",
        "state": "MO",
        "district": "Raytown School District",
        "ban_type": BanType.RESTRICTED,
        "reason_category": "suicide_self_harm",
        "reason": "Restricted for graphic depiction of suicide and its potential influence on at-risk youth.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 6, 7),
    },
    {
        "isbn": "9780142402511",
        "title": "Looking for Alaska",
        "author": "John Green",
        "state": "FL",
        "district": "Martin County School District",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed for sexual content and use of profanity.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2022, 9, 19),
    },
    {
        "isbn": "9781250012579",
        "title": "Eleanor & Park",
        "author": "Rainbow Rowell",
        "state": "VA",
        "district": "Loudoun County Public Schools",
        "ban_type": BanType.CHALLENGED,
        "reason_category": "sexual_content",
        "reason": "Challenged for language and sexual content deemed inappropriate for middle school.",
        "source": BanSource.NEWS,
        "date_reported": date(2024, 1, 16),
    },
    {
        "isbn": "9780374400071",
        "title": "Speak",
        "author": "Laurie Halse Anderson",
        "state": "PA",
        "district": "Norristown Area School District",
        "ban_type": BanType.CHALLENGED,
        "reason_category": "sexual_content",
        "reason": "Challenged for 'soft pornography' despite depicting sexual assault recovery.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 4, 3),
    },
    {
        "isbn": "9780545326995",
        "title": "Drama",
        "author": "Raina Telgemeier",
        "state": "TX",
        "district": "Round Rock Independent School District",
        "ban_type": BanType.BANNED,
        "reason_category": "lgbtq",
        "reason": "Removed for LGBTQ+ content in a middle grade graphic novel.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2022, 4, 28),
    },
    {
        "isbn": "9781626721951",
        "title": "Flamer",
        "author": "Mike Curato",
        "state": "FL",
        "district": "Flagler County School District",
        "ban_type": BanType.BANNED,
        "reason_category": "lgbtq",
        "reason": "Removed for LGBTQ+ content and sexually explicit illustrations.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2022, 8, 1),
    },
    # --- 25 additional reports from live database ---
    {
        "isbn": "9780374303235",
        "title": "The 57 Bus",
        "author": "Dashka Slater",
        "state": "UT",
        "district": "Davis School District",
        "ban_type": BanType.BANNED,
        "reason_category": "lgbtq",
        "reason": "Removed for LGBTQ+ content involving a nonbinary teen.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 6, 15),
    },
    {
        "isbn": "9781449474256",
        "title": "Milk and Honey",
        "author": "Rupi Kaur",
        "state": "UT",
        "district": "Canyons School District",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed for sexual content and references to abuse.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 8, 22),
    },
    {
        "isbn": "9780618871711",
        "title": "Fun Home",
        "author": "Alison Bechdel",
        "state": "UT",
        "district": "Alpine School District",
        "ban_type": BanType.BANNED,
        "reason_category": "lgbtq",
        "reason": "Removed for LGBTQ+ content and sexually explicit illustrations.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 3, 10),
    },
    {
        "isbn": "9781984893147",
        "title": "Let's Talk About It",
        "author": "Erika Moen and Matthew Nolan",
        "state": "UT",
        "district": "Davis School District",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed from school libraries for sexually explicit sex education content.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 9, 1),
    },
    {
        "isbn": "9781416950059",
        "title": "Identical",
        "author": "Ellen Hopkins",
        "state": "UT",
        "district": "Alpine School District",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed for depictions of sexual abuse, incest, and drug use.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 5, 18),
    },
    {
        "isbn": "9781644450383",
        "title": "In the Dream House",
        "author": "Carmen Maria Machado",
        "state": "UT",
        "district": "Granite School District",
        "ban_type": BanType.BANNED,
        "reason_category": "lgbtq",
        "reason": "Removed for LGBTQ+ content depicting an abusive same-sex relationship.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 7, 12),
    },
    {
        "isbn": "9780062422682",
        "title": "Monday's Not Coming",
        "author": "Tiffany D. Jackson",
        "state": "UT",
        "district": "Canyons School District",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed for language and references to sexual abuse and violence.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 11, 8),
    },
    {
        "isbn": "9781635575552",
        "title": "A Court of Thorns and Roses",
        "author": "Sarah J. Maas",
        "state": "UT",
        "district": "Alpine School District",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed for explicit sexual content in a fantasy series popular with teens.",
        "source": BanSource.NEWS,
        "date_reported": date(2024, 1, 22),
    },
    {
        "isbn": "9780689878459",
        "title": "And Tango Makes Three",
        "author": "Justin Richardson and Peter Parnell",
        "state": "FL",
        "district": "Lake County Schools",
        "ban_type": BanType.BANNED,
        "reason_category": "lgbtq",
        "reason": "Removed from elementary libraries for depicting a same-sex penguin couple raising a chick.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 4, 17),
    },
    {
        "isbn": "9780385490818",
        "title": "The Handmaid's Tale",
        "author": "Margaret Atwood",
        "state": "FL",
        "district": "Escambia County School District",
        "ban_type": BanType.RESTRICTED,
        "reason_category": "sexual_content",
        "reason": "Restricted for sexual content, profanity, and themes of reproductive coercion.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 5, 3),
    },
    {
        "isbn": "9780062691194",
        "title": "New Kid",
        "author": "Jerry Craft",
        "state": "TX",
        "district": "Katy Independent School District",
        "ban_type": BanType.CHALLENGED,
        "reason_category": "race",
        "reason": "Challenged for critical race theory content in a graphic novel about a Black kid at a predominantly white school.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2021, 11, 15),
    },
    {
        "isbn": "9781400033416",
        "title": "Beloved",
        "author": "Toni Morrison",
        "state": "TX",
        "district": "Keller Independent School District",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed for sexual content, violence, and depictions of slavery.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2022, 1, 24),
    },
    {
        "isbn": "9781400033416",
        "title": "Beloved",
        "author": "Toni Morrison",
        "state": "IA",
        "district": "Iowa City Community School District",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed under SF 496 which required removal of books with sexual content.",
        "source": BanSource.NEWS,
        "date_reported": date(2023, 9, 1),
    },
    {
        "isbn": "9780156028356",
        "title": "The Color Purple",
        "author": "Alice Walker",
        "state": "IA",
        "district": "Iowa City Community School District",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed under SF 496 for sexual content and language.",
        "source": BanSource.NEWS,
        "date_reported": date(2023, 9, 1),
    },
    {
        "isbn": "9780394747231",
        "title": "Maus",
        "author": "Art Spiegelman",
        "state": "TN",
        "district": "McMinn County Schools",
        "ban_type": BanType.BANNED,
        "reason_category": "violence_profanity",
        "reason": "Banned by school board for profanity, nudity, and depictions of violence and suicide in a Holocaust graphic novel.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2022, 1, 10),
    },
    {
        "isbn": "9780763624910",
        "title": "33 Snowfish",
        "author": "Adam Rapp",
        "state": "VA",
        "district": "Fairfax County Public Schools",
        "ban_type": BanType.CHALLENGED,
        "reason_category": "sexual_content",
        "reason": "Challenged for sexual content, drug use, and violence involving minors.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 8, 14),
    },
    {
        "isbn": "9780385490818",
        "title": "The Handmaid's Tale",
        "author": "Margaret Atwood",
        "state": "MO",
        "district": "Republic School District",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed for sexual content and themes deemed inappropriate for students.",
        "source": BanSource.NEWS,
        "date_reported": date(2023, 10, 16),
    },
    {
        "isbn": "9780786851713",
        "title": "Sold",
        "author": "Patricia McCormick",
        "state": "SC",
        "district": "Horry County Schools",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed for depictions of sex trafficking and sexual content.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 6, 20),
    },
    {
        "isbn": "9781416950073",
        "title": "Tricks",
        "author": "Ellen Hopkins",
        "state": "PA",
        "district": "Central Bucks School District",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed for depictions of prostitution, drug use, and sexual content.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 2, 14),
    },
    {
        "isbn": "9780545812542",
        "title": "George",
        "author": "Alex Gino",
        "state": "NC",
        "district": "Union County Public Schools",
        "ban_type": BanType.BANNED,
        "reason_category": "lgbtq",
        "reason": "Removed for transgender content in an elementary-level novel about a trans girl.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2022, 10, 5),
    },
    {
        "isbn": "9780374312718",
        "title": "All Boys Aren't Blue",
        "author": "George M. Johnson",
        "state": "IN",
        "district": "Hamilton Southeastern Schools",
        "ban_type": BanType.BANNED,
        "reason_category": "lgbtq",
        "reason": "Removed from school libraries for LGBTQ+ content and sexually explicit passages.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2023, 1, 18),
    },
    {
        "isbn": "9781982110994",
        "title": "The Perks of Being a Wallflower",
        "author": "Stephen Chbosky",
        "state": "GA",
        "district": "Forsyth County Schools",
        "ban_type": BanType.BANNED,
        "reason_category": "sexual_content",
        "reason": "Removed for sexual content, drug use, and depictions of homosexuality.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2022, 9, 7),
    },
    {
        "isbn": "9781549304002",
        "title": "Gender Queer: A Memoir",
        "author": "Maia Kobabe",
        "state": "KS",
        "district": "Blue Valley School District",
        "ban_type": BanType.BANNED,
        "reason_category": "lgbtq",
        "reason": "Removed from all school libraries for LGBTQ+ content and sexually explicit illustrations.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2022, 4, 11),
    },
    {
        "isbn": "9780394747231",
        "title": "Maus",
        "author": "Art Spiegelman",
        "state": "WI",
        "district": "Elkhorn Area School District",
        "ban_type": BanType.CHALLENGED,
        "reason_category": "violence_profanity",
        "reason": "Challenged for profanity, nudity, and graphic depictions of the Holocaust.",
        "source": BanSource.NEWS,
        "date_reported": date(2023, 3, 20),
    },
    {
        "isbn": "9780316536318",
        "title": "Stamped: Racism, Antiracism, and You",
        "author": "Ibram X. Kendi and Jason Reynolds",
        "state": "OH",
        "district": "Olentangy Local Schools",
        "ban_type": BanType.CHALLENGED,
        "reason_category": "race",
        "reason": "Challenged for alleged critical race theory content and anti-American messaging.",
        "source": BanSource.PEN_AMERICA,
        "date_reported": date(2022, 3, 8),
    },
]


async def seed_ban_tracker():
    """Seed advocacy letter templates and ban reports.
    
    NOTE: Tables must exist before running this script.
    If tables don't exist, run: docker-compose exec backend python -c "from app.core.database import Base, engine; Base.metadata.create_all(engine)"
    """
    """Seed advocacy letter templates and ban reports."""
    DATABASE_URL = settings.database_url

    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("=" * 70)
        print("Book Ban Tracker Seed")
        print("=" * 70)
        print()

        # --- Advocacy Letter Templates ---
        result = await session.execute(select(AdvocacyLetterTemplate))
        existing_templates = result.scalars().all()

        if existing_templates:
            print(
                f"Found {len(existing_templates)} existing advocacy templates — skipping."
            )
        else:
            print("Creating advocacy letter templates...")
            for tpl_data in ADVOCACY_TEMPLATES:
                session.add(AdvocacyLetterTemplate(**tpl_data))
                print(
                    f"  + [{tpl_data['target_level'].upper()}] {tpl_data['title']}"
                )
            print(f"  => {len(ADVOCACY_TEMPLATES)} templates created")

        print()

        # --- Ban Reports ---
        result = await session.execute(select(BanReport))
        existing_reports = result.scalars().all()

        if existing_reports:
            print(
                f"Found {len(existing_reports)} existing ban reports — skipping."
            )
        else:
            print("Creating ban reports...")
            for report_data in BAN_REPORTS:
                session.add(BanReport(**report_data))
                print(
                    f"  + [{report_data['ban_type'].value}] "
                    f"{report_data['title']} — {report_data['state']}"
                )
            print(f"  => {len(BAN_REPORTS)} ban reports created")

        await session.commit()

    await engine.dispose()

    print()
    print("=" * 70)
    print("Ban Tracker Seeding Complete")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  Advocacy letter templates : {len(ADVOCACY_TEMPLATES)}")
    print(f"  Ban reports               : {len(BAN_REPORTS)}")
    ban_type_counts = {}
    for r in BAN_REPORTS:
        k = r["ban_type"].value
        ban_type_counts[k] = ban_type_counts.get(k, 0) + 1
    for k, v in sorted(ban_type_counts.items()):
        print(f"    {k:<12}: {v}")
    print()
    states = sorted({r["state"] for r in BAN_REPORTS})
    print(f"  States covered: {', '.join(states)}")
    print()


if __name__ == "__main__":
    asyncio.run(seed_ban_tracker())
