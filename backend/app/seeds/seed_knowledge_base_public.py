# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import (
    KnowledgeEntry,
    FAQPattern,
    SeasonalFAQ,
)

logger = get_logger(__name__)

STAFF_USER_ID = 2  # Admin User


# ============================================================================
# FAQ Entries (entry_type = "faq")
# ============================================================================

FAQS = [
    {
        "title": "How do I get a library card?",
        "summary": "Visit any branch with a valid photo ID and proof of address to get a free card.",
        "content": "Getting a library card is free. Bring a valid photo ID (driver's license, passport, or state ID) and proof of your current address (utility bill or bank statement) to any branch. Staff will set you up in about five minutes. Minors need a parent or guardian present with their own ID.",
        "category": "Account & Membership",
        "tags": "library card,sign up,new member,registration",
        "is_featured": True,
    },
    {
        "title": "How do I reset my password?",
        "summary": "Use the 'Forgot Password' link on the login page to reset via email.",
        "content": "Click 'Forgot Password' on the login page and enter your email address. You'll receive a reset link within a few minutes. If you don't see it, check your spam folder. You can also visit any branch with your library card and photo ID to have staff reset it for you.",
        "category": "Account & Membership",
        "tags": "password,reset,login,forgot password,account access",
        "is_featured": False,
    },
    {
        "title": "What is reciprocal borrowing?",
        "summary": "Reciprocal borrowing lets you use your card at participating partner libraries.",
        "content": "Our reciprocal borrowing agreements let you check out materials at participating partner libraries using your L30 card. Present your card at the partner library's circulation desk. Loan periods and limits follow the lending library's policies. Ask staff for a current list of partner libraries.",
        "category": "Borrowing & Returns",
        "tags": "reciprocal,partner libraries,borrowing,other libraries",
        "is_featured": False,
    },
    {
        "title": "How many items can I check out at once?",
        "summary": "Standard cards allow up to 50 physical items and 10 digital checkouts at a time.",
        "content": "Standard library cards allow up to 50 physical items (books, DVDs, audiobooks) and 10 digital items (ebooks and audiobooks via MetisLib) checked out simultaneously. There's no limit on the number of holds you can place. If you need a temporary increase for a class or book club, ask staff at the desk.",
        "category": "Borrowing & Returns",
        "tags": "checkout limit,how many,maximum,items,borrowing limit",
        "is_featured": True,
    },
    {
        "title": "How do I renew my books?",
        "summary": "Renew online through your account, by phone, or at any branch.",
        "content": "Log into your account and click 'Renew' next to the item. You can also call any branch or bring the items in person. Most items can be renewed up to two times unless another patron has placed a hold. Renewals extend the due date by the standard loan period from the renewal date.",
        "category": "Borrowing & Returns",
        "tags": "renew,renewal,extend,due date",
        "is_featured": True,
    },
    {
        "title": "Does the library charge late fees?",
        "summary": "No! We are completely fine-free. There are never late fees on overdue items.",
        "content": "We are a fine-free library. You will never be charged late fees for overdue items. Items that are more than 60 days overdue will be marked as lost and a replacement charge may apply, but that charge is removed automatically when you return the item. We believe fines shouldn't be a barrier to using the library.",
        "category": "Borrowing & Returns",
        "tags": "fines,fees,late,overdue,fine-free,no fines",
        "is_featured": True,
    },
    {
        "title": "Where are the book drop locations?",
        "summary": "Book drops are available 24/7 at every branch entrance and at select partner locations.",
        "content": "Every branch has a 24/7 outdoor book drop near the main entrance. Items returned to the book drop are checked in the next business day. Please do not place fragile items (CDs, DVDs) in the outdoor drop during extreme weather. Check our locations page for addresses and hours.",
        "category": "Borrowing & Returns",
        "tags": "book drop,return,drop off,after hours,locations",
        "is_featured": False,
    },
    {
        "title": "How do I download ebooks and audiobooks?",
        "summary": "Use MetisLib in your browser to browse, borrow, and read ebooks and audiobooks.",
        "content": "Visit [metislib.org](https://metislib.org) in any browser — no app download needed. Sign in with your library card number and PIN, browse the collection, tap **Borrow**, and the title opens immediately. Ebooks loan for 14 or 21 days and return automatically. You can read on phone, tablet, or laptop.",
        "category": "Digital Resources",
        "tags": "ebooks,audiobooks,metislib,download,digital",
        "is_featured": True,
    },
    {
        "title": "How do I access library databases from home?",
        "summary": "Log in with your library card number on our Databases page to access all resources remotely.",
        "content": "Visit our website's Databases page and choose the resource you need. When prompted, enter your library card number and PIN. All databases are available 24/7 from any device. Popular resources include Consumer Reports, Ancestry Library Edition (in-library only), and LinkedIn Learning.",
        "category": "Digital Resources",
        "tags": "databases,remote access,research,home access,online resources",
        "is_featured": False,
    },
    {
        "title": "How do I register for library events?",
        "summary": "Browse upcoming events on our Events page and click 'Register' to save your spot.",
        "content": "Visit the Events page on our website to see upcoming programs. Click on any event for details and hit 'Register' to reserve your spot. Some events are drop-in and don't require registration. You'll receive an email confirmation and a reminder the day before. You can cancel anytime from your account.",
        "category": "Events & Programs",
        "tags": "events,register,programs,sign up,activities",
        "is_featured": False,
    },
    {
        "title": "What is the Summer Reading program?",
        "summary": "A free annual program (June-August) with reading goals, prizes, and events for all ages.",
        "content": "Summer Reading runs from June through August and is open to all ages. Sign up on our website or at any branch. Track your reading, earn badges, and win prizes. Kids, teens, and adults all have separate programs with age-appropriate challenges. It's completely free to participate.",
        "category": "Reading Programs",
        "tags": "summer reading,reading program,prizes,summer,kids,teens",
        "is_featured": True,
    },
    {
        "title": "Can I print from my phone or laptop?",
        "summary": "Yes! Use our mobile printing service to send documents from any device.",
        "content": "Send your document to our mobile printing service via email or our website's print portal. Pick up your prints at any branch within 24 hours. Black-and-white prints are $0.10/page and color prints are $0.25/page. You can also print directly from our public computers at no additional charge for the first 10 pages per day.",
        "category": "Technology Help",
        "tags": "printing,mobile print,wireless,phone,laptop",
        "is_featured": False,
    },
    {
        "title": "Can I reserve a meeting room?",
        "summary": "Meeting rooms are free for community use and can be booked online up to 30 days in advance.",
        "content": "Meeting rooms are available free of charge for community groups and individuals. Book online through our Room Reservations page up to 30 days in advance. Rooms accommodate 4 to 40 people depending on the branch. A projector and whiteboard are provided in most rooms. Food and non-alcoholic beverages are permitted.",
        "category": "Services",
        "tags": "meeting room,reserve,book,room,study room,community room",
        "is_featured": False,
    },
    {
        "title": "Does the library offer notary services?",
        "summary": "Yes, free notary service is available at select branches by appointment.",
        "content": "Free notary service is available at our Main Library and Downtown branch by appointment. Call ahead to schedule. Bring the unsigned document, a valid photo ID, and any required witnesses. Notary appointments are typically 15 minutes. Walk-ins are accommodated when a notary is available.",
        "category": "Services",
        "tags": "notary,notarize,free notary,documents",
        "is_featured": False,
    },
    {
        "title": "Is there free WiFi at the library?",
        "summary": "Yes, free high-speed WiFi is available at all branches, no password needed.",
        "content": "Free WiFi is available at all branches. Connect to the 'L30-Library' network — no password required. The connection is filtered for safety and speeds support streaming and video calls. WiFi is accessible in parking lots and outdoor seating areas during operating hours. We also lend mobile hotspots for home use.",
        "category": "Technology Help",
        "tags": "wifi,internet,free wifi,wireless,hotspot",
        "is_featured": False,
    },
    {
        "title": "What is the library's code of conduct?",
        "summary": "Our code of conduct ensures a safe, welcoming environment for everyone.",
        "content": "The library is a shared community space. We ask that all visitors keep noise at a reasonable level, wear shoes and shirts, and treat staff and other patrons with respect. Food is allowed in designated areas. Cell phone conversations should be taken to the lobby. A full copy of our code of conduct is available at any service desk or on our website under Policies.",
        "category": "Policies",
        "tags": "code of conduct,rules,behavior,policy,expectations",
        "is_featured": False,
    },
    {
        "title": "Can I use the public computers?",
        "summary": "Public computers are available at all branches with your library card, no reservation needed.",
        "content": "Public computers are available on a first-come, first-served basis at all branches. Log in with your library card number. Sessions are 60 minutes and can be extended if no one is waiting. All computers have internet access, Microsoft Office, and printing capability. Staff can help you get started if you're new to computers.",
        "category": "Technology Help",
        "tags": "computers,public computers,internet,technology,computer access",
        "is_featured": False,
    },
    {
        "title": "Can I borrow a laptop or hotspot?",
        "summary": "Yes! Laptops and WiFi hotspots are available for checkout with a library card in good standing.",
        "content": "Chromebook laptops loan for 7 days and WiFi hotspots loan for 14 days. A library card in good standing is required. One device per household at a time. Pick up and return at any branch service desk. Late return of devices may result in a temporary lending suspension for technology items only.",
        "category": "Technology Help",
        "tags": "laptop,hotspot,borrow,lend,chromebook,technology lending",
        "is_featured": False,
    },
    {
        "title": "Are there reading challenges I can join?",
        "summary": "We run reading challenges year-round including seasonal and themed options.",
        "content": "We offer reading challenges throughout the year. Summer Reading (June-August) is our biggest program, but we also run a Winter Reading Challenge (December-February) and special themed challenges like Read Around the World and Genre Bingo. Sign up through your account or the Reading Programs page. Earn badges and prizes for completing goals.",
        "category": "Reading Programs",
        "tags": "reading challenge,reading program,bingo,goals,badges",
        "is_featured": False,
    },
    {
        "title": "What AI tools does the library offer?",
        "summary": "We provide free access to AI-powered research tools and digital literacy workshops.",
        "content": "The library offers access to AI-powered research assistants, our FAQ chatbot for quick answers, and regular workshops on using AI tools responsibly. Our digital literacy classes cover topics like evaluating AI-generated content, using AI for homework help, and understanding privacy implications. Check the Events page for upcoming AI workshops.",
        "category": "AI Tools",
        "tags": "AI,artificial intelligence,chatbot,tools,digital literacy",
        "is_featured": False,
    },
    {
        "title": "Can I take free online courses through the library?",
        "summary": "Yes! Access LinkedIn Learning, Coursera, and other platforms free with your library card.",
        "content": "Your library card gives you free access to LinkedIn Learning (thousands of professional courses), plus additional learning platforms available through our Digital Resources page. Courses cover technology, business, creative skills, and more. Certificates of completion are included. Log in with your library card number to get started.",
        "category": "Learning & Courses",
        "tags": "online courses,linkedin learning,free courses,education,professional development",
        "is_featured": False,
    },
    {
        "title": "What are indie ebooks and how do I find them?",
        "summary": "Indie ebooks are self-published titles available in our catalog alongside traditional books.",
        "content": "Our indie ebook collection features vetted, self-published titles from independent authors. Browse them in the catalog using the 'Indie' filter or visit the Indie Catalog section. All indie ebooks are free to borrow with your library card. They are available through our lending platform with the same loan periods as traditional ebooks. Look for the Indie badge in search results.",
        "category": "Indie Catalog",
        "tags": "indie,ebooks,self-published,independent authors,indie catalog",
        "is_featured": False,
    },
]


