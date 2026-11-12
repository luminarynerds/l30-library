# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import (
    StaffKnowledgeArticle,
    ArticleVersion,
    DecisionTree,
    VideoTutorial,
    OnboardingChecklist,
    StaffQA,
)

logger = get_logger(__name__)


# ============================================================================
# Articles: Policies, Procedures, How-Tos, FAQs
# ============================================================================

ARTICLES = [
    # --- Circulation Policies ---
    {
        "title": "Patron Card Replacement Policy",
        "description": "How to handle lost, stolen, or damaged library cards",
        "content": """PATRON CARD REPLACEMENT POLICY

When a patron reports a lost, stolen, or damaged library card:

1. VERIFY IDENTITY
   - Ask for government-issued photo ID (driver's license, passport, state ID)
   - If no photo ID, ask for two forms of secondary ID (utility bill, bank statement with address)
   - For minors: parent/guardian must be present with their own ID

2. DEACTIVATE OLD CARD
   - Search patron record by name or barcode
   - Mark old card as LOST in the system (Circulation > Patron Lookup > Card Status > Lost)
   - This prevents unauthorized use of the old card

3. ISSUE NEW CARD
   - Click "Issue Replacement Card" in the patron record
   - New card fee: $2.00 (waivable for financial hardship—use your judgment)
   - Print new card and verify barcode scans correctly

4. UPDATE PATRON RECORD
   - Confirm current address, phone, and email
   - Note the replacement in patron notes

EXCEPTIONS:
- First replacement within 12 months: Fee may be waived at staff discretion
- Cards damaged by library equipment: Always waive the fee
- Seniors (65+): Fee waived per board policy 2024-03""",
        "content_type": "policy",
        "category": "Circulation",
        "subcategory": "Card Management",
        "tags": "card,replacement,lost card,damaged card,patron,fee",
    },
    {
        "title": "How to Process an Interlibrary Loan (ILL) Request",
        "description": "Step-by-step guide for processing ILL requests from patrons",
        "content": """INTERLIBRARY LOAN (ILL) REQUEST PROCESSING

ELIGIBILITY:
- Patron must have active library card in good standing
- No overdue items over 30 days
- Maximum 5 active ILL requests per patron

STEP 1: VERIFY ITEM AVAILABILITY
- Check our catalog first to confirm we don't own the item
- Check consortium catalog (OCLC WorldCat)
- If available from a consortium partner, use consortium loan instead (faster)

STEP 2: SUBMIT REQUEST
- Go to Staff > ILL > New Request
- Enter patron barcode and item details (title, author, ISBN if available)
- Select lending library preference (nearest first)
- Set expected delivery method: mail or courier

STEP 3: NOTIFY PATRON
- Estimated arrival: 5-14 business days
- Patron will be notified by email/text when item arrives
- ILL items have a 3-week loan period (non-renewable unless lending library approves)
- ILL items CANNOT be renewed online—patron must contact us

STEP 4: RECEIVING ILL ITEMS
- Check item against request in ILL module
- Apply temporary barcode (use ILL barcode labels)
- Place on hold shelf with patron notification

FEES:
- Most ILL requests: Free
- Rush requests: $5.00
- Some lending libraries charge a fee—always inform patron first""",
        "content_type": "procedure",
        "category": "Circulation",
        "subcategory": "Interlibrary Loan",
        "tags": "ILL,interlibrary loan,request,borrow,lending",
    },
    {
        "title": "Overdue Fine Waiver Guidelines",
        "description": "When and how staff can waive overdue fines",
        "content": """OVERDUE FINE WAIVER GUIDELINES

Staff have discretion to waive fines in the following situations:

AUTOMATIC WAIVER (no supervisor approval needed):
- Fine is $1.00 or less
- Patron is under 18 years old (per board policy—youth fines eliminated)
- Item was returned in the book drop and may have been missed during processing
- Library was closed on the due date (holidays, weather closures, power outage)
- System error caused incorrect fine calculation
- Patron is enrolled in the Fine Forgiveness program (check patron record for flag)

SUPERVISOR APPROVAL REQUIRED:
- Fine is between $1.01 and $25.00 and patron claims hardship
- Fine is related to items damaged by library equipment
- Patron is a new cardholder (first 30 days)

DIRECTOR APPROVAL REQUIRED:
- Fine exceeds $25.00
- Patron has had fines waived 3 or more times in 12 months
- Lost item replacement cost waiver

HOW TO WAIVE:
1. Pull up patron record
2. Go to Fines > Select fine(s) to waive
3. Click "Waive Selected"
4. Select reason from dropdown
5. Add note explaining circumstances
6. Submit (your name and timestamp are recorded automatically)

IMPORTANT: Never make a patron feel judged for requesting a waiver. Financial hardship is a valid reason.""",
        "content_type": "policy",
        "category": "Circulation",
        "subcategory": "Fines",
        "tags": "fine,waiver,overdue,fee,forgiveness,policy",
    },
    {
        "title": "How to Handle a Damaged Item Return",
        "description": "Procedure for assessing and processing damaged items",
        "content": """DAMAGED ITEM RETURN PROCEDURE

STEP 1: ASSESS THE DAMAGE
- Water damage: Check for warping, mold, stuck pages
- Physical damage: Broken spine, torn pages, missing pages
- Stains: Food, drink, ink—assess if item is still usable
- Media: Scratched DVDs/CDs, cracked cases

STEP 2: DETERMINE SEVERITY
- MINOR: Item can still circulate (e.g., small tear, minor cover scuff)
  → Note damage in item record, return to shelf
- MODERATE: Item needs repair (e.g., loose pages, damaged spine)
  → Route to Mending/Repair shelf in processing room
- SEVERE: Item cannot circulate (e.g., water damage, missing pages, mold)
  → Begin damage assessment process

STEP 3: FOR SEVERE DAMAGE
- Pull up the item record and mark as DAMAGED
- Note the damage type and severity
- Photograph the damage (use staff tablet camera)
- Check replacement cost in the system
- Generate damage notice for patron

STEP 4: PATRON NOTIFICATION
- System auto-generates damage assessment email
- Include: Item details, damage description, replacement cost
- Patron has 14 days to dispute the assessment
- Payment options: full replacement cost, or donate a replacement copy

STAFF TIPS:
- Be empathetic—accidents happen
- If a patron reports damage when returning, thank them for their honesty
- Do NOT accuse patrons of intentional damage
- When in doubt about severity, ask a supervisor""",
        "content_type": "procedure",
        "category": "Circulation",
        "subcategory": "Returns",
        "tags": "damaged,item,return,repair,assessment,replacement",
    },

    # --- Patron Services ---
    {
        "title": "New Patron Registration Process",
        "description": "Complete guide to registering new library patrons",
        "content": """NEW PATRON REGISTRATION

REQUIRED INFORMATION:
- Full legal name
- Date of birth
- Current mailing address (must be within service area or eligible township)
- Phone number (at least one)
- Email address (strongly encouraged for notifications)
- Government-issued photo ID

FOR MINORS (under 18):
- Parent or guardian must be present
- Parent/guardian signs the registration form
- Parent/guardian card must be in good standing
- Minor's card linked to parent/guardian account

PROCESS:
1. Welcome the patron and explain card benefits
2. Ask if they've had a card before (check for existing record)
3. Collect required information
4. Verify address (ID or recent utility bill/bank statement)
5. Enter information into the system: Staff > Patron > New Registration
6. Select card type: Adult, Youth (0-12), Teen (13-17), Home Delivery, Bookmobile
7. Print card and test scan
8. Give patron the Welcome Packet (includes hours, services overview, WiFi info)
9. Offer a brief tour if they're interested

SERVICE AREA:
- Residents of Bébé Memorial: Full borrowing privileges
- Non-residents who work in Bébé Memorial: Full privileges with proof of employment
- Reciprocal borrowing: Check consortium agreements
- Non-resident card: $50/year for those outside service area

SPECIAL SITUATIONS:
- Homeless patrons: May use library address; contact supervisor for details
- Temporary residents: Issue 3-month temporary card
- Institutional cards: Schools, daycares—requires director approval""",
        "content_type": "procedure",
        "category": "Patron Services",
        "subcategory": "Registration",
        "tags": "registration,new patron,card,sign up,enroll",
    },
    {
        "title": "Handling Patron Complaints",
        "description": "How to professionally handle and resolve patron complaints",
        "content": """PATRON COMPLAINT HANDLING GUIDE

REMEMBER: Most complaints are about the situation, not about you personally.

STEP 1: LISTEN
- Give the patron your full attention
- Don't interrupt
- Make eye contact and nod to show understanding
- If the patron is upset, let them express their frustration before responding

STEP 2: ACKNOWLEDGE
- "I understand your frustration..."
- "I can see why that would be inconvenient..."
- "Thank you for bringing this to our attention..."
- Avoid "I'm sorry" if the library hasn't done anything wrong—use "I understand" instead

STEP 3: CLARIFY
- Ask questions to fully understand the issue
- Repeat back what you've heard: "So if I understand correctly..."
- Don't make assumptions

STEP 4: RESOLVE
- If you can resolve it immediately, do so
- If you need a supervisor, explain: "Let me get my supervisor who can help with this"
- If it requires follow-up: Get patron's contact info and give a timeline
- Document everything in the patron record

STEP 5: FOLLOW UP
- If you promised follow-up, do it within the stated timeframe
- Even if the issue isn't fully resolved, update the patron on progress

SITUATIONS REQUIRING IMMEDIATE SUPERVISOR:
- Patron is threatening or aggressive
- Patron wants to speak to a manager
- Complaint involves another staff member
- Complaint involves a policy you're unsure about
- Patron mentions legal action

DOCUMENTATION:
- Record all complaints in Staff > Patron > Notes > Complaint
- Include: date, patron name, nature of complaint, resolution, staff member""",
        "content_type": "how_to",
        "category": "Patron Services",
        "subcategory": "Customer Service",
        "tags": "complaint,patron,customer service,conflict,resolution",
    },

    # --- Technology ---
    {
        "title": "Public Computer Troubleshooting Guide",
        "description": "Common computer issues and how to resolve them",
        "content": """PUBLIC COMPUTER TROUBLESHOOTING

COMMON ISSUES AND FIXES:

1. COMPUTER WON'T START
   - Check power cable connection
   - Check power strip is on
   - Try holding power button for 10 seconds, then press again
   - If still won't start: Place "Out of Order" sign and submit IT ticket

2. NO INTERNET CONNECTION
   - Check if other computers are also affected (may be a network issue)
   - Restart the browser
   - If persistent: Restart the computer
   - If all computers affected: Check network switch in server closet (green lights = good)
   - Submit IT ticket if issue persists

3. PRINTER NOT WORKING
   - Check for paper jams (open front panel)
   - Check paper tray levels
   - Verify printer is online: Staff > Print Management > Printer Status
   - Clear print queue if backed up
   - Restart printer (power off, wait 30 seconds, power on)

4. PATRON LOCKED OUT OF SESSION
   - Sessions auto-lock after 15 minutes of inactivity
   - Staff can unlock: Staff > Computer Management > Unlock Station
   - If patron lost work: Unfortunately, unsaved work cannot be recovered

5. USB DRIVE NOT RECOGNIZED
   - Try a different USB port
   - Check if drive works on a staff computer (may be formatted incorrectly)
   - Some drives need to be formatted as FAT32 or exFAT

6. PATRON NEEDS HELP WITH SOFTWARE
   - We can help with basic tasks (printing, email, web search)
   - For complex tasks: Refer to our Tech Help sessions (Tuesdays and Thursdays 2-4 PM)
   - We do NOT provide tech support for personal devices beyond basic WiFi connection

REPORTING ISSUES:
- Submit IT tickets via Staff > Support > New Ticket
- Include: Computer number, description of issue, time observed
- For urgent issues (all computers down, security concern): Call IT directly at ext. 205""",
        "content_type": "how_to",
        "category": "Technology",
        "subcategory": "Troubleshooting",
        "tags": "computer,printer,troubleshooting,IT,technology,public computer",
    },
    {
        "title": "WiFi Access and Troubleshooting for Patrons",
        "description": "Helping patrons connect to library WiFi",
        "content": """WIFI ACCESS GUIDE

NETWORK NAMES:
- L30-Public: General patron use (no password required)
- L30-Secure: Staff only (password changes monthly—check staff board)
- L30-Guest: One-day access for non-cardholders (requires acceptance of terms)

CONNECTING PATRONS:
1. Select "L30-Public" from available networks
2. A captive portal page should appear
3. Accept Terms of Service
4. Patron is connected

IF CAPTIVE PORTAL DOESN'T APPEAR:
- Open a browser and go to any website (e.g., example.com)
- Should redirect to the terms page
- If still no redirect: Try clearing browser cache, or use an incognito/private window

COMMON ISSUES:
- "Connected but no internet": Device may need to forget the network and reconnect
- Slow speeds: We have bandwidth limits per device. Heavy streaming may be throttled
- Can't connect at all: Check if device's WiFi is actually turned on (airplane mode?)
- Chromebook issues: Sometimes need to visit neverssl.com to trigger captive portal

PRINTING FROM PERSONAL DEVICES:
- Patrons can print via our web print portal: print.l30.org
- Upload document, select printer, pay at print release station
- Supported formats: PDF, DOC, DOCX, JPG, PNG

IMPORTANT: We do NOT configure personal devices, install software, or troubleshoot
personal device issues beyond basic WiFi connectivity.""",
        "content_type": "how_to",
        "category": "Technology",
        "subcategory": "WiFi",
        "tags": "WiFi,internet,wireless,connection,troubleshooting",
    },

    # --- Safety & Security ---
    {
        "title": "Emergency Evacuation Procedures",
        "description": "What to do when the fire alarm sounds or an evacuation is needed",
        "content": """EMERGENCY EVACUATION PROCEDURES

WHEN ALARM SOUNDS OR EVACUATION IS ORDERED:

1. REMAIN CALM
   - Do not panic
   - Speak clearly and confidently to patrons

2. ANNOUNCE EVACUATION
   - Use PA system if available: "Attention: Please proceed to the nearest exit immediately."
   - If PA unavailable, walk through your area directing people to exits

3. ASSIST PATRONS
   - Help anyone who needs assistance (mobility issues, children separated from parents)
   - Direct people to nearest exit—DO NOT use elevators
   - Check restrooms and study rooms

4. EVACUATE YOURSELF
   - After clearing your area, exit through nearest exit
   - Do NOT return to retrieve personal items
   - Bring your radio/phone if it's within arm's reach

5. ASSEMBLY POINT
   - Meet at the designated assembly point: Front parking lot, near the flagpole
   - Department heads: Take attendance of your staff
   - Report any missing persons to the Emergency Coordinator

6. WAIT FOR ALL-CLEAR
   - Do NOT re-enter the building until authorized
   - Emergency Coordinator will announce all-clear

FIRE EXTINGUISHER LOCATIONS:
- Main entrance hallway
- Children's area (behind service desk)
- Staff break room
- IT server room
- Meeting rooms hallway

AED LOCATIONS:
- Main circulation desk (wall-mounted)
- Staff break room

EMERGENCY NUMBERS:
- Fire/Police/Ambulance: 911
- Building maintenance emergency: ext. 999
- Library Director cell: Posted in staff break room""",
        "content_type": "policy",
        "category": "Safety & Security",
        "subcategory": "Emergency",
        "tags": "emergency,evacuation,fire,safety,alarm,AED",
    },
    {
        "title": "Closing Procedures Checklist",
        "description": "End-of-day closing procedures for all staff",
        "content": """CLOSING PROCEDURES CHECKLIST

30 MINUTES BEFORE CLOSING:
□ Make PA announcement: "The library will be closing in 30 minutes"
□ Begin walking through the building to alert patrons
□ Start shutting down public computers that are not in use

15 MINUTES BEFORE CLOSING:
□ Second PA announcement: "The library will be closing in 15 minutes"
□ Check all study rooms and meeting rooms
□ Begin cash register closing procedures (count drawer)
□ Run end-of-day circulation report

AT CLOSING TIME:
□ Final PA announcement: "The library is now closed. Thank you for visiting."
□ Walk through all areas to ensure all patrons have left
□ Check restrooms (both main and children's)
□ Check behind shelving units in children's area
□ Lock exterior doors

AFTER PATRONS HAVE LEFT:
□ Complete cash reconciliation
□ Process any remaining items in book drop
□ Reshelve items from returns cart
□ Straighten up children's area
□ Push in all chairs
□ Check for items left behind (log in Lost & Found)
□ Turn off public area lights
□ Set thermostat to overnight mode
□ Ensure all windows are closed and locked
□ Check that fire exits are clear

SECURITY:
□ Arm security system (code: see supervisor)
□ Test door locks on all exits
□ Walk to your car with a buddy when possible
□ Report any suspicious activity near the building

FINAL STEP:
□ Lock main entrance and verify it's secured
□ Drive by and visually confirm building is dark and secured""",
        "content_type": "procedure",
        "category": "Facilities",
        "subcategory": "Daily Operations",
        "tags": "closing,end of day,checklist,security,procedure",
    },

    # --- Staff Management ---
    {
        "title": "Requesting Time Off (PTO)",
        "description": "How to request paid time off and what to expect",
        "content": """REQUESTING TIME OFF (PTO)

SUBMITTING A REQUEST:
1. Go to Staff > My Account > PTO Request
2. Select date range
3. Choose PTO type: Vacation, Sick, Personal, Bereavement, Jury Duty
4. Add notes if relevant
5. Submit for supervisor approval

APPROVAL TIMELINE:
- Requests submitted 2+ weeks in advance: Response within 3 business days
- Requests submitted less than 2 weeks: Response within 1 business day
- Same-day sick leave: Call supervisor directly before shift

PTO ACCRUAL:
- Full-time staff: 1 day per month (first 3 years), 1.5 days per month (3+ years)
- Part-time staff: Pro-rated based on scheduled hours
- Sick leave: 1 day per month (does not expire)
- Maximum carryover: 10 vacation days per year

BLACKOUT PERIODS:
- Summer Reading Program launch week (typically first week of June)
- Annual Book Sale week
- Other blackout periods announced at least 60 days in advance

COVERAGE:
- You are NOT responsible for finding coverage—that's your supervisor's job
- However, it's courteous to mention if a colleague has offered to cover
- For planned absences, please document any pending tasks

EMERGENCY/SICK LEAVE:
- Call your supervisor at least 1 hour before your shift
- If supervisor unavailable, call the library main line
- 3 consecutive sick days require a doctor's note upon return
- FMLA leave: Contact HR for paperwork""",
        "content_type": "policy",
        "category": "Staff Management",
        "subcategory": "Benefits",
        "tags": "PTO,time off,vacation,sick leave,absence,scheduling",
    },
    {
        "title": "Meeting Room Reservation Policy",
        "description": "Rules and procedures for library meeting room bookings",
        "content": """MEETING ROOM RESERVATION POLICY

AVAILABLE ROOMS:
- Community Room A (capacity 50): Projector, screen, podium, WiFi
- Community Room B (capacity 25): TV display, whiteboard, WiFi
- Study Room 1-4 (capacity 4 each): Whiteboard, power outlets
- Maker Lab (capacity 12): 3D printers, computers, craft supplies

BOOKING RULES:
- Study rooms: 2-hour blocks, first-come-first-served, or reserve via website
- Community rooms: Must be reserved at least 48 hours in advance
- Community rooms: Non-profit use is free; commercial use requires $50/hour fee
- Library programs have priority over external bookings
- No alcohol permitted in any library space
- Food is permitted in community rooms only (patron responsible for cleanup)

HOW TO BOOK FOR A PATRON:
1. Staff > Rooms > New Reservation
2. Select room and date/time
3. Enter patron name and contact info
4. Note the purpose of the meeting
5. Review room agreement with patron
6. Confirm reservation (patron receives email confirmation)

CANCELLATIONS:
- 24-hour cancellation notice required for community rooms
- No-shows: Room held for 15 minutes, then released
- 3 no-shows in 12 months: Patron loses reservation privileges for 6 months

SETUP AND CLEANUP:
- Staff sets up tables/chairs for library events
- External groups set up their own configuration
- All groups must leave room in original configuration
- Report any damage to facilities immediately""",
        "content_type": "policy",
        "category": "Facilities",
        "subcategory": "Meeting Rooms",
        "tags": "meeting room,reservation,booking,community room,study room",
    },

    # --- Reference ---
    {
        "title": "How to Help Patrons with Research Questions",
        "description": "Reference interview techniques and database guidance",
        "content": """REFERENCE INTERVIEW GUIDE

THE REFERENCE INTERVIEW:
A reference interview helps you understand what the patron really needs.

OPEN-ENDED QUESTIONS TO ASK:
- "What are you working on?" (school project, personal interest, work-related)
- "What have you already found?" (avoids duplicating effort)
- "How much information do you need?" (quick answer vs. deep research)
- "Is there a specific time period or geographic area?"
- "When do you need this by?"

KEY DATABASES BY TOPIC:
- Academic research: EBSCO Academic Search, JSTOR
- Health information: MedlinePlus, Consumer Health Complete
- Business: Reference USA, Small Business Reference Center
- Legal: LegalTrac, Nolo legal guides
- Genealogy: Ancestry Library Edition, Heritage Quest
- Local history: Our digitized local newspaper archives
- Children's homework: World Book Online, Britannica School

WHEN TO REFER:
- Legal advice: "I can help you find legal information, but I can't give legal advice"
- Medical advice: "Here are some medical databases, but please consult your doctor"
- Tax preparation: We offer seasonal VITA tax help (January-April)
- Complex genealogy: Refer to our monthly Genealogy Club meetings

IMPORTANT PRINCIPLES:
- Never judge what a patron is researching
- Maintain patron privacy—don't discuss research topics with other patrons or staff
- If you don't know the answer, say so and offer to research it
- Follow up: "Did you find what you needed? Can I help with anything else?"

CITING SOURCES:
- Help patrons understand the difference between reliable and unreliable sources
- Point them to our "Evaluating Sources" handout (at the reference desk)""",
        "content_type": "how_to",
        "category": "Reference",
        "subcategory": "Research Assistance",
        "tags": "reference,research,database,interview,patron help",
    },

    # --- Cataloging ---
    {
        "title": "Quick Guide: Adding New Items to the Catalog",
        "description": "Streamlined process for cataloging new acquisitions",
        "content": """ADDING NEW ITEMS TO THE CATALOG

FOR ITEMS WITH ISBN:
1. Go to Staff > Cataloging > New Item
2. Scan or enter ISBN
3. System auto-imports MARC record from OCLC (if available)
4. Review imported data for accuracy:
   - Title, author, publisher, date
   - Subject headings
   - Physical description (pages, dimensions)
5. Add local information:
   - Call number (use our local classification scheme)
   - Location (main collection, reference, children's, YA)
   - Item type (book, DVD, audiobook, etc.)
   - Barcode (scan new barcode label)
6. Save and print spine label

FOR ITEMS WITHOUT ISBN (local publications, gifts, etc.):
1. Staff > Cataloging > New Item > Manual Entry
2. Enter all bibliographic data manually
3. Check OCLC for similar items (may find a matching record)
4. If no match: Create original catalog record
5. Apply appropriate subject headings (use LCSH)
6. Route to supervisor for review before publishing

GIFT ITEMS:
- Check gift acceptance policy before cataloging
- No guarantee that donated items will be added to the collection
- Items not added should be routed to book sale pile
- Thank-you letter generated automatically when gift item is cataloged

COMMON MISTAKES TO AVOID:
- Don't create duplicate records—always search first
- Don't change subject headings without supervisor approval
- Always verify the call number places the item correctly on the shelf
- Attach item to the correct bibliographic record (watch for different editions)""",
        "content_type": "procedure",
        "category": "Cataloging",
        "subcategory": "New Items",
        "tags": "cataloging,new item,MARC,ISBN,catalog,barcode",
    },

    # --- FAQs ---
    {
        "title": "FAQ: What are our operating hours?",
        "description": "Standard library hours and holiday schedule",
        "content": """STANDARD OPERATING HOURS:
Monday-Thursday: 9:00 AM - 8:00 PM
Friday: 9:00 AM - 6:00 PM
Saturday: 10:00 AM - 4:00 PM
Sunday: Closed (except special events)

HOLIDAY CLOSURES (2026):
- New Year's Day (Jan 1)
- Martin Luther King Jr. Day (Jan 19)
- Presidents' Day (Feb 16)
- Memorial Day (May 25)
- Independence Day (July 4)
- Labor Day (Sep 7)
- Thanksgiving (Nov 26-27)
- Christmas Eve & Christmas (Dec 24-25)
- New Year's Eve (Dec 31 - close at 3 PM)

WEATHER CLOSURES:
- Follow the school district's decision
- Director makes final call by 7:00 AM
- Check library website and social media for updates
- Staff: Check the staff text notification chain""",
        "content_type": "faq",
        "category": "Patron Services",
        "subcategory": "Hours",
        "tags": "hours,schedule,holidays,closing,when open",
    },
    {
        "title": "FAQ: How many items can a patron check out?",
        "description": "Checkout limits by patron type and material type",
        "content": """CHECKOUT LIMITS BY PATRON TYPE:

ADULT CARD:
- Books: 50 items
- DVDs: 10 items
- Audiobooks: 10 items
- Magazines: 10 items
- Equipment: 2 items (projector, hotspot, etc.)
- Total maximum: 75 items

TEEN CARD (13-17):
- Books: 25 items
- DVDs: 5 items
- Audiobooks: 5 items
- Total maximum: 35 items

YOUTH CARD (0-12):
- Books: 25 items
- DVDs: 3 items
- Total maximum: 28 items

LOAN PERIODS:
- Books: 3 weeks (2 renewals)
- DVDs: 1 week (1 renewal)
- New releases: 2 weeks (no renewals)
- Magazines: 2 weeks (1 renewal)
- Equipment: 1 week (no renewals)
- ILL items: 3 weeks (no renewals unless approved by lending library)

RENEWALS:
- Online, phone, or in person
- Cannot renew if another patron has a hold on the item
- Cannot renew if patron has overdue items over 30 days""",
        "content_type": "faq",
        "category": "Circulation",
        "subcategory": "Checkout",
        "tags": "checkout,limit,how many,borrow,loan period,renewal",
    },
    # --- Public home page curation (added 2026-06-10) ---
    {
        "title": "Who Controls What Patrons See on the Home Page",
        "description": "Map of the staff pages that change the public home page: hero, shelves, picks, quick links, quotes",
        "content": """WHO CONTROLS WHAT PATRONS SEE ON THE HOME PAGE

The public home page (the page patrons land on) is assembled from a few
different staff surfaces. Here is which page changes what, and who can
use it.

1. HOME PAGE ADMIN (/staff/home-page) — admins only
   - The HERO (the big featured book at the top) and the BOOK SHELVES
     ("New this month", "Staff picks", etc.).
   - Shelves are saved searches, not hand-picked lists. Kinds: new
     arrivals, staff picks, subject, format, manual list.
   - A shelf with no matching items hides itself. That is by design.
   - Hero and shelf items only display if the item is fully cataloged
     and public. If you pick something still in processing, the system
     tells you instead of silently showing nothing.

2. STAFF PICKS (/staff/picks) — any staff member
   - Hand-built recommendation lists ("Summer Picks", "Teen Must-Reads").
   - These power the public /picks page AND the home page "Staff picks"
     shelf, which shows the newest additions across all active lists.
   - Deactivating a list removes it from both places.

3. HOMEPAGE MANAGER (/staff/homepage) — any staff member
   - Quick links and the library-hours strip. Nothing else.

4. HOMEPAGE QUOTES (/staff/admin/homepage-quotes) — admins only
   - The rotating quote.

Changes appear publicly within about a minute (the page is cached
briefly). If something you set is not showing, check that the item is
cataloged and public before assuming the save failed.""",
        "content_type": "how_to",
        "category": "Administration",
        "subcategory": "Public Website",
        "tags": "home page,hero,shelves,staff picks,homepage,public site,curation",
    },
    {
        "title": "Staff Picks: Lists, the /picks Page, and the Home Shelf",
        "description": "How staff-picks lists work and everywhere they appear on the public site",
        "content": """STAFF PICKS: LISTS, THE /PICKS PAGE, AND THE HOME SHELF

WHAT THEY ARE
Staff picks are hand-built lists of titles you recommend, managed at
/staff/picks. Any staff member can create and edit them.

HOW TO ADD ONE
1. Go to Staff Picks (/staff/picks).
2. Create a list (title + a short description patrons will see).
3. Search the catalog and add items. Add a staff note if you want to
   say why you picked it.
4. Keep the list ACTIVE. Inactive lists are hidden everywhere.

WHERE PATRONS SEE THEM
- /picks — every active list, with all its items.
- Home page "Staff picks" shelf — the newest additions across all
  active lists, combined. Adding an item to any active list puts it at
  the front of the home shelf.
- Catalog landing page — highlights the first active list.

THINGS THAT TRIP PEOPLE UP
- Items must be fully cataloged and public to appear on the home page
  shelf. An item mid-processing stays off the public page even though
  it shows inside your list view.
- The same item in two lists appears once on the home shelf.
- The home shelf caps at its configured size (default 6); the full
  set is always on /picks.""",
        "content_type": "how_to",
        "category": "Collection",
        "subcategory": "Staff Picks",
        "tags": "staff picks,picks,recommendations,home page,shelf,curation",
    },
]


