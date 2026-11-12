#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed script for patron-accessible library courses.
Creates neurodivergent-friendly courses available to all patrons.
"""

import asyncio
import os
import sys
sys.path.insert(0, '/app')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.models.learning import Course, Module, Lesson

# Database connection - read from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@localhost:5434/lsc_library")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_digital_literacy_course():
    """Create a patron-accessible digital literacy course."""

    async with async_session() as db:
        # Check if course already exists
        result = await db.execute(select(Course).where(Course.title == "Digital Literacy Basics"))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Course 'Digital Literacy Basics' already exists (id={existing.id}). Skipping.")
            return existing

        # Create the course
        course = Course(
            title="Digital Literacy Basics",
            description="Learn essential digital skills for navigating the internet, using email, and staying safe online. Perfect for beginners or anyone wanting to refresh their knowledge.",
            access_level="patron",
            is_published=True,
            estimated_minutes=60,
            difficulty="beginner",
            sensory_warning="This course contains text-based content with some example screenshots. No auto-playing media or flashing content.",
            xp_reward=150
        )
        db.add(course)
        await db.flush()

        # Module 1: Getting Started with Computers
        module1 = Module(
            course_id=course.id,
            title="Getting Started with Computers",
            description="Basic computer skills including using a mouse, keyboard, and understanding the desktop.",
            sort_order=1
        )
        db.add(module1)
        await db.flush()

        lesson1_1 = Lesson(
            module_id=module1.id,
            title="Understanding Your Computer",
            lesson_type="article",
            content={
                "markdown": """# Understanding Your Computer

Welcome! This lesson introduces you to basic computer concepts. There is no rush - go at your own pace.

## Parts of a Computer

### The Screen (Monitor)
This is where you see everything. The screen shows text, images, and buttons you can interact with.

### The Keyboard
Used for typing text. Each key has a letter, number, or symbol on it.

**Important keys:**
- **Enter/Return:** Confirms actions or starts a new line
- **Backspace:** Deletes text to the left
- **Space bar:** Long key at the bottom - adds spaces between words
- **Shift:** Hold this while pressing a letter to make it CAPITAL

### The Mouse
A device you move with your hand to control a pointer on the screen.

**Mouse basics:**
- **Move:** Slide the mouse on your desk to move the pointer
- **Click:** Press the left button once
- **Double-click:** Press the left button twice quickly
- **Right-click:** Press the right button (opens menus)

### The Desktop
When you turn on the computer, you see the "desktop" - like a digital workspace.

**What you see:**
- **Icons:** Small pictures that represent programs or files
- **Taskbar:** Bar at bottom showing open programs
- **Start button:** Usually in the corner - opens a menu of programs

## Turning On and Off

### Turning On
1. Press the power button (usually marked with ⏻ symbol)
2. Wait for the computer to start (this takes a minute or two)
3. You may need to type a password to log in

### Turning Off Properly
**Important:** Do not just press the power button.

**Correct way:**
1. Click the Start button
2. Look for "Shut Down" or "Power"
3. Click "Shut Down"
4. Wait for the computer to turn off completely

Turning off properly protects your files.

## Practice Tips

Learning to use a computer takes time. That is normal.

**If you make a mistake:**
- It is okay - mistakes rarely break anything
- Try clicking "Cancel" or "No" if a box appears
- Ask for help if you feel stuck

**Remember:**
- There is no "right" speed to learn
- You can always close a program and start over
- The library staff can help if you need it

---

**Next:** Continue to learn about using programs and files.
"""
            },
            estimated_minutes=10,
            sensory_notes="Text only. Clear structure with headings. No time pressure.",
            xp_reward=10,
            sort_order=1
        )
        db.add(lesson1_1)

        lesson1_2 = Lesson(
            module_id=module1.id,
            title="Opening and Closing Programs",
            lesson_type="article",
            content={
                "markdown": """# Opening and Closing Programs

Programs (also called "applications" or "apps") are tools you use on the computer. This lesson shows you how to open and close them.

## What Are Programs?

Programs let you do specific tasks:
- **Web browser:** View websites (like Chrome, Firefox, Edge)
- **Word processor:** Write documents (like Microsoft Word)
- **Email:** Send and receive messages
- **Calculator:** Do math

Each program has a purpose.

## Opening a Program

### Method 1: Desktop Icon
1. Find the program's icon on the desktop
2. Double-click the icon (click twice quickly)
3. Wait for the program to open (takes a few seconds)