# ============================================================================
# Guide Entries (entry_type = "guide")
# ============================================================================

GUIDES = [
    {
        "title": "Getting Started with MetisLib",
        "summary": "A step-by-step guide to using MetisLib to borrow your first ebook or audiobook.",
        "content": "MetisLib is our cooperative ebook and audiobook platform. No app required — read in any browser on phone, tablet, or laptop.\n\n**Getting started:**\n\n1. Visit [metislib.org](https://metislib.org) and click **Sign in with library card**.\n2. Enter your library card number and PIN.\n3. Browse the collection by genre, mood, or new releases.\n4. Tap a title and hit **Borrow** to start reading immediately.\n\nBorrowed titles return automatically when the loan expires.\n\n**Why MetisLib:**\n\n- No vendor lock-in — your reading data stays with the library cooperative\n- Place holds on popular titles\n- Tag and organize your reading list\n- Authors and publishers receive a fair revenue share\n\nVisit the [Digital Resources](https://l30.org/digital-resources) page for more details.",
        "category": "Digital Resources",
        "tags": "metislib,ebooks,audiobooks,cooperative,guide,getting started,digital",
        "is_featured": True,
    },
    {
        "title": "Managing Your Account Online",
        "summary": "Learn how to view checkouts, renew items, update your info, and manage holds online.",
        "content": "Log into your account on our website to manage everything in one place. From your dashboard you can: view current checkouts and due dates, renew eligible items, place and manage holds, update your email and phone number, view your reading history (if opted in), and check any outstanding fees. Your PIN is required to log in. If you've never set one, visit any branch with your library card and photo ID.",
        "category": "Account & Membership",
        "tags": "account,online,manage,renew,holds,dashboard,profile",
        "is_featured": False,
    },
    {
        "title": "Using the 3D Printers",
        "summary": "How to submit a 3D print job, choose materials, and pick up your finished print.",
        "content": "Our Main Library has two 3D printers available for public use. To submit a print job: upload your STL file through our 3D Printing Request form online or bring it on a USB drive. Staff will review your file for printability within 1 business day. Prints cost $0.10 per gram of filament. PLA and PETG filaments are available in multiple colors. Most prints take 2-8 hours. You'll receive an email when your print is ready for pickup. Maximum print size is 220x220x250mm.",
        "category": "Technology Help",
        "tags": "3d printer,makerspace,printing,STL,3d print,technology",
        "is_featured": False,
    },
    {
        "title": "Requesting an Interlibrary Loan",
        "summary": "How to request books and materials from other library systems when we don't have them.",
        "content": "If we don't own the item you need, we can request it from another library through Interlibrary Loan (ILL). Log into your account and click 'Interlibrary Loan Request' or fill out an ILL form at any service desk. Provide as much detail as possible: title, author, ISBN, or publication year. Most requests arrive within 1-3 weeks. You'll be notified by email when it's ready. ILL items typically loan for 3 weeks with no renewals. There is no charge for this service.",
        "category": "Services",
        "tags": "interlibrary loan,ILL,request,other libraries,borrow",
        "is_featured": False,
    },
]


