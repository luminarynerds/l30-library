# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import random
import uuid
from datetime import datetime, timedelta, timezone, date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

utc = timezone.utc


def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago)


def _past_date(days_ago: int) -> date:
    return (datetime.now(utc) - timedelta(days=days_ago)).date()


async def seed_batch_patron_facing(session: AsyncSession) -> bool:

    # Grab reusable IDs
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] in ("patron", "child")]
    all_ids = [u[0] for u in users]

    # Reading programs
    prog_r = await session.execute(text("SELECT id FROM reading_programs"))
    program_ids = [r[0] for r in prog_r.fetchall()]

    # Achievements
    ach_r = await session.execute(text("SELECT id FROM achievements"))
    achievement_ids = [r[0] for r in ach_r.fetchall()]

    # Storytime sessions (completed ones)
    sess_r = await session.execute(text("SELECT id FROM storytime_sessions WHERE status='completed'"))
    completed_session_ids = [r[0] for r in sess_r.fetchall()]

    # Courses
    course_r = await session.execute(text("SELECT id FROM courses"))
    course_ids = [r[0] for r in course_r.fetchall()]

    now = datetime.now(utc)

    # ════════════════════════════════════════════════════════════════
    # 1. READING PROGRAMS (ensure we have at least 4)
    # ════════════════════════════════════════════════════════════════
    if len(program_ids) < 4:
        print("  Ensuring at least 4 reading programs...")
        extra_programs = [
            ("Summer Reading Challenge 2025", "Read your way through summer! Track books, earn prizes, and join fun activities all summer long.",
             "summer", "All Ages", None, None, date(2025, 6, 1), date(2025, 8, 31), "books", 20, False, False),
            ("Winter Warmup Reading Club", "Curl up with a good book this winter. Log your reading and earn cozy prizes.",
             "winter", "Adults", 18, 99, date(2025, 12, 1), date(2026, 2, 28), "books", 10, True, False),
            ("1000 Books Before Kindergarten", "Read 1000 books with your little one before they start school. Every book counts!",
             "year_round", "Children", 0, 5, date(2025, 1, 1), date(2026, 12, 31), "books", 1000, True, False),
        ]
        for name, desc, ptype, age_group, age_min, age_max, start, end, goal_type, goal_val, is_active, is_school in extra_programs:
            # Skip if name already exists
            check = await session.execute(text("SELECT id FROM reading_programs WHERE name = :name"), {"name": name})
            if check.fetchone():
                continue
            r2 = await session.execute(text("""
                INSERT INTO reading_programs (name, description, program_type, age_group, target_age_min, target_age_max,
                    start_date, end_date, reading_goal_type, reading_goal_value, is_active, is_school_program,
                    grade_levels, reading_levels, created_by_id, created_at, updated_at)
                VALUES (:name, :desc, :ptype, :ag, :amin, :amax, :start, :end, :gt, :gv, :active, :school,
                    cast(:grades as json), cast(:levels as json), :creator, :now, :now)
                RETURNING id
            """), {
                "name": name, "desc": desc, "ptype": ptype, "ag": age_group,
                "amin": age_min, "amax": age_max, "start": start, "end": end,
                "gt": goal_type, "gv": goal_val, "active": is_active, "school": is_school,
                "grades": "[]", "levels": "[]",
                "creator": random.choice(staff_ids), "now": now,
            })
            new_id = r2.scalar()
            program_ids.append(new_id)
        print(f"    Reading programs now: {len(program_ids)}")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 2. READING REGISTRATIONS — 35 patrons registered
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM reading_registrations"))
    if r.scalar() == 0 and program_ids:
        print("  Seeding reading_registrations...")
        reg_count = 0
        used = set()
        reg_ids_map = []  # (reg_id, user_id, program_id)
        sample_patrons = random.sample(patron_ids, min(len(patron_ids), 35))
        for uid in sample_patrons:
            pid = random.choice(program_ids)
            if (uid, pid) in used:
                continue
            used.add((uid, pid))
            goal = random.choice([5, 10, 15, 20, 25, 30])
            days_ago = random.randint(7, 180)
            r2 = await session.execute(text("""
                INSERT INTO reading_registrations (user_id, program_id, registered_at, goal_target)
                VALUES (:uid, :pid, :reg_at, :goal)
                RETURNING id
            """), {
                "uid": uid, "pid": pid,
                "reg_at": _past(days_ago),
                "goal": goal,
            })
            reg_id = r2.scalar()
            reg_ids_map.append((reg_id, uid, pid))
            reg_count += 1
        print(f"    Created {reg_count} reading registrations")
        await session.flush()
    else:
        # Load existing registrations for log entries
        rr = await session.execute(text("SELECT id, user_id, program_id FROM reading_registrations"))
        reg_ids_map = [(r[0], r[1], r[2]) for r in rr.fetchall()]

    # ════════════════════════════════════════════════════════════════
    # 3. READING LOG ENTRIES — 120 log entries
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM reading_log_entries"))
    if r.scalar() == 0 and reg_ids_map:
        print("  Seeding reading_log_entries...")
        book_data = [
            ("The Great Gatsby", "F. Scott Fitzgerald"),
            ("To Kill a Mockingbird", "Harper Lee"),
            ("Pride and Prejudice", "Jane Austen"),
            ("The Alchemist", "Paulo Coelho"),
            ("Where the Crawdads Sing", "Delia Owens"),
            ("Educated", "Tara Westover"),
            ("Becoming", "Michelle Obama"),
            ("The Night Circus", "Erin Morgenstern"),
            ("Circe", "Madeline Miller"),
            ("The House in the Cerulean Sea", "TJ Klune"),
            ("Project Hail Mary", "Andy Weir"),
            ("Piranesi", "Susanna Clarke"),
            ("The Midnight Library", "Matt Haig"),
            ("Anxious People", "Fredrik Backman"),
            ("The Vanishing Half", "Brit Bennett"),
            ("Mexican Gothic", "Silvia Moreno-Garcia"),
            ("Klara and the Sun", "Kazuo Ishiguro"),
            ("The Invisible Life of Addie LaRue", "V.E. Schwab"),
            ("Lessons in Chemistry", "Bonnie Garmus"),
            ("Tomorrow, and Tomorrow, and Tomorrow", "Gabrielle Zevin"),
            ("Demon Copperhead", "Barbara Kingsolver"),
            ("The Covenant of Water", "Abraham Verghese"),
            ("Holly", "Stephen King"),
            ("Fourth Wing", "Rebecca Yarros"),
            ("Remarkably Bright Creatures", "Shelby Van Pelt"),
            ("A Court of Thorns and Roses", "Sarah J. Maas"),
            ("The Seven Husbands of Evelyn Hugo", "Taylor Jenkins Reid"),
            ("It Ends with Us", "Colleen Hoover"),
            ("Atomic Habits", "James Clear"),
            ("The Body Keeps the Score", "Bessel van der Kolk"),
        ]
        notes_pool = [
            "Really enjoyed this one. Couldn't put it down.",
            "My book club pick — generated great discussion.",
            "Not my usual genre but pleasantly surprised.",
            "Beautiful prose, slow start but worth it.",
            "Read this to my kids at bedtime. They loved it.",
            "Listened to the audiobook while commuting.",
            "Recommended by the librarian at the front desk.",
            "Re-read from years ago. Even better the second time.",
            "A bit overhyped but still a solid read.",
            "Perfect beach read for vacation.",
            "Had me in tears by the end.",
            "Fascinating subject — learned a lot.",
            None, None, None, None,  # Some entries have no notes
        ]
        log_count = 0
        for _ in range(120):
            reg_id, uid, pid = random.choice(reg_ids_map)
            title, author = random.choice(book_data)
            days_ago = random.randint(1, 180)
            books_read = random.choice([0, 0, 1, 1, 1, 1, 1, 2])
            minutes = random.randint(15, 180)
            pages = random.randint(10, 350)
            rating = random.choice([None, None, 3, 4, 4, 5, 5, 5])
            note = random.choice(notes_pool)
            await session.execute(text("""
                INSERT INTO reading_log_entries (registration_id, logged_at, books_read, minutes_read, pages_read,
                    title, author, notes, rating, book_cover_url)
                VALUES (:reg_id, :logged_at, :books, :minutes, :pages, :title, :author, :notes, :rating, :cover)
            """), {
                "reg_id": reg_id, "logged_at": _past(days_ago),
                "books": books_read, "minutes": minutes, "pages": pages,
                "title": title if books_read > 0 else None,
                "author": author if books_read > 0 else None,
                "notes": note, "rating": rating,
                "cover": None,
            })
            log_count += 1
        print(f"    Created {log_count} reading log entries")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 4. READING PRIZES — 10 prizes
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM reading_prizes"))
    if r.scalar() == 0 and program_ids:
        print("  Seeding reading_prizes...")
        prizes = [
            ("Book Bag", "Canvas tote bag with library logo", "physical", "$8", "books", 5, 20, 3, True, 1),
            ("$5 Coffee Gift Card", "Gift card to Main Street Coffee", "gift_card", "$5", "books", 3, 30, 8, True, 2),
            ("Free Printing Credits", "50 pages of free printing at library computers", "coupon", "$5", "books", 2, 50, 12, True, 3),
            ("Reading Journal", "Hardcover reading journal with book tracker", "physical", "$12", "books", 10, 15, 2, True, 4),
            ("$10 Bookstore Gift Card", "Gift card to Chapter One Books downtown", "gift_card", "$10", "books", 8, 10, 1, True, 5),
            ("Library Sticker Pack", "Set of 6 book-themed vinyl stickers", "physical", "$3", "minutes", 300, 40, 15, True, 6),
            ("Ice Cream Voucher", "Free scoop at Scoops Ice Cream Parlor", "coupon", "$4", "books", 1, 25, 10, True, 7),
            ("Drawstring Backpack", "Waterproof drawstring bag with Summer Reading design", "physical", "$6", "books", 15, 12, 0, True, 8),
            ("Grand Prize: Kindle", "Kindle Paperwhite — end-of-program raffle entry", "raffle", "$140", "books", 20, 1, 0, True, 9),
            ("Bookmark Set", "Handmade bookmarks by local artist", "physical", "$5", "books", 1, 60, 25, True, 10),
        ]
        for name, desc, ptype, value, threshold_type, threshold_val, qty, redeemed, active, sort in prizes:
            pid = random.choice(program_ids)
            await session.execute(text("""
                INSERT INTO reading_prizes (program_id, name, description, prize_type, prize_value, image_url,
                    threshold_type, threshold_value, quantity_available, quantity_redeemed, is_active,
                    available_from, available_until, sort_order, notes, created_by_id, created_at, updated_at)
                VALUES (:pid, :name, :desc, :ptype, :value, NULL,
                    :ttype, :tval, :qty, :redeemed, :active,
                    :from_date, :until_date, :sort, NULL, :creator, :now, :now)
            """), {
                "pid": pid, "name": name, "desc": desc, "ptype": ptype, "value": value,
                "ttype": threshold_type, "tval": threshold_val, "qty": qty, "redeemed": redeemed,
                "active": active, "from_date": date(2025, 6, 1), "until_date": date(2026, 8, 31),
                "sort": sort, "creator": random.choice(staff_ids), "now": now,
            })
        print(f"    Created {len(prizes)} reading prizes")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 5. READING ACHIEVEMENTS — ~30 patrons linked
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM reading_achievements"))
    if r.scalar() == 0 and program_ids and achievement_ids:
        print("  Seeding reading_achievements...")
        badge_defs = [
            ("first-book", "First Book", "Logged your very first book in the reading program!"),
            ("five-books", "Five Book Milestone", "Read 5 books — you're on a roll!"),
            ("ten-books", "Ten Book Champion", "An impressive 10 books completed!"),
            ("twenty-books", "Super Reader", "20 books! You're a reading machine!"),
            ("bookworm-badge", "Bookworm", "Logged reading every day for a week straight."),
            ("genre-hopper", "Genre Hopper", "Read books from 3 different genres."),
            ("night-reader", "Night Reader", "Logged reading after 10 PM."),
            ("early-finisher", "Early Finisher", "Reached your reading goal before the halfway point."),
            ("review-writer", "Review Star", "Wrote 3 book reviews during the program."),
            ("community-reader", "Community Reader", "Attended a reading program event."),
        ]
        ra_count = 0
        used = set()
        sample_patrons = random.sample(patron_ids, min(len(patron_ids), 30))
        for uid in sample_patrons:
            pid = random.choice(program_ids)
            num_badges = random.randint(1, 4)
            chosen = random.sample(badge_defs, min(len(badge_defs), num_badges))
            for badge_id, badge_name, badge_desc in chosen:
                key = (uid, pid, badge_id)
                if key in used:
                    continue
                used.add(key)
                await session.execute(text("""
                    INSERT INTO reading_achievements (user_id, program_id, badge_id, badge_name, badge_description, unlocked_at)
                    VALUES (:uid, :pid, :bid, :bname, :bdesc, :unlocked)
                """), {
                    "uid": uid, "pid": pid, "bid": badge_id,
                    "bname": badge_name, "bdesc": badge_desc,
                    "unlocked": _past(random.randint(1, 150)),
                })
                ra_count += 1
        print(f"    Created {ra_count} reading achievements")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 6. EBOOK FEATURED — 10 featured displays
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM ebook_featured"))
    if r.scalar() == 0:
        print("  Seeding ebook_featured...")
        featured = [
            (1, "Staff Picks: Spring 2026"),
            (2, "New Arrivals This Month"),
            (3, "Award Winners Collection"),
            (4, "Local Authors Spotlight"),
            (5, "Book Club Favorites"),
            (6, "Cozy Reads for Rainy Days"),
            (7, "True Crime Deep Dives"),
            (8, "Diverse Voices"),
            (9, "Science and Nature"),
            (10, "YA Must-Reads"),
        ]
        for order, theme in featured:
            # Use a fake metislib_ebook_id since we don't have real ones
            await session.execute(text("""
                INSERT INTO ebook_featured (metislib_ebook_id, display_order, theme_title,
                    featured_from, featured_until, added_by_id, created_at, updated_at)
                VALUES (:ebook_id, :order, :theme, :from_ts, :until_ts, :added_by, :now, :now)
            """), {
                "ebook_id": order,  # placeholder IDs
                "order": order, "theme": theme,
                "from_ts": _past(random.randint(0, 30)),
                "until_ts": _past(-random.randint(14, 60)),  # future dates
                "added_by": random.choice(staff_ids), "now": now,
            })
        print(f"    Created {len(featured)} featured ebook displays")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 7. STORYTIME ATTENDANCE — 60 records
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM storytime_attendance"))
    if r.scalar() == 0 and completed_session_ids:
        print("  Seeding storytime_attendance...")
        child_names = [
            "Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia", "Mason",
            "Isabella", "Lucas", "Mia", "Oliver", "Charlotte", "Elijah", "Amelia",
            "Aiden", "Harper", "James", "Evelyn", "Benjamin", "Luna", "Jack",
            "Lily", "Henry", "Aria", "Leo", "Chloe", "Owen", "Penelope", "Wyatt",
        ]
        caregiver_names = [
            "Jennifer Martinez", "Sarah Johnson", "Michael Chen", "Amanda Williams",
            "David Thompson", "Lisa Garcia", "Robert Brown", "Emily Davis",
            "James Wilson", "Maria Rodriguez", "John Anderson", "Ashley Taylor",
            "Christopher Lee", "Stephanie Moore", "Daniel Jackson", "Nicole White",
        ]
        feedback_pool = [
            "My daughter loved the story today!",
            "Great selection of books. We'll be back next week.",
            "The craft activity was a hit — messy but fun!",
            "First time here and we had a wonderful experience.",
            "My son asks to come every week now.",
            "The songs were so catchy, we sang them all the way home.",
            "Wish it were longer! The kids were so engaged.",
            "Thank you for the bilingual storytime. So important for our family.",
            None, None, None, None, None,  # Many entries have no feedback
        ]
        age_groups = ["babies", "toddlers", "twos", "threes", "fours", "fives_and_up", "preschool", "school_age", "families"]
        att_count = 0
        for _ in range(60):
            sid = random.choice(completed_session_ids)
            is_child = random.random() < 0.6
            uid = random.choice(patron_ids) if random.random() < 0.3 else None
            child = random.choice(child_names) if is_child else None
            caregiver = random.choice(caregiver_names) if not is_child or random.random() < 0.5 else None
            await session.execute(text("""
                INSERT INTO storytime_attendance (session_id, user_id, child_name, caregiver_name,
                    age_group, attendee_type, is_first_time, caregiver_email, caregiver_phone,
                    feedback, rating, checked_in_at)
                VALUES (:sid, :uid, :child, :caregiver, :age_group, :type, :first_time,
                    :email, :phone, :feedback, :rating, :checked_in)
            """), {
                "sid": sid, "uid": uid, "child": child, "caregiver": caregiver,
                "age_group": random.choice(age_groups),
                "type": "child" if is_child else "caregiver",
                "first_time": random.random() < 0.2,
                "email": f"{caregiver.lower().replace(' ', '.')}@email.com" if caregiver else None,
                "phone": None,
                "feedback": random.choice(feedback_pool),
                "rating": random.choice([None, None, 4, 4, 5, 5, 5, 3]),
                "checked_in": _past(random.randint(1, 150)),
            })
            att_count += 1
        print(f"    Created {att_count} storytime attendance records")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 8. STORYTIME CRAFTS — 12 craft projects
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM storytime_crafts"))
    if r.scalar() == 0:
        print("  Seeding storytime_crafts...")
        crafts = [
            ("Paper Plate Animals", "Create fun animal faces using paper plates, googly eyes, and paint.",
             ["toddlers","threes","fours"], ["animals","farm","zoo"], "simple",
             "1. Give each child a paper plate.\n2. Let them paint the plate their chosen animal color.\n3. While drying, cut out ears/features from construction paper.\n4. Glue on googly eyes, ears, and features.\n5. Add pipe cleaner whiskers if making a cat.",
             20, ["paper plates","googly eyes","washable paint","construction paper","glue sticks","paintbrushes"],
             ["pipe cleaners","markers","stickers"], 2.50, 8, "Easy cleanup. Lay down newspaper first."),
            ("Caterpillar Egg Carton", "Turn egg cartons into adorable caterpillars with paint and pipe cleaners.",
             ["threes","fours","fives_and_up"], ["bugs","spring","garden"], "moderate",
             "1. Cut egg carton into rows of 4-6 cups.\n2. Paint each cup a different color.\n3. Poke pipe cleaners through top of first cup for antennae.\n4. Glue on googly eyes.\n5. Draw a smiley face with marker.",
             25, ["egg cartons","washable paint","pipe cleaners","googly eyes","glue","markers"],
             ["pom poms","stickers"], 1.50, 12, "Pre-cut cartons for younger children."),
            ("Rainbow Handprint Art", "A collaborative mural where each child adds their handprint to create a rainbow.",
             ["babies","toddlers","twos","threes"], ["colors","weather","spring"], "simple",
             "1. Lay out large butcher paper on table.\n2. Pour washable paint in rainbow colors.\n3. Help each child make a handprint on the paper.\n4. Label each print with child's name and date.\n5. Let dry and display in storytime area.",
             15, ["butcher paper","washable paint","paper plates for paint","wet wipes","smocks"],
             ["glitter glue","stickers"], 3.00, 15, "Have wet wipes ready. Smocks are a must."),
            ("Tissue Paper Flowers", "Create colorful flowers by layering and scrunching tissue paper.",
             ["fours","fives_and_up","school_age"], ["flowers","spring","mothers_day"], "moderate",
             "1. Stack 4-5 sheets of tissue paper.\n2. Accordion-fold the stack.\n3. Secure the middle with a pipe cleaner.\n4. Carefully separate and fluff each layer.\n5. Bend pipe cleaner into a stem.",
             20, ["tissue paper","pipe cleaners","scissors"],
             ["ribbon","vases","green tape"], 2.00, 10, "Pre-cut tissue paper for younger kids."),
            ("Story Stones", "Paint smooth stones with story elements for imaginative play.",
             ["fours","fives_and_up","school_age"], ["storytelling","imagination","literacy"], "moderate",
             "1. Wash and dry smooth river stones.\n2. Paint a white base coat and let dry.\n3. Paint simple images: sun, tree, house, person, animal, etc.\n4. Seal with clear coat (staff only).\n5. Use stones to create and tell stories.",
             30, ["smooth stones","acrylic paint","paintbrushes","clear sealant"],
             ["paint pens","drawstring bags"], 4.00, 6, "Staff applies sealant after session. Need ventilation."),
            ("Popsicle Stick Puppets", "Build simple puppets using popsicle sticks and craft supplies.",
             ["threes","fours","fives_and_up"], ["puppets","theater","storytelling"], "simple",
             "1. Choose a character from today's story.\n2. Glue construction paper shapes onto popsicle stick.\n3. Add googly eyes, yarn hair, fabric scraps.\n4. Use puppets to retell the story.",
             15, ["popsicle sticks","construction paper","googly eyes","yarn","glue sticks","scissors"],
             ["fabric scraps","buttons","markers"], 1.75, 11, "Great for retelling the day's story."),
            ("Nature Collage", "Collect leaves, twigs, and flowers to create nature art.",
             ["toddlers","threes","fours","fives_and_up"], ["nature","fall","seasons"], "simple",
             "1. Take a short nature walk to collect items.\n2. Arrange items on cardstock.\n3. Glue down the arrangement.\n4. Add labels or drawings around the edges.\n5. Display in library nature corner.",
             25, ["cardstock","glue","nature items","crayons"],
             ["pressed flowers","magnifying glasses"], 0.50, 9, "Great for outdoor storytime. Check for allergies."),
            ("Paper Bag Monsters", "Transform paper bags into silly monsters with construction paper and imagination.",
             ["threes","fours","fives_and_up"], ["monsters","halloween","imagination"], "simple",
             "1. Give each child a paper lunch bag.\n2. Cut construction paper shapes for eyes, teeth, horns.\n3. Glue shapes onto the bag.\n4. Add yarn, feathers, or stickers.\n5. Use as a puppet for storytelling.",
             20, ["paper lunch bags","construction paper","glue sticks","scissors","crayons"],
             ["feathers","yarn","stickers","googly eyes"], 2.00, 7, "Kids love the sillier the better."),
            ("Snowflake Suncatchers", "Create beautiful translucent snowflakes for winter windows.",
             ["fours","fives_and_up","school_age"], ["winter","snow","holidays"], "complex",
             "1. Cut contact paper into 6-inch squares.\n2. Peel backing and place sticky-side up.\n3. Arrange tissue paper pieces in snowflake pattern.\n4. Place second contact paper on top.\n5. Cut into snowflake shape.\n6. Punch hole and add string for hanging.",
             30, ["clear contact paper","tissue paper","scissors","hole punch","string"],
             ["glitter","sequins"], 3.50, 4, "Pre-cut contact paper. Tricky for younger kids."),
            ("Seed Starter Cups", "Plant seeds in decorated cups to take home and grow.",
             ["threes","fours","fives_and_up","school_age"], ["garden","spring","science"], "moderate",
             "1. Decorate a paper cup with stickers and markers.\n2. Fill 3/4 with potting soil.\n3. Plant 2-3 seeds according to package directions.\n4. Water lightly.\n5. Take home with care instructions sheet.",
             20, ["paper cups","potting soil","seeds","stickers","markers","spray bottles","plastic wrap"],
             ["plant labels","watering cans"], 3.00, 5, "Use fast-growing seeds like beans or sunflowers."),
            ("Friendship Bracelets", "Simple bead-and-string bracelets for older storytime kids.",
             ["fives_and_up","school_age"], ["friendship","community","social"], "moderate",
             "1. Cut elastic cord to wrist size plus 3 inches.\n2. Tape one end to the table.\n3. Thread beads in chosen pattern.\n4. Tie a secure double knot.\n5. Trim excess cord.",
             25, ["elastic cord","letter beads","colored beads","scissors","tape"],
             ["charms","clasps"], 4.50, 3, "Letter beads are popular -- spell names or words."),
            ("Constellation Viewers", "Make a simple constellation viewer from a toilet paper roll.",
             ["fives_and_up","school_age"], ["space","science","night_sky"], "complex",
             "1. Cover one end of toilet paper roll with black paper.\n2. Secure with rubber band.\n3. Using constellation guide, poke pin holes in pattern.\n4. Hold up to light and look through the open end.\n5. Try different constellations!",
             25, ["toilet paper rolls","black construction paper","rubber bands","push pins","constellation guides"],
             ["flashlights","glow-in-dark stars"], 1.00, 2, "Staff should handle the push pins for safety."),
        ]
        for (title, desc, age_groups_list, themes_list, complexity, instructions,
             est_time, required_list, optional_list, cost, times_used, notes) in crafts:
            last_used = _past_date(random.randint(7, 120)) if times_used > 0 else None
            # Build PostgreSQL array literals with proper quoting
            def _pg_arr(lst):
                inner = ",".join(f'"{v}"' for v in lst)
                return "'{" + inner + "}'::varchar[]"
            sql = f"""
                INSERT INTO storytime_crafts (title, description, age_groups, themes, complexity,
                    step_by_step_instructions, estimated_time_minutes, required_supplies, optional_supplies,
                    supplies_cost_estimate, image_url, tutorial_video_url, times_used, last_used_date,
                    librarian_notes, success_tips, cleanup_notes)
                VALUES (:title, :desc, {_pg_arr(age_groups_list)}, {_pg_arr(themes_list)}, :complexity,
                    :instructions, :est_time, {_pg_arr(required_list)}, {_pg_arr(optional_list)},
                    :cost, NULL, NULL, :times_used, :last_used,
                    :notes, NULL, NULL)
            """
            await session.execute(text(sql), {
                "title": title, "desc": desc, "complexity": complexity,
                "instructions": instructions, "est_time": est_time,
                "cost": cost, "times_used": times_used, "last_used": last_used,
                "notes": notes,
            })
        print(f"    Created {len(crafts)} storytime crafts")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 9. CERTIFICATE TEMPLATES — 4 templates
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM certificate_templates"))
    if r.scalar() == 0:
        print("  Seeding certificate_templates...")
        templates = [
            ("Summer Reading Completion", "Awarded for completing the Summer Reading Challenge",
             "Certificate of Achievement", "Congratulations on completing the Summer Reading Challenge!",
             "has demonstrated a love of reading and commitment to lifelong learning",
             "#FDE68A", "#F59E0B", "ornate", True, True, True, True),
            ("Digital Literacy Certificate", "Awarded upon completion of a Digital Literacy course",
             "Certificate of Completion", "Congratulations on completing your Digital Literacy training!",
             "has successfully demonstrated proficiency in essential digital skills",
             "#DBEAFE", "#3B82F6", "modern", True, False, False, True),
            ("Volunteer Service Award", "Recognizes outstanding volunteer service hours",
             "Certificate of Recognition", "Thank you for your dedicated service to our library!",
             "has generously contributed their time and talents to strengthen our community",
             "#D1FAE5", "#10B981", "classic", True, True, False, True),
            ("Makerspace Safety Certification", "Certifies completion of makerspace safety training",
             "Safety Certification", "You are now certified to use our Makerspace equipment!",
             "has completed all required safety training for library Makerspace equipment",
             "#E0E7FF", "#6366F1", "simple", True, False, False, True),
        ]
        template_ids = []
        for name, desc, title_text, congrats, recognition, bg, accent, border, logo, seal, is_default, is_active in templates:
            pid = random.choice(program_ids) if "Reading" in name else None
            r2 = await session.execute(text("""
                INSERT INTO certificate_templates (name, description, program_id, title_text, congratulations_text,
                    recognition_text, background_color, accent_color, border_style, include_logo, include_seal,
                    template_file_url, is_active, is_default, created_by_id, created_at, updated_at)
                VALUES (:name, :desc, :pid, :title, :congrats, :recognition, :bg, :accent, :border,
                    :logo, :seal, NULL, :active, :default, :creator, :now, :now)
                RETURNING id
            """), {
                "name": name, "desc": desc, "pid": pid, "title": title_text,
                "congrats": congrats, "recognition": recognition,
                "bg": bg, "accent": accent, "border": border,
                "logo": logo, "seal": seal, "active": is_active, "default": is_default,
                "creator": random.choice(staff_ids), "now": now,
            })
            template_ids.append(r2.scalar())
        print(f"    Created {len(templates)} certificate templates")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 10. CERTIFICATES — ~20 earned certificates
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM certificates"))
    if r.scalar() == 0 and course_ids:
        print("  Seeding certificates...")
        cert_count = 0
        used = set()
        sample_patrons = random.sample(patron_ids, min(len(patron_ids), 20))
        for uid in sample_patrons:
            cid = random.choice(course_ids)
            if (uid, cid) in used:
                continue
            used.add((uid, cid))
            cert_num = f"CERT-{datetime.now().year}-{cert_count + 1:04d}"
            await session.execute(text("""
                INSERT INTO certificates (user_id, course_id, certificate_number, issued_at)
                VALUES (:uid, :cid, :cert_num, :issued)
            """), {
                "uid": uid, "cid": cid,
                "cert_num": cert_num,
                "issued": _past(random.randint(1, 200)),
            })
            cert_count += 1
        print(f"    Created {cert_count} certificates")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 11. FAQ CHATBOT CONVERSATIONS — 18 conversations
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM faq_chatbot_conversations"))
    if r.scalar() == 0:
        print("  Seeding faq_chatbot_conversations...")
        conversations = [
            ("What are your hours today?", "hours",
             "We're open today from 9 AM to 8 PM. Monday-Thursday: 9 AM - 8 PM, Friday: 9 AM - 6 PM, Saturday: 10 AM - 5 PM, Sunday: 1 PM - 5 PM.",
             92, True, False, "desktop", "in_library"),
            ("How do I renew my library card?", "account",
             "You can renew your library card at any service desk with a valid photo ID. Cards are free and renew for 3 years. You can also update your information online through your account.",
             88, True, False, "mobile", "remote"),
            ("How do I download ebooks?", "digital",
             "We offer ebooks through our digital collection. Visit our Ebooks page, browse or search for a title, and click 'Borrow.' You'll need your library card number and PIN. The Palace Project app is the easiest way to read on your phone or tablet.",
             85, True, False, "mobile", "remote"),
            ("Do you have a 3D printer I can use?", "makerspace",
             "Yes! Our Makerspace has two 3D printers available for patron use. You'll need to complete a free safety certification first. Visit the Makerspace desk to sign up for the next training session.",
             90, True, False, "desktop", "in_library"),
            ("What programs do you have for kids this summer?", "programs",
             "We have lots going on this summer! Our Summer Reading Challenge runs June through August with prizes for all ages. We also offer weekly storytimes, STEM workshops, and special performer events. Check our Events page for the full calendar.",
             78, True, False, "mobile", "remote"),
            ("How do I reserve a meeting room?", "facilities",
             "Meeting rooms can be reserved up to 30 days in advance. Visit our Room Reservations page or call the front desk. Rooms are free for nonprofit community groups. A valid library card is required for booking.",
             95, True, False, "desktop", "in_library"),
            ("Can I print from my phone?", "technology",
             "Yes! You can print from your phone using our mobile printing service. Email your document to print@library.local or use the PrinterOn app. Pick up your prints at the circulation desk. Black and white is $0.10/page, color is $0.25/page.",
             82, None, False, "mobile", "in_library"),
            ("Where is the children's section?", "directions",
             "The children's section is on the first floor, to the left of the main entrance. Look for the colorful sign! Storytime is held in the reading nook area at the back of the section.",
             96, True, False, "desktop", "in_library"),
            ("Do you offer ESL classes?", "programs",
             "We offer free English Conversation Circles every Tuesday and Thursday from 10-11:30 AM. These are informal practice sessions for adult English learners at all levels. No registration required — just drop in!",
             75, True, False, "mobile", "remote"),
            ("How do I get a new library card?", "account",
             "Getting a library card is free and easy! Visit any service desk with a valid photo ID and proof of address. Cards are available for all ages. Children under 14 need a parent or guardian present.",
             93, True, False, "desktop", "in_library"),
            ("Is there WiFi here?", "technology",
             "Yes, we offer free WiFi throughout the building. Network name: LibraryPublic. No password needed — just accept the terms of use. We also have ethernet ports available at study carrels.",
             98, True, False, "mobile", "in_library"),
            ("Can my book club meet at the library?", "facilities",
             "Absolutely! We welcome book clubs. You can reserve a meeting room at no charge. We can also help arrange book sets through interlibrary loan if your club needs multiple copies of the same title.",
             87, True, False, "desktop", "remote"),
            ("Do you have a notary?", "services",
             "We do not currently offer notary services at the library. However, several businesses nearby offer this service. The UPS Store on Main Street and First National Bank both have notaries available during business hours.",
             70, False, True, "desktop", "in_library"),
            ("What databases do you have for research?", "digital",
             "We offer access to dozens of research databases including EBSCO, JSTOR, Ancestry, Consumer Reports, and more. Access is free with your library card. Many databases can be used from home through our website.",
             80, True, False, "desktop", "remote"),
            ("My child left their jacket at storytime", "lost_found",
             "I'm sorry, I can't look up lost items directly, but our lost and found is at the circulation desk. Items are kept for 30 days. I'd recommend calling the front desk at (555) 123-4567 to check if it's been turned in.",
             60, None, True, "mobile", "remote"),
            ("How late are you open on Fridays?", "hours",
             "On Fridays, we're open from 9 AM to 6 PM. We close two hours earlier than our weekday schedule. Saturday hours are 10 AM to 5 PM, and Sunday 1 PM to 5 PM.",
             94, True, False, "mobile", "remote"),
            ("Do you have study rooms?", "facilities",
             "Yes, we have 4 individual study rooms and 2 group study rooms available on a first-come, first-served basis. Individual rooms have a 2-hour limit when others are waiting. No reservation needed.",
             91, True, False, "desktop", "in_library"),
            ("Can I volunteer at the library?", "volunteer",
             "We love volunteers! We have opportunities for adults and teens (14+). Applications are on our website under the 'Get Involved' section. Positions include shelving, event setup, tech help, and more. Background checks are required for all volunteers.",
             83, True, False, "mobile", "remote"),
        ]
        for (question, category, response, confidence, helpful, escalated, device, location) in conversations:
            uid = random.choice(patron_ids) if random.random() < 0.4 else None
            sess_id = str(uuid.uuid4())[:16]
            await session.execute(text("""
                INSERT INTO faq_chatbot_conversations (user_id, session_id, original_question, question_category,
                    matched_faq_id, matched_pattern_id, chatbot_response, confidence_score, was_helpful,
                    escalated_to_support, support_ticket_id, device_type, location, created_at)
                VALUES (:uid, :sess, :question, :category, NULL, NULL, :response, :confidence,
                    :helpful, :escalated, NULL, :device, :location, :created)
            """), {
                "uid": uid, "sess": sess_id, "question": question,
                "category": category, "response": response,
                "confidence": confidence, "helpful": helpful,
                "escalated": escalated, "device": device, "location": location,
                "created": _past(random.randint(1, 120)),
            })
        print(f"    Created {len(conversations)} chatbot conversations")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 12. FAQ ANALYTICS — usage stats
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM faq_analytics"))
    if r.scalar() == 0:
        print("  Seeding faq_analytics...")
        analytics = [
            ("What are your hours?", "what are your hours", 342, 310, 12, 91, "hours", True, "all", True, 85, False, None),
            ("How do I get a library card?", "how do i get a library card", 287, 265, 8, 93, "account", False, None, True, 78, False, None),
            ("How do I download ebooks?", "how do i download ebooks", 198, 170, 18, 86, "digital", False, None, True, 72, False, None),
            ("Where is the children's section?", "where is the children's section", 156, 148, 3, 95, "directions", False, None, False, 45, True, 3),
            ("How do I renew books?", "how do i renew books", 234, 220, 5, 94, "circulation", False, None, True, 68, False, None),
            ("Is there WiFi?", "is there wifi", 189, 185, 1, 98, "technology", False, None, False, 40, True, 2),
            ("Do you have meeting rooms?", "do you have meeting rooms", 145, 130, 8, 90, "facilities", False, None, False, 38, False, None),
            ("What summer programs do you have?", "what summer programs", 267, 230, 20, 86, "programs", True, "summer", True, 82, False, None),
            ("How do I use the 3D printer?", "how do i use the 3d printer", 89, 75, 10, 84, "makerspace", False, None, False, 30, False, None),
            ("Do you have a notary?", "do you have a notary", 112, 78, 25, 70, "services", False, None, False, 35, True, 1),
            ("Can I reserve a study room?", "can i reserve a study room", 178, 165, 6, 93, "facilities", False, None, True, 55, False, None),
            ("What databases do you offer?", "what databases do you offer", 134, 120, 9, 90, "digital", False, None, False, 42, False, None),
            ("How do I volunteer?", "how do i volunteer", 98, 88, 4, 90, "volunteer", False, None, False, 28, False, None),
            ("Can I print from my phone?", "can i print from my phone", 167, 150, 10, 90, "technology", False, None, True, 60, False, None),
            ("Do you have ESL classes?", "do you have esl classes", 76, 65, 5, 86, "programs", True, "fall", False, 22, False, None),
            ("Where are the restrooms?", "where are the restrooms", 203, 200, 0, 99, "directions", False, None, False, 15, True, 1),
            ("How late are you open on Saturday?", "how late open saturday", 156, 150, 2, 96, "hours", True, "all", False, 50, False, None),
            ("Do you have audiobooks?", "do you have audiobooks", 143, 130, 7, 91, "collection", False, None, False, 38, False, None),
        ]
        for (question, normalized, ask_ct, answered, escalated, satisfaction,
             category, seasonal, season, trending, trend_score, signage, signage_pri) in analytics:
            await session.execute(text("""
                INSERT INTO faq_analytics (question_text, normalized_question, ask_count, chatbot_answered_count,
                    escalated_count, satisfaction_rate, category, seasonal, season, is_trending, trend_score,
                    suggested_signage, signage_priority)
                VALUES (:q, :norm, :ask, :answered, :escalated, :satisfaction, :category,
                    :seasonal, :season, :trending, :trend_score, :signage, :signage_pri)
            """), {
                "q": question, "norm": normalized, "ask": ask_ct,
                "answered": answered, "escalated": escalated,
                "satisfaction": satisfaction, "category": category,
                "seasonal": seasonal, "season": season,
                "trending": trending, "trend_score": trend_score,
                "signage": signage, "signage_pri": signage_pri,
            })
        print(f"    Created {len(analytics)} FAQ analytics entries")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # FIX SEQUENCES
    # ════════════════════════════════════════════════════════════════
    seq_tables = [
        "reading_registrations", "reading_log_entries", "reading_prizes",
        "reading_achievements", "ebook_featured", "storytime_attendance",
        "storytime_crafts", "certificate_templates", "certificates",
        "faq_chatbot_conversations", "faq_analytics", "reading_programs",
    ]
    for table in seq_tables:
        try:
            async with session.begin_nested():
                await session.execute(text(
                    f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
                ))
        except SQLAlchemyError:
            pass  # Some tables might not have standard sequence naming

    await session.flush()
    print("  Patron-facing batch seeding complete!")
    return True
