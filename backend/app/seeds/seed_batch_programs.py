# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import random
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

utc = timezone.utc


def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago, hours=random.randint(0, 8))


def _future(days_ahead: int) -> datetime:
    return datetime.now(utc) + timedelta(days=days_ahead)


def _past_date(days_ago: int) -> date:
    return (date.today() - timedelta(days=days_ago))


def _future_date(days_ahead: int) -> date:
    return (date.today() + timedelta(days=days_ahead))


async def _count(session, table: str) -> int:
    r = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
    return r.scalar()


async def _fix_sequence(session, table: str):
    await session.execute(text(
        f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
        f"COALESCE((SELECT MAX(id) FROM {table}), 1))"
    ))


async def seed_batch_programs(session: AsyncSession) -> bool:

    try:
        # ====================================================================
        # Fetch existing IDs for FK references
        # ====================================================================
        users_r = await session.execute(text("SELECT id, role FROM users ORDER BY id"))
        users = users_r.fetchall()
        if not users:
            print("ERROR: No users found. Run bootstrap seed first.")
            return False

        patron_ids = [u[0] for u in users if u[1] in ("patron",)]
        child_ids = [u[0] for u in users if u[1] in ("child",)]
        staff_ids = [u[0] for u in users if u[1] in ("staff", "admin", "super_admin", "director")]
        all_user_ids = [u[0] for u in users]

        branches_r = await session.execute(text("SELECT id FROM branches ORDER BY id"))
        branch_ids = [b[0] for b in branches_r.fetchall()]

        volunteers_r = await session.execute(text("SELECT id FROM volunteers ORDER BY id"))
        volunteer_ids = [v[0] for v in volunteers_r.fetchall()]

        teen_vol_r = await session.execute(text("SELECT id FROM teen_volunteers ORDER BY id"))
        teen_volunteer_ids = [t[0] for t in teen_vol_r.fetchall()]

        partners_r = await session.execute(text("SELECT id FROM outreach_partners ORDER BY id"))
        partner_ids = [p[0] for p in partners_r.fetchall()]

        # Track all tables we touch for sequence fix
        tables_touched = []

        # ====================================================================
        # 1. PROGRAMS + PROGRAM_REGISTRATIONS + PROGRAM_STATISTICS
        # ====================================================================
        if await _count(session, "programs") == 0:
            print("  Seeding programs...")

            programs_data = [
                ("Toddler Storytime", "Interactive stories, songs, and fingerplays for ages 0-3 with caregivers.", "storytime", "children", 25, True, "completed", 60),
                ("Preschool STEAM Explorers", "Science experiments and building activities for ages 3-5.", "stem", "children", 20, True, "completed", 45),
                ("Teen Code Club", "Learn Python and web development. Laptops provided.", "technology", "teen", 15, True, "completed", 90),
                ("Senior Tech Help", "One-on-one help with smartphones, tablets, and computers.", "technology", "senior", 10, False, "completed", 60),
                ("Adult Book Discussion", "Monthly fiction discussion group for adults.", "book_club", "adult", 20, True, "completed", 90),
                ("Family Craft Night", "Seasonal craft projects for all ages. Materials provided.", "arts_crafts", "family", 30, True, "completed", 60),
                ("Author Visit: Local Writers", "Local authors read from their works and sign books.", "lecture", "all_ages", 50, True, "completed", 120),
                ("ESL Conversation Practice", "Casual English practice in small groups.", "educational", "adult", 12, False, "in_progress", 60),
                ("Summer Reading Kickoff Party", "Games, prizes, and sign-ups for summer reading.", "reading_program", "all_ages", 100, False, "scheduled", 180),
                ("Homework Help Hour", "After-school tutoring for grades 3-8.", "educational", "children", 15, False, "scheduled", 60),
            ]

            for i, (title, desc, ptype, audience, cap, reg_req, status, dur_min) in enumerate(programs_data):
                days_offset = random.randint(5, 90) if status == "completed" else -random.randint(5, 30)
                prog_date = _past_date(days_offset) if status == "completed" else _future_date(-days_offset)
                start_hr = random.choice([10, 11, 13, 14, 15, 16])
                start_t = time(start_hr, 0)
                end_t = time(start_hr + dur_min // 60, dur_min % 60)
                actual_att = random.randint(cap // 2, cap) if status == "completed" else 0
                branch = random.choice(branch_ids) if branch_ids else None

                await session.execute(text("""
                    INSERT INTO programs (
                        title, description, program_type, audience, program_date,
                        start_time, end_time, branch_id, location_name, is_virtual,
                        max_capacity, registration_required, expected_attendance,
                        actual_attendance, status, facilitator_id, facilitator_name,
                        registered_count, attended_count, notes, created_by_id
                    ) VALUES (
                        :title, :desc, :ptype, :audience, :prog_date,
                        :start_time, :end_time, :branch_id, :location, :is_virtual,
                        :max_cap, :reg_req, :expected_att,
                        :actual_att, :status, :facilitator_id, :facilitator_name,
                        :reg_count, :att_count, :notes, :created_by_id
                    )
                """), {
                    "title": title, "desc": desc, "ptype": ptype, "audience": audience,
                    "prog_date": prog_date, "start_time": start_t, "end_time": end_t,
                    "branch_id": branch, "location": "Main Branch - Community Room",
                    "is_virtual": False, "max_cap": cap, "reg_req": reg_req,
                    "expected_att": cap, "actual_att": actual_att,
                    "status": status, "facilitator_id": random.choice(staff_ids),
                    "facilitator_name": None, "reg_count": actual_att if status == "completed" else 0,
                    "att_count": actual_att, "notes": None,
                    "created_by_id": random.choice(staff_ids),
                })

            await session.commit()
            tables_touched.append("programs")
            print(f"    -> {await _count(session, 'programs')} programs created")

            # Program registrations
            print("  Seeding program_registrations...")
            progs_r = await session.execute(text(
                "SELECT id, status, max_capacity FROM programs ORDER BY id"
            ))
            all_programs = progs_r.fetchall()
            reg_count = 0

            for prog_id, prog_status, max_cap in all_programs:
                if prog_status not in ("completed", "in_progress"):
                    continue
                num_regs = random.randint(3, min(8, max_cap or 8))
                chosen_patrons = random.sample(patron_ids, min(num_regs, len(patron_ids)))
                for pid in chosen_patrons:
                    attended = prog_status == "completed" and random.random() > 0.15
                    reg_status = "attended" if attended else ("registered" if prog_status != "completed" else "no_show")
                    await session.execute(text("""
                        INSERT INTO program_registrations (
                            program_id, patron_id, status, attended,
                            attended_at, age_group, resident_status, notes
                        ) VALUES (
                            :prog_id, :patron_id, :status, :attended,
                            :attended_at, :age_group, :resident_status, :notes
                        )
                    """), {
                        "prog_id": prog_id, "patron_id": pid, "status": reg_status,
                        "attended": attended,
                        "attended_at": _past(random.randint(5, 60)) if attended else None,
                        "age_group": random.choice(["children_0_5", "children_6_12", "teen_13_18", "adult_19_64", "senior_65_plus"]),
                        "resident_status": "resident",
                        "notes": None,
                    })
                    reg_count += 1

            await session.commit()
            tables_touched.append("program_registrations")
            print(f"    -> {reg_count} program registrations created")

            # Program statistics
            print("  Seeding program_statistics...")
            today = date.today()
            for months_ago in range(3):
                period_start = date(today.year, today.month - months_ago - 1 if today.month - months_ago - 1 > 0 else 12 + (today.month - months_ago - 1), 1)
                if today.month - months_ago - 1 <= 0:
                    period_start = period_start.replace(year=today.year - 1)
                period_end = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

                events_by_cat = json.dumps({"storytime": random.randint(8, 12), "book_club": random.randint(2, 4), "technology": random.randint(3, 6), "arts_crafts": random.randint(2, 4)})
                events_by_age = json.dumps({"children": random.randint(10, 15), "teen": random.randint(4, 8), "adult": random.randint(5, 10), "senior": random.randint(2, 5)})
                att_by_cat = json.dumps({"storytime": random.randint(150, 250), "book_club": random.randint(30, 60), "technology": random.randint(40, 80), "arts_crafts": random.randint(30, 60)})
                att_by_age = json.dumps({"children": random.randint(200, 300), "teen": random.randint(50, 100), "adult": random.randint(80, 150), "senior": random.randint(20, 50)})
                total_progs = random.randint(20, 35)
                total_att = random.randint(350, 600)

                await session.execute(text("""
                    INSERT INTO program_statistics (
                        period_start, period_end, period_type, branch_location,
                        events_by_category, events_by_age_group,
                        attendance_by_category, attendance_by_age_group,
                        total_programs_offered, total_program_attendance,
                        avg_attendance_per_program,
                        childrens_programs_count, childrens_program_attendance,
                        young_adult_programs_count, young_adult_program_attendance,
                        adult_programs_count, adult_program_attendance,
                        outreach_programs_count, outreach_program_attendance,
                        virtual_programs_count, virtual_program_attendance,
                        reading_program_participants, reading_program_completions,
                        generated_by_id, notes
                    ) VALUES (
                        :p_start, :p_end, :p_type, :branch_loc,
                        cast(:ebc as jsonb), cast(:eba as jsonb),
                        cast(:abc as jsonb), cast(:aba as jsonb),
                        :total_progs, :total_att,
                        :avg_att,
                        :child_progs, :child_att,
                        :ya_progs, :ya_att,
                        :adult_progs, :adult_att,
                        :outreach_progs, :outreach_att,
                        :virtual_progs, :virtual_att,
                        :rp_participants, :rp_completions,
                        :gen_by, :notes
                    )
                """), {
                    "p_start": period_start, "p_end": period_end,
                    "p_type": "monthly", "branch_loc": "Main Branch",
                    "ebc": events_by_cat, "eba": events_by_age,
                    "abc": att_by_cat, "aba": att_by_age,
                    "total_progs": total_progs, "total_att": total_att,
                    "avg_att": round(total_att / max(total_progs, 1), 2),
                    "child_progs": random.randint(8, 12), "child_att": random.randint(150, 250),
                    "ya_progs": random.randint(3, 6), "ya_att": random.randint(40, 80),
                    "adult_progs": random.randint(5, 10), "adult_att": random.randint(60, 120),
                    "outreach_progs": random.randint(1, 3), "outreach_att": random.randint(20, 50),
                    "virtual_progs": random.randint(2, 5), "virtual_att": random.randint(30, 70),
                    "rp_participants": random.randint(50, 100), "rp_completions": random.randint(20, 60),
                    "gen_by": random.choice(staff_ids), "notes": None,
                })

            await session.commit()
            tables_touched.append("program_statistics")
            print(f"    -> {await _count(session, 'program_statistics')} program statistics created")
        else:
            print("  programs already seeded, skipping")

        # ====================================================================
        # 2. PROGRAM_TEMPLATES + PROGRAM_PLANS
        # ====================================================================
        if await _count(session, "program_templates") == 0:
            print("  Seeding program_templates...")

            templates_data = [
                ("Storytime Standard", "Standard weekly storytime for toddlers/preschool", "storytime", "children", "storytime", 30, 25, True, 150.00, 2),
                ("STEM Workshop", "Hands-on STEM activity for school-age kids", "stem", "children", "stem", 60, 20, True, 300.00, 3),
                ("Tech Help Drop-In", "Open tech help for seniors/adults", "technology", "adult", "technology", 120, 10, False, 50.00, 1),
                ("Author Event Template", "Author visit with reading, Q&A, and signing", "community", "all_ages", "lecture", 120, 50, True, 500.00, 4),
                ("Book Club Monthly", "Monthly book discussion group", "book_club", "adult", "book_club", 90, 20, True, 75.00, 0),
            ]

            equip_options = [
                json.dumps(["projector", "microphone"]),
                json.dumps(["craft supplies", "tables"]),
                json.dumps(["laptops", "chargers"]),
                json.dumps(["whiteboard", "markers"]),
                json.dumps([]),
            ]
            vol_roles_options = [
                json.dumps(["setup", "registration_desk", "cleanup"]),
                json.dumps(["registration_desk"]),
                json.dumps(["tech_setup", "cleanup"]),
                json.dumps([]),
            ]
            success_options = [
                json.dumps({"min_attendance": 15, "satisfaction_target": 4.0}),
                json.dumps({"min_attendance": 10, "satisfaction_target": 3.5}),
                json.dumps({"min_attendance": 20, "satisfaction_target": 4.5}),
            ]

            for i, (name, desc, category, target_aud, prog_type, dur, cap, reg_req, budget, vols) in enumerate(templates_data):
                await session.execute(text("""
                    INSERT INTO program_templates (
                        name, description, category, target_audience, program_type,
                        default_duration_minutes, recommended_capacity, registration_required,
                        room_type_needed, equipment_needed, estimated_budget,
                        marketing_lead_days, volunteers_needed, volunteer_roles_needed,
                        success_metrics, target_attendance, is_active, times_used,
                        created_by_id
                    ) VALUES (
                        :name, :desc, :category, :target_aud, :prog_type,
                        :dur, :cap, :reg_req,
                        :room_type, cast(:equipment as jsonb), :budget,
                        :mkt_days, :vols, cast(:vol_roles as jsonb),
                        cast(:success as jsonb), :target_att, :is_active, :times_used,
                        :created_by
                    )
                """), {
                    "name": name, "desc": desc, "category": category,
                    "target_aud": target_aud, "prog_type": prog_type,
                    "dur": dur, "cap": cap, "reg_req": reg_req,
                    "room_type": "meeting_room", "equipment": equip_options[i % len(equip_options)],
                    "budget": budget, "mkt_days": 14, "vols": vols,
                    "vol_roles": vol_roles_options[i % len(vol_roles_options)],
                    "success": success_options[i % len(success_options)],
                    "target_att": cap, "is_active": True, "times_used": random.randint(1, 10),
                    "created_by": random.choice(staff_ids),
                })

            await session.commit()
            tables_touched.append("program_templates")
            print(f"    -> {await _count(session, 'program_templates')} program templates created")

            # Program plans (link to existing programs)
            print("  Seeding program_plans...")
            progs_for_plans = await session.execute(text("SELECT id FROM programs LIMIT 4"))
            plan_prog_ids = [r[0] for r in progs_for_plans.fetchall()]
            templates_r = await session.execute(text("SELECT id FROM program_templates LIMIT 5"))
            template_ids = [r[0] for r in templates_r.fetchall()]

            for i, prog_id in enumerate(plan_prog_ids):
                tmpl_id = template_ids[i % len(template_ids)] if template_ids else None
                await session.execute(text("""
                    INSERT INTO program_plans (
                        program_id, template_id, planning_notes,
                        planning_complete, total_budget, total_spent,
                        created_by_id
                    ) VALUES (
                        :prog_id, :tmpl_id, :notes,
                        :complete, :budget, :spent,
                        :created_by
                    )
                """), {
                    "prog_id": prog_id, "tmpl_id": tmpl_id,
                    "notes": "Standard program plan from template",
                    "complete": True, "budget": random.uniform(100, 500),
                    "spent": random.uniform(50, 400),
                    "created_by": random.choice(staff_ids),
                })

            await session.commit()
            tables_touched.append("program_plans")
            print(f"    -> {await _count(session, 'program_plans')} program plans created")
        else:
            print("  program_templates already seeded, skipping")

        # ====================================================================
        # 3. CULTURAL_PROGRAMS + CULTURAL_PROGRAM_REGISTRATIONS
        # ====================================================================
        if await _count(session, "cultural_programs") == 0:
            print("  Seeding cultural_programs...")

            cultural_data = [
                ("Dia de los Muertos Celebration", "Community celebration with altar building, face painting, and pan de muerto.", "celebration", "Mexican/Chicano", _past_date(140), True, True, 75, "Main Branch - Community Room", "Spanish", "Mexican Cultural Society"),
                ("Lunar New Year Festival", "Ring in the Year of the Snake with lion dances, calligraphy, and dumplings.", "festival", "Chinese/East Asian", _past_date(50), True, True, 100, "Main Branch - Community Room", "Mandarin", "Asian Community Center"),
                ("Juneteenth Reading and Celebration", "Poetry readings, music, and storytelling honoring African American heritage.", "celebration", "African American", _future_date(90), True, True, 60, "Main Branch - Community Room", "English", "NAACP Local Chapter"),
                ("Diwali Lights Festival", "Festival of lights with rangoli art, henna, and Indian sweets.", "festival", "South Asian/Indian", _future_date(200), True, True, 80, "Main Branch - Community Room", "Hindi", "India Association"),
            ]

            for title, desc, ptype, culture, evt_date, family, in_person, expected, location, lang, partner in cultural_data:
                actual = random.randint(expected // 2, expected) if evt_date < date.today() else None
                status = "completed" if evt_date < date.today() else "planned"
                await session.execute(text("""
                    INSERT INTO cultural_programs (
                        title, description, program_type, culture_featured,
                        organizer_name, organizer_email, event_date, event_time,
                        location, is_virtual, is_in_person,
                        expected_attendance, actual_attendance, budget,
                        partners_involved, languages_featured,
                        is_family_friendly, registration_required, status,
                        contact_email
                    ) VALUES (
                        :title, :desc, :ptype, :culture,
                        :org_name, :org_email, :evt_date, :evt_time,
                        :location, :is_virtual, :is_in_person,
                        :expected, :actual, :budget,
                        :partners, :languages,
                        :family, :reg_req, :status,
                        :contact_email
                    )
                """), {
                    "title": title, "desc": desc, "ptype": ptype, "culture": culture,
                    "org_name": partner, "org_email": f"info@{partner.lower().replace(' ', '')}.org",
                    "evt_date": evt_date, "evt_time": "14:00",
                    "location": location, "is_virtual": False, "is_in_person": in_person,
                    "expected": expected, "actual": actual,
                    "budget": random.uniform(200, 800),
                    "partners": [partner],
                    "languages": [lang, "English"],
                    "family": family, "reg_req": True, "status": status,
                    "contact_email": f"cultural@library.org",
                })

            await session.commit()
            tables_touched.append("cultural_programs")
            print(f"    -> {await _count(session, 'cultural_programs')} cultural programs created")

            # Cultural program registrations
            print("  Seeding cultural_program_registrations...")
            cult_progs_r = await session.execute(text("SELECT id, status FROM cultural_programs ORDER BY id"))
            cult_progs = cult_progs_r.fetchall()
            cult_reg_count = 0

            for cp_id, cp_status in cult_progs:
                num_regs = random.randint(5, 12)
                chosen = random.sample(patron_ids, min(num_regs, len(patron_ids)))
                for pid in chosen:
                    reg_status = random.choice(["attended", "attended", "no_show"]) if cp_status == "completed" else "registered"
                    await session.execute(text("""
                        INSERT INTO cultural_program_registrations (
                            program_id, patron_id, registration_date,
                            party_size, status, notes
                        ) VALUES (
                            :prog_id, :patron_id, :reg_date,
                            :party_size, :status, :notes
                        )
                    """), {
                        "prog_id": cp_id, "patron_id": pid,
                        "reg_date": _past_date(random.randint(1, 30)),
                        "party_size": random.randint(1, 4),
                        "status": reg_status, "notes": None,
                    })
                    cult_reg_count += 1

            await session.commit()
            tables_touched.append("cultural_program_registrations")
            print(f"    -> {cult_reg_count} cultural program registrations created")
        else:
            print("  cultural_programs already seeded, skipping")

        # ====================================================================
        # 4. VOLUNTEER HOUR LOGS, MILESTONES, COMMUNICATIONS, SCHEDULES
        #    volunteer_hour_logs + volunteer_schedules FK -> delivery_volunteers
        #    volunteer_milestones + volunteer_communications FK -> volunteers
        # ====================================================================
        # Create delivery volunteers if needed (FK target for hour_logs/schedules)
        delivery_vol_r = await session.execute(text("SELECT id FROM delivery_volunteers ORDER BY id"))
        delivery_vol_ids = [d[0] for d in delivery_vol_r.fetchall()]

        if not delivery_vol_ids and patron_ids:
            print("  Creating delivery_volunteers for FK references...")
            chosen_patrons = random.sample(patron_ids, min(4, len(patron_ids)))
            for pid in chosen_patrons:
                await session.execute(text("""
                    INSERT INTO delivery_volunteers (
                        user_id, status, phone, has_vehicle, vehicle_type,
                        background_check_completed, training_completed,
                        available_days, max_deliveries_per_day,
                        total_deliveries, total_volunteer_hours, recognition_level
                    ) VALUES (
                        :user_id, :status, :phone, :has_vehicle, :vehicle_type,
                        :bg_check, :training,
                        :avail_days, :max_del,
                        :total_del, :total_hours, :recog
                    )
                """), {
                    "user_id": pid, "status": "active",
                    "phone": f"555-01{random.randint(10,99)}",
                    "has_vehicle": True, "vehicle_type": random.choice(["sedan", "SUV", "minivan"]),
                    "bg_check": True, "training": True,
                    "avail_days": ["Monday", "Wednesday", "Friday"],
                    "max_del": 5, "total_del": random.randint(10, 50),
                    "total_hours": random.uniform(20, 100), "recog": "silver",
                })
            await session.commit()
            tables_touched.append("delivery_volunteers")
            delivery_vol_r = await session.execute(text("SELECT id FROM delivery_volunteers ORDER BY id"))
            delivery_vol_ids = [d[0] for d in delivery_vol_r.fetchall()]
            print(f"    -> {len(delivery_vol_ids)} delivery volunteers created")

        # Volunteer hour logs (FK -> delivery_volunteers)
        if await _count(session, "volunteer_hour_logs") == 0 and delivery_vol_ids:
            print("  Seeding volunteer_hour_logs...")
            activity_types = ["delivery", "training", "meeting", "other"]
            for _ in range(30):
                await session.execute(text("""
                    INSERT INTO volunteer_hour_logs (
                        volunteer_id, date, hours, activity_type, notes,
                        verified, verified_by_id, verified_at
                    ) VALUES (
                        :vol_id, :log_date, :hours, :activity, :notes,
                        :verified, :verified_by, :verified_at
                    )
                """), {
                    "vol_id": random.choice(delivery_vol_ids),
                    "log_date": _past_date(random.randint(1, 180)),
                    "hours": round(random.uniform(1, 4), 1),
                    "activity": random.choice(activity_types),
                    "notes": random.choice([None, "Regular delivery route", "Holiday schedule", "Training session"]),
                    "verified": True,
                    "verified_by": random.choice(staff_ids),
                    "verified_at": _past(random.randint(1, 30)),
                })
            await session.commit()
            tables_touched.append("volunteer_hour_logs")
            print(f"    -> {await _count(session, 'volunteer_hour_logs')} volunteer hour logs created")
        else:
            print("  volunteer_hour_logs already seeded (or no delivery_volunteers), skipping")

        # Volunteer milestones (FK -> volunteers)
        if await _count(session, "volunteer_milestones") == 0 and volunteer_ids:
            print("  Seeding volunteer_milestones...")
            milestone_types = ["hours_25", "hours_50", "hours_100", "shifts_10", "years_1"]
            for vid in volunteer_ids:
                num_milestones = random.randint(1, 2)
                chosen_types = random.sample(milestone_types, num_milestones)
                for mt in chosen_types:
                    val_map = {"hours_25": 25, "hours_50": 50, "hours_100": 100, "shifts_10": 10, "years_1": 1}
                    await session.execute(text("""
                        INSERT INTO volunteer_milestones (
                            volunteer_id, milestone_type, achieved_at,
                            achievement_value, celebration_message,
                            staff_recognition, public_recognition
                        ) VALUES (
                            :vol_id, :mtype, :achieved_at,
                            :value, :msg,
                            :staff_recog, :public_recog
                        )
                    """), {
                        "vol_id": vid, "mtype": mt,
                        "achieved_at": _past(random.randint(10, 300)),
                        "value": val_map.get(mt, 0),
                        "msg": f"Congratulations on reaching {mt.replace('_', ' ')}!",
                        "staff_recog": "Great work! Keep it up.",
                        "public_recog": random.choice([True, False]),
                    })
            await session.commit()
            tables_touched.append("volunteer_milestones")
            print(f"    -> {await _count(session, 'volunteer_milestones')} volunteer milestones created")
        else:
            print("  volunteer_milestones already seeded, skipping")

        # Volunteer communications (FK -> volunteers)
        if await _count(session, "volunteer_communications") == 0 and volunteer_ids:
            print("  Seeding volunteer_communications...")
            comm_data = [
                ("Shift Reminder: Saturday 10 AM", "Reminder: You are scheduled for a shelving shift this Saturday at 10 AM.", "email", "shift_reminder"),
                ("Training Due: Safety Update", "Your annual safety training renewal is due by end of month.", "email", "training_due"),
                ("New Opportunity: Summer Reading Helper", "We need volunteers for our Summer Reading Program. Interested?", "in_app", "opportunity"),
                ("Thank You for 50 Hours!", "We appreciate your dedication. You have reached 50 volunteer hours!", "email", "other"),
                ("Schedule Change Notice", "The library will be closed next Monday for a holiday. Your shift has been cancelled.", "email", "shift_reminder"),
                ("Welcome to the Team!", "Welcome aboard! Your orientation is scheduled for next Tuesday.", "email", "other"),
                ("Monthly Newsletter", "Check out what is happening at the library this month.", "email", "other"),
                ("Feedback Request", "We would love to hear about your volunteer experience so far.", "in_app", "other"),
                ("Holiday Party Invitation", "You are invited to our annual volunteer appreciation dinner!", "email", "other"),
                ("Coverage Needed: Wednesday PM", "Can anyone cover a 2-5 PM shift this Wednesday?", "in_app", "shift_reminder"),
            ]
            for subject, body, comm_type, category in comm_data:
                await session.execute(text("""
                    INSERT INTO volunteer_communications (
                        volunteer_id, subject, message_body,
                        communication_type, sent_by_id, category,
                        response_required
                    ) VALUES (
                        :vol_id, :subject, :body,
                        :comm_type, :sent_by, :category,
                        :resp_req
                    )
                """), {
                    "vol_id": random.choice(volunteer_ids),
                    "subject": subject, "body": body,
                    "comm_type": comm_type,
                    "sent_by": random.choice(staff_ids),
                    "category": category,
                    "resp_req": category == "shift_reminder",
                })
            await session.commit()
            tables_touched.append("volunteer_communications")
            print(f"    -> {await _count(session, 'volunteer_communications')} volunteer communications created")
        else:
            print("  volunteer_communications already seeded, skipping")

        # Volunteer schedules (FK -> delivery_volunteers)
        if await _count(session, "volunteer_schedules") == 0 and delivery_vol_ids:
            print("  Seeding volunteer_schedules...")
            sched_count = 0
            seen_pairs = set()
            for dvid in delivery_vol_ids:
                for day_offset in range(0, 21, 7):
                    for weekday_add in [0, 2, 4]:  # Mon, Wed, Fri
                        sched_date = _future_date(day_offset + weekday_add)
                        pair_key = (dvid, sched_date)
                        if pair_key in seen_pairs:
                            continue
                        seen_pairs.add(pair_key)
                        await session.execute(text("""
                            INSERT INTO volunteer_schedules (
                                volunteer_id, date, is_available,
                                time_start, time_end, notes
                            ) VALUES (
                                :vol_id, :sdate, :avail,
                                :t_start, :t_end, :notes
                            )
                        """), {
                            "vol_id": dvid, "sdate": sched_date,
                            "avail": random.random() > 0.1,
                            "t_start": "09:00", "t_end": "14:00",
                            "notes": None,
                        })
                        sched_count += 1
            await session.commit()
            tables_touched.append("volunteer_schedules")
            print(f"    -> {sched_count} volunteer schedules created")
        else:
            print("  volunteer_schedules already seeded, skipping")

        # ====================================================================
        # 5. COMMUNITY ARCHIVE SUBMISSIONS, RESOURCE HUBS, LIAISON CONTACTS
        # ====================================================================
        if await _count(session, "community_archive_submissions") == 0:
            print("  Seeding community_archive_submissions...")

            archive_data = [
                ("Historic Downtown Photograph - 1955", "Black and white photograph of Main Street circa 1955, showing original storefronts.", "photo", "1950s", "Downtown", True),
                ("1970 Library Groundbreaking Ceremony", "Newspaper clipping and photographs from the original library building groundbreaking.", "newspaper", "1970", "Main Branch", True),
                ("Oral History: Mary Johnson", "Audio recording of long-time resident Mary Johnson sharing childhood memories.", "audio", "1940s-1960s", "Residential District", True),
                ("Old Town Map Collection", "Hand-drawn maps of the town from the 1890s showing original lot boundaries.", "map", "1890s", "Town Center", True),
                ("High School Yearbook Collection 1960-1980", "Donated collection of local high school yearbooks spanning two decades.", "document", "1960-1980", "Local High School", True),
            ]

            for title, desc, mat_type, period, location, owns in archive_data:
                submitter_patron = random.choice(patron_ids)
                reviewer = random.choice(staff_ids)
                await session.execute(text("""
                    INSERT INTO community_archive_submissions (
                        user_id, submitter_name, submitter_email, submitter_phone,
                        submitter_relationship, material_type, title, description,
                        date_or_period, location, is_public, access_level,
                        submitter_owns_material, has_permission,
                        creative_commons_license, status,
                        reviewed_by, reviewed_at
                    ) VALUES (
                        :user_id, :name, :email, :phone,
                        :relationship, :mat_type, :title, :desc,
                        :period, :location, :is_public, :access_level,
                        :owns, :has_perm,
                        :cc_license, :status,
                        :reviewed_by, :reviewed_at
                    )
                """), {
                    "user_id": submitter_patron,
                    "name": f"Patron {submitter_patron}",
                    "email": f"patron{submitter_patron}@example.com",
                    "phone": f"555-02{random.randint(10,99)}",
                    "relationship": random.choice(["family member", "local historian", "community member"]),
                    "mat_type": mat_type, "title": title, "desc": desc,
                    "period": period, "location": location,
                    "is_public": True, "access_level": "public",
                    "owns": owns, "has_perm": True,
                    "cc_license": "CC-BY-4.0",
                    "status": random.choice(["approved", "published"]),
                    "reviewed_by": reviewer,
                    "reviewed_at": _past(random.randint(5, 60)),
                })

            await session.commit()
            tables_touched.append("community_archive_submissions")
            print(f"    -> {await _count(session, 'community_archive_submissions')} archive submissions created")
        else:
            print("  community_archive_submissions already seeded, skipping")

        if await _count(session, "community_resource_hubs") == 0:
            print("  Seeding community_resource_hubs...")

            hubs_data = [
                ("Main Branch Emergency Hub", 1, "Main floor lobby and community room", 200, True, True),
                ("Elmdale Branch Warming Center", 2, "Elmdale Branch main reading room", 75, False, True),
                ("Bookmobile Emergency Station", 3, "Bookmobile parking area with pop-up tent", 30, False, False),
                ("Tech Center Charging Hub", 4, "Computer lab with 20 charging stations", 50, True, True),
            ]

            for hub_name, b_id, loc_desc, cap, has_gen, has_internet in hubs_data:
                bid = branch_ids[b_id - 1] if b_id <= len(branch_ids) else branch_ids[0]
                purposes = json.dumps(["Emergency shelter", "Charging station", "Information center"])
                emergency_types = json.dumps(["Power outage", "Severe weather", "Natural disaster"])
                resources_avail = json.dumps(["water", "blankets", "phone chargers", "first aid kit"])
                services_offered = json.dumps(["charging", "wifi", "information", "warming"])

                await session.execute(text("""
                    INSERT INTO community_resource_hubs (
                        hub_name, branch_id, location_description,
                        hub_purposes, emergency_types,
                        max_capacity, has_generator_backup, has_internet_connectivity,
                        has_water_supply, has_food_storage, has_medical_supplies,
                        has_charging_stations, has_meeting_spaces,
                        required_staff_count, is_active,
                        supplies_stocked, equipment_tested, staff_trained,
                        emergency_procedures_reviewed,
                        operating_hours, contact_phone, contact_email,
                        resources_available, services_offered
                    ) VALUES (
                        :hub_name, :branch_id, :loc_desc,
                        cast(:purposes as json), cast(:emergency as json),
                        :cap, :has_gen, :has_internet,
                        :has_water, :has_food, :has_medical,
                        :has_charging, :has_meeting,
                        :staff_count, :is_active,
                        :supplies, :equipment, :trained,
                        :procedures,
                        :hours, :phone, :email,
                        cast(:resources as json), cast(:services as json)
                    )
                """), {
                    "hub_name": hub_name, "branch_id": bid, "loc_desc": loc_desc,
                    "purposes": json.dumps(["Emergency shelter", "Charging station", "Information center"]),
                    "emergency": json.dumps(["Power outage", "Severe weather", "Natural disaster"]),
                    "cap": cap, "has_gen": has_gen, "has_internet": has_internet,
                    "has_water": True, "has_food": False, "has_medical": True,
                    "has_charging": True, "has_meeting": True,
                    "staff_count": random.randint(2, 5), "is_active": False,
                    "supplies": True, "equipment": True, "trained": True,
                    "procedures": True,
                    "hours": "8:00 AM - 8:00 PM", "phone": "555-LIB-HELP",
                    "email": "emergency@library.org",
                    "resources": json.dumps(["water", "blankets", "phone chargers"]),
                    "services": json.dumps(["charging", "wifi", "information"]),
                })

            await session.commit()
            tables_touched.append("community_resource_hubs")
            print(f"    -> {await _count(session, 'community_resource_hubs')} resource hubs created")
        else:
            print("  community_resource_hubs already seeded, skipping")

        if await _count(session, "community_liaison_contacts") == 0:
            print("  Seeding community_liaison_contacts...")

            liaison_data = [
                ("Maria", "Rodriguez", "Community Outreach Director", "community_outreach", "United Way Local Chapter", "maria.r@unitedway.org", "555-0301", "Spanish", "social services"),
                ("David", "Chen", "Program Coordinator", "coordinator", "Asian Community Center", "david.chen@asiancc.org", "555-0302", "Mandarin", "cultural programming"),
                ("Fatima", "Al-Hassan", "Refugee Services Coordinator", "caseworker", "Refugee Resettlement Agency", "fatima@refugeeagency.org", "555-0303", "Arabic", "refugee services"),
                ("James", "Washington", "Volunteer Coordinator", "volunteer_coordinator", "Community Action Partnership", "james.w@capagency.org", "555-0304", "English", "volunteer management"),
                ("Sofia", "Petrov", "ESL Program Director", "director", "Adult Learning Center", "sofia.p@adultlearning.org", "555-0305", "Russian", "ESL education"),
                ("Priya", "Sharma", "Interpreter Services", "interpreter", "Language Access Services", "priya@langaccess.org", "555-0306", "Hindi", "translation"),
            ]

            for first, last, title, role, org, email, phone, lang, expertise in liaison_data:
                await session.execute(text("""
                    INSERT INTO community_liaison_contacts (
                        first_name, last_name, title, role, organization,
                        email, phone, languages_spoken, expertise_areas,
                        service_specialties, community_served,
                        years_of_experience, is_active,
                        last_contact_date
                    ) VALUES (
                        :first, :last, :title, :role, :org,
                        :email, :phone, :languages, :expertise,
                        :specialties, :community,
                        :years, :active,
                        :last_contact
                    )
                """), {
                    "first": first, "last": last, "title": title, "role": role, "org": org,
                    "email": email, "phone": phone,
                    "languages": [lang, "English"],
                    "expertise": [expertise],
                    "specialties": [expertise],
                    "community": org,
                    "years": random.randint(3, 15), "active": True,
                    "last_contact": _past_date(random.randint(5, 60)),
                })

            await session.commit()
            tables_touched.append("community_liaison_contacts")
            print(f"    -> {await _count(session, 'community_liaison_contacts')} liaison contacts created")
        else:
            print("  community_liaison_contacts already seeded, skipping")

        # ====================================================================
        # 6. CONVERSATION CIRCLES + SESSIONS + PARTICIPANTS
        # ====================================================================
        if await _count(session, "conversation_circles") == 0:
            print("  Seeding conversation_circles...")

            circles_data = [
                ("English Practice Circle", "Casual English conversation practice for beginners and intermediate learners.", "language_practice", "Ana Martinez", "10:00", "11:00", "Monday", "Spanish", 12),
                ("Cultural Exchange Cafe", "Share stories and traditions from your home country over coffee and tea.", "cultural_exchange", "David Chen", "14:00", "15:30", "Wednesday", "Mandarin", 15),
                ("Womens Empowerment Circle", "Safe space for women to discuss goals, challenges, and support each other.", "women_empowerment", "Fatima Al-Hassan", "13:00", "14:30", "Thursday", "Arabic", 10),
                ("Job Skills Workshop Circle", "Practice interview skills, resume review, and workplace communication.", "job_skills", "James Washington", "15:00", "16:30", "Tuesday", "English", 8),
            ]

            for title, desc, ctype, facilitator, start_t, end_t, day, lang, cap in circles_data:
                await session.execute(text("""
                    INSERT INTO conversation_circles (
                        title, description, circle_type,
                        facilitator_name, facilitator_email,
                        location, schedule_description,
                        start_date, end_date,
                        start_time, end_time,
                        day_of_week, max_capacity,
                        languages_discussed, target_age_group,
                        is_free, is_active
                    ) VALUES (
                        :title, :desc, :ctype,
                        :facilitator, :fac_email,
                        :location, :schedule,
                        :start_date, :end_date,
                        :start_time, :end_time,
                        :day_of_week, :cap,
                        :languages, :age_group,
                        :is_free, :is_active
                    )
                """), {
                    "title": title, "desc": desc, "ctype": ctype,
                    "facilitator": facilitator,
                    "fac_email": f"{facilitator.lower().replace(' ', '.')}@library.org",
                    "location": "Main Branch - Meeting Room B",
                    "schedule": f"Every {day}, {start_t}-{end_t}",
                    "start_date": _past_date(90),
                    "end_date": _future_date(90),
                    "start_time": start_t, "end_time": end_t,
                    "day_of_week": [day],
                    "cap": cap,
                    "languages": [lang, "English"],
                    "age_group": "adults",
                    "is_free": True, "is_active": True,
                })

            await session.commit()
            tables_touched.append("conversation_circles")

            # Sessions
            print("  Seeding conversation_circle_sessions...")
            circles_r = await session.execute(text("SELECT id FROM conversation_circles ORDER BY id"))
            circle_ids = [c[0] for c in circles_r.fetchall()]
            topics = [
                "Greetings and introductions", "Ordering food at restaurants",
                "Visiting the doctor", "Job interview practice",
                "Talking about hobbies", "Asking for directions",
                "Shopping and money", "Telling your story",
                "Holiday traditions", "Current events discussion",
                "Library services overview", "Community resources",
            ]

            for cid in circle_ids:
                for weeks_ago in range(8):
                    await session.execute(text("""
                        INSERT INTO conversation_circle_sessions (
                            circle_id, session_date, session_time,
                            topic, attendance_count, notes, was_held
                        ) VALUES (
                            :cid, :sdate, :stime,
                            :topic, :attendance, :notes, :held
                        )
                    """), {
                        "cid": cid,
                        "sdate": _past_date(weeks_ago * 7),
                        "stime": "10:00",
                        "topic": random.choice(topics),
                        "attendance": random.randint(3, 10),
                        "notes": None,
                        "held": random.random() > 0.1,
                    })

            await session.commit()
            tables_touched.append("conversation_circle_sessions")

            # Participants
            print("  Seeding conversation_circle_participants...")
            part_count = 0
            for cid in circle_ids:
                num_parts = random.randint(4, 8)
                chosen = random.sample(patron_ids, min(num_parts, len(patron_ids)))
                for pid in chosen:
                    await session.execute(text("""
                        INSERT INTO conversation_circle_participants (
                            circle_id, patron_id, name, join_date,
                            status, attendance_count
                        ) VALUES (
                            :cid, :pid, :name, :join_date,
                            :status, :att_count
                        )
                    """), {
                        "cid": cid, "pid": pid,
                        "name": None,
                        "join_date": _past_date(random.randint(10, 80)),
                        "status": "active",
                        "att_count": random.randint(2, 8),
                    })
                    part_count += 1

            await session.commit()
            tables_touched.append("conversation_circle_participants")
            print(f"    -> {await _count(session, 'conversation_circles')} circles, "
                  f"{await _count(session, 'conversation_circle_sessions')} sessions, "
                  f"{part_count} participants created")
        else:
            print("  conversation_circles already seeded, skipping")

        # ====================================================================
        # 7. ESL CLASSES + ESL ENROLLMENTS
        # ====================================================================
        if await _count(session, "esl_classes") == 0:
            print("  Seeding esl_classes...")

            esl_data = [
                ("ESL Beginner: Foundations", "Basic English for daily life: greetings, numbers, directions.", "beginner", "active", "Rosa Mendez", "Mon/Wed", 20),
                ("ESL Intermediate: Workplace English", "English for the workplace: emails, meetings, phone calls.", "intermediate", "active", "John Park", "Tue/Thu", 15),
                ("ESL Advanced: Academic Writing", "Essay writing, research skills, and formal English.", "advanced", "active", "Sarah Williams", "Wednesday", 12),
                ("ESL Elementary: Reading and Writing", "Building literacy skills for early English learners.", "elementary", "planned", "Maria Santos", "Mon/Fri", 18),
            ]

            for title, desc, level, status, instructor, days, cap in esl_data:
                day_list = [d.strip() for d in days.split("/")]
                day_arr = day_list
                skills = ["reading", "writing", "speaking", "listening"]

                await session.execute(text("""
                    INSERT INTO esl_classes (
                        title, description, level, status,
                        instructor_name, instructor_email,
                        location, start_date, end_date,
                        start_time, end_time, day_of_week,
                        max_capacity, current_enrollment,
                        skills_covered, is_in_person
                    ) VALUES (
                        :title, :desc, :level, :status,
                        :instructor, :inst_email,
                        :location, :start_date, :end_date,
                        :start_time, :end_time, :days,
                        :cap, :enrollment,
                        :skills, :in_person
                    )
                """), {
                    "title": title, "desc": desc, "level": level, "status": status,
                    "instructor": instructor,
                    "inst_email": f"{instructor.lower().replace(' ', '.')}@library.org",
                    "location": "Main Branch - Meeting Room A",
                    "start_date": _past_date(60), "end_date": _future_date(120),
                    "start_time": "18:00", "end_time": "20:00",
                    "days": day_arr, "cap": cap,
                    "enrollment": random.randint(5, cap),
                    "skills": skills,
                    "in_person": True,
                })

            await session.commit()
            tables_touched.append("esl_classes")

            # ESL Enrollments
            print("  Seeding esl_enrollments...")
            esl_r = await session.execute(text("SELECT id FROM esl_classes ORDER BY id"))
            esl_ids = [e[0] for e in esl_r.fetchall()]
            enroll_count = 0
            used_pairs = set()

            for eid in esl_ids:
                num_enrollments = random.randint(4, 8)
                chosen = random.sample(patron_ids, min(num_enrollments, len(patron_ids)))
                for pid in chosen:
                    pair = (eid, pid)
                    if pair in used_pairs:
                        continue
                    used_pairs.add(pair)
                    await session.execute(text("""
                        INSERT INTO esl_enrollments (
                            esl_class_id, patron_id, enrollment_date,
                            status, attendance_count, certificate_earned,
                            assessment_score, notes
                        ) VALUES (
                            :esl_id, :patron_id, :enroll_date,
                            :status, :att_count, :cert,
                            :score, :notes
                        )
                    """), {
                        "esl_id": eid, "patron_id": pid,
                        "enroll_date": _past_date(random.randint(10, 50)),
                        "status": random.choice(["enrolled", "enrolled", "completed"]),
                        "att_count": random.randint(3, 20),
                        "cert": random.random() > 0.7,
                        "score": round(random.uniform(60, 98), 1) if random.random() > 0.5 else None,
                        "notes": None,
                    })
                    enroll_count += 1

            await session.commit()
            tables_touched.append("esl_enrollments")
            print(f"    -> {await _count(session, 'esl_classes')} ESL classes, {enroll_count} enrollments created")
        else:
            print("  esl_classes already seeded, skipping")

        # ====================================================================
        # 8. EXTERNAL RESOURCES + EXTERNAL RESOURCE ENROLLMENTS
        # ====================================================================
        if await _count(session, "external_resources") == 0:
            print("  Seeding external_resources...")

            ext_resources_data = [
                ("GED Preparation Course", "Free online GED preparation with practice tests and study guides.", "https://www.gedprep.example.org/course", "course", "beginner", "GED Testing Service", 120),
                ("Resume Builder Workshop", "Interactive resume building tool with templates and examples.", "https://www.careerready.example.org/resume", "toolkit", "beginner", "Career Ready Foundation", 45),
                ("Digital Literacy Fundamentals", "Learn to use computers, email, and internet safely.", "https://www.digitallit.example.org/basics", "course", "beginner", "Digital Literacy Council", 90),
                ("Financial Planning for Families", "Budgeting, saving, and understanding credit basics.", "https://www.finlit.example.org/families", "course", "beginner", "Financial Literacy Foundation", 60),
                ("AI Ethics and Society", "Understanding artificial intelligence impact on communities.", "https://www.data.org/ai-ethics", "playbook", "intermediate", "data.org", 30),
                ("Small Business Startup Guide", "Step-by-step guide to starting a small business.", "https://www.sba.example.gov/startup", "toolkit", "intermediate", "Small Business Administration", 90),
                ("Citizenship Test Preparation", "Study materials and practice tests for US citizenship exam.", "https://www.uscis.example.gov/citizenship", "course", "beginner", "USCIS", 180),
                ("Job Interview Skills", "Video-based training for common interview scenarios.", "https://www.jobskills.example.org/interview", "course", "beginner", "Workforce Development Board", 60),
            ]

            for title, desc, url, rtype, difficulty, source_org, est_min in ext_resources_data:
                topics_list = []
                if "GED" in title:
                    topics_list = ["education", "GED", "testing"]
                elif "Resume" in title or "Job" in title:
                    topics_list = ["career", "employment", "skills"]
                elif "Digital" in title:
                    topics_list = ["technology", "digital literacy"]
                elif "Financial" in title:
                    topics_list = ["finance", "budgeting"]
                elif "AI" in title:
                    topics_list = ["AI", "ethics", "technology"]
                elif "Business" in title:
                    topics_list = ["business", "entrepreneurship"]
                elif "Citizenship" in title:
                    topics_list = ["citizenship", "immigration"]
                else:
                    topics_list = ["skills", "career"]

                await session.execute(text("""
                    INSERT INTO external_resources (
                        title, description, source_url, provider,
                        resource_type, difficulty, topics,
                        access_level, estimated_minutes, is_featured,
                        source_organization
                    ) VALUES (
                        :title, :desc, :url, :provider,
                        :rtype, :difficulty, cast(:topics as jsonb),
                        :access, :est_min, :featured,
                        :source_org
                    )
                """), {
                    "title": title, "desc": desc, "url": url,
                    "provider": "data.org" if "data.org" in url else "library",
                    "rtype": rtype, "difficulty": difficulty,
                    "topics": json.dumps(topics_list),
                    "access": "patron", "est_min": est_min,
                    "featured": random.random() > 0.6,
                    "source_org": source_org,
                })

            await session.commit()
            tables_touched.append("external_resources")

            # External resource enrollments
            print("  Seeding external_resource_enrollments...")
            ext_r = await session.execute(text("SELECT id FROM external_resources ORDER BY id"))
            ext_ids = [e[0] for e in ext_r.fetchall()]
            ext_enroll_count = 0
            used_ext_pairs = set()

            for eid in ext_ids:
                num = random.randint(2, 5)
                chosen = random.sample(patron_ids, min(num, len(patron_ids)))
                for pid in chosen:
                    pair = (pid, eid)
                    if pair in used_ext_pairs:
                        continue
                    used_ext_pairs.add(pair)
                    completed = random.random() > 0.6
                    await session.execute(text("""
                        INSERT INTO external_resource_enrollments (
                            user_id, external_resource_id,
                            clicked_at, completed, completion_date,
                            rating, notes
                        ) VALUES (
                            :uid, :eid,
                            :clicked, :completed, :comp_date,
                            :rating, :notes
                        )
                    """), {
                        "uid": pid, "eid": eid,
                        "clicked": _past(random.randint(1, 60)),
                        "completed": completed,
                        "comp_date": _past(random.randint(1, 30)) if completed else None,
                        "rating": random.randint(3, 5) if completed else None,
                        "notes": None,
                    })
                    ext_enroll_count += 1

            await session.commit()
            tables_touched.append("external_resource_enrollments")
            print(f"    -> {await _count(session, 'external_resources')} resources, {ext_enroll_count} enrollments created")
        else:
            print("  external_resources already seeded, skipping")

        # ====================================================================
        # 9. TEEN ADVISORY BOARD + TEEN ACHIEVEMENTS + TEEN VOLUNTEER HOUR LOGS
        # ====================================================================
        if await _count(session, "teen_advisory_board_members") == 0 and teen_volunteer_ids:
            print("  Seeding teen_advisory_board_members...")
            positions = ["President", "Vice-President", "Secretary", "Member", "Member"]

            for i, tvid in enumerate(teen_volunteer_ids):
                pos = positions[i] if i < len(positions) else "Member"
                await session.execute(text("""
                    INSERT INTO teen_advisory_board_members (
                        volunteer_id, term_start, term_end, position,
                        total_meetings_attended, total_meetings_held,
                        attendance_percentage, initiatives_proposed,
                        initiatives_approved, projects_led,
                        has_voting_rights, votes_cast, is_active
                    ) VALUES (
                        :vol_id, :term_start, :term_end, :position,
                        :meetings_att, :meetings_held,
                        :att_pct, :init_proposed,
                        :init_approved, :projects,
                        :voting, :votes, :active
                    )
                """), {
                    "vol_id": tvid,
                    "term_start": _past_date(200),
                    "term_end": _future_date(165),
                    "position": pos,
                    "meetings_att": random.randint(5, 12),
                    "meetings_held": 12,
                    "att_pct": round(random.uniform(60, 100), 1),
                    "init_proposed": random.randint(0, 4),
                    "init_approved": random.randint(0, 2),
                    "projects": random.sample(["Book Fair", "Teen Reading Challenge", "Library Mural", "Community Service Day"], random.randint(0, 2)),
                    "voting": True,
                    "votes": random.randint(3, 10),
                    "active": True,
                })

            await session.commit()
            tables_touched.append("teen_advisory_board_members")
            print(f"    -> {await _count(session, 'teen_advisory_board_members')} teen board members created")

            # Teen achievements
            print("  Seeding teen_achievements...")
            achievement_data = [
                ("hours_milestone", "10 Hours of Service", "Completed 10 hours of volunteer service!", "bronze", 10.0),
                ("hours_milestone", "25 Hours of Service", "Completed 25 hours of volunteer service!", "silver", 25.0),
                ("task_completion", "Shelving Champion", "Shelved 500 items in a single month!", "gold", None),
                ("leadership", "Meeting Leader", "Led a Teen Advisory Board meeting!", "silver", None),
                ("summer_reading_helper", "Summer Reading Star", "Helped 20 children during Summer Reading Program!", "gold", None),
                ("community_impact", "Community Hero", "Organized a community service project!", "gold", None),
                ("teen_board", "Board Member Excellence", "Perfect attendance at board meetings for 3 months!", "silver", None),
            ]

            ach_count = 0
            for tvid in teen_volunteer_ids:
                num_ach = random.randint(1, 3)
                chosen_ach = random.sample(achievement_data, min(num_ach, len(achievement_data)))
                for ach_type, title, desc, level, hours in chosen_ach:
                    await session.execute(text("""
                        INSERT INTO teen_achievements (
                            volunteer_id, achievement_type, title, description,
                            earned_date, is_public, recognition_level,
                            associated_hours, promoted_on_social
                        ) VALUES (
                            :vol_id, :ach_type, :title, :desc,
                            :earned, :public, :level,
                            :hours, :social
                        )
                    """), {
                        "vol_id": tvid, "ach_type": ach_type,
                        "title": title, "desc": desc,
                        "earned": _past(random.randint(10, 200)),
                        "public": True, "level": level,
                        "hours": hours,
                        "social": random.random() > 0.7,
                    })
                    ach_count += 1

            await session.commit()
            tables_touched.append("teen_achievements")
            print(f"    -> {ach_count} teen achievements created")

            # Teen volunteer hour logs
            print("  Seeding teen_volunteer_hour_logs...")
            teen_task_types = ["reading_helper", "shelving", "tech_support", "event_assistant", "program_helper"]
            teen_log_count = 0

            for tvid in teen_volunteer_ids:
                num_logs = random.randint(4, 8)
                for _ in range(num_logs):
                    branch = random.choice(branch_ids) if branch_ids else None
                    await session.execute(text("""
                        INSERT INTO teen_volunteer_hour_logs (
                            volunteer_id, service_date, hours, minutes,
                            task_type, task_description,
                            branch_id, items_shelved, programs_assisted,
                            patrons_helped, verified, verified_by_id,
                            verified_at
                        ) VALUES (
                            :vol_id, :sdate, :hours, :minutes,
                            :task_type, :task_desc,
                            :branch_id, :shelved, :assisted,
                            :helped, :verified, :verified_by,
                            :verified_at
                        )
                    """), {
                        "vol_id": tvid,
                        "sdate": _past_date(random.randint(5, 120)),
                        "hours": random.choice([1.0, 1.5, 2.0, 2.5, 3.0]),
                        "minutes": 0,
                        "task_type": random.choice(teen_task_types),
                        "task_desc": random.choice(["Shelving returns", "Helped with storytime setup", "Tech support for patrons", "Summer reading assistance"]),
                        "branch_id": branch,
                        "shelved": random.randint(0, 50),
                        "assisted": random.randint(0, 2),
                        "helped": random.randint(0, 10),
                        "verified": True,
                        "verified_by": random.choice(staff_ids),
                        "verified_at": _past(random.randint(1, 30)),
                    })
                    teen_log_count += 1

            await session.commit()
            tables_touched.append("teen_volunteer_hour_logs")
            print(f"    -> {teen_log_count} teen volunteer hour logs created")
        else:
            print("  teen_advisory_board_members already seeded (or no teen_volunteers), skipping")

        # ====================================================================
        # 10. FAMILY READING CHALLENGES + REGISTRATIONS
        #     FK -> reading_programs (currently empty, must create one first)
        # ====================================================================
        if await _count(session, "family_reading_challenges") == 0:
            # Check if reading_programs has data; create one if not
            rp_count = await _count(session, "reading_programs")
            if rp_count == 0:
                print("  Creating a reading_program for FK reference...")
                await session.execute(text("""
                    INSERT INTO reading_programs (
                        name, description, program_type, age_group,
                        start_date, end_date, reading_goal_type,
                        reading_goal_value, is_active, is_school_program,
                        grade_levels, reading_levels
                    ) VALUES (
                        :name, :desc, :ptype, :age_group,
                        :start_date, :end_date, :goal_type,
                        :goal_val, :active, :school,
                        cast(:grades as json), cast(:levels as json)
                    )
                """), {
                    "name": "Spring Reading Challenge 2026",
                    "desc": "Read together as a family this spring!",
                    "ptype": "special",
                    "age_group": "All Ages",
                    "start_date": _past_date(30),
                    "end_date": _future_date(60),
                    "goal_type": "books",
                    "goal_val": 10,
                    "active": True, "school": False,
                    "grades": json.dumps([]),
                    "levels": json.dumps([]),
                })
                await session.commit()
                tables_touched.append("reading_programs")
                print("    -> 1 reading program created")

            rp_r = await session.execute(text("SELECT id FROM reading_programs ORDER BY id LIMIT 1"))
            rp_id = rp_r.scalar()

            print("  Seeding family_reading_challenges...")
            challenges_data = [
                ("Family Story Quest", "Read 5 books together as a family this month!", "family", "books", 5),
                ("Parent-Child Reading Marathon", "Parents and kids read 500 minutes together.", "parent-child", "minutes", 500),
                ("Sibling Read-Along", "Siblings read to each other - 10 books in 4 weeks!", "sibling", "books", 10),
            ]

            for name, desc, ctype, goal_type, goal_val in challenges_data:
                await session.execute(text("""
                    INSERT INTO family_reading_challenges (
                        program_id, name, description, challenge_type,
                        goal_type, goal_value,
                        start_date, end_date,
                        parent_reward_description, child_reward_description,
                        is_active
                    ) VALUES (
                        :prog_id, :name, :desc, :ctype,
                        :goal_type, :goal_val,
                        :start_date, :end_date,
                        :parent_reward, :child_reward,
                        :active
                    )
                """), {
                    "prog_id": rp_id, "name": name, "desc": desc, "ctype": ctype,
                    "goal_type": goal_type, "goal_val": goal_val,
                    "start_date": _past_date(14), "end_date": _future_date(30),
                    "parent_reward": "Library tote bag and bookmark set",
                    "child_reward": "Book of their choice and reading certificate",
                    "active": True,
                })

            await session.commit()
            tables_touched.append("family_reading_challenges")

            # Family challenge registrations
            print("  Seeding family_challenge_registrations...")
            fc_r = await session.execute(text("SELECT id FROM family_reading_challenges ORDER BY id"))
            fc_ids = [f[0] for f in fc_r.fetchall()]
            fc_reg_count = 0

            for fc_id in fc_ids:
                num_regs = random.randint(3, 6)
                parent_sample = random.sample(patron_ids, min(num_regs, len(patron_ids)))
                for parent_id in parent_sample:
                    child_id = random.choice(child_ids) if child_ids else random.choice(patron_ids)
                    await session.execute(text("""
                        INSERT INTO family_challenge_registrations (
                            challenge_id, parent_user_id, child_user_id,
                            parent_goal, child_goal,
                            parent_progress, child_progress, combined_progress
                        ) VALUES (
                            :fc_id, :parent, :child,
                            :p_goal, :c_goal,
                            :p_progress, :c_progress, :combined
                        )
                    """), {
                        "fc_id": fc_id, "parent": parent_id, "child": child_id,
                        "p_goal": random.randint(3, 8),
                        "c_goal": random.randint(3, 8),
                        "p_progress": random.randint(0, 5),
                        "c_progress": random.randint(0, 5),
                        "combined": random.randint(0, 8),
                    })
                    fc_reg_count += 1

            await session.commit()
            tables_touched.append("family_challenge_registrations")
            print(f"    -> {await _count(session, 'family_reading_challenges')} challenges, {fc_reg_count} registrations created")
        else:
            print("  family_reading_challenges already seeded, skipping")

        # ====================================================================
        # 11. CO-SPONSORED PROGRAMS + PROGRAM SESSIONS
        # ====================================================================
        if await _count(session, "co_sponsored_programs") == 0 and partner_ids:
            print("  Seeding co_sponsored_programs...")

            co_programs_data = [
                ("Community Health Fair", "Joint health screening and wellness education event.", "workshop series", "in_development", "Families and Adults", 150, 2000.00),
                ("STEM Saturdays", "Monthly hands-on STEM workshops for K-8 students.", "reading program", "active", "Children ages 5-14", 30, 500.00),
                ("Job Readiness Boot Camp", "Three-day intensive job preparation program.", "workshop series", "completed", "Adults seeking employment", 25, 1500.00),
                ("Bilingual Storytime Series", "Storytime in English and Spanish for bilingual families.", "reading program", "active", "Children ages 0-6", 20, 300.00),
            ]

            goals_options = [
                json.dumps(["Increase community health awareness", "Provide free screenings"]),
                json.dumps(["Inspire STEM interest", "Hands-on learning"]),
                json.dumps(["Improve employment rates", "Build interview skills"]),
                json.dumps(["Support bilingual literacy", "Cultural exchange"]),
            ]

            for i, (name, desc, ptype, status, audience, reach, budget) in enumerate(co_programs_data):
                lead_partner = partner_ids[i % len(partner_ids)]
                co_sponsors = random.sample([p for p in partner_ids if p != lead_partner], min(2, len(partner_ids) - 1))
                participants = random.randint(reach // 2, reach) if status == "completed" else None

                await session.execute(text("""
                    INSERT INTO co_sponsored_programs (
                        name, description, program_type, status,
                        lead_partner_id, co_sponsor_partner_ids,
                        start_date, end_date,
                        target_audience, goals, expected_reach,
                        total_budget, library_contribution,
                        partner_contributions,
                        program_manager_id,
                        participants, completion_rate,
                        outcomes_achieved, impact_summary,
                        created_by_id
                    ) VALUES (
                        :name, :desc, :ptype, :status,
                        :lead, :co_sponsors,
                        :start_date, :end_date,
                        :audience, cast(:goals as jsonb), :reach,
                        :budget, :lib_contrib,
                        cast(:partner_contrib as jsonb),
                        :manager,
                        :participants, :comp_rate,
                        cast(:outcomes as jsonb), :impact,
                        :created_by
                    )
                """), {
                    "name": name, "desc": desc, "ptype": ptype, "status": status,
                    "lead": lead_partner,
                    "co_sponsors": co_sponsors,
                    "start_date": _past_date(60) if status in ("completed", "active") else _future_date(30),
                    "end_date": _past_date(10) if status == "completed" else _future_date(90),
                    "audience": audience, "goals": goals_options[i],
                    "reach": reach, "budget": budget,
                    "lib_contrib": budget * 0.5,
                    "partner_contrib": json.dumps({str(lead_partner): budget * 0.3}),
                    "manager": random.choice(staff_ids),
                    "participants": participants,
                    "comp_rate": round(random.uniform(70, 95), 1) if status == "completed" else None,
                    "outcomes": json.dumps(["Positive community feedback"]) if status == "completed" else json.dumps([]),
                    "impact": "Successful community engagement" if status == "completed" else None,
                    "created_by": random.choice(staff_ids),
                })

            await session.commit()
            tables_touched.append("co_sponsored_programs")

            # Program sessions for co-sponsored programs
            print("  Seeding program_sessions...")
            co_progs_r = await session.execute(text("SELECT id, name FROM co_sponsored_programs ORDER BY id"))
            co_progs = co_progs_r.fetchall()

            session_count = 0
            for cp_id, cp_name in co_progs:
                num_sessions = random.randint(2, 4)
                for snum in range(1, num_sessions + 1):
                    sess_date = _past_date(60 - snum * 14) if snum <= 2 else _future_date(snum * 14)
                    co_fac = json.dumps([f"Partner Staff {random.randint(1,5)}"])
                    await session.execute(text("""
                        INSERT INTO program_sessions (
                            program_id, title, session_number,
                            session_date, start_time, end_time,
                            location, format,
                            expected_attendance, actual_attendance,
                            lead_facilitator_id, co_facilitators,
                            session_notes
                        ) VALUES (
                            :prog_id, :title, :snum,
                            :sdate, :start_time, :end_time,
                            :location, :format,
                            :expected, :actual,
                            :facilitator, cast(:co_fac as jsonb),
                            :notes
                        )
                    """), {
                        "prog_id": cp_id,
                        "title": f"{cp_name} - Session {snum}",
                        "snum": snum,
                        "sdate": sess_date,
                        "start_time": "10:00", "end_time": "12:00",
                        "location": "Main Branch - Community Room",
                        "format": "in-person",
                        "expected": random.randint(15, 40),
                        "actual": random.randint(10, 35) if sess_date < date.today() else None,
                        "facilitator": random.choice(staff_ids),
                        "co_fac": co_fac,
                        "notes": None,
                    })
                    session_count += 1

            await session.commit()
            tables_touched.append("program_sessions")
            print(f"    -> {await _count(session, 'co_sponsored_programs')} co-sponsored programs, "
                  f"{session_count} sessions created")
        else:
            print("  co_sponsored_programs already seeded (or no partners), skipping")

        # ====================================================================
        # FIX ALL SEQUENCES
        # ====================================================================
        print("  Fixing sequences...")
        for table in tables_touched:
            try:
                async with session.begin_nested():
                    await _fix_sequence(session, table)
            except SQLAlchemyError:
                pass  # Some tables may not have serial sequences
        await session.commit()

        # ====================================================================
        # SUMMARY (best-effort — session may be in a broken state after
        # sequence fixes, so wrap in try/except to avoid crashing the batch)
        # ====================================================================
        try:
            print("\n  === SEED SUMMARY ===")
            summary_tables = [
                "programs", "program_registrations", "program_statistics",
                "program_templates", "program_plans",
                "cultural_programs", "cultural_program_registrations",
                "volunteer_hour_logs", "volunteer_milestones", "volunteer_communications", "volunteer_schedules",
                "community_archive_submissions", "community_resource_hubs", "community_liaison_contacts",
                "conversation_circles", "conversation_circle_sessions", "conversation_circle_participants",
                "esl_classes", "esl_enrollments",
                "external_resources", "external_resource_enrollments",
                "teen_advisory_board_members", "teen_achievements", "teen_volunteer_hour_logs",
                "family_reading_challenges", "family_challenge_registrations",
                "co_sponsored_programs", "program_sessions",
            ]
            for t in summary_tables:
                cnt = await _count(session, t)
                if cnt > 0:
                    print(f"    {t}: {cnt}")
        except SQLAlchemyError:
            print("  (summary skipped — session state unrecoverable)")
            await session.rollback()

        print("\n  Batch programs seed complete!")
        return True

    except Exception as e:  # noqa: BLE001  # CLI seed script — outer boundary reports any failure to operator
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        await session.rollback()
        return False