# ============================================================================
# Policy Entries (entry_type = "policy")
# ============================================================================

POLICIES = [
    {
        "title": "Privacy & Data Collection Policy",
        "summary": "We protect your privacy and only collect data necessary to provide library services.",
        "content": "Your privacy is a core value. We collect only the data needed to manage your account and lending activity. Reading history is opt-in and can be deleted at any time. We never sell or share patron data with third parties. Circulation records are purged once items are returned. Computer session logs are deleted after 30 days. Our full privacy policy is available at the service desk and on our website.",
        "category": "Policies",
        "tags": "privacy,data,collection,policy,patron data,confidentiality",
        "is_featured": False,
    },
    {
        "title": "Collection Development Policy",
        "summary": "How we select, maintain, and update the library's collection of materials.",
        "content": "Our collection is developed to serve the diverse needs of the community. Selection criteria include community demand, professional reviews, curriculum support, and representation. We welcome purchase suggestions from patrons through the 'Suggest a Purchase' form. Materials are regularly reviewed and withdrawn based on condition, usage, and relevance. Challenged materials are reviewed through a formal reconsideration process. The full policy is available on our website under Policies.",
        "category": "Policies",
        "tags": "collection,development,selection,policy,materials,books,purchasing",
        "is_featured": False,
    },
    {
        "title": "Loan Periods & Limits",
        "summary": "Standard loan periods, renewal limits, and checkout caps for all material types.",
        "content": "Books and audiobooks: 21 days, 2 renewals. DVDs and Blu-ray: 7 days, 1 renewal. Magazines: 14 days, 2 renewals. Ebooks and digital audiobooks: 14 or 21 days (your choice), auto-return. Hotspots: 14 days, no renewal. Laptops: 7 days, no renewal. Maximum checkouts: 50 physical items and 10 digital items. Holds: unlimited. Items with holds cannot be renewed. All loan periods and limits are subject to change; check our website for the latest information.",
        "category": "Borrowing & Returns",
        "tags": "loan period,limits,due date,renewal,checkout,policy,how long",
        "is_featured": True,
    },
]


