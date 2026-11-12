# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import random
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


def _future_date(days_ahead: int) -> date:
    return (datetime.now(utc) + timedelta(days=days_ahead)).date()


async def seed_batch_patron_services(session: AsyncSession) -> bool:

    # ── Grab reusable IDs ──────────────────────────────────────────
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] == "patron"]
    child_ids = [u[0] for u in users if u[1] == "child"]
    all_ids = [u[0] for u in users]

    items_r = await session.execute(text("SELECT id FROM catalog_items"))
    catalog_ids = [r[0] for r in items_r.fetchall()]

    branches_r = await session.execute(text("SELECT id FROM branches"))
    branch_ids = [r[0] for r in branches_r.fetchall()]

    fines_r = await session.execute(text("SELECT id, user_id FROM fines"))
    fines_data = fines_r.fetchall()
    fine_ids = [f[0] for f in fines_data]

    checkouts_r = await session.execute(text("SELECT id, user_id, item_id FROM checkouts LIMIT 50"))
    checkouts_data = checkouts_r.fetchall()

    copies_r = await session.execute(text("SELECT id, catalog_item_id, barcode FROM item_copies"))
    copies_data = copies_r.fetchall()

    dv_r = await session.execute(text("SELECT id FROM delivery_volunteers"))
    delivery_volunteer_ids = [r[0] for r in dv_r.fetchall()]

    partners_r = await session.execute(text("SELECT id, name FROM outreach_partners"))
    partners_data = partners_r.fetchall()
    partner_ids = [p[0] for p in partners_data]

    teen_r = await session.execute(text("SELECT id FROM teen_volunteers"))
    teen_volunteer_ids = [r[0] for r in teen_r.fetchall()]

    indie_r = await session.execute(text("SELECT id, title FROM indie_ebooks"))
    indie_data = indie_r.fetchall()

    dao_r = await session.execute(text("SELECT id FROM digital_access_orders"))
    dao_ids = [r[0] for r in dao_r.fetchall()]

    now = datetime.now(utc)

    # ════════════════════════════════════════════════════════════════
    # 1. HOMEBOUND APPLICATIONS + ENROLLMENTS + ITEM REQUESTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM homebound_applications"))
    if r.scalar() == 0:
        print("  Seeding homebound_applications, enrollments, item_requests...")

        app_data = [
            ("pending", "Recovering from hip replacement surgery. Cannot drive for 6 weeks.",
             "123 Maple St, Apt 2B", "555-0101", "biweekly", "Tuesday", "09:00", "12:00"),
            ("approved", "Permanent mobility limitation due to MS. Uses wheelchair.",
             "456 Oak Ave", "555-0202", "weekly", "Wednesday", "10:00", "14:00"),
            ("approved", "Legally blind. Cannot safely travel to library.",
             "789 Pine Rd", "555-0303", "biweekly", "Thursday", "09:00", "11:00"),
            ("approved", "Post-stroke recovery. No transportation available.",
             "321 Elm St", "555-0404", "monthly", "Monday", "13:00", "16:00"),
            ("approved", "Severe agoraphobia. Under treatment but cannot leave home.",
             "654 Birch Ln", "555-0505", "biweekly", "Friday", "10:00", "12:00"),
            ("denied", "Lives outside service area. Referred to neighboring library system.",
             "999 Far Away Dr", "555-0606", "weekly", "Monday", "09:00", "17:00"),
            ("waitlisted", "Caring for homebound spouse. Difficult to leave home.",
             "147 Willow Ct", "555-0707", "biweekly", "Wednesday", "14:00", "16:00"),
            ("withdrawn", "Patron recovered from surgery and can visit library again.",
             "258 Cedar Dr", "555-0808", "on_demand", None, None, None),
        ]

        app_ids_created = []
        selected_patrons = random.sample(patron_ids, min(len(patron_ids), 8))
        for i, (status, reason, addr, phone, freq, day, t_start, t_end) in enumerate(app_data):
            pid = selected_patrons[i] if i < len(selected_patrons) else random.choice(patron_ids)
            reviewer = random.choice(staff_ids) if status != "pending" else None
            reviewed_at = _past(random.randint(5, 30)) if reviewer else None
            r2 = await session.execute(text("""
                INSERT INTO homebound_applications
                    (patron_id, status, reason, medical_documentation, delivery_address,
                     contact_phone, preferred_frequency, preferred_day,
                     preferred_time_start, preferred_time_end,
                     submitted_at, reviewed_by_id, reviewed_at,
                     denial_reason)
                VALUES
                    (:pid, :status, :reason, :med_doc, :addr,
                     :phone, :freq, :day, :t_start, :t_end,
                     :submitted, :reviewer, :reviewed_at,
                     :denial)
                RETURNING id
            """), {
                "pid": pid, "status": status, "reason": reason,
                "med_doc": status in ("approved", "pending"),
                "addr": addr, "phone": phone,
                "freq": freq, "day": day, "t_start": t_start, "t_end": t_end,
                "submitted": _past(random.randint(30, 180)),
                "reviewer": reviewer, "reviewed_at": reviewed_at,
                "denial": "Outside service area boundary" if status == "denied" else None,
            })
            app_ids_created.append((r2.scalar(), pid, status, addr, phone, freq, day, t_start, t_end))

        # Create enrollments for approved applications
        enrollment_ids = []
        for app_id, pid, status, addr, phone, freq, day, t_start, t_end in app_ids_created:
            if status == "approved":
                vol_id = random.choice(delivery_volunteer_ids) if delivery_volunteer_ids else None
                r2 = await session.execute(text("""
                    INSERT INTO homebound_enrollments
                        (patron_id, application_id, status, delivery_address,
                         contact_phone, delivery_frequency, preferred_day,
                         preferred_time_start, preferred_time_end,
                         next_scheduled_delivery, assigned_volunteer_id,
                         enrolled_at, enrolled_by_id, total_deliveries, last_delivery_date)
                    VALUES
                        (:pid, :app_id, 'active', :addr,
                         :phone, :freq, :day, :t_start, :t_end,
                         :next_del, :vol_id,
                         :enrolled, :enrolled_by, :total_del, :last_del)
                    RETURNING id
                """), {
                    "pid": pid, "app_id": app_id, "addr": addr,
                    "phone": phone, "freq": freq, "day": day,
                    "t_start": t_start, "t_end": t_end,
                    "next_del": _future_date(random.randint(1, 14)),
                    "vol_id": vol_id,
                    "enrolled": _past(random.randint(5, 25)),
                    "enrolled_by": random.choice(staff_ids),
                    "total_del": random.randint(2, 12),
                    "last_del": _past_date(random.randint(7, 30)),
                })
                enrollment_ids.append(r2.scalar())

        # Create item requests for enrollments
        request_types = [
            ("specific_item", "The Midnight Library", "Matt Haig", "Heard about it on NPR"),
            ("author", None, "Colleen Hoover", "Anything by this author I haven't read"),
            ("genre", None, None, "Looking for cozy mysteries set in small towns"),
            ("topic", None, None, "Gardening books for container gardens on patios"),
            ("specific_item", "Lessons in Chemistry", "Bonnie Garmus", "Book club pick"),
            ("author", None, "James Patterson", "Latest Alex Cross novel please"),
            ("genre", None, None, "Large print romance novels"),
            ("topic", None, None, "Easy recipes for one person, preferably large print"),
        ]
        for enr_id in enrollment_ids:
            num_requests = random.randint(1, 3)
            for req_type, title, author, desc in random.sample(request_types, num_requests):
                await session.execute(text("""
                    INSERT INTO homebound_item_requests
                        (enrollment_id, request_type, title, author, description,
                         fulfilled, created_at)
                    VALUES
                        (:enr_id, :rtype, :title, :author, :desc,
                         :fulfilled, :created)
                """), {
                    "enr_id": enr_id, "rtype": req_type,
                    "title": title, "author": author, "desc": desc,
                    "fulfilled": random.choice([True, False]),
                    "created": _past(random.randint(1, 60)),
                })

        print(f"    Created {len(app_ids_created)} applications, {len(enrollment_ids)} enrollments")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 2. DELIVERY REQUESTS + ROUTES + DELIVERIES + ITEMS + FEEDBACK
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM delivery_requests"))
    if r.scalar() == 0:
        print("  Seeding delivery_requests, routes, deliveries, items, feedback...")

        # Delivery requests (one-click requests from any patron)
        dr_statuses = ["pending", "approved", "completed", "completed", "completed", "declined", "cancelled"]
        for i in range(8):
            status = dr_statuses[i % len(dr_statuses)]
            uid = random.choice(patron_ids)
            iid = random.choice(catalog_ids)
            approved = _past(random.randint(1, 30)) if status in ("approved", "completed") else None
            delivered = _past(random.randint(0, 10)) if status == "completed" else None
            declined = _past(random.randint(1, 15)) if status == "declined" else None
            cancelled = _past(random.randint(1, 10)) if status == "cancelled" else None
            await session.execute(text("""
                INSERT INTO delivery_requests
                    (user_id, item_id, status, frequency, delivery_address,
                     delivery_notes, created_at, updated_at,
                     approved_by_id, approved_at, delivered_at,
                     declined_at, decline_reason, cancelled_at)
                VALUES
                    (:uid, :iid, :status, 'on_demand', :addr,
                     :notes, :created, :created,
                     :approver, :approved, :delivered,
                     :declined, :decline_reason, :cancelled)
            """), {
                "uid": uid, "iid": iid, "status": status,
                "addr": f"{random.randint(100, 999)} Main St, Apt {random.randint(1, 20)}",
                "notes": random.choice(["Leave at front door", "Ring doorbell twice", "Call when arriving", None]),
                "created": _past(random.randint(5, 60)),
                "approver": random.choice(staff_ids) if approved else None,
                "approved": approved, "delivered": delivered,
                "declined": declined,
                "decline_reason": "Outside delivery area" if declined else None,
                "cancelled": cancelled,
            })

        # Delivery routes
        route_ids = []
        route_data = [
            ("North Route - Tuesday", "completed", 90, 12.5),
            ("South Route - Wednesday", "completed", 120, 18.0),
            ("East Route - Thursday", "in_progress", 75, 8.3),
            ("West Route - Friday", "planned", 100, 15.0),
        ]
        for name, status, dur, dist in route_data:
            r2 = await session.execute(text("""
                INSERT INTO delivery_routes
                    (name, date, status, volunteer_id,
                     estimated_duration_minutes, estimated_distance_miles,
                     planned_start_time, planned_end_time,
                     total_stops, completed_stops, total_items,
                     created_by_id, created_at)
                VALUES
                    (:name, :dt, :status, :vol,
                     :dur, :dist, '09:00', '13:00',
                     :stops, :completed, :items,
                     :creator, :created)
                RETURNING id
            """), {
                "name": name, "dt": _past_date(random.randint(1, 30)),
                "status": status,
                "vol": random.choice(delivery_volunteer_ids) if delivery_volunteer_ids else None,
                "dur": dur, "dist": dist,
                "stops": random.randint(3, 6),
                "completed": random.randint(0, 3) if status != "completed" else random.randint(3, 6),
                "items": random.randint(6, 20),
                "creator": random.choice(staff_ids),
                "created": _past(random.randint(2, 35)),
            })
            route_ids.append(r2.scalar())

        # Get enrollment IDs for deliveries
        enr_r = await session.execute(text("SELECT id, delivery_address FROM homebound_enrollments"))
        enrollments = enr_r.fetchall()

        # Deliveries
        delivery_ids = []
        if enrollments:
            del_statuses = ["delivered", "delivered", "delivered", "scheduled", "packed", "out_for_delivery"]
            for i, (enr_id, addr) in enumerate(enrollments):
                for j in range(random.randint(1, 3)):
                    d_status = del_statuses[(i + j) % len(del_statuses)]
                    route = random.choice(route_ids) if route_ids else None
                    r2 = await session.execute(text("""
                        INSERT INTO deliveries
                            (enrollment_id, route_id, route_order, status,
                             scheduled_date, scheduled_time_start, scheduled_time_end,
                             delivery_address,
                             packed_at, packed_by_id,
                             delivered_at, items_count, items_delivered,
                             created_at)
                        VALUES
                            (:enr, :route, :order, :status,
                             :sched_date, '09:00', '12:00',
                             :addr,
                             :packed, :packed_by,
                             :delivered, :items, :items_del,
                             :created)
                        RETURNING id
                    """), {
                        "enr": enr_id, "route": route,
                        "order": j + 1, "status": d_status,
                        "sched_date": _past_date(random.randint(1, 60)),
                        "addr": addr,
                        "packed": _past(random.randint(1, 30)) if d_status in ("delivered", "packed", "out_for_delivery") else None,
                        "packed_by": random.choice(staff_ids) if d_status in ("delivered", "packed", "out_for_delivery") else None,
                        "delivered": _past(random.randint(0, 25)) if d_status == "delivered" else None,
                        "items": random.randint(2, 6),
                        "items_del": random.randint(2, 6) if d_status == "delivered" else 0,
                        "created": _past(random.randint(5, 65)),
                    })
                    delivery_ids.append(r2.scalar())

        # Delivery items
        for del_id in delivery_ids:
            num_items = random.randint(1, 4)
            for _ in range(num_items):
                cid = random.choice(catalog_ids)
                await session.execute(text("""
                    INSERT INTO delivery_items
                        (delivery_id, item_id, item_title, item_author,
                         item_format, status, patron_requested)
                    VALUES
                        (:del_id, :item_id, :title, :author,
                         :fmt, :status, :requested)
                """), {
                    "del_id": del_id, "item_id": cid,
                    "title": f"Item #{cid}",
                    "author": random.choice(["Various", "Staff Selected", "Patron Requested"]),
                    "fmt": random.choice(["book", "large_print", "audiobook"]),
                    "status": random.choice(["delivered", "pending", "packed"]),
                    "requested": random.choice([True, False]),
                })

        # Delivery feedback (for delivered items)
        for del_id in delivery_ids[:4]:
            await session.execute(text("""
                INSERT INTO delivery_feedback
                    (delivery_id, overall_rating, item_satisfaction,
                     volunteer_rating, timeliness_rating,
                     comments, would_recommend, submitted_at)
                VALUES
                    (:del_id, :rating, :item_sat,
                     :vol_rat, :time_rat,
                     :comments, :recommend, :submitted)
            """), {
                "del_id": del_id,
                "rating": random.randint(3, 5),
                "item_sat": random.randint(3, 5),
                "vol_rat": random.randint(4, 5),
                "time_rat": random.randint(3, 5),
                "comments": random.choice([
                    "Wonderful service! The volunteer was so kind.",
                    "Books were exactly what I wanted. Thank you!",
                    "Arrived right on time. Great selection this week.",
                    "Love this program. It keeps me connected to the library.",
                ]),
                "recommend": True,
                "submitted": _past(random.randint(1, 30)),
            })

        print(f"    Created 8 delivery requests, {len(route_ids)} routes, {len(delivery_ids)} deliveries")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 3. PATRON ACCOUNTS + TRANSACTIONS + PAYMENT PLANS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM patron_accounts"))
    if r.scalar() == 0:
        print("  Seeding patron_accounts, transactions, payment_plans...")

        account_ids = []
        selected = random.sample(patron_ids, min(len(patron_ids), 20))
        for pid in selected:
            balance = Decimal(str(round(random.uniform(0, 25), 2)))
            deposited = Decimal(str(round(random.uniform(10, 100), 2)))
            spent = deposited - balance if deposited > balance else Decimal("0.00")
            r2 = await session.execute(text("""
                INSERT INTO patron_accounts
                    (patron_id, balance, total_deposited, total_spent,
                     is_active, low_balance_threshold,
                     auto_reload_enabled, last_deposit_at,
                     created_at, updated_at)
                VALUES
                    (:pid, :bal, :dep, :spent,
                     true, 2.00,
                     :auto, :last_dep,
                     :created, :created)
                RETURNING id
            """), {
                "pid": pid, "bal": balance, "dep": deposited, "spent": spent,
                "auto": random.choice([True, False, False]),
                "last_dep": _past(random.randint(1, 90)),
                "created": _past(random.randint(30, 365)),
            })
            account_ids.append(r2.scalar())

        # Transactions for each account
        tx_types = ["DEPOSIT", "CHARGE", "DEPOSIT", "CHARGE", "CHARGE"]
        tx_descs = {
            "DEPOSIT": ["Cash deposit at desk", "Online payment", "Credit card reload"],
            "CHARGE": ["B&W printing (5 pages)", "Color printing (2 pages)", "3D print job", "Meeting room fee"],
        }
        for acct_id in account_ids:
            num_tx = random.randint(2, 6)
            running_bal = Decimal("0.00")
            for _ in range(num_tx):
                tx_type = random.choice(tx_types)
                amt = Decimal(str(round(random.uniform(1, 20), 2)))
                before = running_bal
                if tx_type == "DEPOSIT":
                    running_bal += amt
                else:
                    running_bal = max(Decimal("0.00"), running_bal - amt)
                after = running_bal
                await session.execute(text("""
                    INSERT INTO patron_transactions
                        (account_id, transaction_type, status,
                         amount, balance_before, balance_after,
                         payment_method, description,
                         receipt_number, created_at)
                    VALUES
                        (:acct, :ttype, 'completed',
                         :amt, :before, :after,
                         :method, :desc,
                         :receipt, :created)
                """), {
                    "acct": acct_id, "ttype": tx_type,
                    "amt": amt, "before": before, "after": after,
                    "method": random.choice(["CASH", "CREDIT_CARD", "ONLINE"]) if tx_type == "DEPOSIT" else "SYSTEM",
                    "desc": random.choice(tx_descs[tx_type]),
                    "receipt": f"RCP-{acct_id}-{random.randint(10000, 99999)}",
                    "created": _past(random.randint(1, 180)),
                })

        # Payment plans (3 patrons with large fines)
        plan_patrons = random.sample(patron_ids, min(len(patron_ids), 3))
        for pid in plan_patrons:
            total = Decimal(str(round(random.uniform(25, 75), 2)))
            installment = Decimal(str(round(float(total) / random.randint(3, 6), 2)))
            paid_so_far = installment * random.randint(0, 2)
            status = "active" if paid_so_far < total else "completed"
            await session.execute(text("""
                INSERT INTO payment_plans
                    (user_id, total_amount, installment_amount,
                     frequency, status, amount_paid, payments_made,
                     total_payments_expected, start_date, next_payment_date,
                     reminder_enabled, notes, created_by_id,
                     created_at, updated_at)
                VALUES
                    (:uid, :total, :install,
                     'monthly', :status, :paid, :made,
                     :expected, :start, :next_pay,
                     true, :notes, :creator,
                     :created, :created)
            """), {
                "uid": pid, "total": total, "install": installment,
                "status": status, "paid": paid_so_far,
                "made": int(paid_so_far / installment) if installment > 0 else 0,
                "expected": max(1, int(float(total) / float(installment))) if installment > 0 else 4,
                "start": _past(random.randint(30, 120)),
                "next_pay": _past(random.randint(0, 15)) if status == "active" else None,
                "notes": "Payment plan for accumulated overdue fines.",
                "creator": random.choice(staff_ids),
                "created": _past(random.randint(30, 120)),
            })

        print(f"    Created {len(account_ids)} accounts, {len(plan_patrons)} payment plans")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 4. PATRON MESSAGES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM patron_messages"))
    if r.scalar() == 0:
        print("  Seeding patron_messages...")

        messages = [
            ("OVERDUE_NOTICE", "EMAIL", "Overdue Notice — Items Past Due", "You have 2 items currently overdue. Please return them at your earliest convenience to avoid additional fines."),
            ("HOLD_READY", "EMAIL", "Your Hold Is Ready for Pickup", "Good news! 'The Midnight Library' is now available for pickup at the Main Branch circulation desk. This hold will expire in 7 days."),
            ("FINE_REMINDER", "EMAIL", "Fine Balance Reminder", "Your current fine balance is $12.50. You can pay online, at any branch, or ask about our Read Down Your Fines program."),
            ("WELCOME_NEW_PATRON", "EMAIL", "Welcome to the Library!", "Welcome! Your new library card gives you access to books, ebooks, databases, museum passes, and so much more."),
            ("CUSTOM", "EMAIL", "Summer Reading Program Invitation", "You're invited to join our Summer Reading Challenge! Read 20 books this summer and earn prizes."),
            ("OVERDUE_NOTICE", "SMS", "Overdue Reminder", "Reminder: You have overdue items. Please return them to avoid fines. Visit your account online for details."),
            ("HOLD_READY", "SMS", "Hold Ready", "Your hold is ready! Pick up 'Lessons in Chemistry' at the Children's Branch within 7 days."),
            ("CUSTOM", "EMAIL", "Library Card Renewal Reminder", "Your library card expires next month. Visit any branch with a valid ID to renew for free."),
            ("ACCOUNT_BLOCKED", "EMAIL", "Account Notice — Action Required", "Your account has been temporarily restricted due to outstanding fines exceeding $25. Please contact circulation to resolve."),
            ("CUSTOM", "EMAIL", "New Digital Resources Available", "We've added new databases: Consumer Reports and Ancestry Library. Access them from our website."),
            ("FINE_REMINDER", "EMAIL", "Payment Plan Reminder", "Your next payment plan installment of $10.00 is due this Friday. Pay online or at the circulation desk."),
            ("HOLD_READY", "EMAIL", "Multiple Holds Ready", "You have 3 holds ready for pickup at the Main Branch. They will be held for 7 days."),
            ("CUSTOM", "EMAIL", "Book Club Meeting This Thursday", "Reminder: The Thursday Night Book Club meets this week to discuss 'Demon Copperhead'. Snacks provided!"),
            ("OVERDUE_NOTICE", "EMAIL", "Final Overdue Notice", "This is a final notice for 3 overdue items. If not returned within 14 days, replacement charges will apply."),
            ("CUSTOM", "SMS", "Event Reminder", "Don't forget: Author talk with local poet Maya Chen tonight at 7pm. Free and open to all!"),
            ("WELCOME_NEW_PATRON", "EMAIL", "Welcome — What's Next?", "Now that you have your card, here are 5 things to try: 1) Browse ebooks 2) Reserve a study room 3) Join a book club 4) Explore databases 5) Attend an event."),
            ("CUSTOM", "EMAIL", "Volunteer Appreciation", "Thank you for volunteering 20 hours this month! Your dedication makes our community stronger."),
            ("HOLD_READY", "EMAIL", "Interlibrary Loan Arrived", "Your interlibrary loan request has arrived. Pick up 'Rare Local History Vol. 3' at the reference desk."),
            ("CUSTOM", "EMAIL", "Survey: Help Us Improve", "We'd love your feedback! Take our 5-minute patron survey to help shape library services."),
            ("FINE_REMINDER", "SMS", "Fine Reminder", "You have a fine balance of $5.25. Pay online or at any branch. Questions? Call 555-0100."),
        ]

        for msg_type, channel, subject, body in messages:
            pid = random.choice(patron_ids)
            sid = random.choice(staff_ids)
            await session.execute(text("""
                INSERT INTO patron_messages
                    (patron_id, sender_id, message_type, channel,
                     subject, body, recipient_email,
                     sent_at, delivered)
                VALUES
                    (:pid, :sid, :mtype, :channel,
                     :subject, :body, :email,
                     :sent, true)
            """), {
                "pid": pid, "sid": sid, "mtype": msg_type, "channel": channel,
                "subject": subject, "body": body,
                "email": f"patron{pid}@example.com" if channel == "EMAIL" else None,
                "sent": _past(random.randint(0, 90)),
            })

        print(f"    Created {len(messages)} patron messages")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 5. PATRON STATISTICS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM patron_statistics"))
    if r.scalar() == 0:
        print("  Seeding patron_statistics...")

        periods = [
            (date(2025, 1, 1), date(2025, 3, 31), "quarterly", None),
            (date(2025, 4, 1), date(2025, 6, 30), "quarterly", None),
            (date(2025, 7, 1), date(2025, 9, 30), "quarterly", None),
            (date(2025, 10, 1), date(2025, 12, 31), "quarterly", None),
            (date(2026, 1, 1), date(2026, 3, 31), "quarterly", None),
            (date(2025, 1, 1), date(2025, 12, 31), "annual", None),
        ]
        for ps, pe, ptype, branch in periods:
            await session.execute(text("""
                INSERT INTO patron_statistics
                    (period_start, period_end, period_type, branch_location,
                     total_registered_patrons, new_registrations,
                     expired_cards, renewed_cards,
                     active_borrowers, active_patrons_any_service,
                     patrons_by_age_group, patrons_by_patron_type, patrons_by_zip_code,
                     avg_checkouts_per_active_patron, avg_visits_per_active_patron,
                     resident_patrons, non_resident_patrons,
                     generated_at, generated_by_id)
                VALUES
                    (:ps, :pe, :ptype, :branch,
                     :total, :new_reg,
                     :expired, :renewed,
                     :borrowers, :any_service,
                     cast(:by_age as jsonb), cast(:by_type as jsonb), cast(:by_zip as jsonb),
                     :avg_co, :avg_vis,
                     :resident, :non_resident,
                     :gen_at, :gen_by)
            """), {
                "ps": ps, "pe": pe, "ptype": ptype, "branch": branch,
                "total": random.randint(8000, 12000),
                "new_reg": random.randint(50, 200),
                "expired": random.randint(10, 50),
                "renewed": random.randint(30, 100),
                "borrowers": random.randint(3000, 6000),
                "any_service": random.randint(5000, 9000),
                "by_age": json.dumps({"child": random.randint(800, 1500), "teen": random.randint(400, 800), "adult": random.randint(4000, 7000), "senior": random.randint(1000, 2000)}),
                "by_type": json.dumps({"regular": random.randint(6000, 9000), "student": random.randint(500, 1500), "staff": random.randint(20, 60)}),
                "by_zip": json.dumps({"46001": random.randint(2000, 4000), "46002": random.randint(1500, 3000), "46003": random.randint(1000, 2000)}),
                "avg_co": round(random.uniform(4, 12), 2),
                "avg_vis": round(random.uniform(2, 8), 2),
                "resident": random.randint(7000, 10000),
                "non_resident": random.randint(200, 800),
                "gen_at": _past(random.randint(1, 30)),
                "gen_by": random.choice(staff_ids),
            })

        print(f"    Created {len(periods)} patron statistics periods")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 6. PATRON GROUPS + MEMBERS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM patron_groups"))
    if r.scalar() == 0:
        print("  Seeding patron_groups and members...")

        groups = [
            ("Johnson Family Account", "Household group for the Johnson family", False, 6),
            ("Lincoln Elementary Classroom", "Mrs. Rivera's 3rd grade class", False, 30),
            ("Senior Book Club", "Weekly senior book discussion group", True, 20),
            ("Teen Advisory Board", "Youth advisory council for library programming", True, 15),
        ]
        group_ids_created = []
        for name, desc, self_join, max_mem in groups:
            r2 = await session.execute(text("""
                INSERT INTO patron_groups
                    (name, description, is_active, created_by_id,
                     allow_self_join, max_members)
                VALUES
                    (:name, :desc, true, :creator,
                     :self_join, :max_mem)
                RETURNING id
            """), {
                "name": name, "desc": desc,
                "creator": random.choice(staff_ids),
                "self_join": self_join, "max_mem": max_mem,
            })
            group_ids_created.append(r2.scalar())

        # Add members to groups
        total_members = 0
        for gid in group_ids_created:
            num_members = random.randint(3, 8)
            member_pool = random.sample(patron_ids, min(len(patron_ids), num_members))
            for j, mid in enumerate(member_pool):
                role = "leader" if j == 0 else "member"
                await session.execute(text("""
                    INSERT INTO patron_group_members
                        (group_id, patron_id, joined_at, added_by_id, role)
                    VALUES
                        (:gid, :pid, :joined, :added_by, :role)
                """), {
                    "gid": gid, "pid": mid,
                    "joined": _past(random.randint(1, 180)),
                    "added_by": random.choice(staff_ids),
                    "role": role,
                })
                total_members += 1

        print(f"    Created {len(group_ids_created)} groups, {total_members} members")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 7. PATRON BOUNDARIES + BOUNDARY POLICIES + BOUNDARY TEMPLATES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM patron_boundaries"))
    if r.scalar() == 0:
        print("  Seeding patron_boundaries, boundary_policies, boundary_templates...")

        boundaries = [
            ("CIRCULATION_SUSPENSION", "Circulation Suspension — Excessive Overdue",
             "Patron has 15+ overdue items over 60 days. Borrowing privileges suspended pending return.",
             "active", False),
            ("BEHAVIOR_CONTRACT", "Behavior Contract — Disruptive Conduct",
             "Patron was loud and argumentative with staff on two occasions. Required to sign behavior contract.",
             "active", False),
            ("SERVICE_RESTRICTION", "Computer Lab Restriction",
             "Patron violated internet use policy by accessing prohibited content. Computer access suspended 30 days.",
             "active", False),
            ("TIME_LIMIT", "Visit Time Limit",
             "Patron has been lingering past closing. Limited to standard operating hours only.",
             "expired", False),
            ("STAFF_INTERACTION_LIMIT", "Single Point of Contact",
             "Patron directed to work with branch manager only due to pattern of escalating interactions with multiple staff.",
             "active", False),
        ]
        for btype, title, desc, status, permanent in boundaries:
            await session.execute(text("""
                INSERT INTO patron_boundaries
                    (organization_id, patron_id, boundary_type, title, description,
                     status, requires_approval, approved_by_director,
                     start_date, end_date, is_permanent,
                     incident_count, can_appeal,
                     created_by_id, approved_by_id,
                     created_at, updated_at, is_deleted)
                VALUES
                    (1, :pid, :btype, :title, :desc,
                     :status, true, true,
                     :start, :end_dt, :perm,
                     :incidents, true,
                     :creator, :approver,
                     :created, :created, false)
            """), {
                "pid": random.choice(patron_ids), "btype": btype,
                "title": title, "desc": desc,
                "status": status, "perm": permanent,
                "start": _past(random.randint(10, 90)),
                "end_dt": _past(-30).replace(tzinfo=None) if status == "active" else _past(5).replace(tzinfo=None),
                "incidents": random.randint(1, 4),
                "creator": random.choice(staff_ids),
                "approver": random.choice(staff_ids),
                "created": _past(random.randint(10, 90)),
            })

        # Boundary policies
        policies = [
            ("BP-001", "Circulation Suspension Policy",
             "Borrowing privileges may be suspended when a patron has 10+ items overdue for 30+ days or outstanding fines exceeding $50.",
             True, False),
            ("BP-002", "Behavior Contract Policy",
             "Patrons who exhibit disruptive behavior on two or more occasions may be required to sign a behavior contract outlining expectations.",
             True, False),
            ("BP-003", "Computer Use Violation Policy",
             "Violations of the acceptable use policy result in computer access suspension: 7 days for first offense, 30 days for second, permanent for third.",
             False, False),
            ("BP-004", "Trespass Policy",
             "Patrons who pose a safety threat may be issued a trespass notice. Requires director approval. Board notification within 48 hours.",
             True, True),
        ]
        for code, name, policy_text, dir_approval, board_approval in policies:
            await session.execute(text("""
                INSERT INTO boundary_policies
                    (organization_id, policy_name, policy_code, policy_text,
                     requires_director_approval, requires_board_approval,
                     effective_date)
                VALUES
                    (1, :name, :code, :text,
                     :dir, :board,
                     :eff)
            """), {
                "name": name, "code": code, "text": policy_text,
                "dir": dir_approval, "board": board_approval,
                "eff": datetime(2025, 1, 1),  # naive datetime for non-TZ column
            })

        # Boundary templates
        templates = [
            ("Overdue Suspension Notice", "CIRCULATION_SUSPENSION",
             "I understand you're frustrated, and I want to help. Currently, your account shows [X] items overdue. Our policy requires us to pause borrowing privileges until these are resolved. Let's look at options together.",
             "empathetic", "When a patron's overdue count exceeds policy threshold"),
            ("Behavior Contract Introduction", "BEHAVIOR_CONTRACT",
             "We value you as a patron and want you to continue using the library. To help us all have a positive experience, we'd like to go over a few guidelines together. This isn't punitive — it's about setting clear expectations.",
             "firm", "After second documented behavioral incident"),
            ("Computer Restriction Explanation", "SERVICE_RESTRICTION",
             "Our computer use policy exists to ensure a safe environment for all patrons. The activity we observed on [date] falls outside acceptable use. Your computer access will be paused for [duration]. You can still use all other library services.",
             "formal", "When internet use policy is violated"),
        ]
        for name, btype, script, tone, when_to_use in templates:
            await session.execute(text("""
                INSERT INTO boundary_templates
                    (organization_id, name, boundary_type, script_content,
                     tone_guidance, when_to_use,
                     created_by_id, usage_count)
                VALUES
                    (1, :name, :btype, :script,
                     :tone, :when,
                     :creator, :usage)
            """), {
                "name": name, "btype": btype, "script": script,
                "tone": tone, "when": when_to_use,
                "creator": random.choice(staff_ids),
                "usage": random.randint(0, 12),
            })

        print(f"    Created {len(boundaries)} boundaries, {len(policies)} policies, {len(templates)} templates")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 8. PARENT/GUARDIAN CONSENTS + COPPA
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM coppa_compliance"))
    if r.scalar() == 0:
        print("  Seeding consents, COPPA compliance...")

        # Parent/guardian consents for teen volunteers
        if teen_volunteer_ids:
            consent_statuses = ["GRANTED", "GRANTED", "GRANTED", "GRANTED", "WITHDRAWN"]
            for i, tv_id in enumerate(teen_volunteer_ids):
                status = consent_statuses[i % len(consent_statuses)]
                signed = _past(random.randint(10, 90)) if status == "GRANTED" else None
                revoked = _past(random.randint(1, 30)) if status == "WITHDRAWN" else None
                await session.execute(text("""
                    INSERT INTO parent_guardian_consents
                        (volunteer_id, status, consent_form_version,
                         consent_signed_date, consent_revoked_date,
                         approved_by_name, approved_by_email,
                         acknowledges_health_risks, acknowledges_background_check,
                         authorizes_transportation, authorizes_photo_use,
                         contact_frequency, preferred_contact_method)
                    VALUES
                        (:vid, :status, '2.0',
                         :signed, :revoked,
                         :parent_name, :parent_email,
                         :health, :bg,
                         :transport, :photo,
                         'monthly', 'email')
                """), {
                    "vid": tv_id, "status": status,
                    "signed": signed, "revoked": revoked,
                    "parent_name": random.choice(["Sarah Johnson", "Mike Williams", "Lisa Chen", "Robert Davis", "Maria Garcia"]),
                    "parent_email": f"parent{tv_id}@example.com",
                    "health": True, "bg": True,
                    "transport": random.choice([True, False]),
                    "photo": random.choice([True, True, False]),
                })

        # COPPA compliance record
        await session.execute(text("""
            INSERT INTO coppa_compliance
                (organization_id, status,
                 parental_consent_process,
                 collect_personal_data_from_minors, requires_parental_consent,
                 minor_data_is_encrypted, minor_data_retention_months,
                 parents_can_review_data, parents_can_delete_data, parents_can_opt_out,
                 staff_trained_on_coppa, staff_training_date, next_training_due,
                 notes)
            VALUES
                (1, 'compliant',
                 'Parents must sign consent form at registration. Digital consent available via parent portal.',
                 true, true,
                 true, 12,
                 true, true, true,
                 true, :train_date, :next_train,
                 'Annual COPPA compliance review completed. All systems meet requirements.')
        """), {
            "train_date": _past_date(60),
            "next_train": _future_date(305),
        })

        print(f"    Created {len(teen_volunteer_ids)} consents, 1 COPPA record")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 9. PATRON CHATBOT CONTEXT
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM patron_chatbot_context"))
    if r.scalar() == 0:
        print("  Seeding patron_chatbot_context...")

        chatbot_questions = [
            "What are the library hours on Saturday?",
            "How do I renew my books online?",
            "Where can I find the tax forms?",
            "Do you have a notary public?",
            "How do I access ebooks on my Kindle?",
            "What databases do you have for genealogy research?",
            "Can I reserve a meeting room for my book club?",
            "How do I get a replacement library card?",
            "What's the fine for a lost book?",
            "Do you offer ESL classes?",
            "How do I use the 3D printer in the makerspace?",
            "Where are the large print books?",
        ]
        chatbot_patrons = random.sample(patron_ids, min(len(patron_ids), 12))
        for i, pid in enumerate(chatbot_patrons):
            q = chatbot_questions[i % len(chatbot_questions)]
            total = random.randint(1, 20)
            resolved = random.randint(0, total)
            escalated = total - resolved
            await session.execute(text("""
                INSERT INTO patron_chatbot_context
                    (user_id, last_question, last_interaction_at,
                     total_interactions, questions_resolved_count,
                     questions_escalated_count,
                     current_unresolved_question, escalation_count_today)
                VALUES
                    (:uid, :question, :last_at,
                     :total, :resolved,
                     :escalated,
                     :unresolved, :esc_today)
            """), {
                "uid": pid, "question": q,
                "last_at": _past(random.randint(0, 30)),
                "total": total, "resolved": resolved, "escalated": escalated,
                "unresolved": q if escalated > 0 else None,
                "esc_today": random.randint(0, 2) if escalated > 0 else 0,
            })

        print(f"    Created {len(chatbot_patrons)} chatbot contexts")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 10. PATRON MEDICAL INFO (minimal/generic)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM patron_medical_info"))
    if r.scalar() == 0:
        print("  Seeding patron_medical_info...")

        med_data = [
            ("Peanut allergy", None, None, "Carries EpiPen", "Jane Smith", "555-1001", "Spouse"),
            ("None known", "Diabetes Type 2", "Metformin", "Wears medical alert bracelet", "Michael Brown", "555-1002", "Son"),
            ("Bee sting allergy", None, "Epinephrine auto-injector", None, "Carol Davis", "555-1003", "Daughter"),
            ("None known", "Epilepsy", "Levetiracetam", "May have seizures. Do not restrain. Clear area.", "Tom Wilson", "555-1004", "Brother"),
            ("Latex allergy", "Asthma", "Albuterol inhaler", "Inhaler kept in purse", "Lisa Anderson", "555-1005", "Partner"),
        ]
        med_patrons = random.sample(patron_ids, min(len(patron_ids), 5))
        for i, pid in enumerate(med_patrons):
            allergies, conditions, meds, notes, ec_name, ec_phone, ec_rel = med_data[i]
            await session.execute(text("""
                INSERT INTO patron_medical_info
                    (patron_id, allergies, medical_conditions, medications,
                     medical_notes,
                     emergency_contact_1_name, emergency_contact_1_phone,
                     emergency_contact_1_relationship,
                     visible_to_staff)
                VALUES
                    (:pid, :allergies, :conditions, :meds,
                     :notes,
                     :ec_name, :ec_phone,
                     :ec_rel,
                     true)
            """), {
                "pid": pid, "allergies": allergies,
                "conditions": conditions, "meds": meds,
                "notes": notes,
                "ec_name": ec_name, "ec_phone": ec_phone,
                "ec_rel": ec_rel,
            })

        print(f"    Created {len(med_patrons)} medical info records")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 11. PATRON ONBOARDING PROGRESS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM patron_onboarding_progress"))
    if r.scalar() == 0:
        print("  Seeding patron_onboarding_progress...")

        onboard_patrons = random.sample(patron_ids, min(len(patron_ids), 15))
        for pid in onboard_patrons:
            step = random.choice([3, 4, 5, 5, 5, 5])  # Most completed
            completed = step == 5
            genres = json.dumps(random.sample(["fiction", "mystery", "romance", "sci-fi", "biography", "history", "fantasy", "thriller"], 3))
            formats = json.dumps(random.sample(["book", "ebook", "audiobook", "large_print"], 2))
            goal = random.choice(["casual", "regular", "avid"])
            await session.execute(text("""
                INSERT INTO patron_onboarding_progress
                    (patron_id,
                     step_welcome_completed, step_preferences_completed,
                     step_branch_completed, step_tour_completed,
                     step_complete_completed,
                     current_step, preferred_genres, preferred_formats,
                     reading_goal, skipped, completed_at, started_at,
                     created_at, updated_at)
                VALUES
                    (:pid,
                     true, :pref,
                     :branch, :tour,
                     :complete,
                     :step, :genres, :formats,
                     :goal, :skipped, :completed_at, :started,
                     :created, :created)
            """), {
                "pid": pid,
                "pref": step >= 2, "branch": step >= 3,
                "tour": step >= 4, "complete": step >= 5,
                "step": step,
                "genres": genres, "formats": formats,
                "goal": goal,
                "skipped": step < 5 and random.choice([True, False]),
                "completed_at": _past(random.randint(1, 60)) if completed else None,
                "started": _past(random.randint(30, 180)),
                "created": _past(random.randint(30, 180)),
            })

        print(f"    Created {len(onboard_patrons)} onboarding progress records")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 12. HOUSEHOLD LINKS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM household_links"))
    if r.scalar() == 0 and child_ids and patron_ids:
        print("  Seeding household_links...")

        link_count = 0
        available_children = list(child_ids)
        available_parents = random.sample(patron_ids, min(len(patron_ids), 4))
        statuses = ["approved", "approved", "approved", "pending", "DECLINED"]

        used_pairs = set()
        for child in available_children:
            parent = random.choice(available_parents)
            if (child, parent) in used_pairs:
                continue
            used_pairs.add((child, parent))
            status = random.choice(statuses)
            await session.execute(text("""
                INSERT INTO household_links
                    (requester_id, target_parent_id, status,
                     decline_reason, message,
                     created_at, updated_at)
                VALUES
                    (:child, :parent, :status,
                     :decline, :msg,
                     :created, :created)
            """), {
                "child": child, "parent": parent, "status": status,
                "decline": "Not recognized as household member" if status == "DECLINED" else None,
                "msg": "Please link my account to my parent's card" if random.choice([True, False]) else None,
                "created": _past(random.randint(1, 120)),
            })
            link_count += 1

        print(f"    Created {link_count} household links")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 13. GROUP HOLDS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM group_holds"))
    gh_count = r.scalar()
    bc_r = await session.execute(text("SELECT id FROM book_clubs"))
    book_club_ids = [row[0] for row in bc_r.fetchall()]
    kit_r = await session.execute(text("SELECT id FROM book_club_kits"))
    kit_ids = [row[0] for row in kit_r.fetchall()]

    if gh_count == 0 and book_club_ids and kit_ids:
        print("  Seeding group_holds...")

        hold_count = 0
        for bc_id in book_club_ids[:4]:
            kit_id = random.choice(kit_ids)
            status = random.choice(["pending", "ready", "fulfilled", "pending"])
            await session.execute(text("""
                INSERT INTO group_holds
                    (book_club_id, kit_id, requested_by_id,
                     status, position_in_queue,
                     requested_at, ready_at, fulfilled_at, expires_at)
                VALUES
                    (:bc, :kit, :req_by,
                     :status, :pos,
                     :req_at, :ready, :fulfilled, :expires)
            """), {
                "bc": bc_id, "kit": kit_id,
                "req_by": random.choice(staff_ids),
                "status": status, "pos": hold_count + 1,
                "req_at": _past(random.randint(5, 60)),
                "ready": _past(random.randint(1, 10)) if status in ("ready", "fulfilled") else None,
                "fulfilled": _past(random.randint(0, 5)) if status == "fulfilled" else None,
                "expires": now + timedelta(days=7) if status == "ready" else None,
            })
            hold_count += 1

        print(f"    Created {hold_count} group holds")
        await session.commit()
    elif gh_count == 0:
        print("  Skipping group_holds — no book_clubs or book_club_kits found")

    # ════════════════════════════════════════════════════════════════
    # 14. BULK CHECKOUTS + ITEMS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM bulk_checkouts"))
    if r.scalar() == 0 and partner_ids:
        print("  Seeding bulk_checkouts and items...")

        bulk_data = [
            ("Mrs. Rivera's 3rd Grade — Spring Reading", "active", "Maria Rivera", "3rd"),
            ("Lincoln Elementary Media Center Refresh", "returned", "James Thompson", "K-5"),
            ("Senior Center Monthly Book Exchange", "active", "Helen Park", None),
            ("Head Start Story Time Collection", "active", "Desiree Cole", "Pre-K"),
        ]
        bulk_ids = []
        for name, status, requestor, grade in bulk_data:
            pid = random.choice(partner_ids)
            total_items = random.randint(10, 30)
            returned = total_items if status == "returned" else 0
            r2 = await session.execute(text("""
                INSERT INTO bulk_checkouts
                    (partner_id, checkout_name, status,
                     requestor_name, requestor_email, requestor_phone,
                     grade_level,
                     checkout_date, due_date, returned_date,
                     total_items, items_returned, items_lost, items_damaged,
                     deposit_required, deposit_amount, deposit_collected,
                     delivery_method, notes, processed_by_id)
                VALUES
                    (:pid, :name, :status,
                     :requestor, :email, :phone,
                     :grade,
                     :co_date, :due_date, :ret_date,
                     :total, :returned, :lost, :damaged,
                     :dep_req, :dep_amt, :dep_col,
                     :delivery, :notes, :processed_by)
                RETURNING id
            """), {
                "pid": pid, "name": name, "status": status,
                "requestor": requestor,
                "email": f"{requestor.split()[0].lower()}@school.edu",
                "phone": f"555-{random.randint(1000, 9999)}",
                "grade": grade,
                "co_date": _past_date(random.randint(10, 60)),
                "due_date": _future_date(random.randint(14, 60)) if status == "active" else _past_date(5),
                "ret_date": _past_date(5) if status == "returned" else None,
                "total": total_items, "returned": returned,
                "lost": 0, "damaged": 0,
                "dep_req": random.choice([True, False]),
                "dep_amt": 50.0 if random.choice([True, False]) else 0.0,
                "dep_col": True,
                "delivery": random.choice(["pickup", "delivery", "visit"]),
                "notes": "Arranged through outreach coordinator.",
                "processed_by": random.choice(staff_ids),
            })
            bulk_ids.append((r2.scalar(), total_items, status))

        # Bulk checkout items
        for bulk_id, total, status in bulk_ids:
            for j in range(min(total, 5)):  # Seed up to 5 items per bulk
                cid = random.choice(catalog_ids)
                item_status = "returned" if status == "returned" else "checked_out"
                await session.execute(text("""
                    INSERT INTO bulk_checkout_items
                        (bulk_checkout_id, barcode, title,
                         status, returned_at, condition_out)
                    VALUES
                        (:bulk_id, :barcode, :title,
                         :status, :returned, :cond)
                """), {
                    "bulk_id": bulk_id,
                    "barcode": f"BULK-{bulk_id}-{j+1:03d}",
                    "title": f"Catalog Item #{cid}",
                    "status": item_status,
                    "returned": _past(random.randint(1, 10)) if item_status == "returned" else None,
                    "cond": "good",
                })

        print(f"    Created {len(bulk_ids)} bulk checkouts")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 15. INSTITUTIONAL CARDS + CHECKOUTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM institutional_cards"))
    if r.scalar() == 0 and partner_ids:
        print("  Seeding institutional_cards and checkouts...")

        inst_data = [
            ("Oakdale Elementary School", "INST-OAK-001", 100, True),
            ("Riverside Middle School", "INST-RMS-001", 75, False),
            ("Sunrise Senior Living", "INST-SSL-001", 50, True),
            ("Community Action Center", "INST-CAC-001", 40, False),
        ]
        inst_card_ids = []
        for i, (name, card_num, limit, exempt) in enumerate(inst_data):
            pid = partner_ids[i % len(partner_ids)]
            r2 = await session.execute(text("""
                INSERT INTO institutional_cards
                    (partner_id, card_number, status, card_name,
                     checkout_limit, hold_limit, loan_period_days, renewal_limit,
                     exempt_from_fines,
                     issued_date, expiry_date,
                     total_checkouts, current_checkouts, current_holds, current_fines,
                     issued_by_id)
                VALUES
                    (:pid, :card_num, 'active', :name,
                     :limit, 25, 28, 2,
                     :exempt,
                     :issued, :expiry,
                     :total, :current, :holds, :fines,
                     :issued_by)
                RETURNING id
            """), {
                "pid": pid, "card_num": card_num, "name": name,
                "limit": limit, "exempt": exempt,
                "issued": _past_date(random.randint(60, 365)),
                "expiry": _future_date(random.randint(180, 365)),
                "total": random.randint(50, 300),
                "current": random.randint(5, 30),
                "holds": random.randint(0, 5),
                "fines": round(random.uniform(0, 10), 2) if not exempt else 0.0,
                "issued_by": random.choice(staff_ids),
            })
            inst_card_ids.append(r2.scalar())

        # Institutional checkouts
        for card_id in inst_card_ids:
            for j in range(random.randint(2, 5)):
                cid = random.choice(catalog_ids)
                co_status = random.choice(["active", "returned", "active"])
                await session.execute(text("""
                    INSERT INTO institutional_checkouts
                        (card_id, barcode, title,
                         checked_out_by_name,
                         checked_out_at, due_date, returned_at,
                         status)
                    VALUES
                        (:card, :barcode, :title,
                         :by_name,
                         :co_at, :due, :ret,
                         :status)
                """), {
                    "card": card_id,
                    "barcode": f"INST-{card_id}-{j+1:03d}",
                    "title": f"Item #{cid}",
                    "by_name": random.choice(["Mrs. Rivera", "Mr. Thompson", "Helen Park", "Staff"]),
                    "co_at": _past(random.randint(5, 30)),
                    "due": now + timedelta(days=random.randint(7, 28)),
                    "ret": _past(random.randint(1, 5)) if co_status == "returned" else None,
                    "status": co_status,
                })

        print(f"    Created {len(inst_card_ids)} institutional cards")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 16. FINE POLICIES + PAYMENT HISTORY + FEE WAIVER ELIGIBILITY
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM fine_policies"))
    if r.scalar() == 0:
        print("  Seeding fine_policies, payment_history, fee_waiver_eligibility...")

        fp_data = [
            ("Standard Book Fine", "Daily overdue fine for standard books", "daily_rate", "book", "0.25", "10.00", 0),
            ("DVD Fine", "Daily overdue fine for DVDs and Blu-ray", "daily_rate", "dvd", "1.00", "25.00", 0),
            ("Children's Material Fine", "Reduced fine for children's materials", "daily_rate", "book", "0.10", "5.00", 24),
            ("High Demand Fine", "Fine for high-demand/new items", "progressive", "book", "0.50", "20.00", 0),
            ("Magazine/Periodical Fine", "Fine for overdue periodicals", "daily_rate", "magazine", "0.25", "5.00", 0),
        ]
        for name, desc, ptype, item_type, per_day, max_cap, grace in fp_data:
            await session.execute(text("""
                INSERT INTO fine_policies
                    (name, description, policy_type,
                     applies_to_item_types, applies_to_user_roles,
                     fine_per_day, progressive_increase_percent,
                     maximum_cap,
                     grace_period_hours,
                     minimum_fine_amount, maximum_daily_fine,
                     is_active,
                     applies_on_weekends, applies_on_holidays,
                     created_by_id, created_at, updated_at)
                VALUES
                    (:name, :desc, :ptype,
                     :item_type, 'all',
                     :per_day, 0.00,
                     :max_cap,
                     :grace,
                     0.00, 50.00,
                     true,
                     true, false,
                     :creator, :created, :created)
            """), {
                "name": name, "desc": desc, "ptype": ptype,
                "item_type": item_type,
                "per_day": Decimal(per_day), "max_cap": Decimal(max_cap),
                "grace": grace,
                "creator": random.choice(staff_ids),
                "created": _past(random.randint(60, 365)),
            })

        # Payment history for existing fines
        if fine_ids:
            for fine_id in fine_ids[:10]:
                user_id = next((f[1] for f in fines_data if f[0] == fine_id), None)
                amt = Decimal(str(round(random.uniform(1, 10), 2)))
                await session.execute(text("""
                    INSERT INTO fine_payment_history
                        (fine_id, user_id, amount, payment_method,
                         receipt_number, processed_by_id,
                         created_at, updated_at)
                    VALUES
                        (:fine_id, :uid, :amt, :method,
                         :receipt, :processed,
                         :created, :created)
                """), {
                    "fine_id": fine_id, "uid": user_id,
                    "amt": amt,
                    "method": random.choice(["cash", "card", "online"]),
                    "receipt": f"FPH-{fine_id}-{random.randint(10000, 99999)}",
                    "processed": random.choice(staff_ids),
                    "created": _past(random.randint(1, 60)),
                })

        # Fee waiver eligibility
        waivers = [
            ("State Court", "state", 125),
            ("County Court", "county", 200),
            ("Federal Court", "federal", 150),
        ]
        for jurisdiction, court_type, fpl in waivers:
            thresholds = json.dumps([
                {"household_size": 1, "annual_income": 18075},
                {"household_size": 2, "annual_income": 24353},
                {"household_size": 3, "annual_income": 30630},
                {"household_size": 4, "annual_income": 36908},
            ])
            auto_elig = json.dumps([
                {"criteria": "Receiving public assistance", "documentation": "Benefit letter"},
                {"criteria": "Income below FPL", "documentation": "Tax return or pay stubs"},
            ])
            await session.execute(text("""
                INSERT INTO fee_waiver_eligibility
                    (jurisdiction, court_type,
                     income_thresholds, fpl_percentage,
                     automatic_eligibility, required_documentation,
                     partial_waiver_available, payment_plan_available,
                     is_active)
                VALUES
                    (:jurisdiction, :court,
                     cast(:thresholds as jsonb), :fpl,
                     cast(:auto as jsonb), cast(:docs as jsonb),
                     true, true,
                     true)
            """), {
                "jurisdiction": jurisdiction, "court": court_type,
                "thresholds": thresholds, "fpl": fpl,
                "auto": auto_elig,
                "docs": json.dumps(["Government-issued ID", "Proof of income", "Benefit verification letter"]),
            })

        print(f"    Created {len(fp_data)} fine policies, {min(len(fine_ids), 10)} payment records, {len(waivers)} fee waivers")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 17. DEPOSIT APPLICATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM deposit_applications"))
    dep_count = r.scalar()
    dep_r = await session.execute(text("SELECT id FROM outreach_deposits"))
    deposit_ids = [row[0] for row in dep_r.fetchall()]

    if dep_count == 0 and deposit_ids:
        print("  Seeding deposit_applications...")
        for dep_id in deposit_ids[:3]:
            await session.execute(text("""
                INSERT INTO deposit_applications
                    (deposit_id, amount, reason,
                     applied_by_id, applied_at, notes)
                VALUES
                    (:dep, :amt, :reason,
                     :applied_by, :applied_at, :notes)
            """), {
                "dep": dep_id,
                "amt": round(random.uniform(5, 25), 2),
                "reason": random.choice(["Lost item replacement", "Damage repair fee", "Late return processing"]),
                "applied_by": random.choice(staff_ids),
                "applied_at": _past(random.randint(1, 60)),
                "notes": "Applied per standard deposit policy.",
            })
        print(f"    Created {min(len(deposit_ids), 3)} deposit applications")
        await session.commit()
    elif dep_count == 0:
        print("  Skipping deposit_applications — no outreach_deposits found")

    # ════════════════════════════════════════════════════════════════
    # 18. TECH ASSISTANCE STAFF + BOOKINGS + SESSION NOTES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM tech_assistance_staff"))
    if r.scalar() == 0:
        print("  Seeding tech assistance (staff, bookings, notes, follow-ups, resources, impact)...")

        # Tech assistance staff
        tech_staff_data = [
            (["email", "smartphone", "computer_basics", "internet_browsing"], "Specializes in helping seniors with basic technology. Patient and thorough.", '{"monday": {"start": "09:00", "end": "17:00"}, "wednesday": {"start": "09:00", "end": "17:00"}, "friday": {"start": "09:00", "end": "13:00"}}'),
            (["resume_building", "job_search_online", "cloud_storage", "video_conferencing"], "Career services specialist. Helps patrons with job applications and remote work tools.", '{"tuesday": {"start": "10:00", "end": "18:00"}, "thursday": {"start": "10:00", "end": "18:00"}}'),
            (["social_media", "online_safety", "password_management", "accessibility_features"], "Digital safety expert. Focuses on online privacy and security.", '{"monday": {"start": "12:00", "end": "20:00"}, "wednesday": {"start": "12:00", "end": "20:00"}, "saturday": {"start": "09:00", "end": "17:00"}}'),
        ]
        tech_staff_ids = []
        for i, (topics, bio, avail) in enumerate(tech_staff_data):
            sid = staff_ids[i % len(staff_ids)]
            topics_literal = "'{" + ",".join(topics) + "}'"
            r2 = await session.execute(text(f"""
                INSERT INTO tech_assistance_staff
                    (staff_id, expertise_topics, max_concurrent_sessions,
                     bio, availability, is_volunteer_coordinator, is_active)
                VALUES
                    (:sid, {topics_literal}::varchar[], 3,
                     :bio, cast(:avail as json), :coord, true)
                RETURNING id
            """), {
                "sid": sid,
                "bio": bio,
                "avail": avail,
                "coord": i == 0,
            })
            tech_staff_ids.append(r2.scalar())

        # Tech bookings
        booking_data = [
            ("email", "beginner", "Need help setting up email on my new phone", "confirmed"),
            ("smartphone", "beginner", "Want to learn how to use my iPhone camera and photos", "completed"),
            ("resume_building", "intermediate", "Updating my resume for job applications", "completed"),
            ("online_safety", "beginner", "Keep getting scam emails. Need to learn how to spot them", "completed"),
            ("video_conferencing", "beginner", "Doctor wants me to do telehealth visits. Need help with Zoom", "pending"),
            ("computer_basics", "beginner", "Never used a computer before. Want to learn basics", "confirmed"),
            ("library_website", "intermediate", "How to use the ebook and audiobook apps", "completed"),
            ("job_search_online", "intermediate", "Need to apply for jobs online but not sure how", "completed"),
            ("password_management", "beginner", "I forget all my passwords. Need a system", "no_show"),
            ("cloud_storage", "intermediate", "Want to back up my photos to the cloud", "cancelled"),
        ]
        booking_ids = []
        for topic, skill, desc, status in booking_data:
            pid = random.choice(patron_ids)
            staff_id = random.choice(tech_staff_ids)
            start = _past(random.randint(1, 60))
            end = start + timedelta(hours=1)
            r2 = await session.execute(text("""
                INSERT INTO tech_assistance_bookings
                    (patron_id, start_time, end_time,
                     topic, skill_level,
                     description, status,
                     assigned_staff_id,
                     checked_in_at, session_start_actual, session_end_actual)
                VALUES
                    (:pid, :start, :end,
                     :topic, :skill,
                     :desc, :status,
                     :staff,
                     :checkin, :sess_start, :sess_end)
                RETURNING id
            """), {
                "pid": pid, "start": start, "end": end,
                "topic": topic, "skill": skill,
                "desc": desc, "status": status,
                "staff": staff_id,
                "checkin": start if status in ("completed", "confirmed") else None,
                "sess_start": start if status == "completed" else None,
                "sess_end": end if status == "completed" else None,
            })
            booking_ids.append((r2.scalar(), status))

        # Session notes for completed bookings
        for bid, status in booking_ids:
            if status == "completed":
                await session.execute(text("""
                    INSERT INTO tech_session_notes
                        (booking_id, content,
                         topics_covered, concepts_taught,
                         patron_comprehension_level,
                         recommendations, challenges, created_by)
                    VALUES
                        (:bid, :content,
                         '{"email setup","basic navigation"}'::varchar[],
                         '{"menu navigation","settings access"}'::varchar[],
                         :comprehension,
                         :recommendations, :challenges, :creator)
                """), {
                    "bid": bid,
                    "content": random.choice([
                        "Patron learned to navigate email and send messages. Needs practice with attachments.",
                        "Covered basic smartphone features. Patron is comfortable with calls and texts now.",
                        "Resume formatted in Word. Patron saved to USB drive and email. Discussed job sites.",
                        "Reviewed phishing red flags. Set up spam filters. Patron feels more confident.",
                    ]),
                    "comprehension": random.randint(2, 5),
                    "recommendations": "Schedule follow-up in 2 weeks to review progress.",
                    "challenges": random.choice(["Vision difficulty with small text — increased font size", "Needed extra time for motor skills", None]),
                    "creator": random.choice(staff_ids),
                })

        # Follow-up bookings
        completed_bookings = [bid for bid, st in booking_ids if st == "completed"]
        for bid in completed_bookings[:3]:
            await session.execute(text("""
                INSERT INTO tech_follow_up_bookings
                    (original_booking_id, status,
                     suggested_topics,
                     reason, suggested_timing, patron_agreed)
                VALUES
                    (:bid, :status,
                     '{"review previous material","new topic introduction"}'::varchar[],
                     :reason, :timing, :agreed)
            """), {
                "bid": bid,
                "status": random.choice(["scheduled", "pending", "completed"]),
                "reason": "Patron needs reinforcement of concepts from first session.",
                "timing": random.choice(["1 week", "2 weeks"]),
                "agreed": True,
            })

        # Resource handouts
        for bid in completed_bookings[:4]:
            await session.execute(text("""
                INSERT INTO tech_resource_handouts
                    (booking_id, title, description,
                     resource_type, topics,
                     sent_to_patron, sent_method)
                VALUES
                    (:bid, :title, :desc,
                     :rtype, '{"email","basics"}'::varchar[],
                     :sent, :method)
            """), {
                "bid": bid,
                "title": random.choice(["Email Basics Cheat Sheet", "Smartphone Quick Reference", "Online Safety Tips", "Resume Writing Guide"]),
                "desc": "Printed handout with step-by-step instructions.",
                "rtype": random.choice(["PDF guide", "printed handout"]),
                "sent": True,
                "method": "printed",
            })

        # Skill impact tracking
        for bid in completed_bookings:
            await session.execute(text("""
                INSERT INTO tech_skill_impact
                    (booking_id, skills_learned,
                     confidence_before, confidence_after,
                     independence_level, goal_achieved,
                     satisfaction_rating, patron_feedback,
                     interested_in_future_sessions)
                VALUES
                    (:bid, '{"email navigation","composing messages"}'::varchar[],
                     :before, :after,
                     :indep, :achieved,
                     :rating, :feedback,
                     :future)
            """), {
                "bid": bid,
                "before": random.randint(1, 2),
                "after": random.randint(3, 5),
                "indep": random.randint(2, 4),
                "achieved": random.choice([True, True, False]),
                "rating": random.randint(3, 5),
                "feedback": random.choice([
                    "Very helpful! I feel much more confident now.",
                    "Thank you for being so patient with me.",
                    "I learned more in one hour than I expected!",
                    "Great session. I'll definitely come back.",
                ]),
                "future": True,
            })

        print(f"    Created {len(tech_staff_ids)} tech staff, {len(booking_ids)} bookings")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 19. TECH VOLUNTEER TUTORS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM tech_volunteer_tutors"))
    if r.scalar() == 0:
        print("  Seeding tech_volunteer_tutors...")

        # Get tech_assistance_staff IDs for coordinator
        tas_r = await session.execute(text("SELECT id FROM tech_assistance_staff LIMIT 1"))
        tas_row = tas_r.fetchone()
        coordinator_id = tas_row[0] if tas_row else None

        tutor_data = [
            (["email", "smartphone", "tablet"], "Retired IT professional. 30 years experience.", "approved"),
            (["computer_basics", "internet_browsing"], "College student studying computer science.", "approved"),
            (["social_media", "online_safety"], "Former teacher with digital literacy background.", "approved"),
            (["resume_building", "job_search_online"], "HR professional volunteering on weekends.", "pending"),
        ]
        tutor_pool = random.sample(patron_ids, min(len(patron_ids), 4))
        for i, (topics, bg, status) in enumerate(tutor_data):
            vid = tutor_pool[i]
            topics_literal = "'{" + ",".join(topics) + "}'"
            await session.execute(text(f"""
                INSERT INTO tech_volunteer_tutors
                    (volunteer_id, expertise_topics,
                     background, assigned_coordinator_id,
                     is_active, approval_status,
                     has_background_check, training_completed,
                     total_sessions, average_rating)
                VALUES
                    (:vid, {topics_literal}::varchar[],
                     :bg, :coord,
                     :active, :status,
                     :bg_check, :trained,
                     :sessions, :rating)
            """), {
                "vid": vid, "bg": bg,
                "coord": coordinator_id,
                "active": status == "approved",
                "status": status,
                "bg_check": status == "approved",
                "trained": status == "approved",
                "sessions": random.randint(5, 25) if status == "approved" else 0,
                "rating": round(random.uniform(4.0, 5.0), 1) if status == "approved" else 0.0,
            })

        print(f"    Created {len(tutor_data)} tech volunteer tutors")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 20. LIBRARIAN CONSULTATION SLOTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM librarian_consultation_slots"))
    if r.scalar() == 0 and partner_ids:
        print("  Seeding librarian_consultation_slots...")

        consult_data = [
            ("Curriculum Alignment Planning", "curriculum-planning", "Review upcoming units and select supporting library materials.", 60),
            ("Reading Level Assessment", "reading-strategies", "Discuss student reading levels and recommend appropriate materials.", 30),
            ("Research Project Support", "assessment", "Plan research project resources and database access for students.", 45),
            ("Summer Reading Program Design", "program-design", "Collaborate on summer reading program for elementary students.", 60),
            ("Digital Literacy Integration", "curriculum-planning", "Integrate digital resources into classroom instruction.", 30),
            ("Book Fair Planning", "program-design", "Plan and organize the annual school book fair.", 45),
        ]
        for title, ctype, desc, duration in consult_data:
            pid = random.choice(partner_ids)
            lib_id = random.choice(staff_ids)
            booked = random.choice([True, True, False])
            await session.execute(text("""
                INSERT INTO librarian_consultation_slots
                    (partner_id, librarian_id, title, description,
                     consultation_type, scheduled_date,
                     start_time, end_time, duration_minutes,
                     max_participants, current_participants,
                     is_booked, is_completed, created_at)
                VALUES
                    (:pid, :lib, :title, :desc,
                     :ctype, :sched,
                     :start, :end, :dur,
                     10, :participants,
                     :booked, :completed, :created)
            """), {
                "pid": pid, "lib": lib_id,
                "title": title, "desc": desc,
                "ctype": ctype,
                "sched": _future_date(random.randint(1, 30)) if not booked else _past_date(random.randint(1, 30)),
                "start": f"{random.randint(9, 15):02d}:00",
                "end": f"{random.randint(10, 16):02d}:00",
                "dur": duration,
                "participants": random.randint(1, 5) if booked else 0,
                "booked": booked,
                "completed": booked and random.choice([True, False]),
                "created": _past(random.randint(5, 60)),
            })

        print(f"    Created {len(consult_data)} consultation slots")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 21. LIBRARY CARD APPLICATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM library_card_applications"))
    if r.scalar() == 0:
        print("  Seeding library_card_applications...")

        applicants = [
            ("Emily", "Chen", "emily.chen@email.com", "555-2001", "123 Maple St", "Oakdale", "IN", "46001", "approved"),
            ("Marcus", "Johnson", "marcus.j@email.com", "555-2002", "456 Oak Ave", "Oakdale", "IN", "46001", "approved"),
            ("Sofia", "Rodriguez", "sofia.r@email.com", "555-2003", "789 Pine Rd", "Oakdale", "IN", "46002", "approved"),
            ("Aiden", "Patel", "aiden.p@email.com", "555-2004", "321 Elm St", "Oakdale", "IN", "46002", "pending"),
            ("Olivia", "Williams", "olivia.w@email.com", "555-2005", "654 Birch Ln", "Oakdale", "IN", "46001", "approved"),
            ("James", "Lee", "james.l@email.com", "555-2006", "147 Willow Ct", "Oakdale", "IN", "46003", "pending"),
            ("Ava", "Brown", "ava.brown@email.com", "555-2007", "258 Cedar Dr", "Oakdale", "IN", "46001", "approved"),
            ("Noah", "Garcia", "noah.g@email.com", "555-2008", "369 Spruce Way", "Riverside", "IN", "46004", "denied"),
            ("Isabella", "Kim", "isabella.k@email.com", "555-2009", "741 Ash Blvd", "Oakdale", "IN", "46002", "approved"),
            ("Liam", "Davis", "liam.d@email.com", "555-2010", "852 Walnut Ave", "Oakdale", "IN", "46001", "approved"),
            ("Mia", "Wilson", "mia.w@email.com", None, "963 Cherry St", "Oakdale", "IN", "46003", "under_review"),
            ("Ethan", "Martinez", "ethan.m@email.com", "555-2012", "174 Poplar Dr", "Oakdale", "IN", "46002", "approved"),
            ("Charlotte", "Anderson", "charlotte.a@email.com", "555-2013", "285 Birch Way", "Greenfield", "IN", "46005", "denied"),
            ("Benjamin", "Taylor", "ben.t@email.com", "555-2014", "396 Hickory Ln", "Oakdale", "IN", "46001", "pending"),
            ("Amelia", "Thomas", "amelia.t@email.com", "555-2015", "507 Sycamore Ct", "Oakdale", "IN", "46003", "approved"),
        ]

        for i, (first, last, email, phone, addr, city, state, zip_code, status) in enumerate(applicants):
            reviewer = random.choice(staff_ids) if status in ("approved", "denied") else None
            card_num = f"L30-{2026}-{i+1:05d}" if status == "approved" else None
            await session.execute(text("""
                INSERT INTO library_card_applications
                    (first_name, last_name, email, phone,
                     address_line1, city, state, zip_code,
                     id_type, id_number_last4,
                     status, submitted_at,
                     reviewed_by_id, reviewed_at, review_notes,
                     denial_reason, assigned_card_number)
                VALUES
                    (:first, :last, :email, :phone,
                     :addr, :city, :state, :zip,
                     :id_type, :id_last4,
                     :status, :submitted,
                     :reviewer, :reviewed, :notes,
                     :denial, :card_num)
            """), {
                "first": first, "last": last, "email": email, "phone": phone,
                "addr": addr, "city": city, "state": state, "zip": zip_code,
                "id_type": random.choice(["driver_license", "passport", "utility_bill"]),
                "id_last4": f"{random.randint(1000, 9999)}",
                "status": status,
                "submitted": _past(random.randint(1, 90)),
                "reviewer": reviewer,
                "reviewed": _past(random.randint(0, 10)) if reviewer else None,
                "notes": "Verified ID and address." if status == "approved" else None,
                "denial": "Address outside service area" if status == "denied" else None,
                "card_num": card_num,
            })

        print(f"    Created {len(applicants)} library card applications")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 22. COLLECTIBLE CARDS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM collectible_cards"))
    if r.scalar() == 0 and indie_data and dao_ids:
        print("  Seeding collectible_cards...")

        card_count = 0
        for ebook_id, title in indie_data:
            owner = random.choice(patron_ids)
            order = random.choice(dao_ids)
            edition = random.choice(["STANDARD", "STANDARD", "LIMITED", "SIGNED"])
            serial = f"CC-{ebook_id:04d}-{card_count+1:04d}"
            await session.execute(text("""
                INSERT INTO collectible_cards
                    (ebook_id, owner_id, order_id, serial_number,
                     edition, is_signed, print_count,
                     cached_title, cached_author_name,
                     qr_url, issued_at, created_at)
                VALUES
                    (:ebook, :owner, :order, :serial,
                     :edition, :signed, :prints,
                     :title, :author,
                     :qr, :issued, :created)
            """), {
                "ebook": ebook_id, "owner": owner, "order": order,
                "serial": serial,
                "edition": edition,
                "signed": edition == "SIGNED",
                "prints": random.randint(0, 3),
                "title": title,
                "author": random.choice(["Amara Osei", "Elena Vargas", "Devon Blake", "Priya Sharma"]),
                "qr": f"https://l30.org/cards/{serial}",
                "issued": _past(random.randint(1, 60)),
                "created": _past(random.randint(1, 60)),
            })
            card_count += 1

        print(f"    Created {card_count} collectible cards")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # FIX SEQUENCES
    # ════════════════════════════════════════════════════════════════
    seq_tables = [
        "homebound_applications", "homebound_enrollments", "homebound_item_requests",
        "delivery_requests", "delivery_routes", "deliveries", "delivery_items",
        "delivery_feedback",
        "patron_accounts", "patron_transactions", "payment_plans",
        "patron_messages", "patron_statistics",
        "patron_groups", "patron_group_members",
        "patron_boundaries", "boundary_policies", "boundary_templates",
        "parent_guardian_consents", "coppa_compliance",
        "patron_chatbot_context", "patron_medical_info", "patron_onboarding_progress",
        "household_links",
        "group_holds",
        "bulk_checkouts", "bulk_checkout_items",
        "institutional_cards", "institutional_checkouts",
        "fine_policies", "fine_payment_history", "fee_waiver_eligibility",
        "deposit_applications",
        "tech_assistance_bookings", "tech_assistance_staff", "tech_session_notes",
        "tech_follow_up_bookings", "tech_resource_handouts", "tech_skill_impact",
        "tech_volunteer_tutors",
        "librarian_consultation_slots",
        "library_card_applications",
        "collectible_cards",
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
    print("  Patron services seeding complete!")
    return True