# ============================================================================
# Decision Trees
# ============================================================================

DECISION_TREES = [
    {
        "title": "Patron Behavior Issue",
        "description": "How to handle disruptive or concerning patron behavior",
        "category": "Safety & Security",
        "tree_data": {
            "root_node": "is_threatening",
            "nodes": {
                "is_threatening": {
                    "id": "is_threatening",
                    "question": "Is the patron threatening violence or acting aggressively toward staff or other patrons?",
                    "yes_next": {"action": "Call 911 immediately. Do not confront. Activate panic alert if available. Move other patrons away from the area.", "result": "Call 911 immediately. Activate panic alert. Move other patrons to safety. Do not confront the individual. Document the incident after the situation is resolved."},
                    "no_next": "is_disruptive"
                },
                "is_disruptive": {
                    "id": "is_disruptive",
                    "question": "Is the patron being loud, disruptive, or violating library conduct rules?",
                    "yes_next": "first_warning",
                    "no_next": "is_policy_violation"
                },
                "first_warning": {
                    "id": "first_warning",
                    "question": "Have you already given the patron a verbal warning today?",
                    "yes_next": {"action": "Ask patron to leave for the day. If they refuse, contact supervisor.", "result": "Politely but firmly ask the patron to leave for the remainder of the day. If they refuse, contact your supervisor. Document the incident in the patron's record."},
                    "no_next": {"action": "Give a polite verbal warning explaining the specific rule being violated.", "result": "Approach the patron calmly and privately. Explain the specific rule being violated. Ask them to modify their behavior. Be respectful and non-confrontational. If they comply, thank them. If they continue, proceed to asking them to leave."}
                },
                "is_policy_violation": {
                    "id": "is_policy_violation",
                    "question": "Is the patron violating a specific library policy (eating in non-food areas, using phone loudly, etc.)?",
                    "yes_next": {"action": "Politely inform them of the policy and ask them to comply.", "result": "Approach the patron and politely explain the policy. Most patrons will comply when informed respectfully. If they refuse, escalate to supervisor."},
                    "no_next": {"action": "No action needed. Monitor the situation.", "result": "No immediate action needed. If something feels off, trust your instincts and mention it to your supervisor. Document if the situation changes."}
                }
            }
        },
    },
    {
        "title": "Item Condition Assessment",
        "description": "Determine what to do when an item is returned in questionable condition",
        "category": "Circulation",
        "tree_data": {
            "root_node": "visible_damage",
            "nodes": {
                "visible_damage": {
                    "id": "visible_damage",
                    "question": "Does the item have visible damage (water stains, torn pages, broken spine, scratched disc)?",
                    "yes_next": "still_usable",
                    "no_next": "odor_check"
                },
                "still_usable": {
                    "id": "still_usable",
                    "question": "Is the item still usable/readable/playable despite the damage?",
                    "yes_next": {"action": "Note damage in item record. Return to shelf if minor. Route to mending if moderate.", "result": "Add a note to the item record describing the damage. If minor (small tear, scuff), return to shelf. If moderate (loose pages, cracked case), route to the Mending shelf in the processing room."},
                    "no_next": {"action": "Mark as DAMAGED. Generate patron damage notice. Photo document the damage.", "result": "Mark the item as DAMAGED in the system. Photograph the damage. Generate a damage notice for the patron. The replacement cost will be added to their account. Route the item to the discard shelf."}
                },
                "odor_check": {
                    "id": "odor_check",
                    "question": "Does the item have an unusual odor (smoke, mold, food)?",
                    "yes_next": {"action": "Quarantine the item. Do not return to shelf. Check for mold specifically.", "result": "Place the item in the quarantine bin. Do NOT return to shelf—smoke/mold can spread to other items. If mold is suspected, double-bag it and notify the supervisor. Process as damaged if the odor cannot be eliminated."},
                    "no_next": {"action": "Item is in acceptable condition. Process normally.", "result": "The item appears to be in good condition. Process the return normally and return to the shelf or hold shelf as needed."}
                }
            }
        },
    },
    {
        "title": "Computer Reservation Issue",
        "description": "Troubleshoot patron computer access problems",
        "category": "Technology",
        "tree_data": {
            "root_node": "has_card",
            "nodes": {
                "has_card": {
                    "id": "has_card",
                    "question": "Does the patron have a valid library card?",
                    "yes_next": "card_blocked",
                    "no_next": {"action": "Offer guest pass for today. Encourage registration for future visits.", "result": "Issue a Guest Computer Pass (valid for today only, 1 hour session). Explain that a library card gives them 2-hour sessions and the ability to print. Offer to help them register for a card."}
                },
                "card_blocked": {
                    "id": "card_blocked",
                    "question": "Is the patron's card blocked or suspended?",
                    "yes_next": {"action": "Check reason for block. If fines, they can still use computers. If behavioral, refer to supervisor.", "result": "Check the patron's account for the reason. Fines do NOT prevent computer access—log them in normally. If the block is behavioral, refer to your supervisor before granting access."},
                    "no_next": "reservation_exists"
                },
                "reservation_exists": {
                    "id": "reservation_exists",
                    "question": "Is there an available computer, or does the patron need a reservation?",
                    "yes_next": {"action": "Log patron in at an available computer. Standard session is 2 hours.", "result": "Log the patron in at an available workstation. Standard session is 2 hours with one 1-hour extension if no one is waiting. Remind them to save work—sessions end automatically."},
                    "no_next": {"action": "Add to waitlist. Estimated wait time shown in the system.", "result": "Add the patron to the computer waitlist in the system. Let them know their estimated wait time. They'll be called when a station opens. The system automatically assigns the next available computer."}
                }
            }
        },
    },
]