### Method 2: Start Menu
1. Click the Start button (bottom corner)
2. Look through the list of programs
3. Click the program name once

### What You See
When a program opens:
- A window appears on screen
- The window has the program's name at the top
- You can now use that program

## Using a Program Window

### Parts of a Window
- **Title bar:** Top bar showing the program name
- **Menu bar:** Row of words like "File" and "Edit" (click these for options)
- **Work area:** Middle section where you do your task
- **Buttons:** Usually in top-right corner

### Common Window Buttons (Top Right)
- **-** (Minimize): Hides window but keeps program running
- **□** (Maximize): Makes window full-screen
- **✕** (Close): Closes the window and program

## Closing a Program

### Method 1: Close Button
Click the **✕** in the top-right corner of the window.

### Method 2: File Menu
1. Click "File" in the menu bar
2. Click "Exit" or "Close"

### What If It Asks "Save Changes?"
If you were working on something, the program might ask if you want to save.

**Options:**
- **Save:** Keeps your work
- **Don't Save:** Loses your changes
- **Cancel:** Goes back to the program

Choose based on whether you want to keep what you did.

## Multiple Programs at Once

You can have several programs open at the same time.

**To switch between them:**
- Click on the program's window
- Or click its icon on the taskbar (bottom of screen)

## If a Program Stops Working

Sometimes a program "freezes" (stops responding).

**What to do:**
1. Wait a moment - it might start working again
2. Try clicking the close button
3. If that does not work, ask library staff for help

Do not worry - this happens to everyone sometimes.

## Practice Exercise

Try this when you are at a computer:
1. Open a simple program (like Calculator)
2. Look at the window parts (title bar, buttons)
3. Minimize it using the **-** button
4. Click its taskbar icon to bring it back
5. Close it using the **✕** button

---

**You are doing great!** Continue to the next module when ready.
"""
            },
            estimated_minutes=12,
            sensory_notes="Step-by-step instructions. Clear structure. Includes practice exercise.",
            xp_reward=10,
            sort_order=2
        )
        db.add(lesson1_2)

        # Module 2: Using the Internet
        module2 = Module(
            course_id=course.id,
            title="Using the Internet",
            description="Learn to browse websites, search for information, and recognize safe links.",
            sort_order=2
        )
        db.add(module2)
        await db.flush()

        lesson2_1 = Lesson(
            module_id=module2.id,
            title="What Is the Internet?",
            lesson_type="article",
            content={
                "markdown": """# What Is the Internet?

The internet is a network that connects computers around the world. It lets you access information, communicate, and use online services.

## Internet vs. Web Browser

### The Internet
The network itself - like roads connecting cities.

### Web Browser
A program you use to view websites - like a car you drive on those roads.

**Common browsers:**
- Google Chrome
- Mozilla Firefox
- Microsoft Edge
- Safari (on Apple devices)

## What Are Websites?

Websites are pages of information stored on the internet.

**Examples:**
- News sites (like bbc.com)
- Search engines (like google.com)
- Library catalog
- Government services
- Shopping sites

Each website has an **address** called a URL.

## Understanding URLs

A URL is a website's address. It looks like this:

`https://www.example.com`

**Parts:**
- **https://**: Security protocol (the "s" means secure)
- **www**: Common prefix (not all sites use it)
- **example.com**: The actual website name
- **.com**: Domain ending (others: .org, .gov, .edu, .ca)

## The Address Bar

At the top of your browser is the **address bar** - a long white box.

**You can:**
- Type a website address here
- See what website you are currently on
- Type search terms (in most browsers)

## How to Visit a Website

### If You Know the Address:
1. Click in the address bar
2. Type the website address (like `wikipedia.org`)
3. Press Enter
4. Wait for the page to load

### If You Are Not Sure:
1. Type what you are looking for in the address bar
2. The browser will search for it
3. Click on a result

## Parts of a Webpage

When a page loads, you might see:

- **Text:** Information to read
- **Links:** Underlined or colored text you can click to go elsewhere
- **Buttons:** Clickable elements (like "Submit" or "Learn More")
- **Images:** Pictures
- **Menus:** Lists of options

## Navigation Buttons

Your browser has helpful buttons:

- **← Back:** Go to the previous page
- **→ Forward:** Go forward (if you went back)
- **⟳ Refresh:** Reload the current page
- **🏠 Home:** Go to your start page

