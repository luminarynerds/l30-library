# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

utc = timezone.utc
def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago)
def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("+00", "+00:00"))
def _d(s: str) -> date:
    return date.fromisoformat(s)
async def seed_batch_operations(session: AsyncSession) -> bool:

    # Grab reusable IDs
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] in ("patron", "child")]
    all_ids = [u[0] for u in users]

    if not staff_ids:
        print("  Skipping operations batch -- no staff found")
        return False

    s = staff_ids
    director = s[0]
    admin = s[1] if len(s) > 1 else s[0]
    p = patron_ids

    # Helper: pick IDs from a query, return empty list if table missing
    async def _ids(query):
        try:
            r = await session.execute(text(query))
            return [row[0] for row in r.fetchall()]
        except SQLAlchemyError:
            return []

    branch_ids = await _ids("SELECT id FROM branches ORDER BY id")
    plan_ids = await _ids("SELECT id FROM strategic_plans ORDER BY id LIMIT 5")
    initiative_ids = await _ids("SELECT id FROM strategic_initiatives ORDER BY id LIMIT 10")
    ill_request_ids = await _ids("SELECT id FROM ill_requests ORDER BY id")
    vendor_ids = await _ids("SELECT id FROM vendors ORDER BY id LIMIT 10")
    fund_ids = await _ids("SELECT id FROM funds ORDER BY id LIMIT 10")
    event_ids = await _ids("SELECT id FROM events ORDER BY id LIMIT 25")
    program_ids = await _ids("SELECT id FROM programs ORDER BY id LIMIT 10")
    item_copy_ids = await _ids("SELECT id FROM item_copies ORDER BY id LIMIT 10")
    catalog_item_ids = await _ids("SELECT id FROM catalog_items ORDER BY id LIMIT 50")
    recovery_project_ids = await _ids("SELECT id FROM collection_recovery_projects ORDER BY id LIMIT 5")
    vol_app_ids = await _ids("SELECT id FROM volunteer_applications ORDER BY id LIMIT 20")

    # ════════════════════════════════════════════════════════════════
    # 1. SKILLS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM skills"))
    if r.scalar() == 0:
        print("  Seeding skills...")
        skills = [
            ("Cataloging (MARC21)", "Proficiency in MARC21 bibliographic record creation and editing", "technical"),
            ("Reference Interview", "Conducting effective reference interviews to identify patron information needs", "public_services"),
            ("Youth Programming", "Planning and delivering engaging programs for children and teens", "programming"),
            ("Collection Development", "Selecting and evaluating materials for library collections", "technical"),
            ("Digital Literacy Instruction", "Teaching patrons to use computers, internet, and digital resources", "public_services"),
            ("Interlibrary Loan Processing", "Managing ILL requests through OCLC WorldShare and regional systems", "technical"),
            ("Community Outreach", "Building partnerships with local organizations and promoting library services", "programming"),
            ("Circulation Systems", "Operating ILS circulation modules including checkouts, returns, and holds", "technical"),
            ("Grant Writing", "Writing and managing library grant proposals and reports", "administrative"),
            ("Conflict De-escalation", "Handling difficult patron interactions with empathy and professionalism", "public_services"),
        ]
        for name, desc, cat in skills:
            await session.execute(text("""
                INSERT INTO skills (name, description, category, is_active)
                VALUES (:name, :desc, :cat, true)
            """), {"name": name, "desc": desc, "cat": cat})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 2. COMMITTEES + MEMBERS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM committees"))
    if r.scalar() == 0:
        print("  Seeding committees...")
        committees = [
            ("Collection Development Committee",
             "Reviews and recommends materials for acquisition across all formats and age groups",
             "Monthly", "active", True, s[1] if len(s) > 1 else s[0], _past(365),
             '["collection diversity", "patron requests", "weeding criteria", "budget allocation"]',
             "Maintain a current, diverse, and responsive collection that reflects community needs"),
            ("Technology Advisory Committee",
             "Evaluates and recommends technology services, equipment, and digital resources",
             "Quarterly", "active", True, s[5] if len(s) > 5 else s[0], _past(200),
             '["public computers", "wifi access", "digital literacy", "emerging technology"]',
             "Ensure technology offerings meet patron and staff needs"),
            ("Summer Reading Planning Committee",
             "Plans and coordinates the annual summer reading program for all age groups",
             "Weekly during planning season", "active", False, s[2] if len(s) > 2 else s[0], _past(60),
             '["program themes", "prizes", "partnerships", "marketing"]',
             "Deliver an engaging summer reading program that increases participation by 10 percent"),
            ("Diversity Equity and Inclusion Committee",
             "Promotes inclusive library services, collections, and workplace culture",
             "Monthly", "active", True, s[0], _past(300),
             '["inclusive programming", "collection audits", "staff training", "community partnerships"]',
             "Foster an equitable and welcoming environment for all patrons and staff"),
            ("Emergency Preparedness Committee",
             "Develops and maintains disaster response and business continuity plans",
             "Quarterly", "on_hold", False, s[1] if len(s) > 1 else s[0], _past(150),
             '["disaster recovery", "staff safety", "collection preservation", "communication protocols"]',
             "Complete and test an updated emergency response plan"),
        ]
        committee_ids = []
        for name, purpose, freq, status, standing, proposed_by, approved, focus, outcomes in committees:
            r2 = await session.execute(text("""
                INSERT INTO committees
                    (organization_id, name, purpose, meeting_frequency, status,
                     is_standing, proposed_by_id, approved_date, focus_areas, expected_outcomes)
                VALUES (0, :name, :purpose, :freq, :status, :standing,
                        :proposed_by, :approved, cast(:focus as jsonb), :outcomes)
                RETURNING id
            """), {"name": name, "purpose": purpose, "freq": freq, "status": status,
                   "standing": standing, "proposed_by": proposed_by, "approved": approved,
                   "focus": focus, "outcomes": outcomes})
            committee_ids.append(r2.scalar())
        await session.flush()

        # Committee members
        print("  Seeding committee_members...")
        members = [
            (committee_ids[0], s[1] if len(s) > 1 else s[0], "chair", "active",
             _past(365), None, "Established quarterly collection review process and weeding schedule"),
            (committee_ids[0], s[4] if len(s) > 4 else s[0], "member", "active",
             _past(300), None, "Leads youth collection review and coordinates with schools on curriculum needs"),
            (committee_ids[0], s[7] if len(s) > 7 else s[0], "member", "active",
             _past(200), None, "Handles cataloging workflow for new acquisitions recommended by committee"),
            (committee_ids[1], s[5] if len(s) > 5 else s[0], "chair", "active",
             _past(200), None, "Drove adoption of new ILS system and public computer refresh"),
            (committee_ids[1], s[3] if len(s) > 3 else s[0], "member", "active",
             _past(200), None, "Manages public computer fleet and troubleshoots patron technology issues"),
            (committee_ids[2], s[2] if len(s) > 2 else s[0], "chair", "active",
             _past(60), None, "Leading 2026 summer reading theme selection and prize sourcing"),
            (committee_ids[2], s[4] if len(s) > 4 else s[0], "member", "active",
             _past(55), None, "Coordinating teen and tween reading tracks"),
            (committee_ids[3], s[0], "facilitator", "active",
             _past(300), None, "Initiated collection diversity audit and inclusive programming review"),
            (committee_ids[3], s[2] if len(s) > 2 else s[0], "secretary", "active",
             _past(280), None, "Documents meeting minutes and tracks action items"),
            (committee_ids[4], s[1] if len(s) > 1 else s[0], "chair", "active",
             _past(150), None, "Drafted initial emergency response plan framework"),
        ]
        for cid, sid, role, status, joined, departed, contrib in members:
            await session.execute(text("""
                INSERT INTO committee_members
                    (committee_id, staff_id, role, status, joined_date, departed_date, contributions_summary)
                VALUES (:cid, :sid, :role, :status, :joined, :departed, :contrib)
            """), {"cid": cid, "sid": sid, "role": role, "status": status,
                   "joined": joined, "departed": departed, "contrib": contrib})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 3. STRATEGIC BUDGETS + ALLOCATIONS + ITEMS + TRANSACTIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM strategic_budgets"))
    if r.scalar() == 0 and plan_ids:
        print("  Seeding strategic_budgets...")
        budgets = [
            (plan_ids[0], "FY2026 Operating Budget",
             "Annual operating budget for library services and collections",
             2026, 485000.00, 392000.00, 178500.00, 85000.00, 221500.00, "active",
             _dt("2025-10-15 13:00:00+00"), director, admin),
            (plan_ids[0], "FY2026 Capital Improvements",
             "Capital budget for facility upgrades and major equipment",
             2026, 125000.00, 95000.00, 42000.00, 35000.00, 48000.00, "active",
             _dt("2025-10-15 13:00:00+00"), director, admin),
            (plan_ids[0], "FY2025 Operating Budget",
             "Prior year operating budget - closed",
             2025, 460000.00, 460000.00, 448200.00, 0.00, 11800.00, "closed",
             _dt("2024-10-10 13:00:00+00"), director, admin),
        ]
        budget_ids = []
        for pid, name, desc, fy, total, alloc, spent, commit, avail, status, approved, approved_by, owner in budgets:
            r2 = await session.execute(text("""
                INSERT INTO strategic_budgets
                    (plan_id, name, description, fiscal_year, total_budget,
                     allocated_amount, spent_amount, committed_amount, available_amount,
                     status, approved_date, approved_by_id, budget_owner_id)
                VALUES (:pid, :name, :desc, :fy, :total, :alloc, :spent, :commit,
                        :avail, :status, :approved, :approved_by, :owner)
                RETURNING id
            """), {"pid": pid, "name": name, "desc": desc, "fy": fy, "total": total,
                   "alloc": alloc, "spent": spent, "commit": commit, "avail": avail,
                   "status": status, "approved": approved, "approved_by": approved_by,
                   "owner": owner})
            budget_ids.append(r2.scalar())
        await session.flush()

        # Budget allocations
        print("  Seeding budget_allocations...")
        ini = initiative_ids
        allocs = [
            (budget_ids[0], "Collections - Adult Materials", 120000.00, _dt("2025-11-01 13:00:00+00"),
             "Annual allocation for adult fiction and nonfiction acquisitions",
             ini[0] if len(ini) > 0 else None, "Collections", director),
            (budget_ids[0], "Collections - Youth Materials", 85000.00, _dt("2025-11-01 13:00:00+00"),
             "Annual allocation for children and YA materials",
             ini[1] if len(ini) > 1 else None, "Youth Services", director),
            (budget_ids[0], "Technology Services", 62000.00, _dt("2025-11-01 13:00:00+00"),
             "IT infrastructure, software licenses, and digital resources",
             ini[2] if len(ini) > 2 else None, "Technology", director),
            (budget_ids[0], "Programming and Events", 45000.00, _dt("2025-11-01 13:00:00+00"),
             "Library programming, author visits, summer reading",
             ini[3] if len(ini) > 3 else None, "Programming", director),
            (budget_ids[0], "Facilities Operations", 80000.00, _dt("2025-11-01 13:00:00+00"),
             "Utilities, maintenance, supplies", None, "Facilities", director),
            (budget_ids[1], "HVAC System Upgrade", 55000.00, _dt("2025-11-15 13:00:00+00"),
             "Replace aging HVAC units in main branch",
             ini[4] if len(ini) > 4 else None, "Facilities", director),
            (budget_ids[1], "Self-Checkout Stations", 40000.00, _dt("2025-11-15 13:00:00+00"),
             "Install 4 new self-checkout kiosks",
             ini[2] if len(ini) > 2 else None, "Technology", director),
        ]
        for bid, desc, amt, adate, purpose, iid, dept, auth in allocs:
            await session.execute(text("""
                INSERT INTO budget_allocations
                    (budget_id, description, amount, allocation_date, purpose,
                     initiative_id, department, authorized_by_id)
                VALUES (:bid, :desc, :amt, :adate, :purpose, :iid, :dept, :auth)
            """), {"bid": bid, "desc": desc, "amt": amt, "adate": adate,
                   "purpose": purpose, "iid": iid, "dept": dept, "auth": auth})
        await session.flush()

        # Budget items
        print("  Seeding budget_items...")
        items = [
            (budget_ids[0], "collections", "adult fiction", "Adult fiction book purchases",
             65000.00, 65000.00, 32100.00, 32900.00, "5110-01", "Collections",
             ini[0] if len(ini) > 0 else None, "Core collection development for adult readers"),
            (budget_ids[0], "collections", "adult nonfiction", "Adult nonfiction acquisitions",
             55000.00, 55000.00, 28400.00, 26600.00, "5110-02", "Collections",
             ini[0] if len(ini) > 0 else None, "Supporting lifelong learning and research needs"),
            (budget_ids[0], "collections", "youth materials", "Children and YA materials",
             85000.00, 85000.00, 41200.00, 43800.00, "5120-01", "Youth Services",
             ini[1] if len(ini) > 1 else None, "Early literacy and youth engagement"),
            (budget_ids[0], "technology", "software licenses", "ILS, databases, and software subscriptions",
             38000.00, 38000.00, 38000.00, 0.00, "5210-01", "Technology",
             ini[2] if len(ini) > 2 else None, "Annual renewal of core technology platforms"),
            (budget_ids[0], "technology", "hardware", "Computer replacements and peripherals",
             24000.00, 24000.00, 12800.00, 11200.00, "5210-02", "Technology",
             ini[2] if len(ini) > 2 else None, "Replacement cycle for public access computers"),
            (budget_ids[0], "programming", "summer reading", "Summer reading program expenses",
             18000.00, 18000.00, 8500.00, 9500.00, "5310-01", "Programming",
             ini[3] if len(ini) > 3 else None, "Annual summer reading incentives and materials"),
            (budget_ids[1], "capital", "hvac", "HVAC system replacement - main branch",
             55000.00, 55000.00, 42000.00, 13000.00, "6110-01", "Facilities",
             ini[4] if len(ini) > 4 else None, "Emergency replacement of failing units"),
            (budget_ids[1], "capital", "self-checkout", "Self-checkout kiosk installation",
             40000.00, 40000.00, 0.00, 40000.00, "6210-01", "Technology",
             ini[2] if len(ini) > 2 else None, "Patron self-service improvement initiative"),
        ]
        for bid, cat, subcat, desc, budgeted, allocated, spent, remaining, code, dept, iid, just in items:
            await session.execute(text("""
                INSERT INTO budget_items
                    (budget_id, category, subcategory, description, budgeted_amount,
                     allocated_amount, spent_amount, remaining_amount, account_code,
                     department, initiative_id, justification)
                VALUES (:bid, :cat, :subcat, :desc, :budgeted, :allocated, :spent,
                        :remaining, :code, :dept, :iid, :just)
            """), {"bid": bid, "cat": cat, "subcat": subcat, "desc": desc,
                   "budgeted": budgeted, "allocated": allocated, "spent": spent,
                   "remaining": remaining, "code": code, "dept": dept, "iid": iid, "just": just})
        await session.flush()

        # Budget transactions
        print("  Seeding budget_transactions...")
        txns = [
            (budget_ids[0], "expenditure", "Baker & Taylor - March adult fiction order",
             4250.00, _dt("2026-03-15 14:30:00+00"), "collections",
             ini[0] if len(ini) > 0 else None, "INV-2026-03-1847", "Baker & Taylor", director),
            (budget_ids[0], "expenditure", "Ingram - YA materials spring order",
             2890.00, _dt("2026-03-20 18:00:00+00"), "collections",
             ini[1] if len(ini) > 1 else None, "INV-2026-03-2201", "Ingram Library Services", director),
            (budget_ids[0], "expenditure", "OCLC annual subscription renewal",
             8500.00, _dt("2026-01-10 13:00:00+00"), "technology",
             ini[2] if len(ini) > 2 else None, "INV-2026-01-0042", "OCLC", director),
            (budget_ids[0], "expenditure", "Demco - processing supplies",
             1245.00, _dt("2026-02-28 15:15:00+00"), "supplies",
             None, "INV-2026-02-0891", "Demco", admin),
            (budget_ids[0], "expenditure", "Summer reading prize inventory",
             3200.00, _dt("2026-03-01 14:00:00+00"), "programming",
             ini[3] if len(ini) > 3 else None, "INV-2026-03-0156", "Oriental Trading", director),
            (budget_ids[1], "expenditure", "HVAC contractor - phase 2 installation",
             22000.00, _dt("2026-02-15 13:00:00+00"), "capital",
             ini[4] if len(ini) > 4 else None, "INV-2026-02-HC-004", "Comfort Systems HVAC", director),
            (budget_ids[0], "adjustment", "State grant funds received - digital literacy",
             -15000.00, _dt("2026-01-20 13:00:00+00"), "technology",
             ini[2] if len(ini) > 2 else None, None, None, director),
        ]
        for bid, ttype, desc, amt, tdate, cat, iid, inv, vendor, approved_by in txns:
            await session.execute(text("""
                INSERT INTO budget_transactions
                    (budget_id, transaction_type, description, amount, transaction_date,
                     category, initiative_id, invoice_number, vendor, approved_by_id)
                VALUES (:bid, :ttype, :desc, :amt, :tdate, :cat, :iid, :inv, :vendor, :approved_by)
            """), {"bid": bid, "ttype": ttype, "desc": desc, "amt": amt,
                   "tdate": tdate, "cat": cat, "iid": iid, "inv": inv,
                   "vendor": vendor, "approved_by": approved_by})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 4. ILL COST RECORDS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM ill_cost_records"))
    if r.scalar() == 0 and ill_request_ids:
        print("  Seeding ill_cost_records...")
        ill = ill_request_ids
        staff_admin = admin if len(s) > 1 else s[0]
        costs = [
            (ill[-6] if len(ill) >= 6 else ill[0], "shipping",
             "USPS Media Mail shipping to Columbus Metropolitan Library", 4.50, True,
             _dt("2026-03-10 14:00:00+00"), staff_admin),
            (ill[-5] if len(ill) >= 5 else ill[0], "lending_fee",
             "Lending fee charged by Ohio State University Libraries", 25.00, True,
             _dt("2026-03-12 18:30:00+00"), staff_admin),
            (ill[-4] if len(ill) >= 4 else ill[0], "shipping",
             "Return shipping via FedEx", 8.75, True,
             _dt("2026-03-18 13:00:00+00"), staff_admin),
            (ill[-3] if len(ill) >= 3 else ill[0], "photocopy",
             "Article photocopy from Cleveland Public Library", 12.00, False,
             None, staff_admin),
            (ill[-2] if len(ill) >= 2 else ill[0], "processing",
             "Processing fee for rush ILL request", 5.00, True,
             _dt("2026-03-25 15:00:00+00"), staff_admin),
            (ill[-1], "shipping",
             "USPS Priority Mail - fragile AV item", 12.50, True,
             _dt("2026-03-28 14:00:00+00"), staff_admin),
        ]
        for illid, cat, desc, amt, invoiced, inv_at, created_by in costs:
            await session.execute(text("""
                INSERT INTO ill_cost_records
                    (ill_request_id, category, description, amount, is_invoiced,
                     invoiced_at, created_by_id)
                VALUES (:illid, :cat, :desc, :amt, :invoiced, :inv_at, :created_by)
            """), {"illid": illid, "cat": cat, "desc": desc, "amt": amt,
                   "invoiced": invoiced, "inv_at": inv_at, "created_by": created_by})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 5. ILL TRACKING UPDATES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM ill_tracking_updates"))
    if r.scalar() == 0 and ill_request_ids:
        print("  Seeding ill_tracking_updates...")
        ill = ill_request_ids
        staff_admin = admin if len(s) > 1 else s[0]
        updates = [
            (ill[-6] if len(ill) >= 6 else ill[0], "submitted",
             "Request submitted to Columbus Metropolitan Library via OCLC WorldShare", True),
            (ill[-6] if len(ill) >= 6 else ill[0], "approved",
             "Request approved by lending library. Expected ship date: 2026-03-12", True),
            (ill[-6] if len(ill) >= 6 else ill[0], "in_transit",
             "Item shipped via USPS Media Mail, tracking 9400111899223847563", True),
            (ill[-5] if len(ill) >= 5 else ill[0], "submitted",
             "Request sent to Ohio State University Libraries", True),
            (ill[-5] if len(ill) >= 5 else ill[0], "approved",
             "Approved with lending fee of 5.00. Patron notified.", True),
            (ill[-4] if len(ill) >= 4 else ill[0], "submitted",
             "Article request sent to Cleveland Public Library", True),
            (ill[-4] if len(ill) >= 4 else ill[0], "completed",
             "Article received via electronic delivery (PDF)", True),
            (ill[-3] if len(ill) >= 3 else ill[0], "pending",
             "Request entered, awaiting verification of bibliographic details", False),
            (ill[-2] if len(ill) >= 2 else ill[0], "submitted",
             "Rush request submitted to Akron-Summit County Public Library", True),
            (ill[-2] if len(ill) >= 2 else ill[0], "in_transit",
             "Item shipped priority, expected arrival 2026-04-02", True),
        ]
        for illid, status, msg, visible in updates:
            await session.execute(text("""
                INSERT INTO ill_tracking_updates
                    (ill_request_id, status, message, is_patron_visible, created_by_id)
                VALUES (:illid, :status, :msg, :visible, :created_by)
            """), {"illid": illid, "status": status, "msg": msg,
                   "visible": visible, "created_by": staff_admin})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 6. SERIAL TITLES + SUBSCRIPTIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM serial_titles"))
    if r.scalar() == 0:
        print("  Seeding serial_titles...")
        staff_admin = admin if len(s) > 1 else s[0]
        titles = [
            ("Library Journal", "0363-0277", None, "Media Source Inc.", "US", "en", "semimonthly",
             True, "Core professional journal for library staff"),
            ("School Library Journal", "0362-8930", None, "Media Source Inc.", "US", "en", "monthly",
             True, "Reviews and news for youth services"),
            ("Booklist", "0006-7385", None, "American Library Association", "US", "en", "semimonthly",
             True, "Book review publication from ALA"),
            ("Publishers Weekly", "0000-0019", None, "PWxyz LLC", "US", "en", "weekly",
             True, "Trade publication for publishing industry"),
            ("People Magazine", "0093-7673", None, "Dotdash Meredith", "US", "en", "weekly",
             True, "Popular magazine for general circulation"),
            ("National Geographic", "0027-9358", None, "National Geographic Partners", "US", "en", "monthly",
             True, "Science and exploration magazine"),
            ("Consumer Reports", "0010-7174", None, "Consumer Reports Inc.", "US", "en", "monthly",
             True, "Product testing and consumer advice"),
        ]
        serial_title_ids = []
        for title, issn_p, issn_e, pub, country, lang, freq, active, notes in titles:
            r2 = await session.execute(text("""
                INSERT INTO serial_titles
                    (title, issn_print, issn_electronic, publisher, country_of_publication,
                     language, frequency, is_active, notes, created_by_id)
                VALUES (:title, :issn_p, :issn_e, :pub, :country, :lang, :freq, :active, :notes, :created_by)
                RETURNING id
            """), {"title": title, "issn_p": issn_p, "issn_e": issn_e, "pub": pub,
                   "country": country, "lang": lang, "freq": freq, "active": active,
                   "notes": notes, "created_by": staff_admin})
            serial_title_ids.append(r2.scalar())
        await session.flush()

        # Serial subscriptions
        r = await session.execute(text("SELECT COUNT(*) FROM serial_subscriptions"))
        if r.scalar() == 0 and vendor_ids and fund_ids and branch_ids:
            print("  Seeding serial_subscriptions...")
            b1 = branch_ids[0]
            f9 = fund_ids[8] if len(fund_ids) > 8 else fund_ids[0]
            v1 = vendor_ids[0]
            v2 = vendor_ids[1] if len(vendor_ids) > 1 else v1
            v4 = vendor_ids[3] if len(vendor_ids) > 3 else v1
            subs = [
                (serial_title_ids[0], v1, f9, b1, "SUB-LJ-2026-001", 1, _d("2026-01-01"), _d("2026-12-31"),
                 189.99, "active", "Professional development collection"),
                (serial_title_ids[1], v1, f9, b1, "SUB-SLJ-2026-001", 1, _d("2026-01-01"), _d("2026-12-31"),
                 164.99, "active", "Youth services desk reference"),
                (serial_title_ids[2], v1, f9, b1, "SUB-BL-2026-001", 1, _d("2026-01-01"), _d("2026-12-31"),
                 170.00, "active", "Collection development tool"),
                (serial_title_ids[3], v2, f9, b1, "SUB-PW-2026-001", 1, _d("2026-01-01"), _d("2026-12-31"),
                 289.99, "active", "Acquisitions reference"),
                (serial_title_ids[4], v4, f9, b1, "SUB-PPL-2026-001", 2, _d("2026-01-01"), _d("2026-12-31"),
                 199.99, "active", "High-demand popular periodical, 2 copies for main branch"),
                (serial_title_ids[5], v4, f9, b1, "SUB-NG-2026-001", 2, _d("2026-01-01"), _d("2026-12-31"),
                 49.00, "active", "1 copy circulating, 1 reference"),
                (serial_title_ids[6], v4, f9, b1, "SUB-CR-2026-001", 1, _d("2026-01-01"), _d("2026-12-31"),
                 39.00, "pending_renewal", "Renewal pending board approval for FY2027"),
            ]
            for stid, vid, fid, bid, subnum, copies, start, end, cost, rstatus, notes in subs:
                await session.execute(text("""
                    INSERT INTO serial_subscriptions
                        (serial_title_id, vendor_id, fund_id, branch_id, subscription_number,
                         copies_ordered, start_date, end_date, cost, renewal_status, notes, created_by_id)
                    VALUES (:stid, :vid, :fid, :bid, :subnum, :copies, :start, :end,
                            :cost, :rstatus, :notes, :created_by)
                """), {"stid": stid, "vid": vid, "fid": fid, "bid": bid, "subnum": subnum,
                       "copies": copies, "start": start, "end": end, "cost": cost,
                       "rstatus": rstatus, "notes": notes, "created_by": staff_admin})
            await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 7. TRANSIT REQUESTS + SHIPMENTS + ITEMS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM transit_requests"))
    if r.scalar() == 0 and item_copy_ids and branch_ids:
        print("  Seeding transit_requests...")
        ic = item_copy_ids
        b = branch_ids
        staff_admin = admin if len(s) > 1 else s[0]
        staff_circ = s[2] if len(s) > 2 else s[0]

        requests = [
            (ic[0], b[0], b[1] if len(b) > 1 else b[0], "hold", "normal", "in_transit",
             _dt("2026-04-01 13:00:00+00"), staff_admin, _d("2026-04-03"), "Patron hold request"),
            (ic[1] if len(ic) > 1 else ic[0], b[2] if len(b) > 2 else b[0], b[0], "return", "normal", "pending",
             _dt("2026-04-02 14:30:00+00"), staff_admin, _d("2026-04-05"), "Return to owning branch"),
            (ic[2] if len(ic) > 2 else ic[0], b[0], b[3] if len(b) > 3 else b[0], "hold", "rush", "approved",
             _dt("2026-04-03 12:15:00+00"), staff_admin, _d("2026-04-04"), "Rush hold - patron traveling"),
            (ic[3] if len(ic) > 3 else ic[0], b[1] if len(b) > 1 else b[0], b[0], "rebalance", "low", "pending",
             _dt("2026-04-03 18:00:00+00"), staff_circ, None, "Collection rebalancing - excess copies at Northern"),
            (ic[4] if len(ic) > 4 else ic[0], b[3] if len(b) > 3 else b[0], b[0], "repair", "normal", "completed",
             _dt("2026-03-25 13:00:00+00"), staff_admin, _d("2026-03-28"), "Sending for rebinding at main branch"),
            (ic[5] if len(ic) > 5 else ic[0], b[0], b[2] if len(b) > 2 else b[0], "hold", "normal", "in_transit",
             _dt("2026-04-02 15:00:00+00"), staff_circ, _d("2026-04-04"), ""),
        ]
        transit_req_ids = []
        for icid, fb, tb, reason, pri, status, req_at, req_by, exp_arr, notes in requests:
            r2 = await session.execute(text("""
                INSERT INTO transit_requests
                    (item_copy_id, from_branch_id, to_branch_id, reason, priority,
                     status, requested_at, requested_by_id, expected_arrival_date, notes)
                VALUES (:icid, :fb, :tb, :reason, :pri, :status, :req_at, :req_by, :exp_arr, :notes)
                RETURNING id
            """), {"icid": icid, "fb": fb, "tb": tb, "reason": reason, "pri": pri,
                   "status": status, "req_at": req_at, "req_by": req_by,
                   "exp_arr": exp_arr, "notes": notes})
            transit_req_ids.append(r2.scalar())
        await session.flush()

        # Transit shipments
        print("  Seeding transit_shipments...")
        shipments = [
            ("SHP-2026-0401-001", b[0], b[1] if len(b) > 1 else b[0], 3, 1, staff_admin,
             _dt("2026-04-01 14:00:00+00"), staff_admin, None, None, "Library courier", None, "Regular Tuesday courier run"),
            ("SHP-2026-0401-002", b[2] if len(b) > 2 else b[0], b[0], 5, 2, staff_circ,
             _dt("2026-04-01 14:30:00+00"), staff_circ, _dt("2026-04-01 19:00:00+00"), staff_admin,
             "Library courier", None, "Returns batch"),
            ("SHP-2026-0402-001", b[0], b[3] if len(b) > 3 else b[0], 2, 1, staff_admin,
             _dt("2026-04-02 13:30:00+00"), staff_admin, None, None, "Library courier", None, "Rush items for NE branch"),
            ("SHP-2026-0403-001", b[1] if len(b) > 1 else b[0], b[0], 4, 1, staff_circ,
             None, None, None, None, None, None, "Pending pickup - Thursday courier"),
        ]
        shipment_ids = []
        for snum, fb, tb, ic_cnt, cc, created_by, shipped, shipped_by, recv, recv_by, carrier, tracking, notes in shipments:
            r2 = await session.execute(text("""
                INSERT INTO transit_shipments
                    (shipment_number, from_branch_id, to_branch_id, item_count, container_count,
                     created_by_id, shipped_at, shipped_by_id, received_at, received_by_id,
                     carrier, tracking_number, notes)
                VALUES (:snum, :fb, :tb, :ic_cnt, :cc, :created_by, :shipped, :shipped_by,
                        :recv, :recv_by, :carrier, :tracking, :notes)
                RETURNING id
            """), {"snum": snum, "fb": fb, "tb": tb, "ic_cnt": ic_cnt, "cc": cc,
                   "created_by": created_by, "shipped": shipped, "shipped_by": shipped_by,
                   "recv": recv, "recv_by": recv_by, "carrier": carrier,
                   "tracking": tracking, "notes": notes})
            shipment_ids.append(r2.scalar())
        await session.flush()

        # Transit shipment items
        print("  Seeding transit_shipment_items...")
        sit_items = [
            (shipment_ids[0], transit_req_ids[0], _dt("2026-04-01 14:05:00+00"), staff_admin, None, None, ""),
            (shipment_ids[0], transit_req_ids[5], _dt("2026-04-01 14:06:00+00"), staff_admin, None, None, ""),
            (shipment_ids[1], transit_req_ids[1], _dt("2026-04-01 14:35:00+00"), staff_circ,
             _dt("2026-04-01 19:02:00+00"), staff_admin, "Received in good condition"),
            (shipment_ids[1], transit_req_ids[4], _dt("2026-04-01 14:36:00+00"), staff_circ,
             _dt("2026-04-01 19:03:00+00"), staff_admin, "Returning after repair"),
            (shipment_ids[2], transit_req_ids[2], _dt("2026-04-02 13:35:00+00"), staff_admin,
             None, None, "Rush item - notify NE branch on arrival"),
        ]
        for sid, trid, scanned, scanned_by, recv, recv_by, notes in sit_items:
            await session.execute(text("""
                INSERT INTO transit_shipment_items
                    (shipment_id, transit_request_id, scanned_in_at, scanned_in_by_id,
                     received_at, received_by_id, notes)
                VALUES (:sid, :trid, :scanned, :scanned_by, :recv, :recv_by, :notes)
            """), {"sid": sid, "trid": trid, "scanned": scanned, "scanned_by": scanned_by,
                   "recv": recv, "recv_by": recv_by, "notes": notes})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 8. REPAIR RECORDS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM repair_records"))
    if r.scalar() == 0 and catalog_item_ids:
        print("  Seeding repair_records...")
        ci = catalog_item_ids
        staff_admin = admin if len(s) > 1 else s[0]
        staff_circ = s[2] if len(s) > 2 else s[0]
        f8 = fund_ids[7] if len(fund_ids) > 7 else fund_ids[0] if fund_ids else None
        v4 = vendor_ids[3] if len(vendor_ids) > 3 else vendor_ids[0] if vendor_ids else None

        ci_31 = 31 if 31 in ci else ci[0]
        ci_518 = 518 if 518 in ci else ci[1] if len(ci) > 1 else ci[0]
        ci_2074 = 2074 if 2074 in ci else ci[2] if len(ci) > 2 else ci[0]
        ci_2075 = 2075 if 2075 in ci else ci[3] if len(ci) > 3 else ci[0]
        ci_2076 = 2076 if 2076 in ci else ci[4] if len(ci) > 4 else ci[0]

        repairs = [
            (ci_31, staff_admin, "rebinding", "in_repair",
             "Spine cracked, pages loose in signatures 3 and 4",
             "Sent to Brodart for professional rebinding", 18.50, None, f8, v4,
             _d("2026-03-28"), _d("2026-04-15"), None, None, None),
            (ci_518, staff_circ, "cover_repair", "completed",
             "Front cover detached from text block",
             "Reattached with PVA adhesive, reinforced with book tape", 5.00, 3.50, f8, None,
             None, None, _d("2026-03-20"), staff_admin, _d("2026-03-20")),
            (ci_2074, staff_admin, "page_repair", "pending",
             "Water damage to pages 45-60, some text obscured",
             None, 12.00, None, f8, None, None, None, None, None, None),
            (ci_2075, staff_circ, "spine_repair", "completed",
             "Spine label peeling, barcode damaged",
             "New spine label and barcode applied", 2.00, 1.50, f8, None,
             None, None, _d("2026-03-15"), staff_circ, _d("2026-03-15")),
            (ci_2076, staff_admin, "rebinding", "sent_out",
             "Heavily used picture book, binding failing",
             "Sent to Brodart for library binding", 15.00, None, f8, v4,
             _d("2026-04-01"), _d("2026-04-20"), None, None, None),
        ]
        for cid, rep_by, rtype, status, damage, rnotes, est, actual, fid, vid, sent, exp_ret, ret, comp_by, comp_date in repairs:
            await session.execute(text("""
                INSERT INTO repair_records
                    (catalog_item_id, reported_by_id, repair_type, status,
                     damage_description, repair_notes, estimated_cost, actual_cost,
                     fund_id, vendor_id, sent_date, expected_return_date,
                     returned_date, completed_by_id, completed_date)
                VALUES (:cid, :rep_by, :rtype, :status, :damage, :rnotes, :est, :actual,
                        :fid, :vid, :sent, :exp_ret, :ret, :comp_by, :comp_date)
            """), {"cid": cid, "rep_by": rep_by, "rtype": rtype, "status": status,
                   "damage": damage, "rnotes": rnotes, "est": est, "actual": actual,
                   "fid": fid, "vid": vid, "sent": sent, "exp_ret": exp_ret,
                   "ret": ret, "comp_by": comp_by, "comp_date": comp_date})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 9. IMPORT JOBS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM import_jobs"))
    if r.scalar() == 0:
        print("  Seeding import_jobs...")
        staff_admin = s[1] if len(s) > 1 else s[0]
        jobs = [
            ("patrons", "csv", "completed", "patron_import_2026-03-01.csv",
             "/opt/l30/imports/patron_import_2026-03-01.csv", 245780, 1250, 1250, 1180, 45, 20, 5,
             "merge", 0.05, director, _dt("2026-03-01 13:00:00+00"), _dt("2026-03-01 13:12:34+00")),
            ("catalog_items", "marc21", "completed", "baker_taylor_march_2026.mrc",
             "/opt/l30/imports/baker_taylor_march_2026.mrc", 1842560, 350, 350, 342, 8, 0, 0,
             "merge", 0.05, staff_admin, _dt("2026-03-15 18:00:00+00"), _dt("2026-03-15 18:08:12+00")),
            ("catalog_items", "marcxml", "completed", "ingram_ya_spring_2026.xml",
             "/opt/l30/imports/ingram_ya_spring_2026.xml", 892400, 175, 175, 170, 3, 0, 2,
             "skip", 0.05, staff_admin, _dt("2026-03-20 14:00:00+00"), _dt("2026-03-20 14:04:56+00")),
            ("holdings", "csv", "completed", "holdings_cleanup_2026-02.csv",
             "/opt/l30/imports/holdings_cleanup_2026-02.csv", 56200, 420, 420, 0, 418, 2, 0,
             "merge", 0.05, director, _dt("2026-02-15 15:00:00+00"), _dt("2026-02-15 15:03:22+00")),
            ("patrons", "csv", "failed", "patron_bulk_update_bad.csv",
             "/opt/l30/imports/patron_bulk_update_bad.csv", 12400, 85, 22, 0, 15, 0, 7,
             "skip", 0.05, staff_admin, _dt("2026-03-25 20:00:00+00"), _dt("2026-03-25 20:01:05+00")),
            ("catalog_items", "marc21", "pending", "midwest_april_order.mrc",
             "/opt/l30/imports/midwest_april_order.mrc", 2105600, 0, 0, 0, 0, 0, 0,
             "merge", 0.05, staff_admin, None, None),
        ]
        for jtype, fformat, status, fname, fpath, fsize, total, processed, created, updated, skipped, errors, dup, thresh, created_by, started, completed in jobs:
            await session.execute(text("""
                INSERT INTO import_jobs
                    (job_type, file_format, status, source_filename, source_file_path,
                     file_size_bytes, total_rows, processed_rows, created_rows, updated_rows,
                     skipped_rows, error_rows, duplicate_action, error_threshold,
                     created_by_id, started_at, completed_at)
                VALUES (:jtype, :fformat, :status, :fname, :fpath, :fsize, :total,
                        :processed, :created, :updated, :skipped, :errors, :dup, :thresh,
                        :created_by, :started, :completed)
            """), {"jtype": jtype, "fformat": fformat, "status": status,
                   "fname": fname, "fpath": fpath, "fsize": fsize, "total": total,
                   "processed": processed, "created": created, "updated": updated,
                   "skipped": skipped, "errors": errors, "dup": dup, "thresh": thresh,
                   "created_by": created_by, "started": started, "completed": completed})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 10. VOLUNTEER SHIFTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM volunteer_shifts"))
    if r.scalar() == 0:
        print("  Seeding volunteer_shifts...")
        staff_admin = admin if len(s) > 1 else s[0]
        shifts = [
            ("Book Shelving - Main Branch",
             "Reshelve returned materials in adult and youth collections",
             "shelving", _d("2026-04-07"), "09:00", "12:00", 3, "Main Branch", None,
             2, 1, [], [], True, "weekly", None, False),
            ("Summer Reading Prep",
             "Help assemble summer reading packets and organize prize inventory",
             "programming", _d("2026-04-12"), "10:00", "14:00", 4,
             "Main Branch - Community Room", None,
             4, 2, [], [], False, None, "Lunch provided", False),
            ("Tech Help Desk",
             "Assist patrons with computer basics, printing, and digital resources",
             "tech_support", _d("2026-04-08"), "13:00", "17:00", 4,
             "Main Branch - Computer Lab", None,
             1, 1, ["digital_literacy"], ["basic_computing"], True, "weekly", None, False),
            ("Story Time Assistant",
             "Help with craft prep and crowd management during preschool story time",
             "programming", _d("2026-04-09"), "09:30", "11:30", 2,
             "Main Branch - Childrens Area", None,
             2, 0, [], [], True, "weekly", None, False),
            ("Delivery Driver - Branch Courier",
             "Drive courier van between branches for interlibrary materials",
             "delivery", _d("2026-04-08"), "08:00", "12:00", 4,
             "All branches", None,
             1, 1, ["driver_safety"], ["valid_license"], True, "biweekly",
             "Must have valid Ohio driver license and clean driving record", False),
            ("Book Sale Sorting",
             "Sort donated books for upcoming Friends of the Library sale",
             "community_outreach", _d("2026-04-15"), "10:00", "15:00", 5,
             "Main Branch - Basement", None,
             6, 3, [], [], False, None, "Annual spring book sale prep", False),
        ]
        for title, desc, role, sdate, start, end, dur, loc, addr, needed, signed, training, skills, recurring, pattern, notes, cancelled in shifts:
            await session.execute(text("""
                INSERT INTO volunteer_shifts
                    (title, description, role_category, shift_date, start_time, end_time,
                     duration_hours, location, location_address, volunteers_needed,
                     volunteers_signed_up, required_training, required_skills,
                     is_recurring, recurring_pattern, created_by_id, notes, cancelled)
                VALUES (:title, :desc, :role, :sdate, :start, :end, :dur, :loc, :addr,
                        :needed, :signed, :training, :skills, :recurring, :pattern,
                        :created_by, :notes, :cancelled)
            """), {"title": title, "desc": desc, "role": role, "sdate": sdate,
                   "start": start, "end": end, "dur": dur, "loc": loc, "addr": addr,
                   "needed": needed, "signed": signed, "training": training,
                   "skills": skills, "recurring": recurring, "pattern": pattern,
                   "created_by": staff_admin, "notes": notes, "cancelled": cancelled})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 11. VOLUNTEER REFERENCES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM volunteer_references"))
    if r.scalar() == 0 and vol_app_ids:
        print("  Seeding volunteer_references...")
        va = vol_app_ids
        refs = [
            (va[0] if len(va) > 0 else va[0], "Stevie Leigh", "Former supervisor",
             "m.chen@example.org", "555-0142",
             _dt("2026-03-01 13:00:00+00"), _dt("2026-03-03 18:22:00+00"),
             "Excellent volunteer. Very reliable, always on time. Great with the public. Highly recommend."),
            (va[0] if len(va) > 0 else va[0], "Robert Fitzgerald", "Colleague",
             "rfitz@gmail.com", "555-0198",
             _dt("2026-03-01 13:00:00+00"), _dt("2026-03-05 14:15:00+00"),
             "Worked with the applicant at community food bank for 2 years. Very organized and dependable."),
            (va[1] if len(va) > 1 else va[0], "Sarah Johnson", "Teacher",
             "sjohnson@lscschools.edu", "555-0167",
             _dt("2026-03-10 13:00:00+00"), _dt("2026-03-12 20:45:00+00"),
             "Outstanding student. Very responsible and enthusiastic about library work. Would be a great teen volunteer."),
            (va[1] if len(va) > 1 else va[0], "David Park", "Youth group leader",
             "dpark@lscchurch.org", "555-0211",
             _dt("2026-03-10 13:00:00+00"), None, None),
            (va[2] if len(va) > 2 else va[0], "Linda Torres", "Neighbor",
             "ltorres@outlook.com", None,
             _dt("2026-03-15 13:00:00+00"), _dt("2026-03-18 13:30:00+00"),
             "Known the applicant for 10 years. Very community-minded, always helping others. Would be wonderful at the library."),
            (va[3] if len(va) > 3 else va[0], "James Wilson", "Former employer",
             "jwilson@acmeretail.com", "555-0234",
             _dt("2026-03-20 13:00:00+00"), None, None),
        ]
        for appid, name, rel, email, phone, invited, responded, content in refs:
            await session.execute(text("""
                INSERT INTO volunteer_references
                    (application_id, reference_name, reference_relationship,
                     reference_email, reference_phone, invited_at, responded_at,
                     response_content)
                VALUES (:appid, :name, :rel, :email, :phone, :invited, :responded, :content)
            """), {"appid": appid, "name": name, "rel": rel, "email": email,
                   "phone": phone, "invited": invited, "responded": responded,
                   "content": content})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 12. ATTENDANCE SESSIONS + CHECK-INS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM attendance_sessions"))
    if r.scalar() == 0:
        print("  Seeding attendance_sessions...")
        ev = event_ids
        pr = program_ids

        sessions_data = [
            (ev[14] if len(ev) > 14 else None, pr[0] if len(pr) > 0 else None,
             "Story Time - March 15", _d("2026-03-15"), "closed", "st-20260315-abc123",
             False, 0, 12, 4, 8, 6, 2, 0.00, "No cost - regular weekly program", False,
             s[2] if len(s) > 2 else s[0], s[2] if len(s) > 2 else s[0],
             _past(20), "Good turnout despite rain. Two new families attended."),
            (ev[15] if len(ev) > 15 else None, None,
             "Teen Book Club - March 20", _d("2026-03-20"), "closed", "tbc-20260320-def456",
             False, 0, 8, 2, 6, 5, 1, 15.50, "Snacks and beverages", True,
             s[4] if len(s) > 4 else s[0], s[4] if len(s) > 4 else s[0],
             _past(15), "Discussed Yellowface. Lively debate about cultural appropriation themes."),
            (ev[16] if len(ev) > 16 else None, None,
             "Adult Book Club - March 25", _d("2026-03-25"), "closed", "abc-20260325-ghi789",
             False, 0, 15, 3, 12, 10, 2, 8.00, "Coffee and cookies", False,
             s[3] if len(s) > 3 else s[0], s[3] if len(s) > 3 else s[0],
             _past(10), "Record attendance this month. Patron requested more diverse author selections."),
            (ev[18] if len(ev) > 18 else None, None,
             "Computer Basics - March 28", _d("2026-03-28"), "closed", "cb-20260328-jkl012",
             True, 6, 0, 0, 0, 0, 0, 0.00, None, False,
             s[4] if len(s) > 4 else s[0], s[4] if len(s) > 4 else s[0],
             _past(7), "Head count only session. All seniors, focused on email setup."),
            (ev[19] if len(ev) > 19 else None, None,
             "Maker Monday - March 31", _d("2026-03-31"), "closed", "mm-20260331-mno345",
             False, 0, 10, 5, 5, 3, 4, 45.00, "3D printer filament and craft supplies", False,
             s[2] if len(s) > 2 else s[0], s[2] if len(s) > 2 else s[0],
             _past(4), "Kids loved the 3D printed bookmarks project."),
            (None, pr[1] if len(pr) > 1 else None,
             "Preschool STEAM - April 1", _d("2026-04-01"), "closed", "ps-20260401-pqr678",
             False, 0, 9, 3, 6, 4, 2, 12.00, "Craft supplies for volcano experiment", False,
             s[2] if len(s) > 2 else s[0], s[2] if len(s) > 2 else s[0],
             _past(3), "Volcano experiment was a huge hit. Minor cleanup needed afterward."),
            (None, pr[2] if len(pr) > 2 else None,
             "Teen Code Club - April 3", _d("2026-04-03"), "open", "tcc-20260403-stu901",
             False, 0, 5, 1, 4, 3, 1, 0.00, "Using library laptops", False,
             s[4] if len(s) > 4 else s[0], None,
             None, "Session in progress. Working on Python basics."),
        ]
        att_session_ids = []
        for eid, pid, name, sdate, status, qr, hc_mode, hc_total, checked, walks, pre, cards, qrs, cost, cost_notes, survey, opened, closed_by, closed_at, notes in sessions_data:
            r2 = await session.execute(text("""
                INSERT INTO attendance_sessions
                    (event_id, program_id, session_name, session_date, status, qr_code_token,
                     head_count_mode, head_count_total, total_checked_in, total_walk_ins,
                     total_pre_registered, total_card_scans, total_qr_scans,
                     event_cost, cost_notes, survey_enabled,
                     opened_by_id, closed_by_id, closed_at, notes)
                VALUES (:eid, :pid, :name, :sdate, :status, :qr, :hc_mode, :hc_total,
                        :checked, :walks, :pre, :cards, :qrs, :cost, :cost_notes, :survey,
                        :opened, :closed_by, :closed_at, :notes)
                RETURNING id
            """), {"eid": eid, "pid": pid, "name": name, "sdate": sdate, "status": status,
                   "qr": qr, "hc_mode": hc_mode, "hc_total": hc_total, "checked": checked,
                   "walks": walks, "pre": pre, "cards": cards, "qrs": qrs,
                   "cost": cost, "cost_notes": cost_notes, "survey": survey,
                   "opened": opened, "closed_by": closed_by, "closed_at": closed_at, "notes": notes})
            att_session_ids.append(r2.scalar())
        await session.flush()

        # Check-ins
        print("  Seeding attendance_check_ins...")
        asid = att_session_ids
        checkins = [
            (asid[0], p[5] if len(p) > 5 else all_ids[5], None, "card_scan",
             _past(20), s[2] if len(s) > 2 else s[0], "L30-0371", "child", True, 8, _d("2025-09-15"), "not_sent", None),
            (asid[0], None, "Maria Santos", "walk_in",
             _past(20), s[2] if len(s) > 2 else s[0], None, "adult", False, 0, _d("2026-03-15"), "not_sent",
             "First time visitor with two toddlers"),
            (asid[0], p[0] if len(p) > 0 else all_ids[0], None, "qr_scan",
             _past(20), None, "L30-0107", "adult", True, 12, _d("2025-06-01"), "not_sent", None),
            (asid[1], p[4] if len(p) > 4 else all_ids[4], None, "card_scan",
             _past(15), s[4] if len(s) > 4 else s[0], "L30-0391", "teen", True, 5, _d("2025-10-20"), "sent", None),
            (asid[1], p[3] if len(p) > 3 else all_ids[3], None, "card_scan",
             _past(15), s[4] if len(s) > 4 else s[0], "L30-0389", "teen", True, 3, _d("2025-12-01"), "sent", None),
            (asid[1], None, "Tyler Washington", "walk_in",
             _past(15), s[4] if len(s) > 4 else s[0], None, "teen", False, 0, _d("2026-03-20"), "sent",
             "Friend of Lilith, interested in joining book club"),
            (asid[2], p[1] if len(p) > 1 else all_ids[1], None, "card_scan",
             _past(10), s[3] if len(s) > 3 else s[0], "L30-0133", "adult", True, 10, _d("2025-04-15"), "not_sent", None),
            (asid[2], p[3] if len(p) > 3 else all_ids[3], None, "qr_scan",
             _past(10), None, "L30-0127", "adult", True, 7, _d("2025-07-01"), "not_sent", None),
            (asid[2], p[2] if len(p) > 2 else all_ids[2], None, "card_scan",
             _past(10), s[3] if len(s) > 3 else s[0], "L30-0105", "adult", True, 15, _d("2025-01-10"), "not_sent",
             "Suggested adding Colson Whitehead to next month reading list"),
            (asid[4], p[5] if len(p) > 5 else all_ids[5], None, "card_scan",
             _past(4), s[2] if len(s) > 2 else s[0], "L30-0371", "child", True, 9, _d("2025-09-15"), "not_sent",
             "Made a 3D printed bookmark of a dragon"),
        ]
        for sid, pid, guest, method, checked_at, checked_by, card, age, repeat, prev, first, survey, notes in checkins:
            await session.execute(text("""
                INSERT INTO attendance_check_ins
                    (session_id, patron_id, guest_name, check_in_method,
                     checked_in_at, checked_in_by_id, library_card_number,
                     age_range, is_repeat_attendee, previous_visit_count,
                     first_visit_date, survey_status, notes)
                VALUES (:sid, :pid, :guest, :method, :checked_at, :checked_by, :card,
                        :age, :repeat, :prev, :first, :survey, :notes)
            """), {"sid": sid, "pid": pid, "guest": guest, "method": method,
                   "checked_at": checked_at, "checked_by": checked_by, "card": card,
                   "age": age, "repeat": repeat, "prev": prev, "first": first,
                   "survey": survey, "notes": notes})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 13. BETA FEEDBACK
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM beta_feedback"))
    if r.scalar() == 0:
        print("  Seeding beta_feedback...")
        feedbacks = [
            ("bug", "resolved", "high", "Catalog search returns duplicate results",
             "When I search for Yellowface I get the same book listed twice with different covers. One has the hardcover jacket and one shows a plain binding.",
             "/catalog/search?q=yellowface", "Firefox 125 / macOS",
             p[0] if len(p) > 0 else all_ids[0], None,
             "Fixed in v2.4.1 - dedup logic added to search results",
             s[0], _past(27), _past(25)),
            ("suggestion", "reviewed", "medium", "Add reading history export",
             "It would be great to export my reading history as a CSV or PDF. I like to track my reading across different apps and this would help.",
             "/my-account/reading-history", "Chrome 124 / Windows 11",
             p[1] if len(p) > 1 else all_ids[1], None, None, None, None, _past(20)),
            ("confusion", "in_progress", "medium", "Hold pickup location unclear",
             "When I place a hold it does not clearly say where I pick it up. I drove to the wrong branch twice before realizing my holds go to the main library.",
             "/catalog/holds", "Safari 17 / iOS",
             p[2] if len(p) > 2 else all_ids[2], None,
             "UX team reviewing hold confirmation flow", None, None, _past(10)),
            ("praise", "resolved", "low", "Love the new dark mode",
             "The dark mode is so much easier on my eyes for evening browsing. Thank you for adding it!",
             "/settings/display", "Chrome 125 / macOS",
             p[4] if len(p) > 4 else all_ids[4], None, None, None, None, _past(7)),
            ("bug", "new", "high", "Event registration button unresponsive on mobile",
             "Tried to register for the Teen Book Club on my phone and the Register button does nothing when I tap it. Works fine on my laptop though.",
             "/events/16", "Chrome 124 / Android 14",
             p[3] if len(p) > 3 else all_ids[3], "jason.ashwood@email.com",
             None, None, None, _past(3)),
            ("suggestion", "new", "low", "Wish list or save for later feature",
             "I often browse the catalog and find books I want to read eventually but am not ready to place a hold on. A wish list would be perfect.",
             "/catalog", "Firefox 126 / Linux",
             p[3] if len(p) > 3 else all_ids[3], None, None, None, None, _past(1)),
        ]
        for ftype, status, priority, subject, desc, page, browser, submitted_by, email, admin_notes, resolved_by, resolved_at, updated in feedbacks:
            await session.execute(text("""
                INSERT INTO beta_feedback
                    (type, status, priority, subject, description, page_url,
                     browser_info, submitted_by_id, email, admin_notes,
                     resolved_by_id, resolved_at, updated_at)
                VALUES (:ftype, :status, :priority, :subject, :desc, :page,
                        :browser, :submitted_by, :email, :admin_notes,
                        :resolved_by, :resolved_at, :updated)
            """), {"ftype": ftype, "status": status, "priority": priority,
                   "subject": subject, "desc": desc, "page": page, "browser": browser,
                   "submitted_by": submitted_by, "email": email,
                   "admin_notes": admin_notes, "resolved_by": resolved_by,
                   "resolved_at": resolved_at, "updated": updated})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 14. CONTENT FLAGS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM content_flags"))
    if r.scalar() == 0:
        print("  Seeding content_flags...")
        flags = [
            (1, "event_review", "spam", 85,
             '{"reason": "Review contains promotional link to external product", "flagged_text": "Check out my blog for more..."}',
             "resolved", _past(40), _past(35)),
            (2, "event_review", "excessive_caps", 42,
             '{"reason": "32 percent of review text in all caps", "flagged_text": "THIS WAS THE BEST EVENT EVER"}',
             "false_positive", _past(30), _past(28)),
            (3, "event_review", "off_topic", 71,
             '{"reason": "Review discusses unrelated personal grievance", "flagged_text": "parking lot needs repaving"}',
             "pending", _past(5), _past(5)),
            (4, "event_review", "hate_speech", 92,
             '{"reason": "Review contains discriminatory language", "flagged_text": "[redacted]"}',
             "resolved", _past(20), _past(18)),
            (5, "event_review", "duplicate", 55,
             '{"reason": "Text is 90 percent similar to review 2 by same user", "original_review_id": 2}',
             "pending", _past(2), _past(2)),
        ]
        for rid, rtype, ftype, conf, details, status, created, updated in flags:
            await session.execute(text("""
                INSERT INTO content_flags
                    (review_id, review_type, flag_type, confidence_score,
                     analysis_details, status, created_at, updated_at)
                VALUES (:rid, :rtype, :ftype, :conf, cast(:details as jsonb), :status, :created, :updated)
            """), {"rid": rid, "rtype": rtype, "ftype": ftype, "conf": conf,
                   "details": details, "status": status, "created": created, "updated": updated})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 15. DAMAGED ITEMS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM damaged_items"))
    if r.scalar() == 0 and recovery_project_ids:
        print("  Seeding damaged_items...")
        rp = recovery_project_ids
        damaged = [
            (rp[0], 3 if 3 in item_copy_ids else item_copy_ids[0], "L30-154-001",
             "The Great Gatsby", "F. Scott Fitzgerald", "water damage", "severe",
             "Pages warped and stuck together from water exposure. Cover boards separating from spine. Mold beginning on interior pages.",
             "assessed", False, None, None, 15.99, "pending_replacement", _past(10), None,
             s[0], False, None),
            (rp[0], 4 if 4 in item_copy_ids else item_copy_ids[1] if len(item_copy_ids) > 1 else item_copy_ids[0],
             "L30-155-001", "Where the Crawdads Sing", "Delia Owens", "torn pages", "moderate",
             "Pages 45 through 52 torn along the gutter. Appears to be from rough handling rather than intentional damage.",
             "assessed", True, "page repair with tissue", 8.5, 18.99, "in_repair", _past(7), None,
             s[4] if len(s) > 4 else s[0], False, None),
            (rp[0], 5 if 5 in item_copy_ids else item_copy_ids[2] if len(item_copy_ids) > 2 else item_copy_ids[0],
             "L30-111-001", "Diary of a Wimpy Kid", "Jeff Kinney", "spine damage", "moderate",
             "Spine cracked in multiple places. Pages loose but all present. Common wear pattern for heavily circulated juvenile titles.",
             "assessed", True, "spine rebinding", 12, 10.99, "pending_decision", _past(5), None,
             s[4] if len(s) > 4 else s[0], False, None),
            (rp[1] if len(rp) > 1 else rp[0],
             6 if 6 in item_copy_ids else item_copy_ids[3] if len(item_copy_ids) > 3 else item_copy_ids[0],
             "L30-031-001", "Yellowface", "R.F. Kuang", "staining", "minor",
             "Coffee stain on pages 120 through 125. Text still readable. Cover has minor discoloration on back.",
             "pending", True, "cleaning", 3, 27.99, None, None, None, None, False, None),
            (rp[1] if len(rp) > 1 else rp[0],
             1 if 1 in item_copy_ids else item_copy_ids[0],
             "L30-152-001", "The Midnight Library", "Matt Haig", "binding failure", "severe",
             "Perfect binding has completely failed. Text block separated from cover. Pages falling out in sections.",
             "assessed", False, None, None, 16.99, "pending_replacement", _past(2), None,
             s[0], True, 16.99),
        ]
        for pid, iid, barcode, title, author, dtype, dsev, ddesc, astatus, salv, smethod, ecost, rcost, rstatus, dassessed, drecovered, assessed_by, claim, camount in damaged:
            await session.execute(text("""
                INSERT INTO damaged_items
                    (project_id, item_id, item_barcode, title, author, damage_type,
                     damage_severity, damage_description, assessment_status, is_salvageable,
                     salvage_method, estimated_repair_cost, replacement_cost, recovery_status,
                     date_assessed, date_recovered, assessed_by_id, included_in_claim, claim_amount)
                VALUES (:pid, :iid, :barcode, :title, :author, :dtype, :dsev, :ddesc,
                        :astatus, :salv, :smethod, :ecost, :rcost, :rstatus,
                        :dassessed, :drecovered, :assessed_by, :claim, :camount)
            """), {"pid": pid, "iid": iid, "barcode": barcode, "title": title,
                   "author": author, "dtype": dtype, "dsev": dsev, "ddesc": ddesc,
                   "astatus": astatus, "salv": salv, "smethod": smethod, "ecost": ecost,
                   "rcost": rcost, "rstatus": rstatus, "dassessed": dassessed,
                   "drecovered": drecovered, "assessed_by": assessed_by,
                   "claim": claim, "camount": camount})
        await session.flush()

    # FIX SEQUENCES
    seq_tables = [
        "skills", "committees", "committee_members",
        "strategic_budgets", "budget_allocations", "budget_items", "budget_transactions",
        "ill_cost_records", "ill_tracking_updates", "serial_titles", "serial_subscriptions",
        "transit_requests", "transit_shipments", "transit_shipment_items",
        "repair_records", "import_jobs", "volunteer_shifts", "volunteer_references",
        "attendance_sessions", "attendance_check_ins",
        "beta_feedback", "content_flags", "damaged_items",
    ]
    for table in seq_tables:
        try:
            async with session.begin_nested():
                await session.execute(text(
                    f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
                ))
        except SQLAlchemyError:
            pass

    await session.flush()
    print("  Operations batch seeding complete!")
    return True