# ============================================================================
# Video Tutorials
# ============================================================================

VIDEO_TUTORIALS = [
    {
        "title": "Circulation System Overview",
        "description": "Complete walkthrough of the check-in, check-out, and hold management features",
        "category": "Circulation",
        "video_url": "/training/videos/circulation-overview.mp4",
        "thumbnail_url": "/training/thumbnails/circulation-overview.jpg",
        "duration_seconds": 720,
        "transcript": "Welcome to the circulation system overview. In this video, we'll walk through check-out, check-in, hold management, and patron lookup...",
    },
    {
        "title": "Handling Difficult Patron Interactions",
        "description": "De-escalation techniques and when to get help",
        "category": "Safety & Security",
        "video_url": "/training/videos/difficult-patrons.mp4",
        "thumbnail_url": "/training/thumbnails/difficult-patrons.jpg",
        "duration_seconds": 540,
        "transcript": "This training video covers de-escalation techniques for handling difficult patron interactions...",
    },
    {
        "title": "Cataloging New Items Step-by-Step",
        "description": "How to add new books, DVDs, and other materials to the catalog",
        "category": "Cataloging",
        "video_url": "/training/videos/cataloging-new-items.mp4",
        "thumbnail_url": "/training/thumbnails/cataloging-new-items.jpg",
        "duration_seconds": 900,
        "transcript": "In this tutorial, we'll walk through the complete process of adding new items to our catalog...",
    },
    {
        "title": "End-of-Day Closing Procedures",
        "description": "Visual walkthrough of the closing checklist",
        "category": "Facilities",
        "video_url": "/training/videos/closing-procedures.mp4",
        "thumbnail_url": "/training/thumbnails/closing-procedures.jpg",
        "duration_seconds": 480,
        "transcript": "This video walks you through the complete closing procedure for the library...",
    },
    {
        "title": "Processing Interlibrary Loans",
        "description": "How to submit, receive, and return ILL items",
        "category": "Circulation",
        "video_url": "/training/videos/ill-processing.mp4",
        "thumbnail_url": "/training/thumbnails/ill-processing.jpg",
        "duration_seconds": 600,
        "transcript": "Interlibrary loans can seem complicated, but this video breaks it down into simple steps...",
    },
    {
        "title": "Emergency Evacuation Drill Walkthrough",
        "description": "Watch a simulated evacuation drill with commentary",
        "category": "Safety & Security",
        "video_url": "/training/videos/evacuation-drill.mp4",
        "thumbnail_url": "/training/thumbnails/evacuation-drill.jpg",
        "duration_seconds": 360,
        "transcript": "This video shows a complete evacuation drill from start to finish...",
    },
    {
        "title": "Reference Interview Techniques",
        "description": "How to conduct an effective reference interview with patrons",
        "category": "Reference",
        "video_url": "/training/videos/reference-interview.mp4",
        "thumbnail_url": "/training/thumbnails/reference-interview.jpg",
        "duration_seconds": 660,
        "transcript": "The reference interview is the foundation of great library service...",
    },
    {
        "title": "Using the Print Management System",
        "description": "Managing public printers, print queues, and troubleshooting",
        "category": "Technology",
        "video_url": "/training/videos/print-management.mp4",
        "thumbnail_url": "/training/thumbnails/print-management.jpg",
        "duration_seconds": 420,
        "transcript": "In this video, we cover the print management system used for public printing...",
    },
]