## Loading Pages

When you click a link or type an address:
- The page starts loading
- You might see a spinning circle
- Wait for it to finish (usually a few seconds)

**If a page takes too long:**
- Your internet connection might be slow
- The website might be busy
- Try clicking refresh (⟳)

## Safe Browsing Tips

**Trust your instincts:**
- If a website looks strange or suspicious, close it
- Legitimate sites do not have lots of pop-up windows
- If something asks for personal information unexpectedly, stop

**Look for security:**
- Secure sites show a padlock icon 🔒 in the address bar
- The URL should start with "https://" for sites where you log in or shop

## Common Mistakes (And Why They Are Okay)

### "I clicked something and do not know where I am"
- Click the **Back** button to return
- Or type a website you know in the address bar

### "Too many windows opened"
- Close the extra ones with the **✕** button
- It is okay - you did not break anything

### "The page looks weird"
- Try clicking refresh (⟳)
- The website might be loading

## Remember

Using the internet takes practice. Everyone starts as a beginner. There is no shame in asking questions or taking your time.

---

**Next:** Learn how to search for information online.
"""
            },
            estimated_minutes=15,
            sensory_notes="Informational content. Clear definitions. Calm, reassuring tone.",
            xp_reward=15,
            sort_order=1
        )
        db.add(lesson2_1)

        lesson2_2 = Lesson(
            module_id=module2.id,
            title="Searching Online",
            lesson_type="article",
            content={
                "markdown": """# Searching Online

Search engines help you find information on the internet. This lesson teaches you how to search effectively.

## What Is a Search Engine?

A search engine is a tool that looks through billions of websites to find what you need.

**Popular search engines:**
- Google (google.com)
- Bing (bing.com)
- DuckDuckGo (duckduckgo.com)

They all work similarly.

## How to Search

### Basic Steps:
1. Go to a search engine website (like google.com)
2. Click in the search box
3. Type what you are looking for
4. Press Enter or click the search button
5. Look through the results

### Search Results
You will see a list of websites related to your search.

**Each result shows:**
- **Title:** Name of the webpage (in blue, clickable)
- **URL:** Website address (in green)
- **Description:** Short summary of what is on that page

Click the title to visit that website.

## Writing Good Search Terms

**Be specific:**
- ❌ "food"
- ✓ "easy vegetarian recipes"

**Use important words:**
- ❌ "I want to know about birds in North of Somewhere"
- ✓ "regional birds identification guide"

**Try different words if first search does not help:**
- First try: "how to fix leaky faucet"
- Second try: "repair dripping tap video"

## Search Tips

### Use Quotes for Exact Phrases
- `"L30 Library"` finds that exact phrase
- `L30 Library` finds pages with those words, but not necessarily together

### Search for Specific Sites
- `site:wikipedia.org dinosaurs` searches only Wikipedia for dinosaurs

### Search for Specific File Types
- `beginner knitting PDF` finds PDF documents about knitting

### Exclude Words
- `jaguars -car` finds information about the animal, not the vehicle

## Recognizing Good Search Results

### Trustworthy Sources:
- Government websites (.gov)
- Educational institutions (.edu)
- Established organizations (.org)
- Known news sources
- Library databases

### Be Cautious Of:
- Sites you have never heard of
- Results that seem too good to be true
- Sites with lots of ads covering the content
- Results asking for personal information right away

## Special Searches

### Images
- Click "Images" at the top of search results
- See pictures related to your search
- Click an image to see it larger or visit its website

### Videos
- Click "Videos" to find video content
- Many results link to YouTube

### News
- Click "News" for recent articles about your topic

### Maps
- Search for an address or place name
- Click "Maps" to see location and directions

## Practice Searches

Try these when you are online:

1. **Local search:** Type your town's name + "library hours"
2. **How-to search:** Type "how to boil an egg"
3. **Definition search:** Type "define protagonist"
4. **Current info search:** Type "today's weather [your city]"

## If You Can't Find What You Need

**Try:**
- Rephrasing your search with different words
- Being more specific or more general
- Asking library staff for help
- Using the library catalog instead (for books and articles)

## Safe Searching

**Remember:**
- Not everything on the internet is true
- Check multiple sources for important information
- If a result makes you uncomfortable, close it
- You can always start a new search

## Common Questions

### "How do I get back to my results after clicking?"
Click the **Back** button in your browser.