# ============================================================================
# How-To Entries (entry_type = "how-to")
# ============================================================================

HOWTOS = [
    {
        "title": "How to Reserve a Study Room",
        "summary": "Book a free study room online in just a few clicks, up to 30 days in advance.",
        "content": "Go to the Room Reservations page on our website. Select your preferred branch, date, and time. Available rooms will display with capacity and amenities listed. Click 'Reserve' and confirm with your library card number. You'll receive a confirmation email. Rooms can be booked for up to 2 hours at a time, twice per day. Cancel at least 2 hours before your reservation if your plans change. Walk-in availability may vary.",
        "category": "Services",
        "tags": "study room,reserve,book,room reservation,quiet room",
        "is_featured": False,
    },
    {
        "title": "How to Register for Events",
        "summary": "Find and register for library events through our website or app in seconds.",
        "content": "Visit the Events page and browse by date, category, or age group. Click on an event to see the full description, date, time, and location. Hit 'Register' and sign in with your library card. You'll get an email confirmation and a reminder 24 hours before the event. To cancel, go to your account dashboard and click 'Cancel' next to the event. Some events are drop-in and don't require registration — these are labeled 'No Registration Required.'",
        "category": "Events & Programs",
        "tags": "events,register,sign up,programs,how to,calendar",
        "is_featured": False,
    },
    {
        "title": "How to Place a Hold",
        "summary": "Reserve an item that's currently checked out so you're next in line.",
        "content": "Search for the item in our catalog. If all copies are checked out, click 'Place Hold.' Sign in with your library card number and choose your preferred pickup branch. You'll move into the hold queue. When the item is available, you'll receive an email and/or text notification. You have 7 days to pick it up before the hold expires. You can manage and cancel holds from your account dashboard at any time.",
        "category": "Borrowing & Returns",
        "tags": "hold,reserve,place hold,waiting list,queue",
        "is_featured": False,
    },
]


