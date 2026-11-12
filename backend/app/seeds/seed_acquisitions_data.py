# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

utc = timezone.utc


def _past(days: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days)


def _date_past(days: int) -> date:
    return date.today() - timedelta(days=days)


def _date_future(days: int) -> date:
    return date.today() + timedelta(days=days)


async def seed_acquisitions_data(session: AsyncSession) -> bool:

    # --- Grab reusable IDs ---
    users_r = await session.execute(
        text("SELECT id, role::text FROM users WHERE role::text NOT IN ('patron', 'child') ORDER BY id LIMIT 10")
    )
    staff = users_r.fetchall()
    if not staff:
        print("  SKIP: No staff users found")
        return False

    staff_ids = [u[0] for u in staff]
    # Map to named roles for readability
    director_id = staff_ids[0]   # sam (super_admin)
    admin_id = staff_ids[1] if len(staff_ids) > 1 else staff_ids[0]   # maria.chen
    staff_1 = staff_ids[3] if len(staff_ids) > 3 else staff_ids[0]    # lisa.patel
    staff_2 = staff_ids[4] if len(staff_ids) > 4 else staff_ids[0]    # janet.ruiz
    staff_3 = staff_ids[5] if len(staff_ids) > 5 else staff_ids[0]    # tom.nguyen

    # Get existing fund and vendor IDs
    fund_r = await session.execute(text("SELECT id, code FROM funds ORDER BY id"))
    funds = {row[1]: row[0] for row in fund_r.fetchall()}
    vendor_r = await session.execute(text("SELECT id, name FROM vendors ORDER BY id"))
    vendors = {row[1]: row[0] for row in vendor_r.fetchall()}

    if not funds or not vendors:
        print("  SKIP: No funds or vendors found")
        return False

    fund_gen = funds.get("GEN-2026", list(funds.values())[0])
    fund_fol = funds.get("FOL-2026", list(funds.values())[0])
    fund_grant = funds.get("GRANT-2026", list(funds.values())[0])
    fund_mem = funds.get("MEM-2026", list(funds.values())[0])
    fund_tech = funds.get("TECH-2026", list(funds.values())[0])

    vendor_bt = vendors.get("Baker & Taylor", list(vendors.values())[0])
    vendor_mw = vendors.get("Midwest Tape", list(vendors.values())[0])
    vendor_ingram = vendors.get("Ingram Library Services", list(vendors.values())[0])

    # Get patron purchase request IDs for linking
    ppr_r = await session.execute(text("SELECT id FROM patron_purchase_requests ORDER BY id LIMIT 5"))
    ppr_ids = [row[0] for row in ppr_r.fetchall()]

    seeded_any = False

    # ========== SELECTION LIST ITEMS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM selection_list_items"))
    if r.scalar() == 0:
        print("  Seeding selection list items...")
        items = [
            {
                "title": "Tomorrow, and Tomorrow, and Tomorrow",
                "author": "Gabrielle Zevin", "isbn": "9780593321201",
                "price": 28.00, "source": "manual", "priority": "high",
                "req_by": staff_1,
                "notes": "Multiple patron requests. Strong reviews, Goodreads Choice Award winner.",
                "status": "approved",
                "ppr_id": ppr_ids[0] if ppr_ids else None,
                "days_ago": 42,
            },
            {
                "title": "Demon Copperhead",
                "author": "Barbara Kingsolver", "isbn": "9780063251922",
                "price": 30.00, "source": "manual", "priority": "high",
                "req_by": staff_2,
                "notes": "Pulitzer Prize winner 2023. Appalachian setting resonates with our community.",
                "status": "ordered",
                "ppr_id": ppr_ids[1] if len(ppr_ids) > 1 else None,
                "days_ago": 38,
            },
            {
                "title": "The Covenant of Water",
                "author": "Abraham Verghese", "isbn": "9780802162175",
                "price": 32.00, "source": "manual", "priority": "medium",
                "req_by": admin_id,
                "notes": "Oprah Book Club pick. Literary fiction, strong holds list at other branches.",
                "status": "approved",
                "ppr_id": None,
                "days_ago": 35,
            },
            {
                "title": "Holly",
                "author": "Stephen King", "isbn": "9781668016138",
                "price": 19.99, "source": "manual", "priority": "high",
                "req_by": staff_3,
                "notes": "Stephen King always circulates well. Holly Gibney series popular with patrons.",
                "status": "ordered",
                "ppr_id": None,
                "days_ago": 30,
            },
            {
                "title": "Yellowface",
                "author": "R.F. Kuang", "isbn": "9780063250833",
                "price": 27.99, "source": "open_library", "priority": "medium",
                "req_by": staff_1,
                "notes": "Satirical literary fiction. Good fit for book club collection.",
                "status": "pending",
                "ppr_id": None,
                "days_ago": 25,
            },
            {
                "title": "The Fraud",
                "author": "Zadie Smith", "isbn": "9780525558965",
                "price": 28.00, "source": "manual", "priority": "low",
                "req_by": staff_2,
                "notes": "Historical fiction. Zadie Smith has dedicated readership here.",
                "status": "pending",
                "ppr_id": None,
                "days_ago": 20,
            },
            {
                "title": "King: A Life",
                "author": "Jonathan Eig", "isbn": "9780374279295",
                "price": 35.00, "source": "manual", "priority": "high",
                "req_by": admin_id,
                "notes": "Definitive MLK biography. Pulitzer finalist. Reference collection candidate.",
                "status": "approved",
                "ppr_id": None,
                "days_ago": 18,
            },
            {
                "title": "The Wager",
                "author": "David Grann", "isbn": "9780385534260",
                "price": 30.00, "source": "google_books", "priority": "medium",
                "req_by": staff_3,
                "notes": "Nonfiction adventure. David Grann titles always do well.",
                "status": "pending",
                "ppr_id": ppr_ids[2] if len(ppr_ids) > 2 else None,
                "days_ago": 14,
            },
            {
                "title": "Birnam Wood",
                "author": "Eleanor Catton", "isbn": "9780374110338",
                "price": 28.00, "source": "manual", "priority": "low",
                "req_by": staff_1,
                "notes": "Literary thriller from Booker Prize winner. Limited local demand likely.",
                "status": "rejected",
                "ppr_id": None,
                "days_ago": 12,
            },
            {
                "title": "I'm Glad My Mom Died",
                "author": "Jennette McCurdy", "isbn": "9781982185824",
                "price": 27.99, "source": "manual", "priority": "medium",
                "req_by": staff_2,
                "notes": "Memoir, very popular with YA crossover audience. 30+ holds at county.",
                "status": "approved",
                "ppr_id": ppr_ids[3] if len(ppr_ids) > 3 else None,
                "days_ago": 8,
            },
        ]
        for item in items:
            await session.execute(text("""
                INSERT INTO selection_list_items
                    (title, author, isbn, estimated_price, source, priority,
                     requested_by_id, notes, status, purchase_request_id,
                     created_at, updated_at)
                VALUES
                    (:title, :author, :isbn, :price, :source, :priority,
                     :req_by, :notes, :status, :ppr_id,
                     :created_at, :updated_at)
            """), {
                "title": item["title"], "author": item["author"],
                "isbn": item["isbn"], "price": item["price"],
                "source": item["source"], "priority": item["priority"],
                "req_by": item["req_by"], "notes": item["notes"],
                "status": item["status"], "ppr_id": item["ppr_id"],
                "created_at": _past(item["days_ago"]),
                "updated_at": _past(max(1, item["days_ago"] - 5)),
            })
        seeded_any = True
        print(f"    Inserted {len(items)} selection list items")

    # ========== ORDER TEMPLATES ==========
    r = await session.execute(text("SELECT COUNT(*) FROM order_templates"))
    if r.scalar() == 0:
        print("  Seeding order templates...")

        fiction_items = json.dumps([
            {"title": "", "author": "", "isbn": "", "quantity": 1, "unit_price": None,
             "notes": "New release - adult fiction"},
            {"title": "", "author": "", "isbn": "", "quantity": 1, "unit_price": None,
             "notes": "New release - adult fiction"},
            {"title": "", "author": "", "isbn": "", "quantity": 2, "unit_price": None,
             "notes": "High-demand title - order 2 copies"},
            {"title": "", "author": "", "isbn": "", "quantity": 1, "unit_price": None,
             "notes": "Staff pick / book club selection"},
        ])

        childrens_items = json.dumps([
            {"title": "Diary of a Wimpy Kid (latest)", "author": "Jeff Kinney",
             "isbn": "", "quantity": 3, "unit_price": 14.99,
             "notes": "Always high demand during summer"},
            {"title": "Dog Man (latest)", "author": "Dav Pilkey",
             "isbn": "", "quantity": 3, "unit_price": 12.99,
             "notes": "Graphic novel - very popular"},
            {"title": "Wings of Fire (latest)", "author": "Tui T. Sutherland",
             "isbn": "", "quantity": 2, "unit_price": 16.99,
             "notes": "Series - check which volumes we need"},
            {"title": "Percy Jackson (latest)", "author": "Rick Riordan",
             "isbn": "", "quantity": 2, "unit_price": 19.99,
             "notes": "Renewed interest from Disney+ series"},
            {"title": "", "author": "", "isbn": "", "quantity": 2, "unit_price": None,
             "notes": "Summer reading list title - TBD"},
            {"title": "", "author": "", "isbn": "", "quantity": 2, "unit_price": None,
             "notes": "Summer reading list title - TBD"},
        ])

        await session.execute(text("""
            INSERT INTO order_templates
                (name, description, vendor_id, fund_id, created_by_id, is_shared,
                 template_items, created_at, updated_at)
            VALUES
                (:n1, :d1, :v1, :f1, :c1, true, :i1, :ca1, :ua1),
                (:n2, :d2, :v2, :f2, :c2, true, :i2, :ca2, :ua2)
        """), {
            "n1": "Monthly New Fiction",
            "d1": "Template for monthly new adult fiction acquisitions. Fill in titles from review journals and patron requests.",
            "v1": vendor_bt, "f1": fund_gen, "c1": staff_1,
            "i1": fiction_items, "ca1": _past(90), "ua1": _past(15),
            "n2": "Summer Reading Restock",
            "d2": "Annual template for restocking popular children's series before summer reading program. Adjust quantities based on holds list.",
            "v2": vendor_ingram, "f2": fund_fol, "c2": admin_id,
            "i2": childrens_items, "ca2": _past(180), "ua2": _past(60),
        })
        seeded_any = True
        print("    Inserted 2 order templates")

    # ========== ADDITIONAL PURCHASE ORDERS ==========
    r = await session.execute(text("SELECT COUNT(*) FROM purchase_orders WHERE po_number = 'PO-2026-009'"))
    if r.scalar() == 0:
        print("  Seeding additional purchase orders (PO-2026-009 through PO-2026-012)...")

        # --- PO-009: Draft (just created, not yet submitted) ---
        await session.execute(text("""
            INSERT INTO purchase_orders
                (po_number, vendor_id, fund_id, order_date, status, total_amount,
                 notes, created_by_id, created_at, updated_at)
            VALUES (:po, :vid, :fid, :od, 'draft', :total, :notes, :cby, :ca, :ua)
        """), {
            "po": "PO-2026-009", "vid": vendor_bt, "fid": fund_gen,
            "od": _date_past(2), "total": Decimal("156.97"),
            "notes": "Draft - gathering remaining titles for monthly fiction order",
            "cby": staff_1, "ca": _past(2), "ua": _past(1),
        })
        po_r = await session.execute(text("SELECT id FROM purchase_orders WHERE po_number = 'PO-2026-009'"))
        po_id = po_r.scalar()
        for title, author, isbn, qty, price in [
            ("Tomorrow, and Tomorrow, and Tomorrow", "Gabrielle Zevin", "9780593321201", 1, "28.00"),
            ("Yellowface", "R.F. Kuang", "9780063250833", 2, "27.99"),
            ("The Covenant of Water", "Abraham Verghese", "9780802162175", 1, "32.00"),
            ("Holly", "Stephen King", "9781668016138", 1, "12.99"),
        ]:
            await session.execute(text("""
                INSERT INTO purchase_order_items
                    (purchase_order_id, title, author, isbn, quantity, unit_price,
                     received_quantity, created_at, updated_at)
                VALUES (:pid, :t, :a, :i, :q, :p, 0, :ca, :ua)
            """), {"pid": po_id, "t": title, "a": author, "i": isbn,
                   "q": qty, "p": Decimal(price), "ca": _past(2), "ua": _past(1)})

        # --- PO-010: Approved (ready to send to vendor) ---
        await session.execute(text("""
            INSERT INTO purchase_orders
                (po_number, vendor_id, fund_id, order_date, status, total_amount,
                 notes, created_by_id, approved_by_id, approved_at,
                 created_at, updated_at)
            VALUES (:po, :vid, :fid, :od, 'approved', :total, :notes, :cby, :aby, :aat, :ca, :ua)
        """), {
            "po": "PO-2026-010", "vid": vendor_ingram, "fid": fund_grant,
            "od": _date_past(5), "total": Decimal("245.94"),
            "notes": "Grant-funded STEM materials for summer program",
            "cby": staff_2, "aby": admin_id, "aat": _past(3),
            "ca": _past(5), "ua": _past(3),
        })
        po_r = await session.execute(text("SELECT id FROM purchase_orders WHERE po_number = 'PO-2026-010'"))
        po_id = po_r.scalar()
        for title, author, isbn, qty, price in [
            ("The Code Breaker (YA Edition)", "Walter Isaacson", "9781534446427", 2, "18.99"),
            ("Hidden Figures Young Readers Edition", "Margot Lee Shetterly", "9780062662378", 2, "16.99"),
            ("Braiding Sweetgrass for Young Adults", "Robin Wall Kimmerer", "9781728458984", 2, "22.99"),
            ("What If? 2", "Randall Munroe", "9780525537113", 3, "30.00"),
        ]:
            await session.execute(text("""
                INSERT INTO purchase_order_items
                    (purchase_order_id, title, author, isbn, quantity, unit_price,
                     received_quantity, created_at, updated_at)
                VALUES (:pid, :t, :a, :i, :q, :p, 0, :ca, :ua)
            """), {"pid": po_id, "t": title, "a": author, "i": isbn,
                   "q": qty, "p": Decimal(price), "ca": _past(5), "ua": _past(3)})

        # --- PO-011: Partially received (some items checked in) ---
        await session.execute(text("""
            INSERT INTO purchase_orders
                (po_number, vendor_id, fund_id, order_date, expected_delivery,
                 status, total_amount, notes, created_by_id, approved_by_id, approved_at,
                 created_at, updated_at)
            VALUES (:po, :vid, :fid, :od, :ed, 'partially_received', :total, :notes,
                    :cby, :aby, :aat, :ca, :ua)
        """), {
            "po": "PO-2026-011", "vid": vendor_bt, "fid": fund_mem,
            "od": _date_past(21), "ed": _date_past(7),
            "total": Decimal("189.94"),
            "notes": "Memorial fund - donated in memory of Ruth Albright. Box 1 of 2 received.",
            "cby": admin_id, "aby": director_id, "aat": _past(19),
            "ca": _past(21), "ua": _past(3),
        })
        po_r = await session.execute(text("SELECT id FROM purchase_orders WHERE po_number = 'PO-2026-011'"))
        po_id = po_r.scalar()
        for title, author, isbn, qty, price, recv in [
            ("When Breath Becomes Air", "Paul Kalanithi", "9780812988406", 2, "17.00", 2),
            ("The Year of Magical Thinking", "Joan Didion", "9781400078431", 1, "16.95", 1),
            ("Being Mortal", "Atul Gawande", "9780805095159", 2, "16.00", 0),
            ("Tuesdays with Morrie", "Mitch Albom", "9780767905923", 2, "15.99", 0),
            ("H Is for Hawk", "Helen Macdonald", "9780802124739", 1, "17.00", 1),
        ]:
            await session.execute(text("""
                INSERT INTO purchase_order_items
                    (purchase_order_id, title, author, isbn, quantity, unit_price,
                     received_quantity, created_at, updated_at)
                VALUES (:pid, :t, :a, :i, :q, :p, :r, :ca, :ua)
            """), {"pid": po_id, "t": title, "a": author, "i": isbn,
                   "q": qty, "p": Decimal(price), "r": recv,
                   "ca": _past(21), "ua": _past(3)})

        # --- PO-012: Submitted (sent to vendor, awaiting shipment) ---
        await session.execute(text("""
            INSERT INTO purchase_orders
                (po_number, vendor_id, fund_id, order_date, expected_delivery,
                 status, total_amount, notes, created_by_id, approved_by_id, approved_at,
                 created_at, updated_at)
            VALUES (:po, :vid, :fid, :od, :ed, 'submitted', :total, :notes,
                    :cby, :aby, :aat, :ca, :ua)
        """), {
            "po": "PO-2026-012", "vid": vendor_mw, "fid": fund_tech,
            "od": _date_past(10), "ed": _date_future(4),
            "total": Decimal("209.70"),
            "notes": "AV materials - new DVD and audiobook releases for spring",
            "cby": staff_3, "aby": admin_id, "aat": _past(9),
            "ca": _past(10), "ua": _past(8),
        })
        po_r = await session.execute(text("SELECT id FROM purchase_orders WHERE po_number = 'PO-2026-012'"))
        po_id = po_r.scalar()
        for title, author, isbn, qty, price in [
            ("Killers of the Flower Moon (DVD)", "Martin Scorsese", "5099301", 2, "29.95"),
            ("The Holdovers (DVD)", "Alexander Payne", "5099302", 1, "24.95"),
            ("Iron Flame (Audiobook)", "Rebecca Yarros", "9781250362070", 1, "44.99"),
            ("Tom Clancy: Red Winter (Audiobook)", "Marc Cameron", "9780593632710", 2, "39.93"),
        ]:
            await session.execute(text("""
                INSERT INTO purchase_order_items
                    (purchase_order_id, title, author, isbn, quantity, unit_price,
                     received_quantity, created_at, updated_at)
                VALUES (:pid, :t, :a, :i, :q, :p, 0, :ca, :ua)
            """), {"pid": po_id, "t": title, "a": author, "i": isbn,
                   "q": qty, "p": Decimal(price), "ca": _past(10), "ua": _past(8)})

        seeded_any = True
        print("    Inserted 4 purchase orders with 17 line items")

    if seeded_any:
        print("  Acquisitions seed data complete.")
    else:
        print("  Acquisitions data already exists, skipping.")

    return True