### "Can I search in my own language?"
Yes! Search engines work in many languages.

### "What if I spell something wrong?"
Search engines usually suggest the correct spelling.

## You Are Building a Skill

Searching well takes practice. The more you do it, the better you will get at finding what you need quickly.

---

**Congratulations!** You have completed Digital Literacy Basics. You now have the foundation to explore the digital world with confidence.
"""
            },
            estimated_minutes=18,
            sensory_notes="Practical examples throughout. Clear formatting. Supportive tone.",
            xp_reward=20,
            sort_order=2
        )
        db.add(lesson2_2)

        await db.commit()
        print(f"Created course 'Digital Literacy Basics' with id={course.id}")
        print(f"  - Module 1: '{module1.title}' (2 lessons)")
        print(f"  - Module 2: '{module2.title}' (2 lessons)")
        print("  - Total: 4 lessons, ~60 minutes")
        print("  - Access level: patron")

        return course


async def create_library_tour_course():
    """Create a patron-accessible virtual library tour course."""

    async with async_session() as db:
        # Check if course already exists
        result = await db.execute(select(Course).where(Course.title == "Library Tour: Getting Started"))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Course 'Library Tour: Getting Started' already exists (id={existing.id}). Skipping.")
            return existing

        # Create the course
        course = Course(
            title="Library Tour: Getting Started",
            description="A gentle introduction to using the Bébé Memorial Library. Learn about our services, how to find books, and what resources are available to you.",
            access_level="patron",
            is_published=True,
            estimated_minutes=30,
            difficulty="beginner",
            sensory_warning="Text-based course with calm pacing. No multimedia. Self-paced - take breaks as needed.",
            xp_reward=100
        )
        db.add(course)
        await db.flush()

        # Module 1: Welcome to the Library
        module1 = Module(
            course_id=course.id,
            title="Welcome to the Library",
            description="Learn about library services and how to get a library card.",
            sort_order=1
        )
        db.add(module1)
        await db.flush()

        lesson1_1 = Lesson(
            module_id=module1.id,
            title="Welcome to Bébé Memorial Library",
            lesson_type="article",
            content={
                "markdown": """# Welcome to Bébé Memorial Library

Welcome! We are glad you are here. This course will help you get comfortable using our library.

## What Is a Library?

A library is:
- A place to borrow books, audiobooks, movies, and more
- A quiet space to read or work
- A source of free programs and resources
- A welcoming community space

**Everything is free.** You do not pay to borrow materials or use our services.

## What We Offer

### Materials You Can Borrow
- **Books:** Fiction and non-fiction for all ages
- **Audiobooks:** Books you can listen to
- **Movies & TV shows:** DVDs and digital options
- **Magazines:** Current and back issues
- **Music:** CDs and digital streaming

### Services
- **Computer access:** Free internet and computers
- **Printing & copying:** Small fee for printing
- **WiFi:** Free throughout the library
- **Research help:** Staff can help you find information
- **Programs:** Book clubs, classes, events

### Spaces
- **Quiet zones:** For focused reading or work
- **Study rooms:** Small rooms you can book
- **Children's area:** Space designed for families
- **Community room:** For events and gatherings

## Our Values

Bébé Memorial Library is:

### Neurodivergent-Friendly
We design our space and services with different needs in mind:
- Quiet spaces available
- Clear signage
- Patient, non-judgmental staff
- Flexible policies when possible

### Accessible
We work to ensure everyone can use our library:
- Wheelchair accessible
- Large print books available
- Assistive technology on computers
- Staff trained to offer accommodations

### Judgment-Free
We welcome everyone:
- No question is too small
- We do not judge what you read or watch
- You can ask for help as many times as you need

## How to Use the Library

You will need a **library card** to:
- Borrow materials
- Use computers
- Access digital resources from home

Getting a card is free and easy. We will cover that in the next lesson.

## Library Etiquette

To help everyone enjoy the library:

**Please:**
- Use quiet voices in quiet zones
- Return materials on time (or renew them)
- Treat materials carefully
- Be respectful of other patrons and staff

**It is okay to:**
- Ask questions
- Need help finding things
- Take your time browsing
- Use the library your own way

## We Are Here to Help

Library staff are here to:
- Help you find materials
- Answer questions
- Show you how to use services
- Make your library experience good

**Never hesitate to ask for help.** That is what we are here for.

---