# ============================================================================
# Q&A Entries
# ============================================================================

QA_ENTRIES = [
    {
        "question": "Where do I find the keys for the meeting rooms? I checked the desk drawer and they're not there.",
        "category": "Facilities",
        "is_answered": True,
        "answer": "Meeting room keys are now kept in the key cabinet on the wall behind the circulation desk (it has a combination lock—code is 4729). Each key is labeled with the room name. Sign keys out on the clipboard and return them at the end of the day. If a key is missing, check with the last person who signed it out.",
    },
    {
        "question": "A patron wants to use our 3D printer for a commercial product. Is that allowed?",
        "category": "Policies & Procedures",
        "is_answered": True,
        "answer": "Per our Makerspace Policy (updated January 2026): The 3D printer is available for personal, educational, and small business use. Commercial use is allowed for small-batch prototyping (under 10 units). Large-scale production runs are not permitted. The patron must sign the Maker Agreement form and agrees that the library is not liable for product quality or safety. If unsure about the scale, check with the Makerspace Coordinator.",
    },
    {
        "question": "What's the process for recommending a book for the collection? A patron keeps asking about a title we don't have.",
        "category": "Cataloging",
        "is_answered": True,
        "answer": "Go to Staff > Acquisitions > Purchase Suggestion. Enter the book details and note that it was patron-requested (this gives it higher priority). You can also suggest the patron submit a request through their online account under 'Suggest a Purchase.' The acquisitions team reviews suggestions weekly. In the meantime, you can also check if it's available through ILL for the patron.",
    },
    {
        "question": "How do I handle a patron who refuses to wear headphones in the quiet study area?",
        "category": "Patron Services",
        "is_answered": False,
        "answer": None,
    },
    {
        "question": "Is there a way to batch-print spine labels for a whole cart of new items, or do I have to do them one by one?",
        "category": "Cataloging",
        "is_answered": False,
        "answer": None,
    },
]


