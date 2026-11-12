# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import random
import uuid
from datetime import datetime, timedelta, timezone, date, time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

utc = timezone.utc


def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago)


def _past_date(days_ago: int) -> date:
    return (datetime.now(utc) - timedelta(days=days_ago)).date()


def _future(days_ahead: int) -> datetime:
    return datetime.now(utc) + timedelta(days=days_ahead)


def _tok() -> str:
    return uuid.uuid4().hex


async def seed_batch_events_misc(session: AsyncSession) -> bool:

    # ── Reusable IDs ──────────────────────────────────────────────
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] in ("patron", "child")]
    all_ids = [u[0] for u in users]

    ev_r = await session.execute(text("SELECT id FROM events ORDER BY id"))
    event_ids = [r[0] for r in ev_r.fetchall()]

    cat_r = await session.execute(text("SELECT id FROM catalog_items ORDER BY id"))
    catalog_ids = [r[0] for r in cat_r.fetchall()]

    now = datetime.now(utc)

    # ════════════════════════════════════════════════════════════════
    # 3. EVENT MARKETING CAMPAIGNS  (must come before feedback/flyers)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM event_marketing_campaigns"))
    if r.scalar() == 0 and event_ids:
        print("  Seeding event_marketing_campaigns...")
        campaigns_data = [
            ("Summer Reading Kickoff Promo", "Get the word out about our Summer Reading kickoff event!", "Join us for stories, prizes, and fun as we launch Summer Reading 2026!", '{"email": true, "social": true, "flyer": true}'),
            ("Board Game Night Social Push", "Social media campaign for weekly Board Game Night", "Every Friday is Board Game Night at the library! Bring friends, play games, win bragging rights.", '{"social": true, "flyer": false, "email": false}'),
            ("Tech Help Tuesday Campaign", "Multi-channel campaign for Tech Help Tuesday series", "Need help with your phone, tablet, or laptop? Our patient volunteers are here every Tuesday.", '{"email": true, "social": true, "flyer": true}'),
            ("Writers Circle Recruitment", "Attract new members to the Writers Circle", "Whether you write poetry, fiction, or memoir — join our supportive Writers Circle community.", '{"email": true, "social": true, "flyer": true}'),
        ]
        campaign_ids_created = []
        for i, (name, short_desc, copy, channels) in enumerate(campaigns_data):
            eid = event_ids[i % len(event_ids)]
            r2 = await session.execute(text("""
                INSERT INTO event_marketing_campaigns
                    (event_id, campaign_name, short_description, marketing_copy,
                     hashtags, target_audience_tags, channels, distribute_at,
                     auto_distribute, archive_status, created_by_id, created_at, updated_at)
                VALUES (:eid, :name, :short, :copy,
                        '{"#LibraryLife","#ReadMore"}'::varchar[],
                        '{"families","adults"}'::varchar[],
                        cast(:channels as jsonb), :dist,
                        false, 'active', :staff, :created, :created)
                RETURNING id
            """), {
                "eid": eid, "name": name, "short": short_desc, "copy": copy,
                "channels": channels, "dist": _past(random.randint(1, 30)),
                "staff": random.choice(staff_ids), "created": _past(random.randint(30, 90)),
            })
            campaign_ids_created.append(r2.scalar())
        print(f"    Created {len(campaigns_data)} event marketing campaigns")
        await session.flush()

    # Fetch campaign IDs for dependent tables
    emc_r = await session.execute(text("SELECT id FROM event_marketing_campaigns ORDER BY id"))
    emc_ids = [r[0] for r in emc_r.fetchall()]

    # ════════════════════════════════════════════════════════════════
    # 1. EVENT FEEDBACK
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM event_feedback"))
    if r.scalar() == 0 and event_ids and emc_ids:
        print("  Seeding event_feedback...")
        feedback_items = [
            (5, True, True, "Loved the energy and the speaker", "Maybe more seating next time", "social_media"),
            (4, True, True, "Great selection of activities", "Longer time slots would help", "newsletter"),
            (5, True, True, "My kids had an amazing time", None, "friend"),
            (3, False, True, "It was okay, a bit crowded", "Better signage for rooms", "website"),
            (4, True, True, "Really informative session", "Handouts would be nice", "flyer"),
            (5, True, True, "Best library event I have attended", None, "social_media"),
            (2, False, False, "Not what I expected from the description", "More accurate descriptions please", "newsletter"),
            (4, True, True, "Good networking opportunity", "Offer name tags", "word_of_mouth"),
            (5, True, True, "The presenter was fantastic", None, "email"),
            (4, True, True, "Fun for the whole family", "Add a snack table", "website"),
            (3, True, False, "Decent but could be more interactive", "More hands-on activities", "flyer"),
            (5, True, True, "Exactly what our community needed", None, "social_media"),
            (4, False, True, "Learned a lot about local resources", "Follow-up materials via email", "newsletter"),
            (5, True, True, "Will definitely come back next month", None, "friend"),
            (4, True, True, "Well organized and on time", "Parking was tough", "website"),
            (3, True, False, "Good concept, needs polish", "Better AV setup", "flyer"),
            (5, True, True, "My favorite recurring event", None, "word_of_mouth"),
            (4, True, True, "Welcoming atmosphere, friendly staff", None, "email"),
            (5, True, True, "Changed my perspective on the topic", "Offer a follow-up workshop", "social_media"),
            (4, True, True, "Great use of library space", "More events like this please", "newsletter"),
        ]
        names = ["Alex T.", "Jordan M.", "Sam K.", "Pat R.", "Chris L.",
                 "Morgan D.", "Taylor S.", "Jamie B.", "Casey W.", "Robin N."]
        for i, (rating, again, recommend, liked, improve, source) in enumerate(feedback_items):
            await session.execute(text("""
                INSERT INTO event_feedback
                    (campaign_id, event_id, patron_name, is_anonymous, overall_rating,
                     would_attend_again, would_recommend, what_liked, what_improve,
                     heard_from_source, feedback_token, created_at, updated_at)
                VALUES (:cid, :eid, :name, :anon, :rating,
                        :again, :recommend, :liked, :improve,
                        :source, :token, :created, :created)
            """), {
                "cid": random.choice(emc_ids), "eid": random.choice(event_ids),
                "name": random.choice(names), "anon": random.choice([True, False]),
                "rating": rating, "again": again, "recommend": recommend,
                "liked": liked, "improve": improve, "source": source,
                "token": _tok(), "created": _past(random.randint(1, 60)),
            })
        print(f"    Created {len(feedback_items)} event feedback entries")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 2. EVENT FLYERS + EVENT GRAPHICS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM event_flyers"))
    if r.scalar() == 0 and emc_ids:
        print("  Seeding event_flyers...")
        flyers = [
            ("letter", "Summer Reading Kickoff", "June 1st — All Ages Welcome!"),
            ("half_page", "Board Game Night", "Every Friday 6-9 PM"),
            ("letter", "Tech Help Tuesday", "Free one-on-one tech assistance"),
            ("poster", "Writers Circle", "Share your words, find your voice"),
            ("half_page", "Story Time", "Wednesdays at 10:30 AM"),
            ("letter", "Book Club Monthly", "New picks every first Thursday"),
        ]
        for title_text, subtitle, body in flyers:
            color = json.dumps({"primary": "#2563EB", "secondary": "#FBBF24", "text": "#1F2937"})
            await session.execute(text("""
                INSERT INTO event_flyers
                    (campaign_id, size, title, subtitle, body_text,
                     template_name, color_scheme, include_logo, include_map,
                     print_count, generated_by_id, created_at, updated_at)
                VALUES (:cid, :size, :title, :sub, :body,
                        'standard_v2', cast(:color as jsonb), true, false,
                        :prints, :staff, :created, :created)
            """), {
                "cid": random.choice(emc_ids), "size": title_text,
                "title": subtitle, "sub": body, "body": f"Join us at the library for {subtitle}. All are welcome!",
                "color": color, "prints": random.randint(25, 200),
                "staff": random.choice(staff_ids), "created": _past(random.randint(5, 60)),
            })
        print(f"    Created {len(flyers)} event flyers")
        await session.flush()

    r = await session.execute(text("SELECT COUNT(*) FROM event_graphics"))
    if r.scalar() == 0 and emc_ids:
        print("  Seeding event_graphics...")
        graphics = [
            ("instagram_post", "Summer Reading IG Post", 1080, 1080),
            ("facebook_cover", "Board Game Night FB Cover", 1200, 630),
            ("twitter_card", "Tech Help Tuesday Tweet", 1200, 675),
            ("instagram_story", "Writers Circle Story", 1080, 1920),
            ("facebook_post", "Story Time Promo", 1200, 1200),
            ("email_header", "Book Club Email Banner", 600, 200),
            ("instagram_post", "Library Events Roundup", 1080, 1080),
            ("twitter_card", "Weekend Events Preview", 1200, 675),
        ]
        for fmt, title, w, h in graphics:
            color = json.dumps({"primary": "#7C3AED", "accent": "#F59E0B"})
            await session.execute(text("""
                INSERT INTO event_graphics
                    (campaign_id, format, title, width, height,
                     template_name, color_scheme, download_count, share_count,
                     created_at, updated_at)
                VALUES (:cid, :fmt, :title, :w, :h,
                        'social_v3', cast(:color as jsonb), :dl, :shares,
                        :created, :created)
            """), {
                "cid": random.choice(emc_ids), "fmt": fmt, "title": title,
                "w": w, "h": h, "color": color,
                "dl": random.randint(0, 15), "shares": random.randint(0, 8),
                "created": _past(random.randint(5, 60)),
            })
        print(f"    Created {len(graphics)} event graphics")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 4. CAMPAIGN RECIPIENTS  (FK -> marketing_campaigns, not event_marketing_campaigns)
    # ════════════════════════════════════════════════════════════════
    mktg_r = await session.execute(text("SELECT id FROM marketing_campaigns ORDER BY id"))
    mktg_ids = [r[0] for r in mktg_r.fetchall()]

    nl_r = await session.execute(text("SELECT id FROM newsletter_subscriptions ORDER BY id"))
    nl_ids = [r[0] for r in nl_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM campaign_recipients"))
    if r.scalar() == 0 and mktg_ids and nl_ids:
        print("  Seeding campaign_recipients...")
        statuses = ["sent", "delivered", "opened", "clicked"]
        count = 0
        used_pairs = set()
        for cid in mktg_ids:
            email_counter = 0
            for _ in range(random.randint(5, 8)):
                email_counter += 1
                email = f"patron_c{cid}_r{email_counter}@example.com"
                if (cid, email) in used_pairs:
                    continue
                used_pairs.add((cid, email))
                st = random.choice(statuses)
                sent = _past(random.randint(1, 30))
                await session.execute(text("""
                    INSERT INTO campaign_recipients
                        (campaign_id, subscription_id, email, status,
                         sent_at, delivered_at, opened_at, clicked_at, unsubscribe_token)
                    VALUES (:cid, :sid, :email, :status,
                            :sent, :delivered, :opened, :clicked, :token)
                """), {
                    "cid": cid, "sid": random.choice(nl_ids),
                    "email": email,
                    "status": st, "sent": sent,
                    "delivered": sent + timedelta(minutes=2) if st in ("delivered", "opened", "clicked") else None,
                    "opened": sent + timedelta(hours=random.randint(1, 24)) if st in ("opened", "clicked") else None,
                    "clicked": sent + timedelta(hours=random.randint(2, 48)) if st == "clicked" else None,
                    "token": _tok(),
                })
                count += 1
        print(f"    Created {count} campaign recipients")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 5. EVENT DISTRIBUTIONS + EVENT REGISTRATION SOURCES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM event_distributions"))
    if r.scalar() == 0 and emc_ids:
        print("  Seeding event_distributions...")
        channels = ["facebook", "twitter", "instagram", "email", "website"]
        count = 0
        for cid in emc_ids:
            for ch in random.sample(channels, random.randint(2, 4)):
                posted = _past(random.randint(1, 30))
                await session.execute(text("""
                    INSERT INTO event_distributions
                        (campaign_id, channel, status, posted_at,
                         impressions, clicks, likes, shares, comments,
                         retry_count, max_retries, created_at, updated_at)
                    VALUES (:cid, :ch, 'posted', :posted,
                            :imp, :clicks, :likes, :shares, :comments,
                            0, 3, :created, :created)
                """), {
                    "cid": cid, "ch": ch, "posted": posted,
                    "imp": random.randint(50, 2000), "clicks": random.randint(5, 200),
                    "likes": random.randint(2, 80), "shares": random.randint(0, 30),
                    "comments": random.randint(0, 15), "created": posted,
                })
                count += 1
        print(f"    Created {count} event distributions")
        await session.flush()

    reg_r = await session.execute(text("SELECT id FROM event_registrations ORDER BY id"))
    reg_ids = [r[0] for r in reg_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM event_registration_sources"))
    if r.scalar() == 0 and emc_ids:
        print("  Seeding event_registration_sources...")
        sources = [
            ("facebook", "social", "summer2026"),
            ("google", "cpc", "tech_help"),
            ("newsletter", "email", "monthly_digest"),
            ("direct", "none", "walk_in"),
            ("twitter", "social", "writers_promo"),
            ("instagram", "social", "story_ad"),
            ("flyer", "print", "branch_display"),
            ("partner_site", "referral", "community_center"),
        ]
        for source, medium, tag in sources:
            await session.execute(text("""
                INSERT INTO event_registration_sources
                    (campaign_id, registration_id, source, medium, campaign_tag,
                     tracking_token, click_count, first_clicked_at, created_at, updated_at)
                VALUES (:cid, :rid, :source, :medium, :tag,
                        :token, :clicks, :clicked, :created, :created)
            """), {
                "cid": random.choice(emc_ids),
                "rid": random.choice(reg_ids) if reg_ids else None,
                "source": source, "medium": medium, "tag": tag,
                "token": _tok(), "clicks": random.randint(1, 50),
                "clicked": _past(random.randint(1, 30)),
                "created": _past(random.randint(1, 30)),
            })
        print(f"    Created {len(sources)} event registration sources")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 6. EVENT REVIEW RESPONSES + REPEAT ATTENDEES + SHARED EVENTS
    # ════════════════════════════════════════════════════════════════
    er_r = await session.execute(text("SELECT id FROM event_reviews ORDER BY id"))
    er_ids = [r[0] for r in er_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM event_review_responses"))
    if r.scalar() == 0 and er_ids:
        print("  Seeding event_review_responses...")
        responses = [
            ("Thank you for your kind words! We are so glad you enjoyed the event.", True),
            ("We appreciate the feedback and will look into improving the seating.", True),
            ("Thanks for coming! We hope to see you at our next session.", True),
            ("Great suggestion — we will add handouts for future workshops.", True),
            ("We are thrilled the kids had fun! Family-friendly events are our favorite.", True),
            ("I also loved this event — the speaker was so engaging!", False),
            ("Totally agree about the parking situation. Carpooling helped us!", False),
            ("My family had a great time too. The craft station was a hit!", False),
        ]
        for content, is_staff in responses:
            aid = random.choice(staff_ids) if is_staff else random.choice(all_ids)
            await session.execute(text("""
                INSERT INTO event_review_responses
                    (review_id, author_id, content, is_staff_response,
                     moderation_status)
                VALUES (:rid, :aid, :content, :is_staff, 'approved')
            """), {
                "rid": random.choice(er_ids), "aid": aid,
                "content": content, "is_staff": is_staff,
            })
        print(f"    Created {len(responses)} event review responses")
        await session.flush()

    st_r = await session.execute(text("SELECT id FROM storytime_sessions ORDER BY id"))
    st_ids = [r[0] for r in st_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM repeat_attendees"))
    if r.scalar() == 0 and st_ids:
        print("  Seeding repeat_attendees...")
        attendees = [
            ("caregiver_001", "Elena Vasquez", 12, "devoted"),
            ("caregiver_002", "Marcus Johnson", 8, "frequent"),
            ("caregiver_003", "Priya Patel", 22, "super_fan"),
            ("caregiver_004", "Tom O'Brien", 5, "regular"),
            ("caregiver_005", "Aisha Williams", 15, "devoted"),
            ("caregiver_006", "David Chen", 3, "regular"),
            ("caregiver_007", "Sarah Kim", 10, "frequent"),
            ("caregiver_008", "James Rodriguez", 6, "regular"),
        ]
        for ident, name, sessions, status in attendees:
            first = _past_date(sessions * 7 + random.randint(0, 30))
            last = _past_date(random.randint(1, 14))
            await session.execute(text("""
                INSERT INTO repeat_attendees
                    (session_id, caregiver_identifier, caregiver_name,
                     total_sessions_attended, last_attended_date, first_attended_date,
                     recognition_status, recognition_badges,
                     theme_preferences)
                VALUES (:sid, :ident, :name,
                        :sessions, :last, :first,
                        :status, '{"loyal_reader","storytime_regular"}'::varchar[],
                        '{"animals","music","science"}'::varchar[])
            """), {
                "sid": random.choice(st_ids), "ident": ident, "name": name,
                "sessions": sessions, "last": last, "first": first,
                "status": status,
            })
        print(f"    Created {len(attendees)} repeat attendees")
        await session.flush()

    op_r = await session.execute(text("SELECT id FROM outreach_partners ORDER BY id"))
    op_ids = [r[0] for r in op_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM shared_events"))
    if r.scalar() == 0 and op_ids:
        print("  Seeding shared_events...")
        shared = [
            ("Community Health Fair", "Joint health and wellness event with local partners", "community_event", "completed"),
            ("Teen Career Workshop", "Career exploration workshop co-hosted with schools", "workshop", "completed"),
            ("Senior Tech Day", "Technology help day for seniors at assisted living", "outreach", "confirmed"),
            ("Summer Literacy Carnival", "Fun literacy activities for elementary-age kids", "program", "planned"),
            ("Immigrant Resource Fair", "Connecting newcomers with community resources", "community_event", "confirmed"),
        ]
        for title, desc, etype, status in shared:
            co_ids_lit = "'{" + ",".join(str(x) for x in random.sample(op_ids, min(2, len(op_ids)))) + "}'"
            coord_ids_lit = "'{" + ",".join(str(x) for x in random.sample(staff_ids, min(2, len(staff_ids)))) + "}'"
            await session.execute(text(f"""
                INSERT INTO shared_events
                    (title, description, event_type, event_date, start_time, end_time,
                     status, is_public, location, organizing_partner_id,
                     co_organizing_partner_ids, expected_attendance, target_audience,
                     budget, coordinator_ids, created_by_id)
                VALUES (:title, :desc, :etype, :edate, '10:00', '14:00',
                        :status, true, 'Main Branch', :op_id,
                        {co_ids_lit}::integer[], :attendance, 'Community members',
                        :budget, {coord_ids_lit}::integer[], :staff)
            """), {
                "title": title, "desc": desc, "etype": etype,
                "edate": _past_date(random.randint(1, 90)),
                "status": status, "op_id": random.choice(op_ids),
                "attendance": random.randint(30, 200),
                "budget": round(random.uniform(200, 2000), 2),
                "staff": random.choice(staff_ids),
            })
        print(f"    Created {len(shared)} shared events")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 7. SOCIAL MEDIA CONFIGS + SOCIAL SHARING CONFIG
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM social_media_configs"))
    if r.scalar() == 0:
        print("  Seeding social_media_configs...")
        configs = [
            ("facebook", "L30 Library - Facebook", True, True),
            ("twitter", "L30 Library - Twitter/X", True, True),
            ("instagram", "L30 Library - Instagram", True, False),
            ("linkedin", "L30 Library - LinkedIn", False, False),
        ]
        for platform, display, active, auto in configs:
            await session.execute(text("""
                INSERT INTO social_media_configs
                    (platform, display_name, is_active, auto_post_enabled,
                     default_hashtags, configured_by_id, created_at, updated_at)
                VALUES (:platform, :display, :active, :auto,
                        '{"#L30Library","#ReadLocal","#LibraryLife"}'::varchar[],
                        :staff, :created, :created)
            """), {
                "platform": platform, "display": display,
                "active": active, "auto": auto,
                "staff": random.choice(staff_ids), "created": _past(120),
            })
        print(f"    Created {len(configs)} social media configs")
        await session.flush()

    r = await session.execute(text("SELECT COUNT(*) FROM social_sharing_config"))
    if r.scalar() == 0:
        print("  Seeding social_sharing_config...")
        await session.execute(text("""
            INSERT INTO social_sharing_config
                (sharing_enabled, share_buttons_enabled, share_counts_enabled,
                 default_message_template, twitter_handle, linkedin_enabled,
                 pinterest_enabled, email_enabled, copy_link_enabled,
                 utm_tracking_enabled, utm_source, utm_medium,
                 updated_by_id, created_at, updated_at)
            VALUES (true, true, true,
                    'Check out this event at L30 Library! {title} - {url}',
                    '@L30Library', true,
                    false, true, true,
                    true, 'l30_library', 'social_share',
                    :staff, :created, :created)
        """), {"staff": random.choice(staff_ids), "created": _past(90)})
        print("    Created 1 social sharing config")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 8. GENERATED MARKETING CONTENT + SUBSCRIBER INTERESTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM generated_marketing_content"))
    if r.scalar() == 0:
        print("  Seeding generated_marketing_content...")
        content_items = [
            ("social_post", "Summer Reading Launch Tweet", "Join us June 1st for the Summer Reading Kickoff! Games, prizes, and stories for all ages. #SummerReading #LibraryFun", "Write a tweet promoting a summer reading kickoff event at a public library"),
            ("newsletter", "Monthly Events Digest", "This month at L30 Library: Board Game Night returns, new Tech Help hours, and our Writers Circle welcomes guest author Maria Torres. Plus, do not miss Storytime Wednesdays!", "Write a brief monthly newsletter intro highlighting upcoming library events"),
            ("flyer", "Teen Book Club Flyer Copy", "TEEN BOOK CLUB — First Thursday of every month at 4 PM. Current pick: The House in the Cerulean Sea. Snacks provided. No sign-up needed. Bring a friend!", "Write copy for a teen book club flyer"),
            ("event_promo", "Maker Monday Promo", "This Monday: Learn to use our 3D printer! Maker Monday is open to all skill levels. Our trained staff will walk you through your first print. Spots are limited — register online.", "Write a promotional paragraph for a library makerspace event"),
            ("program_promo", "ESL Conversation Circle", "Practice your English in a friendly, supportive group! Our ESL Conversation Circle meets Tuesdays and Thursdays at 2 PM. All levels welcome. Free childcare available.", "Write a promo for an ESL conversation circle at a library"),
            ("social_post", "Banned Books Week IG", "Celebrate the freedom to read! This week we spotlight books that have been challenged in libraries across the country. Visit our display in the main lobby. #BannedBooksWeek", "Write an Instagram caption for Banned Books Week"),
        ]
        for ctype, title, gen_text, prompt in content_items:
            await session.execute(text("""
                INSERT INTO generated_marketing_content
                    (content_type, title, generated_text, user_prompt,
                     model_used, temperature, generation_time_ms,
                     event_id, is_favorite, created_by_id, created_at)
                VALUES (:ctype, :title, :text, :prompt,
                        'llama3.2:1b', 0.7, :ms,
                        :eid, :fav, :staff, :created)
            """), {
                "ctype": ctype, "title": title, "text": gen_text, "prompt": prompt,
                "ms": random.randint(800, 3000),
                "eid": random.choice(event_ids) if event_ids else None,
                "fav": random.choice([True, False]),
                "staff": random.choice(staff_ids), "created": _past(random.randint(1, 60)),
            })
        print(f"    Created {len(content_items)} generated marketing content items")
        await session.flush()

    # subscriber_interests requires interest_categories — check if any exist
    ic_r = await session.execute(text("SELECT id FROM interest_categories ORDER BY id"))
    ic_ids = [r[0] for r in ic_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM subscriber_interests"))
    if r.scalar() == 0 and nl_ids and ic_ids:
        print("  Seeding subscriber_interests...")
        count = 0
        used = set()
        for sid in random.sample(nl_ids, min(len(nl_ids), 20)):
            for cid in random.sample(ic_ids, min(len(ic_ids), random.randint(1, 3))):
                if (sid, cid) not in used:
                    used.add((sid, cid))
                    await session.execute(text("""
                        INSERT INTO subscriber_interests (subscription_id, category_id, subscribed_at)
                        VALUES (:sid, :cid, :sub_at)
                    """), {"sid": sid, "cid": cid, "sub_at": _past(random.randint(1, 90))})
                    count += 1
        print(f"    Created {count} subscriber interests")
        await session.flush()
    elif not ic_ids:
        print("  Skipping subscriber_interests — no interest_categories exist")

    # ════════════════════════════════════════════════════════════════
    # 9. AMA SESSIONS (now managed by MetisLib — no local seeding)
    # ════════════════════════════════════════════════════════════════

    # ════════════════════════════════════════════════════════════════
    # 10. NOTIFICATION QUEUE + NOTIFICATION HISTORY + NOTIFICATION METRICS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM notification_queue"))
    if r.scalar() == 0:
        print("  Seeding notification_queue...")
        notifs = [
            ("hold_ready", "sent", "Hold Ready for Pickup", "<p>Great news! Your hold is ready for pickup at the front desk.</p>"),
            ("due_date_reminder", "sent", "Items Due Soon", "<p>You have items due in 3 days. Please return or renew them.</p>"),
            ("overdue_notice", "pending", "Overdue Notice", "<p>Your borrowed items are now overdue. Please return them soon.</p>"),
            ("hold_expiring", "sent", "Hold Expiring Soon", "<p>Your hold will expire in 48 hours. Please pick it up.</p>"),
            ("checkout_receipt", "sent", "Checkout Confirmation", "<p>Your checkout has been confirmed.</p>"),
            ("event_reminder", "failed", "Event Reminder", "<p>Reminder: your registered event is coming up soon.</p>"),
            ("welcome_email", "cancelled", "Welcome to the Library", "<p>Welcome! Your library account has been created.</p>"),
            ("overdue_notice", "pending", "Your Daily Library Digest", "<p>Here is your daily library activity summary.</p>"),
        ]
        for ntype, status, subject, body in notifs:
            uid = random.choice(all_ids)
            scheduled = _past(random.randint(0, 14))
            await session.execute(text("""
                INSERT INTO notification_queue
                    (user_id, notification_type, status, recipient_email,
                     subject, html_body, scheduled_for,
                     sent_at, retry_count)
                VALUES (:uid, :ntype, :status, :email,
                        :subject, :body, :scheduled,
                        :sent, :retry)
            """), {
                "uid": uid, "ntype": ntype, "status": status,
                "email": f"user{uid}@example.com",
                "subject": subject, "body": body,
                "scheduled": scheduled,
                "sent": scheduled + timedelta(seconds=30) if status == "sent" else None,
                "retry": 0 if status != "failed" else 3,
            })
        print(f"    Created {len(notifs)} notification queue entries")
        await session.flush()

    r = await session.execute(text("SELECT COUNT(*) FROM notification_history"))
    if r.scalar() == 0:
        print("  Seeding notification_history...")
        count = 0
        for _ in range(15):
            uid = random.choice(all_ids)
            ntype = random.choice(["new_match", "match_accepted", "swap_claimed", "claim_approved"])
            sent = _past(random.randint(1, 60))
            await session.execute(text("""
                INSERT INTO notification_history
                    (user_id, notification_type, recipient_email, subject,
                     sent_at, success)
                VALUES (:uid, :ntype, :email, :subject,
                        :sent, :success)
            """), {
                "uid": uid, "ntype": ntype,
                "email": f"user{uid}@example.com",
                "subject": f"Library Notification: {ntype.replace('_', ' ').title()}",
                "sent": sent, "success": random.choice([True, True, True, False]),
            })
            count += 1
        print(f"    Created {count} notification history entries")
        await session.flush()

    r = await session.execute(text("SELECT COUNT(*) FROM notification_metrics"))
    if r.scalar() == 0:
        print("  Seeding notification_metrics...")
        templates = ["hold_ready", "overdue_notice", "event_reminder", "welcome_email"]
        count = 0
        for tmpl in templates:
            for ch in ["email", "sms"]:
                window = _past(random.randint(1, 7))
                sent = random.randint(20, 200)
                success = int(sent * random.uniform(0.85, 0.99))
                fail = sent - success
                await session.execute(text("""
                    INSERT INTO notification_metrics
                        (channel, template_name, window_start,
                         sent_count, success_count, failure_count, timeout_count,
                         created_at, updated_at)
                    VALUES (:ch, :tmpl, :window,
                            :sent, :success, :fail, :timeout,
                            :created, :created)
                """), {
                    "ch": ch, "tmpl": tmpl, "window": window,
                    "sent": sent, "success": success, "fail": fail,
                    "timeout": random.randint(0, 3),
                    "created": window,
                })
                count += 1
        print(f"    Created {count} notification metrics entries")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 11. SMS TEMPLATES + SMS QUEUE + SMS DELIVERY LOG + SMS COST RECORDS + SMS OPT OUTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM sms_templates"))
    if r.scalar() == 0:
        print("  Seeding sms_templates...")
        templates = [
            ("hold_ready", "L30 Library: Your hold '{title}' is ready for pickup at {branch}. Pick up by {expiry_date}. Reply STOP to opt out.", 160, True, 2),
            ("overdue_notice", "L30 Library: '{title}' is overdue. Please return it to avoid additional fees. Questions? Call (555) 123-4567. Reply STOP to opt out.", 160, True, 2),
            ("due_date_reminder", "L30 Library: '{title}' is due on {due_date}. Renew online at l30.org or reply RENEW. Reply STOP to opt out.", 160, False, 1),
            ("event_reminder", "L30 Library: Reminder — '{event_name}' is tomorrow at {time}! We look forward to seeing you. Reply STOP to opt out.", 160, False, 1),
            ("checkout_receipt", "L30 Library: You checked out {count} item(s). Due back {due_date}. Manage your account at l30.org. Reply STOP to opt out.", 160, False, 1),
            ("ad_hoc", "L30 Library: {message} Reply STOP to opt out.", 160, True, 3),
        ]
        for ntype, body, max_chars, multipart, max_seg in templates:
            await session.execute(text("""
                INSERT INTO sms_templates
                    (notification_type, template_body, max_chars, allow_multipart,
                     max_segments, description, is_active,
                     created_by_user_id)
                VALUES (:ntype, :body, :max_chars, :multi,
                        :max_seg, :desc, true,
                        :staff)
            """), {
                "ntype": ntype, "body": body, "max_chars": max_chars,
                "multi": multipart, "max_seg": max_seg,
                "desc": f"Template for {ntype.replace('_', ' ').lower()} SMS notifications",
                "staff": random.choice(staff_ids),
            })
        print(f"    Created {len(templates)} SMS templates")
        await session.flush()

    r = await session.execute(text("SELECT COUNT(*) FROM sms_queue"))
    if r.scalar() == 0:
        print("  Seeding sms_queue...")
        sms_items = [
            ("hold_ready", "delivered", "(555) 234-5678", "L30 Library: Your hold 'Project Hail Mary' is ready at Main Branch. Pick up by 3/25."),
            ("overdue_notice", "delivered", "(555) 345-6789", "L30 Library: 'The Midnight Library' is overdue. Please return to avoid fees."),
            ("due_date_reminder", "sent", "(555) 456-7890", "L30 Library: 'Lessons in Chemistry' is due on 3/20. Renew online."),
            ("event_reminder", "delivered", "(555) 567-8901", "L30 Library: Reminder — Board Game Night is tomorrow at 6 PM!"),
            ("hold_ready", "failed", "(555) 678-9012", "L30 Library: Your hold 'Tomorrow and Tomorrow' is ready."),
            ("checkout_receipt", "delivered", "(555) 789-0123", "L30 Library: You checked out 3 items. Due back 4/1."),
            ("ad_hoc", "pending", "(555) 890-1234", "L30 Library: The library will be closed this Saturday for maintenance."),
            ("overdue_notice", "delivered", "(555) 901-2345", "L30 Library: 'Yellowface' is overdue. Please return."),
        ]
        sms_q_ids = []
        for ntype, status, phone, msg in sms_items:
            uid = random.choice(all_ids)
            scheduled = _past(random.randint(0, 14))
            r2 = await session.execute(text("""
                INSERT INTO sms_queue
                    (user_id, notification_type, status, recipient_phone,
                     message_body, message_segments, scheduled_for,
                     sent_at, delivered_at, failed_at,
                     retry_count, max_retries, cost_cents, initiated_by_user_id)
                VALUES (:uid, :ntype, :status, :phone,
                        :msg, 1, :scheduled,
                        :sent, :delivered, :failed,
                        :retry, 3, :cost, :staff)
                RETURNING id
            """), {
                "uid": uid, "ntype": ntype, "status": status, "phone": phone,
                "msg": msg, "scheduled": scheduled,
                "sent": scheduled + timedelta(seconds=5) if status in ("sent", "delivered") else None,
                "delivered": scheduled + timedelta(seconds=15) if status == "delivered" else None,
                "failed": scheduled + timedelta(seconds=10) if status == "failed" else None,
                "retry": 3 if status == "failed" else 0,
                "cost": random.choice([1, 1, 2]) if status == "delivered" else None,
                "staff": random.choice(staff_ids),
            })
            sms_q_ids.append(r2.scalar())
        print(f"    Created {len(sms_items)} SMS queue entries")
        await session.flush()

    sq_r = await session.execute(text("SELECT id FROM sms_queue ORDER BY id"))
    sq_ids = [r[0] for r in sq_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM sms_delivery_log"))
    if r.scalar() == 0 and sq_ids:
        print("  Seeding sms_delivery_log...")
        count = 0
        for sqid in sq_ids:
            for prev, new in [("pending", "sent"), ("sent", "delivered")]:
                await session.execute(text("""
                    INSERT INTO sms_delivery_log
                        (sms_queue_id, previous_status, new_status)
                    VALUES (:sqid, :prev, :new)
                """), {"sqid": sqid, "prev": prev, "new": new})
                count += 1
        print(f"    Created {count} SMS delivery log entries")
        await session.flush()

    r = await session.execute(text("SELECT COUNT(*) FROM sms_cost_records"))
    if r.scalar() == 0:
        print("  Seeding sms_cost_records...")
        count = 0
        for uid in random.sample(all_ids, min(len(all_ids), 10)):
            for ntype in random.sample(["hold_ready", "overdue_notice", "due_date_reminder", "event_reminder"], 2):
                sent = random.randint(1, 8)
                delivered = max(0, sent - random.randint(0, 1))
                await session.execute(text("""
                    INSERT INTO sms_cost_records
                        (user_id, year, month, notification_type,
                         messages_sent, messages_delivered, messages_failed,
                         total_segments, total_cost_cents)
                    VALUES (:uid, 2026, :month, :ntype,
                            :sent, :delivered, :failed,
                            :segments, :cost)
                """), {
                    "uid": uid, "month": random.randint(1, 3), "ntype": ntype,
                    "sent": sent, "delivered": delivered,
                    "failed": sent - delivered, "segments": sent,
                    "cost": sent * random.choice([1, 2]),
                })
                count += 1
        print(f"    Created {count} SMS cost records")
        await session.flush()

    r = await session.execute(text("SELECT COUNT(*) FROM sms_opt_outs"))
    if r.scalar() == 0:
        print("  Seeding sms_opt_outs...")
        opt_outs = [
            ("(555) 111-0001", "stop", True),
            ("(555) 111-0002", "STOP ALL", True),
            ("(555) 111-0003", "stop", False),  # re-opted in
        ]
        for phone, msg, active in opt_outs:
            uid = random.choice(all_ids)
            opted_out = _past(random.randint(10, 60))
            await session.execute(text("""
                INSERT INTO sms_opt_outs
                    (phone_number, user_id, opted_out_at, opt_out_message,
                     opted_in_at, is_active)
                VALUES (:phone, :uid, :out_at, :msg,
                        :in_at, :active)
            """), {
                "phone": phone, "uid": uid, "out_at": opted_out,
                "msg": msg,
                "in_at": _past(5) if not active else None,
                "active": active,
            })
        print(f"    Created {len(opt_outs)} SMS opt-out records")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 12. EMAIL UNSUBSCRIBE TOKENS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM email_unsubscribe_tokens"))
    if r.scalar() == 0:
        print("  Seeding email_unsubscribe_tokens...")
        tokens = [
            ("events", "event_notifications"),
            ("newsletter", "marketing"),
            ("holds", "transactional"),
            ("overdue", "transactional"),
            ("newsletter", "marketing"),
            ("events", "event_notifications"),
            ("holds", "transactional"),
            ("newsletter", "marketing"),
        ]
        for etype, category in tokens:
            uid = random.choice(all_ids)
            await session.execute(text("""
                INSERT INTO email_unsubscribe_tokens
                    (token, user_id, email, email_type, email_category, expires_at)
                VALUES (:token, :uid, :email, :etype, :cat, :expires)
            """), {
                "token": _tok(), "uid": uid,
                "email": f"user{uid}@example.com",
                "etype": etype, "cat": category,
                "expires": _future(90),
            })
        print(f"    Created {len(tokens)} email unsubscribe tokens")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 13. PRINT NOTICE BATCHES + PRINT NOTICES + PRINT NOTICE HISTORY + COST CONFIG
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM print_notice_batches"))
    if r.scalar() == 0:
        print("  Seeding print_notice_batches...")
        batches = [
            ("BATCH-2026-001", "January Overdue Notices", "completed", 12, 18),
            ("BATCH-2026-002", "February Mixed Notices", "mailed", 8, 12),
            ("BATCH-2026-003", "March Overdue Notices", "printed", 15, 22),
            ("BATCH-2026-004", "March Welcome Letters", "open", 5, 5),
        ]
        batch_ids_created = []
        for bnum, name, status, notice_ct, pages in batches:
            opened = _past(random.randint(5, 60))
            r2 = await session.execute(text("""
                INSERT INTO print_notice_batches
                    (batch_number, name, status, notice_count, page_count,
                     total_print_cost, total_postage_cost,
                     opened_at, closed_at, printed_at, mailed_at, completed_at,
                     created_by_id, notes)
                VALUES (:bnum, :name, :status, :ct, :pages,
                        :print_cost, :postage_cost,
                        :opened, :closed, :printed, :mailed, :completed,
                        :staff, :notes)
                RETURNING id
            """), {
                "bnum": bnum, "name": name, "status": status,
                "ct": notice_ct, "pages": pages,
                "print_cost": round(pages * 0.08, 2),
                "postage_cost": round(notice_ct * 0.63, 2),
                "opened": opened,
                "closed": opened + timedelta(hours=2) if status != "open" else None,
                "printed": opened + timedelta(hours=4) if status in ("printed", "mailed", "completed") else None,
                "mailed": opened + timedelta(days=1) if status in ("mailed", "completed") else None,
                "completed": opened + timedelta(days=5) if status == "completed" else None,
                "staff": random.choice(staff_ids),
                "notes": f"Batch {bnum} — {status.lower()}",
            })
            batch_ids_created.append(r2.scalar())
        print(f"    Created {len(batches)} print notice batches")
        await session.flush()

    pnb_r = await session.execute(text("SELECT id FROM print_notice_batches ORDER BY id"))
    pnb_ids = [r[0] for r in pnb_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM print_notices"))
    if r.scalar() == 0 and pnb_ids:
        print("  Seeding print_notices...")
        notice_types = ["overdue", "fine", "hold_ready", "welcome"]
        count = 0
        for _ in range(12):
            uid = random.choice(patron_ids) if patron_ids else random.choice(all_ids)
            ntype = random.choice(notice_types)
            await session.execute(text("""
                INSERT INTO print_notices
                    (patron_id, notice_type, status, batch_id,
                     recipient_name, address_line1, city, state, zip_code, country,
                     subject, body_html, print_cost, postage_cost, pages,
                     created_by_id)
                VALUES (:uid, :ntype, 'BATCHED', :bid,
                        :name, :addr, 'Oakdale', 'IL', '60453', 'US',
                        :subject, :body, 0.08, 0.63, 1,
                        :staff)
            """), {
                "uid": uid, "ntype": ntype, "bid": random.choice(pnb_ids),
                "name": f"Patron {uid}", "addr": f"{random.randint(100,9999)} Library Lane",
                "subject": f"{ntype.replace('_', ' ').title()} Notice",
                "body": f"<p>Dear Patron, this is your {ntype.lower().replace('_', ' ')} notice from L30 Library.</p>",
                "staff": random.choice(staff_ids),
            })
            count += 1
        print(f"    Created {count} print notices")
        await session.flush()

    r = await session.execute(text("SELECT COUNT(*) FROM print_notice_history"))
    if r.scalar() == 0:
        print("  Seeding print_notice_history...")
        count = 0
        for _ in range(10):
            uid = random.choice(patron_ids) if patron_ids else random.choice(all_ids)
            ntype = random.choice(["overdue", "fine", "hold_ready", "welcome"])
            await session.execute(text("""
                INSERT INTO print_notice_history
                    (patron_id, patron_name, notice_type, subject,
                     mailing_address, final_status, mailed_at,
                     returned, total_cost)
                VALUES (:uid, :name, :ntype, :subject,
                        :addr, :status, :mailed,
                        :returned, :cost)
            """), {
                "uid": uid, "name": f"Patron {uid}", "ntype": ntype,
                "subject": f"{ntype.replace('_', ' ').title()} Notice",
                "addr": f"{random.randint(100,9999)} Library Lane, Oakdale IL 60453",
                "status": random.choice(["mailed", "delivered", "returned"]),
                "mailed": _past(random.randint(5, 60)),
                "returned": random.choice([True, False, False, False]),
                "cost": round(0.08 + 0.63, 2),
            })
            count += 1
        print(f"    Created {count} print notice history entries")
        await session.flush()

    r = await session.execute(text("SELECT COUNT(*) FROM print_notice_cost_config"))
    if r.scalar() == 0:
        print("  Seeding print_notice_cost_config...")
        await session.execute(text("""
            INSERT INTO print_notice_cost_config
                (cost_per_page, first_class_letter, first_class_large_envelope,
                 presort_standard, large_envelope_page_threshold,
                 is_active, effective_from, notes, created_by_id)
            VALUES (0.08, 0.63, 1.00,
                    0.42, 6,
                    true, :eff, 'Current USPS rates as of Jan 2026', :staff)
        """), {"eff": datetime(2026, 1, 1, tzinfo=utc), "staff": random.choice(staff_ids)})
        print("    Created 1 print notice cost config")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 14. WELCOME PACKETS + ASSEMBLIES + DISTRIBUTIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM welcome_packets"))
    if r.scalar() == 0:
        print("  Seeding welcome_packets...")
        packets = [
            ("New Patron Welcome Kit", "new_resident", "Everything a new library card holder needs to get started", "adults"),
            ("Family Welcome Packet", "family", "Resources for families with children, including reading lists and program info", "families"),
            ("Senior Services Guide", "senior", "Large print guide to library services, home delivery, and accessibility options", "seniors"),
            ("Teen Resource Pack", "youth", "Info on teen programs, study spaces, college prep resources, and volunteer hours", "teens"),
            ("Job Seeker Toolkit", "job_seeker", "Resume help, computer access info, job databases, and workforce development programs", "job_seekers"),
        ]
        for title, ptype, desc, audience in packets:
            await session.execute(text("""
                INSERT INTO welcome_packets
                    (title, packet_type, description,
                     languages_included, components,
                     print_available, digital_available,
                     target_audience, creation_date, is_active,
                     created_at, updated_at)
                VALUES (:title, :ptype, :desc,
                        '{"English","Spanish"}'::varchar[],
                        '{"welcome_letter","program_guide","library_map","bookmark"}'::varchar[],
                        true, true,
                        :audience, :cdate, true,
                        :created, :created)
            """), {
                "title": title, "ptype": ptype, "desc": desc,
                "audience": audience, "cdate": _past_date(120),
                "created": _past(120),
            })
        print(f"    Created {len(packets)} welcome packets")
        await session.flush()

    wp_r = await session.execute(text("SELECT id FROM welcome_packets ORDER BY id"))
    wp_ids = [r[0] for r in wp_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM welcome_packet_assemblies"))
    if r.scalar() == 0 and wp_ids:
        print("  Seeding welcome_packet_assemblies...")
        count = 0
        for pid in wp_ids:
            for _ in range(random.randint(1, 3)):
                await session.execute(text("""
                    INSERT INTO welcome_packet_assemblies
                        (packet_id, assembly_date, quantity_assembled,
                         assembled_by, volunteer_hours, notes,
                         created_at, updated_at)
                    VALUES (:pid, :adate, :qty,
                            :assembled_by, :hours, :notes,
                            :created, :created)
                """), {
                    "pid": pid, "adate": _past_date(random.randint(5, 90)),
                    "qty": random.randint(10, 50),
                    "assembled_by": random.choice(["Volunteer Team A", "Staff", "Teen Volunteers"]),
                    "hours": round(random.uniform(1.0, 4.0), 1),
                    "notes": "Assembly completed successfully",
                    "created": _past(random.randint(5, 90)),
                })
                count += 1
        print(f"    Created {count} welcome packet assemblies")
        await session.flush()

    r = await session.execute(text("SELECT COUNT(*) FROM welcome_packet_distributions"))
    if r.scalar() == 0 and wp_ids:
        print("  Seeding welcome_packet_distributions...")
        methods = ["in_person", "mail", "email"]
        count = 0
        for _ in range(15):
            uid = random.choice(patron_ids) if patron_ids else random.choice(all_ids)
            await session.execute(text("""
                INSERT INTO welcome_packet_distributions
                    (packet_id, patron_id, distribution_date, quantity_distributed,
                     distribution_method, recipient_name, notes,
                     created_at, updated_at)
                VALUES (:pid, :uid, :ddate, 1,
                        :method, :name, :notes,
                        :created, :created)
            """), {
                "pid": random.choice(wp_ids), "uid": uid,
                "ddate": _past_date(random.randint(1, 60)),
                "method": random.choice(methods),
                "name": f"Patron {uid}",
                "notes": "Distributed at registration desk",
                "created": _past(random.randint(1, 60)),
            })
            count += 1
        print(f"    Created {count} welcome packet distributions")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 15. ORIENTATION SCHEDULES + PRE-ARRIVAL CHECKLIST ITEMS
    # ════════════════════════════════════════════════════════════════
    ob_r = await session.execute(text("SELECT id FROM staff_onboarding ORDER BY id"))
    ob_ids = [r[0] for r in ob_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM orientation_schedules"))
    if r.scalar() == 0 and ob_ids:
        print("  Seeding orientation_schedules...")
        activities = [
            ("Welcome and Building Tour", "Tour of all library areas, staff introductions, and key locations", 60, "Main Branch"),
            ("ILS Training — Circulation Basics", "Introduction to the integrated library system for checkout/checkin", 120, "Training Room"),
            ("Safety and Emergency Procedures", "Fire exits, AED locations, emergency protocols, and lockdown procedures", 90, "Community Room A"),
            ("Customer Service Standards", "Library service philosophy, patron interaction guidelines, and de-escalation", 60, "Training Room"),
            ("IT Systems Overview", "Email, scheduling, internal tools, printing, and network access setup", 90, "Computer Lab"),
            ("Collections and Shelving", "Dewey Decimal system, shelving procedures, and collection areas tour", 60, "Main Stacks"),
        ]
        for ob_id in ob_ids:
            base_time = _past(random.randint(5, 30))
            for i, (title, desc, dur, loc) in enumerate(activities):
                sched = base_time + timedelta(hours=i * 3)
                await session.execute(text("""
                    INSERT INTO orientation_schedules
                        (onboarding_id, activity_title, description,
                         scheduled_time, duration_minutes, location,
                         facilitator_id, status)
                    VALUES (:ob_id, :title, :desc,
                            :sched, :dur, :loc,
                            :staff, :status)
                """), {
                    "ob_id": ob_id, "title": title, "desc": desc,
                    "sched": sched, "dur": dur, "loc": loc,
                    "staff": random.choice(staff_ids),
                    "status": random.choice(["completed", "completed", "pending"]),
                })
        print(f"    Created {len(ob_ids) * len(activities)} orientation schedule entries")
        await session.flush()

    r = await session.execute(text("SELECT COUNT(*) FROM pre_arrival_checklist_items"))
    if r.scalar() == 0 and ob_ids:
        print("  Seeding pre_arrival_checklist_items...")
        items = [
            ("Create network account", "Set up Active Directory account and email", "IT"),
            ("Order name badge", "Order personalized staff name badge", "HR"),
            ("Prepare desk/workstation", "Clean and set up workstation with supplies", "Facilities"),
            ("Add to staff directory", "Add name, photo, and contact info to website", "Communications"),
            ("Set up payroll", "Complete payroll enrollment and direct deposit", "HR"),
            ("Assign locker/mailbox", "Assign a staff locker and internal mailbox", "Facilities"),
            ("Schedule first-week meetings", "Book meetings with department heads and mentor", "Supervisor"),
            ("Prepare welcome packet", "Assemble staff welcome packet with handbook and materials", "HR"),
        ]
        for ob_id in ob_ids:
            for title, desc, category in items:
                assigned = random.choice(staff_ids)
                status = random.choice(["completed", "completed", "completed", "pending"])
                await session.execute(text("""
                    INSERT INTO pre_arrival_checklist_items
                        (onboarding_id, title, description, category,
                         assigned_to_id, status,
                         completed_at, completed_by_id)
                    VALUES (:ob_id, :title, :desc, :cat,
                            :assigned, :status,
                            :completed, :completed_by)
                """), {
                    "ob_id": ob_id, "title": title, "desc": desc, "cat": category,
                    "assigned": assigned, "status": status,
                    "completed": _past(random.randint(1, 15)) if status == "completed" else None,
                    "completed_by": assigned if status == "completed" else None,
                })
        print(f"    Created {len(ob_ids) * len(items)} pre-arrival checklist items")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 16. DONATION RECORDS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM donation_records"))
    if r.scalar() == 0:
        print("  Seeding donation_records...")
        donations = [
            ("Stevie Leigh", "stevie.leigh@email.com", False, True, "The Great Gatsby", "F. Scott Fitzgerald", "978-0743273565", "BOOK", 2, "Good", "accepted", 15),
            ("Anonymous", None, True, False, None, None, None, "BOOK", 25, "Mixed condition — box of paperbacks", "pending", None),
            ("Robert Foster", "rfoster@email.com", False, True, "National Geographic Collection", None, None, "MAGAZINE", 50, "1990-2000 complete years", "under_review", 100),
            ("David Park", "dpark@email.com", False, False, "The Hobbit — First Edition", "J.R.R. Tolkien", "978-0618260300", "BOOK", 1, "Excellent, dust jacket intact", "accepted", 75),
            ("Susan Miller", "smiller@email.com", False, True, "Assorted children's books", None, None, "BOOK", 15, "Gently used picture books", "accepted", 30),
            ("Anonymous", None, True, False, "DVD Collection — Marvel Films", None, None, "DVD", 12, "Good condition", "accepted", 60),
            ("James O'Connor", "joconnor@email.com", False, True, "Programming textbooks", None, None, "BOOK", 8, "Recent editions, clean", "accepted", 120),
            ("Patricia Hughes", "phughes@email.com", False, False, "Local history documents", None, None, "BOOK", 3, "Fragile, historical maps included", "under_review", None),
            ("Anonymous", None, True, False, None, None, None, "BOOK", 40, "Large box, unsorted", "pending", None),
            ("Tom Richardson", "trich@email.com", False, True, "Complete Harry Potter set", "J.K. Rowling", None, "BOOK", 7, "Hardcover, first US editions", "accepted", 85),
            ("Angela Brooks", "abrooks@email.com", False, False, "Audiobook CDs", None, None, "AUDIOBOOK", 20, "Various titles, good condition", "accepted", 60),
            ("Maria Santos", "msantos@email.com", False, True, "Spanish language children's books", None, None, "BOOK", 10, "New condition", "accepted", 50),
            ("Anonymous", None, True, False, "Graphic novels — manga", None, None, "BOOK", 30, "Mixed condition", "declined", None),
            ("Chris Taylor", "ctaylor@email.com", False, False, "Encyclopedia Britannica 2010", None, None, "BOOK", 32, "Complete set, minor shelf wear", "declined", 20),
            ("Linda Washington", "lwash@email.com", False, True, "Knitting pattern books", None, None, "BOOK", 5, "Like new", "accepted", 25),
            ("Anonymous", None, True, False, None, None, None, "DVD", 8, "Scratched discs", "declined", None),
            ("Kevin Nguyen", "knguyen@email.com", False, True, "Vietnamese language materials", None, None, "BOOK", 12, "New, imported", "accepted", 90),
            ("Sarah Kim", "skim@email.com", False, False, "College textbooks — biology", None, None, "BOOK", 4, "Current edition, clean", "under_review", 80),
        ]
        for (name, email, anon, receipt, title, author, isbn, mtype,
             qty, condition, status, value) in donations:
            await session.execute(text("""
                INSERT INTO donation_records
                    (donor_name, donor_email, is_anonymous, tax_receipt_requested,
                     tax_receipt_sent, title, author, isbn, material_type,
                     quantity, condition_notes, estimated_value,
                     status, received_date, received_by_id,
                     created_at, updated_at)
                VALUES (:name, :email, :anon, :receipt,
                        :sent, :title, :author, :isbn, :mtype,
                        :qty, :condition, :value,
                        :status, :rdate, :staff,
                        :created, :created)
            """), {
                "name": name, "email": email, "anon": anon, "receipt": receipt,
                "sent": receipt and status == "accepted",
                "title": title, "author": author, "isbn": isbn, "mtype": mtype,
                "qty": qty, "condition": condition, "value": value,
                "status": status, "rdate": _past_date(random.randint(1, 90)),
                "staff": random.choice(staff_ids), "created": _past(random.randint(1, 90)),
            })
        print(f"    Created {len(donations)} donation records")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 17. BUDGET ITEMS + BUDGET ALLOCATIONS + BUDGET TRANSACTIONS
    # ════════════════════════════════════════════════════════════════
    sb_r = await session.execute(text("SELECT id FROM strategic_budgets ORDER BY id"))
    sb_ids = [r[0] for r in sb_r.fetchall()]

    si_r = await session.execute(text("SELECT id FROM strategic_initiatives ORDER BY id"))
    si_ids = [r[0] for r in si_r.fetchall()]

    if not sb_ids:
        print("  Skipping budget tables — no strategic_budgets exist")
    else:
        r = await session.execute(text("SELECT COUNT(*) FROM budget_items"))
        if r.scalar() == 0:
            print("  Seeding budget_items...")
            items = [
                ("Materials", "Adult Books", "Annual book acquisitions for adult collection", 45000, "5100"),
                ("Materials", "Children's Books", "Picture books, early readers, and middle grade", 25000, "5101"),
                ("Materials", "Digital Resources", "Ebooks, databases, and streaming services", 18000, "5102"),
                ("Technology", "Computer Equipment", "Public computer replacements and upgrades", 12000, "5200"),
                ("Technology", "Software Licenses", "ILS, productivity suite, and security software", 8500, "5201"),
                ("Programs", "Summer Reading", "Summer reading program materials, prizes, and performers", 6000, "5300"),
                ("Programs", "Adult Programming", "Author visits, workshops, and cultural events", 4000, "5301"),
                ("Facilities", "Maintenance", "Building repairs and routine maintenance", 15000, "5400"),
                ("Staff Development", "Training", "Conferences, webinars, and continuing education", 5000, "5500"),
                ("Marketing", "Outreach", "Flyers, social media ads, and community partnerships", 3000, "5600"),
            ]
            for category, subcat, desc, amount, code in items:
                spent = round(amount * random.uniform(0.2, 0.7), 2)
                await session.execute(text("""
                    INSERT INTO budget_items
                        (budget_id, category, subcategory, description,
                         budgeted_amount, allocated_amount, spent_amount, remaining_amount,
                         account_code, department)
                    VALUES (:bid, :cat, :subcat, :desc,
                            :budgeted, :allocated, :spent, :remaining,
                            :code, :dept)
                """), {
                    "bid": sb_ids[0], "cat": category, "subcat": subcat, "desc": desc,
                    "budgeted": amount, "allocated": round(amount * 0.9, 2),
                    "spent": spent, "remaining": round(amount - spent, 2),
                    "code": code, "dept": category,
                })
            print(f"    Created {len(items)} budget items")
            await session.flush()

        r = await session.execute(text("SELECT COUNT(*) FROM budget_allocations"))
        if r.scalar() == 0:
            print("  Seeding budget_allocations...")
            allocs = [
                ("Q1 Materials Budget Release", 25000, "First quarter allocation for book and media purchases"),
                ("Summer Program Funding", 6000, "Full allocation for Summer Reading 2026"),
                ("Technology Refresh Fund", 12000, "Annual computer replacement and upgrade budget"),
                ("Staff Development Q1-Q2", 2500, "First half training and conference budget"),
                ("Emergency Maintenance Reserve", 5000, "Set aside for unexpected facility repairs"),
            ]
            for desc, amount, purpose in allocs:
                await session.execute(text("""
                    INSERT INTO budget_allocations
                        (budget_id, description, amount, allocation_date,
                         purpose, department, authorized_by_id)
                    VALUES (:bid, :desc, :amount, :adate,
                            :purpose, :dept, :staff)
                """), {
                    "bid": sb_ids[0], "desc": desc, "amount": amount,
                    "adate": _past(random.randint(10, 60)),
                    "purpose": purpose, "dept": "General",
                    "staff": random.choice(staff_ids),
                })
            print(f"    Created {len(allocs)} budget allocations")
            await session.flush()

        r = await session.execute(text("SELECT COUNT(*) FROM budget_transactions"))
        if r.scalar() == 0:
            print("  Seeding budget_transactions...")
            txns = [
                ("expense", "Baker & Taylor book order — January", 3250.00, "Materials", "INV-2026-0142", "Baker & Taylor"),
                ("expense", "Summer Reading prizes — Amazon", 450.00, "Programs", "AMZ-98765", "Amazon"),
                ("expense", "HVAC repair — main branch", 2800.00, "Facilities", "INV-HVAC-001", "Cool Air Services"),
                ("expense", "ALA Annual Conference registration x2", 890.00, "Staff Development", "ALA-2026-REG", "ALA"),
                ("revenue", "Friends of the Library donation", 5000.00, "Revenue", None, "Friends of L30"),
                ("expense", "Dell computer purchase x4", 3200.00, "Technology", "DELL-PO-4421", "Dell Technologies"),
                ("revenue", "State library grant — technology", 8000.00, "Revenue", "GRANT-IL-2026", "IL State Library"),
                ("expense", "Printing — monthly flyers and bookmarks", 185.00, "Marketing", "INV-PRINT-MAR", "Quick Print Co."),
            ]
            for ttype, desc, amount, category, inv, vendor in txns:
                await session.execute(text("""
                    INSERT INTO budget_transactions
                        (budget_id, transaction_type, description, amount,
                         transaction_date, category, invoice_number, vendor,
                         approved_by_id)
                    VALUES (:bid, :ttype, :desc, :amount,
                            :tdate, :cat, :inv, :vendor,
                            :staff)
                """), {
                    "bid": sb_ids[0], "ttype": ttype, "desc": desc, "amount": amount,
                    "tdate": _past(random.randint(1, 60)),
                    "cat": category, "inv": inv, "vendor": vendor,
                    "staff": random.choice(staff_ids),
                })
            print(f"    Created {len(txns)} budget transactions")
            await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 18. FOUND ITEMS + STORAGE LOCATIONS + PHOTOS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM found_item_storage_locations"))
    if r.scalar() == 0:
        print("  Seeding found_item_storage_locations...")
        locations = [
            ("Front Desk Drawer", "FD-01", "Behind circulation desk, left drawer", "Main Branch", 20, False, False),
            ("Lost & Found Bin", "LF-01", "Large bin in staff workroom", "Main Branch", 50, False, False),
            ("Secure Cabinet", "SEC-01", "Locked cabinet in director office for valuables", "Main Branch", 10, True, True),
            ("Children's Desk Basket", "CD-01", "Small basket at children's service desk", "Main Branch", 15, False, False),
            ("Elmdale Branch L&F", "NB-LF-01", "Lost and found shelf in break room", "Elmdale Branch", 30, False, False),
        ]
        for name, code, desc, branch, max_items, secure, restricted in locations:
            await session.execute(text("""
                INSERT INTO found_item_storage_locations
                    (location_name, location_code, description, branch,
                     max_items, current_item_count, is_secure_storage,
                     requires_verification, access_restricted, is_active)
                VALUES (:name, :code, :desc, :branch,
                        :max, 0, :secure,
                        :verify, :restricted, true)
            """), {
                "name": name, "code": code, "desc": desc, "branch": branch,
                "max": max_items, "secure": secure,
                "verify": secure, "restricted": restricted,
            })
        print(f"    Created {len(locations)} found item storage locations")
        await session.flush()

    fsl_r = await session.execute(text("SELECT id FROM found_item_storage_locations ORDER BY id"))
    fsl_ids = [r[0] for r in fsl_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM found_items"))
    if r.scalar() == 0 and fsl_ids:
        print("  Seeding found_items...")
        items = [
            ("Blue water bottle — Hydro Flask", "water_bottle", "Blue", "Hydro Flask", None, "Good", "Children's Reading Area", 30),
            ("Black reading glasses", "glasses", "Black", None, None, "Good", "Reference Desk", 30),
            ("Red knit scarf", "clothing", "Red", None, None, "Good", "Coat hooks near entrance", 60),
            ("iPhone in clear case", "electronics", "Silver", "Apple", None, "Good", "Computer Lab — Station 5", 30),
            ("Car keys with Toyota fob", "keys", "Silver", "Toyota", None, "Good", "Main floor study table", 30),
            ("Children's lunchbox — dinosaur print", "bag", "Green", None, None, "Good", "Children's storytime area", 30),
            ("Umbrella — black folding", "umbrella", "Black", None, None, "Fair", "Entryway umbrella stand", 60),
            ("USB flash drive — 32GB SanDisk", "electronics", "Black", "SanDisk", None, "Good", "Computer Lab — Station 12", 30),
            ("Stuffed animal — teddy bear", "toy", "Brown", None, None, "Good", "Picture book corner", 60),
            ("Prescription medication bottle", "medical", None, None, None, "Good", "Restroom counter", 14),
            ("Wallet — brown leather", "wallet", "Brown", None, None, "Good", "Self-checkout area", 30),
            ("Homework folder — 5th grade math", "documents", "Yellow", None, None, "Good", "Young adult section table", 14),
        ]
        fi_ids = []
        for desc, cat, color, brand, size, cond, location, retention in items:
            found_date = _past(random.randint(1, 45))
            r2 = await session.execute(text("""
                INSERT INTO found_items
                    (description, category, color, brand_or_label,
                     condition, location_found, date_found,
                     storage_location_id, secure_storage_flag, status,
                     retention_period_days, retention_end_date,
                     found_by_id, logged_by_id)
                VALUES (:desc, :cat, :color, :brand,
                        :cond, :loc, :found,
                        :slid, :secure, 'stored',
                        :retention, :ret_end,
                        :found_by, :logged_by)
                RETURNING id
            """), {
                "desc": desc, "cat": cat, "color": color, "brand": brand,
                "cond": cond, "loc": location, "found": found_date,
                "slid": random.choice(fsl_ids),
                "secure": cat in ("electronics", "wallet", "medical", "keys"),
                "retention": retention,
                "ret_end": found_date + timedelta(days=retention),
                "found_by": random.choice(staff_ids),
                "logged_by": random.choice(staff_ids),
            })
            fi_ids.append(r2.scalar())

        # Update storage counts
        for slid in fsl_ids:
            await session.execute(text("""
                UPDATE found_item_storage_locations SET current_item_count =
                    (SELECT COUNT(*) FROM found_items WHERE storage_location_id = :slid AND status = 'stored')
                WHERE id = :slid
            """), {"slid": slid})

        print(f"    Created {len(items)} found items")
        await session.flush()

    fi_r = await session.execute(text("SELECT id FROM found_items ORDER BY id"))
    found_ids = [r[0] for r in fi_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM found_item_photos"))
    if r.scalar() == 0 and found_ids:
        print("  Seeding found_item_photos...")
        count = 0
        for fid in found_ids[:8]:
            await session.execute(text("""
                INSERT INTO found_item_photos
                    (found_item_id, photo_url, photo_key,
                     upload_timestamp, is_primary, uploaded_by_id)
                VALUES (:fid, :url, :key,
                        :uploaded, true, :staff)
            """), {
                "fid": fid,
                "url": f"/uploads/found_items/{fid}_main.jpg",
                "key": f"found_items/{fid}_main.jpg",
                "uploaded": _past(random.randint(1, 30)),
                "staff": random.choice(staff_ids),
            })
            count += 1
        print(f"    Created {count} found item photos")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 19. WORKFLOWS + WORKFLOW STEPS + WORKFLOW EXECUTIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM workflows"))
    if r.scalar() == 0:
        print("  Seeding workflows...")
        wf_data = [
            ("New Patron Welcome", "Sends welcome email and schedules orientation for new patron accounts", "event", True, True),
            ("Overdue Notice Escalation", "Escalates overdue items through email, SMS, then print notice", "schedule", True, False),
            ("Hold Expiration Cleanup", "Cancels expired holds and notifies next patron in queue", "schedule", True, False),
            ("Lost Item Processing", "Flags account, sends bill, and updates item status for lost items", "event", True, False),
            ("Staff Onboarding Workflow", "Triggers IT setup, badge creation, and orientation scheduling", "manual", False, True),
        ]
        wf_ids_created = []
        for name, desc, trigger, active, is_template in wf_data:
            r2 = await session.execute(text("""
                INSERT INTO workflows
                    (name, description, created_by_id, trigger,
                     active, is_template, run_count,
                     created_at, updated_at)
                VALUES (:name, :desc, :staff, :trigger,
                        :active, :template, :runs,
                        :created, :created)
                RETURNING id
            """), {
                "name": name, "desc": desc, "staff": random.choice(staff_ids),
                "trigger": trigger, "active": active, "template": is_template,
                "runs": random.randint(0, 50) if active else 0,
                "created": _past(random.randint(30, 180)),
            })
            wf_ids_created.append(r2.scalar())
        print(f"    Created {len(wf_data)} workflows")
        await session.flush()

    wf_r = await session.execute(text("SELECT id FROM workflows ORDER BY id"))
    wf_ids = [r[0] for r in wf_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM workflow_steps"))
    if r.scalar() == 0 and wf_ids:
        print("  Seeding workflow_steps...")
        # Steps for first workflow (New Patron Welcome)
        steps_by_wf = {
            0: [
                (1, "Send Welcome Email", "action", "send_email"),
                (2, "Wait 3 days", "delay", None),
                (3, "Check orientation scheduled", "condition", None),
                (4, "Send reminder if no orientation", "action", "send_email"),
            ],
            1: [
                (1, "Send overdue email", "action", "send_email"),
                (2, "Wait 7 days", "delay", None),
                (3, "Send SMS if still overdue", "action", "send_sms"),
                (4, "Wait 14 days", "delay", None),
                (5, "Generate print notice", "action", "generate_report"),
            ],
            2: [
                (1, "Check hold expiration", "condition", None),
                (2, "Cancel expired hold", "action", "cancel_hold"),
                (3, "Notify next patron", "notification", "send_email"),
            ],
        }
        count = 0
        for wf_idx, steps in steps_by_wf.items():
            if wf_idx < len(wf_ids):
                for order, name, stype, atype in steps:
                    await session.execute(text("""
                        INSERT INTO workflow_steps
                            (workflow_id, "order", name, step_type, action_type,
                             delay_duration, delay_unit,
                             created_at, updated_at)
                        VALUES (:wfid, :ord, :name, :stype, :atype,
                                :delay_dur, :delay_unit,
                                :created, :created)
                    """), {
                        "wfid": wf_ids[wf_idx], "ord": order, "name": name,
                        "stype": stype, "atype": atype,
                        "delay_dur": 3 if stype == "delay" and "3" in name else (7 if stype == "delay" and "7" in name else (14 if stype == "delay" else None)),
                        "delay_unit": "days" if stype == "delay" else None,
                        "created": _past(random.randint(30, 180)),
                    })
                    count += 1
        print(f"    Created {count} workflow steps")
        await session.flush()

    r = await session.execute(text("SELECT COUNT(*) FROM workflow_executions"))
    if r.scalar() == 0 and wf_ids:
        print("  Seeding workflow_executions...")
        count = 0
        for wfid in wf_ids[:3]:
            for _ in range(random.randint(2, 5)):
                triggered = _past(random.randint(1, 30))
                status = random.choice(["completed", "completed", "completed", "failed"])
                await session.execute(text("""
                    INSERT INTO workflow_executions
                        (workflow_id, triggered_by_id, triggered_at,
                         completed_at, status, current_step)
                    VALUES (:wfid, :staff, :triggered,
                            :completed, :status, :step)
                """), {
                    "wfid": wfid, "staff": random.choice(staff_ids),
                    "triggered": triggered,
                    "completed": triggered + timedelta(hours=random.randint(1, 48)) if status == "completed" else None,
                    "status": status, "step": random.randint(1, 4),
                })
                count += 1
        print(f"    Created {count} workflow executions")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 20. NOTE TEMPLATES + NOTE AUDITS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM note_templates"))
    if r.scalar() == 0:
        print("  Seeding note_templates...")
        templates = [
            ("Patron Complaint", "Template for recording patron complaints", "Complaint received on {date} regarding: {issue}. Staff response: {response}. Follow-up required: {followup}.", "general", "normal"),
            ("Accommodation Request", "For tracking accessibility accommodation requests", "Patron requests accommodation: {accommodation}. Approved by: {approver}. Implementation date: {date}. Notes: {notes}.", "accommodation_needs", "high"),
            ("Behavioral Incident", "For documenting behavioral incidents", "Incident on {date} at {time} in {location}. Description: {description}. Staff involved: {staff}. Action taken: {action}.", "incident", "urgent"),
            ("Phone Follow-Up", "For phone call follow-ups with patrons", "Called patron on {date} regarding: {reason}. Outcome: {outcome}. Next steps: {next}.", "follow_up", "low"),
            ("Reading Preference", "For noting patron reading preferences", "Patron enjoys: {genres}. Favorite authors: {authors}. Avoids: {avoids}. Last recommendation given: {rec}.", "patron_preference", "low"),
            ("General Note", "Catch-all template for miscellaneous notes", "Note: {content}. Added by: {staff} on {date}.", "general", "normal"),
        ]
        for title, desc, content, category, priority in templates:
            await session.execute(text("""
                INSERT INTO note_templates
                    (title, description, content_template, category, priority,
                     usage_count, is_active, created_by_id, created_at)
                VALUES (:title, :desc, :content, :cat, :priority,
                        :usage, true, :staff, :created)
            """), {
                "title": title, "desc": desc, "content": content,
                "cat": category, "priority": priority,
                "usage": random.randint(0, 30),
                "staff": random.choice(staff_ids),
                "created": _past(random.randint(30, 180)),
            })
        print(f"    Created {len(templates)} note templates")
        await session.flush()

    pn_r = await session.execute(text("SELECT id FROM patron_notes ORDER BY id"))
    pn_ids = [r[0] for r in pn_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM note_audits"))
    if r.scalar() == 0 and pn_ids:
        print("  Seeding note_audits...")
        actions = ["created", "updated", "updated", "updated"]
        count = 0
        for nid in pn_ids[:10]:
            action = random.choice(actions)
            await session.execute(text("""
                INSERT INTO note_audits
                    (note_id, action, changed_by_id,
                     previous_content, new_content, change_reason)
                VALUES (:nid, :action, :staff,
                        :prev, :new, :reason)
            """), {
                "nid": nid, "action": action, "staff": random.choice(staff_ids),
                "prev": "Previous note content" if action == "updated" else None,
                "new": "Updated note content with additional details",
                "reason": "Added follow-up information" if action == "updated" else "Initial creation",
            })
            count += 1
        print(f"    Created {count} note audits")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 21. SEASONAL FAQS + POPULAR BOOK CLUB PICKS
    # ════════════════════════════════════════════════════════════════
    ke_r = await session.execute(text("SELECT id FROM knowledge_entries ORDER BY id"))
    ke_ids = [r[0] for r in ke_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM seasonal_faqs"))
    if r.scalar() == 0 and ke_ids:
        print("  Seeding seasonal_faqs...")
        faqs = [
            ("summer", "06-01", "08-31", 1, "Summer reading enrollment starts June 1st"),
            ("summer", "06-01", "08-31", 2, "Extended hours during summer months"),
            ("winter", "12-01", "02-28", 1, "Holiday closures and adjusted hours"),
            ("winter", "12-01", "02-28", 2, "Winter reading challenge registration open"),
            ("spring", "03-01", "05-31", 1, "Tax preparation help available through April"),
            ("spring", "03-01", "05-31", 2, "Garden seed library opens in March"),
            ("fall", "09-01", "11-30", 1, "Back to school resources and homework help"),
            ("fall", "09-01", "11-30", 2, "Banned Books Week celebration in September"),
        ]
        for season, start, end, priority, note in faqs:
            await session.execute(text("""
                INSERT INTO seasonal_faqs
                    (knowledge_entry_id, season, start_date, end_date,
                     is_active, priority, seasonal_note, created_by_id)
                VALUES (:keid, :season, :start, :end,
                        true, :priority, :note, :staff)
            """), {
                "keid": random.choice(ke_ids), "season": season,
                "start": start, "end": end,
                "priority": priority, "note": note,
                "staff": random.choice(staff_ids),
            })
        print(f"    Created {len(faqs)} seasonal FAQs")
        await session.flush()

    r = await session.execute(text("SELECT COUNT(*) FROM popular_book_club_picks"))
    if r.scalar() == 0 and catalog_ids:
        print("  Seeding popular_book_club_picks...")
        count = 0
        used_cids = set()
        for _ in range(10):
            cid = random.choice(catalog_ids)
            if cid in used_cids:
                continue
            used_cids.add(cid)
            await session.execute(text("""
                INSERT INTO popular_book_club_picks
                    (catalog_item_id, total_discussions, total_kits,
                     average_rating, is_featured, featured_at,
                     first_discussed_at, last_discussed_at)
                VALUES (:cid, :discussions, :kits,
                        :rating, :featured, :feat_at,
                        :first, :last)
            """), {
                "cid": cid, "discussions": random.randint(1, 8),
                "kits": random.randint(1, 5),
                "rating": random.randint(3, 5),
                "featured": random.choice([True, False]),
                "feat_at": _past(random.randint(1, 60)),
                "first": _past(random.randint(90, 365)),
                "last": _past(random.randint(1, 30)),
            })
            count += 1
        print(f"    Created {count} popular book club picks")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 23. VIDEO TUTORIALS + DISCUSSION GUIDES + MULTILINGUAL RESOURCES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM video_tutorials"))
    if r.scalar() == 0:
        print("  Seeding video_tutorials...")
        tutorials = [
            ("How to Place a Hold Online", "Step-by-step guide to placing holds through our catalog", "catalog", "https://videos.l30library.org/holds-tutorial.mp4", 185),
            ("Using the Self-Checkout Kiosk", "Walk-through of the self-checkout process", "circulation", "https://videos.l30library.org/self-checkout.mp4", 120),
            ("Downloading Ebooks to Your Device", "How to borrow and download ebooks using our digital catalog", "digital", "https://videos.l30library.org/ebook-download.mp4", 240),
            ("Navigating the Library Database Collection", "Tour of our research databases and how to access them", "research", "https://videos.l30library.org/databases-tour.mp4", 310),
            ("Setting Up Your Library Account", "Create and manage your online library account", "account", "https://videos.l30library.org/account-setup.mp4", 150),
            ("3D Printer Basics in the Makerspace", "Introduction to 3D printing for beginners", "makerspace", "https://videos.l30library.org/3d-printing.mp4", 420),
        ]
        for title, desc, category, url, duration in tutorials:
            await session.execute(text("""
                INSERT INTO video_tutorials
                    (title, description, category, video_url,
                     duration_seconds, is_published, created_by_id,
                     view_count, created_at, updated_at)
                VALUES (:title, :desc, :cat, :url,
                        :dur, true, :staff,
                        :views, :created, :created)
            """), {
                "title": title, "desc": desc, "cat": category, "url": url,
                "dur": duration, "staff": random.choice(staff_ids),
                "views": random.randint(10, 500),
                "created": _past(random.randint(30, 180)),
            })
        print(f"    Created {len(tutorials)} video tutorials")
        await session.flush()

    bcm_r = await session.execute(text("SELECT id FROM book_club_meetings ORDER BY id"))
    bcm_ids = [r[0] for r in bcm_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM discussion_guides"))
    if r.scalar() == 0 and catalog_ids:
        print("  Seeding discussion_guides...")
        guides = [
            ("Discussion Guide: Monthly Pick", "application/pdf", "Stevie Leigh", True, 12),
            ("Reader's Questions: Last Month's Selection", "application/pdf", "David O'Brien", True, 10),
            ("Teen Book Club Discussion Sheet", "application/pdf", "Susan Park", True, 8),
            ("Advanced Readers Discussion Notes", "application/pdf", "Staff", False, 15),
            ("Community Read Discussion Points", "application/pdf", "Angela Brooks", True, 20),
        ]
        for title, mime, author, official, questions in guides:
            await session.execute(text("""
                INSERT INTO discussion_guides
                    (book_club_meeting_id, catalog_item_id, title,
                     file_url, file_size_bytes, mime_type,
                     author, version, is_official,
                     auto_generated_questions_count,
                     created_at, updated_at)
                VALUES (:bcm_id, :cid, :title,
                        :url, :size, :mime,
                        :author, 1, :official,
                        :questions,
                        :created, :created)
            """), {
                "bcm_id": random.choice(bcm_ids) if bcm_ids else None,
                "cid": random.choice(catalog_ids), "title": title,
                "url": f"/uploads/discussion_guides/{_tok()}.pdf",
                "size": random.randint(50000, 500000), "mime": mime,
                "author": author, "official": official,
                "questions": questions,
                "created": _past(random.randint(5, 90)),
            })
        print(f"    Created {len(guides)} discussion guides")
        await session.flush()

    r = await session.execute(text("SELECT COUNT(*) FROM multilingual_resources"))
    if r.scalar() == 0:
        print("  Seeding multilingual_resources...")
        resources = [
            ("Guia de la Biblioteca", "Complete library services guide in Spanish", "Spanish", "guide", None, "beginner", "978-0-00-000001-0"),
            ("Hoc Tieng Anh — English Basics", "Basic English learning workbook for Vietnamese speakers", "Vietnamese", "workbook", "English", "beginner", None),
            ("Biblioteka Poradnik", "Polish language library orientation materials", "Polish", "guide", None, "beginner", None),
            ("Arabic Storytime Collection", "Bilingual Arabic-English picture books for storytime", "Arabic", "book_collection", "English", "beginner", None),
            ("Mandarin Computer Class Materials", "Handouts for computer basics class in Mandarin", "Chinese", "handout", "English", "intermediate", None),
            ("Hindi Family Literacy Kit", "Family literacy activities in Hindi with English support", "Hindi", "kit", "English", "beginner", None),
            ("French Conversation Circle Materials", "Discussion prompts and vocabulary sheets for French circle", "French", "handout", None, "intermediate", None),
            ("Korean New Patron Guide", "Welcome packet translated to Korean", "Korean", "guide", None, "beginner", None),
        ]
        for title, desc, lang, rtype, orig_lang, level, isbn in resources:
            await session.execute(text("""
                INSERT INTO multilingual_resources
                    (title, description, language, resource_type,
                     original_language, proficiency_level,
                     subject_areas, isbn,
                     availability, community_request, is_active,
                     created_at, updated_at)
                VALUES (:title, :desc, :lang, :rtype,
                        :orig, :level,
                        '{"language_learning","library_services"}'::varchar[], :isbn,
                        'available', :community, true,
                        :created, :created)
            """), {
                "title": title, "desc": desc, "lang": lang, "rtype": rtype,
                "orig": orig_lang, "level": level, "isbn": isbn,
                "community": random.choice([True, False]),
                "created": _past(random.randint(30, 180)),
            })
        print(f"    Created {len(resources)} multilingual resources")
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # FIX SEQUENCES
    # ════════════════════════════════════════════════════════════════
    seq_tables = [
        "event_feedback", "event_flyers", "event_graphics",
        "event_marketing_campaigns", "campaign_recipients",
        "event_distributions", "event_registration_sources",
        "event_review_responses", "repeat_attendees", "shared_events",
        "social_media_configs", "social_sharing_config",
        "generated_marketing_content", "subscriber_interests",
        "notification_queue", "notification_history", "notification_metrics",
        "sms_templates", "sms_queue", "sms_delivery_log",
        "sms_cost_records", "sms_opt_outs",
        "email_unsubscribe_tokens",
        "print_notice_batches", "print_notices", "print_notice_history",
        "print_notice_cost_config",
        "welcome_packets", "welcome_packet_assemblies", "welcome_packet_distributions",
        "orientation_schedules", "pre_arrival_checklist_items",
        "donation_records",
        "budget_items", "budget_allocations", "budget_transactions",
        "found_item_storage_locations", "found_items", "found_item_photos",
        "workflows", "workflow_steps", "workflow_executions",
        "note_templates", "note_audits",
        "seasonal_faqs", "popular_book_club_picks",

        "video_tutorials", "discussion_guides", "multilingual_resources",
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
    print("  Events/misc batch seeding complete!")
    return True
