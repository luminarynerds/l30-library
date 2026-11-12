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


async def seed_batch_staff(session: AsyncSession) -> bool:

    # Grab reusable IDs
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    all_ids = [u[0] for u in users]

    branches_r = await session.execute(text("SELECT id, name FROM branches"))
    branches = branches_r.fetchall()
    branch_names = [b[1] for b in branches]

    vol_r = await session.execute(text("SELECT id FROM volunteers"))
    volunteer_ids = [r[0] for r in vol_r.fetchall()]

    tt_r = await session.execute(text("SELECT id FROM training_types"))
    training_type_ids = [r[0] for r in tt_r.fetchall()]

    now = datetime.now(utc)

    # ════════════════════════════════════════════════════════════════
    # 1. TRAINING COMPLETIONS (teacher_training_modules FK)
    # ════════════════════════════════════════════════════════════════
    # training_completions requires teacher_training_modules.
    # Seed modules first if empty, then completions.
    r = await session.execute(text("SELECT COUNT(*) FROM teacher_training_modules"))
    ttm_count = r.scalar()
    if ttm_count == 0:
        # Need outreach_partners for FK
        op_r = await session.execute(text("SELECT id FROM outreach_partners LIMIT 1"))
        partner_row = op_r.fetchone()
        if partner_row:
            partner_id = partner_row[0]
            print("  Seeding teacher_training_modules (prerequisite)...")
            modules = [
                ("Early Literacy Best Practices", "Techniques for fostering literacy in pre-K through 2nd grade", "reading-strategies", "beginner", 60),
                ("Guided Reading Workshop", "Structured approach to guided reading groups", "reading-strategies", "intermediate", 90),
                ("Engaging Reluctant Readers", "Strategies for motivating reluctant and struggling readers", "engagement", "intermediate", 75),
                ("Reading Assessment Tools", "Using formative and summative reading assessments effectively", "assessment", "advanced", 120),
                ("Digital Reading Resources", "Leveraging ebooks and digital platforms for reading instruction", "technology", "beginner", 45),
                ("Phonics Refresher for Teachers", "Updated phonics instruction methods and materials", "reading-strategies", "beginner", 60),
                ("Book Club Facilitation", "Running effective student book clubs and literature circles", "engagement", "intermediate", 60),
                ("Reading Across the Curriculum", "Integrating reading skills into science, math, and social studies", "reading-strategies", "advanced", 90),
            ]
            for title, desc, cat, level, dur in modules:
                await session.execute(text("""
                    INSERT INTO teacher_training_modules (partner_id, title, description, category, level, duration_minutes, is_active, created_at)
                    VALUES (:pid, :title, :desc, :cat, :level, :dur, true, :now)
                """), {"pid": partner_id, "title": title, "desc": desc, "cat": cat, "level": level, "dur": dur, "now": now})
            print(f"    Created {len(modules)} training modules")
            await session.commit()

    # Now seed training_completions
    r = await session.execute(text("SELECT COUNT(*) FROM training_completions"))
    if r.scalar() == 0:
        mod_r = await session.execute(text("SELECT id FROM teacher_training_modules"))
        module_ids = [r[0] for r in mod_r.fetchall()]
        if module_ids and staff_ids:
            print("  Seeding training_completions...")
            count = 0
            used = set()
            for _ in range(40):
                mid = random.choice(module_ids)
                uid = random.choice(staff_ids)
                if (mid, uid) in used:
                    continue
                used.add((mid, uid))
                days_ago = random.randint(10, 300)
                status = random.choice(["completed", "completed", "completed", "in_progress", "certified"])
                completed = status in ("completed", "certified")
                score = random.randint(70, 100) if completed else None
                started = _past(days_ago)
                finished = _past(days_ago - random.randint(1, 7)) if completed else None
                await session.execute(text("""
                    INSERT INTO training_completions (module_id, user_id, started_at, completed_at, status, quiz_score, passed_assessment)
                    VALUES (:mid, :uid, :started, :completed, :status, :score, :passed)
                """), {
                    "mid": mid, "uid": uid, "started": started, "completed": finished,
                    "status": status, "score": score, "passed": completed,
                })
                count += 1
            print(f"    Created {count} training completions")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 2. TRAINING RECORDS (volunteer training history)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM training_records"))
    if r.scalar() == 0 and volunteer_ids and training_type_ids:
        print("  Seeding training_records...")
        statuses = ["not_started", "in_progress", "completed", "completed", "completed", "overdue"]
        count = 0
        used = set()
        for vid in volunteer_ids:
            num = random.randint(2, 5)
            for ttid in random.sample(training_type_ids, min(len(training_type_ids), num)):
                if (vid, ttid) in used:
                    continue
                used.add((vid, ttid))
                status = random.choice(statuses)
                days_ago = random.randint(30, 365)
                assigned = _past(days_ago)
                started = _past(days_ago - random.randint(1, 10)) if status != "not_started" else None
                completed = _past(days_ago - random.randint(11, 30)) if status == "completed" else None
                due = _past(days_ago - 60)
                expires = _past_date(-365) if status == "completed" else None
                score = round(random.uniform(70, 100), 1) if status == "completed" else None
                trainer = random.choice(staff_ids) if status == "completed" else None
                notes = "Completed successfully" if status == "completed" else None
                await session.execute(text("""
                    INSERT INTO training_records (volunteer_id, training_type_id, status, assigned_at, started_at,
                        completed_at, due_at, expires_at, trainer_id, completion_notes, score, renewal_required, last_renewal_date)
                    VALUES (:vid, :ttid, :status, :assigned, :started, :completed, :due, :expires,
                        :trainer, :notes, :score, :renewal, :renewal_date)
                """), {
                    "vid": vid, "ttid": ttid, "status": status, "assigned": assigned,
                    "started": started, "completed": completed, "due": due,
                    "expires": expires, "trainer": trainer, "notes": notes,
                    "score": score, "renewal": random.choice([True, False]),
                    "renewal_date": _past_date(random.randint(30, 200)) if status == "completed" else None,
                })
                count += 1
        print(f"    Created {count} training records")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 3. STAFF CERTIFICATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM staff_certifications"))
    if r.scalar() == 0 and staff_ids:
        print("  Seeding staff_certifications...")
        certs = [
            ("cpr_first_aid", "CPR & First Aid", "American Red Cross", True, 24),
            ("cpr_first_aid", "CPR/AED Certification", "American Heart Association", True, 24),
            ("food_handler", "Food Handler Certificate", "County Health Department", True, 36),
            ("mental_health_training", "Mental Health First Aid", "National Council for Mental Wellbeing", True, 36),
            ("background_check", "Background Check Clearance", "State Bureau of Investigation", False, None),
            ("mandatory_reporter", "Mandatory Reporter Training", "State Department of Human Services", True, 12),
            ("accessibility_training", "ADA Accessibility Training", "ADA National Network", True, 24),
            ("data_protection", "Data Protection & Privacy", "LYRASIS", True, 12),
            ("library_mls", "Master of Library Science", "State University", False, None),
            ("library_mls", "MLIS Degree", "Graduate School of Library Studies", False, None),
            ("specialized_skill", "Notary Public Commission", "Secretary of State", True, 48),
            ("specialized_skill", "Grant Writing Certificate", "Foundation Center", False, None),
            ("specialized_skill", "Youth Services Specialist", "State Library Association", True, 36),
            ("specialized_skill", "Archives Management Certificate", "Society of American Archivists", False, None),
            ("specialized_skill", "Digital Media Certification", "Adobe", True, 24),
        ]
        count = 0
        used = set()
        for cert_type, cert_name, issuer, renewal, freq in certs:
            uid = random.choice(staff_ids)
            key = (uid, cert_type, issuer)
            if key in used:
                continue
            used.add(key)
            days_ago = random.randint(30, 900)
            obtained = _past_date(days_ago)
            expiry = _past_date(days_ago - (freq * 30)) if renewal and freq else None
            verifier = random.choice(staff_ids)
            cred_num = f"CERT-{random.randint(10000, 99999)}" if random.random() > 0.3 else None
            await session.execute(text("""
                INSERT INTO staff_certifications (user_id, organization_id, certification_type, certification_name,
                    issuing_organization, obtained_date, expiration_date, is_active, renewal_required,
                    renewal_frequency_months, next_renewal_due, renewal_in_progress,
                    credential_number, verified, verified_by_id, verified_date, notes)
                VALUES (:uid, 1, :cert_type, :cert_name, :issuer, :obtained, :expiry, true,
                    :renewal, :freq, :next_due, false, :cred_num, true, :verifier, :verified_date, :notes)
            """), {
                "uid": uid, "cert_type": cert_type, "cert_name": cert_name, "issuer": issuer,
                "obtained": obtained, "expiry": expiry,
                "renewal": renewal, "freq": freq,
                "next_due": expiry if renewal and expiry else None,
                "cred_num": cred_num,
                "verifier": verifier, "verified_date": _past_date(days_ago - 5),
                "notes": None,
            })
            count += 1
        print(f"    Created {count} staff certifications")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 4. PROFESSIONAL DEVELOPMENT PLANS + ACTIVITIES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM professional_development_plans"))
    if r.scalar() == 0 and staff_ids:
        print("  Seeding professional_development_plans & activities...")
        plans_data = [
            ("Youth Services Leadership Development", "Develop leadership skills to manage youth services department",
             '["leadership", "community_engagement"]', '["Attend ALA Youth Services conference", "Shadow department heads"]',
             2500.00, 800.00, 2026),
            ("Digital Literacy Specialist Track", "Build expertise in digital literacy instruction and ebook technology",
             '["technical_skills", "innovation"]', '["Complete digital literacy instructor cert", "Attend EdTech conference"]',
             1500.00, 350.00, 2026),
            ("Community Engagement & Outreach", "Strengthen community partnership and outreach programming skills",
             '["community_engagement", "personal_growth"]', '["Visit partner libraries", "Develop new outreach program"]',
             2000.00, 600.00, 2026),
            ("Cataloging & Metadata Standards", "Advance cataloging expertise with focus on linked data and RDA",
             '["technical_skills", "subject_expertise"]', '["Complete RDA toolkit training", "Join NACO funnel"]',
             1200.00, 200.00, 2026),
            ("Archives & Special Collections", "Develop skills in archival processing and digital preservation",
             '["subject_expertise", "technical_skills"]', '["SAA DAS certification", "Digital preservation workshop"]',
             1800.00, 0.00, 2026),
            ("Management & Supervision Skills", "Prepare for supervisory role with focus on staff development",
             '["leadership", "personal_growth"]', '["Supervisory skills workshop", "Mentoring program"]',
             2200.00, 450.00, 2025),
            ("Reference & Research Services", "Deepen reference interview and research consultation skills",
             '["subject_expertise", "community_engagement"]', '["Advanced reference webinar series", "Database training"]',
             800.00, 300.00, 2025),
            ("Inclusive Services Development", "Build cultural competency and inclusive service delivery skills",
             '["community_engagement", "personal_growth"]', '["DEI certificate program", "Community listening sessions"]',
             1600.00, 500.00, 2026),
        ]
        plan_ids = []
        plan_staff = []
        # Ensure unique (staff_id, plan_year) to satisfy uq_staff_dev_plan_year
        used_staff_year = set()
        for title, goals, focus, planned, budget, used_budget, year in plans_data:
            # Pick a staff member not yet used for this year
            available = [s for s in staff_ids if (s, year) not in used_staff_year]
            if not available:
                continue
            sid = random.choice(available)
            used_staff_year.add((sid, year))
            r2 = await session.execute(text("""
                INSERT INTO professional_development_plans (staff_id, organization_id, title, career_goals,
                    focus_areas, planned_activities, annual_budget, budget_used, plan_year, is_active,
                    last_review_date, review_notes)
                VALUES (:sid, 1, :title, :goals, cast(:focus as jsonb), cast(:planned as jsonb),
                    :budget, :used, :year, true, :review_date, :review_notes)
                RETURNING id
            """), {
                "sid": sid, "title": title, "goals": goals,
                "focus": focus, "planned": planned,
                "budget": budget, "used": used_budget, "year": year,
                "review_date": _past(random.randint(10, 60)),
                "review_notes": "Making good progress on planned activities" if random.random() > 0.3 else None,
            })
            pid = r2.scalar()
            plan_ids.append(pid)
            plan_staff.append(sid)

        # Activities for each plan
        activity_templates = [
            ("ALA Annual Conference", "Attended panels on youth engagement and collection development", "conference", "community_engagement", 24.0, 1200.00, "ALA"),
            ("Advanced Cataloging with RDA", "Online course covering RDA metadata standards", "course", "technical_skills", 40.0, 350.00, "Library Juice Academy"),
            ("De-escalation Workshop", "Half-day workshop on patron conflict resolution", "workshop", "personal_growth", 4.0, 75.00, "County HR Training"),
            ("Reading Group: Radical Cataloging", "Staff reading and discussion group on critical cataloging", "reading", "subject_expertise", 8.0, 0.00, None),
            ("Peer Mentoring Circle", "Monthly peer learning group on reference services", "peer_learning", "community_engagement", 12.0, 0.00, None),
            ("Mentoring New Cataloger", "One-on-one mentoring of newly hired cataloging assistant", "mentoring", "leadership", 20.0, 0.00, None),
            ("State Library Association Talk", "Presented on digital literacy programming for seniors", "presentation", "innovation", 8.0, 150.00, "State Library Association"),
            ("Grant Writing Basics", "Online course on writing competitive library grants", "course", "technical_skills", 16.0, 200.00, "GrantStation"),
            ("Digital Preservation Workshop", "Two-day workshop on born-digital archiving", "workshop", "technical_skills", 16.0, 500.00, "Digital Preservation Coalition"),
            ("EdTech Conference", "Technology in education conference", "conference", "innovation", 16.0, 800.00, "ISTE"),
            ("Project: Seed Library Expansion", "Led project to expand community seed library", "project_based", "community_engagement", 30.0, 0.00, None),
            ("Cultural Competency Certificate", "12-week online certificate program", "certification", "personal_growth", 48.0, 400.00, "University Extension"),
        ]
        activity_count = 0
        for i, pid in enumerate(plan_ids):
            sid = plan_staff[i]
            num_activities = random.randint(2, 4)
            chosen = random.sample(activity_templates, num_activities)
            for title, desc, atype, cat, hours, cost, provider in chosen:
                days_ago = random.randint(5, 200)
                completed = random.random() > 0.3
                await session.execute(text("""
                    INSERT INTO professional_development_activities (plan_id, staff_id, title, description,
                        activity_type, category, start_date, end_date, hours_spent, cost, approved,
                        completed, completion_date, reflection, provider, certificate_earned)
                    VALUES (:pid, :sid, :title, :desc, :atype, :cat, :start, :end, :hours, :cost,
                        true, :completed, :comp_date, :reflection, :provider, :cert)
                """), {
                    "pid": pid, "sid": sid, "title": title, "desc": desc,
                    "atype": atype, "cat": cat,
                    "start": _past(days_ago),
                    "end": _past(days_ago - random.randint(1, 14)) if completed else None,
                    "hours": hours if completed else round(hours * random.uniform(0.2, 0.6), 1),
                    "cost": cost, "completed": completed,
                    "comp_date": _past(days_ago - random.randint(1, 14)) if completed else None,
                    "reflection": "Very valuable experience, learned practical skills I can apply immediately." if completed and random.random() > 0.4 else None,
                    "provider": provider, "cert": completed and random.random() > 0.5,
                })
                activity_count += 1
        print(f"    Created {len(plan_ids)} plans, {activity_count} activities")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 5. STAFF EXPERTISE
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM staff_expertise"))
    if r.scalar() == 0 and staff_ids:
        print("  Seeding staff_expertise...")
        expertise_data = [
            ("Youth Services", "Programming for children and teens, early literacy, summer reading", "expert", 12, True, True),
            ("Cataloging & Classification", "MARC records, RDA, Dewey Decimal, subject headings", "advanced", 8, False, True),
            ("Reference Services", "Research consultation, database searching, readers advisory", "proficient", 5, True, True),
            ("Digital Media", "Ebook platforms, digital audiobooks, streaming services", "advanced", 6, True, True),
            ("Community Outreach", "Partnership development, pop-up libraries, bookmobile services", "proficient", 4, True, False),
            ("Genealogy Research", "Census records, vital records, DNA analysis, local history", "expert", 15, True, True),
            ("Makerspace Technology", "3D printing, laser cutting, CNC routing, vinyl cutting", "advanced", 3, False, True),
            ("Grant Writing", "Federal and state library grants, LSTA, foundation proposals", "proficient", 7, False, True),
            ("Collection Development", "Selection, weeding, vendor negotiations, collection assessment", "expert", 10, True, True),
            ("Accessibility Services", "Assistive technology, WCAG compliance, inclusive programming", "proficient", 4, True, True),
            ("Interlibrary Loan", "ILL protocols, OCLC WorldShare, copyright compliance", "advanced", 6, False, True),
            ("Spanish Language Services", "Bilingual programming, Spanish collection development", "advanced", 8, True, True),
        ]
        count = 0
        used = set()
        sample_staff = random.sample(staff_ids, min(len(staff_ids), 10))
        for i, sid in enumerate(sample_staff):
            num = random.randint(1, 3)
            choices = random.sample(expertise_data, num)
            for domain, desc, level, years, mentor, consult in choices:
                if (sid, domain) in used:
                    continue
                used.add((sid, domain))
                creds = json.dumps(["MLS", "State Certification"]) if random.random() > 0.5 else "[]"
                await session.execute(text("""
                    INSERT INTO staff_expertise (staff_id, organization_id, domain, description, level,
                        relevant_credentials, years_experience, willing_to_mentor, willing_to_train,
                        willing_to_consult, is_public)
                    VALUES (:sid, 1, :domain, :desc, :level, cast(:creds as jsonb), :years,
                        :mentor, :train, :consult, true)
                """), {
                    "sid": sid, "domain": domain, "desc": desc, "level": level,
                    "creds": creds, "years": years,
                    "mentor": mentor, "train": random.choice([True, False]),
                    "consult": consult,
                })
                count += 1
        print(f"    Created {count} staff expertise records")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 6. STAFF BIOS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM staff_bios"))
    if r.scalar() == 0 and staff_ids:
        print("  Seeding staff_bios...")
        bios = [
            ("Stevie Leigh", "Assistant Director", "Stevie oversees technology infrastructure, AI projects, digital collections, and the Makerspace. She is all about bringing libraries into the future with approachable, patron-centered tech.", "Once organized a 24-hour read-a-thon that raised $12,000 for new children's books.", "Pachinko by Min Jin Lee", 15),
            ("David Okonkwo", "Head of Circulation", "David manages our circulation operations with warmth and efficiency. He's the friendly face that greets you at the desk and the logistics expert who keeps materials flowing between branches.", "Can identify any regular patron by their library card number alone.", "The Fifth Season by N.K. Jemisin", 8),
            ("Susan Park", "Youth Services Librarian", "Susan creates magical experiences for our youngest patrons through storytime, summer reading programs, and STEAM workshops. She believes every child deserves a librarian who champions their curiosity.", "Has performed over 500 storytimes and still gets nervous before each one.", "Last Stop on Market Street by Matt de la Pena", 12),
            ("Tom Rodriguez", "Reference Librarian", "Tom is our resident research guru. Whether you need help tracing your family tree, finding a scholarly article, or navigating government resources, Tom will find the answer.", "Solved a genealogy mystery that reunited a family separated for 40 years.", "Moby-Dick by Herman Melville", 10),
            ("Angela Brooks", "Technical Services Manager", "Angela keeps our catalog accurate and our collections organized. She's passionate about metadata standards and making sure every item is discoverable.", "Has cataloged over 50,000 items in her career and remembers most of them.", "The Library Book by Susan Orlean", 14),
            ("Janice Kim", "Children's Librarian", "Janice brings boundless energy to the children's room. From puppet shows to coding clubs, she creates programming that makes learning irresistible for kids of all ages.", "Built a life-size cardboard castle in the children's room that took three weeks to complete.", "Where the Wild Things Are by Maurice Sendak", 6),
            ("Robert Franklin", "Digital Services Librarian", "Robert bridges the digital divide in our community. He teaches computer classes, manages our ebook collection, and ensures our technology resources serve everyone.", "Built the library's first website in 1998 using Notepad.", "Ready Player One by Ernest Cline", 9),
            ("Maria Santos", "Community Outreach Coordinator", "Maria takes the library beyond its walls. She manages our bookmobile, builds partnerships with schools and community organizations, and ensures underserved populations can access library services.", "Has driven the bookmobile over 30,000 miles across the county.", "The House on Mango Street by Sandra Cisneros", 7),
            ("Patricia Hughes", "Local History Librarian", "Patricia is the guardian of our community's memory. She manages our local history collection, digitization projects, and helps patrons uncover the stories of their families and neighborhoods.", "Discovered a lost diary from 1892 that changed the town's founding story.", "The Personal Librarian by Marie Benedict", 18),
            ("James Wilson", "Makerspace Coordinator", "James runs our award-winning makerspace, teaching patrons everything from 3D printing to woodworking. He believes libraries should be places where people create, not just consume.", "3D-printed a working prosthetic hand for a community member.", "The Martian by Andy Weir", 4),
        ]
        sample_staff = random.sample(staff_ids, min(len(staff_ids), len(bios)))
        for i, (name, role, bio, fun, fav_book, years) in enumerate(bios):
            if i >= len(sample_staff):
                break
            await session.execute(text("""
                INSERT INTO staff_bios (staff_name, role, bio, fun_fact, favorite_book,
                    years_of_service, is_visible, sort_order, user_id, created_at, updated_at)
                VALUES (:name, :role, :bio, :fun, :fav, :years, true, :order, :uid, :now, :now)
            """), {
                "name": name, "role": role, "bio": bio, "fun": fun, "fav": fav_book,
                "years": years, "order": (i + 1) * 10, "uid": sample_staff[i], "now": now,
            })
        print(f"    Created {min(len(sample_staff), len(bios))} staff bios")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 7. STAFF CHECKINS (requires threat_alerts)
    # ════════════════════════════════════════════════════════════════
    # staff_checkins requires threat_alert_id (NOT NULL FK to threat_alerts).
    # Create a drill threat alert first if none exist.
    r = await session.execute(text("SELECT COUNT(*) FROM staff_checkins"))
    if r.scalar() == 0 and staff_ids:
        ta_r = await session.execute(text("SELECT id FROM threat_alerts LIMIT 1"))
        ta_row = ta_r.fetchone()
        if not ta_row:
            print("  Seeding threat_alerts (prerequisite for staff_checkins)...")
            # Create 2 resolved drill alerts
            drills = [
                ("other", "all_clear", "Fire drill — annual safety drill conducted successfully", 1),
                ("structural_emergency", "all_clear", "Severe weather shelter drill — tornado warning test", 1),
                ("other", "all_clear", "Lockdown drill — quarterly security exercise", 2),
            ]
            drill_ids = []
            for ttype, tlevel, desc, branch_id in drills:
                r2 = await session.execute(text("""
                    INSERT INTO threat_alerts (threat_type, threat_level, branch_id, description,
                        dispatch_called, lockdown_initiated, total_staff_expected, staff_checked_in,
                        staff_checked_in_safe, staff_unaccounted, children_present, children_count,
                        created_at)
                    VALUES (:ttype, :tlevel, :bid, :desc, false, false, :total, :checked, :safe, 0,
                        false, 0, :created)
                    RETURNING id
                """), {
                    "ttype": ttype, "tlevel": tlevel, "bid": branch_id, "desc": desc,
                    "total": len(staff_ids), "checked": len(staff_ids), "safe": len(staff_ids),
                    "created": _past(random.randint(30, 180)),
                })
                drill_ids.append(r2.scalar())
            await session.commit()
            print(f"    Created {len(drill_ids)} threat alert drills")
        else:
            ta_r2 = await session.execute(text("SELECT id FROM threat_alerts"))
            drill_ids = [r[0] for r in ta_r2.fetchall()]

        # Now create staff check-ins
        print("  Seeding staff_checkins...")
        count = 0
        locations = ["Main desk", "Children's room", "Staff break room", "Reference area",
                      "Back office", "Meeting room A", "Parking lot", "Second floor"]
        for ta_id in drill_ids:
            check_staff = random.sample(staff_ids, min(len(staff_ids), random.randint(8, 15)))
            for uid in check_staff:
                await session.execute(text("""
                    INSERT INTO staff_checkins (threat_alert_id, user_id, is_safe, location, notes,
                        checked_in_at, updated_at)
                    VALUES (:ta_id, :uid, true, :loc, :notes, :checked, :checked)
                """), {
                    "ta_id": ta_id, "uid": uid, "loc": random.choice(locations),
                    "notes": random.choice([None, "All clear", "Sheltering in place", "Evacuated safely"]),
                    "checked": _past(random.randint(30, 180)),
                })
                count += 1
        print(f"    Created {count} staff check-ins")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 8. RECOGNITION AWARDS (volunteer recognition)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM recognition_awards"))
    if r.scalar() == 0 and volunteer_ids:
        print("  Seeding recognition_awards...")
        awards = [
            ("Volunteer of the Month - January", "award", "Exceptional dedication during winter reading program", "Recognized at staff meeting"),
            ("Volunteer of the Month - March", "award", "Outstanding contribution to the seed library garden beds", "Certificate presented at board meeting"),
            ("100 Hours Service Award", "certificate", "Reached 100 cumulative volunteer hours milestone", "Certificate and pin ceremony"),
            ("250 Hours Service Award", "certificate", "Reached 250 cumulative volunteer hours — quarter-millennium!", "Award presented at annual volunteer appreciation dinner"),
            ("Outstanding Shelving Award", "badge", "Maintained perfect shelving accuracy for 6 months straight", "Badge added to volunteer profile"),
            ("Community Impact Award", "public_recognition", "Led ESL conversation circles that served 40+ community members", "Featured in library newsletter and social media"),
            ("Summer Reading Champion", "certificate", "Recruited and mentored 15 teen summer reading volunteers", "Certificate at summer reading finale event"),
            ("Innovation Award", "award", "Developed the volunteer scheduling app that improved shift coverage by 30%", "Recognized at annual awards ceremony"),
            ("Peer Appreciation", "thank_you_email", "Nominated by fellow volunteers for always being helpful and positive", "Personal thank-you from library director"),
            ("Youth Mentor of the Year", "public_recognition", "Mentored 8 teen volunteers through the teen advisory board program", "Featured on library website and local newspaper"),
            ("Event Setup Hero", "badge", "Set up and broke down 25+ events without a single complaint", "Badge and gift card"),
            ("Digital Literacy Champion", "certificate", "Helped 50+ seniors learn basic computer and internet skills", "Certificate and library tote bag"),
        ]
        for award_name, award_type, reason, presentation in awards:
            vid = random.choice(volunteer_ids)
            await session.execute(text("""
                INSERT INTO recognition_awards (volunteer_id, award_name, award_type, description,
                    reason, awarded_at, awarded_by_id, presentation_details, public_announcement)
                VALUES (:vid, :name, :atype, :desc, :reason, :awarded, :awarded_by, :presentation, :public)
            """), {
                "vid": vid, "name": award_name, "atype": award_type,
                "desc": reason, "reason": reason,
                "awarded": _past(random.randint(5, 300)),
                "awarded_by": random.choice(staff_ids),
                "presentation": presentation,
                "public": award_type in ("public_recognition", "award"),
            })
        print(f"    Created {len(awards)} recognition awards")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 9. EOD TEMPLATES + SESSIONS + TASKS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM eod_templates"))
    if r.scalar() == 0 and staff_ids:
        print("  Seeding eod_templates, sessions & tasks...")

        templates_data = [
            ("Main Branch Closing", "Standard end-of-day closing procedure for main branch", "Main Branch", 25,
             json.dumps([
                 {"task_type": "close_registers", "required": True, "display_name": "Close Cash Registers"},
                 {"task_type": "process_holds", "required": True, "display_name": "Process Outstanding Holds"},
                 {"task_type": "send_overdue_notices", "required": True, "display_name": "Send Overdue Notices"},
                 {"task_type": "backup_confirmation", "required": True, "display_name": "Confirm System Backup"},
                 {"task_type": "security_check", "required": True, "display_name": "Security Walkthrough"},
                 {"task_type": "statistics_summary", "required": False, "display_name": "Daily Statistics Summary"},
                 {"task_type": "tomorrow_events", "required": False, "display_name": "Review Tomorrow Events"},
             ])),
            ("Branch Closing - Standard", "Standard closing procedure for branch locations", "Elmdale Branch", 20,
             json.dumps([
                 {"task_type": "close_registers", "required": True, "display_name": "Close Cash Drawer"},
                 {"task_type": "process_holds", "required": True, "display_name": "Process Holds"},
                 {"task_type": "security_check", "required": True, "display_name": "Security Check"},
                 {"task_type": "backup_confirmation", "required": True, "display_name": "Confirm Backup"},
                 {"task_type": "statistics_summary", "required": False, "display_name": "Daily Stats"},
             ])),
            ("Weekend Closing - Extended", "Extended closing procedure for weekend shifts", "Main Branch", 35,
             json.dumps([
                 {"task_type": "close_registers", "required": True, "display_name": "Close All Registers"},
                 {"task_type": "process_holds", "required": True, "display_name": "Process Weekend Holds"},
                 {"task_type": "send_overdue_notices", "required": True, "display_name": "Weekend Overdue Batch"},
                 {"task_type": "holds_pull_list", "required": True, "display_name": "Monday Holds Pull List"},
                 {"task_type": "backup_confirmation", "required": True, "display_name": "Weekend Backup"},
                 {"task_type": "security_check", "required": True, "display_name": "Full Security Walkthrough"},
                 {"task_type": "statistics_summary", "required": True, "display_name": "Weekend Summary"},
                 {"task_type": "tomorrow_events", "required": True, "display_name": "Monday Events Preview"},
             ])),
        ]

        template_ids = []
        template_branches = []
        for name, desc, branch, dur, configs in templates_data:
            r2 = await session.execute(text("""
                INSERT INTO eod_templates (name, description, branch_location, is_active,
                    estimated_duration_minutes, task_configs, created_by_id)
                VALUES (:name, :desc, :branch, true, :dur, cast(:configs as json), :creator)
                RETURNING id
            """), {
                "name": name, "desc": desc, "branch": branch, "dur": dur,
                "configs": configs, "creator": random.choice(staff_ids),
            })
            tid = r2.scalar()
            template_ids.append(tid)
            template_branches.append(branch)

        # Sessions
        session_ids = []
        session_count = 0
        for day_offset in range(20):
            template_idx = random.randint(0, len(template_ids) - 1)
            tid = template_ids[template_idx]
            branch = template_branches[template_idx]
            closing_dt = _past(day_offset)
            closing_d = closing_dt.date()
            code = f"EOD-{closing_d.isoformat()}-{branch[:4].upper()}"
            status = "completed" if day_offset > 0 else "in_progress"
            started = closing_dt.replace(hour=20, minute=30)
            completed = closing_dt.replace(hour=20, minute=55) if status == "completed" else None
            total_tasks = random.randint(5, 8)
            completed_tasks = total_tasks if status == "completed" else random.randint(2, total_tasks - 1)
            failed = random.randint(0, 1) if status == "completed" else 0
            skipped = random.randint(0, 1)
            stats = json.dumps({"total_checkouts": random.randint(80, 200), "total_checkins": random.randint(70, 190), "holds_placed": random.randint(5, 30)})
            r2 = await session.execute(text("""
                INSERT INTO eod_sessions (session_code, template_id, branch_location, closing_date,
                    staff_id, status, started_at, completed_at, total_duration_seconds,
                    total_tasks, completed_tasks, failed_tasks, skipped_tasks,
                    backup_status, security_checks, statistics_summary, notes)
                VALUES (:code, :tid, :branch, :date, :staff, :status, :started, :completed,
                    :duration, :total, :done, :failed, :skipped, :backup,
                    cast(:security as json), cast(:stats as json), :notes)
                RETURNING id
            """), {
                "code": code, "tid": tid, "branch": branch, "date": closing_d,
                "staff": random.choice(staff_ids), "status": status,
                "started": started, "completed": completed,
                "duration": random.randint(900, 2100) if status == "completed" else None,
                "total": total_tasks, "done": completed_tasks, "failed": failed, "skipped": skipped,
                "backup": "success" if status == "completed" else "pending",
                "security": json.dumps([{"check": "doors", "passed": True}, {"check": "alarm", "passed": True}]),
                "stats": stats,
                "notes": random.choice([None, "Smooth closing tonight", "Had to wait for last patron to leave", "Register 2 was short $0.50"]),
            })
            sid = r2.scalar()
            session_ids.append(sid)
            session_count += 1

        # Tasks for each session
        task_templates = [
            ("close_registers", "Close Cash Registers"),
            ("process_holds", "Process Outstanding Holds"),
            ("send_overdue_notices", "Send Overdue Notices"),
            ("backup_confirmation", "Confirm System Backup"),
            ("security_check", "Security Walkthrough"),
            ("statistics_summary", "Daily Statistics Summary"),
            ("tomorrow_events", "Review Tomorrow Events"),
            ("holds_pull_list", "Generate Holds Pull List"),
        ]
        task_count = 0
        for sess_id in session_ids:
            num_tasks = random.randint(4, 7)
            chosen_tasks = random.sample(task_templates, num_tasks)
            for task_type, display in chosen_tasks:
                t_status = random.choice(["completed", "completed", "completed", "skipped"])
                t_started = _past(random.randint(0, 20))
                t_completed = t_started + timedelta(minutes=random.randint(1, 10)) if t_status == "completed" else None
                task_data_val = json.dumps({"auto": True}) if random.random() > 0.5 else None
                await session.execute(text("""
                    INSERT INTO eod_tasks (session_id, task_type, display_name, status, task_data,
                        started_at, completed_at, duration_seconds, assigned_to_id, completed_by_id, skip_reason)
                    VALUES (:sess, :ttype, :display, :status, cast(:data as json), :started, :completed,
                        :duration, :assigned, :completed_by, :skip)
                """), {
                    "sess": sess_id, "ttype": task_type, "display": display, "status": t_status,
                    "data": task_data_val,
                    "started": t_started, "completed": t_completed,
                    "duration": random.randint(30, 600) if t_status == "completed" else None,
                    "assigned": random.choice(staff_ids),
                    "completed_by": random.choice(staff_ids) if t_status == "completed" else None,
                    "skip": "Not applicable today" if t_status == "skipped" else None,
                })
                task_count += 1
        print(f"    Created {len(template_ids)} templates, {session_count} sessions, {task_count} tasks")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 10. CHECK-IN SESSIONS + RESULTS (book return check-in)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM check_in_sessions"))
    if r.scalar() == 0 and staff_ids:
        print("  Seeding check_in_sessions & results...")
        ci_session_ids = []
        for i in range(10):
            days_ago = random.randint(1, 60)
            branch = random.choice(branch_names)
            code = f"CI-{_past_date(days_ago).isoformat()}-{i+1:03d}"
            total_items = random.randint(8, 40)
            successful = total_items - random.randint(0, 3)
            holds = random.randint(0, 5)
            transits = random.randint(0, 3)
            exceptions = random.randint(0, 2)
            started = _past(days_ago).replace(hour=random.randint(9, 17))
            ended = started + timedelta(minutes=random.randint(10, 60))
            r2 = await session.execute(text("""
                INSERT INTO check_in_sessions (session_code, branch_location, workstation_id, staff_id,
                    status, started_at, ended_at, use_backdating, total_items, successful_checkins,
                    holds_trapped, transits_created, exceptions_count)
                VALUES (:code, :branch, :ws, :staff, 'completed', :started, :ended, false,
                    :total, :success, :holds, :transits, :exceptions)
                RETURNING id
            """), {
                "code": code, "branch": branch,
                "ws": f"WS-{random.randint(1,4):02d}",
                "staff": random.choice(staff_ids),
                "started": started, "ended": ended,
                "total": total_items, "success": successful,
                "holds": holds, "transits": transits, "exceptions": exceptions,
            })
            ci_session_ids.append(r2.scalar())

        # Results for each session
        result_count = 0
        for sess_id in ci_session_ids:
            num_results = random.randint(5, 15)
            for j in range(num_results):
                barcode = f"3900{random.randint(10000000, 99999999)}"
                status = random.choice(["checked_in", "checked_in", "checked_in", "hold_trapped", "transit", "exception"])
                was_overdue = random.random() < 0.15
                overdue_days = random.randint(1, 30) if was_overdue else 0
                fine = round(overdue_days * 0.25, 2) if was_overdue else 0
                sort_dest = random.choice(["shelving", "shelving", "holds_shelf", "transit", "repair"])
                await session.execute(text("""
                    INSERT INTO check_in_results (session_id, barcode, status, sort_destination,
                        checked_in_at, was_overdue, overdue_days, fine_amount,
                        condition_checked, condition_status)
                    VALUES (:sess, :barcode, :status, :dest, :checked, :overdue, :days,
                        :fine, :cond_checked, :cond_status)
                """), {
                    "sess": sess_id, "barcode": barcode, "status": status, "dest": sort_dest,
                    "checked": _past(random.randint(1, 60)),
                    "overdue": was_overdue, "days": overdue_days, "fine": fine,
                    "cond_checked": random.choice([True, False]),
                    "cond_status": random.choice(["good", "good", "good", "fair", "needs_repair"]),
                })
                result_count += 1
        print(f"    Created {len(ci_session_ids)} check-in sessions, {result_count} results")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 11. ONBOARDING CHECKLISTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM onboarding_checklists"))
    if r.scalar() == 0 and staff_ids:
        print("  Seeding onboarding_checklists...")
        checklists = [
            ("New Circulation Staff Onboarding", "Complete onboarding checklist for new circulation desk staff",
             [
                 {"id": "tour", "title": "Building Tour", "description": "Tour all areas including staff-only spaces", "due_days": 1, "completed": True, "completed_at": "2026-01-15"},
                 {"id": "ils_training", "title": "ILS System Training", "description": "Complete ILS circulation module training", "due_days": 5, "completed": True, "completed_at": "2026-01-20"},
                 {"id": "desk_shadow", "title": "Shadow Circulation Desk", "description": "Shadow experienced staff for two full shifts", "due_days": 7, "completed": True, "completed_at": "2026-01-22"},
                 {"id": "policies", "title": "Read Circulation Policies", "description": "Read and acknowledge all circulation policies", "due_days": 3, "completed": True, "completed_at": "2026-01-18"},
                 {"id": "cash_drawer", "title": "Cash Drawer Training", "description": "Learn opening/closing cash drawer procedures", "due_days": 5, "completed": True, "completed_at": "2026-01-20"},
                 {"id": "solo_shift", "title": "First Solo Shift", "description": "Complete first independent shift at circulation desk", "due_days": 14, "completed": True, "completed_at": "2026-01-29"},
             ], True),
            ("New Youth Services Staff Onboarding", "Onboarding for youth services librarians and assistants",
             [
                 {"id": "tour", "title": "Building & Children's Area Tour", "description": "Tour with focus on youth services spaces and emergency exits", "due_days": 1, "completed": True, "completed_at": "2026-02-10"},
                 {"id": "child_safety", "title": "Child Safety Training", "description": "Complete mandatory child safety and mandatory reporter training", "due_days": 3, "completed": True, "completed_at": "2026-02-13"},
                 {"id": "storytime_observe", "title": "Observe Storytime", "description": "Observe three storytime sessions led by experienced staff", "due_days": 7, "completed": True, "completed_at": "2026-02-17"},
                 {"id": "collection_review", "title": "Collection Orientation", "description": "Review children's and YA collection organization and displays", "due_days": 5, "completed": False, "completed_at": None},
                 {"id": "programming", "title": "Program Planning Meeting", "description": "Meet with youth services team to discuss upcoming programs", "due_days": 10, "completed": False, "completed_at": None},
             ], False),
            ("General Staff Onboarding - All Departments", "Universal onboarding tasks for all new staff members",
             [
                 {"id": "hr_paperwork", "title": "HR Paperwork", "description": "Complete all HR forms, direct deposit, benefits enrollment", "due_days": 1, "completed": True, "completed_at": "2026-03-01"},
                 {"id": "badge", "title": "Staff ID Badge", "description": "Photo taken and badge issued by facilities", "due_days": 2, "completed": True, "completed_at": "2026-03-02"},
                 {"id": "email", "title": "Email Account Setup", "description": "Set up library email and learn communication protocols", "due_days": 1, "completed": True, "completed_at": "2026-03-01"},
                 {"id": "handbook", "title": "Employee Handbook Review", "description": "Read employee handbook and sign acknowledgment", "due_days": 5, "completed": True, "completed_at": "2026-03-05"},
                 {"id": "safety", "title": "Safety Training", "description": "Complete fire, weather, and emergency procedure training", "due_days": 7, "completed": False, "completed_at": None},
                 {"id": "tech_training", "title": "Technology Orientation", "description": "Login credentials, phone system, copier, staff intranet", "due_days": 3, "completed": False, "completed_at": None},
                 {"id": "meet_greet", "title": "Meet & Greet", "description": "Introduction to all department heads and key staff", "due_days": 3, "completed": True, "completed_at": "2026-03-03"},
             ], False),
        ]
        for title, desc, items, is_completed in checklists:
            uid = random.choice(staff_ids)
            assigner = random.choice(staff_ids)
            start = _past(random.randint(10, 90))
            completed_date = _past(random.randint(1, 9)) if is_completed else None
            await session.execute(text("""
                INSERT INTO onboarding_checklists (user_id, title, description, checklist_items,
                    is_completed, start_date, completed_date, assigned_by_id, created_at, updated_at)
                VALUES (:uid, :title, :desc, cast(:items as json), :done, :start, :completed,
                    :assigner, :now, :now)
            """), {
                "uid": uid, "title": title, "desc": desc,
                "items": json.dumps(items),
                "done": is_completed, "start": start, "completed": completed_date,
                "assigner": assigner, "now": now,
            })
        print(f"    Created {len(checklists)} onboarding checklists")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 12. INTRODUCTION ANNOUNCEMENTS (requires staff_onboarding)
    # ════════════════════════════════════════════════════════════════
    # introduction_announcements requires onboarding_id FK to staff_onboarding.
    # Create staff_onboarding records first if none exist.
    r = await session.execute(text("SELECT COUNT(*) FROM introduction_announcements"))
    if r.scalar() == 0 and staff_ids:
        onb_r = await session.execute(text("SELECT id FROM staff_onboarding LIMIT 1"))
        onb_row = onb_r.fetchone()
        if not onb_row:
            print("  Seeding staff_onboarding (prerequisite for announcements)...")
            onboarding_staff = random.sample(staff_ids, min(len(staff_ids), 4))
            onb_ids = []
            departments = ["Circulation", "Youth Services", "Reference", "Technical Services"]
            positions = ["Library Assistant", "Youth Services Librarian", "Reference Librarian", "Cataloger"]
            for i, uid in enumerate(onboarding_staff):
                dept = departments[i % len(departments)]
                pos = positions[i % len(positions)]
                start_d = _past_date(random.randint(30, 120))
                expected = start_d + timedelta(days=90)
                manager = random.choice([s for s in staff_ids if s != uid])
                buddy = random.choice([s for s in staff_ids if s != uid and s != manager])
                r2 = await session.execute(text("""
                    INSERT INTO staff_onboarding (user_id, status, start_date, expected_completion_date,
                        department, position, manager_id, buddy_mentor_id, buddy_mentor_assigned_at,
                        probation_status, progress_percentage, all_policies_acknowledged, all_systems_provisioned)
                    VALUES (:uid, 'completed', :start, :expected, :dept, :pos, :mgr, :buddy, :buddy_at,
                        'passed', 100, true, true)
                    RETURNING id
                """), {
                    "uid": uid, "start": start_d, "expected": expected,
                    "dept": dept, "pos": pos, "mgr": manager, "buddy": buddy,
                    "buddy_at": _past(random.randint(30, 120)),
                })
                onb_ids.append(r2.scalar())
            await session.commit()
            print(f"    Created {len(onb_ids)} staff onboarding records")
        else:
            onb_r2 = await session.execute(text("SELECT id FROM staff_onboarding"))
            onb_ids = [r[0] for r in onb_r2.fetchall()]

        # Now create announcements
        print("  Seeding introduction_announcements...")
        announcements = [
            ("Welcome Priya Sharma to Youth Services!", "Please join us in welcoming Priya Sharma to the Youth Services team! Priya comes to us from the Metro City Public Library where she spent 3 years developing innovative teen programming. She holds an MLS from the University of Illinois and is passionate about graphic novels, STEAM education, and making the library a welcoming space for all young people. Stop by the children's room to say hello!", "all_staff"),
            ("New Staff: Marcus Johnson, Circulation", "We are excited to introduce Marcus Johnson, who has joined our circulation team at the Main Branch. Marcus brings 5 years of customer service experience and is already impressing everyone with his warmth and efficiency at the desk. Fun fact: Marcus is an avid tabletop gamer and is hoping to start a board game club at the library!", "email"),
            ("Introducing Dr. Amara Obi, Reference", "Please welcome Dr. Amara Obi to our reference department. Dr. Obi recently completed her PhD in Information Science and specializes in digital humanities and open access resources. She will be taking over our database instruction program and is eager to help patrons with research consultations.", "bulletin"),
            ("Welcome to the Team: Sofia Reyes", "Our technical services department has a new member! Sofia Reyes joins us as a cataloger with specialized expertise in Spanish-language materials and multilingual cataloging. Sofia previously worked at the National Library of Mexico and will be instrumental in expanding our Spanish collection. Bienvenida, Sofia!", "all_staff"),
        ]
        for i, (title, content, atype) in enumerate(announcements):
            onb_id = onb_ids[i % len(onb_ids)]
            creator = random.choice(staff_ids)
            sched_date = _past_date(random.randint(10, 90))
            await session.execute(text("""
                INSERT INTO introduction_announcements (onboarding_id, title, content, announcement_type,
                    scheduled_date, distributed_to, created_by_id, published_at, published_by_id)
                VALUES (:onb_id, :title, :content, :atype, :sched,
                    '{"all_staff","department"}'::varchar[], :creator, :published, :publisher)
            """), {
                "onb_id": onb_id, "title": title, "content": content, "atype": atype,
                "sched": sched_date, "creator": creator,
                "published": _past(random.randint(10, 90)),
                "publisher": creator,
            })
        print(f"    Created {len(announcements)} introduction announcements")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # FIX SEQUENCES
    # ════════════════════════════════════════════════════════════════
    seq_tables = [
        "teacher_training_modules", "training_completions", "training_records",
        "staff_certifications", "professional_development_plans",
        "professional_development_activities", "staff_expertise", "staff_bios",
        "threat_alerts", "staff_checkins", "recognition_awards",
        "eod_templates", "eod_sessions", "eod_tasks",
        "check_in_sessions", "check_in_results",
        "onboarding_checklists", "staff_onboarding", "introduction_announcements",
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
    print("  Staff batch seeding complete!")
    return True