# ============================================================================
# Seeder Function
# ============================================================================

async def seed_staff_knowledge_base(db: AsyncSession) -> None:

    # Check if already seeded
    existing = await db.execute(
        select(StaffKnowledgeArticle.id).limit(1)
    )
    if existing.scalar_one_or_none():
        logger.info("Staff knowledge base already seeded, skipping")
        return True

    logger.info("Seeding staff knowledge base...")

    # Get admin user ID dynamically
    from sqlalchemy import text
    result = await db.execute(text("SELECT id FROM users WHERE role IN ('super_admin', 'admin') ORDER BY id LIMIT 1"))
    admin_row = result.fetchone()
    admin_id = admin_row[0] if admin_row else 1

    # Seed articles
    for article_data in ARTICLES:
        article = StaffKnowledgeArticle(
            title=article_data["title"],
            description=article_data.get("description"),
            content=article_data["content"],
            content_type=article_data["content_type"],
            category=article_data["category"],
            subcategory=article_data.get("subcategory"),
            tags=article_data.get("tags"),
            is_published=True,
            created_by_id=admin_id,  # Dynamic admin user
            current_version=1,
        )
        db.add(article)
        await db.flush()

        # Create initial version
        version = ArticleVersion(
            article_id=article.id,
            version_number=1,
            title=article.title,
            content=article.content,
            change_notes="Initial version",
            changed_by_id=1,
        )
        db.add(version)

    logger.info(f"  Seeded {len(ARTICLES)} knowledge articles")

    # Seed decision trees
    for tree_data in DECISION_TREES:
        tree = DecisionTree(
            title=tree_data["title"],
            description=tree_data.get("description"),
            category=tree_data["category"],
            tree_data=tree_data["tree_data"],
            is_published=True,
            created_by_id=admin_id,
        )
        db.add(tree)

    logger.info(f"  Seeded {len(DECISION_TREES)} decision trees")

    # Seed video tutorials
    for video_data in VIDEO_TUTORIALS:
        video = VideoTutorial(
            title=video_data["title"],
            description=video_data.get("description"),
            category=video_data["category"],
            video_url=video_data["video_url"],
            thumbnail_url=video_data.get("thumbnail_url"),
            duration_seconds=video_data.get("duration_seconds"),
            transcript=video_data.get("transcript"),
            is_published=True,
            created_by_id=admin_id,
        )
        db.add(video)

    logger.info(f"  Seeded {len(VIDEO_TUTORIALS)} video tutorials")

    # Seed Q&A entries
    for qa_data in QA_ENTRIES:
        qa = StaffQA(
            question=qa_data["question"],
            category=qa_data["category"],
            asked_by_id=1,
            is_answered=qa_data["is_answered"],
            answer=qa_data.get("answer"),
            answered_by_id=1 if qa_data["is_answered"] else None,
        )
        db.add(qa)

    logger.info(f"  Seeded {len(QA_ENTRIES)} Q&A entries")

    await db.commit()
    logger.info("Staff knowledge base seeding complete")