**Next:** Learn how to get a library card.
"""
            },
            estimated_minutes=8,
            sensory_notes="Welcoming, calm tone. Clear structure. No time pressure.",
            xp_reward=10,
            sort_order=1
        )
        db.add(lesson1_1)

        lesson1_2 = Lesson(
            module_id=module1.id,
            title="Getting Your Library Card",
            lesson_type="article",
            content={
                "markdown": """# Getting Your Library Card

Your library card is your key to using library services. This lesson explains how to get one and how to use it.

## What Is a Library Card?

A library card is a free card with:
- Your name
- A barcode (for checking out materials)
- A card number (for logging in online)

It is yours to keep and use.

## How to Get a Library Card

### What You Need:
1. **Proof of identity:**
   - Driver's license
   - Government-issued ID
   - Passport
   - Or other official ID

2. **Proof of address:**
   - Utility bill
   - Bank statement
   - Lease agreement
   - Government letter
   - (Must show your current address)

### Steps:
1. Come to the library
2. Go to the front desk
3. Tell staff you want a library card
4. Show your ID and proof of address
5. Staff will create your card (takes 2-3 minutes)
6. You get your card right away

**That is it.** You can start using your card immediately.

## If You Do Not Have Proof of Address

Tell staff. We may be able to:
- Accept other forms of proof
- Issue a temporary card
- Work with you to find a solution

## Using Your Library Card

### At the Library:
- Give your card to staff when checking out materials
- Or use the self-checkout machine (staff can show you how)

### Online:
- Log in to your account on our website
- You will need your card number and a PIN (password)
- Staff will give you a default PIN when you get your card
- You can change your PIN to something easier to remember

## What You Can Do Online

With your library card number and PIN, you can:
- Renew borrowed items
- Place holds on books you want
- See what you have checked out
- Access digital books and audiobooks
- Check your account information

## Taking Care of Your Card

**Keep it:**
- In your wallet or a safe place
- Away from magnets (they can damage the barcode)
- Dry (water can damage the card)

**If your card is:**
- **Lost:** Tell staff - they can issue a new one (small replacement fee)
- **Damaged:** Bring it in - we can replace it
- **Not working:** Staff can check the barcode and help

## Card Rules

### Your card is for your use only
Do not let others borrow your card.

### You are responsible for items checked out on your card
Even if someone else borrows it.

### Cards expire
We will send you a renewal notice. Just update your information to keep your card active.

## PIN (Password)

Your PIN keeps your account secure.

**Tips:**
- Choose something you will remember
- Do not share your PIN
- Change it if you think someone else knows it

**To change your PIN:**
- Log in to your account online
- Or ask staff at the front desk

## Family Cards

Each family member should have their own card.

**Why?**
- Children learn responsibility for their own borrowing
- Each person can have their own holds and preferences
- If one person has overdue items, it does not affect others' borrowing

We can set up cards for your whole family in one visit.

## Using Your Card at Other Libraries

Your Bébé Memorial Library card may work at other libraries in our region. Ask staff for details about reciprocal borrowing.

## Questions About Your Card?

Ask staff at any time. We can:
- Look up your card number if you forgot it
- Reset your PIN
- Check your card status
- Help with any card issues

---

**You are ready!** Next, learn how to find and borrow materials.
"""
            },
            estimated_minutes=10,
            sensory_notes="Step-by-step process. Clear, simple language. Reassuring tone.",
            xp_reward=10,
            sort_order=2
        )
        db.add(lesson1_2)

        lesson1_3 = Lesson(
            module_id=module1.id,
            title="Finding and Borrowing Books",
            lesson_type="article",
            content={
                "markdown": """# Finding and Borrowing Books

This lesson teaches you how to find books in the library and borrow them.

## How Books Are Organized

Libraries use a system to organize books so you can find them.

### Fiction Books (Made-up Stories)
Organized **alphabetically by author's last name.**

- Books by Jane Austen are in the "A" section
- Books by Stephen King are in the "K" section

### Non-Fiction Books (True Information)
Organized by **topic** using numbers called Dewey Decimal System.

**Common sections:**
- **000-099:** Computers, general knowledge
- **100-199:** Philosophy, psychology
- **200-299:** Religion
- **300-399:** Social sciences
- **400-499:** Language
- **500-599:** Science
- **600-699:** Technology, cooking, health
- **700-799:** Arts, music, sports
- **800-899:** Literature, poetry
- **900-999:** History, geography

