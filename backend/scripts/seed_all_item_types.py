#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive LSC Library Item Types Seeder - All Formats
Seeds complete data for ALL item types with proper MARC records,
multiple copies at different branches, and varied availability statuses
"""
import sys, os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@database:5432/lsc_library")
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Content rating mapping - normalize to lowercase database enum values
RATING_MAP = {
    "G": "g",
    "PG": "pg",
    "PG-13": "pg13",
    "R": "r",
    "NC-17": "nc17",
    "E": "e",
    "E10+": "e10",
    "T": "t",
    "M": "m",
    "AO": "ao",
    "Explicit": "explicit",
    "Clean": "clean",
    "Unrated": "unrated",
    "Not Rated": "not_rated",
}

def normalize_rating(rating):
    """Normalize content rating to database enum value."""
    if not rating:
        return None
    return RATING_MAP.get(rating, rating.lower())

# Comprehensive Catalog Items - All Required Types
CATALOG_ITEMS = [
    # =============================================
    # 1. BOOKS (Fiction - Regular Print)
    # =============================================
    {
        "title": "The Ministry of Time",
        "author": "Kaliane Bradley",
        "item_type": "book",
        "isbn": "9781668049495",
        "publisher": "Avid Reader Press",
        "publication_year": 2024,
        "subjects": "Science Fiction, Time Travel, LGBTQ+",
        "description": "A time-travel romance exploring colonialism and queer identity.",
        "page_count": 368,
        "dewey_decimal": "823.92",
        "call_number": "FIC BRA",
        "lc_classification": "PR6102.R22",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "All Fours",
        "author": "Miranda July",
        "item_type": "book",
        "isbn": "9780593732595",
        "publisher": "Riverhead Books",
        "publication_year": 2024,
        "subjects": "Fiction, Women's Fiction",
        "description": "A woman upends her life in a roadside motel.",
        "page_count": 320,
        "dewey_decimal": "813.6",
        "call_number": "FIC JUL",
        "lc_classification": "PS3610.U38",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "The Serviceberry",
        "author": "Robin Wall Kimmerer",
        "item_type": "book",
        "isbn": "9781982187866",
        "publisher": "Scribner",
        "publication_year": 2024,
        "subjects": "Nature, Indigenous Knowledge, Philosophy",
        "description": "From gift economies to reciprocity with the natural world.",
        "page_count": 160,
        "dewey_decimal": "304.2",
        "call_number": "304.2 KIM",
        "lc_classification": "GN296.5.K55",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 2. BOOKS (Non-Fiction)
    # =============================================
    {
        "title": "Unmasking Autism",
        "author": "Devon Price",
        "item_type": "book",
        "isbn": "9780593235232",
        "publisher": "Harmony",
        "publication_year": 2022,
        "subjects": "Autism, Neurodiversity, Mental Health",
        "description": "Discovering the new faces of neurodiversity.",
        "page_count": 288,
        "dewey_decimal": "616.8588",
        "call_number": "616.8588 PRI",
        "lc_classification": "RC455.4.A88",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "The Anxious Generation",
        "author": "Jonathan Haidt",
        "item_type": "book",
        "isbn": "9780593655030",
        "publisher": "Penguin Press",
        "publication_year": 2024,
        "subjects": "Psychology, Technology, Youth Mental Health",
        "description": "How phone-based childhood is harming young people.",
        "page_count": 400,
        "dewey_decimal": "155.5",
        "call_number": "155.5 HAI",
        "lc_classification": "BF575.A6",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "Salt, Fat, Acid, Heat",
        "author": "Samin Nosrat",
        "item_type": "book",
        "isbn": "9781476753836",
        "publisher": "Simon & Schuster",
        "publication_year": 2017,
        "subjects": "Cooking, Food Science",
        "description": "Mastering the elements of good cooking.",
        "page_count": 480,
        "dewey_decimal": "641.5",
        "call_number": "641.5 NOS",
        "lc_classification": "TX714.N67",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 3. LARGE PRINT BOOKS
    # =============================================
    {
        "title": "The Women (Large Print)",
        "author": "Kristin Hannah",
        "item_type": "book",
        "isbn": "9781250249837",  # Large print edition
        "publisher": "Thorndike Press",
        "publication_year": 2024,
        "subjects": "Historical Fiction, Vietnam War, Women, Large Print",
        "description": "Women who served in Vietnam and came home to silence. [LARGE PRINT EDITION]",
        "page_count": 784,  # Large print has more pages
        "dewey_decimal": "813.54",
        "call_number": "FIC HAN (LP)",
        "lc_classification": "PS3608.A5365",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "The Housemaid (Large Print)",
        "author": "Freida McFadden",
        "item_type": "book",
        "isbn": "9781496716605",  # Large print edition
        "publisher": "Random House Large Print",
        "publication_year": 2023,
        "subjects": "Thriller, Mystery, Suspense, Large Print",
        "description": "A psychological thriller about secrets and survival. [LARGE PRINT EDITION]",
        "page_count": 544,
        "dewey_decimal": "813.6",
        "call_number": "FIC MCA (LP)",
        "lc_classification": "PS3613.C336",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 4. AUDIOBOOKS (Digital)
    # =============================================
    {
        "title": "Tomorrow, and Tomorrow, and Tomorrow (Audiobook)",
        "author": "Gabrielle Zevin",
        "item_type": "audiobook",
        "isbn": "9780593470961",
        "publisher": "Random House Audio",
        "publication_year": 2022,
        "subjects": "Fiction, Gaming, Friendship, Audiobook",
        "description": "Two game designers navigate love and creativity. [AUDIOBOOK]",
        "page_count": 0,
        "dewey_decimal": "813.6",
        "call_number": "AB ZEV",
        "lc_classification": "PS3626.E95",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "Demon Copperhead (Audiobook)",
        "author": "Barbara Kingsolver",
        "item_type": "audiobook",
        "isbn": "9780063251939",
        "publisher": "Harper Audio",
        "publication_year": 2022,
        "subjects": "Fiction, Appalachia, Coming-of-age, Audiobook",
        "description": "Pulitzer Prize winner about a boy in foster care. [AUDIOBOOK]",
        "page_count": 0,
        "dewey_decimal": "813.54",
        "call_number": "AB KIN",
        "lc_classification": "PS3561.I496",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 5. AUDIOBOOKS (CD Format)
    # =============================================
    {
        "title": "The Seven Husbands of Evelyn Hugo (Audiobook CD)",
        "author": "Taylor Jenkins Reid",
        "item_type": "audiobook",
        "isbn": "9781549103929",
        "publisher": "Macmillan Audio",
        "publication_year": 2017,
        "subjects": "Fiction, Historical Fiction, Audiobook CD, Old Hollywood",
        "description": "The fabulous life of Old Hollywood icon Evelyn Hugo on CD audiobook format.",
        "page_count": 0,
        "media_format": "cd",
        "disc_count": 17,
        "dewey_decimal": "813.6",
        "call_number": "AB CDR",
        "lc_classification": "PS3618.E57",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 6. EBOOKS
    # =============================================
    {
        "title": "Project Hail Mary (eBook)",
        "author": "Andy Weir",
        "item_type": "ebook",
        "isbn": "9780593135204",
        "publisher": "Ballantine Books",
        "publication_year": 2021,
        "subjects": "Science Fiction, Space, Adventure, eBook",
        "description": "A lone astronaut must save Earth from extinction. [eBook]",
        "page_count": 0,
        "dewey_decimal": "813.54",
        "call_number": "EB WEI",
        "lc_classification": "PS3623.E537",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "Remarkably Bright (eBook)",
        "author": "Catherine Sampson",
        "item_type": "ebook",
        "isbn": "9780008139759",
        "publisher": "HarperCollins",
        "publication_year": 2015,
        "subjects": "Romance, Women's Fiction, eBook",
        "description": "A widow discovers her late husband's hidden past. [eBook]",
        "page_count": 0,
        "dewey_decimal": "823.92",
        "call_number": "EB SAM",
        "lc_classification": "PR6119.A57",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 7. DVDS
    # =============================================
    {
        "title": "Everything Everywhere All at Once",
        "author": "Daniels",
        "item_type": "dvd",
        "publisher": "A24",
        "publication_year": 2022,
        "subjects": "Film, Science Fiction, Family Drama, DVD",
        "description": "Oscar winner exploring multiverse and family.",
        "director": "Daniel Kwan, Daniel Scheinert",
        "actors": "Michelle Yeoh, Ke Huy Quan, Stephanie Hsu",
        "runtime_minutes": 139,
        "media_format": "dvd",
        "disc_count": 1,
        "content_rating": "PG-13",
        "studio": "A24",
        "dewey_decimal": "791.43",
        "call_number": "DVD EVE",
        "lc_classification": "PN1997.2.E87",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "Autism in Love",
        "author": "Matt Fuller",
        "item_type": "dvd",
        "publisher": "Kino Lorber",
        "publication_year": 2015,
        "subjects": "Documentary, Autism, Relationships, DVD",
        "description": "Four adults on the autism spectrum navigate love.",
        "director": "Matt Fuller",
        "runtime_minutes": 89,
        "media_format": "dvd",
        "disc_count": 1,
        "content_rating": "Not Rated",
        "studio": "Kino Lorber",
        "dewey_decimal": "791.43",
        "call_number": "DVD AUT",
        "lc_classification": "PN1997.2.A97",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 8. BLU-RAYS
    # =============================================
    {
        "title": "Oppenheimer (Blu-ray)",
        "author": "Christopher Nolan",
        "item_type": "bluray",
        "publisher": "Universal Pictures",
        "publication_year": 2023,
        "subjects": "Historical Drama, Biography, Blu-ray, Nuclear Physics",
        "description": "The life and times of J. Robert Oppenheimer.",
        "director": "Christopher Nolan",
        "actors": "Cillian Murphy, Robert Downey Jr., Emily Blunt",
        "runtime_minutes": 180,
        "media_format": "bluray",
        "disc_count": 1,
        "content_rating": "R",
        "studio": "Universal Pictures",
        "dewey_decimal": "791.43",
        "call_number": "BLU OPP",
        "lc_classification": "PN1997.2.O55",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "The Lord of the Rings Extended Edition (Blu-ray)",
        "author": "Peter Jackson",
        "item_type": "bluray",
        "publisher": "New Line Cinema",
        "publication_year": 2020,
        "subjects": "Fantasy, Adventure, Blu-ray, Epic",
        "description": "The complete extended edition trilogy in stunning 4K.",
        "director": "Peter Jackson",
        "actors": "Elijah Wood, Ian McKellen, Viggo Mortensen",
        "runtime_minutes": 558,
        "media_format": "bluray",
        "disc_count": 6,
        "content_rating": "PG-13",
        "studio": "New Line Cinema",
        "dewey_decimal": "791.43",
        "call_number": "BLU LOR",
        "lc_classification": "PN1997.2.L65",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 9. MUSIC CDS
    # =============================================
    {
        "title": "1989",
        "author": "Taylor Swift",
        "item_type": "cd",
        "publisher": "Big Machine Records",
        "publication_year": 2014,
        "subjects": "Pop Music, CD, Contemporary",
        "description": "Taylor Swift's pop album featuring 'Shake It Off' and 'Blank Space'.",
        "artist": "Taylor Swift",
        "track_count": 13,
        "music_genre": "Pop",
        "media_format": "cd",
        "content_rating": "Clean",
        "studio": "Big Machine Records",
        "dewey_decimal": "782.42",
        "call_number": "CD SWI",
        "lc_classification": "M1527.S94",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "Abbey Road",
        "author": "The Beatles",
        "item_type": "cd",
        "publisher": "Apple Records",
        "publication_year": 2009,  # Remaster
        "subjects": "Rock Music, CD, Classic",
        "description": "The iconic 1969 album remastered.",
        "artist": "The Beatles",
        "track_count": 17,
        "music_genre": "Rock",
        "media_format": "cd",
        "content_rating": "Clean",
        "studio": "Apple Records",
        "dewey_decimal": "782.42",
        "call_number": "CD BEA",
        "lc_classification": "M1527.B33",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 10. MAGAZINES / PERIODICALS
    # =============================================
    {
        "title": "The New Yorker - February 2026",
        "author": "Conde Nast",
        "item_type": "magazine",
        "publisher": "Conde Nast",
        "publication_year": 2026,
        "subjects": "Magazine, Literature, Current Events",
        "description": "Weekly magazine of culture, politics, and ideas.",
        "dewey_decimal": "051",
        "call_number": "MAG NEW",
        "lc_classification": "AP2.N6",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "National Geographic - March 2026",
        "author": "National Geographic Society",
        "item_type": "magazine",
        "publisher": "National Geographic Society",
        "publication_year": 2026,
        "subjects": "Magazine, Science, Travel, Photography",
        "description": "Exploring the world through stunning photography and journalism.",
        "dewey_decimal": "050",
        "call_number": "MAG NAT",
        "lc_classification": "G1",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 11. GRAPHIC NOVELS
    # =============================================
    {
        "title": "Gender Queer: A Memoir (Graphic Novel)",
        "author": "Maia Kobabe",
        "item_type": "book",
        "isbn": "9781549303005",
        "publisher": "Oni Press",
        "publication_year": 2019,
        "subjects": "Memoir, LGBTQ+, Gender Identity, Graphic Novel",
        "description": "A memoir exploring gender identity and sexuality in graphic novel format.",
        "page_count": 240,
        "dewey_decimal": "741.5",
        "call_number": "GN KOB",
        "lc_classification": "PN6727.K63",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "The Magic Fish (Graphic Novel)",
        "author": "Trung Le Nguyen",
        "item_type": "book",
        "isbn": "9781984851598",
        "publisher": "Random House Graphic",
        "publication_year": 2020,
        "subjects": "Graphic Novel, LGBTQ+, Immigration",
        "description": "A boy uses fairy tales to come out to his parents in graphic novel format.",
        "page_count": 224,
        "dewey_decimal": "741.5",
        "call_number": "GN NGU",
        "lc_classification": "PN6727.N48",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 12. MANGA (with volume numbers)
    # =============================================
    {
        "title": "Attack on Titan Vol. 1",
        "author": "Hajime Isayama",
        "item_type": "book",
        "isbn": "9781612620009",
        "publisher": "Kodansha Comics",
        "publication_year": 2012,
        "subjects": "Manga, Fantasy, Action, Anime",
        "description": "Humanity fights for survival against giant humanoid creatures. Volume 1.",
        "page_count": 192,
        "dewey_decimal": "741.5952",
        "call_number": "MAN ISA V.1",
        "lc_classification": "PN6790.J3",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "Jujutsu Kaisen Vol. 5",
        "author": "Gege Akutami",
        "item_type": "book",
        "isbn": "9781974709724",
        "publisher": "Viz Media",
        "publication_year": 2019,
        "subjects": "Manga, Fantasy, Action, Supernatural",
        "description": "A sorcerer in training battles dark spirits and curses. Volume 5.",
        "page_count": 216,
        "dewey_decimal": "741.5952",
        "call_number": "MAN AKU V.5",
        "lc_classification": "PN6790.J3",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 13. VIDEO GAMES
    # =============================================
    {
        "title": "The Legend of Zelda: Tears of the Kingdom",
        "author": "Nintendo",
        "item_type": "game",
        "publisher": "Nintendo",
        "publication_year": 2023,
        "subjects": "Video Game, Adventure, Fantasy, Nintendo Switch",
        "description": "An epic adventure on the Nintendo Switch platform.",
        "platform": "Nintendo Switch",
        "player_count": "1 player",
        "game_genre": "Adventure",
        "content_rating": "E10+",
        "dewey_decimal": "794.8",
        "call_number": "VG ZEL",
        "lc_classification": "GV1469.35.Z4",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "Elden Ring",
        "author": "FromSoftware",
        "item_type": "game",
        "publisher": "Bandai Namco Entertainment",
        "publication_year": 2022,
        "subjects": "Video Game, Action, RPG, PlayStation 5",
        "description": "Collaboration between FromSoftware and George R.R. Martin.",
        "platform": "PlayStation 5",
        "player_count": "1 player",
        "game_genre": "Action RPG",
        "content_rating": "M",
        "dewey_decimal": "794.8",
        "call_number": "VG ELD",
        "lc_classification": "GV1469.35.E43",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 14. BOARD GAMES
    # =============================================
    {
        "title": "Wingspan",
        "author": "Elizabeth Hargrave",
        "item_type": "game",
        "publisher": "Stonemaier Games",
        "publication_year": 2019,
        "subjects": "Board Game, Birds, Strategy",
        "description": "Award-winning bird-themed engine-building game.",
        "player_count": "1-5 players",
        "game_genre": "Strategy",
        "dewey_decimal": "794.2",
        "call_number": "BG WIN",
        "lc_classification": "GV1312.W56",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "Catan",
        "author": "Klaus Teuber",
        "item_type": "game",
        "publisher": "Catan Studio",
        "publication_year": 2015,
        "subjects": "Board Game, Strategy, Trading",
        "description": "Classic resource management and building game.",
        "player_count": "2-4 players",
        "game_genre": "Strategy",
        "dewey_decimal": "794.2",
        "call_number": "BG CAT",
        "lc_classification": "GV1312.C37",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 15. EQUIPMENT / DEVICES
    # =============================================
    {
        "title": "HP Chromebook 14",
        "author": "HP",
        "item_type": "equipment",
        "publisher": "HP",
        "publication_year": 2023,
        "subjects": "Equipment, Laptop, Computer, Technology",
        "description": "Laptop computer for library patron use.",
        "brand": "HP",
        "model_number": "14a-na0013dx",
        "dimensions": "13.0 x 9.1 x 0.63 inches",
        "material": "Aluminum chassis",
        "dewey_decimal": "004.16",
        "call_number": "EQ LAP",
        "lc_classification": "QA76.5.H6",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "Mobile Hotspot Device - Verizon",
        "author": "Verizon",
        "item_type": "equipment",
        "publisher": "Verizon",
        "publication_year": 2023,
        "subjects": "Equipment, Hotspot, Internet Access, Technology",
        "description": "Portable WiFi hotspot device for community internet access.",
        "brand": "Verizon",
        "model_number": "Moto G7 Micro",
        "dimensions": "6.0 x 3.0 x 1.0 inches",
        "material": "Plastic",
        "dewey_decimal": "621.39",
        "call_number": "EQ HOT",
        "lc_classification": "TK5105.5.V4",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 16. KITS
    # =============================================
    {
        "title": "STEM Learning Kit: Robotics Basics",
        "author": "LEGO Education",
        "item_type": "kit",
        "publisher": "LEGO Education",
        "publication_year": 2023,
        "subjects": "Kit, STEM, Robotics, Education",
        "description": "Complete kit for learning robotics and programming.",
        "kit_contents": "LEGO bricks, robot chassis, motors, sensors, programming software, instruction manual",
        "brand": "LEGO",
        "model_number": "LEGO BOOST",
        "dewey_decimal": "629.892",
        "call_number": "KIT ROB",
        "lc_classification": "TJ211.5.L44",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "Book Club Kit: Modern Classics Discussion Set",
        "author": "Library Services",
        "item_type": "kit",
        "publisher": "LSC Library",
        "publication_year": 2024,
        "subjects": "Kit, Book Club, Discussion",
        "description": "Kit containing multiple copies of a modern classic for book club discussions.",
        "kit_contents": "5 copies of selected novel, discussion guide, facilitator notes, bookmark set",
        "brand": "LSC",
        "model_number": "BC-001",
        "dewey_decimal": "809.3",
        "call_number": "KIT BCK",
        "lc_classification": "PN3311.G8",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 17. MAPS AND ATLASES
    # =============================================
    {
        "title": "World Atlas 2024",
        "author": "National Geographic",
        "item_type": "book",
        "isbn": "9781426220265",
        "publisher": "National Geographic",
        "publication_year": 2023,
        "subjects": "Maps, Atlases, Geography, Reference",
        "description": "Comprehensive world atlas with detailed maps, country information, and statistics.",
        "page_count": 416,
        "dewey_decimal": "912",
        "call_number": "REF NAT",
        "lc_classification": "G1021.N18",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "State Highway Map - Minnesota",
        "author": "Minnesota DOT",
        "item_type": "book",
        "publisher": "Minnesota Department of Transportation",
        "publication_year": 2024,
        "subjects": "Maps, State Maps, Minnesota, Travel",
        "description": "Detailed highway map of Minnesota state.",
        "page_count": 1,
        "dewey_decimal": "912.776",
        "call_number": "MAP MIN",
        "lc_classification": "G4143.G74",
        "cataloging_status": "CATALOGED",
    },

    # =============================================
    # 18. MICROFILM / MICROFICHE
    # =============================================
    {
        "title": "Historical Newspapers Collection - 1900-1950 (Microfilm)",
        "author": "University Microfilms",
        "item_type": "other",
        "publisher": "University Microfilms International",
        "publication_year": 2000,
        "subjects": "Microfilm, Newspapers, Historical Archives, Reference",
        "description": "Complete microfilm collection of historical newspapers from 1900-1950.",
        "dewey_decimal": "070.9",
        "call_number": "MF NEWS",
        "lc_classification": "PN4896.U5",
        "cataloging_status": "CATALOGED",
    },
    {
        "title": "Historical Patents Collection - 1950-2000 (Microfiche)",
        "author": "U.S. Patent Office",
        "item_type": "other",
        "publisher": "U.S. Patent and Trademark Office",
        "publication_year": 2005,
        "subjects": "Microfiche, Patents, Technology, Reference",
        "description": "Microfiche collection of U.S. patents from 1950-2000.",
        "dewey_decimal": "346.7304",
        "call_number": "MF PAT",
        "lc_classification": "KF3114.P8",
        "cataloging_status": "CATALOGED",
    },
]

BRANCHES = ["Main Branch", "Elmdale Branch", "Reference Section", "Digital Collection"]
CONDITIONS = ["excellent", "good", "fair", "poor"]
STATUSES = ["available", "checked_out", "on_hold", "in_transit", "damaged", "lost"]

async def seed_all():
    print("=" * 80)
    print("🌱 LSC Library - COMPREHENSIVE Item Types Seeder")
    print("=" * 80)

    async with async_session() as session:
        try:
            # Get the next available barcode number
            max_barcode_result = await session.execute(
                text("SELECT MAX(CAST(SUBSTRING(barcode, 4) AS INTEGER)) FROM catalog_items WHERE barcode LIKE 'LSC%'")
            )
            max_barcode = max_barcode_result.scalar() or 1000

            # Clean up existing test data if needed
            print("\n📚 Adding/updating catalog items...")
            added_count = 0
            updated_count = 0

            for idx, item in enumerate(CATALOG_ITEMS, 1):
                # Check if item exists
                result = await session.execute(
                    text("SELECT id FROM catalog_items WHERE title = :title"),
                    {"title": item["title"]}
                )
                existing = result.fetchone()

                if existing:
                    # Update existing
                    await session.execute(
                        text("""
                            UPDATE catalog_items SET
                                author = :author,
                                item_type = :item_type,
                                isbn = :isbn,
                                publisher = :publisher,
                                publication_year = :pub_year,
                                subjects = :subjects,
                                description = :description,
                                page_count = :page_count,
                                dewey_decimal = :dewey,
                                call_number = :call_number,
                                lc_classification = :lc_class,
                                cataloging_status = :cat_status,
                                director = :director,
                                actors = :actors,
                                runtime_minutes = :runtime,
                                media_format = :media_format,
                                disc_count = :disc_count,
                                content_rating = :content_rating,
                                studio = :studio,
                                artist = :artist,
                                track_count = :track_count,
                                music_genre = :music_genre,
                                platform = :platform,
                                player_count = :player_count,
                                game_genre = :game_genre,
                                brand = :brand,
                                model_number = :model_number,
                                dimensions = :dimensions,
                                material = :material,
                                kit_contents = :kit_contents
                            WHERE id = :id
                        """),
                        {
                            "id": existing[0],
                            "author": item.get("author"),
                            "item_type": item["item_type"],
                            "isbn": item.get("isbn"),
                            "publisher": item.get("publisher"),
                            "pub_year": item.get("publication_year"),
                            "subjects": item.get("subjects"),
                            "description": item.get("description"),
                            "page_count": item.get("page_count"),
                            "dewey": item.get("dewey_decimal"),
                            "call_number": item.get("call_number"),
                            "lc_class": item.get("lc_classification"),
                            "cat_status": item.get("cataloging_status"),
                            "director": item.get("director"),
                            "actors": item.get("actors"),
                            "runtime": item.get("runtime_minutes"),
                            "media_format": item.get("media_format"),
                            "disc_count": item.get("disc_count"),
                            "content_rating": normalize_rating(item.get("content_rating")),
                            "studio": item.get("studio"),
                            "artist": item.get("artist"),
                            "track_count": item.get("track_count"),
                            "music_genre": item.get("music_genre"),
                            "platform": item.get("platform"),
                            "player_count": item.get("player_count"),
                            "game_genre": item.get("game_genre"),
                            "brand": item.get("brand"),
                            "model_number": item.get("model_number"),
                            "dimensions": item.get("dimensions"),
                            "material": item.get("material"),
                            "kit_contents": item.get("kit_contents"),
                        }
                    )
                    updated_count += 1
                else:
                    # Create new with next available barcode
                    barcode = f"LSC{max_barcode + idx:06d}"
                    await session.execute(
                        text("""
                            INSERT INTO catalog_items (
                                title, author, item_type, status, isbn, publisher,
                                publication_year, description, subjects, page_count,
                                dewey_decimal, call_number, lc_classification,
                                cataloging_status, cataloged_at, location, barcode,
                                director, actors, runtime_minutes, media_format,
                                disc_count, content_rating, studio, artist,
                                track_count, music_genre, platform, player_count,
                                game_genre, brand, model_number, dimensions,
                                material, kit_contents, sensitivity_level, share_count
                            ) VALUES (
                                :title, :author, :item_type, 'available', :isbn,
                                :publisher, :pub_year, :description, :subjects,
                                :page_count, :dewey, :call_number, :lc_class,
                                :cat_status, :now, :location, :barcode,
                                :director, :actors, :runtime, :media_format,
                                :disc_count, :content_rating, :studio, :artist,
                                :track_count, :music_genre, :platform, :player_count,
                                :game_genre, :brand, :model_number, :dimensions,
                                :material, :kit_contents, :sensitivity_level, 0
                            )
                        """),
                        {
                            "title": item["title"],
                            "author": item.get("author"),
                            "item_type": item["item_type"],
                            "isbn": item.get("isbn"),
                            "publisher": item.get("publisher"),
                            "pub_year": item.get("publication_year"),
                            "description": item.get("description"),
                            "subjects": item.get("subjects"),
                            "page_count": item.get("page_count", 0),
                            "dewey": item.get("dewey_decimal"),
                            "call_number": item.get("call_number"),
                            "lc_class": item.get("lc_classification"),
                            "cat_status": item.get("cataloging_status", "CATALOGED"),
                            "now": datetime.now(timezone.utc),
                            "location": BRANCHES[0],
                            "barcode": barcode,
                            "director": item.get("director"),
                            "actors": item.get("actors"),
                            "runtime": item.get("runtime_minutes"),
                            "media_format": item.get("media_format"),
                            "disc_count": item.get("disc_count"),
                            "content_rating": normalize_rating(item.get("content_rating")),
                            "studio": item.get("studio"),
                            "artist": item.get("artist"),
                            "track_count": item.get("track_count"),
                            "music_genre": item.get("music_genre"),
                            "platform": item.get("platform"),
                            "player_count": item.get("player_count"),
                            "game_genre": item.get("game_genre"),
                            "brand": item.get("brand"),
                            "model_number": item.get("model_number"),
                            "dimensions": item.get("dimensions"),
                            "material": item.get("material"),
                            "kit_contents": item.get("kit_contents"),
                            "sensitivity_level": item.get("sensitivity_level", "PUBLIC"),
                        }
                    )
                    added_count += 1

                if (idx) % 5 == 0:
                    print(f"  ✓ Processed {idx}/{len(CATALOG_ITEMS)} items...")

            await session.commit()
            print(f"  ✅ Added {added_count} new items, updated {updated_count} existing items")

            # Create diverse item copies with multiple branches and statuses
            print("\n📖 Creating item copies with multiple branches and varied statuses...")

            # Get all catalog items
            result = await session.execute(text("SELECT id, item_type FROM catalog_items ORDER BY id"))
            catalog_items = result.fetchall()

            copy_count = 0
            for idx, (cat_id, item_type) in enumerate(catalog_items):
                # Create 3-5 copies per item (more for popular types)
                num_copies = 4 if item_type in ["book", "game"] else 3

                for copy_num in range(1, num_copies + 1):
                    # Distribute across branches
                    branch = BRANCHES[(idx + copy_num - 1) % len(BRANCHES)]
                    condition = CONDITIONS[(copy_num - 1) % len(CONDITIONS)]
                    # Vary statuses: first copy available, others mixed
                    if copy_num == 1:
                        status = "available"
                    else:
                        status = STATUSES[(idx + copy_num) % len(STATUSES)]

                    barcode = f"COPY-{cat_id:04d}-{copy_num:03d}"

                    # Check if copy already exists
                    result = await session.execute(
                        text("SELECT id FROM item_copies WHERE barcode = :barcode"),
                        {"barcode": barcode}
                    )
                    if not result.fetchone():
                        await session.execute(
                            text("""
                                INSERT INTO item_copies
                                (catalog_item_id, barcode, condition, location, status, created_at, updated_at)
                                VALUES (:cat_id, :barcode, :condition, :location, :status, :now, :now)
                            """),
                            {
                                "cat_id": cat_id,
                                "barcode": barcode,
                                "condition": condition,
                                "location": branch,
                                "status": status,
                                "now": datetime.now(timezone.utc),
                            }
                        )
                        copy_count += 1

                if (idx + 1) % 5 == 0:
                    print(f"  ✓ Created copies for {idx + 1}/{len(catalog_items)} items...")

            await session.commit()
            print(f"  ✅ Created {copy_count} item copies")

            # Generate summary report
            print("\n" + "=" * 80)
            print("📊 SEED DATA VERIFICATION REPORT")
            print("=" * 80)

            # Count by type
            result = await session.execute(
                text("SELECT item_type, COUNT(*) FROM catalog_items GROUP BY item_type ORDER BY item_type")
            )
            print("\n📚 CATALOG ITEMS BY TYPE:")
            type_counts = {}
            for item_type, count in result.fetchall():
                print(f"   {item_type.upper():20s}: {count:3d} items")
                type_counts[item_type] = count

            # Total items
            result = await session.execute(text("SELECT COUNT(*) FROM catalog_items"))
            total_items = result.scalar()
            print(f"   {'─' * 30}")
            print(f"   {'TOTAL':20s}: {total_items:3d} items")

            # Count copies by status
            print("\n📖 ITEM COPIES BY STATUS:")
            result = await session.execute(
                text("SELECT status, COUNT(*) FROM item_copies GROUP BY status ORDER BY status")
            )
            for status, count in result.fetchall():
                print(f"   {status.upper():20s}: {count:3d} copies")

            # Count copies by branch
            print("\n🏢 ITEM COPIES BY BRANCH:")
            result = await session.execute(
                text("SELECT location, COUNT(*) FROM item_copies GROUP BY location ORDER BY location")
            )
            for location, count in result.fetchall():
                print(f"   {location:20s}: {count:3d} copies")

            # Count copies by condition
            print("\n✨ ITEM COPIES BY CONDITION:")
            result = await session.execute(
                text("SELECT condition, COUNT(*) FROM item_copies GROUP BY condition ORDER BY condition")
            )
            for condition, count in result.fetchall():
                print(f"   {condition.upper():20s}: {count:3d} copies")

            # Total copies
            result = await session.execute(text("SELECT COUNT(*) FROM item_copies"))
            total_copies = result.scalar()
            print(f"   {'─' * 30}")
            print(f"   {'TOTAL':20s}: {total_copies:3d} copies")
            print(f"\n   Average copies per item: {total_copies / total_items:.1f}")

            # Verify cataloging fields
            print("\n📋 CATALOGING VERIFICATION:")
            result = await session.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN call_number IS NOT NULL THEN 1 END) as with_call_number,
                    COUNT(CASE WHEN dewey_decimal IS NOT NULL THEN 1 END) as with_dewey,
                    COUNT(CASE WHEN lc_classification IS NOT NULL THEN 1 END) as with_lc_class
                FROM catalog_items
            """))
            row = result.fetchone()
            print(f"   Total items:             {row[0]}")
            print(f"   With call numbers:       {row[1]} ({row[1]/row[0]*100:.1f}%)")
            print(f"   With Dewey decimals:     {row[2]} ({row[2]/row[0]*100:.1f}%)")
            print(f"   With LC classification:  {row[3]} ({row[3]/row[0]*100:.1f}%)")

            print("\n" + "=" * 80)
            print("✅ SEEDING COMPLETE!")
            print("=" * 80)

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise

async def main():
    try:
        await seed_all()
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
