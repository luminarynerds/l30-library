# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import contextlib
import random
from datetime import datetime, timedelta, timezone, date, time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

utc = timezone.utc


def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago)


def _future(days_ahead: int) -> datetime:
    return datetime.now(utc) + timedelta(days=days_ahead)


def _past_date(days_ago: int) -> date:
    return (datetime.now(utc) - timedelta(days=days_ago)).date()


async def seed_medium_domains(session: AsyncSession) -> bool:

    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] in ("patron", "child")]
    all_ids = [u[0] for u in users]
    admin_id = staff_ids[0]

    branch_r = await session.execute(text("SELECT id, name FROM branches"))
    branches = branch_r.fetchall()
    branch_ids = [b[0] for b in branches]

    catalog_r = await session.execute(text("SELECT id FROM catalog_items"))
    catalog_ids = [r[0] for r in catalog_r.fetchall()]

    now = datetime.now(utc)

    # ════════════════════════════════════════════════════════════════
    # 1. STRATEGIC PLAN + GOALS + INITIATIVES + KPIs + MILESTONES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM strategic_plans"))
    if r.scalar() == 0:
        print("  Seeding strategic planning...")

        # Create the strategic plan
        r2 = await session.execute(text("""
            INSERT INTO strategic_plans (title, description, period_start, period_end, mission, vision,
                values, status, last_reviewed, next_review, story_intro, created_by_id)
            VALUES (:title, :desc, :start, :end, :mission, :vision,
                cast(:vals as jsonb), :status, :reviewed, :next_review, :story, :creator)
            RETURNING id
        """), {
            "title": "2024-2027 Strategic Plan: Connecting Community Through Knowledge",
            "desc": "A three-year strategic plan to strengthen the library's role as a community hub, expand digital services, and ensure equitable access for all residents.",
            "start": datetime(2024, 7, 1, tzinfo=utc),
            "end": datetime(2027, 6, 30, tzinfo=utc),
            "mission": "The Bébé Memorial Library empowers our community through free access to knowledge, technology, and cultural enrichment for people of all ages and backgrounds.",
            "vision": "A thriving community where every resident has the tools, resources, and support they need to learn, grow, and connect.",
            "vals": '["Intellectual Freedom", "Equitable Access", "Community Engagement", "Innovation", "Stewardship"]',
            "status": "active",
            "reviewed": _past(45),
            "next_review": _future(45),
            "story": "Since 1952, the Bébé Memorial Library has served as the heart of our community. This strategic plan charts our course for the next three years.",
            "creator": admin_id,
        })
        plan_id = r2.scalar()

        # Goals
        goals_data = [
            ("Expand Digital Access & Literacy", "Ensure all community members can participate in the digital world through expanded technology resources, training, and support.", "technology", 65, "active", 1),
            ("Strengthen Youth & Family Services", "Create a comprehensive ecosystem of programs and resources that support children, teens, and families at every stage.", "programs", 50, "active", 2),
            ("Deepen Community Partnerships", "Build and sustain meaningful partnerships with local organizations, schools, and businesses to extend the library's reach.", "outreach", 40, "active", 3),
            ("Modernize Facilities & Collections", "Update physical spaces and collections to meet evolving community needs and ensure accessibility for all.", "facilities", 30, "active", 4),
            ("Invest in Staff Development", "Attract, retain, and develop a diverse and skilled workforce that reflects and serves our community.", "people", 55, "active", 5),
        ]
        goal_ids = []
        for title, desc, category, progress, status, priority in goals_data:
            r3 = await session.execute(text("""
                INSERT INTO strategic_goals (plan_id, title, description, category, progress, status,
                    target_date, priority, is_public, staff_can_update, display_order, approval_status, created_at)
                VALUES (:plan, :title, :desc, :cat, :progress, :status,
                    :target, :priority, true, true, :order, 'approved', :created)
                RETURNING id
            """), {
                "plan": plan_id, "title": title, "desc": desc, "cat": category,
                "progress": progress, "status": status,
                "target": datetime(2027, 6, 30, tzinfo=utc),
                "priority": priority, "order": priority,
                "created": _past(600),
            })
            goal_ids.append(r3.scalar())

        # Initiatives (2-3 per goal)
        initiatives = [
            (goal_ids[0], "Public Computer Refresh", "Replace all public-access computers with current-generation hardware.", "completed", 100, 45000, 42000),
            (goal_ids[0], "Digital Literacy Workshop Series", "Monthly workshops covering internet basics, email, job searching, and cybersecurity.", "in_progress", 70, 5000, 3200),
            (goal_ids[0], "Hotspot Lending Program", "Circulate 50 WiFi hotspots to patrons without home internet access.", "in_progress", 60, 15000, 12000),
            (goal_ids[1], "Summer Reading Expansion", "Double participation in summer reading through school partnerships and incentives.", "in_progress", 45, 8000, 4500),
            (goal_ids[1], "Teen Advisory Board Relaunch", "Recruit and empower teen leaders to shape YA programming and collection.", "completed", 100, 2000, 1800),
            (goal_ids[2], "School Outreach Partnership", "Establish regular visits to all 8 elementary schools in the district.", "in_progress", 55, 6000, 3500),
            (goal_ids[2], "Homebound Delivery Service", "Launch a home delivery service for patrons unable to visit the library.", "in_progress", 40, 10000, 4000),
            (goal_ids[3], "Children's Area Renovation", "Redesign the children's space with flexible furniture, sensory areas, and improved accessibility.", "not_started", 10, 120000, 8000),
            (goal_ids[3], "Collection Diversity Audit", "Conduct a comprehensive audit of collection representation across all demographics.", "in_progress", 75, 3000, 2800),
            (goal_ids[4], "Staff Training Framework", "Develop a competency-based training program for all position levels.", "in_progress", 60, 12000, 7500),
            (goal_ids[4], "DEI Committee Formation", "Establish a staff-led DEI committee to guide inclusive practices.", "completed", 100, 1500, 1200),
        ]
        for plan_goal_id, title, desc, status, pct, budget, cost in initiatives:
            await session.execute(text("""
                INSERT INTO strategic_initiatives (plan_id, title, description, status, completion_percentage,
                    estimated_budget, actual_cost, assigned_leader_id, priority, board_approved,
                    start_date, target_completion_date)
                VALUES (:plan, :title, :desc, :status, :pct,
                    :budget, :cost, :leader, :priority, true,
                    :start, :target)
            """), {
                "plan": plan_id, "title": title, "desc": desc, "status": status,
                "pct": pct, "budget": budget, "cost": cost,
                "leader": random.choice(staff_ids), "priority": random.randint(1, 5),
                "start": _past(random.randint(180, 500)),
                "target": _future(random.randint(60, 400)),
            })

        # KPIs
        kpis = [
            ("Annual Circulation", "Total items circulated per year", "circulation", "items", 150000, 120000, 138000, "monthly"),
            ("Program Attendance", "Total attendance at library programs", "programs", "people", 12000, 8500, 10200, "monthly"),
            ("New Library Cards", "Cards issued to new patrons", "membership", "cards", 1500, 1100, 1320, "monthly"),
            ("Digital Resource Usage", "Downloads and streams from digital platforms", "technology", "sessions", 45000, 28000, 39000, "monthly"),
            ("Website Visits", "Unique visitors to library website", "technology", "visits", 200000, 150000, 185000, "monthly"),
            ("Volunteer Hours", "Total volunteer service hours", "community", "hours", 3000, 2200, 2650, "quarterly"),
            ("Outreach Events", "Community events held outside library walls", "outreach", "events", 60, 35, 48, "quarterly"),
            ("Customer Satisfaction", "Average satisfaction score from patron surveys", "quality", "score", 4.5, 4.0, 4.3, "annually"),
        ]
        for name, desc, cat, unit, target, baseline, current, freq in kpis:
            await session.execute(text("""
                INSERT INTO strategic_kpis (plan_id, name, description, category, unit_of_measure,
                    target_value, baseline_value, current_value,
                    threshold_red, threshold_yellow, threshold_green,
                    frequency, is_active, last_updated, responsible_person_id)
                VALUES (:plan, :name, :desc, :cat, :unit,
                    :target, :baseline, :current,
                    :red, :yellow, :green,
                    :freq, true, :updated, :person)
            """), {
                "plan": plan_id, "name": name, "desc": desc, "cat": cat, "unit": unit,
                "target": target, "baseline": baseline, "current": current,
                "red": baseline * 0.8, "yellow": baseline, "green": target * 0.9,
                "freq": freq, "updated": _past(random.randint(1, 30)),
                "person": random.choice(staff_ids),
            })

        # Milestones
        milestones = [
            (goal_ids[0], "50 Public Computers Replaced", "All public workstations upgraded to current-gen hardware.", True, 180),
            (goal_ids[0], "100th Digital Literacy Graduate", "Celebrated the 100th patron to complete the full workshop series.", True, 90),
            (goal_ids[1], "Teen Advisory Board First Meeting", "12 teens showed up for the inaugural TAB meeting — exceeded expectations.", True, 150),
            (goal_ids[2], "All 8 Schools Visited", "Completed initial outreach visits to every elementary school in the district.", False, 0),
            (goal_ids[4], "DEI Committee Chartered", "Board approved the staff DEI committee charter and first-year work plan.", True, 200),
        ]
        for gid, title, desc, achieved, days_ago in milestones:
            params = {
                "plan": plan_id, "goal": gid, "title": title, "desc": desc,
                "public": True, "featured": achieved, "type": "achievement",
                "approval": "approved", "creator": admin_id,
            }
            if achieved:
                params["achieved"] = _past(days_ago)
                params["celebration"] = f"We're proud to announce: {title}!"
            else:
                params["achieved"] = None
                params["celebration"] = None

            await session.execute(text("""
                INSERT INTO strategic_milestones (plan_id, goal_id, title, description,
                    achieved_date, celebration_text, is_public, is_featured,
                    milestone_type, approval_status, created_by_id)
                VALUES (:plan, :goal, :title, :desc,
                    :achieved, :celebration, :public, :featured,
                    :type, :approval, :creator)
            """), params)

        # Strategic Metrics (per-goal measures)
        for gid in goal_ids:
            for name, unit, target, current in [
                ("Progress Score", "percent", 100, random.randint(30, 70)),
                ("Budget Utilization", "percent", 100, random.randint(40, 85)),
                ("Community Impact Score", "score", 5.0, round(random.uniform(3.0, 4.8), 1)),
            ]:
                await session.execute(text("""
                    INSERT INTO strategic_metrics (goal_id, name, unit, target_value, current_value,
                        baseline_value, update_frequency, last_updated)
                    VALUES (:goal, :name, :unit, :target, :current, :baseline, :freq, :updated)
                """), {
                    "goal": gid, "name": name, "unit": unit, "target": target,
                    "current": current, "baseline": current * 0.6,
                    "freq": "monthly", "updated": _past(random.randint(1, 30)),
                })

        await session.commit()
        print("    Created strategic plan with 5 goals, 11 initiatives, 8 KPIs, 5 milestones, 15 metrics")

    # ════════════════════════════════════════════════════════════════
    # 2. STAFF SCHEDULING (shifts, profiles, PTO)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM staff_scheduling_profiles"))
    if r.scalar() == 0:
        print("  Seeding staff scheduling...")

        # Scheduling profiles for staff
        emp_types = ["full_time", "full_time", "full_time", "part_time", "part_time",
                     "full_time", "part_time", "full_time", "full_time", "full_time"]
        profile_staff = staff_ids[:min(10, len(staff_ids))]
        for i, sid in enumerate(profile_staff):
            emp = emp_types[i % len(emp_types)]
            hours = 40.0 if emp == "full_time" else 20.0
            await session.execute(text("""
                INSERT INTO staff_scheduling_profiles (staff_id, branch_id, employment_type,
                    contracted_hours_per_week, min_hours_per_week, max_hours_per_week,
                    skills, hire_date, seniority_level,
                    max_consecutive_days, min_hours_between_shifts,
                    max_weekend_shifts_per_month, max_closing_shifts_per_week,
                    desirable_shift_score, is_active, created_at, updated_at)
                VALUES (:sid, :branch, :emp,
                    :hours, :min_h, :max_h,
                    cast(:skills as json), :hire, :seniority,
                    :max_days, :min_between,
                    :max_weekend, :max_closing,
                    :score, true, :now, :now)
            """), {
                "sid": sid, "branch": random.choice(branch_ids), "emp": emp,
                "hours": hours, "min_h": hours * 0.8, "max_h": hours * 1.1,
                "skills": '["circulation", "reference", "programming"]',
                "hire": _past_date(random.randint(365, 3650)),
                "seniority": random.randint(1, 5),
                "max_days": 5 if emp == "full_time" else 4,
                "min_between": 10.0, "max_weekend": 2, "max_closing": 2,
                "score": round(random.uniform(0.5, 1.0), 2),
                "now": now,
            })

        # Staff shifts — past 4 weeks + next 2 weeks
        shift_types = ["opening", "mid_day", "closing"]
        shift_times = {
            "opening": (time(9, 0), time(17, 0), 8.0),
            "mid_day": (time(11, 0), time(19, 0), 8.0),
            "closing": (time(13, 0), time(21, 0), 8.0),
        }
        shift_count = 0
        for days_offset in range(-28, 14):
            shift_date = (now + timedelta(days=days_offset)).date()
            if shift_date.weekday() == 6:  # skip Sundays
                continue
            # 3-5 staff per day
            day_staff = random.sample(profile_staff, min(len(profile_staff), random.randint(3, 5)))
            for sid in day_staff:
                stype = random.choice(shift_types)
                start_t, end_t, hours = shift_times[stype]
                is_past = days_offset < 0
                status = "completed" if is_past else ("confirmed" if days_offset < 7 else "assigned")

                await session.execute(text("""
                    INSERT INTO staff_shifts (branch_id, staff_id, shift_date, shift_type, status,
                        scheduled_start, scheduled_end, actual_start, actual_end,
                        scheduled_hours, actual_hours, is_overtime, is_holiday, is_weekend, created_at, updated_at)
                    VALUES (:branch, :sid, :date, :type, :status,
                        :start, :end, :a_start, :a_end,
                        :hours, :a_hours, false, false, :weekend, :now, :now)
                """), {
                    "branch": random.choice(branch_ids), "sid": sid, "date": shift_date,
                    "type": stype, "status": status,
                    "start": start_t, "end": end_t,
                    "a_start": start_t if is_past else None,
                    "a_end": end_t if is_past else None,
                    "hours": hours, "a_hours": hours if is_past else None,
                    "weekend": shift_date.weekday() == 5,
                    "now": now,
                })
                shift_count += 1

        # PTO balances — one per user (unique constraint on user_id)
        for sid in profile_staff:
            used = random.randint(2, 10)
            await session.execute(text("""
                INSERT INTO pto_balance (user_id, pto_type, annual_allotment, accrued_days,
                    used_days, pending_days, carryover_days, carryover_limit, year, last_updated)
                VALUES (:uid, :type, :allot, :accrued, :used, :pending, :carry, :carry_limit, :year, :now)
            """), {
                "uid": sid, "type": "vacation", "allot": 15,
                "accrued": 15 * 0.25 * (now.month / 12.0),
                "used": used, "pending": random.randint(0, 2),
                "carry": random.randint(0, 3), "carry_limit": 5,
                "year": now.year, "now": now,
            })

        # PTO requests (a handful of past and future)
        pto_data = [
            ("vacation", "approved", 14, 18, "Family vacation"),
            ("sick", "approved", 5, 5, ""),
            ("vacation", "approved", 45, 49, "Holiday travel"),
            ("personal", "approved", 30, 30, "Appointment"),
            ("vacation", "submitted", -10, -6, "Spring break trip"),
            ("sick", "approved", 3, 3, ""),
            ("vacation", "submitted", -21, -14, "Conference attendance"),
        ]
        for pto_type, status, start_ago, end_ago, reason in pto_data:
            sid = random.choice(profile_staff)
            approver = random.choice([s for s in staff_ids if s != sid])
            start = _past_date(-start_ago) if start_ago < 0 else _past_date(start_ago)
            end = _past_date(-end_ago) if end_ago < 0 else _past_date(end_ago)
            if start > end:
                start, end = end, start
            await session.execute(text("""
                INSERT INTO pto_requests (user_id, start_date, end_date, pto_type, status,
                    partial_day_type, reason, approved_by, auto_delegate, has_conflicts, is_recurring)
                VALUES (:uid, :start, :end, :type, :status,
                    'FULL_DAY', :reason, :approver, false, false, false)
            """), {
                "uid": sid, "start": start, "end": end, "type": pto_type,
                "status": status, "reason": reason, "approver": approver if status == "approved" else None,
            })

        await session.commit()
        print(f"    Created {len(profile_staff)} profiles, {shift_count} shifts, PTO balances & requests")

    # ════════════════════════════════════════════════════════════════
    # 3. OUTREACH PARTNERS + VISITS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM outreach_partners"))
    if r.scalar() == 0:
        print("  Seeding outreach...")

        partners = [
            ("Oakdale Elementary School", "school", "active", "gold", "K-5", "Oakdale Unified", 420, 28),
            ("Riverside Middle School", "school", "active", "silver", "6-8", "Oakdale Unified", 580, 35),
            ("Sunrise Senior Living", "senior_center", "active", "silver", None, None, None, None),
            ("Community Action Center", "nonprofit", "active", "gold", None, None, None, None),
            ("Oakdale Head Start", "school", "active", "bronze", "Pre-K", "Oakdale Unified", 60, 8),
            ("Hope House Shelter", "nonprofit", "active", "silver", None, None, None, None),
            ("Valley View Assisted Living", "senior_center", "active", "bronze", None, None, None, None),
            ("Meadowbrook Apartments", "housing", "active", "bronze", None, None, None, None),
        ]
        partner_ids = []
        for name, ptype, status, tier, level, district, students, teachers in partners:
            r2 = await session.execute(text("""
                INSERT INTO outreach_partners (name, partner_type, status, partnership_tier,
                    city, state, school_level, school_district, student_count, teacher_count,
                    partnership_start_date, allows_bulk_checkout, allows_institutional_card,
                    requires_deposit, checkout_limit, loan_period_days, created_by_id)
                VALUES (:name, :type, :status, :tier,
                    'Oakdale', 'IL', :level, :district, :students, :teachers,
                    :start, :bulk, :inst,
                    false, :limit, :loan, :creator)
                RETURNING id
            """), {
                "name": name, "type": ptype, "status": status, "tier": tier,
                "level": level, "district": district, "students": students, "teachers": teachers,
                "start": _past_date(random.randint(180, 1000)),
                "bulk": ptype == "school", "inst": ptype == "school",
                "limit": 100 if ptype == "school" else 30,
                "loan": 28 if ptype == "school" else 21,
                "creator": admin_id,
            })
            partner_ids.append(r2.scalar())

        # Outreach visits — a few per partner
        visit_types = ["storytime", "book_delivery", "library_card_signup", "program", "collection_exchange"]
        visit_count = 0
        for pid in partner_ids:
            for v in range(random.randint(2, 5)):
                days_ago = random.randint(7, 180)
                is_past = True
                attendees = random.randint(8, 45)
                await session.execute(text("""
                    INSERT INTO outreach_visits (partner_id, visit_type, status, title, description,
                        scheduled_date, expected_attendees, actual_attendees, age_group,
                        lead_staff_id, new_cards_issued, books_checked_out,
                        follow_up_needed, is_recurring, created_by_id)
                    VALUES (:pid, :type, 'completed', :title, :desc,
                        :date, :expected, :actual, :age,
                        :lead, :cards, :books,
                        :followup, false, :creator)
                """), {
                    "pid": pid, "type": random.choice(visit_types),
                    "title": f"Visit to partner site",
                    "desc": "Regular outreach visit with materials and programming.",
                    "date": _past_date(days_ago),
                    "expected": attendees + random.randint(-5, 5),
                    "actual": attendees, "age": random.choice(["children", "teens", "adults", "seniors", "all_ages"]),
                    "lead": random.choice(staff_ids),
                    "cards": random.randint(0, 5), "books": random.randint(10, 60),
                    "followup": random.choice([True, False]),
                    "creator": admin_id,
                })
                visit_count += 1

        await session.commit()
        print(f"    Created {len(partners)} partners, {visit_count} visits")

    # ════════════════════════════════════════════════════════════════
    # 4. VISIT STATISTICS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM visit_statistics"))
    if r.scalar() == 0:
        print("  Seeding visit_statistics...")
        # Monthly stats for the past 12 months
        count = 0
        for months_ago in range(12, 0, -1):
            month = now.month - months_ago
            year = now.year
            while month <= 0:
                month += 12
                year -= 1
            period_start = date(year, month, 1)
            if month == 12:
                period_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                period_end = date(year, month + 1, 1) - timedelta(days=1)
            days_in_month = (period_end - period_start).days + 1

            # Seasonal variation
            seasonal = 1.0
            if month in [6, 7]:
                seasonal = 1.3  # summer reading bump
            elif month in [12, 1]:
                seasonal = 0.8  # holidays
            base_visits = int(4500 * seasonal + random.randint(-300, 300))

            for branch_name in ["Main Branch", "Elmdale Branch", "Jamie Chick Community Annex"]:
                branch_factor = {"Main Branch": 1.0, "Elmdale Branch": 0.5, "Jamie Chick Community Annex": 0.4}[branch_name]
                visits = int(base_visits * branch_factor)
                await session.execute(text("""
                    INSERT INTO visit_statistics (period_start, period_end, period_type, branch_location,
                        total_visits, avg_daily_visits, peak_hour, peak_day_of_week,
                        generated_at, generated_by_id)
                    VALUES (:start, :end, 'monthly', :branch,
                        :visits, :avg, :peak_h, :peak_d,
                        :gen, :gen_by)
                """), {
                    "start": period_start, "end": period_end, "branch": branch_name,
                    "visits": visits, "avg": round(visits / days_in_month, 1),
                    "peak_h": random.choice([10, 11, 14, 15]),
                    "peak_d": random.choice([1, 2, 3, 5]),  # Tue, Wed, Thu, Sat
                    "gen": _past(months_ago * 30 - 25), "gen_by": admin_id,
                })
                count += 1

        await session.commit()
        print(f"    Created {count} visit stat records")

    # ════════════════════════════════════════════════════════════════
    # 5. STORYTIME PLANS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM storytime_annual_plans"))
    if r.scalar() == 0:
        print("  Seeding storytime plans...")

        await session.execute(text("""
            INSERT INTO storytime_annual_plans (year, annual_theme, goals, special_events,
                total_sessions_planned, expected_total_attendance, estimated_budget, notes)
            VALUES (:year, :theme,
                '{"Increase attendance by 15%","Add bilingual storytime","Launch sensory-friendly sessions"}'::varchar[],
                '{"Pajama Storytime (January)","Read Across America (March)","Summer Kickoff (June)","Halloween Stories (October)"}'::varchar[],
                :sessions, :attendance, :budget, :notes)
        """), {
            "year": 2026, "theme": "Adventures in Reading",
            "sessions": 96, "attendance": 2400, "budget": 3500.0,
            "notes": "Continuing partnership with Head Start for off-site storytimes.",
        })

        themes = [
            (1, "Winter Wonders", "Seasons and weather", 8, 180),
            (2, "Love & Friendship", "Social-emotional learning", 8, 200),
            (3, "Growing Things", "Nature and science", 8, 220),
            (4, "Around the World", "Cultural awareness", 8, 210),
            (5, "Splash & Play", "Water and summer", 10, 280),
            (6, "Animal Kingdom", "Animals and habitats", 10, 300),
            (7, "Construction Zone", "Building and STEM", 8, 250),
            (8, "Back to School", "Learning and routines", 8, 220),
            (9, "Harvest Time", "Food and community", 8, 200),
            (10, "Spooky Stories", "Courage and imagination", 8, 240),
            (11, "Thankful Hearts", "Gratitude and giving", 8, 190),
            (12, "Holiday Magic", "Traditions and celebrations", 8, 200),
        ]
        for month, theme, focus, sessions, attendance in themes:
            await session.execute(text("""
                INSERT INTO storytime_monthly_plans (year, month, monthly_theme, learning_focus,
                    sessions_planned, expected_attendance, special_dates, craft_supply_needs, notes)
                VALUES (:year, :month, :theme, :focus,
                    :sessions, :attendance, '{}'::varchar[], '{}'::varchar[], :notes)
            """), {
                "year": 2026, "month": month, "theme": theme, "focus": focus,
                "sessions": sessions, "attendance": attendance,
                "notes": "",
            })

        await session.commit()
        print("    Created 1 annual plan, 12 monthly plans")

    # ════════════════════════════════════════════════════════════════
    # 6. ILL PARTNER LIBRARIES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM ill_partner_libraries"))
    if r.scalar() == 0:
        print("  Seeding ILL partner libraries...")
        libraries = [
            ("Springfield Public Library", "SPL", "Springfield", "IL", "active", 0, 0, 21, True),
            ("Champaign Public Library", "CPL", "Champaign", "IL", "active", 0, 0, 28, True),
            ("Bloomington Public Library", "BPL", "Bloomington", "IL", "active", 5.00, 5.00, 21, False),
            ("Decatur Public Library", "DPL", "Decatur", "IL", "active", 0, 0, 21, True),
            ("Peoria Public Library", "PPL", "Peoria", "IL", "active", 3.00, 3.00, 28, True),
            ("University of Illinois Library", "UIL", "Urbana", "IL", "active", 10.00, 0, 14, False),
            ("Illinois State Library", "ISL", "Springfield", "IL", "active", 0, 0, 28, True),
            ("Rockford Public Library", "RPL", "Rockford", "IL", "inactive", 5.00, 5.00, 21, False),
        ]
        for name, code, city, state, status, lend_fee, borrow_fee, days, reciprocal in libraries:
            await session.execute(text("""
                INSERT INTO ill_partner_libraries (name, code, city, state, country, status,
                    lending_fee, borrowing_fee, max_loan_days, max_renewals, reciprocal_agreement,
                    created_at, updated_at)
                VALUES (:name, :code, :city, :state, 'US', :status,
                    :lend, :borrow, :days, :renew, :recip,
                    :now, :now)
            """), {
                "name": name, "code": code, "city": city, "state": state,
                "status": status, "lend": lend_fee, "borrow": borrow_fee,
                "days": days, "renew": 1, "recip": reciprocal, "now": now,
            })

        await session.commit()
        print(f"    Created {len(libraries)} ILL partner libraries")

    # ════════════════════════════════════════════════════════════════
    # 7. EQUIPMENT (makerspace/lending)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM equipment"))
    if r.scalar() == 0:
        print("  Seeding equipment...")
        equip = [
            ("Cricut Maker 3", "Cutting machine for vinyl, paper, and fabric", "makerspace", "CRICUT-001", "CRT001", "Cricut", "Maker 3", "available", "good", 7, 5.00, 399.99),
            ("3D Printer - Prusa MK4", "FDM 3D printer for prototyping and projects", "makerspace", "3DP-001", "3DP001", "Prusa", "MK4", "available", "good", 0, 0, 799.00),
            ("Sewing Machine - Singer", "Basic sewing machine for textile projects", "makerspace", "SEW-001", "SEW001", "Singer", "Heavy Duty 4423", "available", "good", 7, 3.00, 179.99),
            ("Canon DSLR Camera Kit", "DSLR camera with 2 lenses and tripod", "lending", "CAM-001", "CAM001", "Canon", "EOS Rebel T8i", "available", "good", 7, 10.00, 899.99),
            ("Hotspot - T-Mobile", "Portable WiFi hotspot with unlimited data", "lending", "HS-001", "HS001", "T-Mobile", "Inseego 5G", "checked_out", "good", 21, 0, 149.99),
            ("Hotspot - T-Mobile", "Portable WiFi hotspot with unlimited data", "lending", "HS-002", "HS002", "T-Mobile", "Inseego 5G", "available", "good", 21, 0, 149.99),
            ("iPad + Keyboard", "iPad Air with keyboard case for checkout", "lending", "IPAD-001", "IPAD01", "Apple", "iPad Air M1", "available", "good", 14, 5.00, 649.99),
            ("Telescope - Orion StarBlast", "Tabletop reflector telescope for stargazing", "lending", "TELE-001", "TEL001", "Orion", "StarBlast 4.5", "available", "good", 14, 5.00, 249.99),
            ("Kill A Watt Energy Monitor", "Measures electricity usage of appliances", "lending", "ENERGY-001", "ENR001", "P3", "Kill A Watt", "available", "excellent", 14, 0, 29.99),
            ("Radon Test Kit", "Home radon detection kit", "lending", "RADON-001", "RAD001", "Safety Siren", "Pro Series", "available", "good", 14, 0, 39.99),
            ("Cake Pans Set", "Assorted specialty cake pans (12 shapes)", "lending", "CAKE-001", "CAKE01", "Wilton", "Various", "available", "good", 7, 0, 89.99),
            ("Metal Detector", "Beach and yard metal detector", "lending", "METAL-001", "MET001", "Garrett", "Ace 300", "available", "good", 7, 0, 249.99),
        ]
        for name, desc, etype, serial, barcode, mfr, model, status, condition, max_days, fine, cost in equip:
            await session.execute(text("""
                INSERT INTO equipment (name, description, equipment_type, serial_number, barcode,
                    manufacturer, model, status, condition,
                    requires_agreement, max_checkout_days, fine_per_day, max_renewals,
                    deposit_required, deposit_refundable, replacement_cost, purchase_price,
                    location, home_location, total_checkouts, is_high_demand,
                    created_at, created_by_id)
                VALUES (:name, :desc, :type, :serial, :barcode,
                    :mfr, :model, :status, :cond,
                    :agreement, :max_days, :fine, 1,
                    :deposit, true, :cost, :cost,
                    'Main Branch', 'Main Branch', :checkouts, :demand,
                    :now, :creator)
            """), {
                "name": name, "desc": desc, "type": etype, "serial": serial, "barcode": barcode,
                "mfr": mfr, "model": model, "status": status, "cond": condition,
                "agreement": etype == "lending", "max_days": max_days, "fine": fine,
                "deposit": cost > 200, "cost": cost,
                "checkouts": random.randint(5, 40), "demand": cost > 300,
                "now": now, "creator": admin_id,
            })

        await session.commit()
        print(f"    Created {len(equip)} equipment items")

    # ════════════════════════════════════════════════════════════════
    # 8. PATRON ACTIVITIES (recent activity log)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM patron_activities"))
    if r.scalar() == 0 and catalog_ids:
        print("  Seeding patron_activities...")
        activity_types = ["checkout", "return_item", "hold_placed", "hold_fulfilled",
                          "renewal", "fine_paid", "account_created", "profile_updated"]
        count = 0
        for _ in range(200):
            uid = random.choice(all_ids)
            atype = random.choice(activity_types)
            cid = random.choice(catalog_ids) if atype in ("checkout", "return_item", "hold_placed", "hold_fulfilled", "renewal") else None
            await session.execute(text("""
                INSERT INTO patron_activities (patron_id, staff_id, activity_type, description,
                    item_id, created_at, updated_at)
                VALUES (:patron, :staff, :type, :desc, :item, :created, :created)
            """), {
                "patron": uid,
                "staff": random.choice(staff_ids) if atype in ("checkout", "return_item", "fine_paid") else None,
                "type": atype,
                "desc": {
                    "checkout": "Item checked out", "return_item": "Item returned",
                    "hold_placed": "Hold placed", "hold_fulfilled": "Hold ready for pickup",
                    "renewal": "Item renewed", "fine_paid": "Fine payment received",
                    "account_created": "New patron account created",
                    "profile_updated": "Patron updated contact information",
                }[atype],
                "item": cid,
                "created": _past(random.randint(0, 180)),
            })
            count += 1

        await session.commit()
        print(f"    Created {count} patron activity records")

    # ════════════════════════════════════════════════════════════════
    # FIX SEQUENCES
    # ════════════════════════════════════════════════════════════════
    seq_tables = [
        "strategic_plans", "strategic_goals", "strategic_initiatives", "strategic_kpis",
        "strategic_milestones", "strategic_metrics",
        "staff_scheduling_profiles", "staff_shifts", "pto_balance", "pto_requests",
        "outreach_partners", "outreach_visits", "visit_statistics",
        "storytime_annual_plans", "storytime_monthly_plans",
        "ill_partner_libraries", "equipment", "patron_activities",
    ]
    for table in seq_tables:
        # Best-effort sequence fix; tables that don't exist or lack an
        # id sequence are silently skipped during seeding.
        with contextlib.suppress(SQLAlchemyError):
            await session.execute(text(
                f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
            ))

    await session.commit()
    print("  Medium domains seeding complete!")
    return True