You do not need to memorize these. Just know books on similar topics are grouped together.

## Ways to Find Books

### Method 1: Browse the Shelves
Just walk around and look at books.

**Good for:**
- Discovering new books
- When you know what section you want
- Enjoying the browsing experience

**Tips:**
- Look at spine labels to see section
- Pull out books that interest you
- It is okay to put them back if you change your mind

### Method 2: Use the Library Catalog
The catalog is a searchable database of everything in the library.

**You can search by:**
- Title: "Pride and Prejudice"
- Author: "Jane Austen"
- Subject: "gardening"
- Keyword: any word related to what you want

**How to use it:**
1. Find a catalog computer in the library (or use our website)
2. Type what you are looking for
3. Press Enter or click Search
4. Look through results
5. Write down the **call number** (like "FIC AUS" or "641.5")

The call number tells you where to find the book on the shelf.

### Method 3: Ask Staff
Just ask! Staff can:
- Help you find specific books
- Suggest books you might like
- Show you how to use the catalog
- Look up whether we have something

## Reading the Shelf Labels

Books have labels on their spines showing:
- **Call number:** Where it belongs
- **Author's last name** (for fiction)
- Sometimes a sticker indicating special collection (new books, large print, etc.)

## Checking Out Books

### At the Desk:
1. Bring your books and library card to the front desk
2. Give them to staff
3. Staff will scan your card and the books
4. You will be told when they are due back
5. Take your books and receipt (if you want one)

### Self-Checkout Machine:
1. Scan your library card
2. Place each book on the pad and scan it (staff can show you the first time)
3. Remove books when done
4. Machine will print a receipt with due dates

## Due Dates

You can borrow books for a set time (usually 2-3 weeks).

**Important:**
- Due dates are stamped in books or printed on receipt
- You can write down due dates at home
- You will get a reminder email before items are due

## Renewing Books

If you are not finished with a book, you can **renew** it - borrow it for longer.

**How to renew:**
- Online through your account
- By phone
- In person at the library
- Usually you can renew 2-3 times

**You cannot renew if:**
- Someone else has placed a hold on the book
- The book is already overdue
- You have reached the renewal limit

## Holds (Reserving Books)

If a book is checked out, you can **place a hold** - reserve it for when it comes back.

**How:**
1. Search for the book in the catalog
2. Click "Place Hold"
3. Log in with your card number and PIN
4. Wait for notification that it is ready (email or phone)
5. Pick it up within the hold period (usually 7 days)

Holds are free.

## What If a Book Is Damaged?

If you notice damage when you borrow a book:
- Tell staff before you leave
- They will make a note on your account
- You will not be charged for pre-existing damage

## Late Returns

If you return books late:
- There may be a small fine per day
- Or your account might be blocked from borrowing until you return items
- Just bring them back as soon as you can

**Having trouble returning on time?**
- Renew items before they are due
- Talk to staff if there is a problem - we can often help

## Returning Books

### Book Drop:
- Outside the library for after-hours returns
- Just drop books through the slot
- Do not put DVDs in outdoor drop (they can be damaged by weather)

### Inside Returns:
- Bring books to the front desk
- Or place in the indoor book return

**Your account updates:**
Books are checked in usually within 24 hours of return.

## Tips for Successful Borrowing

1. **Set reminders:** Note due dates on your calendar
2. **Keep books together:** Have a spot at home for library books
3. **Renew early:** Do not wait until the last day
4. **Ask questions:** Staff can help with any part of this process

---

**Congratulations!** You now know how to use Bébé Memorial Library. Enjoy exploring!
"""
            },
            estimated_minutes=15,
            sensory_notes="Comprehensive but organized. Clear sections. Practical instructions.",
            xp_reward=15,
            sort_order=3
        )
        db.add(lesson1_3)

        await db.commit()
        print(f"Created course 'Library Tour: Getting Started' with id={course.id}")
        print(f"  - Module 1: '{module1.title}' (3 lessons)")
        print("  - Total: 3 lessons, ~30 minutes")
        print("  - Access level: patron")

        return course


async def main():
    print("Seeding patron-accessible courses...")
    print()

    try:
        course1 = await create_digital_literacy_course()
        print()
        course2 = await create_library_tour_course()
        print()
        print("✓ Done! Created 2 patron-level courses.")
        print()
        print("Patrons can now access:")
        print(f"  1. {course1.title}")
        print(f"  2. {course2.title}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