# ============================================================================
# Read-Alike Entries (entry_type = "read-alike")
# ============================================================================

READ_ALIKES = [
    {
        "title": "If You Liked The Midnight Library",
        "if_you_liked": "The Midnight Library",
        "if_you_liked_author": "Matt Haig",
        "then_try": "Oona Out of Order",
        "then_try_author": "Margarita Montimore",
        "reason": "Both explore alternate life paths with warmth and wonder. If you loved Nora's journey through her unlived lives, Oona's time-jumping adventure through her own years will hit the same sweet spot.",
        "category": "Services",
        "tags": "read-alike,fiction,literary fiction,alternate lives,book recommendation",
        "is_featured": True,
    },
    {
        "title": "If You Liked Project Hail Mary",
        "if_you_liked": "Project Hail Mary",
        "if_you_liked_author": "Andy Weir",
        "then_try": "The Kaiju Preservation Society",
        "then_try_author": "John Scalzi",
        "reason": "Both blend humor with high-concept sci-fi. If you loved Ryland Grace's resourceful problem-solving and unlikely friendship, you'll enjoy Scalzi's witty take on an accidental scientist in an extraordinary situation.",
        "category": "Services",
        "tags": "read-alike,science fiction,sci-fi,humor,book recommendation",
        "is_featured": True,
    },
    {
        "title": "If You Liked Tomorrow, and Tomorrow, and Tomorrow",
        "if_you_liked": "Tomorrow, and Tomorrow, and Tomorrow",
        "if_you_liked_author": "Gabrielle Zevin",
        "then_try": "The Invisible Life of Addie LaRue",
        "then_try_author": "V.E. Schwab",
        "reason": "Both are sweeping stories about creative partnership, identity, and the passage of time. If you loved Sam and Sadie's decades-long bond, Addie's centuries-long fight to be remembered hits the same emotional notes.",
        "category": "Services",
        "tags": "read-alike,fiction,literary fiction,friendship,book recommendation",
        "is_featured": False,
    },
    {
        "title": "If You Liked Lessons in Chemistry",
        "if_you_liked": "Lessons in Chemistry",
        "if_you_liked_author": "Bonnie Garmus",
        "then_try": "Remarkably Bright Creatures",
        "then_try_author": "Shelby Van Pelt",
        "reason": "Both feature unconventional protagonists who defy expectations with quiet determination and dry wit. If Elizabeth Zott won you over, the unlikely bond between a widow and an octopus will charm you just as much.",
        "category": "Services",
        "tags": "read-alike,fiction,humor,heartwarming,book recommendation",
        "is_featured": False,
    },
    {
        "title": "If You Liked The House in the Cerulean Sea",
        "if_you_liked": "The House in the Cerulean Sea",
        "if_you_liked_author": "TJ Klune",
        "then_try": "Legends & Lattes",
        "then_try_author": "Travis Baldree",
        "reason": "Both are cozy, low-stakes fantasies about found family and building something meaningful. If Linus Baker's journey to the island warmed your heart, an orc barbarian opening a coffee shop will do the same.",
        "category": "Services",
        "tags": "read-alike,fantasy,cozy,found family,book recommendation",
        "is_featured": False,
    },
]


