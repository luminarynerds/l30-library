# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

utc = timezone.utc


def _past(days: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days)


def _future(days: int) -> datetime:
    return datetime.now(utc) + timedelta(days=days)


def _d(s: str) -> str:
    return s


def _ts(days_ago: int = 0, hour: int = 10) -> str:
    dt = datetime.now(utc) - timedelta(days=days_ago)
    return dt.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()


async def seed_missing_data(session: AsyncSession) -> bool:

    # --- Grab reusable IDs ---
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] in ("patron", "child")]

    branches_r = await session.execute(text("SELECT id FROM branches"))
    branch_ids = [r[0] for r in branches_r.fetchall()]

    items_r = await session.execute(text("SELECT id FROM item_copies LIMIT 30"))
    item_copy_ids = [r[0] for r in items_r.fetchall()]

    catalog_r = await session.execute(text("SELECT id FROM catalog_items LIMIT 30"))
    catalog_ids = [r[0] for r in catalog_r.fetchall()]

    meetings_r = await session.execute(text("SELECT id FROM board_meetings ORDER BY id LIMIT 6"))
    meeting_ids = [r[0] for r in meetings_r.fetchall()]

    serial_titles_r = await session.execute(text("SELECT id FROM serial_titles"))
    serial_title_ids = [r[0] for r in serial_titles_r.fetchall()]

    partner_libs_r = await session.execute(text("SELECT id FROM ill_partner_libraries"))
    partner_lib_ids = [r[0] for r in partner_libs_r.fetchall()]

    storytime_series_r = await session.execute(text("SELECT id FROM storytime_series LIMIT 1"))
    storytime_series_ids = [r[0] for r in storytime_series_r.fetchall()]

    if not staff_ids or not patron_ids or not branch_ids:
        print("  Skipping missing data seed -- no staff/patrons/branches")
        return False

    s1, s2, s3 = staff_ids[0], staff_ids[min(1, len(staff_ids)-1)], staff_ids[min(2, len(staff_ids)-1)]
    p1, p2, p3, p4, p5 = (patron_ids[i % len(patron_ids)] for i in range(5))
    b1, b2, b3 = branch_ids[0], branch_ids[min(1, len(branch_ids)-1)], branch_ids[min(2, len(branch_ids)-1)]

    # ========== PRINTERS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM printers"))
    if r.scalar() == 0:
        print("  Seeding printers...")
        await session.execute(text("""
            INSERT INTO printers (name, device_id, printer_type, model, status, location, 
                supports_color, supports_double_sided, black_toner_level, color_toner_level, 
                paper_level, total_jobs, total_pages_printed, total_color_pages, total_revenue,
                low_toner_threshold, low_paper_threshold, has_low_toner_alert, has_low_paper_alert,
                is_enabled)
            VALUES
            ('Main Floor Laser', 'PRT-MAIN-01', 'laser', 'HP LaserJet Pro M404dn', 'online', 
                'Main Floor - Near Circulation Desk', false, true, 72.0, NULL, 85.0,
                14523, 38291, 0, 1914.55, 20.0, 15.0, false, false, true),
            ('Main Floor Color', 'PRT-MAIN-02', 'laser', 'HP Color LaserJet Pro M454dw', 'online',
                'Main Floor - Near Reference', true, true, 65.0, 58.0, 70.0,
                8934, 21456, 12890, 3218.40, 20.0, 15.0, false, false, true),
            ('Teen Zone Printer', 'PRT-TEEN-01', 'laser', 'Brother HL-L2350DW', 'online',
                'Teen Zone - Upper Floor', false, true, 45.0, NULL, 60.0,
                3201, 8540, 0, 427.00, 20.0, 15.0, false, false, true),
            ('Children''s Printer', 'PRT-KIDS-01', 'inkjet', 'Epson EcoTank ET-2850', 'online',
                'Children''s Library', true, false, 80.0, 75.0, 90.0,
                1823, 4210, 3890, 210.50, 20.0, 15.0, false, false, true),
            ('Staff Workroom Printer', 'PRT-STAFF-01', 'multifunction', 'Xerox VersaLink C405', 'online',
                'Staff Workroom', true, true, 55.0, 50.0, 40.0,
                22451, 67302, 15230, 0.00, 20.0, 15.0, false, false, true),
            ('Elmdale Branch Printer', 'PRT-NORTH-01', 'laser', 'HP LaserJet Pro M404dn', 'maintenance',
                'Elmdale Branch - Public Area', false, true, 18.0, NULL, 30.0,
                6780, 18920, 0, 946.00, 20.0, 15.0, true, false, true)
        """))

    # ========== VENDORS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM vendors"))
    if r.scalar() == 0:
        print("  Seeding vendors...")
        await session.execute(text("""
            INSERT INTO vendors (name, contact_name, email, phone, address, account_number, notes, is_active)
            VALUES
            ('Baker & Taylor', 'Sarah Mitchell', 'orders@btol.com', '800-775-1800',
                '2550 West Tyvola Rd, Charlotte, NC 28217', 'BT-L30-4521',
                'Primary book distributor. Net 30 terms.', true),
            ('Ingram Content Group', 'James Park', 'library.sales@ingramcontent.com', '800-937-8200',
                'One Ingram Blvd, La Vergne, TN 37086', 'ICG-89234',
                'Secondary distributor, good for rush orders.', true),
            ('Midwest Tape / hoopla', 'Customer Service', 'library@midwesttape.com', '800-875-2785',
                '6950 Hall St, Holland, OH 43528', 'MWT-L30-112',
                'AV materials and hoopla digital streaming.', true),
            ('Demco', 'Library Supplies Team', 'custserv@demco.com', '800-356-1200',
                '4810 Forest Run Rd, Madison, WI 53704', 'DEM-7834',
                'Supplies, furniture, processing materials.', true),
            ('Brodart', 'Order Dept', 'orders@brodart.com', '800-233-8467',
                '500 Arch St, Williamsport, PA 17701', 'BRD-L30-556',
                'Book processing, covers, and cataloging supplies.', true),
            ('HF Group (formerly Hertzberg-New Method)', 'Bindery Services', 'bindery@hfrg.com', '800-435-6575',
                '333 N Plankinton Ave, Milwaukee, WI 53203', 'HFG-2918',
                'Book binding and repair services.', true)
        """))

    # ========== VOLUNTEERS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM volunteers"))
    if r.scalar() == 0:
        print("  Seeding volunteers...")
        # Use patron IDs as volunteer user_ids
        vol_patrons = patron_ids[:8] if len(patron_ids) >= 8 else patron_ids
        for i, uid in enumerate(vol_patrons):
            roles = ['shelving', 'programming', 'tech_support', 'delivery',
                     'reader_advisory', 'community_outreach', 'patron_services', 'makerspace']
            statuses = ['active', 'active', 'active', 'active', 'active', 'inactive', 'on_leave', 'pending_approval']
            await session.execute(text("""
                INSERT INTO volunteers (user_id, status, primary_role_category, secondary_role_categories, phone,
                    emergency_contact_name, emergency_contact_phone, emergency_contact_relationship,
                    max_hours_per_week, total_hours, total_shifts, background_check_required,
                    approved_at, approved_by_id)
                VALUES (:uid, :status, :role, :sec_roles, :phone, :ec_name, :ec_phone, :ec_rel,
                    :max_hrs, :total_hrs, :total_shifts, true, :approved_at, :approved_by)
            """), {
                "uid": uid,
                "status": statuses[i],
                "role": roles[i],
                "sec_roles": [],
                "phone": f"555-{100+i:03d}-{1000+i*111:04d}",
                "ec_name": f"Emergency Contact {i+1}",
                "ec_phone": f"555-{200+i:03d}-{2000+i*111:04d}",
                "ec_rel": ["Spouse", "Parent", "Sibling", "Partner", "Friend", "Parent", "Spouse", "Sibling"][i],
                "max_hrs": [8, 10, 6, 12, 8, 10, 8, 6][i],
                "total_hrs": [120.5, 89.0, 45.5, 210.0, 67.0, 34.0, 0.0, 0.0][i],
                "total_shifts": [48, 35, 18, 84, 27, 14, 0, 0][i],
                "approved_at": _past([180, 120, 90, 365, 60, 200, 30, 0][i]) if statuses[i] not in ('pending_approval',) else None,
                "approved_by": s1 if statuses[i] not in ('pending_approval',) else None,
            })

    # ========== TEEN VOLUNTEERS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM teen_volunteers"))
    if r.scalar() == 0:
        print("  Seeding teen volunteers...")
        teen_patrons = patron_ids[8:13] if len(patron_ids) >= 13 else patron_ids[-5:]
        teen_data = [
            ("pending_approval", "Maple Ridge High", "10th Grade", "active"),
            ("active", "Somewhere Up North Secondary", "11th Grade", "active"),
            ("active", "Northside Academy", "9th Grade", "active"),
            ("active", "Somewhere Up North Secondary", "12th Grade", "active"),
            ("inactive", "Maple Ridge High", "11th Grade", "completed"),
        ]
        for i, uid in enumerate(teen_patrons):
            status, school, grade, _ = teen_data[i]
            await session.execute(text("""
                INSERT INTO teen_volunteers (user_id, status, date_of_birth, age_at_registration,
                    school_name, grade_level, guardian_name, guardian_email, guardian_phone,
                    guardian_relationship, interests, strengths, preferred_task_types, available_days, max_hours_per_week,
                    total_service_hours, total_verified_hours, total_tasks_completed, training_completed,
                    safety_acknowledgment, background_check_completed)
                VALUES (:uid, :status, :dob, :age, :school, :grade,
                    :gname, :gemail, :gphone, :grel, :interests, :strengths, :task_types, :days, :max_hrs,
                    :total_hrs, :verified_hrs, :tasks, :training, :safety, :bg)
            """), {
                "uid": uid,
                "status": status,
                "dob": date(2010 + i % 3, 3 + i, 15),
                "age": 14 + i % 3,
                "school": school,
                "grade": grade,
                "gname": f"Parent {i+1} Guardian",
                "gemail": f"parent{i+1}@email.com",
                "gphone": f"555-300-{3000+i:04d}",
                "grel": "Parent",
                "interests": ["reading","technology","art"] if i % 2 == 0 else ["sports","community","leadership"],
                "strengths": ["creative","detail-oriented"],
                "task_types": ["shelving","tech_help"],
                "days": ["Monday","Wednesday","Friday"] if i % 2 == 0 else ["Tuesday","Thursday"],
                "max_hrs": 8,
                "total_hrs": [0, 45.5, 32.0, 78.5, 120.0][i],
                "verified_hrs": [0, 40.0, 28.0, 70.0, 110.0][i],
                "tasks": [0, 18, 12, 31, 48][i],
                "training": status != "pending_approval",
                "safety": status != "pending_approval",
                "bg": status != "pending_approval",
            })

    # ========== TEEN ADVISORY BOARD ==========
    r = await session.execute(text("SELECT COUNT(*) FROM teen_advisory_board_members"))
    if r.scalar() == 0:
        tv_r = await session.execute(text("SELECT id FROM teen_volunteers WHERE status = 'active' LIMIT 3"))
        tv_ids = [r[0] for r in tv_r.fetchall()]
        if tv_ids:
            print("  Seeding teen advisory board...")
            positions = ["President", "Vice-President", "Member"]
            for i, tvid in enumerate(tv_ids):
                await session.execute(text("""
                    INSERT INTO teen_advisory_board_members (volunteer_id, term_start, term_end,
                        position, total_meetings_attended, total_meetings_held, attendance_percentage,
                        initiatives_proposed, has_voting_rights, is_active)
                    VALUES (:vid, :start, :end, :pos, :attended, :held, :pct, :init, true, true)
                """), {
                    "vid": tvid,
                    "start": date(2026, 1, 1),
                    "end": date(2026, 12, 31),
                    "pos": positions[i],
                    "attended": [8, 7, 6][i],
                    "held": 9,
                    "pct": [88.9, 77.8, 66.7][i],
                    "init": [3, 2, 1][i],
                })

    # ========== MAKERSPACE RESOURCES ==========
    r = await session.execute(text("SELECT COUNT(*) FROM makerspace_resources"))
    if r.scalar() == 0:
        print("  Seeding makerspace resources...")
        await session.execute(text("""
            INSERT INTO makerspace_resources (name, description, resource_type, location, asset_tag,
                manufacturer, model, status, requires_certification, minimum_age,
                hourly_cost, setup_fee, max_reservation_hours, min_reservation_hours,
                advance_booking_days, buffer_minutes, available_from, available_until,
                available_days, total_reservations, total_hours_used, total_revenue,
                maintenance_interval_days, is_active)
            VALUES
            ('Prusa i3 MK3S+ #1', 'FDM 3D printer with auto bed leveling. PLA/PETG/TPU capable.',
                'printer_3d', 'Makerspace - 3D Printing Station', 'MKR-3D-001',
                'Prusa Research', 'i3 MK3S+', 'available', true, 14, 2.00, 0.00, 4, 1, 14, 15, '09:00', '20:00', '{0,1,2,3,4,5}', 0, 0, 0.00, 90, true),
            ('Prusa i3 MK3S+ #2', 'FDM 3D printer, identical to #1. Good for batch printing.',
                'printer_3d', 'Makerspace - 3D Printing Station', 'MKR-3D-002',
                'Prusa Research', 'i3 MK3S+', 'available', true, 14, 2.00, 0.00, 4, 1, 14, 15, '09:00', '20:00', '{0,1,2,3,4,5}', 0, 0, 0.00, 90, true),
            ('Glowforge Pro', '45W CO2 laser cutter/engraver. Cuts wood, acrylic, leather.',
                'laser_cutter', 'Makerspace - Laser Room', 'MKR-LS-001',
                'Glowforge', 'Pro', 'available', true, 16, 5.00, 0.00, 2, 1, 14, 15, '10:00', '19:00', '{0,1,2,3,4,5}', 0, 0, 0.00, 30, true),
            ('Cricut Maker 3', 'Precision vinyl and fabric cutter. Great for signs, decals, iron-ons.',
                'vinyl_cutter', 'Makerspace - Craft Area', 'MKR-VC-001',
                'Cricut', 'Maker 3', 'available', true, 12, 0.00, 0.00, 3, 1, 14, 15, '09:00', '20:00', '{0,1,2,3,4,5}', 0, 0, 0.00, 90, true),
            ('Brother PE800 Embroidery', '5x7 inch embroidery field, 138 built-in designs.',
                'embroidery_machine', 'Makerspace - Sewing Corner', 'MKR-EM-001',
                'Brother', 'PE800', 'available', true, 14, 0.00, 0.00, 3, 1, 14, 15, '09:00', '20:00', '{0,1,2,3,4,5}', 0, 0, 0.00, 90, true),
            ('Soldering Station', 'Hakko FX-888D digital soldering station with fume extractor.',
                'soldering_station', 'Makerspace - Electronics Bench', 'MKR-SOL-001',
                'Hakko', 'FX-888D', 'available', true, 16, 0.00, 0.00, 2, 1, 14, 15, '10:00', '19:00', '{0,1,2,3,4,5}', 0, 0, 0.00, 30, true),
            ('Audio Recording Studio', 'Soundproofed room with Focusrite interface, condenser mic, monitors.',
                'recording_studio', 'Makerspace - Studio Room', 'MKR-STU-001',
                'Various', 'Focusrite Scarlett 2i2 + AT2020', 'available', true, 14, 0.00, 0.00, 2, 1, 14, 15, '10:00', '20:00', '{0,1,2,3,4,5}', 0, 0, 0.00, 90, true),
            ('VR Workstation', 'Meta Quest 3 with dedicated play space and PC tether option.',
                'vr_station', 'Makerspace - VR Area', 'MKR-VR-001',
                'Meta', 'Quest 3', 'maintenance', false, 10, 0.00, 0.00, 1, 1, 14, 15, '10:00', '19:00', '{0,1,2,3,4,5}', 0, 0, 0.00, 90, true)
        """))

    # ========== MAKERSPACE WORKSHOPS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM makerspace_workshops"))
    if r.scalar() == 0:
        print("  Seeding makerspace workshops...")
        workshops = [
            ("Intro to 3D Printing", "Learn the basics of FDM 3D printing with our Prusa printers. Design a simple keychain.",
             "Get started with 3D printing", 120, "Makerspace - 3D Printing Station", "beginner", 8),
            ("Laser Cutting 101", "Safety orientation and first project on the Glowforge. Required before solo use.",
             "Learn laser cutting safety and basics", 90, "Makerspace - Laser Room", "beginner", 6),
            ("Vinyl Sticker Workshop", "Design and cut custom vinyl stickers and decals using the Cricut Maker.",
             "Create custom vinyl designs", 90, "Makerspace - Craft Area", "beginner", 10),
            ("Intermediate 3D Printing", "Multi-color prints, support structures, and advanced slicer settings.",
             "Level up your 3D printing skills", 120, "Makerspace - 3D Printing Station", "intermediate", 6),
            ("Intro to Soldering", "Learn to solder through-hole components. Build a blinking LED circuit.",
             "Build your first electronic circuit", 120, "Makerspace - Electronics Bench", "beginner", 6),
            ("Podcast Recording Workshop", "Record, edit, and publish a short podcast episode using our studio.",
             "Create your first podcast episode", 150, "Makerspace - Studio Room", "beginner", 4),
        ]
        for i, (title, desc, short, dur, loc, level, cap) in enumerate(workshops):
            start = _future(7 + i * 7)
            await session.execute(text("""
                INSERT INTO makerspace_workshops (title, description, short_description,
                    start_time, end_time, duration_minutes, location, skill_level,
                    max_participants, min_participants, current_participants, allow_waitlist,
                    waitlist_count, instructor_id, instructor_name, is_virtual,
                    is_certification_training, age_requirement, fee, materials_fee,
                    materials_included, registration_required, cancellation_deadline_hours,
                    status, is_recurring)
                VALUES (:title, :desc, :short, :start, :end, :dur, :loc, :level,
                    :cap, 1, 0, true, 0, :instr, :iname, false,
                    false, 14, 0.00, 0.00, true, true, 24, 'published', false)
            """), {
                "title": title, "desc": desc, "short": short,
                "start": start.replace(hour=14, minute=0),
                "end": start.replace(hour=14, minute=0) + timedelta(minutes=dur),
                "dur": dur, "loc": loc, "level": level, "cap": cap,
                "instr": s1, "iname": "Library Makerspace Staff",
            })

    # ========== COMIC SERIES + ISSUES ==========
    r = await session.execute(text("SELECT COUNT(*) FROM comic_series"))
    if r.scalar() == 0:
        print("  Seeding comic series...")
        series_data = [
            ("Saga", "Image Comics", "single_issue", True, 2012, None, 66,
             ["science fiction","fantasy","drama"], ["Alana","Marko","Hazel"]),
            ("Maus", "Pantheon Books", "graphic_novel", False, 1980, 1991, 2,
             ["memoir","historical","drama"], ["Vladek","Art"]),
            ("Ms. Marvel (Kamala Khan)", "Marvel Comics", "single_issue", False, 2014, 2019, 38,
             ["superhero","coming-of-age"], ["Kamala Khan"]),
            ("Lumberjanes", "BOOM! Studios", "single_issue", False, 2014, 2020, 75,
             ["adventure","humor","lgbtq"], ["Jo","April","Mal","Molly","Ripley"]),
            ("March", "Top Shelf Productions", "graphic_novel", False, 2013, 2016, 3,
             ["historical","memoir","civil rights"], ["John Lewis"]),
        ]
        for title, pub, fmt, ongoing, start_yr, end_yr, total, genres, chars in series_data:
            await session.execute(text("""
                INSERT INTO comic_series (title, publisher, comic_format, is_ongoing,
                    first_publication_year, last_publication_year, total_issues_published,
                    genres, characters)
                VALUES (:title, :pub, :fmt, :ongoing, :start, :end, :total, :genres, :chars)
            """), {
                "title": title, "pub": pub, "fmt": fmt, "ongoing": ongoing,
                "start": start_yr, "end": end_yr, "total": total,
                "genres": genres, "chars": chars,
            })

        # Add comic issues linked to catalog items
        series_r = await session.execute(text("SELECT id, title FROM comic_series"))
        series_map = {r[1]: r[0] for r in series_r.fetchall()}

        if catalog_ids:
            print("  Seeding comic issues...")
            issues = [
                ("Saga", "1", "Brian K. Vaughan", "Fiona Staples"),
                ("Saga", "2", "Brian K. Vaughan", "Fiona Staples"),
                ("Saga", "3", "Brian K. Vaughan", "Fiona Staples"),
                ("Maus", "1", "Art Spiegelman", "Art Spiegelman"),
                ("Maus", "2", "Art Spiegelman", "Art Spiegelman"),
                ("Ms. Marvel (Kamala Khan)", "1", "G. Willow Wilson", "Adrian Alphona"),
                ("Ms. Marvel (Kamala Khan)", "2", "G. Willow Wilson", "Adrian Alphona"),
                ("Ms. Marvel (Kamala Khan)", "3", "G. Willow Wilson", "Adrian Alphona"),
                ("Lumberjanes", "1", "Noelle Stevenson", "Brooklyn Allen"),
                ("Lumberjanes", "2", "Noelle Stevenson", "Brooklyn Allen"),
                ("Lumberjanes", "3", "Shannon Watters", "Brooklyn Allen"),
                ("March", "1", "John Lewis & Andrew Aydin", "Nate Powell"),
                ("March", "2", "John Lewis & Andrew Aydin", "Nate Powell"),
                ("March", "3", "John Lewis & Andrew Aydin", "Nate Powell"),
            ]
            for i, (series_title, issue_num, writer, artist) in enumerate(issues):
                sid = series_map.get(series_title)
                cid = catalog_ids[i % len(catalog_ids)]
                if sid:
                    await session.execute(text("""
                        INSERT INTO comic_issues (series_id, catalog_item_id, issue_number,
                            writers, artists, page_count, is_color)
                        VALUES (:sid, :cid, :num, :writers, :artists, :pages, true)
                        ON CONFLICT (series_id, issue_number) DO NOTHING
                    """), {
                        "sid": sid, "cid": cid, "num": issue_num,
                        "writers": [writer],
                        "artists": [artist],
                        "pages": 32 if issue_num != "1" else 48,
                    })

    # ========== STORYTIME CONTENT ==========
    # Themes
    r = await session.execute(text("SELECT COUNT(*) FROM storytime_themes"))
    if r.scalar() == 0 and storytime_series_ids:
        print("  Seeding storytime themes...")
        ssid = storytime_series_ids[0]
        themes = [
            ("Animals on the Farm", "Barnyard animals, sounds, and habitats", "#4CAF50"),
            ("Under the Sea", "Ocean creatures and underwater adventures", "#2196F3"),
            ("Space Explorers", "Planets, stars, and astronauts", "#673AB7"),
            ("Friendship", "Making friends and being kind", "#FF9800"),
            ("Colors Everywhere", "Learning colors through stories and songs", "#F44336"),
            ("Weather and Seasons", "Rain, sun, snow, and seasonal changes", "#00BCD4"),
            ("Family Love", "Different families and family traditions", "#E91E63"),
            ("Bugs and Butterflies", "Insects, metamorphosis, and gardens", "#8BC34A"),
        ]
        for title, desc, color in themes:
            await session.execute(text("""
                INSERT INTO storytime_themes (series_id, title, description, theme_color, 
                    discussion_points, song_ids, rhyme_ids, craft_ids, times_used)
                VALUES (:sid, :title, :desc, :color, :disc, :songs, :rhymes, :crafts, :used)
            """), {"sid": ssid, "title": title, "desc": desc, "color": color,
                   "disc": [], "songs": [], "rhymes": [], "crafts": [], "used": 0})

    # Books
    r = await session.execute(text("SELECT COUNT(*) FROM storytime_books"))
    if r.scalar() == 0:
        print("  Seeding storytime books...")
        books = [
            ("Brown Bear, Brown Bear, What Do You See?", "Bill Martin Jr.", "Eric Carle", "9780805047905", ["toddler","preschool"], 200, 28),
            ("The Very Hungry Caterpillar", "Eric Carle", "Eric Carle", "9780399226908", ["toddler","preschool"], 224, 26),
            ("Goodnight Moon", "Margaret Wise Brown", "Clement Hurd", "9780064430173", ["baby","toddler"], 131, 32),
            ("Where the Wild Things Are", "Maurice Sendak", "Maurice Sendak", "9780060254926", ["preschool","kindergarten"], 338, 48),
            ("Chicka Chicka Boom Boom", "Bill Martin Jr.", "Lois Ehlert", "9781442450707", ["toddler","preschool"], 168, 36),
            ("The Snowy Day", "Ezra Jack Keats", "Ezra Jack Keats", "9780670867332", ["preschool","kindergarten"], 319, 32),
            ("Corduroy", "Don Freeman", "Don Freeman", "9780140501735", ["preschool","kindergarten"], 694, 32),
            ("If You Give a Mouse a Cookie", "Laura Numeroff", "Felicia Bond", "9780060245863", ["preschool","kindergarten"], 291, 32),
            ("Pete the Cat: I Love My White Shoes", "Eric Litwin", "James Dean", "9780061906220", ["preschool","kindergarten"], 250, 40),
            ("Dragon Loves Tacos", "Adam Rubin", "Daniel Salmieri", "9780803736801", ["preschool","kindergarten"], 300, 40),
            ("The Giving Tree", "Shel Silverstein", "Shel Silverstein", "9780060256654", ["preschool","school_age"], 621, 64),
            ("Press Here", "Herve Tullet", "Herve Tullet", "9780811879545", ["toddler","preschool"], 56, 56),
        ]
        for title, author, illus, isbn, ages, wc, pages in books:
            await session.execute(text("""
                INSERT INTO storytime_books (title, author, illustrator, isbn, age_groups,
                    word_count, page_count, is_in_collection, times_read)
                VALUES (:title, :author, :illus, :isbn, :ages, :wc, :pages, true, :read)
            """), {
                "title": title, "author": author, "illus": illus, "isbn": isbn,
                "ages": ages, "wc": wc, "pages": pages, "read": 0,
            })

    # Songs
    r = await session.execute(text("SELECT COUNT(*) FROM storytime_songs"))
    if r.scalar() == 0:
        print("  Seeding storytime songs...")
        songs = [
            ("Wheels on the Bus", "Traditional", ["toddler","preschool"], ["transportation","movement"],
             "The wheels on the bus go round and round,\nRound and round, round and round.\nThe wheels on the bus go round and round,\nAll through the town.",
             "Rolling hand motions, opening/closing doors, wipers"),
            ("If You're Happy and You Know It", "Traditional", ["toddler","preschool"], ["feelings","movement"],
             "If you're happy and you know it, clap your hands!\nIf you're happy and you know it, clap your hands!\nIf you're happy and you know it, and you really want to show it,\nIf you're happy and you know it, clap your hands!",
             "Clapping, stomping, shouting hooray"),
            ("Head, Shoulders, Knees and Toes", "Traditional", ["toddler","preschool"], ["body","movement"],
             "Head, shoulders, knees and toes, knees and toes.\nHead, shoulders, knees and toes, knees and toes.\nAnd eyes and ears and mouth and nose.\nHead, shoulders, knees and toes, knees and toes.",
             "Touch each body part as named, speed up each verse"),
            ("Old MacDonald Had a Farm", "Traditional", ["baby","toddler","preschool"], ["animals","farm"],
             "Old MacDonald had a farm, E-I-E-I-O!\nAnd on his farm he had a cow, E-I-E-I-O!\nWith a moo moo here and a moo moo there,\nHere a moo, there a moo, everywhere a moo moo.",
             "Animal sounds and motions"),
            ("Twinkle, Twinkle, Little Star", "Jane Taylor", ["baby","toddler"], ["night","nature"],
             "Twinkle, twinkle, little star,\nHow I wonder what you are!\nUp above the world so high,\nLike a diamond in the sky.",
             "Opening/closing hands like twinkling stars"),
            ("The Itsy Bitsy Spider", "Traditional", ["baby","toddler","preschool"], ["animals","weather"],
             "The itsy bitsy spider climbed up the water spout.\nDown came the rain and washed the spider out.\nOut came the sun and dried up all the rain,\nAnd the itsy bitsy spider climbed up the spout again.",
             "Finger climbing, rain falling, sun spreading"),
            ("Five Little Ducks", "Traditional", ["toddler","preschool"], ["animals","counting"],
             "Five little ducks went out one day,\nOver the hills and far away.\nMother duck said quack quack quack quack,\nBut only four little ducks came back.",
             "Hold up fingers counting down, duck quacking motion"),
            ("Baby Shark", "Traditional/Pinkfong", ["baby","toddler","preschool"], ["animals","ocean","movement"],
             "Baby shark, doo doo doo doo doo doo.\nBaby shark, doo doo doo doo doo doo.\nBaby shark, doo doo doo doo doo doo.\nBaby shark!",
             "Hand motions for each shark size - baby (pinch), mama (clap), daddy (arms)"),
        ]
        for title, composer, ages, themes, lyrics, movements in songs:
            await session.execute(text("""
                INSERT INTO storytime_songs (title, composer, age_groups, themes, lyrics,
                    movement_suggestions, times_used)
                VALUES (:title, :composer, :ages, :themes, :lyrics, :movements, 0)
            """), {
                "title": title, "composer": composer, "ages": ages, "themes": themes,
                "lyrics": lyrics, "movements": movements,
            })

    # Rhymes
    r = await session.execute(text("SELECT COUNT(*) FROM storytime_rhymes"))
    if r.scalar() == 0:
        print("  Seeding storytime rhymes...")
        rhymes = [
            ("Five Little Monkeys", "Traditional",
             "Five little monkeys jumping on the bed,\nOne fell off and bumped his head.\nMama called the doctor and the doctor said,\n\"No more monkeys jumping on the bed!\"",
             "Hold up fingers, count down, shake finger at end", ["toddler","preschool"], ["counting","animals"], "gross"),
            ("Pat-a-Cake", "Traditional",
             "Pat-a-cake, pat-a-cake, baker's man.\nBake me a cake as fast as you can.\nPat it and prick it and mark it with B,\nAnd put it in the oven for Baby and me!",
             "Clap hands together, pat motions, drawing letter", ["baby","toddler"], ["food","rhyming"], "fine"),
            ("This Little Piggy", "Traditional",
             "This little piggy went to market,\nThis little piggy stayed home,\nThis little piggy had roast beef,\nThis little piggy had none,\nAnd this little piggy cried wee wee wee all the way home!",
             "Wiggle each toe/finger in turn", ["baby","toddler"], ["animals","counting"], "fine"),
            ("Round and Round the Garden", "Traditional",
             "Round and round the garden,\nLike a teddy bear.\nOne step, two step,\nTickle you under there!",
             "Circle finger on palm, walk fingers up arm, tickle", ["baby","toddler"], ["animals","movement"], "fine"),
            ("Two Little Blackbirds", "Traditional",
             "Two little blackbirds sitting on a hill,\nOne named Jack and one named Jill.\nFly away Jack, fly away Jill,\nCome back Jack, come back Jill.",
             "Fingers behind back and return", ["baby","toddler","preschool"], ["animals","rhyming"], "fine"),
            ("Open Shut Them", "Traditional",
             "Open shut them, open shut them,\nGive a little clap, clap, clap.\nOpen shut them, open shut them,\nLay them in your lap, lap, lap.",
             "Open and close hands, clap, place in lap", ["baby","toddler"], ["movement","opposites"], "fine"),
            ("Hickory Dickory Dock", "Traditional",
             "Hickory dickory dock,\nThe mouse ran up the clock.\nThe clock struck one,\nThe mouse ran down,\nHickory dickory dock.",
             "Run fingers upward, clap once, run fingers down", ["toddler","preschool"], ["animals","counting","time"], "both"),
            ("Little Turtle", "Vachel Lindsay",
             "There was a little turtle,\nHe lived in a box.\nHe swam in a puddle,\nHe climbed on the rocks.\nHe snapped at a mosquito,\nHe snapped at a flea,\nHe snapped at a minnow,\nAnd he snapped at me!\nHe caught the mosquito,\nHe caught the flea,\nHe caught the minnow,\nBut he didn't catch me!",
             "Make fist for turtle, swimming motion, snapping motions, point to self", ["toddler","preschool"], ["animals","movement"], "both"),
        ]
        for title, author, rhyme_text, motions, ages, themes, motor in rhymes:
            await session.execute(text("""
                INSERT INTO storytime_rhymes (title, author, text, hand_motions_description,
                    age_groups, themes, motor_skill_level, times_used)
                VALUES (:title, :author, :text, :motions, :ages, :themes, :motor, 0)
            """), {
                "title": title, "author": author, "text": rhyme_text, "motions": motions,
                "ages": ages, "themes": themes, "motor": motor,
            })

    # ========== STREAMING SERVICE CONFIGS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM streaming_service_configs"))
    if r.scalar() == 0:
        print("  Seeding streaming service configs...")
        await session.execute(text("""
            INSERT INTO streaming_service_configs (service, is_active, api_base_url, library_id,
                cost_per_checkout, web_deep_link_template)
            VALUES ('palace', true, 'https://circulation.thepalaceproject.org',
                'l30-library', 1.50, 'https://thepalaceproject.org/title/{content_id}')
        """))

    # ========== DATABASE SUBSCRIPTIONS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM database_subscriptions"))
    if r.scalar() == 0:
        print("  Seeding database subscriptions...")
        db_vendor_r = await session.execute(text("SELECT id FROM database_vendors LIMIT 6"))
        db_vendor_ids = [r[0] for r in db_vendor_r.fetchall()]
        subs = [
            ("Ancestry Library Edition", "ALE", "Genealogy research: census, vital records, immigration, military records",
             "genealogy", "https://www.ancestrylibrary.com", "active", 2500.00),
            ("Consumer Reports", "CR", "Product reviews, ratings, and buying guides for consumer decisions",
             "general_reference", "https://www.consumerreports.org/library", "active", 850.00),
            ("Mango Languages", "Mango", "Self-paced language learning in 70+ languages with conversation focus",
             "language_learning", "https://connect.mangolanguages.com/l30", "active", 1200.00),
            ("NoveList Plus", "NovPlus", "Reading recommendations, read-alikes, book discussion guides",
             "general_reference", "https://www.ebscohost.com/novelist", "active", 950.00),
            ("Gale Legal Forms", "GLF", "State-specific legal forms, court documents, and legal guides",
             "legal", "https://www.gale.com/legal-forms", "active", 750.00),
            ("MetisLib", "MetisLib", "Cooperative ebook and audiobook lending platform",
             "ebooks", "https://metislib.org", "active", 15000.00),
        ]
        for i, (name, short, desc, cat, url, status, cost) in enumerate(subs):
            vid = db_vendor_ids[i % len(db_vendor_ids)] if db_vendor_ids else None
            await session.execute(text("""
                INSERT INTO database_subscriptions (name, short_name, description, category,
                    vendor_id, access_url, subscription_start, subscription_end, status,
                    annual_cost, auto_renew, requires_proxy, auth_method, is_active)
                VALUES (:name, :short, :desc, :cat, :vid, :url, :start, :end, :status,
                    :cost, true, :proxy, :auth, true)
            """), {
                "name": name, "short": short, "desc": desc, "cat": cat, "vid": vid,
                "url": url, "start": date(2026, 1, 1), "end": date(2026, 12, 31), "status": status,
                "cost": cost, "proxy": cat not in ("language_learning", "ebooks"),
                "auth": "barcode" if cat in ("genealogy", "ebooks") else "ip",
            })

    # ========== ILL REQUESTS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM ill_requests"))
    if r.scalar() == 0 and partner_lib_ids:
        print("  Seeding ILL requests...")
        ill_items = [
            ("The Name of the Wind", "Patrick Rothfuss", "9780756404741", "borrow", "pending"),
            ("Station Eleven", "Emily St. John Mandel", "9780385353304", "borrow", "in_transit"),
            ("The Overstory", "Richard Powers", "9780393356687", "borrow", "received"),
            ("Kindred", "Octavia Butler", "9780807083697", "borrow", "checked_out"),
            ("The Fifth Season", "N.K. Jemisin", "9780316229296", "borrow", "completed"),
            ("Parable of the Sower", "Octavia Butler", "9781538732182", "borrow", "searching"),
            ("Local history of Somewhere Up North", None, None, "borrow", "not_found"),
            ("The Goldfinch", "Donna Tartt", "9780316055444", "lend", "in_transit"),
            ("A Gentleman in Moscow", "Amor Towles", "9780670026197", "lend", "completed"),
            ("Circe", "Madeline Miller", "9780316556347", "lend", "returned"),
        ]
        for i, (title, author, isbn, rtype, status) in enumerate(ill_items):
            await session.execute(text("""
                INSERT INTO ill_requests (patron_id, staff_id, request_type, partner_library_id,
                    title, author, isbn, status, pickup_branch_id, needed_by, notes, renewal_count, max_renewals)
                VALUES (:pid, :sid, :rtype, :plib, :title, :author, :isbn, :status, :branch,
                    :needed, :notes, 0, 2)
            """), {
                "pid": patron_ids[i % len(patron_ids)] if rtype == "borrow" else None,
                "sid": s1,
                "rtype": rtype,
                "plib": partner_lib_ids[i % len(partner_lib_ids)],
                "title": title, "author": author, "isbn": isbn, "status": status,
                "branch": b1,
                "needed": date.today() + timedelta(days=30) if status in ("pending", "searching") else None,
                "notes": None,
            })

    # ========== TRANSIT REQUESTS + SHIPMENTS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM transit_requests"))
    if r.scalar() == 0 and item_copy_ids and len(branch_ids) >= 2:
        print("  Seeding transit requests...")
        transit_data = [
            ("hold_fulfillment", "normal", "completed"),
            ("hold_fulfillment", "high", "in_transit"),
            ("return_to_home", "normal", "completed"),
            ("rebalancing", "low", "approved"),
            ("hold_fulfillment", "urgent", "received"),
            ("return_to_home", "normal", "requested"),
            ("collection_transfer", "normal", "in_transit"),
            ("special_request", "high", "picked_up"),
        ]
        transit_req_ids = []
        for i, (reason, priority, status) in enumerate(transit_data):
            from_b = branch_ids[i % len(branch_ids)]
            to_b = branch_ids[(i + 1) % len(branch_ids)]
            result = await session.execute(text("""
                INSERT INTO transit_requests (item_copy_id, from_branch_id, to_branch_id,
                    reason, priority, status, requested_by_id)
                VALUES (:item, :from_b, :to_b, :reason, :priority, :status, :staff)
                RETURNING id
            """), {
                "item": item_copy_ids[i % len(item_copy_ids)],
                "from_b": from_b, "to_b": to_b,
                "reason": reason, "priority": priority, "status": status,
                "staff": s1,
            })
            transit_req_ids.append(result.scalar())

        print("  Seeding transit shipments...")
        for i in range(4):
            from_b = branch_ids[i % len(branch_ids)]
            to_b = branch_ids[(i + 1) % len(branch_ids)]
            await session.execute(text("""
                INSERT INTO transit_shipments (shipment_number, from_branch_id, to_branch_id,
                    item_count, container_count, created_by_id, shipped_at, shipped_by_id,
                    received_at, received_by_id, notes)
                VALUES (:num, :from_b, :to_b, :items, :containers, :created, :shipped_at,
                    :shipped_by, :received_at, :received_by, :notes)
            """), {
                "num": f"SHIP-2026-{1000+i}",
                "from_b": from_b, "to_b": to_b,
                "items": [3, 5, 2, 8][i],
                "containers": 1,
                "created": s1,
                "shipped_at": _past([14, 10, 7, 3][i]),
                "shipped_by": s1,
                "received_at": _past([12, 8, 5, 0][i]) if i < 3 else None,
                "received_by": s2 if i < 3 else None,
                "notes": [None, "Rush hold items", None, "Weekly rebalancing run"][i],
            })

    # ========== SERIAL SUBSCRIPTIONS + ISSUES ==========
    r = await session.execute(text("SELECT COUNT(*) FROM serial_subscriptions"))
    vendor_r = await session.execute(text("SELECT id FROM vendors LIMIT 3"))
    vendor_ids = [r[0] for r in vendor_r.fetchall()]
    if r.scalar() == 0 and serial_title_ids and vendor_ids:
        print("  Seeding serial subscriptions...")
        for i, stid in enumerate(serial_title_ids[:4]):
            result = await session.execute(text("""
                INSERT INTO serial_subscriptions (serial_title_id, vendor_id, branch_id,
                    subscription_number, copies_ordered, start_date, end_date, cost,
                    renewal_status, created_by_id)
                VALUES (:stid, :vid, :bid, :subnum, :copies, :start, :end, :cost, 'active', :staff)
                RETURNING id
            """), {
                "stid": stid,
                "vid": vendor_ids[i % len(vendor_ids)],
                "bid": b1,
                "subnum": f"SER-2026-{100+i}",
                "copies": 1,
                "start": date(2026, 1, 1),
                "end": date(2026, 12, 31),
                "cost": [350.00, 120.00, 85.00, 450.00][i],
                "staff": s1,
            })
            sub_id = result.scalar()

            # Add 3 issues per subscription
            print(f"  Seeding serial issues for subscription {sub_id}...")
            for j in range(3):
                status = ["received", "received", "expected"][j]
                await session.execute(text("""
                    INSERT INTO serial_issues (serial_title_id, serial_subscription_id,
                        volume, number, designation, expected_date, received_date, status,
                        branch_id, is_combined, is_supplement)
                    VALUES (:stid, :subid, :vol, :num, :desig, :expected, :received, :status, :bid, :combined, :supplement)
                """), {
                    "stid": stid, "subid": sub_id,
                    "vol": "2026", "num": str(j + 1),
                    "desig": f"Vol. 2026, No. {j+1}",
                    "expected": date(2026, 1 + j * 4, 15),
                    "received": date(2026, 1 + j * 4, 17) if status == "received" else None,
                    "status": status,
                    "bid": b1,
                    "combined": False,
                    "supplement": False,
                })

    # ========== NEWSLETTER SUBSCRIPTIONS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM newsletter_subscriptions"))
    if r.scalar() == 0:
        print("  Seeding newsletter subscriptions...")
        subscribers = [
            (p1, "elena.vasquez@example.org", "Elena", "Vasquez", "active", "weekly"),
            (p2, "marcus.chen@example.org", "Marcus", "Chen", "active", "monthly"),
            (p3, "priya.sharma@example.org", "Priya", "Sharma", "active", "weekly"),
            (None, "sarah.jones@email.com", "Sarah", "Jones", "active", "biweekly"),
            (None, "mike.wilson@email.com", "Mike", "Wilson", "active", "weekly"),
            (None, "jennifer.lee@email.com", "Jennifer", "Lee", "active", "monthly"),
            (p4, "jamal.washington@example.org", "Jamal", "Washington", "paused", "weekly"),
            (None, "amy.chen@email.com", "Amy", "Chen", "active", "weekly"),
            (None, "robert.kim@email.com", "Robert", "Kim", "active", "biweekly"),
            (None, "lisa.garcia@email.com", "Lisa", "Garcia", "active", "monthly"),
            (p5, "sophie.dubois@example.org", "Sophie", "Dubois", "active", "weekly"),
            (None, "david.patel@email.com", "David", "Patel", "unsubscribed", "weekly"),
            (None, "maria.santos@email.com", "Maria", "Santos", "active", "weekly"),
            (None, "chris.brown@email.com", "Chris", "Brown", "active", "biweekly"),
            (None, "nancy.taylor@email.com", "Nancy", "Taylor", "active", "monthly"),
        ]
        for uid, email, first, last, status, freq in subscribers:
            await session.execute(text("""
                INSERT INTO newsletter_subscriptions (user_id, email, first_name, last_name,
                    status, frequency, consent_given, unsubscribe_token, mailchimp_sync_status)
                VALUES (:uid, :email, :first, :last, :status, :freq, true, :token, 'synced')
            """), {
                "uid": uid, "email": email, "first": first, "last": last,
                "token": email.replace('@', '-at-').replace('.', '-'),
                "status": status, "freq": freq,
            })

    # ========== MARKETING CAMPAIGNS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM marketing_campaigns"))
    if r.scalar() == 0:
        print("  Seeding marketing campaigns...")
        campaigns = [
            ("Summer Reading Kickoff 2026", "summer-reading-kickoff-2026",
             "Announce the summer reading program launch with prizes and events",
             "event", "Summer Reading Program Starts June 1!", "Join us for reading adventures!",
             "sent", _past(15), _past(15), 245, 89, 34),
            ("New Database: Mango Languages", "mango-languages-launch",
             "Promote the new Mango Languages database subscription",
             "newsletter", "Learn 70+ Languages Free with Your Library Card",
             "Mango Languages is now available!",
             "sent", _past(30), _past(30), 312, 145, 67),
            ("April Author Visit Series", "april-author-visits-2026",
             "Promote upcoming author visits and book signings",
             "event", "Meet Your Favorite Authors This April",
             "Three amazing author events coming up!",
             "scheduled", _future(5), None, 0, 0, 0),
            ("Monthly New Arrivals - April", "new-arrivals-april-2026",
             "Highlight new books, DVDs, and digital resources added this month",
             "new_arrivals", "Fresh Reads: April New Arrivals",
             "Check out what is new at L30!",
             "draft", None, None, 0, 0, 0),
        ]
        for name, slug, desc, ctype, subject, preview, status, scheduled_dt, sent_dt, recip, opens, clicks in campaigns:
            await session.execute(text("""
                INSERT INTO marketing_campaigns (name, slug, description, campaign_type,
                    subject, preview_text, target_all_subscribers, status, scheduled_for, sent_at,
                    recipients_count, opens_count, clicks_count, created_by_id)
                VALUES (:name, :slug, :desc, :ctype, :subject, :preview, true, :status,
                    :scheduled, :sent, :recip, :opens, :clicks, :created)
            """), {
                "name": name, "slug": slug, "desc": desc, "ctype": ctype,
                "subject": subject, "preview": preview, "status": status,
                "scheduled": scheduled_dt, "sent": sent_dt,
                "recip": recip, "opens": opens, "clicks": clicks,
                "created": s1,
            })

    # ========== BOARD REPORTS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM board_reports"))
    if r.scalar() == 0:
        print("  Seeding board reports...")
        reports = [
            ("January 2026 Monthly Report", "2026-01-01", "2026-01-31", "published"),
            ("February 2026 Monthly Report", "2026-02-01", "2026-02-28", "published"),
            ("March 2026 Monthly Report", "2026-03-01", "2026-03-31", "draft"),
        ]
        for title, start, end, status in reports:
            await session.execute(text("""
                INSERT INTO board_reports (title, report_period_start, report_period_end,
                    status, frequency, format_generated, created_by,
                    executive_summary, key_metrics)
                VALUES (:title, :start, :end, :status, 'monthly', 'both', :staff,
                    :summary, :metrics)
            """), {
                "title": title, "start": datetime.fromisoformat(start + "T00:00:00+00:00"), "end": datetime.fromisoformat(end + "T00:00:00+00:00"), "status": status,
                "staff": s1,
                "summary": f"Library operations report for the period {start} to {end}. Circulation remained strong with continued growth in digital lending.",
                "metrics": '{"total_checkouts": 2450, "new_patrons": 34, "program_attendance": 890, "digital_borrows": 567}',
            })

    # ========== BOARD MEETING BRIEFS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM board_meeting_briefs"))
    if r.scalar() == 0 and meeting_ids:
        print("  Seeding board meeting briefs...")
        for i, mid in enumerate(meeting_ids[:4]):
            await session.execute(text("""
                INSERT INTO board_meeting_briefs (meeting_id, executive_summary,
                    background_context, agenda_highlights, recommended_prep,
                    action_items_pending, status, created_by_id)
                VALUES (:mid, :summary, :context, :highlights, :prep, :actions, 'completed', :staff)
            """), {
                "mid": mid,
                "summary": f"Board meeting {i+1}: Key topics include budget review, strategic plan progress, and upcoming community events.",
                "context": "Regular monthly board meeting covering standard governance items and special presentations.",
                "highlights": ["Budget Q1 review","Strategic plan milestone update","Summer reading program planning","Facility maintenance report"],
                "prep": ["Review attached financial statements","Read strategic plan progress report","Review proposed summer events calendar"],
                "actions": ["Approve Q1 budget amendments","Vote on summer program funding","Schedule facility walk-through"],
                "staff": s1,
            })

    # ========== REPAIR RECORDS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM repair_records"))
    if r.scalar() == 0 and catalog_ids:
        print("  Seeding repair records...")
        vendor_r2 = await session.execute(text("SELECT id FROM vendors WHERE name LIKE '%HF Group%' OR name LIKE '%Brodart%' LIMIT 2"))
        repair_vendor_ids = [r[0] for r in vendor_r2.fetchall()]
        repairs = [
            ("spine_repair", "completed", "Spine cracked and pages loosening", 15.00, 12.50),
            ("rebinding", "at_bindery", "Cover detached, needs full rebinding", 35.00, None),
            ("page_repair", "completed", "Water damage to pages 45-60", 8.00, 8.00),
            ("replacement_cover", "in_repair", "Cover badly worn, replacing with library binding", 25.00, None),
            ("in_house_repair", "completed", "Torn dust jacket repaired with archival tape", 0.00, 0.00),
            ("bindery", "assessed", "Periodical volumes need binding for shelf", 45.00, None),
        ]
        for i, (rtype, status, desc, est_cost, actual_cost) in enumerate(repairs):
            vid = repair_vendor_ids[i % len(repair_vendor_ids)] if repair_vendor_ids and rtype in ("rebinding", "bindery") else None
            await session.execute(text("""
                INSERT INTO repair_records (catalog_item_id, reported_by_id, repair_type,
                    status, damage_description, estimated_cost, actual_cost, vendor_id,
                    sent_date, expected_return_date, returned_date, completed_by_id, completed_date)
                VALUES (:cid, :reporter, :rtype, :status, :desc, :est, :actual, :vid,
                    :sent, :expected, :returned, :completed_by, :completed_date)
            """), {
                "cid": catalog_ids[i % len(catalog_ids)],
                "reporter": s1,
                "rtype": rtype, "status": status, "desc": desc,
                "est": est_cost, "actual": actual_cost,
                "vid": vid,
                "sent": date.today() - timedelta(days=30) if status in ("at_bindery", "completed") else None,
                "expected": date.today() + timedelta(days=14) if status == "at_bindery" else None,
                "returned": date.today() - timedelta(days=5) if status == "completed" and rtype != "in_house_repair" else None,
                "completed_by": s2 if status == "completed" else None,
                "completed_date": date.today() - timedelta(days=3) if status == "completed" else None,
            })

    # ========== STORYTIME SESSIONS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM storytime_sessions"))
    if r.scalar() == 0 and storytime_series_ids:
        print("  Seeding storytime sessions...")
        ssid = storytime_series_ids[0]
        sessions = [
            (10, 0, 30),   # Wed 10:00
            (10, 30, 30),  # Tue 10:30
            (10, 0, 45),   # Thu 10:00
            (11, 0, 45),   # Sat 11:00
            (18, 30, 30),  # Mon 18:30
            (10, 30, 30),  # Fri 10:30
        ]
        for i, (hour, minute, duration) in enumerate(sessions):
            start = _future(7 + i)
            start_dt = start.replace(hour=hour, minute=minute, second=0, microsecond=0)
            end_dt = start_dt + timedelta(minutes=duration)
            await session.execute(text("""
                INSERT INTO storytime_sessions (series_id, session_date, start_time, end_time,
                    status, book_ids, actual_attendance, assigned_leader_id,
                    expected_attendance)
                VALUES (:sid, :sdate, :start, :end, 'scheduled', :books, 0, :leader, :expected)
            """), {
                "sid": ssid,
                "sdate": start_dt.date(),
                "start": start_dt,
                "end": end_dt,
                "books": [],
                "leader": s1,
                "expected": [15, 20, 25, 30, 20, 15][i],
            })


    # ========== TECH CLASSES ==========
    r = await session.execute(text("SELECT COUNT(*) FROM tech_classes"))
    if r.scalar() == 0:
        print("  Seeding tech classes...")
        for i, (title, desc, days_out, hour, loc, level, instructor, cap, enrolled) in enumerate([
            ("Computer Basics: Getting Started",
             "Learn the fundamentals of using a computer, including mouse and keyboard skills, file management, and navigating the desktop. Perfect for absolute beginners.",
             20, 10, "Main Branch - Computer Lab", "beginner", "David Rose", 12, 4),
            ("Internet & Email Essentials",
             "Discover how to browse the web safely, set up and use email, and evaluate online information. Covers Chrome, Gmail, and basic search techniques.",
             22, 14, "Main Branch - Computer Lab", "beginner", "Twyla Sands", 12, 7),
            ("Smartphone Help: iPhone & Android",
             "Hands-on help with your smartphone. Learn to make calls, send texts, take photos, download apps, and adjust settings. Bring your own device.",
             27, 10, "Elmdale Branch - Meeting Room", "beginner", "Alexis Rose", 10, 3),
            ("Staying Safe Online",
             "Protect yourself from scams, phishing, and identity theft. Learn to create strong passwords, spot fake websites, and keep your personal information secure.",
             29, 14, "Main Branch - Computer Lab", "beginner", "Stevie Budd", 12, 9),
            ("Google Docs & Productivity Apps",
             "Learn to create documents, spreadsheets, and presentations using free Google tools. Covers Google Docs, Sheets, and Slides with hands-on practice.",
             34, 18, "Main Branch - Computer Lab", "intermediate", "David Rose", 12, 5),
            ("Digital Literacy Workshop: Beyond the Basics",
             "Take your skills further with cloud storage, video calling, online banking safety, and managing digital photos. For those comfortable with basic computer use.",
             36, 10, "Elmdale Branch - Meeting Room", "intermediate", "Twyla Sands", 10, 6),
        ]):
            class_dt = _future(days_out).replace(hour=hour, minute=0, second=0, microsecond=0)
            await session.execute(text("""
                INSERT INTO tech_classes (title, description, date, location, level, instructor, capacity, enrolled, is_active)
                VALUES (:title, :desc, :dt, :loc, :level, :instructor, :cap, :enrolled, true)
            """), {"title": title, "desc": desc, "dt": class_dt, "loc": loc,
                   "level": level, "instructor": instructor, "cap": cap, "enrolled": enrolled})

    # ========== TECH HELP OPTIONS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM tech_help_options"))
    if r.scalar() == 0:
        print("  Seeding tech help options...")
        await session.execute(text("""
            INSERT INTO tech_help_options (title, description, schedule, location, phone, icon, is_active, sort_order)
            VALUES
            ('Drop-In Tech Help',
             'Walk in with your device or question and get one-on-one help from a tech volunteer. No appointment needed. First come, first served.',
             'Tuesdays & Thursdays, 10:00 AM - 12:00 PM; Saturdays, 1:00 PM - 3:00 PM',
             'Main Branch - Computer Lab', NULL, 'help-circle', true, 1),
            ('Tech Appointments',
             'Book a 30-minute session with a trained tech helper for focused, personalized assistance with your device, software, or online accounts.',
             'Monday - Friday, 9:00 AM - 5:00 PM by appointment',
             'Main Branch or Elmdale Branch', '(555) 310-5544', 'calendar', true, 2),
            ('Tech Help Hotline',
             'Call our tech help line for quick questions about your computer, phone, or tablet. Our staff can walk you through common issues over the phone.',
             'Monday - Friday, 10:00 AM - 4:00 PM',
             NULL, '(555) 310-5500 x3', 'phone', true, 3)
        """))

    # ========== TECH QUICK LINKS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM tech_quick_links"))
    if r.scalar() == 0:
        print("  Seeding tech quick links...")
        await session.execute(text("""
            INSERT INTO tech_quick_links (section_title, name, url, sort_order, is_active)
            VALUES
            ('Internet & WiFi', 'Connect to Library WiFi', 'https://www.gcfglobal.org/en/internetbasics/connecting-to-the-internet/1/', 1, true),
            ('Internet & WiFi', 'Internet Basics Tutorial', 'https://www.gcfglobal.org/en/internetbasics/', 2, true),
            ('Internet & WiFi', 'WiFi Troubleshooting Tips', 'https://edu.gcfglobal.org/en/basic-computer-skills/how-to-set-up-a-wifi-network/1/', 3, true),
            ('Devices', 'Windows 11 Getting Started', 'https://www.gcfglobal.org/en/windows/', 4, true),
            ('Devices', 'Mac Basics Guide', 'https://www.gcfglobal.org/en/macosbasics/', 5, true),
            ('Devices', 'iPhone & iPad Help', 'https://support.apple.com/guide/iphone/welcome/ios', 6, true),
            ('Devices', 'Android Phone Help', 'https://support.google.com/android/', 7, true),
            ('Learning', 'GCFGlobal Free Tutorials', 'https://edu.gcfglobal.org/en/', 8, true),
            ('Learning', 'DigitalLearn.org Courses', 'https://www.digitallearn.org/', 9, true),
            ('Learning', 'Northstar Digital Literacy', 'https://www.digitalliteracyassessment.org/', 10, true),
            ('Learning', 'LinkedIn Learning (Free with Card)', 'https://www.linkedin.com/learning/', 11, true),
            ('Printing & Scanning', 'Print from Your Device', 'https://www.printeron.net/help/', 12, true),
            ('Printing & Scanning', 'Scanning Documents Guide', 'https://edu.gcfglobal.org/en/basic-computer-skills/how-to-use-a-scanner/1/', 13, true),
            ('Printing & Scanning', 'Printing FAQ', 'https://www.gcfglobal.org/en/basic-computer-skills/common-printing-problems/1/', 14, true)
        """))

    # ========== TECH HELP RESOURCES ==========
    r = await session.execute(text("SELECT COUNT(*) FROM tech_help_resources"))
    if r.scalar() == 0:
        print("  Seeding tech help resources...")
        await session.execute(text("""
            INSERT INTO tech_help_resources (title, description, category, format, duration, href, difficulty_level, is_active, sort_order)
            VALUES
            ('Computer Basics: Getting to Know Your Computer',
             'Learn the parts of a computer, how to turn it on, and navigate the desktop. Covers mouse, keyboard, and basic file management.',
             'basics', 'Interactive Guide', '30 min', 'https://edu.gcfglobal.org/en/computerbasics/', 'Beginner', true, 1),
            ('Using a Keyboard & Mouse',
             'Practice essential keyboard shortcuts and mouse skills with interactive exercises designed for new computer users.',
             'basics', 'Interactive Guide', '20 min', 'https://edu.gcfglobal.org/en/computerbasics/basic-parts-of-a-computer/1/', 'Beginner', true, 2),
            ('Email Basics with Gmail',
             'Step-by-step guide to creating a Gmail account, sending and receiving email, managing attachments, and organizing your inbox.',
             'internet', 'Video Tutorial', '25 min', 'https://edu.gcfglobal.org/en/gmail/', 'Beginner', true, 3),
            ('Web Browsing & Online Search',
             'Learn to navigate websites, use search engines effectively, evaluate online information, and manage bookmarks and tabs.',
             'internet', 'Interactive Guide', '20 min', 'https://edu.gcfglobal.org/en/internetbasics/', 'Beginner', true, 4),
            ('iPhone & iPad Basics',
             'Get comfortable with your Apple device. Covers touchscreen navigation, settings, app downloads, making calls, and taking photos.',
             'mobile', 'Video Tutorial', '30 min', 'https://edu.gcfglobal.org/en/iphone/', 'Beginner', true, 5),
            ('Android Phone Essentials',
             'Learn to set up and use your Android phone, including contacts, camera, text messaging, Google Play Store, and accessibility settings.',
             'mobile', 'Video Tutorial', '30 min', 'https://edu.gcfglobal.org/en/androidbasics/', 'Beginner', true, 6),
            ('Protecting Yourself Online',
             'Understand common online threats like phishing and malware. Learn to create strong passwords, enable two-factor authentication, and recognize scams.',
             'safety', 'PDF Handout', '15 min', 'https://www.digitallearn.org/courses/online-safety', 'Beginner', true, 7),
            ('Privacy & Identity Theft Prevention',
             'Practical steps to protect your personal information online, secure your accounts, and know what to do if your identity is compromised.',
             'safety', 'Interactive Guide', '25 min', 'https://edu.gcfglobal.org/en/internetsafety/', 'Intermediate', true, 8),
            ('Getting Started with Google Docs',
             'Create, edit, format, and share documents online for free. Includes real-time collaboration and basic formatting techniques.',
             'apps', 'Video Tutorial', '20 min', 'https://edu.gcfglobal.org/en/googledocuments/', 'Beginner', true, 9),
            ('Introduction to Google Sheets',
             'Learn spreadsheet basics including entering data, using simple formulas, sorting, filtering, and creating charts.',
             'apps', 'Interactive Guide', '25 min', 'https://edu.gcfglobal.org/en/googlespreadsheets/', 'Intermediate', true, 10)
        """))

    await session.flush()
    print("  Missing data seed complete.")
    return True
