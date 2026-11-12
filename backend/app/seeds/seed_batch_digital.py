# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import random
import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

utc = timezone.utc


def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago)


def _past_date(days_ago: int) -> date:
    return (datetime.now(utc) - timedelta(days=days_ago)).date()


async def seed_batch_digital(session: AsyncSession) -> bool:

    # ── Grab reusable IDs ──────────────────────────────────────────
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] in ("patron", "child")]
    all_ids = [u[0] for u in users]

    items_r = await session.execute(text("SELECT id FROM catalog_items"))
    catalog_ids = [r[0] for r in items_r.fetchall()]

    ebook_r = await session.execute(text("SELECT id FROM indie_ebooks"))
    ebook_ids = [r[0] for r in ebook_r.fetchall()]

    copy_r = await session.execute(text("SELECT id, barcode FROM item_copies"))
    copies = copy_r.fetchall()
    copy_ids = [c[0] for c in copies]
    copy_barcodes = [c[1] for c in copies]

    work_r = await session.execute(text("SELECT id FROM bibframe_works"))
    work_ids = [r[0] for r in work_r.fetchall()]

    comp_r = await session.execute(text("SELECT id FROM computers"))
    computer_ids = [r[0] for r in comp_r.fetchall()]

    svc_r = await session.execute(text("SELECT id, service FROM streaming_service_configs"))
    svc_configs = svc_r.fetchall()
    svc_config_ids = [r[0] for r in svc_configs]

    branch_r = await session.execute(text("SELECT id, name FROM branches"))
    branches = branch_r.fetchall()
    branch_ids = [b[0] for b in branches]
    branch_names = [b[1] for b in branches]

    checkout_r = await session.execute(text("SELECT id FROM checkouts LIMIT 30"))
    checkout_ids = [r[0] for r in checkout_r.fetchall()]

    now = datetime.now(utc)

    # ════════════════════════════════════════════════════════════════
    # 1. DIGITAL ACCESS ORDERS & CARDS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM digital_access_orders"))
    if r.scalar() == 0 and ebook_ids and patron_ids:
        print("  Seeding digital_access_orders & digital_access_cards...")
        order_count = 0
        card_count = 0
        statuses = ["pending", "approved", "completed", "completed", "completed",
                     "completed", "completed", "failed"]
        for i in range(8):
            uid = random.choice(patron_ids)
            eid = random.choice(ebook_ids)
            status = statuses[i]
            order_num = f"DAO-2026-{1000 + i}"
            fee = 0.70
            author_share = 9.65
            library_share = 9.65
            approved_by = random.choice(staff_ids) if status in ("approved", "completed") else None
            approved_at = _past(random.randint(1, 60)) if approved_by else None
            created = _past(random.randint(1, 90))

            await session.execute(text("""
                INSERT INTO digital_access_orders
                    (order_number, user_id, ebook_id, amount, currency, status,
                     stripe_fee, author_share, library_share,
                     approved_by_id, approved_at, created_at, updated_at)
                VALUES (:order_num, :uid, :eid, 20.00, 'USD', :status,
                        :fee, :author_share, :library_share,
                        :approved_by, :approved_at, :created, :created)
                RETURNING id
            """), {
                "order_num": order_num, "uid": uid, "eid": eid,
                "status": status, "fee": fee,
                "author_share": author_share, "library_share": library_share,
                "approved_by": approved_by, "approved_at": approved_at,
                "created": created,
            })
            order_count += 1

        await session.commit()

        # Now create cards for completed orders
        ord_r = await session.execute(text(
            "SELECT id, user_id, ebook_id FROM digital_access_orders WHERE status = 'completed'"
        ))
        completed_orders = ord_r.fetchall()
        for oid, uid, eid in completed_orders:
            card_num = f"DAC-{secrets.token_hex(4).upper()}"
            card_status = random.choice(["active", "active", "active", "expired"])
            expires = now + timedelta(days=365) if card_status == "active" else _past(random.randint(1, 30))
            await session.execute(text("""
                INSERT INTO digital_access_cards
                    (card_number, order_id, user_id, ebook_id, status,
                     issued_at, expires_at, last_accessed_at, access_count, created_at)
                VALUES (:card_num, :oid, :uid, :eid, :status,
                        :issued, :expires, :last_access, :count, :created)
            """), {
                "card_num": card_num, "oid": oid, "uid": uid, "eid": eid,
                "status": card_status,
                "issued": _past(random.randint(5, 60)),
                "expires": expires,
                "last_access": _past(random.randint(0, 14)) if random.random() > 0.3 else None,
                "count": random.randint(1, 25),
                "created": _past(random.randint(5, 60)),
            })
            card_count += 1

        print(f"    Created {order_count} orders, {card_count} cards")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 2. DATABASE VENDORS, SUBSCRIPTIONS, USAGE STATS, RENEWAL NOTIFS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM database_vendors"))
    if r.scalar() == 0:
        print("  Seeding database_vendors & subscriptions...")
        vendors = [
            ("EBSCO Information Services", "EBSCO", "https://www.ebsco.com",
             "support@ebsco.com", "1-800-653-2726", "Jane Morrison", "jane.morrison@ebsco.com"),
            ("Gale, a Cengage Company", "Gale", "https://www.gale.com",
             "gale.sales@cengage.com", "1-800-877-4253", "Mark Chen", "mark.chen@cengage.com"),
            ("ProQuest / Clarivate", "ProQuest", "https://www.proquest.com",
             "support@proquest.com", "1-800-521-0600", "Sarah Williams", "sarah.w@proquest.com"),
            ("Ancestry / ProQuest", "Ancestry", "https://www.ancestrylibrary.com",
             "libraryedition@ancestry.com", "1-800-262-3787", "Lisa Park", "lisa.park@ancestry.com"),
            ("Consumer Reports", "ConsReports", "https://www.consumerreports.org",
             "library@consumerreports.org", "1-800-333-0663", "Amy Foster", "amy.f@cr.org"),
            ("Mango Languages", "Mango", "https://mangolanguages.com",
             "support@mangolanguages.com", "1-877-626-4615", "Carlos Ruiz", "carlos@mangolanguages.com"),
        ]
        vendor_ids = []
        for name, short, website, email, phone, rep_name, rep_email in vendors:
            vr = await session.execute(text("""
                INSERT INTO database_vendors
                    (name, short_name, website, support_email, support_phone,
                     account_rep_name, account_rep_email)
                VALUES (:name, :short, :website, :email, :phone, :rep_name, :rep_email)
                RETURNING id
            """), {
                "name": name, "short": short, "website": website,
                "email": email, "phone": phone, "rep_name": rep_name,
                "rep_email": rep_email,
            })
            vendor_ids.append(vr.scalar())

        print(f"    Created {len(vendors)} vendors")
        await session.commit()

        # Create subscriptions for each vendor
        print("  Seeding database_subscriptions...")
        sub_data = [
            ("Academic Search Complete", "general_reference", 0, "https://search.ebscohost.com", 4500.00),
            ("Gale OneFile", "general_reference", 1, "https://go.gale.com", 3200.00),
            ("ProQuest Central", "academic", 2, "https://search.proquest.com", 5800.00),
            ("Ancestry Library Edition", "genealogy", 3, "https://www.ancestrylibrary.com", 2800.00),
            ("Consumer Reports Online", "general_reference", 4, "https://www.consumerreports.org/library", 1200.00),
            ("Mango Languages", "language_learning", 5, "https://connect.mangolanguages.com", 3500.00),
        ]
        sub_ids = []
        for name, category, vid_idx, url, cost in sub_data:
            sr = await session.execute(text("""
                INSERT INTO database_subscriptions
                    (name, category, vendor_id, access_url, subscription_start,
                     subscription_end, status, annual_cost, is_active, created_by_id)
                VALUES (:name, :cat, :vid, :url, :start, :end, 'active',
                        :cost, true, :creator)
                RETURNING id
            """), {
                "name": name, "cat": category, "vid": vendor_ids[vid_idx],
                "url": url, "start": date(2026, 1, 1),
                "end": date(2026, 12, 31), "cost": cost,
                "creator": staff_ids[0],
            })
            sub_ids.append(sr.scalar())

        print(f"    Created {len(sub_data)} subscriptions")
        await session.commit()

        # Usage stats - monthly for last 3 months
        print("  Seeding database_usage_stats...")
        stat_count = 0
        for sid in sub_ids:
            for month_offset in range(3):
                m = now.month - month_offset
                y = now.year
                if m <= 0:
                    m += 12
                    y -= 1
                await session.execute(text("""
                    INSERT INTO database_usage_stats
                        (subscription_id, stat_year, stat_month,
                         total_item_requests, unique_item_requests,
                         searches_regular, total_sessions, unique_users,
                         onsite_sessions, offsite_sessions, data_source, imported_at)
                    VALUES (:sid, :year, :month,
                            :requests, :unique_req,
                            :searches, :sessions, :users,
                            :onsite, :offsite, 'counter_sushi', :imported)
                """), {
                    "sid": sid, "year": y, "month": m,
                    "requests": random.randint(100, 2000),
                    "unique_req": random.randint(50, 800),
                    "searches": random.randint(200, 5000),
                    "sessions": random.randint(50, 500),
                    "users": random.randint(20, 200),
                    "onsite": random.randint(10, 100),
                    "offsite": random.randint(30, 300),
                    "imported": _past(month_offset * 30),
                })
                stat_count += 1

        print(f"    Created {stat_count} usage stat records")
        await session.commit()

        # Renewal notifications
        print("  Seeding database_renewal_notifications...")
        notif_count = 0
        for sid in random.sample(sub_ids, min(4, len(sub_ids))):
            for ntype in ["60_day", "30_day"]:
                await session.execute(text("""
                    INSERT INTO database_renewal_notifications
                        (subscription_id, sent_at, notification_type, sent_to,
                         delivered, responded_at, response_action)
                    VALUES (:sid, :sent, :ntype, :email,
                            true, :responded, :action)
                """), {
                    "sid": sid, "sent": _past(random.randint(30, 90)),
                    "ntype": ntype, "email": "director@library.org",
                    "responded": _past(random.randint(1, 29)),
                    "action": "renewed",
                })
                notif_count += 1

        print(f"    Created {notif_count} renewal notifications")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 3. STREAMING CATALOG, CHECKOUTS, USAGE STATS, BUDGETS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM streaming_catalog_items"))
    if r.scalar() == 0 and svc_config_ids:
        print("  Seeding streaming_catalog_items...")
        streaming_items = [
            (svc_config_ids[0], "KNP-001", "13th", "Ava DuVernay", "An in-depth look at the prison system in the United States.", "documentary", 100, 2016),
            (svc_config_ids[0], "KNP-002", "RBG", "Betsy West", "The life and career of Supreme Court Justice Ruth Bader Ginsburg.", "documentary", 98, 2018),
            (svc_config_ids[0], "KNP-003", "Won't You Be My Neighbor?", "Morgan Neville", "A look at the life of Fred Rogers.", "documentary", 94, 2018),
            (svc_config_ids[0], "KNP-004", "I Am Not Your Negro", "Raoul Peck", "James Baldwin's unfinished manuscript about race in America.", "documentary", 93, 2016),
            (svc_config_ids[0], "KNP-005", "Paris Is Burning", "Jennie Livingston", "A chronicle of New York's drag ball culture.", "documentary", 78, 1990),
            (svc_config_ids[1], "PLC-001", "The Midnight Library", "Matt Haig", "A novel about infinite possibilities.", "ebook", None, 2020),
            (svc_config_ids[1], "PLC-002", "Project Hail Mary", "Andy Weir", "An astronaut wakes up alone on a ship.", "ebook", None, 2021),
            (svc_config_ids[1], "PLC-003", "Atomic Habits", "James Clear", "Tiny changes, remarkable results.", "audiobook", 330, 2018),
            (svc_config_ids[1], "PLC-004", "Where the Crawdads Sing", "Delia Owens", "A woman raised in the marshes becomes a suspect.", "audiobook", 720, 2018),
            (svc_config_ids[1], "PLC-005", "Klara and the Sun", "Kazuo Ishiguro", "An AI observes the human world.", "ebook", None, 2021),
        ]
        stream_item_ids = []
        for svc_id, ext_id, title, author, desc, ctype, dur, year in streaming_items:
            sr = await session.execute(text("""
                INSERT INTO streaming_catalog_items
                    (service_config_id, external_id, title, author, description,
                     content_type, duration_minutes, release_year,
                     is_available, last_synced_at, created_at, updated_at)
                VALUES (:svc, :ext, :title, :author, :desc,
                        :ctype, :dur, :year,
                        true, :synced, :created, :created)
                RETURNING id
            """), {
                "svc": svc_id, "ext": ext_id, "title": title, "author": author,
                "desc": desc, "ctype": ctype, "dur": dur, "year": year,
                "synced": _past(1), "created": _past(random.randint(30, 180)),
            })
            stream_item_ids.append(sr.scalar())

        print(f"    Created {len(streaming_items)} streaming catalog items")
        await session.commit()

        # Streaming checkouts
        print("  Seeding streaming_checkouts...")
        co_count = 0
        checkout_statuses = ["active", "expired", "returned", "returned", "expired"]
        for _ in range(15):
            item_idx = random.randrange(len(stream_item_ids))
            svc_id = streaming_items[item_idx][0]
            status = random.choice(checkout_statuses)
            checked_out = _past(random.randint(1, 90))
            expires = checked_out + timedelta(days=random.choice([3, 7, 14, 21]))
            returned = checked_out + timedelta(days=random.randint(1, 14)) if status == "returned" else None
            await session.execute(text("""
                INSERT INTO streaming_checkouts
                    (user_id, service_config_id, streaming_item_id,
                     status, checked_out_at, expires_at, returned_at,
                     cost, item_title, item_content_type, created_at, updated_at)
                VALUES (:uid, :svc, :item,
                        :status, :co_at, :exp, :ret,
                        :cost, :title, :ctype, :created, :created)
            """), {
                "uid": random.choice(patron_ids), "svc": svc_id,
                "item": stream_item_ids[item_idx],
                "status": status, "co_at": checked_out,
                "exp": expires, "ret": returned,
                "cost": round(random.uniform(1.0, 5.0), 2),
                "title": streaming_items[item_idx][2],
                "ctype": streaming_items[item_idx][5],
                "created": checked_out,
            })
            co_count += 1

        print(f"    Created {co_count} streaming checkouts")
        await session.commit()

        # Streaming usage stats
        print("  Seeding streaming_usage_stats...")
        sus_count = 0
        for svc_id in svc_config_ids:
            for days_ago in [7, 14, 21, 28]:
                stat_dt = _past(days_ago)
                await session.execute(text("""
                    INSERT INTO streaming_usage_stats
                        (service_config_id, stat_date,
                         total_checkouts, unique_patrons, total_cost)
                    VALUES (:svc, :dt, :co, :patrons, :cost)
                """), {
                    "svc": svc_id, "dt": stat_dt,
                    "co": random.randint(10, 80),
                    "patrons": random.randint(5, 40),
                    "cost": round(random.uniform(50.0, 300.0), 2),
                })
                sus_count += 1

        print(f"    Created {sus_count} streaming usage stat records")
        await session.commit()

        # Streaming budgets
        print("  Seeding streaming_budgets...")
        sb_count = 0
        for svc_id in svc_config_ids:
            await session.execute(text("""
                INSERT INTO streaming_budgets
                    (service_config_id, fiscal_year, fiscal_month,
                     allocated_amount, spent_amount,
                     max_checkouts, current_checkouts, created_at, updated_at)
                VALUES (:svc, 2026, NULL,
                        :alloc, :spent, :max_co, :cur_co, :created, :created)
            """), {
                "svc": svc_id, "alloc": round(random.uniform(3000, 8000), 2),
                "spent": round(random.uniform(500, 2500), 2),
                "max_co": random.choice([500, 1000, None]),
                "cur_co": random.randint(50, 300),
                "created": _past(90),
            })
            sb_count += 1

        print(f"    Created {sb_count} streaming budgets")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 4. COLLECTION ALERTS & RECOVERY PROJECTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM collection_alerts"))
    if r.scalar() == 0 and catalog_ids:
        print("  Seeding collection_alerts...")
        alert_data = [
            ("last_copy_checkout", "warning", "active", '{"available_copies": 1, "total_copies": 5}', "Main Stacks"),
            ("high_demand_hold", "critical", "active", '{"hold_count": 7, "available_copies": 1}', "New Arrivals"),
            ("non_circulating", "info", "active", '{"months_since_checkout": 18}', "Reference"),
            ("long_hold_queue", "warning", "dismissed", '{"pending_holds": 9, "available_copies": 2}', "Fiction"),
            ("low_inventory", "warning", "resolved", '{"available_copies": 0, "branch": "Elmdale"}', "Children's"),
        ]
        for atype, severity, status, context, location in alert_data:
            dismissed_at = _past(5) if status == "dismissed" else None
            resolved_at = _past(3) if status == "resolved" else None
            dismissed_by = random.choice(staff_ids) if status in ("dismissed", "resolved") else None
            await session.execute(text("""
                INSERT INTO collection_alerts
                    (catalog_item_id, alert_type, severity, status,
                     context_data, location, dismissed_at, resolved_at, dismissed_by_id)
                VALUES (:item, :atype, :severity, :status,
                        :ctx, :loc, :dismissed_at, :resolved_at, :dismissed_by)
            """), {
                "item": random.choice(catalog_ids), "atype": atype,
                "severity": severity, "status": status,
                "ctx": context, "loc": location,
                "dismissed_at": dismissed_at, "resolved_at": resolved_at,
                "dismissed_by": dismissed_by,
            })

        print(f"    Created {len(alert_data)} collection alerts")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM collection_recovery_projects"))
    if r.scalar() == 0:
        print("  Seeding collection_recovery_projects...")
        vr = await session.execute(text("SELECT id FROM vendors LIMIT 1"))
        vendor_row = vr.fetchone()
        vendor_id = vendor_row[0] if vendor_row else None

        projects = [
            ("Water Damage Recovery - Basement Flood",
             "Recovery of materials affected by basement flooding from burst pipe",
             "Water Damage", _past(60),
             '["Basement Storage", "Local History Room"]',
             250, 180, 150, 30),
            ("Mold Remediation - HVAC Failure",
             "Treatment of mold-affected materials after HVAC system failure during summer",
             "Mold", _past(120),
             '["Periodicals Room", "Staff Workroom"]',
             100, 95, 80, 15),
        ]
        for pname, desc, dtype, ddate, areas, est, assessed, salvaged, lost in projects:
            await session.execute(text("""
                INSERT INTO collection_recovery_projects
                    (project_name, project_description, disaster_type, disaster_date,
                     affected_areas, estimated_items_affected, total_items_assessed,
                     items_salvaged, items_lost, is_active, lead_staff_id,
                     estimated_cost, vendor_id, created_at, updated_at)
                VALUES (:name, :desc, :dtype, :ddate,
                        cast(:areas as json), :est, :assessed,
                        :salvaged, :lost, :active, :lead,
                        :cost, :vendor, :created, :created)
            """), {
                "name": pname, "desc": desc, "dtype": dtype, "ddate": ddate,
                "areas": areas, "est": est, "assessed": assessed,
                "salvaged": salvaged, "lost": lost,
                "active": pname.startswith("Water"),
                "lead": random.choice(staff_ids),
                "cost": random.uniform(5000, 25000),
                "vendor": vendor_id,
                "created": ddate,
            })

        print(f"    Created {len(projects)} recovery projects")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 5. WEEDING CANDIDATES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM weeding_candidates"))
    if r.scalar() == 0 and copy_ids:
        print("  Seeding weeding_candidates...")
        reasons = ["low_circulation", "poor_condition", "outdated", "duplicate",
                    "never_circulated", "damaged_beyond_repair", "superseded"]
        statuses = ["candidate", "candidate", "candidate", "under_review",
                     "approved", "rejected", "disposed"]
        crew_cats = ["000", "300", "500", "600", "fiction", "computing", "medical"]
        dispositions = ["donate_good_condition", "recycle_poor_condition",
                        "sell_popular_title", "discard", None]
        weed_count = 0
        used_copies = set()
        for i in range(min(15, len(copy_ids))):
            cid = copy_ids[i] if i < len(copy_ids) else random.choice(copy_ids)
            if cid in used_copies:
                continue
            used_copies.add(cid)
            status = random.choice(statuses)
            reason = random.choice(reasons)
            reviewed_by = random.choice(staff_ids) if status not in ("candidate",) else None
            reviewed_at = _past(random.randint(1, 30)) if reviewed_by else None
            approved_by = random.choice(staff_ids) if status in ("approved", "disposed") else None
            approved_at = _past(random.randint(1, 15)) if approved_by else None

            await session.execute(text("""
                INSERT INTO weeding_candidates
                    (item_copy_id, status, reason, reason_notes,
                     last_checkout_date, total_checkouts, years_since_acquisition,
                     condition_score, crew_category, crew_score,
                     auto_generated, disposition_recommendation,
                     reviewed_by_id, reviewed_at,
                     approved_by_id, approved_at,
                     created_by_id, created_at, updated_at)
                VALUES (:cid, :status, :reason, :notes,
                        :last_co, :total_co, :years,
                        :cond, :crew_cat, :crew_score,
                        :auto, :disp,
                        :reviewed_by, :reviewed_at,
                        :approved_by, :approved_at,
                        :created_by, :created, :created)
            """), {
                "cid": cid, "status": status, "reason": reason,
                "notes": f"Auto-flagged: {reason.replace('_', ' ')}",
                "last_co": _past_date(random.randint(180, 1200)) if reason != "never_circulated" else None,
                "total_co": random.randint(0, 5) if reason == "low_circulation" else random.randint(0, 20),
                "years": random.randint(3, 25),
                "cond": round(random.uniform(0.1, 0.9), 2),
                "crew_cat": random.choice(crew_cats),
                "crew_score": round(random.uniform(20, 95), 1),
                "auto": random.choice([True, True, False]),
                "disp": random.choice(dispositions),
                "reviewed_by": reviewed_by, "reviewed_at": reviewed_at,
                "approved_by": approved_by, "approved_at": approved_at,
                "created_by": random.choice(staff_ids),
                "created": _past(random.randint(5, 60)),
            })
            weed_count += 1

        print(f"    Created {weed_count} weeding candidates")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 6. SERIES MANAGEMENT
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM series_reading_order"))
    if r.scalar() == 0 and work_ids:
        print("  Seeding series_reading_order...")
        series_data = [
            ("Harry Potter", [
                (1.0, "Harry Potter and the Philosopher's Stone", 1997),
                (2.0, "Harry Potter and the Chamber of Secrets", 1998),
                (3.0, "Harry Potter and the Prisoner of Azkaban", 1999),
                (4.0, "Harry Potter and the Goblet of Fire", 2000),
                (5.0, "Harry Potter and the Order of the Phoenix", 2003),
                (6.0, "Harry Potter and the Half-Blood Prince", 2005),
                (7.0, "Harry Potter and the Deathly Hallows", 2007),
            ]),
            ("The Hunger Games", [
                (1.0, "The Hunger Games", 2008),
                (2.0, "Catching Fire", 2009),
                (3.0, "Mockingjay", 2010),
                (4.0, "The Ballad of Songbirds and Snakes", 2020),
                (5.0, "Sunrise on the Reaping", 2025),
            ]),
            ("A Court of Thorns and Roses", [
                (1.0, "A Court of Thorns and Roses", 2015),
                (2.0, "A Court of Mist and Fury", 2016),
                (3.0, "A Court of Wings and Ruin", 2017),
                (4.0, "A Court of Frost and Starlight", 2018),
                (5.0, "A Court of Silver Flames", 2021),
            ]),
            ("Dune", [
                (1.0, "Dune", 1965),
                (2.0, "Dune Messiah", 1969),
                (3.0, "Children of Dune", 1976),
                (4.0, "God Emperor of Dune", 1981),
            ]),
            ("Wayfarers", [
                (1.0, "The Long Way to a Small, Angry Planet", 2014),
                (2.0, "A Closed and Common Orbit", 2016),
                (3.0, "Record of a Spaceborn Few", 2018),
                (4.0, "The Galaxy, and the Ground Within", 2021),
            ]),
        ]
        sro_count = 0
        for series_title, books in series_data:
            for seq, book_title, pub_year in books:
                wid = random.choice(work_ids)
                await session.execute(text("""
                    INSERT INTO series_reading_order
                        (series_title, series_type, bibframe_work_id,
                         sequence_number, book_title, publication_year,
                         is_recommended_starting_point, verified,
                         created_by_id)
                    VALUES (:series, 'main_series', :wid,
                            :seq, :title, :year,
                            :start, :verified,
                            :creator)
                """), {
                    "series": series_title, "wid": wid,
                    "seq": seq, "title": book_title, "year": pub_year,
                    "start": seq == 1.0,
                    "verified": random.choice([True, True, False]),
                    "creator": random.choice(staff_ids),
                })
                sro_count += 1

        print(f"    Created {sro_count} series reading order entries")
        await session.commit()

        # Series completion
        print("  Seeding series_completion...")
        sc_count = 0
        used_combos = set()
        for uid in random.sample(patron_ids, min(len(patron_ids), 20)):
            for series_title, books in random.sample(series_data, random.randint(1, 3)):
                if (uid, series_title) in used_combos:
                    continue
                used_combos.add((uid, series_title))
                total = len(books)
                read_count = random.randint(1, total)
                await session.execute(text("""
                    INSERT INTO series_completion
                        (user_id, series_title, total_books_in_series,
                         books_read, books_available,
                         last_book_read_number, next_book_number,
                         last_book_read_title, next_book_title,
                         is_completed, is_following, preferred,
                         last_read_date, started_date)
                    VALUES (:uid, :series, :total,
                            :read, :avail,
                            :last_num, :next_num,
                            :last_title, :next_title,
                            :completed, :following, :preferred,
                            :last_read, :started)
                """), {
                    "uid": uid, "series": series_title, "total": total,
                    "read": read_count, "avail": total,
                    "last_num": float(read_count),
                    "next_num": float(read_count + 1) if read_count < total else None,
                    "last_title": books[min(read_count - 1, len(books) - 1)][1],
                    "next_title": books[read_count][1] if read_count < total else None,
                    "completed": read_count >= total,
                    "following": random.choice([True, True, False]),
                    "preferred": random.choice([True, False, False]),
                    "last_read": _past(random.randint(1, 180)),
                    "started": _past(random.randint(60, 365)),
                })
                sc_count += 1

        print(f"    Created {sc_count} series completion records")
        await session.commit()

        # Series popularity
        print("  Seeding series_popularity...")
        for series_title, books in series_data:
            await session.execute(text("""
                INSERT INTO series_popularity
                    (series_title, patron_followers, patron_completion_count,
                     average_rating, total_checkouts, unique_patrons_read,
                     is_trending, trend_score, last_updated)
                VALUES (:title, :followers, :completions,
                        :rating, :checkouts, :patrons,
                        :trending, :score, :updated)
            """), {
                "title": series_title,
                "followers": random.randint(10, 200),
                "completions": random.randint(5, 80),
                "rating": round(random.uniform(3.5, 5.0), 2),
                "checkouts": random.randint(50, 500),
                "patrons": random.randint(20, 150),
                "trending": random.choice([True, False]),
                "score": round(random.uniform(0.3, 0.95), 3),
                "updated": _past(random.randint(0, 7)),
            })

        print(f"    Created {len(series_data)} series popularity records")
        await session.commit()

        # Series recommendations
        print("  Seeding series_recommendations...")
        rec_reasons = ["similar_genre", "same_author", "reading_history",
                        "popularity", "editorial"]
        rec_count = 0
        for uid in random.sample(patron_ids, min(len(patron_ids), 15)):
            for series_title, _ in random.sample(series_data, random.randint(1, 2)):
                await session.execute(text("""
                    INSERT INTO series_recommendations
                        (user_id, series_title, first_book_bibframe_work_id,
                         reason, confidence_score,
                         viewed, clicked, created_at, updated_at)
                    VALUES (:uid, :series, :wid,
                            :reason, :conf,
                            :viewed, :clicked, :created, :created)
                """), {
                    "uid": uid, "series": series_title,
                    "wid": random.choice(work_ids),
                    "reason": random.choice(rec_reasons),
                    "conf": round(random.uniform(0.3, 0.95), 2),
                    "viewed": random.choice([True, False]),
                    "clicked": random.choice([True, False, False]),
                    "created": _past(random.randint(1, 60)),
                })
                rec_count += 1

        print(f"    Created {rec_count} series recommendations")
        await session.commit()

        # Series notification rules
        print("  Seeding series_notification_rules...")
        triggers = ["new_release", "next_available", "series_complete"]
        snr_count = 0
        used_rules = set()
        for uid in random.sample(patron_ids, min(len(patron_ids), 10)):
            for series_title, _ in random.sample(series_data, random.randint(1, 2)):
                trigger = random.choice(triggers)
                key = (uid, series_title, trigger)
                if key in used_rules:
                    continue
                used_rules.add(key)
                await session.execute(text("""
                    INSERT INTO series_notification_rules
                        (user_id, series_title, trigger_type,
                         is_active, notification_method, frequency,
                         notification_count, created_by_id)
                    VALUES (:uid, :series, :trigger,
                            true, :method, :freq,
                            :count, :creator)
                """), {
                    "uid": uid, "series": series_title, "trigger": trigger,
                    "method": random.choice(["email", "sms", "both"]),
                    "freq": random.choice(["immediate", "daily", "weekly"]),
                    "count": random.randint(0, 5),
                    "creator": uid,
                })
                snr_count += 1

        print(f"    Created {snr_count} series notification rules")
        await session.commit()

        # Series waitlist
        print("  Seeding series_waitlist...")
        sw_count = 0
        for uid in random.sample(patron_ids, min(len(patron_ids), 8)):
            series_title, books = random.choice(series_data)
            last_seq = max(b[0] for b in books)
            await session.execute(text("""
                INSERT INTO series_waitlist
                    (user_id, series_title, next_book_sequence,
                     next_book_title, status, position,
                     notification_method, reminder_frequency)
                VALUES (:uid, :series, :seq,
                        :title, 'active', :pos,
                        :method, 'weekly')
            """), {
                "uid": uid, "series": series_title,
                "seq": last_seq + 1.0,
                "title": f"{series_title} Book {int(last_seq) + 1}",
                "pos": sw_count + 1,
                "method": random.choice(["email", "sms"]),
            })
            sw_count += 1

        print(f"    Created {sw_count} series waitlist entries")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 7. NEW ARRIVAL ALERTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM new_arrival_alerts"))
    if r.scalar() == 0 and patron_ids:
        print("  Seeding new_arrival_alerts...")
        alert_specs = [
            (None, "mystery thriller", None, None),
            (None, "science fiction", None, None),
            (None, None, "Brandon Sanderson", None),
            (None, None, "Colleen Hoover", None),
            (None, None, None, "Harry Potter"),
            (None, "romance", None, None),
            (None, None, "Stephen King", None),
            (None, "children's picture books", None, None),
            (None, "graphic novels manga", None, None),
            (None, None, "James Patterson", None),
            (None, "nonfiction biography", None, None),
            (None, None, None, "Diary of a Wimpy Kid"),
            (None, "young adult fantasy", None, None),
            (None, None, "Emily Henry", None),
            (None, "true crime", None, None),
            (None, None, None, "A Court of Thorns and Roses"),
            (None, "historical fiction", None, None),
            (None, None, "Rick Riordan", None),
            (None, "cookbooks baking", None, None),
            (None, None, "Tana French", None),
        ]
        na_count = 0
        for cat_id, query, author, series in alert_specs:
            uid = random.choice(patron_ids)
            token = secrets.token_urlsafe(32)
            await session.execute(text("""
                INSERT INTO new_arrival_alerts
                    (user_id, category_id, search_query, author_name, series_name,
                     delivery_method, frequency, is_active, unsubscribe_token)
                VALUES (:uid, :cat, :query, :author, :series,
                        :method, :freq, true, :token)
            """), {
                "uid": uid, "cat": cat_id, "query": query,
                "author": author, "series": series,
                "method": random.choice(["email", "email", "sms", "both"]),
                "freq": random.choice(["weekly", "biweekly", "monthly"]),
                "token": token,
            })
            na_count += 1

        print(f"    Created {na_count} new arrival alerts")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 8. CATALOG IMAGES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM catalog_images"))
    if r.scalar() == 0 and catalog_ids:
        print("  Seeding catalog_images...")
        img_count = 0
        sample_items = random.sample(catalog_ids, min(15, len(catalog_ids)))
        for i, cid in enumerate(sample_items):
            key = f"covers/{cid}/{secrets.token_hex(6)}.jpg"
            await session.execute(text("""
                INSERT INTO catalog_images
                    (catalog_item_id, image_url, image_key,
                     is_primary, caption, display_order,
                     file_size, content_type, uploaded_at, uploaded_by_id)
                VALUES (:cid, :url, :key,
                        :primary, :caption, :order,
                        :size, 'image/jpeg', :uploaded, :uploader)
            """), {
                "cid": cid,
                "url": f"https://cdn.library.org/{key}",
                "key": key,
                "primary": i % 3 == 0,
                "caption": random.choice(["Front cover", "Back cover", "Spine", "Interior page", None]),
                "order": i % 3,
                "size": random.randint(50000, 500000),
                "uploaded": _past(random.randint(1, 180)),
                "uploader": random.choice(staff_ids),
            })
            img_count += 1

        print(f"    Created {img_count} catalog images")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 9. COMPUTER SESSIONS & USAGE STATISTICS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM computer_sessions"))
    if r.scalar() == 0 and computer_ids and patron_ids:
        print("  Seeding computer_sessions...")
        session_statuses = ["active", "ended", "ended", "ended", "timed_out",
                            "ended", "ended", "ended", "ended", "terminated"]
        cs_count = 0
        for i in range(30):
            status = random.choice(session_statuses)
            started = _past(random.randint(0, 60))
            ended = started + timedelta(minutes=random.randint(15, 120)) if status != "active" else None
            comp_id = random.choice(computer_ids)
            is_minor = random.random() < 0.15
            token = f"CS-{secrets.token_hex(8)}"
            await session.execute(text("""
                INSERT INTO computer_sessions
                    (patron_id, session_token, status,
                     is_minor, patron_type,
                     workstation_id, branch_location,
                     content_filtering_enabled, minor_filtering_enabled,
                     started_at, ended_at,
                     max_duration_minutes, extension_count,
                     ip_address, computer_id,
                     is_active, auto_logout_executed,
                     was_extended, user_initiated_logout, print_jobs_count,
                     created_at, updated_at)
                VALUES (:patron, :token, :status,
                        :minor, :ptype,
                        :ws, :branch,
                        true, :minor_filter,
                        :started, :ended,
                        120, :ext_count,
                        :ip, :comp_id,
                        :is_active, false,
                        :was_extended, :user_logout, :print_jobs,
                        :started, :started)
            """), {
                "patron": random.choice(patron_ids),
                "token": token, "status": status,
                "minor": is_minor, "ptype": "child" if is_minor else random.choice(["adult", "teen"]),
                "ws": f"PC-{random.randint(1, 15):03d}",
                "branch": random.choice(branch_names),
                "minor_filter": is_minor,
                "started": started, "ended": ended,
                "ext_count": random.randint(0, 2),
                "ip": f"192.168.1.{random.randint(10, 250)}",
                "comp_id": comp_id,
                "is_active": status == "active",
                "was_extended": random.choice([True, False, False]),
                "user_logout": status == "ended" and random.random() > 0.5,
                "print_jobs": random.randint(0, 5),
            })
            cs_count += 1

        print(f"    Created {cs_count} computer sessions")
        await session.commit()

    # computer_usage_statistics (IMLS reporting aggregates)
    r = await session.execute(text("SELECT COUNT(*) FROM computer_usage_statistics"))
    if r.scalar() == 0:
        print("  Seeding computer_usage_statistics...")
        cus_count = 0
        for month_offset in range(3):
            m = now.month - month_offset
            y = now.year
            if m <= 0:
                m += 12
                y -= 1
            period_start = date(y, m, 1)
            if m == 12:
                period_end = date(y + 1, 1, 1) - timedelta(days=1)
            else:
                period_end = date(y, m + 1, 1) - timedelta(days=1)

            for bname in branch_names[:2]:
                await session.execute(text("""
                    INSERT INTO computer_usage_statistics
                        (period_start, period_end, period_type, branch_location,
                         total_sessions, unique_users, total_hours_used,
                         avg_session_length_minutes,
                         wifi_sessions, wifi_unique_devices,
                         print_jobs, pages_printed, copy_jobs, pages_copied,
                         generated_at, generated_by_id)
                    VALUES (:start, :end, 'monthly', :branch,
                            :sessions, :users, :hours,
                            :avg_len,
                            :wifi, :wifi_devices,
                            :prints, :pages, :copies, :copy_pages,
                            :gen_at, :gen_by)
                """), {
                    "start": period_start, "end": period_end, "branch": bname,
                    "sessions": random.randint(200, 800),
                    "users": random.randint(80, 300),
                    "hours": round(random.uniform(100, 500), 2),
                    "avg_len": round(random.uniform(30, 75), 2),
                    "wifi": random.randint(500, 2000),
                    "wifi_devices": random.randint(200, 800),
                    "prints": random.randint(100, 500),
                    "pages": random.randint(300, 2000),
                    "copies": random.randint(20, 100),
                    "copy_pages": random.randint(50, 300),
                    "gen_at": _past(month_offset * 30),
                    "gen_by": staff_ids[0],
                })
                cus_count += 1

        print(f"    Created {cus_count} computer usage statistics records")
        await session.commit()

    # computer_usage_stats (per-computer daily aggregates)
    r = await session.execute(text("SELECT COUNT(*) FROM computer_usage_stats"))
    if r.scalar() == 0 and computer_ids:
        print("  Seeding computer_usage_stats...")
        cus2_count = 0
        for comp_id in random.sample(computer_ids, min(5, len(computer_ids))):
            for days_ago in range(7):
                stat_date = _past(days_ago)
                hourly = json.dumps({str(h): random.randint(0, 8) for h in range(9, 21)})
                await session.execute(text("""
                    INSERT INTO computer_usage_stats
                        (computer_id, date,
                         total_reservations, completed_sessions,
                         cancelled_reservations, no_show_count,
                         total_minutes_used, total_extension_minutes,
                         guest_sessions, cardholders_sessions,
                         extension_requests, extension_requests_granted,
                         extension_requests_denied,
                         hourly_usage, downtime_minutes,
                         maintenance_events, print_jobs_count)
                    VALUES (:comp, :dt,
                            :reservations, :completed,
                            :cancelled, :no_show,
                            :minutes, :ext_min,
                            :guest, :cardholder,
                            :ext_req, :ext_granted,
                            :ext_denied,
                            cast(:hourly as jsonb), :downtime,
                            :maint, :prints)
                """), {
                    "comp": comp_id, "dt": stat_date,
                    "reservations": random.randint(5, 15),
                    "completed": random.randint(3, 12),
                    "cancelled": random.randint(0, 3),
                    "no_show": random.randint(0, 2),
                    "minutes": random.randint(180, 600),
                    "ext_min": random.randint(0, 120),
                    "guest": random.randint(0, 3),
                    "cardholder": random.randint(3, 10),
                    "ext_req": random.randint(0, 4),
                    "ext_granted": random.randint(0, 3),
                    "ext_denied": random.randint(0, 1),
                    "hourly": hourly,
                    "downtime": random.randint(0, 30),
                    "maint": random.randint(0, 1),
                    "prints": random.randint(0, 15),
                })
                cus2_count += 1

        print(f"    Created {cus2_count} computer usage stats records")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 10. SIP2 DEVICES & TRANSACTIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM sip2_devices"))
    if r.scalar() == 0:
        print("  Seeding sip2_devices...")
        devices = [
            ("Self-Checkout Kiosk 1", "SC-KIOSK-001", "192.168.10.101", 6001, "MAIN-LIB"),
            ("Self-Checkout Kiosk 2", "SC-KIOSK-002", "192.168.10.102", 6001, "MAIN-LIB"),
            ("Book Return Station", "AMH-RETURN-001", "192.168.10.110", 6001, "MAIN-LIB"),
            ("Drive-Through Return", "AMH-DRIVE-001", "192.168.10.120", 6001, "MAIN-LIB"),
        ]
        for name, dev_id, host, port, inst in devices:
            await session.execute(text("""
                INSERT INTO sip2_devices
                    (name, device_id, host, port, institution_id,
                     status, timeout_seconds, retry_attempts,
                     supports_checkin, supports_checkout, supports_sorting)
                VALUES (:name, :dev_id, :host, :port, :inst,
                        :status, 30, 3,
                        :checkin, :checkout, :sorting)
            """), {
                "name": name, "dev_id": dev_id, "host": host,
                "port": port, "inst": inst,
                "status": random.choice(["online", "online", "online", "offline"]),
                "checkin": "RETURN" in name or "DRIVE" in name,
                "checkout": "KIOSK" in name,
                "sorting": "AMH" in dev_id,
            })

        print(f"    Created {len(devices)} SIP2 devices")
        await session.commit()

    # SIP2 transactions
    r = await session.execute(text("SELECT COUNT(*) FROM sip2_transactions"))
    if r.scalar() == 0 and catalog_ids:
        print("  Seeding sip2_transactions...")
        commands = ["11", "12",
                    "09", "10",
                    "23", "24",
                    "63", "64",
                    "93", "94"]
        tx_count = 0
        for i in range(20):
            cmd = random.choice(commands)
            sess_id = secrets.token_hex(16)
            success = random.random() > 0.1
            created = _past(random.randint(0, 30))
            response_at = created + timedelta(milliseconds=random.randint(50, 500))
            await session.execute(text("""
                INSERT INTO sip2_transactions
                    (session_id, terminal_id, institution_id,
                     command, patron_id, item_id,
                     user_id, catalog_item_id, checkout_id,
                     success, error_message,
                     client_ip, client_port,
                     created_at, response_at, processing_time_ms)
                VALUES (:sess, :term, :inst,
                        :cmd, :patron_str, :item_str,
                        :user_id, :cat_id, :co_id,
                        :success, :error,
                        :ip, :port,
                        :created, :response, :proc_ms)
            """), {
                "sess": sess_id,
                "term": f"SC-KIOSK-{random.randint(1,2):03d}",
                "inst": "MAIN-LIB",
                "cmd": cmd,
                "patron_str": f"P{random.choice(all_ids):06d}" if cmd in ("23", "24", "63", "64", "11", "12") else None,
                "item_str": f"L30-{random.randint(1,370):03d}-001" if cmd in ("17", "18", "09", "10", "11", "12") else None,
                "user_id": random.choice(patron_ids) if cmd in ("11", "12") else None,
                "cat_id": random.choice(catalog_ids) if cmd in ("09", "10", "11", "12") else None,
                "co_id": random.choice(checkout_ids) if cmd == "12" and checkout_ids else None,
                "success": success,
                "error": "Connection timeout" if not success else None,
                "ip": f"192.168.10.{random.randint(101, 120)}",
                "port": random.randint(40000, 60000),
                "created": created,
                "response": response_at,
                "proc_ms": random.randint(20, 400),
            })
            tx_count += 1

        print(f"    Created {tx_count} SIP2 transactions")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 11. RFID READERS, TAGS, SESSIONS, SCANS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM rfid_readers"))
    if r.scalar() == 0:
        print("  Seeding rfid_readers...")
        readers = [
            ("Circulation Desk Reader", "RFID-SN-001", "Main Circulation Desk", "circulation_desk", "192.168.20.10"),
            ("Self-Checkout RFID Pad 1", "RFID-SN-002", "Self-Checkout Area", "self_checkout", "192.168.20.11"),
            ("Security Gate East", "RFID-SN-003", "Main Entrance East", "security_gate", "192.168.20.20"),
            ("Handheld Scanner 1", "RFID-SN-004", "Mobile", "handheld", "192.168.20.30"),
        ]
        for name, serial, location, rtype, ip in readers:
            await session.execute(text("""
                INSERT INTO rfid_readers
                    (name, serial_number, location, reader_type, protocol,
                     ip_address, port, status, antenna_count,
                     is_active, created_at)
                VALUES (:name, :serial, :loc, :rtype, 'sip2',
                        :ip, 5084, :status, :antennas,
                        true, :created)
            """), {
                "name": name, "serial": serial, "loc": location,
                "rtype": rtype, "ip": ip,
                "status": "online",
                "antennas": 2 if rtype == "security_gate" else 1,
                "created": _past(180),
            })

        print(f"    Created {len(readers)} RFID readers")
        await session.commit()

    # Get reader IDs for FK references
    rr = await session.execute(text("SELECT id FROM rfid_readers"))
    reader_ids_local = [r[0] for r in rr.fetchall()]

    # RFID tags
    r = await session.execute(text("SELECT COUNT(*) FROM rfid_tags"))
    if r.scalar() == 0 and copy_barcodes and reader_ids_local:
        print("  Seeding rfid_tags...")
        tag_count = 0
        for barcode in copy_barcodes:
            tag_id = f"E2003412{secrets.token_hex(4).upper()}"
            await session.execute(text("""
                INSERT INTO rfid_tags
                    (tag_id, item_barcode, security_bit, afi_byte, eas_enabled,
                     tag_type, manufacturer,
                     programmed_at, programmed_by_id, programmed_by_reader_id,
                     read_count, is_active, created_at)
                VALUES (:tag_id, :barcode, :sec, 'C2', true,
                        'ISO 15693', '3M',
                        :prog_at, :prog_by, :reader,
                        :reads, true, :created)
            """), {
                "tag_id": tag_id, "barcode": barcode,
                "sec": random.choice([True, True, True, False]),
                "prog_at": _past(random.randint(30, 365)),
                "prog_by": random.choice(staff_ids),
                "reader": reader_ids_local[0],
                "reads": random.randint(1, 100),
                "created": _past(random.randint(30, 365)),
            })
            tag_count += 1

        # Add more tags without barcodes for a total of ~20
        for i in range(max(0, 20 - tag_count)):
            tag_id = f"E2003412{secrets.token_hex(4).upper()}"
            await session.execute(text("""
                INSERT INTO rfid_tags
                    (tag_id, security_bit, afi_byte, eas_enabled,
                     tag_type, manufacturer,
                     programmed_at, programmed_by_id, programmed_by_reader_id,
                     read_count, is_active, created_at)
                VALUES (:tag_id, true, 'C2', true,
                        'ISO 15693', '3M',
                        :prog_at, :prog_by, :reader,
                        :reads, true, :created)
            """), {
                "tag_id": tag_id,
                "prog_at": _past(random.randint(30, 365)),
                "prog_by": random.choice(staff_ids),
                "reader": reader_ids_local[0],
                "reads": random.randint(0, 50),
                "created": _past(random.randint(30, 365)),
            })
            tag_count += 1

        print(f"    Created {tag_count} RFID tags")
        await session.commit()

    # RFID sessions
    r = await session.execute(text("SELECT COUNT(*) FROM rfid_sessions"))
    if r.scalar() == 0 and reader_ids_local:
        print("  Seeding rfid_sessions...")
        session_types = ["batch_checkout", "batch_checkin", "inventory_scan",
                         "tag_programming", "security_monitor"]
        rfid_session_ids = []
        for i in range(5):
            stype = session_types[i]
            started = _past(random.randint(1, 30))
            ended = started + timedelta(minutes=random.randint(5, 60)) if i < 4 else None
            sr = await session.execute(text("""
                INSERT INTO rfid_sessions
                    (session_type, reader_id, operator_id,
                     patron_id, target_location,
                     started_at, ended_at, is_active,
                     tags_scanned, tags_processed, tags_failed)
                VALUES (:stype, :reader, :operator,
                        :patron, :location,
                        :started, :ended, :active,
                        :scanned, :processed, :failed)
                RETURNING id
            """), {
                "stype": stype,
                "reader": random.choice(reader_ids_local),
                "operator": random.choice(staff_ids),
                "patron": random.choice(patron_ids) if stype in ("batch_checkout", "batch_checkin") else None,
                "location": random.choice(["Main Stacks", "Children's", "Reference", None]),
                "started": started, "ended": ended,
                "active": ended is None,
                "scanned": random.randint(5, 50),
                "processed": random.randint(4, 48),
                "failed": random.randint(0, 3),
            })
            rfid_session_ids.append(sr.scalar())

        print(f"    Created {len(rfid_session_ids)} RFID sessions")
        await session.commit()

        # RFID scans
        print("  Seeding rfid_scans...")
        tag_r = await session.execute(text("SELECT id, tag_id, item_barcode FROM rfid_tags LIMIT 30"))
        tags = tag_r.fetchall()
        scan_count = 0
        for sess_id in rfid_session_ids:
            num_scans = random.randint(3, 8)
            for _ in range(num_scans):
                tag_row = random.choice(tags) if tags else None
                await session.execute(text("""
                    INSERT INTO rfid_scans
                        (session_id, tag_id, rfid_tag_id,
                         item_barcode, item_title,
                         processed, process_result,
                         signal_strength, antenna_id,
                         found_at_location, is_misplaced,
                         scanned_at)
                    VALUES (:sess, :tag_str, :tag_fk,
                            :barcode, :title,
                            :processed, :result,
                            :signal, :antenna,
                            :location, :misplaced,
                            :scanned)
                """), {
                    "sess": sess_id,
                    "tag_str": tag_row[1] if tag_row else secrets.token_hex(8),
                    "tag_fk": tag_row[0] if tag_row else None,
                    "barcode": tag_row[2] if tag_row and tag_row[2] else None,
                    "title": "Library Item" if tag_row and tag_row[2] else None,
                    "processed": True,
                    "result": random.choice(["checkout_success", "checkin_success", "inventory_found"]),
                    "signal": round(random.uniform(-70, -30), 1),
                    "antenna": random.randint(1, 2),
                    "location": random.choice(["Main Stacks", "Children's", "Reference"]),
                    "misplaced": random.random() < 0.1,
                    "scanned": _past(random.randint(0, 30)),
                })
                scan_count += 1

        print(f"    Created {scan_count} RFID scans")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 12. SIGNAGE: TEMPLATES, DISPLAYS, CONTENT, SCHEDULES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM signage_template"))
    if r.scalar() == 0:
        print("  Seeding signage_template...")
        templates = [
            ("Event Announcement", "Standard event promotion template", "events",
             "<div class='event'><h1>{{event_name}}</h1><p>{{event_date}}</p><p>{{description}}</p></div>",
             ".event { text-align: center; padding: 2rem; }"),
            ("Library Hours", "Display current operating hours", "information",
             "<div class='hours'><h2>Library Hours</h2><ul>{{hours_list}}</ul></div>",
             ".hours { font-size: 1.5rem; }"),
            ("New Arrivals Showcase", "Rotating display of new materials", "collection",
             "<div class='arrivals'><h2>New This Week</h2><div class='grid'>{{items}}</div></div>",
             ".arrivals .grid { display: grid; grid-template-columns: repeat(4, 1fr); }"),
        ]
        template_ids = []
        for name, desc, category, html, css in templates:
            tr = await session.execute(text("""
                INSERT INTO signage_template
                    (name, description, category,
                     html_template, css_styles,
                     is_public, created_by_user_id)
                VALUES (:name, :desc, :cat,
                        :html, :css,
                        true, :creator)
                RETURNING id
            """), {
                "name": name, "desc": desc, "cat": category,
                "html": html, "css": css,
                "creator": staff_ids[0],
            })
            template_ids.append(tr.scalar())

        print(f"    Created {len(templates)} signage templates")
        await session.commit()
    else:
        tr = await session.execute(text("SELECT id FROM signage_template"))
        template_ids = [r[0] for r in tr.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM signage_display"))
    if r.scalar() == 0:
        print("  Seeding signage_display...")
        displays = [
            ("Main Lobby Display", "wall_mounted", "Main entrance lobby, above circulation desk", 1),
            ("Children's Area Kiosk", "kiosk", "Children's reading area, near entrance", 1),
            ("Meeting Room Directory", "directory", "Hallway outside meeting rooms A & B", 1),
            ("Drive-Through Info Board", "digital_poster", "Drive-through lane digital sign", 2),
        ]
        display_ids = []
        for name, dtype, location, bid in displays:
            dr = await session.execute(text("""
                INSERT INTO signage_display
                    (name, display_type, location_description,
                     status, width_pixels, height_pixels,
                     is_online, branch_id, created_by_user_id)
                VALUES (:name, :dtype, :loc,
                        'active', 1920, 1080,
                        true, :bid, :creator)
                RETURNING id
            """), {
                "name": name, "dtype": dtype, "loc": location,
                "bid": bid, "creator": staff_ids[0],
            })
            display_ids.append(dr.scalar())

        print(f"    Created {len(displays)} signage displays")
        await session.commit()
    else:
        dr = await session.execute(text("SELECT id FROM signage_display"))
        display_ids = [r[0] for r in dr.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM signage_content"))
    if r.scalar() == 0:
        print("  Seeding signage_content...")
        content_items = [
            ("Summer Reading Program 2026", "announcement", "Join our Summer Reading Program! Track your reading and win prizes.", "approved"),
            ("New Hours Starting April", "hours", "Updated spring hours for all branches.", "active"),
            ("Book Sale This Saturday", "event", "Friends of the Library annual book sale. All proceeds support library programs.", "active"),
            ("Free Tax Help Available", "promotion", "VITA volunteers available every Saturday through April 15.", "active"),
            ("Makerspace Now Open", "announcement", "Our new makerspace is open! 3D printers, laser cutters, and more.", "approved"),
            ("Story Time Schedule", "schedule", "Weekly story time for ages 0-5. Tuesdays and Thursdays at 10:30 AM.", "active"),
            ("WiFi Password", "announcement", "Free WiFi. Network: Library-Public. No password required.", "active"),
            ("Computer Lab Rules", "announcement", "60-minute sessions. Please save work frequently. Printing: 10 cents/page.", "active"),
            ("Teen Advisory Board Meeting", "event", "Next meeting: Friday at 4 PM. Snacks provided!", "scheduled"),
            ("Holiday Closures", "hours", "The library will be closed for Memorial Day, May 25.", "approved"),
        ]
        content_ids = []
        for title, ctype, desc, approval in content_items:
            cr = await session.execute(text("""
                INSERT INTO signage_content
                    (title, description, content_type,
                     html_content, approval_status,
                     display_duration_seconds, transition_effect,
                     template_id, branch_id, created_by_user_id)
                VALUES (:title, :desc, :ctype,
                        :html, :approval,
                        :dur, 'fade',
                        :template, :branch, :creator)
                RETURNING id
            """), {
                "title": title, "desc": desc, "ctype": ctype,
                "html": f"<div><h1>{title}</h1><p>{desc}</p></div>",
                "approval": approval,
                "dur": random.choice([15, 20, 30, 45]),
                "template": random.choice(template_ids) if template_ids and random.random() > 0.5 else None,
                "branch": random.choice(branch_ids) if random.random() > 0.3 else None,
                "creator": random.choice(staff_ids),
            })
            content_ids.append(cr.scalar())

        print(f"    Created {len(content_items)} signage content items")
        await session.commit()
    else:
        cr = await session.execute(text("SELECT id FROM signage_content"))
        content_ids = [r[0] for r in cr.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM signage_schedule"))
    if r.scalar() == 0 and display_ids and content_ids:
        print("  Seeding signage_schedule...")
        sched_count = 0
        for did in display_ids:
            num_content = random.randint(2, 4)
            for cid in random.sample(content_ids, min(num_content, len(content_ids))):
                stype = random.choice(["continuous", "recurring_daily", "one_time"])
                start = _past(random.randint(0, 30))
                end = start + timedelta(days=random.randint(14, 90))
                await session.execute(text("""
                    INSERT INTO signage_schedule
                        (display_id, content_id, schedule_type,
                         start_datetime, end_datetime,
                         start_time_of_day, end_time_of_day,
                         display_priority, is_active,
                         created_by_user_id)
                    VALUES (:did, :cid, :stype,
                            :start, :end,
                            :start_tod, :end_tod,
                            :priority, true,
                            :creator)
                """), {
                    "did": did, "cid": cid, "stype": stype,
                    "start": start, "end": end,
                    "start_tod": "09:00" if stype == "recurring_daily" else None,
                    "end_tod": "21:00" if stype == "recurring_daily" else None,
                    "priority": random.choice([50, 100, 100, 200]),
                    "creator": random.choice(staff_ids),
                })
                sched_count += 1

        print(f"    Created {sched_count} signage schedules")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # FIX SEQUENCES
    # ════════════════════════════════════════════════════════════════
    seq_tables = [
        "digital_access_orders", "digital_access_cards",
        "database_vendors", "database_subscriptions",
        "database_usage_stats", "database_renewal_notifications",
        "streaming_catalog_items", "streaming_checkouts",
        "streaming_usage_stats", "streaming_budgets",
        "collection_alerts", "collection_recovery_projects",
        "weeding_candidates",
        "series_reading_order", "series_completion", "series_popularity",
        "series_recommendations", "series_notification_rules", "series_waitlist",
        "new_arrival_alerts", "catalog_images",
        "computer_sessions", "computer_usage_statistics", "computer_usage_stats",
        "sip2_devices", "sip2_transactions", "sip2_terminals",
        "rfid_readers", "rfid_tags", "rfid_sessions", "rfid_scans",
        "signage_display", "signage_content", "signage_template", "signage_schedule",
    ]
    for table in seq_tables:
        try:
            async with session.begin_nested():
                await session.execute(text(
                    f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
                ))
        except SQLAlchemyError:
            pass

    await session.commit()
    print("  Digital batch seeding complete!")
    return True