# ============================================================================
# FAQ Patterns for chatbot matching
# ============================================================================

# Maps FAQ title to list of patterns
FAQ_PATTERNS = {
    "How do I get a library card?": [
        {"pattern_text": "How do I get a library card?", "pattern_keywords": "library card,get,sign up,register", "priority": 10},
        {"pattern_text": "I want to sign up for a library card", "pattern_keywords": "sign up,library card,new", "priority": 8},
        {"pattern_text": "What do I need to get a library card?", "pattern_keywords": "need,library card,requirements", "priority": 7},
    ],
    "How do I reset my password?": [
        {"pattern_text": "I forgot my password", "pattern_keywords": "forgot,password,reset", "priority": 10},
        {"pattern_text": "How do I change my password?", "pattern_keywords": "change,password,reset,update", "priority": 8},
    ],
    "How many items can I check out at once?": [
        {"pattern_text": "How many books can I check out?", "pattern_keywords": "how many,checkout,limit,books", "priority": 9},
        {"pattern_text": "What is the checkout limit?", "pattern_keywords": "checkout,limit,maximum", "priority": 8},
        {"pattern_text": "Can I borrow more books?", "pattern_keywords": "borrow,more,limit", "priority": 6},
    ],
    "Does the library charge late fees?": [
        {"pattern_text": "Are there late fees?", "pattern_keywords": "late,fees,fines,overdue", "priority": 10},
        {"pattern_text": "How much are library fines?", "pattern_keywords": "fines,fees,how much,cost", "priority": 9},
        {"pattern_text": "What happens if I return a book late?", "pattern_keywords": "late,return,overdue,penalty", "priority": 7},
    ],
    "How do I download ebooks and audiobooks?": [
        {"pattern_text": "How do I get ebooks?", "pattern_keywords": "ebooks,download,digital,get", "priority": 9},
        {"pattern_text": "How does MetisLib work?", "pattern_keywords": "metislib,ebooks,reading,how", "priority": 8},
        {"pattern_text": "Can I borrow ebooks from the library?", "pattern_keywords": "borrow,ebooks,library,digital", "priority": 7},
        {"pattern_text": "What digital resources do you offer?", "pattern_keywords": "digital,resources,ebooks,online", "priority": 6},
        {"pattern_text": "Do you have ebooks?", "pattern_keywords": "ebooks,digital,borrow", "priority": 5},
    ],
    "How do I renew my books?": [
        {"pattern_text": "How do I renew a book?", "pattern_keywords": "renew,book,extend,due date", "priority": 9},
        {"pattern_text": "Can I renew online?", "pattern_keywords": "renew,online,extend", "priority": 8},
    ],
    "Is there free WiFi at the library?": [
        {"pattern_text": "Does the library have WiFi?", "pattern_keywords": "wifi,internet,wireless,free", "priority": 9},
        {"pattern_text": "What is the WiFi password?", "pattern_keywords": "wifi,password,connect,internet", "priority": 8},
    ],
    "What is the Summer Reading program?": [
        {"pattern_text": "When does summer reading start?", "pattern_keywords": "summer,reading,start,when,program", "priority": 9},
        {"pattern_text": "How do I sign up for summer reading?", "pattern_keywords": "summer,reading,sign up,register", "priority": 8},
        {"pattern_text": "Is there a summer program for kids?", "pattern_keywords": "summer,kids,program,reading,children", "priority": 7},
    ],
    "How to Place a Hold": [
        {"pattern_text": "How do I place a hold?", "pattern_keywords": "hold,place,reserve,waiting", "priority": 9},
        {"pattern_text": "Can I reserve a book?", "pattern_keywords": "reserve,book,hold", "priority": 7},
    ],
    "Can I print from my phone or laptop?": [
        {"pattern_text": "Where can I print?", "pattern_keywords": "print,printing,printer", "priority": 9},
        {"pattern_text": "Can I print from my phone?", "pattern_keywords": "print,phone,mobile,wireless", "priority": 8},
        {"pattern_text": "How much does printing cost?", "pattern_keywords": "print,cost,price,printing", "priority": 7},
    ],
}


