# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import random
from datetime import datetime, timedelta, timezone, date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

utc = timezone.utc


def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago)


def _past_date(days_ago: int) -> date:
    return (datetime.now(utc) - timedelta(days=days_ago)).date()


async def seed_batch_staff_facing(session: AsyncSession) -> bool:

    # Grab reusable IDs
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] in ("patron", "child")]
    all_ids = [u[0] for u in users]

    plans_r = await session.execute(text("SELECT id FROM strategic_plans LIMIT 1"))
    plan_row = plans_r.fetchone()
    plan_id = plan_row[0] if plan_row else None

    courses_r = await session.execute(text("SELECT id FROM courses"))
    course_ids = [r[0] for r in courses_r.fetchall()]

    lessons_r = await session.execute(text("SELECT id, module_id FROM lessons"))
    lessons = lessons_r.fetchall()
    lesson_ids = [r[0] for r in lessons]

    gtc_r = await session.execute(text("SELECT id FROM genealogy_training_courses"))
    gtc_ids = [r[0] for r in gtc_r.fetchall()]

    partners_r = await session.execute(text("SELECT id FROM outreach_partners"))
    partner_ids = [r[0] for r in partners_r.fetchall()]

    now = datetime.now(utc)

    # ════════════════════════════════════════════════════════════════
    # 1. STAFF KNOWLEDGE ARTICLES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM staff_knowledge_articles"))
    if r.scalar() == 0:
        print("  Seeding staff_knowledge_articles...")
        articles = [
            ("Circulation Desk Opening Procedures", "Step-by-step guide for opening the circulation desk each morning.",
             "Complete checklist for starting the circulation desk:\n\n1. Log into the ILS workstation with your staff credentials.\n2. Check the overnight book drop — sort returns into bins by material type.\n3. Process all returns through the system, checking for damage or notes.\n4. Count and verify the cash drawer float ($100.00 for main desk).\n5. Check the holds shelf — pull any holds that expired overnight.\n6. Review the daily schedule board for staffing changes.\n7. Turn on self-checkout kiosks and verify they connect to the network.\n8. Check printer paper and receipt roll supplies.\n9. Review any notes left by the closing staff from the previous evening.\n10. Unlock the front doors at exactly the posted opening time.",
             "procedure", "circulation", "opening", "circulation,opening,checklist,daily", 87),

            ("Handling Patron Complaints: De-escalation Guide", "Best practices for managing upset or frustrated patrons.",
             "When a patron is upset, follow the LAST method:\n\nL — Listen: Let the patron explain their concern fully without interrupting. Make eye contact and nod to show you are engaged.\n\nA — Acknowledge: Validate their feelings. Say things like 'I understand that must be frustrating' or 'I can see why that would be upsetting.'\n\nS — Solve: Offer a concrete solution or explain the steps you will take. If you cannot resolve it immediately, give a timeline.\n\nT — Thank: Thank the patron for bringing the issue to your attention. This reframes the interaction positively.\n\nKey rules:\n- Never argue or get defensive.\n- If a patron becomes verbally abusive, calmly state: 'I want to help you, but I need us to speak respectfully.'\n- If you feel physically unsafe, use the staff alert code and contact a supervisor.\n- Document all complaints in the incident log within 30 minutes.",
             "guide", "patron_services", "complaints", "patron,complaints,de-escalation,conflict", 134),

            ("Interlibrary Loan (ILL) Processing", "How to submit, track, and fulfill ILL requests.",
             "ILL Request Processing:\n\n1. Patron submits ILL request via catalog or at the desk.\n2. Verify the item is not available in our consortium (check all branches first).\n3. Search OCLC WorldCat for lending libraries.\n4. Submit request through ILLiad, selecting up to 5 potential lenders.\n5. Track request status — typical turnaround is 7-14 business days.\n6. When item arrives, check condition, apply ILL band, and place on patron hold shelf.\n7. Notify patron via email/text that their ILL item is ready.\n8. Loan period for ILL items is determined by the lending library (usually 21-28 days).\n9. ILL items CANNOT be renewed without lending library approval.\n10. When returned, remove ILL band, check condition, and ship back within 2 business days.\n\nCosts: Most ILL requests are free to patrons. If the lending library charges a fee over $10, contact the patron before proceeding.",
             "procedure", "circulation", "ILL", "ILL,interlibrary-loan,OCLC,requests", 62),

            ("Cataloging Standards: MARC Record Basics", "Quick reference for MARC field usage in original cataloging.",
             "Essential MARC fields for original cataloging:\n\n- 020: ISBN\n- 100: Main entry (personal name/author)\n- 245: Title statement (include subtitle in $b, statement of responsibility in $c)\n- 250: Edition statement\n- 264: Publication info (place $a, publisher $b, date $c)\n- 300: Physical description (pages $a, dimensions $c)\n- 336/337/338: Content, media, carrier types (RDA)\n- 490: Series statement\n- 500: General notes\n- 520: Summary\n- 650: Subject headings (LCSH)\n- 655: Genre/form terms\n\nAlways check for existing records in OCLC before creating original cataloging. Copy cataloging saves time and ensures consistency. When editing imported records, verify the 050/090 call number matches our local classification scheme.",
             "reference", "cataloging", None, "cataloging,MARC,RDA,metadata", 45),

            ("Emergency Evacuation Procedures", "Building evacuation protocol for all emergencies.",
             "EMERGENCY EVACUATION — ALL STAFF MUST KNOW\n\nWhen the alarm sounds or an evacuation is ordered:\n\n1. REMAIN CALM. Do not shout or run.\n2. Direct patrons to the nearest exit. Use firm, clear instructions: 'Please follow me to the exit.'\n3. Sweep your assigned zone — check restrooms, study rooms, and hidden corners.\n4. Assist anyone with mobility issues. Wheelchair users: use the evacuation chair stored at each stairwell.\n5. Do NOT use elevators during fire emergencies.\n6. Proceed to the designated assembly point in the east parking lot.\n7. Take the attendance clipboard from the circulation desk if possible.\n8. Account for all staff in your zone. Report to the Incident Commander (Branch Manager or senior staff on duty).\n9. Do NOT re-enter the building until the fire department gives the all-clear.\n\nAssembly point: East parking lot, near the flagpole.\nFire extinguisher locations: Main lobby, staff workroom, community room A, children's area.\nAED location: Front entrance, mounted on wall near restrooms.",
             "procedure", "safety", "evacuation", "emergency,evacuation,fire,safety,AED", 201),

            ("Technology Troubleshooting: Public Computers", "Common tech issues and solutions for patron workstations.",
             "Common issues and fixes:\n\nPrinter not working:\n1. Check if printer is online (green light on front panel).\n2. Verify paper tray is loaded and not jammed.\n3. Restart the print release station.\n4. If still failing, restart the printer using the power button on the back.\n\nComputer frozen:\n1. Try Ctrl+Alt+Delete to access Task Manager.\n2. End unresponsive applications.\n3. If completely frozen, hold power button for 10 seconds to force restart.\n4. DeepFreeze will restore to default state on reboot.\n\nInternet not working:\n1. Check if other stations are affected (might be network-wide).\n2. Run 'ipconfig /release' then 'ipconfig /renew' from admin command prompt.\n3. If network-wide, restart the public network switch in the server closet (labeled SWITCH-PUB-1).\n4. Call IT support if issue persists beyond 15 minutes.\n\nPatron cannot log in:\n1. Verify their library card is active.\n2. Check if their computer privileges are suspended (ILS patron record).\n3. Reset session time if needed through the admin console.",
             "guide", "technology", "troubleshooting", "computers,printing,network,troubleshooting", 156),

            ("Programming Guidelines: Planning Library Events", "Standards and checklists for planning and executing library programs.",
             "Event Planning Checklist:\n\nSix Weeks Before:\n- Submit program proposal form to supervisor.\n- Reserve room and equipment.\n- Confirm presenter/performer availability and fee.\n- Draft promotional copy and submit to marketing.\n\nFour Weeks Before:\n- Create event in the events calendar system.\n- Order supplies and materials.\n- Send press release to local media.\n- Post on social media channels.\n\nOne Week Before:\n- Confirm presenter, room setup, and AV needs.\n- Print sign-in sheets and evaluation forms.\n- Send reminder to registered attendees.\n- Prepare materials/handouts.\n\nDay Of:\n- Set up room at least 30 minutes before start.\n- Test all technology (projector, sound, WiFi).\n- Set out sign-in sheet, name tags, and handouts.\n- Welcome attendees warmly.\n\nAfter Event:\n- Collect evaluation forms.\n- Enter attendance and demographics into the stats system.\n- Submit supply receipts for reimbursement.\n- Send thank-you to presenter within 48 hours.\n- File event report within one week.",
             "guide", "programming", None, "events,programming,planning,marketing", 93),

            ("Collection Development Criteria", "Guidelines for selecting new materials for the collection.",
             "Selection Criteria:\n\nAll materials are evaluated against the following criteria:\n\n1. Community Relevance: Does it meet an identified community need or interest?\n2. Authority: Is the author/creator qualified? Is the publisher reputable?\n3. Accuracy: Is the information current and factually correct?\n4. Literary/Artistic Merit: Does it meet quality standards for its format?\n5. Demand: Is there patron interest (purchase suggestions, hold ratios, trend data)?\n6. Format Suitability: Is this the best format for the content and our patrons?\n7. Cost: Is the price reasonable for the expected use?\n8. Collection Balance: Does it fill a gap or replace a worn/outdated item?\n\nAutomatic Purchase Triggers:\n- New York Times bestsellers (top 15 fiction and nonfiction)\n- 3+ patron purchase requests for the same title\n- Award winners: Pulitzer, National Book Award, Caldecott, Newbery, Hugo, Nebula\n\nWeeding Schedule:\n- Nonfiction: Review items not circulated in 5 years\n- Fiction: Review items not circulated in 3 years\n- Reference: Annual review for currency\n- Periodicals: Keep current year + 2 years for magazines, 1 year for newspapers",
             "reference", "collection_development", None, "collection,selection,weeding,acquisitions", 78),

            ("Self-Checkout Kiosk Troubleshooting", "Resolving common self-checkout station issues.",
             "Self-Checkout Station Troubleshooting Guide:\n\nScanner not reading barcodes:\n1. Clean the scanner glass with the microfiber cloth stored in the station drawer.\n2. Ensure items are placed barcode-down on the scanner.\n3. Try manual barcode entry using the on-screen keyboard.\n4. If scanner hardware fails, place an 'Out of Order' sign and notify IT.\n\nReceipt printer issues:\n1. Open the printer compartment (latch on right side).\n2. Check paper roll — replace if low (stock in supply cabinet B).\n3. If jammed, gently pull paper free and rethread.\n4. Close compartment firmly until you hear the click.\n\nKiosk screen frozen:\n1. Do NOT unplug the kiosk.\n2. Use the staff override card to access the admin menu.\n3. Select 'Restart Application' from the admin menu.\n4. If that fails, press and hold the small reset button on the back panel (use a pen).\n\nPatron locked out:\n1. Patrons with outstanding fines over $10 are blocked from self-checkout.\n2. Direct them to the circulation desk for assistance.\n3. Staff can override the block if the patron makes a partial payment.",
             "procedure", "technology", "self-checkout", "self-checkout,kiosk,scanner,troubleshooting", 112),

            ("Storytime Best Practices", "Tips for engaging and effective storytimes for different age groups.",
             "Storytime Guidelines by Age Group:\n\nBaby Storytime (0-18 months):\n- Keep to 20 minutes maximum.\n- Use board books with high-contrast images.\n- Include songs, rhymes, and gentle bouncing activities.\n- Explain early literacy concepts to caregivers during the session.\n\nToddler Storytime (18-36 months):\n- 25-minute sessions.\n- Choose books with repetitive text and audience participation.\n- Include a simple craft or sensory activity.\n- Allow movement — these kids cannot sit still for long!\n\nPreschool Storytime (3-5 years):\n- 30-minute sessions.\n- Read 2-3 picture books on a theme.\n- Include a flannel board or puppet activity.\n- End with a craft or coloring activity.\n\nFamily Storytime (all ages):\n- 30-minute sessions.\n- Mix books for different levels.\n- Include songs everyone can sing along to.\n- Encourage siblings to participate together.\n\nGeneral Tips:\n- Always read the book to yourself before presenting it.\n- Practice voices and expressions.\n- Make eye contact with your audience.\n- Be flexible — if the kids are restless, skip ahead or add movement.",
             "guide", "programming", "storytimes", "storytime,children,early-literacy,programming", 167),

            ("Fine and Fee Policy Quick Reference", "Summary of current fine and fee schedules.",
             "Current Fine & Fee Schedule (effective January 2026):\n\nOverdue Fines:\n- Books, audiobooks: $0.25/day (max $5.00)\n- DVDs, Blu-ray: $1.00/day (max $10.00)\n- Magazines, periodicals: $0.10/day (max $2.00)\n- Interlibrary loan items: $0.50/day (max $10.00)\n- Equipment (laptops, hotspots): $5.00/day (max $50.00)\n\nReplacement Charges:\n- Lost items: Retail replacement cost + $5.00 processing fee\n- Damaged items: Assessed by staff (minimum $5.00)\n- Lost library card: $2.00 replacement fee\n- Lost DVD case: $2.00\n\nFee Waivers:\n- Director may waive fines for hardship cases.\n- All children under 18 have fines waived automatically.\n- Food for Fines program runs annually in November.\n- Reading minutes can offset fines during Summer Reading.\n\nPayment Methods: Cash, check, credit/debit card (in-person or online).\nMinimum card payment: $1.00",
             "reference", "circulation", "fines", "fines,fees,overdue,payments,waivers", 198),

            ("Room Reservation Management", "How to process and manage meeting room reservations.",
             "Meeting Room Reservation Procedures:\n\nAccepting Reservations:\n1. Verify the requester represents a nonprofit or community group.\n2. Check room availability in the booking system.\n3. Confirm the room capacity meets their needs (Room A: 50, Room B: 25, Study Rooms: 4-6).\n4. Have the requester sign the Meeting Room Agreement form.\n5. Note any special equipment needs (projector, microphone, etc.).\n\nDay of Reservation:\n1. Unlock the room 15 minutes before the scheduled time.\n2. Set up any requested equipment.\n3. Provide the WiFi password for the meeting room network.\n4. Check in after the event to assess room condition.\n5. Lock the room after the group departs.\n\nCancellations:\n- Groups must cancel at least 24 hours in advance.\n- Two no-shows result in a 30-day booking suspension.\n\nRestrictions:\n- No admission fees, no sales, no alcohol.\n- The library name cannot be used to imply endorsement.\n- Maximum booking: 4 hours per session, 2 sessions per month per group.\n- After-hours use requires Board approval and a $75/hour facility fee.",
             "procedure", "facilities", "rooms", "rooms,reservations,meetings,booking", 89),

            ("Handling Suspected Child Abuse or Neglect", "Mandated reporter obligations and procedures.",
             "IMPORTANT: Library staff are mandated reporters in our state.\n\nSigns to Watch For:\n- Unexplained injuries or bruises\n- Child is frequently unsupervised or abandoned at the library\n- Child appears malnourished, unwashed, or inappropriately dressed for weather\n- Child expresses fear of going home\n- Child displays age-inappropriate sexual knowledge\n\nWhat to Do:\n1. Do NOT investigate or interrogate the child.\n2. Document what you observed — factual observations only, no opinions.\n3. Report immediately to your supervisor.\n4. Call the Child Abuse Hotline: 1-800-XXX-XXXX\n5. Provide: child's name (if known), age, description, what you observed.\n6. You are protected by law from liability for good-faith reports.\n7. Do NOT confront the parent or caregiver.\n8. Do NOT discuss the report with other staff unless directly involved.\n\nAfter Reporting:\n- File a written report within 48 hours.\n- Cooperate with any investigation by child protective services.\n- Keep all documentation confidential.\n\nRemember: You are not responsible for determining if abuse is occurring. You are responsible for reporting your concerns.",
             "procedure", "safety", "child-safety", "child-safety,mandated-reporter,abuse,neglect", 54),

            ("Patron Privacy and Confidentiality", "Staff obligations regarding patron data protection.",
             "Patron Privacy Obligations:\n\nWhat is Confidential:\n- Circulation records (what a patron has checked out, holds, history)\n- Computer use records (sites visited, search history)\n- Reference transaction records (questions asked)\n- Program registration and attendance\n- Patron contact information and demographics\n\nKey Rules:\n1. Never share patron records with anyone other than the patron themselves.\n2. Parents/guardians may access their minor child's record ONLY.\n3. Spouses, partners, or other family members have NO right to access records.\n4. Law enforcement requests require a valid court order — contact the Director immediately.\n5. Do not leave patron records visible on screens when stepping away.\n6. Shred all printed patron information after use.\n7. Do not discuss patron activities or reading habits with other staff casually.\n\nSocial Media:\n- Never photograph patrons without written consent.\n- Never post about specific patrons on library social media.\n- Event photos: use the opt-out sign and respect anyone who does not want to be photographed.\n\nBreach Response:\nIf you suspect a data breach, notify the IT department and Director within 1 hour.",
             "reference", "privacy", None, "privacy,confidentiality,CIPA,data-protection", 143),

            ("Closing Procedures Checklist", "End-of-day tasks for closing the library building.",
             "Closing Checklist (30 minutes before close):\n\n1. Make a closing announcement at 30 minutes, 15 minutes, and 5 minutes before close.\n2. Begin patron sweep — politely remind patrons of closing time.\n3. Check all study rooms, restrooms, and hidden corners.\n4. Process any remaining returns in the book drop.\n\nAt Closing Time:\n5. Lock all exterior doors.\n6. Run the end-of-day circulation report.\n7. Count the cash drawer and complete the cash drawer reconciliation form.\n8. Secure the cash drawer in the safe.\n9. Shut down all public computers (they will reimage overnight via DeepFreeze).\n10. Turn off lights in public areas (leave security lighting on).\n11. Set the alarm system (code is posted in the staff break room).\n12. Do a final walk-through of the building.\n13. Exit through the staff door and ensure it locks behind you.\n14. Leave any notes for the opening staff on the communication board.\n\nWeekend Closing (additional):\n- Lower all window blinds.\n- Verify the book drop is accessible from outside.\n- Double-check the HVAC is set to weekend mode.",
             "procedure", "circulation", "closing", "closing,checklist,daily,security", 176),

            ("Accessible Services Overview", "Accommodations and resources for patrons with disabilities.",
             "Accessible Services Available:\n\nPhysical Access:\n- Wheelchair-accessible entrances, restrooms, and aisles.\n- Adjustable-height circulation desk and computer stations.\n- Elevator access to all floors.\n- Automatic door openers at main entrance.\n\nVisual Impairments:\n- Large print collection (over 2,000 titles).\n- CCTV magnifier available at the reference desk.\n- Screen reader software (JAWS) on two designated workstations.\n- Talking book players available for checkout (BARD partnership).\n- High-contrast signage throughout the building.\n\nHearing Impairments:\n- Assistive listening devices available for programs.\n- Video relay service (VRS) phone at the circulation desk.\n- Closed-captioned DVDs labeled in the catalog.\n- Written communication always available at all service points.\n\nCognitive/Neurodivergent:\n- Quiet study rooms available without reservation.\n- Noise-canceling headphones for checkout.\n- Visual schedule boards in the children's area.\n- Sensory-friendly storytime offered monthly.\n- Fidget tools available at the children's desk.\n\nHomebound Services:\n- Free home delivery for patrons unable to visit.\n- Monthly delivery schedule — contact outreach coordinator.\n- Materials selected based on patron preferences.",
             "reference", "patron_services", "accessibility", "accessibility,ADA,accommodations,disability", 91),

            ("Volunteer Training Orientation Guide", "Onboarding packet content for new library volunteers.",
             "New Volunteer Orientation Agenda (2 hours):\n\n1. Welcome and Introductions (15 min)\n- Staff contacts and who to ask for help.\n- Tour of the building including staff-only areas.\n\n2. Library Mission and Values (15 min)\n- We serve everyone equally.\n- Intellectual freedom and privacy.\n- Community as our core purpose.\n\n3. Policies and Expectations (20 min)\n- Dress code: business casual.\n- Attendance: notify supervisor if you cannot make your shift.\n- Confidentiality: patron information is private.\n- Cell phone use: personal calls on break only.\n\n4. Hands-On Training (45 min)\n- Shelving: Dewey Decimal system overview.\n- Materials handling: how to check spine labels and sort.\n- Basic patron interactions: directing to service desks.\n\n5. Safety and Emergency (15 min)\n- Fire exits and assembly point.\n- Active threat protocol overview.\n- First aid kit locations.\n\n6. Questions and Paperwork (10 min)\n- Sign volunteer agreement.\n- Submit emergency contact form.\n- Receive volunteer ID badge.\n\nVolunteers log hours using the sign-in binder at the staff desk. Hours are reported monthly.",
             "guide", "human_resources", "volunteers", "volunteers,training,orientation,onboarding", 38),

            ("Weeding the Collection: MUSTIE Criteria", "When and how to remove outdated materials.",
             "MUSTIE Criteria for Weeding:\n\nM — Misleading: Factually inaccurate or obsolete information.\n    Example: Medical books more than 5 years old, travel guides more than 3 years old.\n\nU — Ugly: Worn, damaged, stained, or unattractive.\n    Torn covers, broken spines, water damage, heavy highlighting.\n\nS — Superseded: A newer edition is available.\n    Always check if we own the newer edition before discarding.\n\nT — Trivial: Of no discernible literary or scientific merit.\n    Community interest has waned; no checkouts in 3+ years.\n\nI — Irrelevant: Not related to the community's needs or interests.\n    Topics no longer relevant to our service area demographics.\n\nE — Elsewhere: Available through ILL or digital resources.\n    If we can easily get it from another library, we may not need to own it.\n\nWeeding Process:\n1. Pull items meeting MUSTIE criteria.\n2. Check circulation history — if checked out in the past year, reconsider.\n3. Place on a review cart for supervisor approval.\n4. Approved items go to the Friends of the Library book sale.\n5. Update the catalog record (withdraw/discard).\n6. Log all weeded items in the annual weeding report.",
             "reference", "collection_development", "weeding", "weeding,MUSTIE,deselection,collection-maintenance", 67),

            ("Digital Resources: Database Access Guide", "How to help patrons access library databases remotely.",
             "Database Access for Patrons:\n\nIn-Library Access:\n- All databases are accessible from any library computer without login.\n- Look for the 'Databases' link on the library website homepage.\n- Some databases auto-authenticate by IP address.\n\nRemote Access:\n- Patrons need their library card number and PIN.\n- Direct them to: library website > Resources > Databases.\n- Click the database name, then enter credentials when prompted.\n- If a patron forgot their PIN, reset it at the circulation desk.\n\nPopular Databases:\n- Consumer Reports: Product reviews and ratings.\n- Ancestry Library Edition: In-library use only (licensing restriction).\n- Mango Languages: Language learning (also has a mobile app).\n- LinkedIn Learning: Professional development courses.\n- Palace Project: Ebooks and audiobooks.\n- Newspapers: New York Times, Wall Street Journal (via ProQuest).\n\nTroubleshooting:\n- 'Access Denied': Verify card is active and not expired.\n- 'Too many users': Some databases have concurrent user limits — try again later.\n- Mobile issues: Some databases require the library's EZProxy URL — check the remote access guide.",
             "guide", "technology", "databases", "databases,remote-access,EZProxy,digital-resources", 124),
        ]

        for title, desc, content, content_type, category, subcategory, tags, views in articles:
            await session.execute(text("""
                INSERT INTO staff_knowledge_articles
                    (title, description, content, content_type, category, subcategory, tags,
                     is_published, current_version, created_by_id, created_at, updated_at,
                     view_count, bookmark_count, helpful_count, unhelpful_count)
                VALUES (:title, :desc, :content, :ctype, :cat, :subcat, :tags,
                        true, 1, :author, :created, :created,
                        :views, :bookmarks, :helpful, :unhelpful)
            """), {
                "title": title, "desc": desc, "content": content,
                "ctype": content_type, "cat": category, "subcat": subcategory,
                "tags": tags, "author": random.choice(staff_ids),
                "created": _past(random.randint(30, 500)),
                "views": views, "bookmarks": random.randint(0, views // 3),
                "helpful": random.randint(5, views // 2),
                "unhelpful": random.randint(0, 5),
            })
        print(f"    Created {len(articles)} knowledge articles")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 2. DECISION TREES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM decision_trees"))
    if r.scalar() == 0:
        print("  Seeding decision_trees...")
        trees = [
            ("Patron Wants to Dispute a Fine", "Guide staff through the fine dispute resolution process.",
             "circulation",
             {
                 "start": "q1",
                 "nodes": {
                     "q1": {"type": "question", "text": "Is the fine amount correct in the system?",
                            "options": [
                                {"label": "Yes, amount is correct", "next": "q2"},
                                {"label": "No, system error found", "next": "a1"}
                            ]},
                     "q2": {"type": "question", "text": "Does the patron have a valid reason (illness, weather emergency, etc.)?",
                            "options": [
                                {"label": "Yes, documented hardship", "next": "a2"},
                                {"label": "Patron disagrees but no special circumstance", "next": "q3"}
                            ]},
                     "q3": {"type": "question", "text": "Is this the patron's first fine dispute?",
                            "options": [
                                {"label": "Yes, first time", "next": "a3"},
                                {"label": "No, repeat dispute", "next": "a4"}
                            ]},
                     "a1": {"type": "answer", "text": "Correct the system error and waive the fine. Document the error in the incident log. Apologize to the patron."},
                     "a2": {"type": "answer", "text": "Waive the fine per hardship policy. Note the reason in the patron record. Offer a courtesy renewal if applicable."},
                     "a3": {"type": "answer", "text": "Offer a one-time courtesy waiver of up to $5.00. Explain the fine policy for future reference. If over $5.00, escalate to supervisor."},
                     "a4": {"type": "answer", "text": "Politely explain that the fine is valid and offer a payment plan if the amount is over $10. Direct to the branch manager if the patron insists."}
                 }
             }),

            ("Handling a Noise Complaint", "Decision guide for addressing noise issues in the library.",
             "patron_services",
             {
                 "start": "q1",
                 "nodes": {
                     "q1": {"type": "question", "text": "Where is the noise coming from?",
                            "options": [
                                {"label": "Quiet zone / study area", "next": "q2"},
                                {"label": "General area / children's section", "next": "q3"},
                                {"label": "Meeting room / program space", "next": "a1"}
                            ]},
                     "q2": {"type": "question", "text": "What type of noise?",
                            "options": [
                                {"label": "Conversation / phone call", "next": "a2"},
                                {"label": "Electronic device without headphones", "next": "a3"},
                                {"label": "Disruptive behavior (yelling, banging)", "next": "a4"}
                            ]},
                     "q3": {"type": "question", "text": "Is the noise level above what's reasonable for that area?",
                            "options": [
                                {"label": "Yes, excessively loud", "next": "a5"},
                                {"label": "No, within normal range", "next": "a6"}
                            ]},
                     "a1": {"type": "answer", "text": "Check if the room is reserved and a program is in session. If so, explain to the complainant that the room is in scheduled use. Offer earplugs or suggest a quieter area."},
                     "a2": {"type": "answer", "text": "Approach the person calmly and say: 'I'm sorry, this is a designated quiet area. Could you please take your conversation to the lobby or a study room?' Offer a study room if available."},
                     "a3": {"type": "answer", "text": "Offer the patron headphones from the circulation desk (free to borrow with library card). If they refuse, ask them to mute the device or move to a general area."},
                     "a4": {"type": "answer", "text": "This is a Code of Conduct issue. Give a verbal warning first. If behavior continues, involve the branch manager. Third occurrence: ask the patron to leave for the day. Document in the incident log."},
                     "a5": {"type": "answer", "text": "Politely ask the group or individual to lower the volume. Suggest they move to a meeting room for group work. If children, engage them in a quieter activity or direct them to the play area."},
                     "a6": {"type": "answer", "text": "Explain to the complainant that some conversational noise is expected in general areas. Offer earplugs or suggest a quiet study room for their use."}
                 }
             }),

            ("Processing an ILL Request", "Step-by-step decision tree for interlibrary loan requests.",
             "circulation",
             {
                 "start": "q1",
                 "nodes": {
                     "q1": {"type": "question", "text": "Is the item available in our catalog or consortium?",
                            "options": [
                                {"label": "Yes, available locally", "next": "a1"},
                                {"label": "No, not in consortium", "next": "q2"}
                            ]},
                     "q2": {"type": "question", "text": "Is the item available in OCLC WorldCat?",
                            "options": [
                                {"label": "Yes, found in WorldCat", "next": "q3"},
                                {"label": "No, not found anywhere", "next": "a2"}
                            ]},
                     "q3": {"type": "question", "text": "Is there a lending fee from the supplying library?",
                            "options": [
                                {"label": "No fee or under $10", "next": "a3"},
                                {"label": "Fee over $10", "next": "a4"}
                            ]},
                     "a1": {"type": "answer", "text": "Place a hold through the consortium system instead of ILL. The item should arrive within 3-5 business days. Notify the patron of the expected arrival."},
                     "a2": {"type": "answer", "text": "Inform the patron the item cannot be located through ILL. Suggest alternatives: purchase request, digital version, or similar titles in our collection."},
                     "a3": {"type": "answer", "text": "Submit the ILL request through ILLiad. Select up to 5 lending libraries. Notify the patron of the 7-14 day expected turnaround. No charge to the patron."},
                     "a4": {"type": "answer", "text": "Contact the patron before submitting. Explain the fee and ask if they wish to proceed. If yes, submit with fee authorization. If no, search for alternative sources."}
                 }
             }),

            ("When to Call Security", "Guide for determining when to escalate to security or law enforcement.",
             "safety",
             {
                 "start": "q1",
                 "nodes": {
                     "q1": {"type": "question", "text": "Is anyone in immediate physical danger?",
                            "options": [
                                {"label": "Yes, immediate danger", "next": "a1"},
                                {"label": "No immediate danger", "next": "q2"}
                            ]},
                     "q2": {"type": "question", "text": "What is the situation?",
                            "options": [
                                {"label": "Verbal threat or aggressive behavior", "next": "q3"},
                                {"label": "Theft or property damage", "next": "a2"},
                                {"label": "Intoxication or substance use", "next": "a3"},
                                {"label": "Unattended child / vulnerable person", "next": "a4"}
                            ]},
                     "q3": {"type": "question", "text": "Has the person been given a verbal warning?",
                            "options": [
                                {"label": "Yes, warning was ignored", "next": "a5"},
                                {"label": "No, not yet warned", "next": "a6"}
                            ]},
                     "a1": {"type": "answer", "text": "CALL 911 IMMEDIATELY. Do not attempt to intervene physically. Clear patrons from the area. Use the staff panic button if available. Document everything after the situation is resolved."},
                     "a2": {"type": "answer", "text": "Call security. Do not confront the person directly. Note a physical description and direction of travel. Secure any evidence. File a police report if the value exceeds $50."},
                     "a3": {"type": "answer", "text": "Approach with caution and a partner. If the person is calm, offer water and suggest they rest in a quiet area. If disruptive, call security. If unconscious or in medical distress, call 911."},
                     "a4": {"type": "answer", "text": "Attempt to locate the parent/guardian in the building (page them). If the child is under 10 and alone for more than 30 minutes, contact the police non-emergency line. Document in the incident log."},
                     "a5": {"type": "answer", "text": "Call security to remove the person. If security is not available, call the police non-emergency line. Issue a trespass warning if the person has been warned 3 times previously. Document everything."},
                     "a6": {"type": "answer", "text": "Give a calm, firm verbal warning: 'Your behavior is making others uncomfortable. Please stop or I will need to ask you to leave.' Document the warning. If behavior continues, proceed with security call."}
                 }
             }),

            ("Lost Library Card Procedure", "How to handle a patron who has lost their library card.",
             "circulation",
             {
                 "start": "q1",
                 "nodes": {
                     "q1": {"type": "question", "text": "Can the patron verify their identity?",
                            "options": [
                                {"label": "Yes, has photo ID", "next": "q2"},
                                {"label": "No ID available", "next": "a1"}
                            ]},
                     "q2": {"type": "question", "text": "Is the patron's account in good standing?",
                            "options": [
                                {"label": "Yes, account is clear", "next": "a2"},
                                {"label": "Account has blocks or fines", "next": "q3"}
                            ]},
                     "q3": {"type": "question", "text": "What type of block?",
                            "options": [
                                {"label": "Overdue fines only", "next": "a3"},
                                {"label": "Suspended or restricted account", "next": "a4"}
                            ]},
                     "a1": {"type": "answer", "text": "Cannot issue a replacement without identity verification. Offer a temporary day pass for in-library use. Ask patron to return with a photo ID to get a replacement card."},
                     "a2": {"type": "answer", "text": "Deactivate the old card number. Issue a new card and charge the $2.00 replacement fee. Update the card number in the patron record. Remind patron they can add the card to the mobile app."},
                     "a3": {"type": "answer", "text": "Issue the replacement card ($2.00 fee). Inform patron of outstanding fines and offer payment options. The fine does not prevent card replacement."},
                     "a4": {"type": "answer", "text": "Explain the account restriction. Refer to a supervisor to review the block. The supervisor can lift the restriction if appropriate before issuing a replacement card."}
                 }
             }),

            ("Patron Requesting Material Reconsideration", "How to handle challenges to library materials.",
             "collection",
             {
                 "start": "q1",
                 "nodes": {
                     "q1": {"type": "question", "text": "Has the patron read or viewed the material in question?",
                            "options": [
                                {"label": "Yes, they have engaged with it", "next": "q2"},
                                {"label": "No, objecting based on secondhand info", "next": "a1"}
                            ]},
                     "q2": {"type": "question", "text": "Does the patron want to formally challenge the material?",
                            "options": [
                                {"label": "Yes, formal challenge", "next": "a2"},
                                {"label": "No, just expressing concern", "next": "a3"}
                            ]},
                     "a1": {"type": "answer", "text": "Thank the patron for their concern. Encourage them to review the material themselves. Explain our selection policy. Offer the Request for Reconsideration form if they still wish to proceed after reviewing."},
                     "a2": {"type": "answer", "text": "Provide the official Request for Reconsideration form. Explain the review process: the form goes to the Collection Development Committee, who will review within 30 days. The material remains in circulation during review. The patron will receive a written response."},
                     "a3": {"type": "answer", "text": "Listen respectfully. Explain the library's mission to provide diverse perspectives. Note that the presence of an item does not equal endorsement. Thank them for sharing their viewpoint. Document the conversation in the feedback log."}
                 }
             }),
        ]

        for title, desc, category, tree_data in trees:
            await session.execute(text("""
                INSERT INTO decision_trees (title, description, category, tree_data, is_published,
                    created_by_id, view_count, created_at, updated_at)
                VALUES (:title, :desc, :cat, cast(:tree as json), true,
                    :author, :views, :created, :created)
            """), {
                "title": title, "desc": desc, "cat": category,
                "tree": json.dumps(tree_data),
                "author": random.choice(staff_ids),
                "views": random.randint(15, 120),
                "created": _past(random.randint(30, 400)),
            })
        print(f"    Created {len(trees)} decision trees")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 3. EXECUTIVE DASHBOARDS + DASHBOARD WIDGETS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM executive_dashboards"))
    if r.scalar() == 0 and plan_id is not None:
        print("  Seeding executive_dashboards & dashboard_widgets...")

        dashboards_data = [
            ("Circulation Overview", "Real-time circulation metrics and trends for all branches.",
             "operational", "staff", True, 5,
             [
                 ("Total Checkouts Today", "kpi_card", "metric", '{"metric": "checkouts_today", "icon": "book-open", "color": "blue"}', 0, 0, 3, 2),
                 ("Active Holds", "kpi_card", "metric", '{"metric": "active_holds", "icon": "clock", "color": "amber"}', 3, 0, 3, 2),
                 ("Overdue Items", "kpi_card", "metric", '{"metric": "overdue_count", "icon": "alert-triangle", "color": "red"}', 6, 0, 3, 2),
                 ("Items in Transit", "kpi_card", "metric", '{"metric": "in_transit", "icon": "truck", "color": "green"}', 9, 0, 3, 2),
                 ("Weekly Circulation Trend", "line_chart", "timeseries", '{"metric": "weekly_checkouts", "period": "12_weeks"}', 0, 2, 6, 4),
                 ("Checkouts by Format", "pie_chart", "breakdown", '{"metric": "format_distribution", "period": "current_month"}', 6, 2, 6, 4),
             ]),
            ("Program Attendance", "Event and program attendance tracking dashboard.",
             "operational", "staff", True, 10,
             [
                 ("Total Programs This Month", "kpi_card", "metric", '{"metric": "programs_count", "icon": "calendar", "color": "purple"}', 0, 0, 4, 2),
                 ("Total Attendance This Month", "kpi_card", "metric", '{"metric": "total_attendance", "icon": "users", "color": "blue"}', 4, 0, 4, 2),
                 ("Average Attendance per Event", "kpi_card", "metric", '{"metric": "avg_attendance", "icon": "bar-chart", "color": "green"}', 8, 0, 4, 2),
                 ("Attendance by Program Type", "bar_chart", "breakdown", '{"metric": "attendance_by_type", "period": "current_quarter"}', 0, 2, 6, 4),
                 ("Monthly Trend", "line_chart", "timeseries", '{"metric": "monthly_attendance", "period": "12_months"}', 6, 2, 6, 4),
             ]),
            ("Budget Status", "Financial overview for the current fiscal year.",
             "financial", "director", False, 30,
             [
                 ("YTD Expenditures", "kpi_card", "metric", '{"metric": "ytd_expenditures", "icon": "dollar-sign", "color": "green", "format": "currency"}', 0, 0, 4, 2),
                 ("Budget Remaining", "kpi_card", "metric", '{"metric": "budget_remaining", "icon": "wallet", "color": "blue", "format": "currency"}', 4, 0, 4, 2),
                 ("Revenue Collected", "kpi_card", "metric", '{"metric": "revenue_collected", "icon": "trending-up", "color": "emerald", "format": "currency"}', 8, 0, 4, 2),
                 ("Spending by Category", "donut_chart", "breakdown", '{"metric": "spending_by_category", "period": "fiscal_year"}', 0, 2, 6, 4),
                 ("Monthly Budget Burn Rate", "line_chart", "timeseries", '{"metric": "monthly_spend", "period": "fiscal_year", "show_target": true}', 6, 2, 6, 4),
             ]),
            ("Staff Scheduling Overview", "Staff coverage and scheduling metrics.",
             "operational", "admin", False, 15,
             [
                 ("Staff on Duty Today", "kpi_card", "metric", '{"metric": "staff_on_duty", "icon": "user-check", "color": "green"}', 0, 0, 4, 2),
                 ("Open Shifts This Week", "kpi_card", "metric", '{"metric": "open_shifts", "icon": "alert-circle", "color": "amber"}', 4, 0, 4, 2),
                 ("PTO Requests Pending", "kpi_card", "metric", '{"metric": "pto_pending", "icon": "calendar-off", "color": "red"}', 8, 0, 4, 2),
                 ("Weekly Coverage by Branch", "stacked_bar", "breakdown", '{"metric": "branch_coverage", "period": "current_week"}', 0, 2, 12, 4),
             ]),
        ]

        for name, desc, dtype, audience, is_default, refresh, widgets in dashboards_data:
            dr = await session.execute(text("""
                INSERT INTO executive_dashboards
                    (plan_id, name, description, dashboard_type, audience, is_default,
                     auto_refresh, refresh_interval_minutes, created_by_id)
                VALUES (:plan_id, :name, :desc, :dtype, :audience, :default,
                        true, :refresh, :creator)
                RETURNING id
            """), {
                "plan_id": plan_id, "name": name, "desc": desc, "dtype": dtype,
                "audience": audience, "default": is_default, "refresh": refresh,
                "creator": random.choice(staff_ids),
            })
            dash_id = dr.scalar()

            for i, (wtitle, wtype, dstype, config, px, py, w, h) in enumerate(widgets):
                await session.execute(text("""
                    INSERT INTO dashboard_widgets
                        (dashboard_id, title, widget_type, data_source_type, config,
                         position_x, position_y, width, height, display_order, is_visible)
                    VALUES (:dash_id, :title, :wtype, :dstype, cast(:config as jsonb),
                            :px, :py, :w, :h, :order, true)
                """), {
                    "dash_id": dash_id, "title": wtitle, "wtype": wtype,
                    "dstype": dstype, "config": config,
                    "px": px, "py": py, "w": w, "h": h, "order": i + 1,
                })

        print(f"    Created {len(dashboards_data)} dashboards with widgets")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 4. EXECUTIVE REPORTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM executive_reports"))
    if r.scalar() == 0:
        print("  Seeding executive_reports...")
        reports = [
            ("January 2026 Monthly Report", "monthly",
             "Monthly operations summary for January 2026.",
             datetime(2026, 1, 1, tzinfo=utc), datetime(2026, 1, 31, 23, 59, 59, tzinfo=utc),
             "January saw strong circulation numbers despite winter weather closures on three days. Digital checkouts exceeded physical for the first time in a single month. The new self-checkout kiosks processed 42% of all transactions.",
             '[{"title": "Circulation up 8% year-over-year", "detail": "Total checkouts: 14,872 vs 13,771 in Jan 2025"}, {"title": "Digital checkouts surpassed physical", "detail": "7,621 digital vs 7,251 physical"}]',
             '[{"title": "Expand digital collection budget by 10%", "priority": "high"}, {"title": "Schedule self-checkout training for remaining staff", "priority": "medium"}]',
             '{"total_checkouts": 14872, "new_cards": 187, "program_attendance": 1243, "door_count": 22456}',
             "published", 35),

            ("February 2026 Monthly Report", "monthly",
             "Monthly operations summary for February 2026.",
             datetime(2026, 2, 1, tzinfo=utc), datetime(2026, 2, 28, 23, 59, 59, tzinfo=utc),
             "February was marked by the successful launch of the Seed Library and strong programming attendance. Black History Month displays and events drew record numbers. Two staff members completed their MLS degrees.",
             '[{"title": "Seed Library launched with 200+ varieties", "detail": "87 patron sign-ups in the first two weeks"}, {"title": "Black History Month programs exceeded capacity", "detail": "Three events required waitlists"}]',
             '[{"title": "Consider expanding Seed Library space", "priority": "medium"}, {"title": "Plan for larger venue for popular cultural programs", "priority": "high"}]',
             '{"total_checkouts": 13456, "new_cards": 162, "program_attendance": 1567, "door_count": 20189}',
             "published", 28),

            ("Q4 2025 Quarterly Review", "quarterly",
             "Fourth quarter 2025 performance review.",
             datetime(2025, 10, 1, tzinfo=utc), datetime(2025, 12, 31, 23, 59, 59, tzinfo=utc),
             "Q4 2025 closed out a strong year with record program attendance and the completion of the main branch renovation. The new teen space opened in November to enthusiastic response. Holiday programming saw a 23% increase in attendance over Q4 2024. Budget ended the year at 97.2% utilization.",
             '[{"title": "Teen space renovation completed on time and under budget", "detail": "Came in $12,400 under the $175,000 budget"}, {"title": "Holiday program attendance up 23%", "detail": "2,834 attendees across 47 programs"}, {"title": "Annual door count exceeded 250,000", "detail": "Final count: 258,923 — a 6% increase over 2024"}]',
             '[{"title": "Begin planning for children area refresh in Q2 2026", "priority": "high"}, {"title": "Evaluate teen space usage after 6 months", "priority": "medium"}, {"title": "Increase outreach to underserved neighborhoods", "priority": "high"}]',
             '{"total_checkouts": 42567, "new_cards": 534, "program_attendance": 4892, "door_count": 67234}',
             "published", 52),

            ("Board Meeting Report — March 2026", "board",
             "Prepared for the March 2026 Board of Trustees meeting.",
             datetime(2026, 2, 1, tzinfo=utc), datetime(2026, 2, 28, 23, 59, 59, tzinfo=utc),
             "Report prepared for the March 12, 2026 Board of Trustees meeting. Covers February operations, budget status, capital projects update, and personnel matters. Key discussion items include the proposed FY2027 budget and the children's area renovation timeline.",
             '[{"title": "FY2026 budget on track at 62% utilization through February", "detail": "Materials budget is 71% spent due to front-loaded ordering"}, {"title": "Three new staff hires completed", "detail": "Two reference librarians and one IT support specialist"}]',
             '[{"title": "Approve FY2027 preliminary budget for public comment period", "priority": "high"}, {"title": "Authorize architectural study for children area renovation", "priority": "high"}, {"title": "Review and approve updated Internet Use Policy", "priority": "medium"}]',
             '{"total_checkouts": 13456, "new_cards": 162, "program_attendance": 1567, "door_count": 20189}',
             "published", 18),

            ("Annual Report 2025", "annual",
             "Comprehensive annual report for fiscal year 2025.",
             datetime(2025, 1, 1, tzinfo=utc), datetime(2025, 12, 31, 23, 59, 59, tzinfo=utc),
             "Fiscal Year 2025 was a year of growth and transformation. The library served over 258,000 visitors, circulated 168,000 items, and hosted 412 programs attended by 18,500 community members. Key accomplishments include the teen space renovation, launch of the mobile hotspot lending program, and a 15% increase in digital resource usage.",
             '[{"title": "Record annual door count: 258,923", "detail": "6% increase over FY2024"}, {"title": "168,234 items circulated", "detail": "3% increase, driven by audiobook and ebook growth"}, {"title": "412 programs hosted with 18,500 attendees", "detail": "New record for both metrics"}]',
             '[{"title": "Continue digital collection expansion", "priority": "high"}, {"title": "Pursue LSTA grant for literacy programming", "priority": "high"}, {"title": "Implement new ILS system (RFP in Q2)", "priority": "medium"}, {"title": "Launch community needs assessment survey", "priority": "medium"}]',
             '{"total_checkouts": 168234, "new_cards": 2156, "program_attendance": 18500, "door_count": 258923}',
             "published", 89),

            ("State Library Annual Report 2025", "state",
             "Statistical report submitted to the State Library for FY2025.",
             datetime(2025, 1, 1, tzinfo=utc), datetime(2025, 12, 31, 23, 59, 59, tzinfo=utc),
             "Statistical data compiled for the State Library annual survey. Includes all required metrics: collection size, circulation, program statistics, staffing FTE, budget figures, and technology infrastructure details.",
             '[{"title": "Collection size: 89,234 physical + 42,100 digital titles", "detail": "Net growth of 3,200 titles after weeding"}, {"title": "Staffing: 22.5 FTE", "detail": "14 full-time, 17 part-time employees"}]',
             '[]',
             '{"total_checkouts": 168234, "collection_physical": 89234, "collection_digital": 42100, "fte": 22.5, "operating_budget": 2156000}',
             "published", 12),

            ("March 2026 Monthly Report", "monthly",
             "Monthly operations summary for March 2026 (in progress).",
             datetime(2026, 3, 1, tzinfo=utc), datetime(2026, 3, 31, 23, 59, 59, tzinfo=utc),
             "March report is being compiled. Preliminary numbers show strong spring break programming attendance and the beginning of the Summer Reading planning cycle.",
             '[]',
             '[]',
             None,
             "draft", 3),

            ("Strategic Plan Progress — Mid-Year 2025", "strategic",
             "Mid-year progress report on the 2024-2027 Strategic Plan.",
             datetime(2025, 1, 1, tzinfo=utc), datetime(2025, 6, 30, 23, 59, 59, tzinfo=utc),
             "The library is on track to meet 78% of Year 2 strategic plan goals. Notable progress in Goal 1 (Community Engagement) with new outreach partnerships. Goal 3 (Digital Transformation) is ahead of schedule with the early launch of the mobile app. Goal 2 (Lifelong Learning) needs attention — adult literacy program enrollment is below target.",
             '[{"title": "78% of Year 2 goals on track or completed", "detail": "32 of 41 action items in progress or done"}, {"title": "Mobile app launched 3 months ahead of schedule", "detail": "1,200 downloads in first month"}, {"title": "Adult literacy enrollment at 60% of target", "detail": "Need targeted outreach to increase enrollment"}]',
             '[{"title": "Increase adult literacy marketing budget", "priority": "high"}, {"title": "Partner with workforce development agency for referrals", "priority": "high"}, {"title": "Begin Year 3 action item planning in Q3", "priority": "medium"}]',
             '{"goals_on_track": 32, "goals_total": 41, "completion_percentage": 78}',
             "published", 41),
        ]

        for title, rtype, desc, pstart, pend, summary, findings, recs, kpi_json, status, views in reports:
            await session.execute(text("""
                INSERT INTO executive_reports
                    (title, report_type, description, period_start, period_end,
                     executive_summary, key_findings, recommendations, kpi_snapshot,
                     status, published_date, created_by_id, approved_by_id)
                VALUES (:title, :rtype, :desc, :pstart, :pend,
                        :summary, cast(:findings as jsonb), cast(:recs as jsonb),
                        cast(:kpi as jsonb),
                        :status, :pub_date, :creator, :approver)
            """), {
                "title": title, "rtype": rtype, "desc": desc,
                "pstart": pstart, "pend": pend, "summary": summary,
                "findings": findings, "recs": recs,
                "kpi": kpi_json,
                "status": status,
                "pub_date": pend + timedelta(days=random.randint(3, 10)) if status == "published" else None,
                "creator": random.choice(staff_ids),
                "approver": random.choice(staff_ids) if status == "published" else None,
            })
        print(f"    Created {len(reports)} executive reports")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 5. IMPACT STORIES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM impact_stories"))
    if r.scalar() == 0:
        print("  Seeding impact_stories...")
        stories = [
            ("How the ESL Program Changed Maria's Life",
             "A newcomer's journey from isolation to community leadership through library ESL classes.",
             "When Maria arrived in our community three years ago, she spoke almost no English and felt completely isolated. A neighbor told her about the library's free ESL conversation circles, and she decided to try.\n\n'I was so nervous the first day,' Maria recalls. 'But the volunteers were so patient. They made me feel welcome even when I could barely say hello.'\n\nMaria attended twice a week for two years. She progressed from beginner to advanced level, and along the way she made friends, learned about community resources, and gained confidence.\n\nToday, Maria works as a bilingual receptionist at a local medical clinic. She volunteers at the library's ESL program, helping new arrivals the same way she was helped.\n\n'The library gave me my voice back,' she says. 'Now I help others find theirs.'",
             "Maria (name changed)", None, "participant",
             "published", True, False, "en",
             '{"ESL","immigration","workforce","community"}',
             "ESL Conversation Circle", 3, 2450,
             "Sarah Chen", "Powerful story. Good for annual report."),

            ("Teen Maker Builds Award-Winning Robot",
             "A high school student's makerspace journey leads to a regional robotics competition win.",
             "Jayden had always been interested in engineering but had no access to tools or materials at home. When the library opened its makerspace two years ago, everything changed.\n\nStarting with basic 3D printing, Jayden quickly progressed to electronics and Arduino programming. Library staff mentored him through increasingly complex projects.\n\nHis robot, built entirely at the library makerspace over four months, won second place at the Regional Youth Robotics Challenge. He was the only competitor who built his robot at a public library.\n\n'Without the library, I never would have had access to a 3D printer or learned to solder,' Jayden told the local newspaper. 'The staff here believed in me before I believed in myself.'\n\nJayden is now applying to engineering programs at several universities, with a strong portfolio of projects built at the library.",
             "Jayden T.", None, "participant",
             "published", True, True, "en",
             '{"STEM","youth","makerspace","education"}',
             "Teen Makerspace", None, 3200,
             "David Ortiz", "Great for makerspace funding requests."),

            ("Homebound Patron Reads 100th Book",
             "Library home delivery service keeps a lifelong reader connected to the world of books.",
             "Dorothy has been a library patron for over 40 years. When a fall left her unable to visit the library two years ago, she feared she would never read a new book again.\n\nThen she learned about the library's Homebound Delivery Service. Every month, a library volunteer brings Dorothy a carefully curated selection of books based on her preferences.\n\n'They know exactly what I like,' Dorothy says with a smile. 'Mysteries with strong women and historical fiction set in England. They never disappoint.'\n\nLast month, Dorothy celebrated a milestone: her 100th book through the homebound program. Library staff delivered a small cake and a certificate to mark the occasion.\n\n'Books are my window to the world now that I can't get out much. The library hasn't just given me books — they've given me a reason to look forward to each day.'",
             "Dorothy M.", None, "participant",
             "published", True, False, "en",
             '{"homebound","seniors","outreach","reading"}',
             "Homebound Delivery Service", None, 1890,
             "Angela Brooks", "Perfect for outreach program promotion."),

            ("Job Seeker Lands Career After Library Workshop",
             "A laid-off factory worker rebuilds his career using library resources.",
             "After 18 years at the manufacturing plant, Carlos found himself unemployed when the factory closed. At 52, he felt too old to start over and too young to retire.\n\nA friend suggested the library's Job Search and Career Resources workshop. Carlos was skeptical but desperate.\n\n'I didn't even know how to write a modern resume,' Carlos admits. 'The last time I applied for a job, you mailed a paper application.'\n\nOver three months, Carlos attended resume workshops, practiced interview skills, and used the library's computers to apply for positions. Staff helped him create a LinkedIn profile and navigate online job portals.\n\nCarlos now works as a maintenance supervisor at a regional hospital. His salary is higher than his factory wage.\n\n'The library didn't just help me find a job. They helped me find my confidence again. I tell everyone — if you need help, go to the library first.'",
             "Carlos R.", None, "participant",
             "published", True, False, "en",
             '{"workforce","career","digital-literacy","adults"}',
             "Job Search and Career Resources", None, 2100,
             "Tom Richards", "Strong story for workforce development grants."),

            ("Summer Reading Sparks a Lifelong Love of Books",
             "A reluctant reader discovers the joy of stories through the Summer Reading Challenge.",
             "Eight-year-old Aisha did not like reading. Her mother enrolled her in the Summer Reading Challenge hoping it would help, but expectations were low.\n\n'She would throw fits about reading at home,' her mother recalls. 'I was at my wit's end.'\n\nThe gamification elements of the program — earning badges, tracking progress, and choosing prizes — gave Aisha the motivation she needed. The children's librarian helped her find graphic novels and books about animals, which turned out to be perfect.\n\nBy the end of summer, Aisha had read 32 books and earned the top reader award for her age group. More importantly, she asked for a library card of her own.\n\nNow in fourth grade, Aisha visits the library weekly and has started writing her own stories. She recently told her teacher she wants to be an author when she grows up.\n\nHer mother says simply: 'The library changed my daughter.'",
             "Aisha's mother (name withheld)", None, "parent",
             "published", True, True, "en",
             '{"summer-reading","children","literacy","motivation"}',
             "Summer Reading Challenge", None, 4500,
             "Susan Park", "Use for Summer Reading promotion. Great testimonial."),

            ("Citizenship Test Success Through Library Resources",
             "Library study groups help immigrants prepare for and pass the U.S. citizenship exam.",
             "The library's Citizenship Preparation Study Group has helped 47 community members pass their citizenship test over the past two years.\n\nThe weekly sessions, led by a trained volunteer and supported by library staff, cover civics, U.S. history, reading, and writing components of the naturalization test.\n\n'We use practice tests, flashcards, and conversation practice,' explains volunteer tutor Jim Barrett. 'But the real value is the community. People support each other through a stressful process.'\n\nParticipant Nguyen Thi wrote after passing her test: 'I studied in the library for six months. The volunteers and the other students became my family. When I took the oath of citizenship, I thought of them all.'\n\nThe program costs almost nothing to run — just volunteer time and printed study materials — but its impact on individual lives and the community is immeasurable.",
             "Jim Barrett (volunteer tutor)", None, "volunteer",
             "published", True, False, "en",
             '{"citizenship","ESL","immigration","civic-engagement"}',
             "Citizenship Preparation", 5, 1650,
             "Stevie Leigh", "47 successful applicants is a strong data point."),

            ("Seniors Bridge the Digital Divide",
             "Smartphone basics class empowers older adults to connect with family and services.",
             "When the library launched its Smartphone Basics for Seniors class, staff expected a handful of sign-ups. Instead, every session filled to capacity with a waitlist.\n\n'I bought this phone two years ago and it's been sitting in a drawer,' said one participant, a 78-year-old retired teacher. 'My grandchildren kept telling me to text them, but I didn't know how.'\n\nThe six-week course covers everything from making calls and sending texts to using the camera, downloading apps, and accessing telehealth services. Each participant is paired with a teen volunteer for one-on-one help.\n\nThe intergenerational pairing has been an unexpected highlight. 'My teen helper is so patient,' says another participant. 'She reminds me of my granddaughter. We're going to stay in touch after the class ends.'\n\nPost-class surveys show that 89% of participants use their smartphones daily after completing the course, up from 12% before.",
             None, None, "staff",
             "published", False, False, "en",
             '{"digital-literacy","seniors","intergenerational","technology"}',
             "Smartphone Basics for Seniors", None, 1320,
             "David Ortiz", "89% daily usage stat is excellent."),

            ("The Book Club That Became a Support Group",
             "A women's book club transforms into a lifeline for its members.",
             "What started as a casual Thursday evening book club five years ago has become something much deeper for its twelve regular members.\n\nThe group — all women ranging in age from 34 to 72 — reads one book a month, but the discussions often extend far beyond the text. Members have supported each other through divorces, cancer diagnoses, job losses, and the deaths of parents.\n\n'We read the book, sure,' says founding member Rachel. 'But we also share our lives. This group has gotten me through things I couldn't have survived alone.'\n\nThe library provides the space, suggests titles, and occasionally hosts author visits for the group. It's one of the longest-running programs at the branch.\n\n'Libraries are sometimes called the living room of the community,' says the branch librarian. 'This group proves that's more than a metaphor. These women found each other here, and their bond is remarkable.'",
             "Rachel (with permission)", None, "participant",
             "published", True, False, "en",
             '{"book-clubs","community","women","social-connection"}',
             "Adult Book Clubs", None, 980,
             "Angela Brooks", "Speaks to the social value of libraries."),

            ("From GED to College: A Library Success Story",
             "An adult learner completes her GED and enrolls in community college with library support.",
             "Tanya dropped out of high school at 16. For fifteen years, she worked low-wage jobs and struggled to provide for her two children. When she decided to pursue her GED, the library became her classroom.\n\nUsing the library's study rooms, practice test databases, and tutoring referrals, Tanya studied for eight months. Library staff helped her navigate the GED testing process and apply for fee waivers.\n\nShe passed all four subjects on her first attempt.\n\n'The library was the only place I could study in peace,' Tanya says. 'At home there's always noise and distractions. Here, the staff checked on me, encouraged me, and celebrated with me when I passed.'\n\nTanya is now enrolled in the nursing program at the community college. She still studies at the library most evenings.\n\n'I want my kids to see that it's never too late to learn. And I want them to know the library helped make it possible.'",
             "Tanya W.", None, "participant",
             "published", True, False, "en",
             '{"GED","adult-education","literacy","workforce"}',
             "Adult Learning Resources", None, 2780,
             "Sarah Chen", "Ties into literacy and workforce outcomes."),

            ("Therapy Dogs Bring Joy to Young Readers",
             "The Read to a Dog program boosts confidence in struggling young readers.",
             "Every Saturday morning, three certified therapy dogs — Biscuit, Luna, and Maple — visit the children's area for the library's Read to a Dog program.\n\nThe concept is simple: children who struggle with reading can practice by reading aloud to a calm, nonjudgmental audience. The dogs lie quietly while children read at their own pace.\n\n'My son used to cry when he had to read aloud in school,' says one parent. 'But he'll read to Biscuit for 30 minutes straight. He even picks out books during the week to practice for Saturday.'\n\nTeachers from local elementary schools have reported measurable improvements in participating students' reading fluency and confidence.\n\nThe program, run in partnership with the local therapy dog organization, serves about 15 children per session. There is always a waitlist.\n\n'Dogs don't correct your pronunciation,' the children's librarian explains with a smile. 'They just listen. That's exactly what some kids need.'",
             None, None, "staff",
             "published", True, True, "en",
             '{"literacy","children","therapy-dogs","partnerships"}',
             "Read to a Dog", None, 5200,
             "Susan Park", "Always a crowd-pleaser. Great for social media."),
        ]

        for (title, summary, full_story, author_name, author_email, author_role,
             story_status, featured_web, featured_social, lang, themes_literal,
             program, immigrant_yrs, reach, reviewer, review_notes) in stories:
            sql = (
                "INSERT INTO impact_stories"
                "    (title, summary, full_story, author_name, author_email, author_role,"
                "     submitted_date, status, publication_date, featured_on_website,"
                "     featured_on_social_media, language, themes, related_program,"
                "     immigrant_experience_years, consent_to_publish, consent_to_attribute,"
                "     reach_count, reviewer_name, review_date, review_notes,"
                "     created_at, updated_at)"
                " VALUES (:title, :summary, :story, :author_name, :author_email, :author_role,"
                "     :submitted, cast(:story_status as impactstorystatus), :pub_date, :feat_web,"
                f"     :feat_social, :lang, '{themes_literal}'::varchar[], :program,"
                "     :immigrant_yrs, true, :consent_attr,"
                "     :reach, :reviewer, :review_date, :review_notes,"
                "     :created, :created)"
            )
            await session.execute(text(sql), {
                "title": title, "summary": summary, "story": full_story,
                "author_name": author_name, "author_email": author_email,
                "author_role": author_role,
                "submitted": _past_date(random.randint(30, 400)),
                "story_status": story_status,
                "pub_date": _past_date(random.randint(10, 350)) if story_status == "published" else None,
                "feat_web": featured_web, "feat_social": featured_social,
                "lang": lang, "program": program,
                "immigrant_yrs": immigrant_yrs,
                "consent_attr": author_name is not None,
                "reach": reach, "reviewer": reviewer,
                "review_date": _past_date(random.randint(15, 360)),
                "review_notes": review_notes,
                "created": _past(random.randint(30, 400)),
            })
        print(f"    Created {len(stories)} impact stories")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 6. IMPACT METRICS (requires partner_impact_reports)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM impact_metrics"))
    pir_r = await session.execute(text("SELECT COUNT(*) FROM partner_impact_reports"))
    if r.scalar() == 0 and pir_r.scalar() == 0 and partner_ids:
        print("  Seeding partner_impact_reports & impact_metrics...")
        # First create some partner impact reports to satisfy the FK
        pir_data = [
            (partner_ids[0], date(2025, 7, 1), date(2025, 12, 31), 8, 24, 340, 15000.0, 120.0, 45.0, 280, 95,
             "Strong second half with expanded programming reach."),
            (partner_ids[1], date(2025, 7, 1), date(2025, 12, 31), 5, 15, 220, 8500.0, 80.0, 30.0, 190, 65,
             "Steady growth in after-school programming attendance."),
            (partner_ids[2], date(2026, 1, 1), date(2026, 3, 15), 3, 10, 85, 4200.0, 45.0, 15.0, 72, 45,
             "Q1 outreach to senior living communities showing results."),
        ]
        pir_ids = []
        for (pid, pstart, pend, progs, sessions, participants, res_val,
             vol_hrs, staff_hrs, unique_served, underserved, summary) in pir_data:
            pr = await session.execute(text("""
                INSERT INTO partner_impact_reports
                    (partner_id, reporting_period_start, reporting_period_end,
                     programs_delivered, program_sessions, total_participants,
                     resources_shared_value, volunteer_hours, staff_hours_contributed,
                     unique_people_served, underserved_population_served, impact_summary,
                     created_by_id)
                VALUES (:pid, :pstart, :pend, :progs, :sessions, :participants,
                        :res_val, :vol_hrs, :staff_hrs, :unique, :underserved, :summary,
                        :creator)
                RETURNING id
            """), {
                "pid": pid, "pstart": pstart, "pend": pend,
                "progs": progs, "sessions": sessions, "participants": participants,
                "res_val": res_val, "vol_hrs": vol_hrs, "staff_hrs": staff_hrs,
                "unique": unique_served, "underserved": underserved,
                "summary": summary, "creator": random.choice(staff_ids),
            })
            pir_ids.append(pr.scalar())

        # Now insert impact metrics
        metrics = [
            (pir_ids[0], "participants_served", "Total Program Participants", 400.0, 340.0, "people", "Below target due to weather cancellations in November", "attendance_sheets"),
            (pir_ids[0], "hours_contributed", "Volunteer Hours", 150.0, 120.0, "hours", "Strong volunteer retention", "volunteer_logs"),
            (pir_ids[0], "resources_shared", "Materials Distributed", 500.0, 487.0, "items", "Books, pamphlets, and school supplies", "distribution_log"),
            (pir_ids[0], "events_hosted", "Programs Delivered", 10.0, 8.0, "programs", "Two programs postponed to Q1 2026", "event_calendar"),
            (pir_ids[0], "community_reach", "Social Media Impressions", 5000.0, 6200.0, "impressions", "Exceeded target through viral book drive post", "social_analytics"),
            (pir_ids[0], "learning_outcomes", "Students Improving Grades", 30.0, 28.0, "students", "Based on teacher-reported grade improvements", "teacher_surveys"),
            (pir_ids[0], "funding_generated", "Grant Funding Secured", 25000.0, 32000.0, "dollars", "Received unexpected LSTA supplemental grant", "financial_records"),
            (pir_ids[1], "participants_served", "After-School Attendance", 250.0, 220.0, "students", "Consistent weekly attendance averaging 15 students", "sign_in_sheets"),
            (pir_ids[1], "hours_contributed", "Tutor Hours", 100.0, 80.0, "hours", "Two tutors relocated, recruiting replacements", "tutor_logs"),
            (pir_ids[1], "learning_outcomes", "Reading Level Improvements", 20.0, 18.0, "students", "90% of regular attendees improved by at least one level", "assessment_scores"),
            (pir_ids[1], "community_reach", "Family Engagement Events", 4.0, 5.0, "events", "Added extra family literacy night due to demand", "event_records"),
            (pir_ids[1], "awareness_raised", "Newsletter Distribution", 1000.0, 1150.0, "copies", "Distributed through school backpack program", "print_run_records"),
            (pir_ids[2], "participants_served", "Seniors Served", 100.0, 85.0, "people", "On pace for quarterly target", "visit_logs"),
            (pir_ids[2], "hours_contributed", "Staff Outreach Hours", 20.0, 15.0, "hours", "Reduced due to staff vacancy in January", "timesheets"),
            (pir_ids[2], "resources_shared", "Large Print Books Delivered", 200.0, 175.0, "items", "Home delivery to 3 facilities", "delivery_records"),
            (pir_ids[2], "events_hosted", "On-Site Programs", 4.0, 3.0, "programs", "Book discussion, tech help, movie showing", "program_calendar"),
            (pir_ids[2], "community_reach", "Facility Staff Trained", 10.0, 8.0, "staff", "Trained on library card sign-up assistance", "training_log"),
            (pir_ids[2], "learning_outcomes", "Digital Literacy Sessions", 6.0, 4.0, "sessions", "Tablet basics and video calling for seniors", "session_logs"),
        ]

        for report_id, mtype, mname, target, actual, unit, notes, source in metrics:
            await session.execute(text("""
                INSERT INTO impact_metrics
                    (report_id, metric_type, metric_name, target_value, actual_value,
                     unit, notes, data_source)
                VALUES (:rid, cast(:mtype as impactmetrictype), :mname, :target, :actual,
                        :unit, :notes, :source)
            """), {
                "rid": report_id, "mtype": mtype, "mname": mname,
                "target": target, "actual": actual, "unit": unit,
                "notes": notes, "source": source,
            })
        print(f"    Created {len(pir_data)} partner impact reports, {len(metrics)} impact metrics")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 7. COURSE ENROLLMENTS (FK: genealogy_training_courses)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM course_enrollments"))
    if r.scalar() == 0 and gtc_ids and patron_ids:
        print("  Seeding course_enrollments...")
        count = 0
        used = set()
        statuses = ["enrolled", "completed", "completed", "completed", "in_progress", "dropped"]
        for _ in range(30):
            uid = random.choice(patron_ids)
            cid = random.choice(gtc_ids)
            if (uid, cid) in used:
                continue
            used.add((uid, cid))
            status = random.choice(statuses)
            enrolled_at = _past(random.randint(10, 300))
            completion_pct = 100 if status == "completed" else (random.randint(10, 90) if status == "in_progress" else random.randint(0, 30))
            completed_at = enrolled_at + timedelta(days=random.randint(7, 60)) if status == "completed" else None
            attended_at = enrolled_at + timedelta(days=random.randint(1, 5)) if status != "enrolled" else None

            await session.execute(text("""
                INSERT INTO course_enrollments
                    (user_id, course_id, status, completion_percentage, enrolled_at, attended_at, completed_at)
                VALUES (:uid, :cid, :status, :pct, :enrolled, :attended, :completed)
            """), {
                "uid": uid, "cid": cid, "status": status, "pct": completion_pct,
                "enrolled": enrolled_at, "attended": attended_at, "completed": completed_at,
            })
            count += 1
        print(f"    Created {count} course enrollments")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 8. COURSE FEEDBACK (FK: courses, lessons)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM course_feedback"))
    if r.scalar() == 0 and course_ids and patron_ids:
        print("  Seeding course_feedback...")
        feedback_data = [
            ("course_review", 5.0, "Excellent course! The self-paced format worked perfectly for my schedule. I learned so much about using library databases.", "approved"),
            ("course_review", 4.0, "Very helpful content. The videos were clear and easy to follow. Would love more hands-on exercises.", "approved"),
            ("course_review", 5.0, "I had no idea the library offered these kinds of resources. This course opened my eyes to everything available.", "approved"),
            ("course_review", 3.0, "Good overview but some sections felt rushed. The quiz questions were fair. Would recommend a more gradual pace for beginners.", "approved"),
            ("course_review", 4.5, "The genealogy module was fascinating. I've already started building my family tree using the techniques I learned.", "approved"),
            ("course_review", 5.0, "Best free educational resource I've ever used. Better than some paid courses I've taken. Thank you!", "approved"),
            ("course_review", 4.0, "My kids and I went through the library tour course together. Great way to learn about all the services.", "approved"),
            ("course_review", 2.0, "Some of the content felt outdated. The screenshots didn't match the current website. Needs updating.", "approved"),
            ("lesson_feedback", 4.5, "The section on evaluating sources was eye-opening. I wish I'd learned this in school.", "approved"),
            ("course_review", 5.0, "As a senior, I was intimidated by technology courses. This was gentle, patient, and respectful. I can now use my phone!", "approved"),
            ("suggestion", None, "It would be great to have a course on using social media safely. Many of us seniors want to connect with family online.", "pending"),
            ("course_review", 4.0, "The job search course helped me redo my resume and I got three interviews within a week. Highly recommend.", "approved"),
            ("lesson_feedback", 3.5, "The 3D printing lesson was fun but I wish there was more time to practice with the actual printer.", "approved"),
            ("course_review", 5.0, "The privacy and security course should be mandatory for everyone. So many useful tips for staying safe online.", "approved"),
            ("bug_report", None, "The quiz on Lesson 18 wouldn't load on my phone. Worked fine on a library computer though.", "resolved"),
            ("course_review", 4.0, "Clear, well-organized, and at just the right difficulty level. I completed it in two afternoons at the library.", "approved"),
            ("suggestion", None, "Would love a course on basic home repair or gardening. The library's seed collection made me want to learn more.", "pending"),
            ("course_review", 4.5, "The catalog course saved me so much time. I had no idea you could filter by format and availability.", "approved"),
        ]

        for ftype, rating, comment, status in feedback_data:
            cid = random.choice(course_ids)
            lid = random.choice(lesson_ids) if ftype == "lesson_feedback" else None
            reviewer = random.choice(staff_ids) if status in ("approved", "resolved") else None
            reviewed_at = _past(random.randint(1, 30)) if reviewer else None
            created = _past(random.randint(5, 200))
            await session.execute(text("""
                INSERT INTO course_feedback
                    (user_id, course_id, lesson_id, feedback_type, rating, comment,
                     status, reviewed_by_id, reviewed_at, created_at, updated_at)
                VALUES (:uid, :cid, :lid, :ftype, :rating, :comment,
                        :status, :reviewer, :reviewed_at, :created, :created)
            """), {
                "uid": random.choice(patron_ids), "cid": cid, "lid": lid,
                "ftype": ftype, "rating": rating, "comment": comment,
                "status": status, "reviewer": reviewer, "reviewed_at": reviewed_at,
                "created": created,
            })
        print(f"    Created {len(feedback_data)} course feedback entries")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 9. QUIZ QUESTIONS + QUIZ ATTEMPTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM quiz_questions"))
    if r.scalar() == 0 and lesson_ids:
        print("  Seeding quiz_questions...")
        # Use lessons that look like quiz lessons (IDs 13,18,25,32,39,46,51,58,63)
        quiz_lesson_ids = [13, 18, 25, 32, 39, 46, 51, 58, 63]
        # Filter to only existing lesson IDs
        valid_quiz_lessons = [lid for lid in quiz_lesson_ids if lid in [l[0] for l in lessons]]

        quiz_questions_data = [
            # Computer Basics quiz (lesson 13)
            (13, "What is the main function of a computer's operating system?", "multiple_choice",
             '{"choices": ["Managing hardware and software resources", "Playing videos", "Connecting to the internet", "Printing documents"], "correct_index": 0}',
             "The operating system manages all hardware and software resources on a computer.", 1),
            (13, "Which of these is an input device?", "multiple_choice",
             '{"choices": ["Monitor", "Printer", "Keyboard", "Speaker"], "correct_index": 2}',
             "A keyboard sends information to the computer, making it an input device.", 2),
            (13, "What does 'saving' a file do?", "multiple_choice",
             '{"choices": ["Deletes the file permanently", "Stores the file so you can open it later", "Sends the file to a printer", "Closes the program"], "correct_index": 1}',
             "Saving stores your work so you can access it again later.", 3),

            # Internet Skills quiz (lesson 18)
            (18, "What does 'URL' stand for?", "multiple_choice",
             '{"choices": ["Universal Resource Locator", "Uniform Resource Locator", "United Resource Link", "Universal Reference Locator"], "correct_index": 1}',
             "URL stands for Uniform Resource Locator — the address of a webpage.", 1),
            (18, "Which of these is the safest practice for email?", "multiple_choice",
             '{"choices": ["Open all attachments immediately", "Click every link to see what it is", "Never open attachments from unknown senders", "Share your password with friends"], "correct_index": 2}',
             "Never open attachments from unknown senders to protect yourself from malware.", 2),
            (18, "What does a search engine do?", "multiple_choice",
             '{"choices": ["Fixes broken websites", "Finds web pages based on your search terms", "Creates new websites", "Protects your computer from viruses"], "correct_index": 1}',
             "A search engine indexes web pages and returns results matching your search terms.", 3),

            # Catalog Skills quiz (lesson 25)
            (25, "What is a 'hold' in the library catalog?", "multiple_choice",
             '{"choices": ["Deleting a book from the system", "Reserving an item that is currently checked out", "Renewing a book for extra time", "Reporting a lost book"], "correct_index": 1}',
             "A hold reserves an item so it will be set aside for you when it becomes available.", 1),
            (25, "How many times can you typically renew a library book?", "multiple_choice",
             '{"choices": ["Unlimited times", "Once", "Twice, unless someone has a hold on it", "Never"], "correct_index": 2}',
             "Books can typically be renewed twice unless another patron has placed a hold.", 2),
            (25, "What is an ISBN?", "multiple_choice",
             '{"choices": ["A library fine code", "A unique book identification number", "A type of barcode scanner", "An online reading program"], "correct_index": 1}',
             "ISBN stands for International Standard Book Number — a unique identifier for books.", 3),

            # Smartphone Skills quiz (lesson 32)
            (32, "What is an 'app' on a smartphone?", "multiple_choice",
             '{"choices": ["A type of phone call", "A software application that performs a specific function", "A brand of smartphone", "A setting to make the phone louder"], "correct_index": 1}',
             "An app (application) is software designed to perform a specific task on your device.", 1),
            (32, "How do you increase the text size on most smartphones?", "multiple_choice",
             '{"choices": ["Buy a bigger phone", "Go to Settings > Accessibility > Display", "Download a magnifying app", "Tap the screen harder"], "correct_index": 1}',
             "Most phones have accessibility settings that allow you to increase text size.", 2),
            (32, "What should you do if your phone screen freezes?", "multiple_choice",
             '{"choices": ["Throw it away", "Hold the power button to force restart", "Wait 24 hours", "Remove the battery"], "correct_index": 1}',
             "A force restart (holding the power button) usually resolves a frozen screen.", 3),

            # Research Ethics quiz (lesson 39)
            (39, "What is plagiarism?", "multiple_choice",
             json.dumps({"choices": ["Citing your sources correctly", "Using someone else's work without giving credit", "Writing an original paper", "Quoting an author with attribution"], "correct_index": 1}),
             "Plagiarism is presenting someone else's work or ideas as your own.", 1),
            (39, "Which citation style is most commonly used in the humanities?", "multiple_choice",
             '{"choices": ["APA", "MLA", "Chicago", "IEEE"], "correct_index": 1}',
             "MLA (Modern Language Association) style is most commonly used in the humanities.", 2),
            (39, "What is the difference between paraphrasing and quoting?", "multiple_choice",
             '{"choices": ["There is no difference", "Paraphrasing uses exact words, quoting does not", "Quoting uses exact words, paraphrasing restates ideas in your own words", "Both require quotation marks"], "correct_index": 2}',
             "Quoting uses the exact words with quotation marks; paraphrasing restates ideas in your own words.", 3),

            # Job Search Skills quiz (lesson 46)
            (46, "What is the most important section of a resume?", "multiple_choice",
             '{"choices": ["Hobbies", "References", "Work experience and skills relevant to the job", "Personal photo"], "correct_index": 2}',
             "Relevant work experience and skills are what employers look for first on a resume.", 1),
            (46, "What should you research before a job interview?", "multiple_choice",
             json.dumps({"choices": ["The interviewer's personal social media", "The company's mission, products, and recent news", "Other candidates applying", "The closest restaurants"], "correct_index": 1}),
             "Researching the company shows preparation and genuine interest.", 2),
            (46, "Which library resource can help with job searching?", "multiple_choice",
             json.dumps({"choices": ["DVD collection", "Children's storytime", "Resume databases and career workshop programs", "The book drop"], "correct_index": 2}),
             "The library offers resume resources, career databases, and job search workshops.", 3),

            # 3D Printing quiz (lesson 51)
            (51, "What material do most library 3D printers use?", "multiple_choice",
             '{"choices": ["Wood", "PLA filament", "Metal wire", "Paper"], "correct_index": 1}',
             "PLA (polylactic acid) is the most common 3D printing filament, especially in library settings.", 1),
            (51, "What software can you use to design 3D objects for printing?", "multiple_choice",
             '{"choices": ["Microsoft Word", "Tinkercad", "Adobe Photoshop", "Google Maps"], "correct_index": 1}',
             "Tinkercad is a free, browser-based 3D design tool perfect for beginners.", 2),
            (51, "What is the first safety rule of the makerspace?", "multiple_choice",
             '{"choices": ["Run as fast as possible", "Never touch any equipment", "Always get staff approval before starting a print", "Bring your own tools from home"], "correct_index": 2}',
             "All prints must be approved by staff to ensure safety and appropriate use of materials.", 3),

            # Genealogy Basics quiz (lesson 58)
            (58, "What is the best first step in genealogy research?", "multiple_choice",
             '{"choices": ["Order a DNA test immediately", "Start with what you already know about your family", "Visit a foreign country", "Search random names online"], "correct_index": 1}',
             "Always start by documenting what you already know from family members and personal records.", 1),
            (58, "Which type of record lists names, ages, and addresses of everyone in a household?", "multiple_choice",
             '{"choices": ["Birth certificate", "Census record", "Newspaper obituary", "Church bulletin"], "correct_index": 1}',
             "Census records provide a snapshot of households and are essential for genealogy research.", 2),
            (58, "What does DNA testing tell you about your ancestry?", "multiple_choice",
             '{"choices": ["Your exact family tree going back 1000 years", "Your ethnicity estimates and genetic matches to other testers", "The names of all your ancestors", "Where your ancestors are buried"], "correct_index": 1}',
             "DNA testing provides ethnicity estimates and connects you with genetic relatives who have also tested.", 3),

            # Privacy and Security quiz (lesson 63)
            (63, "What is 'phishing'?", "multiple_choice",
             '{"choices": ["A type of computer virus", "A scam that tricks you into revealing personal information", "A way to speed up your internet", "A social media platform"], "correct_index": 1}',
             "Phishing is a social engineering attack designed to trick you into revealing sensitive information.", 1),
            (63, "What makes a strong password?", "multiple_choice",
             json.dumps({"choices": ["Your birthday", "The word 'password'", "A mix of uppercase, lowercase, numbers, and symbols, at least 12 characters", "Your pet's name"], "correct_index": 2}),
             "Strong passwords are long, complex, and don't contain personal information.", 2),
            (63, "What should you do if you receive a suspicious email asking for your bank information?", "multiple_choice",
             '{"choices": ["Reply with your information immediately", "Click the link to verify", "Delete it and report it as phishing", "Forward it to all your contacts"], "correct_index": 2}',
             "Never respond to suspicious emails. Delete them and report them as phishing.", 3),
        ]

        valid_lesson_set = {l[0] for l in lessons}
        inserted_qq = 0
        for lid, qtext, qtype, options_json, explanation, sort in quiz_questions_data:
            if lid not in valid_lesson_set:
                continue
            await session.execute(text("""
                INSERT INTO quiz_questions
                    (lesson_id, question_text, question_type, options, explanation, sort_order)
                VALUES (:lid, :qtext, :qtype, cast(:options as jsonb), :explanation, :sort)
            """), {
                "lid": lid, "qtext": qtext, "qtype": qtype,
                "options": options_json, "explanation": explanation, "sort": sort,
            })
            inserted_qq += 1
        print(f"    Created {inserted_qq} quiz questions")
        await session.commit()

    # Quiz Attempts
    r = await session.execute(text("SELECT COUNT(*) FROM quiz_attempts"))
    if r.scalar() == 0 and patron_ids:
        print("  Seeding quiz_attempts...")
        valid_lesson_set = {l[0] for l in lessons}
        quiz_lesson_ids = [13, 18, 25, 32, 39, 46, 51, 58, 63]
        valid_quiz_lessons = [lid for lid in quiz_lesson_ids if lid in valid_lesson_set]

        count = 0
        if valid_quiz_lessons:
            for _ in range(40):
                uid = random.choice(patron_ids)
                lid = random.choice(valid_quiz_lessons)
                score = random.randint(40, 100)
                passed = score >= 70
                started = _past(random.randint(5, 200))
                completed = started + timedelta(minutes=random.randint(5, 25))
                answers_json = json.dumps({
                    "responses": [
                        {"question_index": i, "selected": random.randint(0, 3), "correct": random.choice([True, True, True, False])}
                        for i in range(3)
                    ]
                })
                await session.execute(text("""
                    INSERT INTO quiz_attempts
                        (user_id, lesson_id, score, passed, answers, started_at, completed_at)
                    VALUES (:uid, :lid, :score, :passed, cast(:answers as jsonb), :started, :completed)
                """), {
                    "uid": uid, "lid": lid, "score": score, "passed": passed,
                    "answers": answers_json, "started": started, "completed": completed,
                })
                count += 1
        print(f"    Created {count} quiz attempts")
        if count > 0:
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 10. COHORTS + COHORT MEMBERS + COHORT TRAININGS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM cohorts"))
    if r.scalar() == 0 and staff_ids and course_ids:
        print("  Seeding cohorts, cohort_members & cohort_trainings...")
        cohorts_data = [
            ("New Hire Orientation — Spring 2026",
             "Onboarding cohort for staff hired in Q1 2026. Covers library systems, policies, and customer service fundamentals.",
             '["onboarding", "new-hire", "spring-2026"]'),
            ("Annual Safety Recertification 2026",
             "All-staff cohort for annual safety training including fire evacuation, active threat response, and first aid refresher.",
             '["safety", "annual", "required", "2026"]'),
            ("Leadership Development Program",
             "Six-month leadership development track for aspiring supervisors. Covers management skills, budgeting, and strategic planning.",
             '["leadership", "management", "professional-development"]'),
            ("Digital Services Training Cohort",
             "Focused training on digital resources, ebook platforms, and technology assistance for front-line staff.",
             '["digital", "technology", "ebooks", "staff-development"]'),
        ]

        cohort_ids = []
        for name, desc, tags_json in cohorts_data:
            cr = await session.execute(text("""
                INSERT INTO cohorts (name, description, tags, created_by)
                VALUES (:name, :desc, cast(:tags as jsonb), :creator)
                RETURNING id
            """), {
                "name": name, "desc": desc, "tags": tags_json,
                "creator": random.choice(staff_ids),
            })
            cohort_ids.append(cr.scalar())

        # Add members to each cohort
        member_count = 0
        for i, cid in enumerate(cohort_ids):
            # Each cohort gets 4-8 members from staff
            num_members = random.randint(4, min(8, len(staff_ids)))
            members = random.sample(staff_ids, num_members)
            for j, uid in enumerate(members):
                role = "lead" if j == 0 else "member"
                status = random.choice(["active", "active", "active", "inactive"]) if i < 3 else "active"
                await session.execute(text("""
                    INSERT INTO cohort_members (cohort_id, user_id, role, status, joined_at)
                    VALUES (:cid, :uid, cast(:role as cohortmemberrole), cast(:member_status as cohortmemberstatus), :joined)
                """), {
                    "cid": cid, "uid": uid, "role": role, "member_status": status,
                    "joined": _past(random.randint(5, 180)),
                })
                member_count += 1

        # Add training assignments to each cohort
        training_count = 0
        for i, cid in enumerate(cohort_ids):
            num_courses = random.randint(2, min(4, len(course_ids)))
            assigned_courses = random.sample(course_ids, num_courses)
            for course_id in assigned_courses:
                due_date = now + timedelta(days=random.randint(14, 90))
                assigned_at = _past(random.randint(5, 30))
                await session.execute(text("""
                    INSERT INTO cohort_trainings (cohort_id, course_id, due_date, assigned_at)
                    VALUES (:cid, :course_id, :due, :assigned)
                """), {
                    "cid": cid, "course_id": course_id,
                    "due": due_date, "assigned": assigned_at,
                })
                training_count += 1

        print(f"    Created {len(cohorts_data)} cohorts, {member_count} members, {training_count} training assignments")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # FIX SEQUENCES
    # ════════════════════════════════════════════════════════════════
    seq_tables = [
        "staff_knowledge_articles", "decision_trees", "executive_dashboards",
        "dashboard_widgets", "executive_reports", "impact_stories",
        "impact_metrics", "course_enrollments", "course_feedback",
        "quiz_questions", "quiz_attempts", "cohorts", "cohort_members",
        "cohort_trainings", "partner_impact_reports",
    ]
    for table in seq_tables:
        try:
            async with session.begin_nested():
                await session.execute(text(
                    f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
                ))
        except SQLAlchemyError:
            pass  # Some tables might not have standard sequence naming

    await session.commit()
    print("  Staff-facing batch seeding complete!")
    return True
