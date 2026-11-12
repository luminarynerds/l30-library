# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import random
import datetime as _dt
from datetime import datetime, timedelta, timezone, date, time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from ..core.encryption import encrypt_pii

utc = timezone.utc


def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago)


def _past_date(days_ago: int) -> date:
    return (datetime.now(utc) - timedelta(days=days_ago)).date()


def _future_date(days_ahead: int) -> date:
    return (datetime.now(utc) + timedelta(days=days_ahead)).date()


def _future(days_ahead: int) -> datetime:
    return datetime.now(utc) + timedelta(days=days_ahead)


async def seed_batch_makerspace(session: AsyncSession) -> bool:
    now = datetime.now(utc)

    # ── Reusable IDs ──────────────────────────────────────────────────
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] in ("patron", "child")]
    all_ids = [u[0] for u in users]

    branch_r = await session.execute(text("SELECT id FROM branches"))
    branch_ids = [r[0] for r in branch_r.fetchall()]

    equip_r = await session.execute(text("SELECT id FROM equipment"))
    equipment_ids = [r[0] for r in equip_r.fetchall()]

    catalog_r = await session.execute(text("SELECT id FROM catalog_items"))
    catalog_ids = [r[0] for r in catalog_r.fetchall()]

    item_copy_r = await session.execute(text("SELECT id FROM item_copies"))
    item_copy_ids = [r[0] for r in item_copy_r.fetchall()]

    checkout_r = await session.execute(text("SELECT id FROM checkouts"))
    checkout_ids = [r[0] for r in checkout_r.fetchall()]

    # Makerspace resources
    res_r = await session.execute(text("SELECT id FROM makerspace_resources"))
    resource_ids = [r[0] for r in res_r.fetchall()]

    # Cert types
    cert_type_r = await session.execute(text("SELECT id FROM makerspace_certification_types"))
    cert_type_ids = [r[0] for r in cert_type_r.fetchall()]

    # Workshops
    ws_r = await session.execute(text("SELECT id FROM makerspace_workshops"))
    workshop_ids = [r[0] for r in ws_r.fetchall()]

    # Book clubs
    bc_r = await session.execute(text("SELECT id FROM book_clubs"))
    book_club_ids = [r[0] for r in bc_r.fetchall()]

    # Comic series
    cs_r = await session.execute(text("SELECT id FROM comic_series"))
    comic_series_ids = [r[0] for r in cs_r.fetchall()]

    # Bibframe works
    bw_r = await session.execute(text("SELECT id FROM bibframe_works"))
    bibframe_work_ids = [r[0] for r in bw_r.fetchall()]

    # ══════════════════════════════════════════════════════════════════
    # 1. MAKERSPACE CONSUMABLES
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM makerspace_consumables"))
    if r.scalar() == 0:
        print("  Seeding makerspace_consumables...")
        consumables = [
            (
                "PLA Filament - White",
                "Standard white PLA 1.75mm filament",
                "FIL-W-001",
                "filament",
                "PLA",
                "White",
                1.75,
                "grams",
                2500.00,
                200.00,
                5000.00,
                0.0250,
                0.0400,
                "MatterHackers",
            ),
            (
                "PLA Filament - Black",
                "Standard black PLA 1.75mm filament",
                "FIL-B-001",
                "filament",
                "PLA",
                "Black",
                1.75,
                "grams",
                1800.00,
                200.00,
                5000.00,
                0.0250,
                0.0400,
                "MatterHackers",
            ),
            (
                "PLA Filament - Red",
                "Standard red PLA 1.75mm filament",
                "FIL-R-001",
                "filament",
                "PLA",
                "Red",
                1.75,
                "grams",
                900.00,
                200.00,
                3000.00,
                0.0280,
                0.0450,
                "MatterHackers",
            ),
            (
                "PETG Filament - Clear",
                "PETG 1.75mm translucent filament",
                "FIL-PETG-001",
                "filament",
                "PETG",
                "Clear",
                1.75,
                "grams",
                1200.00,
                200.00,
                3000.00,
                0.0350,
                0.0550,
                "Prusa Research",
            ),
            (
                "Adhesive Vinyl - Assorted",
                "Oracal 651 permanent adhesive vinyl sheets",
                "VIN-001",
                "vinyl",
                None,
                "Assorted",
                None,
                "sheets",
                150.00,
                25.00,
                200.00,
                0.7500,
                1.5000,
                "Specialty Graphics",
            ),
            (
                "Heat Transfer Vinyl - White",
                "Siser EasyWeed HTV for garment decoration",
                "HTV-W-001",
                "vinyl",
                None,
                "White",
                None,
                "sheets",
                80.00,
                15.00,
                100.00,
                1.2000,
                2.0000,
                "Specialty Graphics",
            ),
            (
                "Cotton Fabric - Assorted",
                "Pre-cut cotton fabric for sewing projects",
                "FAB-001",
                "fabric",
                None,
                "Assorted",
                None,
                "meters",
                25.00,
                5.00,
                30.00,
                3.5000,
                5.0000,
                "Joann Fabrics",
            ),
            (
                "Resin - Standard Grey",
                "Water-washable photopolymer resin for SLA printing",
                "RES-G-001",
                "resin",
                None,
                "Grey",
                None,
                "milliliters",
                3500.00,
                500.00,
                5000.00,
                0.0450,
                0.0750,
                "Elegoo",
            ),
            (
                "Solder Wire - Lead-free",
                "Sn99.3Cu0.7 lead-free solder 0.8mm",
                "SOL-001",
                "electronics",
                None,
                None,
                None,
                "grams",
                400.00,
                50.00,
                500.00,
                0.0800,
                0.0000,
                "Kester",
            ),
            (
                "Laser Engraving Wood Blanks",
                "3mm Baltic birch plywood blanks 12x12 inch",
                "LAS-W-001",
                "wood",
                None,
                "Natural",
                None,
                "pieces",
                45.00,
                10.00,
                50.00,
                1.2500,
                2.0000,
                "Woodpeckers",
            ),
        ]
        for (
            name,
            desc,
            sku,
            cat,
            mat,
            color,
            dia,
            unit,
            qty,
            reorder_thresh,
            reorder_qty,
            cost,
            price,
            supplier,
        ) in consumables:
            params = {
                "name": name,
                "desc": desc,
                "sku": sku,
                "cat": cat,
                "mat": mat,
                "color": color,
                "dia": dia,
                "unit": unit,
                "qty": qty,
                "reorder_thresh": reorder_thresh,
                "reorder_qty": reorder_qty,
                "cost": cost,
                "price": price,
                "supplier": supplier,
            }
            await session.execute(
                text("""
                INSERT INTO makerspace_consumables
                    (name, description, sku, category, material_type, color, diameter_mm,
                     unit, quantity_in_stock, reorder_threshold, reorder_quantity,
                     cost_per_unit, price_per_unit, supplier_name, is_active)
                VALUES (:name, :desc, :sku, :cat, :mat, :color, :dia,
                        :unit, :qty, :reorder_thresh, :reorder_qty,
                        :cost, :price, :supplier, true)
            """),
                params,
            )
        print(f"    Created {len(consumables)} consumables")
        await session.commit()

    # Get consumable IDs
    cons_r = await session.execute(text("SELECT id FROM makerspace_consumables"))
    consumable_ids = [r[0] for r in cons_r.fetchall()]

    # ══════════════════════════════════════════════════════════════════
    # 1b. MAKERSPACE CONSUMABLE USAGE
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM makerspace_consumable_usage"))
    if r.scalar() == 0 and consumable_ids and resource_ids:
        print("  Seeding makerspace_consumable_usage...")
        count = 0
        for _ in range(15):
            cid = random.choice(consumable_ids)
            qty = round(random.uniform(5.0, 200.0), 2)
            cost = round(qty * random.uniform(0.02, 0.10), 2)
            await session.execute(
                text("""
                INSERT INTO makerspace_consumable_usage
                    (consumable_id, resource_id, quantity_used, cost, recorded_by_id)
                VALUES (:cid, :rid, :qty, :cost, :staff)
            """),
                {
                    "cid": cid,
                    "rid": random.choice(resource_ids),
                    "qty": qty,
                    "cost": cost,
                    "staff": random.choice(staff_ids),
                },
            )
            count += 1
        print(f"    Created {count} consumable usage records")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 2. MAKERSPACE CERTIFICATIONS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM makerspace_certifications"))
    if r.scalar() == 0 and cert_type_ids:
        print("  Seeding makerspace_certifications...")
        count = 0
        used = set()
        for uid in random.sample(patron_ids, min(len(patron_ids), 25)):
            for ctid in random.sample(cert_type_ids, min(len(cert_type_ids), random.randint(1, 3))):
                if (uid, ctid) in used:
                    continue
                used.add((uid, ctid))
                status = random.choice(["active", "active", "active", "expired", "pending"])
                certified_at = _past(random.randint(10, 300)) if status != "pending" else None
                expires_at = (
                    _future(random.randint(30, 365))
                    if status == "active"
                    else (_past(random.randint(1, 60)) if status == "expired" else None)
                )
                score = random.randint(75, 100) if status != "pending" else None
                await session.execute(
                    text("""
                    INSERT INTO makerspace_certifications
                        (user_id, certification_type_id, status, training_completed_at,
                         quiz_score, quiz_attempts, certified_at, expires_at,
                         certified_by_id, renewal_count, notes)
                    VALUES (:uid, :ctid, :status, :trained, :score, :attempts,
                            :certified, :expires, :certifier, :renewals, :notes)
                """),
                    {
                        "uid": uid,
                        "ctid": ctid,
                        "status": status,
                        "trained": certified_at,
                        "score": score,
                        "attempts": random.randint(1, 2) if score else 0,
                        "certified": certified_at,
                        "expires": expires_at,
                        "certifier": random.choice(staff_ids) if status != "pending" else None,
                        "renewals": random.randint(0, 2) if status == "active" else 0,
                        "notes": None,
                    },
                )
                count += 1
        print(f"    Created {count} certifications")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 3. MAKERSPACE JOBS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM makerspace_jobs"))
    if r.scalar() == 0 and resource_ids:
        print("  Seeding makerspace_jobs...")
        jobs = [
            (
                "MJ-2026-001",
                "Phone Stand",
                "Ergonomic phone stand for desk",
                "PLA",
                "White",
                15,
                0.20,
                True,
                "completed",
                45,
                30.5,
            ),
            (
                "MJ-2026-002",
                "Bookmark Set",
                "Custom bookmarks with library logo",
                "PLA",
                "Red",
                10,
                0.20,
                False,
                "picked_up",
                60,
                18.2,
            ),
            (
                "MJ-2026-003",
                "Gear Train Demo",
                "Working gear mechanism for STEM demo",
                "PETG",
                "Clear",
                25,
                0.16,
                True,
                "completed",
                120,
                85.0,
            ),
            (
                "MJ-2026-004",
                "Plant Pot",
                "Self-watering planter insert",
                "PLA",
                "Black",
                20,
                0.20,
                False,
                "in_progress",
                90,
                55.0,
            ),
            (
                "MJ-2026-005",
                "Cable Organizer",
                "Desk cable management clip set",
                "PLA",
                "Black",
                10,
                0.20,
                False,
                "queued",
                30,
                12.0,
            ),
            (
                "MJ-2026-006",
                "Dice Tower",
                "Tabletop gaming dice tower",
                "PLA",
                "White",
                20,
                0.20,
                True,
                "ready_pickup",
                75,
                42.0,
            ),
            (
                "MJ-2026-007",
                "Cookie Cutter Set",
                "Library-themed cookie cutters",
                "PLA",
                "Red",
                10,
                0.20,
                False,
                "completed",
                45,
                22.0,
            ),
            (
                "MJ-2026-008",
                "Name Badge Holder",
                "Staff badge holder prototype",
                "PLA",
                "Black",
                5,
                0.28,
                False,
                "completed",
                15,
                8.0,
            ),
            (
                "MJ-2026-009",
                "Lithophane Frame",
                "Photo lithophane with stand",
                "PLA",
                "White",
                10,
                0.12,
                False,
                "completed",
                90,
                35.0,
            ),
            (
                "MJ-2026-010",
                "Replacement Knob",
                "Drawer knob for children's desk",
                "PETG",
                "Black",
                15,
                0.20,
                False,
                "picked_up",
                20,
                10.0,
            ),
            (
                "MJ-2026-011",
                "Board Game Insert",
                "Custom organizer for Catan",
                "PLA",
                "Black",
                20,
                0.20,
                True,
                "approved",
                180,
                95.0,
            ),
            (
                "MJ-2026-012",
                "Keychain Batch",
                "50 library keychain giveaways",
                "PLA",
                "Red",
                10,
                0.28,
                False,
                "in_progress",
                240,
                150.0,
            ),
            (
                "MJ-2026-013",
                "Braille Label Set",
                "Tactile shelf labels for accessibility",
                "PLA",
                "White",
                5,
                0.16,
                False,
                "completed",
                60,
                20.0,
            ),
            (
                "MJ-2026-014",
                "Telescope Adapter",
                "Phone-to-telescope adapter ring",
                "PETG",
                "Black",
                15,
                0.20,
                False,
                "submitted",
                30,
                15.0,
            ),
            (
                "MJ-2026-015",
                "Display Stand",
                "Book display easel for new arrivals",
                "PLA",
                "White",
                15,
                0.20,
                False,
                "pending_review",
                40,
                25.0,
            ),
            (
                "MJ-2026-016",
                "Seed Library Dividers",
                "Labeled dividers for seed packets",
                "PLA",
                "Black",
                5,
                0.28,
                False,
                "completed",
                35,
                18.0,
            ),
            (
                "MJ-2026-017",
                "Cat Toy (Ernie)",
                "Mouse-shaped toy for library cat",
                "PLA",
                "Red",
                10,
                0.20,
                False,
                "picked_up",
                15,
                6.0,
            ),
            (
                "MJ-2026-018",
                "ADA Door Sign",
                "Tactile room sign prototype",
                "PLA",
                "White",
                10,
                0.12,
                False,
                "failed",
                45,
                22.0,
            ),
        ]
        for jn, name, desc, mat, color, infill, layer, supports, status, est_min, est_grams in jobs:
            cost = round(est_grams * 0.04, 2)
            await session.execute(
                text("""
                INSERT INTO makerspace_jobs
                    (job_number, user_id, resource_id, status, priority,
                     project_name, project_description, material_type, material_color,
                     infill_percentage, layer_height, supports_needed,
                     estimated_print_time_minutes, estimated_material_grams,
                     estimated_cost, material_cost, machine_time_cost, payment_status,
                     created_at, updated_at)
                VALUES (:jn, :uid, :rid, :status, 'normal',
                        :name, :desc, :mat, :color,
                        :infill, :layer, :supports,
                        :est_min, :est_grams,
                        :cost, :cost, :mach_cost, 'paid',
                        :created, :created)
            """),
                {
                    "jn": jn,
                    "uid": random.choice(patron_ids),
                    "rid": random.choice(resource_ids),
                    "status": status,
                    "name": name,
                    "desc": desc,
                    "mat": mat,
                    "color": color,
                    "infill": infill,
                    "layer": layer,
                    "supports": supports,
                    "est_min": est_min,
                    "est_grams": est_grams,
                    "cost": cost,
                    "mach_cost": round(cost * 0.5, 2),
                    "created": _past(random.randint(1, 90)),
                },
            )
        print(f"    Created {len(jobs)} makerspace jobs")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 4. MAKERSPACE MAINTENANCE
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM makerspace_maintenance"))
    if r.scalar() == 0 and resource_ids:
        print("  Seeding makerspace_maintenance...")
        maint_data = [
            (
                "Quarterly nozzle replacement",
                "preventive",
                "completed",
                "Replaced 0.4mm brass nozzle on Ender 3 Pro",
            ),
            (
                "Laser alignment check",
                "calibration",
                "completed",
                "Mirrors cleaned and realigned; power output verified at 39W",
            ),
            (
                "Vinyl cutter blade change",
                "corrective",
                "completed",
                "Blade dulled; replaced with 45-degree blade",
            ),
            (
                "3D printer bed leveling",
                "calibration",
                "completed",
                "Auto-leveled and verified with test print",
            ),
            (
                "Sewing machine service",
                "preventive",
                "completed",
                "Oiled, cleaned bobbin case, checked tension",
            ),
            (
                "Laser tube inspection",
                "preventive",
                "scheduled",
                "Annual laser tube inspection due",
            ),
            (
                "Soldering station tip replacement",
                "corrective",
                "in_progress",
                "Tip oxidized; replacing with chisel tip",
            ),
            (
                "CNC spindle lubrication",
                "preventive",
                "scheduled",
                "Monthly spindle bearing lubrication",
            ),
            (
                "Embroidery machine needle swap",
                "corrective",
                "completed",
                "Replaced bent needle, tested on scrap",
            ),
            (
                "Recording booth sound check",
                "calibration",
                "completed",
                "Checked mic levels and sound isolation",
            ),
        ]
        for title, m_type, status, desc in maint_data:
            sched = (
                _past_date(random.randint(1, 90))
                if status == "completed"
                else _future_date(random.randint(1, 30))
            )
            completed = _past(random.randint(1, 60)) if status == "completed" else None
            await session.execute(
                text("""
                INSERT INTO makerspace_maintenance
                    (resource_id, maintenance_type, status, scheduled_date,
                     scheduled_by_id, title, description,
                     completed_at, performed_by_id,
                     parts_cost, labor_hours, notes)
                VALUES (:rid, :mtype, :status, :sched,
                        :sched_by, :title, :desc,
                        :completed, :performer,
                        :parts, :labor, NULL)
            """),
                {
                    "rid": random.choice(resource_ids),
                    "mtype": m_type,
                    "status": status,
                    "sched": sched,
                    "sched_by": random.choice(staff_ids),
                    "title": title,
                    "desc": desc,
                    "completed": completed,
                    "performer": random.choice(staff_ids) if status == "completed" else None,
                    "parts": round(random.uniform(0, 45), 2) if status == "completed" else 0,
                    "labor": round(random.uniform(0.5, 3.0), 2) if status == "completed" else 0,
                },
            )
        print(f"    Created {len(maint_data)} makerspace maintenance records")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 5. MAKERSPACE PAYMENTS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM makerspace_payments"))
    if r.scalar() == 0:
        print("  Seeding makerspace_payments...")
        count = 0
        for i in range(15):
            amt = round(random.uniform(1.50, 35.00), 2)
            method = random.choice(["cash", "card", "card", "card", "account_credit"])
            status = random.choice(["paid", "paid", "paid", "paid", "waived", "refunded"])
            await session.execute(
                text("""
                INSERT INTO makerspace_payments
                    (user_id, amount, payment_method, status,
                     receipt_number, machine_time_fee, consumables_fee, setup_fee,
                     refund_amount, processed_by_id, notes)
                VALUES (:uid, :amt, :method, :status,
                        :receipt, :machine, :consum, :setup,
                        :refund, :staff, :notes)
            """),
                {
                    "uid": random.choice(patron_ids),
                    "amt": amt,
                    "method": method,
                    "status": status,
                    "receipt": f"RCP-{2026}-{1000 + i}",
                    "machine": round(amt * 0.6, 2),
                    "consum": round(amt * 0.3, 2),
                    "setup": round(amt * 0.1, 2),
                    "refund": amt if status == "refunded" else 0,
                    "staff": random.choice(staff_ids),
                    "notes": None,
                },
            )
            count += 1
        print(f"    Created {count} payments")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 6. MAKERSPACE SAFETY INCIDENTS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM makerspace_safety_incidents"))
    if r.scalar() == 0 and resource_ids:
        print("  Seeding makerspace_safety_incidents...")
        incidents = [
            (
                "SI-2026-001",
                "minor",
                "Minor burn from soldering iron",
                "Patron touched soldering iron tip briefly. Cold water applied immediately. No blistering.",
            ),
            (
                "SI-2026-002",
                "minor",
                "Filament jam spatter",
                "PLA filament jammed and small piece ejected from nozzle. No injury; safety glasses worn as required.",
            ),
            (
                "SI-2026-003",
                "moderate",
                "Paper cut from vinyl cutter",
                "Patron received a small cut from vinyl sheet edge. First aid kit bandage applied. Patron continued work.",
            ),
            (
                "SI-2026-004",
                "minor",
                "Laser cutter smoke alarm trigger",
                "Excess smoke from engraving MDF triggered room smoke detector. Ventilation fan was on low; switched to high. No fire.",
            ),
        ]
        for inc_num, severity, title, desc in incidents:
            await session.execute(
                text("""
                INSERT INTO makerspace_safety_incidents
                    (incident_number, resource_id, reported_by_id, involved_user_id,
                     incident_date, severity, title, description, location,
                     injuries_reported, injury_description, equipment_damage,
                     immediate_action_taken, first_aid_administered,
                     emergency_services_called, follow_up_required,
                     is_resolved, resolved_at, resolved_by_id)
                VALUES (:inc, :rid, :reporter, :involved,
                        :date, :sev, :title, :desc, 'Makerspace',
                        :injuries, :injury_desc, false,
                        :action, :first_aid,
                        false, false,
                        true, :resolved, :resolver)
            """),
                {
                    "inc": inc_num,
                    "rid": random.choice(resource_ids),
                    "reporter": random.choice(staff_ids),
                    "involved": random.choice(patron_ids),
                    "date": _past(random.randint(5, 180)),
                    "sev": severity,
                    "title": title,
                    "desc": desc,
                    "injuries": severity != "minor" or "burn" in title.lower(),
                    "injury_desc": desc
                    if "burn" in title.lower() or "cut" in title.lower()
                    else None,
                    "action": "Applied first aid. Documented incident."
                    if "burn" in title.lower() or "cut" in title.lower()
                    else "Adjusted equipment settings. Documented incident.",
                    "first_aid": "burn" in title.lower() or "cut" in title.lower(),
                    "resolved": _past(random.randint(1, 170)),
                    "resolver": random.choice(staff_ids),
                },
            )
        print(f"    Created {len(incidents)} safety incidents")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 7. MAKERSPACE WAITLIST
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM makerspace_waitlist"))
    if r.scalar() == 0 and resource_ids:
        print("  Seeding makerspace_waitlist...")
        statuses = [
            "waiting",
            "waiting",
            "waiting",
            "notified",
            "fulfilled",
            "cancelled",
            "expired",
        ]
        count = 0
        for i in range(7):
            st = statuses[i]
            await session.execute(
                text("""
                INSERT INTO makerspace_waitlist
                    (user_id, resource_id, preferred_date, preferred_start_time,
                     flexible_dates, status, position, notify_email, notify_sms, notes)
                VALUES (:uid, :rid, :pdate, :ptime,
                        false, :status, :pos, true, false, :notes)
            """),
                {
                    "uid": random.choice(patron_ids),
                    "rid": random.choice(resource_ids),
                    "pdate": _future_date(random.randint(1, 14)),
                    "ptime": random.choice(["09:00", "10:00", "13:00", "15:00"]),
                    "status": st,
                    "pos": i + 1,
                    "notes": None,
                },
            )
            count += 1
        print(f"    Created {count} waitlist entries")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 8. MAKERSPACE WORKSHOP REGISTRATIONS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM makerspace_workshop_registrations"))
    if r.scalar() == 0 and workshop_ids:
        print("  Seeding makerspace_workshop_registrations...")
        reg_statuses = [
            "registered",
            "confirmed",
            "attended",
            "attended",
            "attended",
            "no_show",
            "cancelled",
        ]
        count = 0
        used = set()
        for wid in workshop_ids:
            num_regs = random.randint(3, 8)
            for _ in range(num_regs):
                uid = random.choice(patron_ids)
                if (wid, uid) in used:
                    continue
                used.add((wid, uid))
                st = random.choice(reg_statuses)
                await session.execute(
                    text("""
                    INSERT INTO makerspace_workshop_registrations
                        (workshop_id, user_id, status, payment_status, amount_paid, refund_issued, notes)
                    VALUES (:wid, :uid, :status, 'paid', :paid, false, NULL)
                """),
                    {
                        "wid": wid,
                        "uid": uid,
                        "status": st,
                        "paid": round(random.uniform(0, 15), 2),
                    },
                )
                count += 1
                if count >= 20:
                    break
            if count >= 20:
                break
        print(f"    Created {count} workshop registrations")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 9. EQUIPMENT CHECKOUTS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM equipment_checkouts"))
    if r.scalar() == 0 and equipment_ids:
        print("  Seeding equipment_checkouts...")
        count = 0
        active_equip = set()  # Track which equipment has an active checkout
        for i in range(20):
            status = random.choice(
                ["returned", "returned", "returned", "returned", "active", "active", "overdue"]
            )
            eid = random.choice(equipment_ids)
            # Only one active/overdue checkout per equipment item (unique partial index)
            if status in ("active", "overdue"):
                if eid in active_equip:
                    status = "returned"
                else:
                    active_equip.add(eid)
            co_date = _past(random.randint(2, 120))
            due = co_date + timedelta(days=7)
            returned = (
                co_date + timedelta(days=random.randint(3, 10)) if status == "returned" else None
            )
            await session.execute(
                text("""
                INSERT INTO equipment_checkouts
                    (equipment_id, user_id, status,
                     checked_out_at, due_date, returned_at,
                     renewal_count, condition_at_checkout, condition_at_return,
                     checked_out_by_id, returned_to_id,
                     fine_amount, fine_paid, deposit_amount, deposit_collected,
                     deposit_refunded,
                     created_at, updated_at)
                VALUES (:eid, :uid, :status,
                        :co, :due, :ret,
                        :renewals, 'good', :ret_cond,
                        :co_by, :ret_by,
                        :fine, :fine_paid, 0, false,
                        false,
                        :co, :co)
            """),
                {
                    "eid": eid,
                    "uid": random.choice(patron_ids),
                    "status": status,
                    "co": co_date,
                    "due": due,
                    "ret": returned,
                    "renewals": random.randint(0, 1),
                    "ret_cond": "good" if status == "returned" else None,
                    "co_by": random.choice(staff_ids),
                    "ret_by": random.choice(staff_ids) if status == "returned" else None,
                    "fine": round(random.uniform(0, 10), 2) if status == "overdue" else 0,
                    "fine_paid": status != "overdue",
                },
            )
            count += 1
        print(f"    Created {count} equipment checkouts")
        await session.commit()

    # Get checkout IDs for equipment
    eco_r = await session.execute(text("SELECT id FROM equipment_checkouts"))
    equip_checkout_ids = [r[0] for r in eco_r.fetchall()]

    # ══════════════════════════════════════════════════════════════════
    # 10. EQUIPMENT AGREEMENTS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM equipment_agreements"))
    if r.scalar() == 0:
        print("  Seeding equipment_agreements...")
        agreement_text = "I accept responsibility for this equipment and agree to return it in good condition by the due date."
        count = 0
        used_users = set()
        for _ in range(10):
            uid = random.choice(patron_ids)
            if uid in used_users:
                continue
            used_users.add(uid)
            status = random.choice(["signed", "signed", "signed", "signed", "expired", "pending"])
            signed = _past(random.randint(5, 200)) if status in ("signed", "expired") else None
            valid_from = signed
            valid_until = signed + timedelta(days=365) if signed else None
            await session.execute(
                text("""
                INSERT INTO equipment_agreements
                    (user_id, agreement_version, status, agreement_text,
                     signature, signed_at, valid_from, valid_until,
                     processed_by_id, created_at, updated_at)
                VALUES (:uid, '1.0', :status, :text,
                        :sig, :signed, :vf, :vu,
                        :staff, :created, :created)
            """),
                {
                    "uid": uid,
                    "status": status,
                    "text": agreement_text,
                    "sig": f"Patron #{uid}" if signed else None,
                    "signed": signed,
                    "vf": valid_from,
                    "vu": valid_until,
                    "staff": random.choice(staff_ids) if signed else None,
                    "created": signed or now,
                },
            )
            count += 1
        print(f"    Created {count} equipment agreements")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 11. EQUIPMENT MAINTENANCE
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM equipment_maintenance"))
    if r.scalar() == 0 and equipment_ids:
        print("  Seeding equipment_maintenance...")
        maint_types = [
            "routine_check",
            "cleaning",
            "software_update",
            "hardware_repair",
            "battery_replacement",
            "calibration",
            "deep_clean",
            "diagnostic",
        ]
        count = 0
        for i in range(10):
            mt = maint_types[i % len(maint_types)]
            status = random.choice(
                ["completed", "completed", "completed", "scheduled", "in_progress"]
            )
            sched = (
                _past_date(random.randint(1, 120))
                if status == "completed"
                else _future_date(random.randint(1, 30))
            )
            completed = _past(random.randint(1, 100)) if status == "completed" else None
            await session.execute(
                text("""
                INSERT INTO equipment_maintenance
                    (equipment_id, maintenance_type, status, description,
                     scheduled_date, completed_at,
                     condition_before, condition_after,
                     parts_cost, labor_cost, performed_by_id,
                     requires_followup, created_at, updated_at)
                VALUES (:eid, :mtype, :status, :desc,
                        :sched, :completed,
                        :cond_before, :cond_after,
                        :parts, :labor, :performer,
                        false, :now, :now)
            """),
                {
                    "eid": random.choice(equipment_ids),
                    "mtype": mt,
                    "status": status,
                    "desc": f"Routine {mt.replace('_', ' ')} performed",
                    "sched": sched,
                    "completed": completed,
                    "cond_before": random.choice(["good", "fair", "poor"])
                    if status == "completed"
                    else "fair",
                    "cond_after": "good" if status == "completed" else None,
                    "parts": round(random.uniform(0, 50), 2) if status == "completed" else 0,
                    "labor": round(random.uniform(0, 25), 2) if status == "completed" else 0,
                    "performer": random.choice(staff_ids) if status == "completed" else None,
                    "now": now,
                },
            )
            count += 1
        print(f"    Created {count} equipment maintenance records")
        await session.commit()

    # Get equipment maintenance IDs
    em_r = await session.execute(text("SELECT id FROM equipment_maintenance"))
    equip_maint_ids = [r[0] for r in em_r.fetchall()]

    # ══════════════════════════════════════════════════════════════════
    # 12. EQUIPMENT RESERVATIONS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM equipment_reservations"))
    if r.scalar() == 0 and equipment_ids:
        print("  Seeding equipment_reservations...")
        count = 0
        for i in range(15):
            status = random.choice(
                ["completed", "completed", "confirmed", "pending", "cancelled", "no_show"]
            )
            start = (
                _past_date(random.randint(1, 60))
                if status in ("completed", "cancelled", "no_show")
                else _future_date(random.randint(1, 14))
            )
            end = start + timedelta(days=random.randint(3, 7))
            await session.execute(
                text("""
                INSERT INTO equipment_reservations
                    (equipment_id, user_id, status, start_date, end_date,
                     position, purpose, notes, created_at, updated_at)
                VALUES (:eid, :uid, :status, :start, :end,
                        :pos, :purpose, NULL, :created, :created)
            """),
                {
                    "eid": random.choice(equipment_ids),
                    "uid": random.choice(patron_ids),
                    "status": status,
                    "start": start,
                    "end": end,
                    "pos": 1,
                    "purpose": random.choice(
                        [
                            "School project presentation",
                            "Remote work - need WiFi hotspot",
                            "Community meeting recording",
                            "Family vacation photo editing",
                            "Job search and resume work",
                            None,
                        ]
                    ),
                    "created": _past(random.randint(1, 90)),
                },
            )
            count += 1
        print(f"    Created {count} equipment reservations")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 13. EQUIPMENT ALERTS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM equipment_alerts"))
    if r.scalar() == 0 and equipment_ids:
        print("  Seeding equipment_alerts...")
        alerts = [
            (
                "overdue",
                "high",
                "Laptop #3 overdue by 5 days",
                "Patron has not returned Dell Latitude. Contact attempted.",
                5,
            ),
            (
                "maintenance_due",
                "medium",
                "Hotspot #2 maintenance due",
                "Monthly diagnostic check overdue by 3 days.",
                None,
            ),
            (
                "condition_degraded",
                "medium",
                "Projector #1 bulb dimming",
                "Brightness noticeably reduced during last checkout.",
                None,
            ),
            (
                "overdue",
                "urgent",
                "Tablet #5 severely overdue",
                "iPad not returned for 14 days. Second notice sent.",
                14,
            ),
            (
                "reservation_ready",
                "low",
                "Camera #1 ready for pickup",
                "Reserved camera available at circulation desk.",
                None,
            ),
            (
                "damaged_item",
                "high",
                "E-reader screen cracked",
                "Kindle returned with cracked screen. Repair needed.",
                None,
            ),
            (
                "lost_item",
                "urgent",
                "Hotspot #4 reported lost",
                "Patron reports hotspot was stolen from vehicle.",
                None,
            ),
            (
                "maintenance_due",
                "low",
                "Charger kit routine check",
                "Quarterly cable inspection due.",
                None,
            ),
        ]
        for atype, priority, title, msg, days_overdue in alerts:
            status = random.choice(["active", "active", "acknowledged", "resolved"])
            await session.execute(
                text("""
                INSERT INTO equipment_alerts
                    (alert_type, priority, status, equipment_id, user_id,
                     title, message, days_overdue, escalation_level,
                     resolved_by_id, resolved_at, resolution_notes,
                     created_at, updated_at)
                VALUES (:atype, :priority, :status, :eid, :uid,
                        :title, :msg, :days, 0,
                        :resolver, :resolved, :res_notes,
                        :created, :created)
            """),
                {
                    "atype": atype,
                    "priority": priority,
                    "status": status,
                    "eid": random.choice(equipment_ids),
                    "uid": random.choice(patron_ids)
                    if "overdue" in atype or "lost" in atype
                    else None,
                    "title": title,
                    "msg": msg,
                    "days": days_overdue,
                    "resolver": random.choice(staff_ids) if status == "resolved" else None,
                    "resolved": _past(random.randint(1, 30)) if status == "resolved" else None,
                    "res_notes": "Issue addressed." if status == "resolved" else None,
                    "created": _past(random.randint(1, 60)),
                },
            )
        print(f"    Created {len(alerts)} equipment alerts")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 14. EQUIPMENT CONDITION LOGS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM equipment_condition_logs"))
    if r.scalar() == 0 and equipment_ids:
        print("  Seeding equipment_condition_logs...")
        transitions = [
            ("excellent", "good", "Normal wear from checkout", "checkout_return"),
            ("good", "fair", "Minor scratches on screen", "checkout_return"),
            ("fair", "good", "Cleaned and refurbished", "maintenance"),
            ("good", "good", "Routine inspection - no issues", "inspection"),
            ("good", "poor", "Battery no longer holds charge", "checkout_return"),
            ("poor", "good", "Battery replaced", "maintenance"),
            ("excellent", "good", "Light scuffing on case", "checkout_return"),
            ("fair", "poor", "Loose charging port", "inspection"),
            ("poor", "fair", "Port repaired", "maintenance"),
            ("good", "needs_repair", "Power button intermittent", "checkout_return"),
            ("needs_repair", "good", "Power button replaced", "maintenance"),
            ("good", "fair", "Screen protector peeling", "inspection"),
            ("fair", "good", "New screen protector applied", "maintenance"),
            ("good", "excellent", "Full refurbishment completed", "maintenance"),
            ("excellent", "good", "Minor cosmetic wear", "checkout_return"),
        ]
        maint_id_for_log = equip_maint_ids[0] if equip_maint_ids else None
        co_id_for_log = equip_checkout_ids[0] if equip_checkout_ids else None
        for prev, new, notes, reason in transitions:
            await session.execute(
                text("""
                INSERT INTO equipment_condition_logs
                    (equipment_id, previous_condition, new_condition,
                     change_reason, notes, checkout_id, maintenance_id,
                     recorded_by_id, created_at, updated_at)
                VALUES (:eid, :prev, :new,
                        :reason, :notes, :co_id, :maint_id,
                        :staff, :created, :created)
            """),
                {
                    "eid": random.choice(equipment_ids),
                    "prev": prev,
                    "new": new,
                    "reason": reason,
                    "notes": notes,
                    "co_id": co_id_for_log if "checkout" in reason else None,
                    "maint_id": maint_id_for_log if "maintenance" in reason else None,
                    "staff": random.choice(staff_ids),
                    "created": _past(random.randint(1, 180)),
                },
            )
        print(f"    Created {len(transitions)} condition logs")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 15. BOOK CHALLENGES + NOTES
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM book_challenges"))
    if r.scalar() == 0:
        print("  Seeding book_challenges & notes...")
        challenges = [
            (
                "Gender Queer: A Memoir",
                "Maia Kobabe",
                "978-1549304002",
                "sexual_content",
                "resolved_retained",
                "retained",
                "This book contains explicit illustrations that are inappropriate for minors.",
                "Committee reviewed the book and determined it is appropriately shelved in the Young Adult section. The book addresses important identity issues and is widely recognized by library professionals.",
            ),
            (
                "The Hate U Give",
                "Angie Thomas",
                "978-0062498533",
                "language",
                "resolved_retained",
                "retained",
                "Contains excessive profanity and promotes anti-police sentiment.",
                "The committee found the language reflects authentic teen voices and the book promotes critical thinking about social justice. Retained without changes.",
            ),
            (
                "Lawn Boy",
                "Jonathan Evison",
                "978-1984898982",
                "sexual_content",
                "under_review",
                "pending",
                "Contains sexually explicit content involving minors.",
                None,
            ),
            (
                "Captain Underpants (series)",
                "Dav Pilkey",
                "978-0439014571",
                "age_inappropriate",
                "resolved_retained",
                "retained_with_changes",
                "Encourages disrespect for authority and contains toilet humor unsuitable for young children.",
                "Retained in collection. Added an age recommendation sticker (ages 7+) on the spine. Series remains in Children's section.",
            ),
        ]
        challenge_ids_created = []
        for title, author, isbn, reason, status, outcome, complaint, resolution in challenges:
            cid_val = random.choice(catalog_ids) if catalog_ids else None
            r2 = await session.execute(
                text("""
                INSERT INTO book_challenges
                    (catalog_item_id, title, author, isbn, status, primary_reason,
                     challenger_complaint, challenger_name, challenger_is_patron,
                     date_received, outcome, resolution_summary,
                     assigned_staff_id, is_public, created_at, updated_at)
                VALUES (:cid, :title, :author, :isbn, :status, :reason,
                        :complaint, :name, true,
                        :received, :outcome, :resolution,
                        :staff, false, :created, :created)
                RETURNING id
            """),
                {
                    "cid": cid_val,
                    "title": title,
                    "author": author,
                    "isbn": isbn,
                    "status": status,
                    "reason": reason,
                    # Raw SQL bypasses the EncryptedString/EncryptedText type
                    # decorators, so encrypt here to match what an ORM write
                    # would store. encrypt_pii is a passthrough when
                    # encryption is disabled (dev/test), same as the ORM path.
                    "complaint": encrypt_pii(complaint),
                    "name": encrypt_pii(f"Community Member {random.randint(1, 50)}"),
                    "received": _past(random.randint(30, 365)),
                    "outcome": outcome,
                    "resolution": resolution,
                    "staff": random.choice(staff_ids),
                    "created": _past(random.randint(30, 365)),
                },
            )
            challenge_ids_created.append(r2.scalar())

        # Add notes
        notes_data = [
            "Initial complaint received via email. Formal reconsideration form mailed to challenger.",
            "Reconsideration form returned. Assigned to review committee.",
            "Committee meeting scheduled for next Tuesday to discuss this challenge.",
            "Committee reviewed the material and prepared recommendation for the director.",
            "Director approved committee recommendation. Response letter drafted.",
            "Response letter mailed to challenger. Case documentation filed.",
        ]
        note_count = 0
        for ch_id in challenge_ids_created:
            for note_text in random.sample(notes_data, random.randint(2, 4)):
                await session.execute(
                    text("""
                    INSERT INTO book_challenge_notes
                        (challenge_id, note, is_internal, created_by_id, created_at, updated_at)
                    VALUES (:chid, :note, true, :staff, :created, :created)
                """),
                    {
                        "chid": ch_id,
                        "note": note_text,
                        "staff": random.choice(staff_ids),
                        "created": _past(random.randint(1, 300)),
                    },
                )
                note_count += 1
        print(f"    Created {len(challenges)} challenges, {note_count} notes")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 16. BOOK CLUB KITS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM book_club_kits"))
    if r.scalar() == 0 and book_club_ids:
        print("  Seeding book_club_kits...")
        kits = [
            (
                "Where the Crawdads Sing Kit",
                "10 copies plus discussion guide and author bio",
                10,
                8,
            ),
            ("Educated by Tara Westover Kit", "8 copies with discussion questions", 8, 6),
            ("The Midnight Library Kit", "10 copies, bookmark set, and facilitator notes", 10, 10),
            ("Lessons in Chemistry Kit", "10 copies with book club discussion guide", 10, 7),
            ("Project Hail Mary Kit", "8 copies with science supplement materials", 8, 5),
            ("The House in the Cerulean Sea Kit", "10 copies and cozy reading guide", 10, 9),
            ("Circe by Madeline Miller Kit", "8 copies with mythology reference cards", 8, 4),
            ("Klara and the Sun Kit", "10 copies and AI ethics discussion prompts", 10, 10),
        ]
        for name, desc, total, avail in kits:
            bcid = random.choice(book_club_ids)
            await session.execute(
                text("""
                INSERT INTO book_club_kits
                    (book_club_id, name, description, total_copies, available_copies,
                     created_at, updated_at)
                VALUES (:bcid, :name, :desc, :total, :avail, :now, :now)
            """),
                {
                    "bcid": bcid,
                    "name": name,
                    "desc": desc,
                    "total": total,
                    "avail": avail,
                    "now": now,
                },
            )
        print(f"    Created {len(kits)} book club kits")
        await session.commit()

    # Get kit IDs
    kit_r = await session.execute(text("SELECT id FROM book_club_kits"))
    kit_ids = [r[0] for r in kit_r.fetchall()]

    # ══════════════════════════════════════════════════════════════════
    # 17. BOOK DROPS
    # ══════════════════════════════════════════════════════════════════
    # Book drops depend on sip2_devices FK - we'll create without that FK
    r = await session.execute(text("SELECT COUNT(*) FROM book_drops"))
    if r.scalar() == 0:
        print("  Seeding book_drops...")
        drops = [
            (
                "Main Entrance Drop",
                "BD-MAIN",
                "Outside main entrance, 24/7 access",
                "Main Branch",
                "active",
                "21:00",
            ),
            (
                "Drive-Through Drop",
                "BD-DRIVE",
                "Drive-up lane on north side of building",
                "Main Branch",
                "active",
                "21:00",
            ),
            (
                "Children's Wing Drop",
                "BD-CHILD",
                "Inside children's wing entrance vestibule",
                "Main Branch",
                "active",
                "17:00",
            ),
            (
                "Downtown Branch Drop",
                "BD-DT",
                "Outside downtown branch front door",
                "Downtown Branch",
                "active",
                "20:00",
            ),
            (
                "Eastside Branch Drop",
                "BD-EAST",
                "Parking lot kiosk at Eastside branch",
                "Eastside Branch",
                "active",
                "20:00",
            ),
            (
                "Mobile Stop Drop",
                "BD-MOB",
                "Bookmobile stop at community center",
                "Main Branch",
                "maintenance",
                "18:00",
            ),
        ]
        for name, code, desc, branch_loc, status, btime in drops:
            h, m = int(btime.split(":")[0]), int(btime.split(":")[1])
            await session.execute(
                text("""
                INSERT INTO book_drops
                    (name, code, description, branch_location, physical_location,
                     status, backdate_mode, backdate_fixed_time,
                     exempt_overnight_fines, max_backdate_hours,
                     created_by_id)
                VALUES (:name, :code, :desc, :branch, :physical,
                        :status, 'fixed_time', :btime,
                        true, 16,
                        :staff)
            """),
                {
                    "name": name,
                    "code": code,
                    "desc": desc,
                    "branch": branch_loc,
                    "physical": desc,
                    "status": status,
                    "btime": time(h, m),
                    "staff": random.choice(staff_ids),
                },
            )
        print(f"    Created {len(drops)} book drops")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 18. KIT CONTENTS + KIT CHECKOUTS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM kit_contents"))
    if r.scalar() == 0 and kit_ids and catalog_ids:
        print("  Seeding kit_contents...")
        count = 0
        for kid in kit_ids:
            cid = random.choice(catalog_ids)
            await session.execute(
                text("""
                INSERT INTO kit_contents (kit_id, catalog_item_id, quantity, sort_order)
                VALUES (:kid, :cid, :qty, :order)
            """),
                {"kid": kid, "cid": cid, "qty": random.randint(5, 10), "order": 1},
            )
            count += 1
            # Add a second item sometimes
            if random.random() > 0.5:
                cid2 = random.choice(catalog_ids)
                await session.execute(
                    text("""
                    INSERT INTO kit_contents (kit_id, catalog_item_id, quantity, sort_order)
                    VALUES (:kid, :cid, :qty, :order)
                """),
                    {"kid": kid, "cid": cid2, "qty": 1, "order": 2},
                )
                count += 1
        print(f"    Created {count} kit content items")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM kit_checkouts"))
    if r.scalar() == 0 and kit_ids and book_club_ids:
        print("  Seeding kit_checkouts...")
        count = 0
        for i in range(min(8, len(kit_ids))):
            kid = kit_ids[i]
            status = random.choice(["active", "returned", "returned", "returned"])
            co = _past(random.randint(5, 90))
            due = co + timedelta(days=28)
            ret = co + timedelta(days=random.randint(14, 28)) if status == "returned" else None
            await session.execute(
                text("""
                INSERT INTO kit_checkouts
                    (kit_id, book_club_id, user_id, status,
                     checked_out_at, due_date, returned_at,
                     all_items_returned, created_at, updated_at)
                VALUES (:kid, :bcid, :uid, :status,
                        :co, :due, :ret,
                        :all_ret, :co, :co)
            """),
                {
                    "kid": kid,
                    "bcid": random.choice(book_club_ids),
                    "uid": random.choice(patron_ids),
                    "status": status,
                    "co": co,
                    "due": due,
                    "ret": ret,
                    "all_ret": status == "returned",
                },
            )
            count += 1
        print(f"    Created {count} kit checkouts")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 19. MENDING QUEUE
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM mending_queue"))
    if r.scalar() == 0 and item_copy_ids:
        print("  Seeding mending_queue...")
        repairs = [
            ("rebinding", "Spine separated from cover block", "PVA glue, bookbinding tape", 1.5, 2),
            ("page repair", "Pages 45-48 torn at gutter", "Archival tissue, wheat paste", 0.75, 3),
            ("cover repair", "Front cover delaminating", "Book repair tape, weights", 1.0, 2),
            ("spine repair", "Spine cracked at hinge", "Super glue, binding tape", 1.25, 1),
            ("page repair", "Water-warped pages 10-30", "Blotting paper, press", 2.0, 3),
            (
                "rebinding",
                "Boards detached, textblock intact",
                "New boards, adhesive, cloth",
                3.0,
                1,
            ),
            ("cover repair", "Torn dust jacket", "Archival tape, Mylar cover", 0.5, 4),
            ("page repair", "Crayon marks on multiple pages", "Eraser, careful cleaning", 1.0, 5),
            (
                "disc replacement",
                "DVD case cracked, disc scratched",
                "Replacement case, disc resurfacing",
                0.25,
                3,
            ),
            (
                "spine repair",
                "Paperback spine crease severe",
                "Contact paper reinforcement",
                0.5,
                4,
            ),
            ("rebinding", "Complete binding failure", "Full rebind with new spine", 4.0, 1),
            ("cover repair", "Coffee stain on cover", "Cleaning solution, new Mylar", 0.75, 5),
            ("page repair", "Dog-eared and folded pages", "Flatten and press", 0.5, 5),
        ]
        for i, (rtype, instructions, materials, hours, priority) in enumerate(repairs):
            is_done = i < 5
            await session.execute(
                text("""
                INSERT INTO mending_queue
                    (item_copy_id, priority, queue_position,
                     repair_type, repair_instructions, materials_needed,
                     estimated_time_hours, is_in_progress, is_completed,
                     added_at, started_at, completed_at,
                     added_by_id, assigned_to_id, completed_by_id,
                     estimated_cost, actual_cost, notes)
                VALUES (:icid, :priority, :pos,
                        :rtype, :instructions, :materials,
                        :hours, :in_prog, :done,
                        :added, :started, :completed,
                        :adder, :assignee, :completer,
                        :est_cost, :act_cost, NULL)
            """),
                {
                    "icid": random.choice(item_copy_ids),
                    "priority": priority,
                    "pos": i + 1,
                    "rtype": rtype,
                    "instructions": instructions,
                    "materials": materials,
                    "hours": hours,
                    "in_prog": not is_done and i == 5,
                    "done": is_done,
                    "added": _past(random.randint(10, 90)),
                    "started": _past(random.randint(5, 30)) if is_done or i == 5 else None,
                    "completed": _past(random.randint(1, 20)) if is_done else None,
                    "adder": random.choice(staff_ids),
                    "assignee": random.choice(staff_ids),
                    "completer": random.choice(staff_ids) if is_done else None,
                    "est_cost": round(hours * 8 + random.uniform(0, 5), 2),
                    "act_cost": round(hours * 8 + random.uniform(0, 5), 2) if is_done else None,
                },
            )
        print(f"    Created {len(repairs)} mending queue items")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 20. DAMAGED ITEM RECORDS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM damaged_item_records"))
    if r.scalar() == 0 and item_copy_ids:
        print("  Seeding damaged_item_records...")
        damages = [
            ("reported", "minor", "Small tear on page 12", '["torn_pages"]'),
            (
                "assessment_pending",
                "moderate",
                "Water damage to cover and first 20 pages",
                '["water_damage"]',
            ),
            ("repairable", "minor", "Spine cracking at several points", '["spine_damage"]'),
            (
                "in_mending",
                "moderate",
                "Cover partially detached, binding loose",
                '["binding_loose", "missing_cover"]',
            ),
            ("repaired", "minor", "Pencil writing on margins cleaned", '["writing_marks"]'),
            (
                "withdrawn",
                "severe",
                "Extensive mold damage from humidity exposure",
                '["water_damage"]',
            ),
            ("charged", "moderate", "Coffee spill on 15 pages", '["stains"]'),
            ("reported", "minor", "Missing DVD from audiobook set", '["missing_disc"]'),
        ]
        for status, severity, desc, dtypes in damages:
            await session.execute(
                text("""
                INSERT INTO damaged_item_records
                    (item_copy_id, catalog_item_id, patron_id,
                     status, severity, damage_types, damage_description,
                     is_patron_responsible, repair_priority,
                     reported_at, reported_by_id)
                VALUES (:icid, :catid, :patron,
                        :status, :sev, cast(:dtypes as jsonb), :desc,
                        :responsible, :priority,
                        :reported, :reporter)
            """),
                {
                    "icid": random.choice(item_copy_ids),
                    "catid": random.choice(catalog_ids) if catalog_ids else None,
                    "patron": random.choice(patron_ids),
                    "status": status,
                    "sev": severity,
                    "dtypes": dtypes,
                    "desc": desc,
                    "responsible": random.choice([True, True, False]),
                    "priority": random.randint(1, 5),
                    "reported": _past(random.randint(1, 120)),
                    "reporter": random.choice(staff_ids),
                },
            )
        print(f"    Created {len(damages)} damaged item records")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 21. LOST ITEM RECORDS + LOST_DAMAGED_SETTINGS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM lost_item_records"))
    if r.scalar() == 0 and item_copy_ids:
        print("  Seeding lost_item_records...")
        lost = [
            ("reported", "lost_by_patron", "Patron says book fell out of bag on bus", 25.00, 5.00),
            (
                "confirmed",
                "lost_by_patron",
                "Not returned after 60 days; patron unresponsive",
                18.99,
                5.00,
            ),
            ("charged", "overdue_conversion", "Auto-converted from 45-day overdue", 32.00, 5.00),
            (
                "found",
                "claims_returned",
                "Found behind shelving unit during inventory",
                14.95,
                5.00,
            ),
            (
                "written_off",
                "missing_inventory",
                "Missing from annual inventory count",
                22.50,
                5.00,
            ),
            (
                "dispute_pending",
                "claims_returned",
                "Patron insists they returned the item in the book drop",
                29.99,
                5.00,
            ),
            ("charged", "lost_by_patron", "Child lost DVD case at park", 19.99, 5.00),
            (
                "confirmed",
                "lost_in_transit",
                "ILL item not received by destination library",
                45.00,
                5.00,
            ),
        ]
        for status, ltype, notes, price, fee in lost:
            await session.execute(
                text("""
                INSERT INTO lost_item_records
                    (item_copy_id, catalog_item_id, patron_id,
                     status, lost_type, item_price, processing_fee,
                     replacement_cost, report_notes,
                     reported_at, reported_by_id, last_known_location)
                VALUES (:icid, :catid, :patron,
                        :status, :ltype, :price, :fee,
                        :repl, :notes,
                        :reported, :reporter, :loc)
            """),
                {
                    "icid": random.choice(item_copy_ids),
                    "catid": random.choice(catalog_ids) if catalog_ids else None,
                    "patron": random.choice(patron_ids),
                    "status": status,
                    "ltype": ltype,
                    "price": price,
                    "fee": fee,
                    "repl": price + fee,
                    "notes": notes,
                    "reported": _past(random.randint(5, 200)),
                    "reporter": random.choice(staff_ids),
                    "loc": random.choice(
                        ["Adult Fiction", "Children's", "Reference", "DVD Shelves", "Unknown"]
                    ),
                },
            )
        print(f"    Created {len(lost)} lost item records")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM lost_damaged_settings"))
    if r.scalar() == 0:
        print("  Seeding lost_damaged_settings...")
        await session.execute(
            text("""
            INSERT INTO lost_damaged_settings
                (branch_location, lost_item_processing_fee, default_replacement_cost,
                 overdue_to_lost_days, auto_convert_overdue_enabled,
                 found_item_full_credit, found_item_grace_period_days,
                 claims_returned_review_days, max_claims_per_patron_year,
                 notify_patron_on_lost, notify_patron_on_damaged_charge,
                 notify_patron_on_found, notify_staff_on_claims,
                 is_active, created_by_id, created_at, updated_at)
            VALUES (NULL, 5.00, 25.00,
                    30, true,
                    true, 365,
                    30, 3,
                    true, true, true, true,
                    true, :staff, :now, :now)
        """),
            {"staff": staff_ids[0], "now": now},
        )
        print("    Created system-wide lost/damaged settings")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 22. CLAIMS RETURNED DISPUTES
    # ══════════════════════════════════════════════════════════════════
    # Get lost item record IDs
    lir_r = await session.execute(text("SELECT id FROM lost_item_records"))
    lost_item_ids = [r[0] for r in lir_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM claims_returned_disputes"))
    if r.scalar() == 0 and lost_item_ids and item_copy_ids:
        print("  Seeding claims_returned_disputes...")
        disputes = [
            (
                "pending",
                "I returned this book in the outside drop box two weeks ago.",
                "Book drop",
                date(2026, 3, 1),
            ),
            (
                "under_review",
                "I definitely returned it at the front desk before closing.",
                "Circulation desk",
                date(2026, 2, 15),
            ),
            (
                "approved",
                "Found on reshelving cart. Patron was correct.",
                "Main stacks",
                date(2026, 1, 20),
            ),
            (
                "denied",
                "Security footage shows patron left without returning item.",
                None,
                date(2026, 2, 1),
            ),
        ]
        for status, statement, loc, claimed_date in disputes:
            await session.execute(
                text("""
                INSERT INTO claims_returned_disputes
                    (lost_item_record_id, item_copy_id, patron_id,
                     status, patron_statement, claimed_return_date,
                     claimed_return_location,
                     patron_previous_claims_count,
                     filed_at, filed_by_id)
                VALUES (:lir, :icid, :patron,
                        :status, :stmt, :claimed_date,
                        :loc,
                        :prev_claims,
                        :filed, :filer)
            """),
                {
                    "lir": random.choice(lost_item_ids),
                    "icid": random.choice(item_copy_ids),
                    "patron": random.choice(patron_ids),
                    "status": status,
                    "stmt": statement,
                    "claimed_date": claimed_date,
                    "loc": loc,
                    "prev_claims": random.randint(0, 2),
                    "filed": _past(random.randint(5, 90)),
                    "filer": random.choice(staff_ids),
                },
            )
        print(f"    Created {len(disputes)} claims returned disputes")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 23. CONDITION CHANGES
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM condition_changes"))
    if r.scalar() == 0 and item_copy_ids:
        print("  Seeding condition_changes...")
        changes = [
            ("new", "good", None, "Normal wear after first few checkouts"),
            ("good", "fair", "spine_damage", "Spine cracking noticed at check-in"),
            ("fair", "good", None, "Repaired spine, returned to circulation"),
            ("good", "damaged", "water_damage", "Returned with water damage"),
            ("new", "good", None, "Initial processing and cataloging"),
            ("good", "fair", "writing_marks", "Pencil marks found in margins"),
            ("fair", "poor", "torn_pages", "Multiple torn pages discovered"),
            ("poor", "withdrawn", "binding_loose", "Beyond repair, withdrawn from collection"),
            ("good", "fair", "stains", "Coffee stain on front cover"),
            ("fair", "good", None, "Cover cleaned and protected with Mylar"),
        ]
        for prev, new, dtype, desc in changes:
            await session.execute(
                text("""
                INSERT INTO condition_changes
                    (item_copy_id, previous_condition, new_condition,
                     damage_type, damage_description,
                     reported_by_id, created_at)
                VALUES (:icid, :prev, :new,
                        :dtype, :desc,
                        :reporter, :created)
            """),
                {
                    "icid": random.choice(item_copy_ids),
                    "prev": prev,
                    "new": new,
                    "dtype": dtype,
                    "desc": desc,
                    "reporter": random.choice(staff_ids),
                    "created": _past(random.randint(1, 365)),
                },
            )
        print(f"    Created {len(changes)} condition changes")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 24. INVENTORY AUDITS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM inventory_audits"))
    if r.scalar() == 0:
        print("  Seeding inventory_audits...")
        audits = [
            (
                "Annual Inventory 2025",
                "Full library inventory audit for FY2025",
                "Adult Fiction",
                2400,
                2350,
                42,
                8,
            ),
            (
                "Children's Section Spot Check",
                "Quarterly spot check of children's materials",
                "Children's",
                800,
                785,
                12,
                3,
            ),
            (
                "DVD Collection Audit",
                "Complete audit of AV materials",
                "Media Center",
                450,
                430,
                18,
                2,
            ),
            (
                "Reference Collection Review",
                "Biannual reference section review",
                "Reference",
                600,
                598,
                2,
                0,
            ),
        ]
        for name, desc, loc, expected, found, missing, misplaced in audits:
            completed = _past(random.randint(10, 180))
            await session.execute(
                text("""
                INSERT INTO inventory_audits
                    (name, description, location_filter,
                     started_at, completed_at,
                     items_expected, items_found, items_missing, items_misplaced,
                     created_by_id)
                VALUES (:name, :desc, :loc,
                        :started, :completed,
                        :expected, :found, :missing, :misplaced,
                        :creator)
            """),
                {
                    "name": name,
                    "desc": desc,
                    "loc": loc,
                    "started": completed - timedelta(hours=random.randint(4, 16)),
                    "completed": completed,
                    "expected": expected,
                    "found": found,
                    "missing": missing,
                    "misplaced": misplaced,
                    "creator": random.choice(staff_ids),
                },
            )
        print(f"    Created {len(audits)} inventory audits")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 25. SHELF READING SCHEDULES + SESSIONS + SCANS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM shelf_reading_schedules"))
    if r.scalar() == 0 and branch_ids:
        print("  Seeding shelf_reading_schedules...")
        schedules = [
            ("Adult Fiction A-M", "Adult Fiction A-M", "A", "M", "monthly"),
            ("Adult Fiction N-Z", "Adult Fiction N-Z", "N", "Z", "monthly"),
            ("Children's Picture Books", "Children's", "E", "E", "quarterly"),
        ]
        for name, loc, cn_start, cn_end, freq in schedules:
            await session.execute(
                text("""
                INSERT INTO shelf_reading_schedules
                    (name, description, branch_id, location,
                     call_number_start, call_number_end, frequency,
                     is_active, next_due_at,
                     assigned_to_id, created_by_id, created_at, updated_at)
                VALUES (:name, :desc, :bid, :loc,
                        :cns, :cne, :freq,
                        true, :next_due,
                        :assignee, :creator, :now, :now)
            """),
                {
                    "name": name,
                    "desc": name,
                    "bid": random.choice(branch_ids),
                    "loc": loc,
                    "cns": cn_start,
                    "cne": cn_end,
                    "freq": freq,
                    "next_due": _future(random.randint(7, 30)),
                    "assignee": random.choice(staff_ids),
                    "creator": random.choice(staff_ids),
                    "now": now,
                },
            )
        print(f"    Created {len(schedules)} shelf reading schedules")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM shelf_reading_sessions"))
    if r.scalar() == 0 and branch_ids:
        print("  Seeding shelf_reading_sessions...")
        sessions = [
            ("Adult Fiction A-M Read", "completed", "Adult Fiction A-M", 120, 115, 4, 1, 95.8),
            ("Children's Shelf Read", "completed", "Children's", 85, 80, 3, 2, 94.1),
            ("Adult Fiction N-Z Read", "in_progress", "Adult Fiction N-Z", 45, 42, 2, 1, 93.3),
        ]
        session_ids_created = []
        for name, status, loc, total, in_order, out_order, wrong, accuracy in sessions:
            completed = _past(random.randint(1, 30)) if status == "completed" else None
            r2 = await session.execute(
                text("""
                INSERT INTO shelf_reading_sessions
                    (name, branch_id, location, status,
                     started_at, completed_at,
                     total_items_scanned, items_in_order, items_out_of_order,
                     items_wrong_shelf, accuracy_percentage,
                     created_by_id, points_earned, created_at, updated_at)
                VALUES (:name, :bid, :loc, :status,
                        :started, :completed,
                        :total, :in_order, :out_order,
                        :wrong, :accuracy,
                        :creator, :points, :now, :now)
                RETURNING id
            """),
                {
                    "name": name,
                    "bid": random.choice(branch_ids),
                    "loc": loc,
                    "status": status,
                    "started": _past(random.randint(2, 35)),
                    "completed": completed,
                    "total": total,
                    "in_order": in_order,
                    "out_order": out_order,
                    "wrong": wrong,
                    "accuracy": accuracy,
                    "creator": random.choice(staff_ids),
                    "points": total * 2,
                    "now": now,
                },
            )
            session_ids_created.append(r2.scalar())
        print(f"    Created {len(sessions)} shelf reading sessions")
        await session.commit()

        # Scans for first session
        if session_ids_created and item_copy_ids:
            print("  Seeding shelf_reading_scans...")
            sid = session_ids_created[0]
            scan_count = 0
            used_items = set()
            for i in range(min(10, len(item_copy_ids))):
                icid = item_copy_ids[i]
                if icid in used_items:
                    continue
                used_items.add(icid)
                result = random.choice(
                    ["in_order", "in_order", "in_order", "out_of_order", "wrong_shelf"]
                )
                await session.execute(
                    text("""
                    INSERT INTO shelf_reading_scans
                        (session_id, item_copy_id, scan_order, result,
                         scanned_at, scanned_by_id)
                    VALUES (:sid, :icid, :order, :result,
                            :scanned, :scanner)
                """),
                    {
                        "sid": sid,
                        "icid": icid,
                        "order": i + 1,
                        "result": result,
                        "scanned": _past(random.randint(1, 30)),
                        "scanner": random.choice(staff_ids),
                    },
                )
                scan_count += 1
            print(f"    Created {scan_count} shelf reading scans")
            await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 26. COMIC ISSUES + CREATORS + CONTENT ADVISORIES
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM comic_issues"))
    if r.scalar() == 0 and comic_series_ids and catalog_ids:
        print("  Seeding comic_issues, creators, advisories...")
        issues_data = [
            ("1", "The Beginning", None, "2024-01-15", 32, True, "T for Teen"),
            ("2", "Rising Tension", None, "2024-02-15", 32, True, "T for Teen"),
            ("3", "The Turning Point", None, "2024-03-15", 32, True, "T for Teen"),
            ("4", "Escalation", None, "2024-04-15", 36, True, "T for Teen"),
            ("5", "Climax", None, "2024-05-15", 40, True, "T+ for Older Teens"),
            ("6", "Aftermath", None, "2024-06-15", 32, True, "T for Teen"),
            ("7", "New Beginnings", None, "2024-07-15", 32, True, "T for Teen"),
            ("8", "Crossroads", None, "2024-08-15", 32, True, "T for Teen"),
            ("9", "The Revelation", None, "2024-09-15", 36, True, "T for Teen"),
            ("10", "Anniversary Special", None, "2024-10-15", 48, True, "T for Teen"),
            ("11", "Descent", None, "2024-11-15", 32, True, "T+ for Older Teens"),
            ("12", "Resolution", None, "2024-12-15", 40, True, "T for Teen"),
        ]
        issue_ids_created = []
        for issue_num, title, synopsis, pub_date, pages, color, rating in issues_data:
            sid = random.choice(comic_series_ids)
            cid = random.choice(catalog_ids)
            # Check uniqueness
            existing = await session.execute(
                text("SELECT id FROM comic_issues WHERE series_id = :sid AND issue_number = :inum"),
                {"sid": sid, "inum": issue_num},
            )
            if existing.scalar():
                continue
            r2 = await session.execute(
                text("""
                INSERT INTO comic_issues
                    (series_id, catalog_item_id, issue_number, issue_title,
                     publication_date, page_count, is_color, rating,
                     has_variant_covers, is_part_of_crossover)
                VALUES (:sid, :cid, :inum, :title,
                        :pub, :pages, :color, :rating,
                        false, false)
                RETURNING id
            """),
                {
                    "sid": sid,
                    "cid": cid,
                    "inum": issue_num,
                    "title": title,
                    "pub": datetime.strptime(pub_date, "%Y-%m-%d").replace(tzinfo=utc),
                    "pages": pages,
                    "color": color,
                    "rating": rating,
                },
            )
            issue_ids_created.append(r2.scalar())

        # Creators
        creators = [
            ("Alex Rivera", "writer"),
            ("Sarah Kim", "penciller"),
            ("Marcus Johnson", "inker"),
            ("Yuki Tanaka", "colorist"),
            ("Pat Chen", "letterer"),
            ("Jordan Ellis", "writer"),
            ("Mia Santos", "penciller"),
            ("David Park", "colorist"),
        ]
        creator_count = 0
        for iid in issue_ids_created:
            for cname, role in random.sample(creators, random.randint(3, 5)):
                # Check uniqueness
                existing = await session.execute(
                    text(
                        "SELECT id FROM comic_issue_creators WHERE issue_id = :iid AND creator_name = :cn AND creator_role = :cr"
                    ),
                    {"iid": iid, "cn": cname, "cr": role},
                )
                if existing.scalar():
                    continue
                await session.execute(
                    text("""
                    INSERT INTO comic_issue_creators
                        (issue_id, creator_name, creator_role, display_order)
                    VALUES (:iid, :name, :role, :order)
                """),
                    {"iid": iid, "name": cname, "role": role, "order": creator_count},
                )
                creator_count += 1

        # Content advisories
        advisory_count = 0
        advisory_data = [
            ("violence", "mild", "Stylized action sequences with no graphic depictions"),
            ("strong_language", "moderate", "Occasional strong language in dialogue"),
            ("death", "mild", "Character death implied off-panel"),
        ]
        for iid in random.sample(issue_ids_created, min(4, len(issue_ids_created))):
            for wtype, severity, desc in random.sample(advisory_data, random.randint(1, 2)):
                await session.execute(
                    text("""
                    INSERT INTO comic_content_advisories
                        (issue_id, warning_type, severity, description, recurring, added_by_id)
                    VALUES (:iid, :wtype, :sev, :desc, false, :staff)
                """),
                    {
                        "iid": iid,
                        "wtype": wtype,
                        "sev": severity,
                        "desc": desc,
                        "staff": random.choice(staff_ids),
                    },
                )
                advisory_count += 1

        print(
            f"    Created {len(issue_ids_created)} issues, {creator_count} creators, {advisory_count} advisories"
        )
        await session.commit()
    else:
        # Get existing issue IDs
        issue_ids_created = []

    ci_r = await session.execute(text("SELECT id FROM comic_issues"))
    all_issue_ids = [r[0] for r in ci_r.fetchall()]

    # ══════════════════════════════════════════════════════════════════
    # 27. MANGA METADATA + VOLUME RECORDS + MAGAZINES + SERIALIZATIONS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM manga_metadata"))
    if r.scalar() == 0 and bibframe_work_ids:
        print("  Seeding manga_metadata...")
        manga_data = [
            ("One Piece", "Wan Piisu", "Eiichiro Oda", "Stephen Paul", "JP", True, "right-to-left"),
            (
                "My Hero Academia",
                "Boku no Hero Academia",
                "Kohei Horikoshi",
                "Caleb Cook",
                "JP",
                True,
                "right-to-left",
            ),
            (
                "Spy x Family",
                "Supai Famirii",
                "Tatsuya Endo",
                "Casey Loe",
                "JP",
                True,
                "right-to-left",
            ),
            (
                "Demon Slayer",
                "Kimetsu no Yaiba",
                "Koyoharu Gotouge",
                "John Werry",
                "JP",
                True,
                "right-to-left",
            ),
            (
                "Chainsaw Man",
                "Chensoo Man",
                "Tatsuki Fujimoto",
                "Amanda Haley",
                "JP",
                True,
                "right-to-left",
            ),
        ]
        used_work_ids = set()
        for jp_title, romaji, author, translator, country, is_vol, direction in manga_data:
            wid = None
            for candidate in bibframe_work_ids:
                if candidate not in used_work_ids:
                    wid = candidate
                    used_work_ids.add(candidate)
                    break
            if not wid:
                break
            await session.execute(
                text("""
                INSERT INTO manga_metadata
                    (bibframe_work_id, original_japanese_title, romaji_title,
                     translator_name, original_publication_country,
                     is_volume_collection, reading_direction)
                VALUES (:wid, :jp, :romaji,
                        :translator, :country,
                        :is_vol, :direction)
            """),
                {
                    "wid": wid,
                    "jp": jp_title,
                    "romaji": romaji,
                    "translator": translator,
                    "country": country,
                    "is_vol": is_vol,
                    "direction": direction,
                },
            )
        print(f"    Created {len(manga_data)} manga metadata records")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM manga_volume_records"))
    if r.scalar() == 0 and catalog_ids:
        print("  Seeding manga_volume_records...")
        vol_count = 0
        for series in ["One Piece", "My Hero Academia", "Spy x Family"]:
            for vol in range(1, 6):
                await session.execute(
                    text("""
                    INSERT INTO manga_volume_records
                        (catalog_item_id, series_title, volume_number, volume_title,
                         publisher, original_language, page_count, is_color)
                    VALUES (:cid, :series, :vol, NULL,
                            'Viz Media', 'Japanese', :pages, false)
                """),
                    {
                        "cid": random.choice(catalog_ids),
                        "series": series,
                        "vol": vol,
                        "pages": random.randint(180, 210),
                    },
                )
                vol_count += 1
        print(f"    Created {vol_count} manga volume records")
        await session.commit()

    # Publishers (needed for magazines)
    r = await session.execute(text("SELECT COUNT(*) FROM publishers"))
    publisher_ids_local = []
    if r.scalar() == 0:
        print("  Seeding publishers...")
        pubs = [
            (
                "Viz Media",
                "publisher",
                "north_america",
                "Leading manga publisher in North America",
                "https://www.viz.com",
            ),
            (
                "Kodansha USA",
                "publisher",
                "north_america",
                "US division of Kodansha publishing",
                "https://kodansha.us",
            ),
            (
                "Shueisha",
                "publisher",
                "japan",
                "Publisher of Weekly Shonen Jump",
                "https://www.shueisha.co.jp",
            ),
            (
                "Yen Press",
                "publisher",
                "north_america",
                "Manga and light novel publisher",
                "https://yenpress.com",
            ),
            (
                "Seven Seas Entertainment",
                "publisher",
                "north_america",
                "Publisher of manga and light novels",
                "https://sevenseasentertainment.com",
            ),
        ]
        for name, ptype, region, desc, url in pubs:
            r2 = await session.execute(
                text("""
                INSERT INTO publishers
                    (name, publisher_type, primary_region, description, website_url, is_active)
                VALUES (:name, :ptype, :region, :desc, :url, true)
                RETURNING id
            """),
                {"name": name, "ptype": ptype, "region": region, "desc": desc, "url": url},
            )
            publisher_ids_local.append(r2.scalar())
        print(f"    Created {len(pubs)} publishers")
        await session.commit()
    else:
        pub_r = await session.execute(text("SELECT id FROM publishers"))
        publisher_ids_local = [r[0] for r in pub_r.fetchall()]

    # Manga magazines
    r = await session.execute(text("SELECT COUNT(*) FROM manga_magazines"))
    if r.scalar() == 0 and publisher_ids_local:
        print("  Seeding manga_magazines...")
        magazines = [
            ("Weekly Shonen Jump", "Weekly Shonen Jump", "ja", "Weekly", 1968, True, "Shonen"),
            (
                "Monthly Shonen Magazine",
                "Monthly Shonen Magazine",
                "ja",
                "Monthly",
                1964,
                True,
                "Shonen",
            ),
            ("Weekly Young Jump", "Weekly Young Jump", "ja", "Weekly", 1979, True, "Seinen"),
            ("Shonen Jump+", "Shonen Jump+", "ja", "Digital daily", 2014, True, "Shonen"),
        ]
        mag_ids = []
        for name, eng_name, lang, freq, year, ongoing, demo in magazines:
            r2 = await session.execute(
                text("""
                INSERT INTO manga_magazines
                    (name, english_name, original_language, publisher_id,
                     publication_frequency, first_published, is_ongoing,
                     target_demographic)
                VALUES (:name, :eng, :lang, :pub,
                        :freq, :year, :ongoing,
                        :demo)
                RETURNING id
            """),
                {
                    "name": name,
                    "eng": eng_name,
                    "lang": lang,
                    "pub": random.choice(publisher_ids_local),
                    "freq": freq,
                    "year": year,
                    "ongoing": ongoing,
                    "demo": demo,
                },
            )
            mag_ids.append(r2.scalar())
        print(f"    Created {len(magazines)} manga magazines")
        await session.commit()

        # Serializations
        if bibframe_work_ids and mag_ids:
            r = await session.execute(text("SELECT COUNT(*) FROM manga_serializations"))
            if r.scalar() == 0:
                print("  Seeding manga_serializations...")
                ser_count = 0
                used_ser = set()
                for wid in random.sample(bibframe_work_ids, min(4, len(bibframe_work_ids))):
                    mid = random.choice(mag_ids)
                    if (wid, mid) in used_ser:
                        continue
                    used_ser.add((wid, mid))
                    await session.execute(
                        text("""
                        INSERT INTO manga_serializations
                            (bibframe_work_id, magazine_id, start_date, is_ongoing, notes)
                        VALUES (:wid, :mid, :start, :ongoing, NULL)
                    """),
                        {
                            "wid": wid,
                            "mid": mid,
                            "start": str(random.randint(2018, 2023)),
                            "ongoing": random.choice([True, False]),
                        },
                    )
                    ser_count += 1
                print(f"    Created {ser_count} manga serializations")
                await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 28. STORY ARCS + STORY ARC ISSUES
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM story_arcs"))
    if r.scalar() == 0 and comic_series_ids:
        print("  Seeding story_arcs...")
        arcs = [
            ("Origin Story", "The hero's origin and first adventure", "1", "4", 4, False),
            ("The Dark Descent", "A darker turn as the villain rises", "5", "8", 4, False),
            ("Crisis Crossover", "Multi-series crossover event", "9", "12", 4, True),
            ("Rebirth", "A fresh start after the crisis", "13", "16", 4, False),
        ]
        arc_ids_created = []
        for arc_title, desc, start, end, count, is_crossover in arcs:
            sid = random.choice(comic_series_ids)
            existing = await session.execute(
                text("SELECT id FROM story_arcs WHERE series_id = :sid AND arc_title = :title"),
                {"sid": sid, "title": arc_title},
            )
            if existing.scalar():
                continue
            r2 = await session.execute(
                text("""
                INSERT INTO story_arcs
                    (series_id, arc_title, description, is_crossover,
                     start_issue_number, end_issue_number, issue_count,
                     sequence_number, is_prequel, is_sequel)
                VALUES (:sid, :title, :desc, :cross,
                        :start, :end, :count,
                        :seq, false, false)
                RETURNING id
            """),
                {
                    "sid": sid,
                    "title": arc_title,
                    "desc": desc,
                    "cross": is_crossover,
                    "start": start,
                    "end": end,
                    "count": count,
                    "seq": len(arc_ids_created) + 1,
                },
            )
            arc_ids_created.append(r2.scalar())
        print(f"    Created {len(arc_ids_created)} story arcs")

        # Link arcs to issues
        if arc_ids_created and all_issue_ids:
            link_count = 0
            for aid in arc_ids_created:
                for iid in random.sample(all_issue_ids, min(3, len(all_issue_ids))):
                    existing = await session.execute(
                        text(
                            "SELECT 1 FROM story_arc_issues WHERE story_arc_id = :aid AND issue_id = :iid"
                        ),
                        {"aid": aid, "iid": iid},
                    )
                    if existing.scalar():
                        continue
                    await session.execute(
                        text("""
                        INSERT INTO story_arc_issues (story_arc_id, issue_id)
                        VALUES (:aid, :iid)
                    """),
                        {"aid": aid, "iid": iid},
                    )
                    link_count += 1
            print(f"    Linked {link_count} arc-issue pairs")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 29. VARIANT COVERS
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM variant_covers"))
    if r.scalar() == 0 and all_issue_ids:
        print("  Seeding variant_covers...")
        variants = [
            ("first_print", "Standard Cover", "Alex Rivera", "1st print"),
            ("variant_artist", "Variant Cover A", "Sarah Kim", "1st print"),
            ("virgin_cover", "Virgin Variant", "Marcus Johnson", "1st print"),
            ("incentive_variant", "1:25 Incentive", "Yuki Tanaka", "1:25 ratio variant"),
            ("foil_cover", "Foil Edition", "Pat Chen", "1st print"),
            ("retailer_exclusive", "Midtown Exclusive", "Jordan Ellis", "1st print"),
            ("blank_variant", "Blank Sketch Cover", None, "1st print"),
            ("convention_exclusive", "NYCC Exclusive", "Mia Santos", "Convention exclusive"),
        ]
        for vtype, vname, artist, print_run in variants:
            iid = random.choice(all_issue_ids)
            await session.execute(
                text("""
                INSERT INTO variant_covers
                    (issue_id, variant_type, variant_name, cover_artist, print_run)
                VALUES (:iid, :vtype, :vname, :artist, :prun)
            """),
                {
                    "iid": iid,
                    "vtype": vtype,
                    "vname": vname,
                    "artist": artist,
                    "prun": print_run,
                },
            )
        print(f"    Created {len(variants)} variant covers")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # 30. PUBLISHER SERIES
    # ══════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM publisher_series"))
    if r.scalar() == 0 and publisher_ids_local:
        print("  Seeding publisher_series...")
        series_data = [
            ("Shonen Jump Manga", "Main Shonen Jump lineup", True, 50, 12),
            ("Viz Signature", "Premium manga editions for mature readers", False, 25, 8),
            ("Kodansha Comics", "Kodansha's main English manga line", True, 40, 10),
            ("Yen Press Manga", "Yen Press main manga imprint", False, 30, 6),
            ("Seven Seas Manga", "Seven Seas core manga releases", False, 20, 5),
        ]
        for title, desc, featured, total, in_lib in series_data:
            pid = random.choice(publisher_ids_local)
            existing = await session.execute(
                text(
                    "SELECT id FROM publisher_series WHERE publisher_id = :pid AND series_title = :title"
                ),
                {"pid": pid, "title": title},
            )
            if existing.scalar():
                continue
            await session.execute(
                text("""
                INSERT INTO publisher_series
                    (publisher_id, series_title, series_description,
                     is_featured, total_published_books, books_in_library)
                VALUES (:pid, :title, :desc,
                        :featured, :total, :in_lib)
            """),
                {
                    "pid": pid,
                    "title": title,
                    "desc": desc,
                    "featured": featured,
                    "total": total,
                    "in_lib": in_lib,
                },
            )
        print(f"    Created {len(series_data)} publisher series")
        await session.commit()

    # ══════════════════════════════════════════════════════════════════
    # FIX SEQUENCES
    # ══════════════════════════════════════════════════════════════════
    seq_tables = [
        "makerspace_consumables",
        "makerspace_consumable_usage",
        "makerspace_certifications",
        "makerspace_jobs",
        "makerspace_maintenance",
        "makerspace_payments",
        "makerspace_safety_incidents",
        "makerspace_waitlist",
        "makerspace_workshop_registrations",
        "equipment_checkouts",
        "equipment_agreements",
        "equipment_maintenance",
        "equipment_reservations",
        "equipment_alerts",
        "equipment_condition_logs",
        "book_challenges",
        "book_challenge_notes",
        "book_club_kits",
        "book_drops",
        "kit_contents",
        "kit_checkouts",
        "mending_queue",
        "damaged_item_records",
        "lost_item_records",
        "lost_damaged_settings",
        "claims_returned_disputes",
        "condition_changes",
        "inventory_audits",
        "shelf_reading_schedules",
        "shelf_reading_sessions",
        "shelf_reading_scans",
        "comic_issues",
        "comic_issue_creators",
        "comic_content_advisories",
        "manga_metadata",
        "manga_volume_records",
        "manga_magazines",
        "manga_serializations",
        "story_arcs",
        "variant_covers",
        "publishers",
        "publisher_series",
    ]
    for table in seq_tables:
        try:
            async with session.begin_nested():
                await session.execute(
                    text(
                        f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
                    )
                )
        except SQLAlchemyError:
            pass

    await session.commit()
    print("  Batch makerspace seeding complete!")
    return True