# ============================================================================
# Seasonal FAQs
# ============================================================================

SEASONAL_FAQS = [
    {
        "faq_title": "What is the Summer Reading program?",
        "season": "summer",
        "start_date": "05-15",
        "end_date": "08-31",
        "priority": 1,
        "seasonal_note": "Summer Reading registration is open!",
    },
    {
        "faq_title": "Are there reading challenges I can join?",
        "season": "winter",
        "start_date": "12-01",
        "end_date": "02-28",
        "priority": 1,
        "seasonal_note": "Winter Reading Challenge is happening now!",
    },
    {
        "faq_title": "How do I register for library events?",
        "season": "summer",
        "start_date": "06-01",
        "end_date": "08-15",
        "priority": 2,
        "seasonal_note": "Summer event schedule is live — register early!",
    },
]


# ============================================================================
# Main Seed Function
# ============================================================================

async def seed_knowledge_base_public(db: AsyncSession) -> bool:
    # Check if patron-facing FAQ entries already exist
    count_result = await db.execute(
        select(func.count()).select_from(KnowledgeEntry).where(
            KnowledgeEntry.entry_type == "faq"
        )
    )
    faq_count = count_result.scalar()

    if faq_count > 5:
        logger.info(f"Knowledge base already has {faq_count} FAQ entries. Skipping.")
        return True

    logger.info("Seeding patron-facing public knowledge base...")

    # Look up actual admin user ID
    global STAFF_USER_ID
    from sqlalchemy import text as _text
    _r = await db.execute(_text("SELECT id FROM users WHERE role IN ('super_admin', 'admin', 'staff') ORDER BY id LIMIT 1"))
    _row = _r.fetchone()
    if _row:
        STAFF_USER_ID = _row[0]

    # Delete the existing placeholder entry and orphaned seasonal FAQs
    await db.execute(delete(SeasonalFAQ))
    await db.execute(delete(FAQPattern))
    await db.execute(delete(KnowledgeEntry))
    await db.flush()

    logger.info("Cleared existing knowledge_entries, seasonal_faqs, and faq_patterns.")

    # Track title -> entry for FK linking
    title_to_entry = {}

    # --- Seed FAQs ---
    for faq_data in FAQS:
        entry = KnowledgeEntry(
            entry_type="faq",
            category=faq_data["category"],
            title=faq_data["title"],
            summary=faq_data["summary"],
            content=faq_data["content"],
            tags=faq_data["tags"],
            is_featured=faq_data["is_featured"],
            source_type="manual",
            review_status="approved",
            added_by_id=STAFF_USER_ID,
            added_by_name="Library Staff",
            view_count=0,
            helpful_count=0,
            version=1,
        )
        db.add(entry)
        title_to_entry[faq_data["title"]] = entry

    # --- Seed Guides ---
    for guide_data in GUIDES:
        entry = KnowledgeEntry(
            entry_type="guide",
            category=guide_data["category"],
            title=guide_data["title"],
            summary=guide_data["summary"],
            content=guide_data["content"],
            tags=guide_data["tags"],
            is_featured=guide_data.get("is_featured", False),
            source_type="manual",
            review_status="approved",
            added_by_id=STAFF_USER_ID,
            added_by_name="Library Staff",
            view_count=0,
            helpful_count=0,
            version=1,
        )
        db.add(entry)
        title_to_entry[guide_data["title"]] = entry

    # --- Seed Policies ---
    for policy_data in POLICIES:
        entry = KnowledgeEntry(
            entry_type="policy",
            category=policy_data["category"],
            title=policy_data["title"],
            summary=policy_data["summary"],
            content=policy_data["content"],
            tags=policy_data["tags"],
            is_featured=policy_data.get("is_featured", False),
            source_type="manual",
            review_status="approved",
            added_by_id=STAFF_USER_ID,
            added_by_name="Library Staff",
            view_count=0,
            helpful_count=0,
            version=1,
        )
        db.add(entry)
        title_to_entry[policy_data["title"]] = entry

    # --- Seed How-Tos ---
    for howto_data in HOWTOS:
        entry = KnowledgeEntry(
            entry_type="how-to",
            category=howto_data["category"],
            title=howto_data["title"],
            summary=howto_data["summary"],
            content=howto_data["content"],
            tags=howto_data["tags"],
            is_featured=howto_data.get("is_featured", False),
            source_type="manual",
            review_status="approved",
            added_by_id=STAFF_USER_ID,
            added_by_name="Library Staff",
            view_count=0,
            helpful_count=0,
            version=1,
        )
        db.add(entry)
        title_to_entry[howto_data["title"]] = entry

    # --- Seed Read-Alikes ---
    for ra_data in READ_ALIKES:
        entry = KnowledgeEntry(
            entry_type="read-alike",
            category=ra_data["category"],
            title=ra_data["title"],
            summary=f"Try {ra_data['then_try']} by {ra_data['then_try_author']}.",
            content=ra_data["reason"],
            if_you_liked=ra_data["if_you_liked"],
            if_you_liked_author=ra_data["if_you_liked_author"],
            then_try=ra_data["then_try"],
            then_try_author=ra_data["then_try_author"],
            reason=ra_data["reason"],
            tags=ra_data["tags"],
            is_featured=ra_data.get("is_featured", False),
            source_type="manual",
            review_status="approved",
            added_by_id=STAFF_USER_ID,
            added_by_name="Library Staff",
            view_count=0,
            helpful_count=0,
            version=1,
        )
        db.add(entry)
        title_to_entry[ra_data["title"]] = entry

    # Flush to get IDs for FK linking
    await db.flush()

    logger.info(f"Seeded {len(title_to_entry)} knowledge entries.")

    # --- Seed FAQ Patterns ---
    pattern_count = 0
    for faq_title, patterns in FAQ_PATTERNS.items():
        entry = title_to_entry.get(faq_title)
        if not entry:
            logger.warning(f"FAQ pattern target not found: {faq_title}")
            continue
        for p in patterns:
            pattern = FAQPattern(
                knowledge_entry_id=entry.id,
                pattern_text=p["pattern_text"],
                pattern_keywords=p["pattern_keywords"],
                match_type="keyword",
                priority=p["priority"],
                match_count=0,
                is_active=True,
            )
            db.add(pattern)
            pattern_count += 1

    logger.info(f"Seeded {pattern_count} FAQ patterns.")

    # --- Seed Seasonal FAQs ---
    seasonal_count = 0
    for sfaq_data in SEASONAL_FAQS:
        entry = title_to_entry.get(sfaq_data["faq_title"])
        if not entry:
            logger.warning(f"Seasonal FAQ target not found: {sfaq_data['faq_title']}")
            continue
        seasonal = SeasonalFAQ(
            knowledge_entry_id=entry.id,
            season=sfaq_data["season"],
            start_date=sfaq_data["start_date"],
            end_date=sfaq_data["end_date"],
            priority=sfaq_data["priority"],
            seasonal_note=sfaq_data["seasonal_note"],
            is_active=True,
            created_by_id=STAFF_USER_ID,
        )
        db.add(seasonal)
        seasonal_count += 1

    logger.info(f"Seeded {seasonal_count} seasonal FAQs.")

    await db.commit()
    logger.info("Public knowledge base seeding complete.")
    return True
