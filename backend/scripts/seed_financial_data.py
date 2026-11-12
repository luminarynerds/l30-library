#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive Financial Seed Data for LSC Library.

Seeds realistic financial data including:
- Fines at various amounts (overdue, lost item, damaged item, other)
- Paid fines with payment records
- Waived fines with reasons
- Lost item charges
- Damaged item charges
- Fine payment history across multiple payment methods
- Refund records (overpayment corrections)
- Fee exemptions (staff-waived, policy-based)
- Fund management data (multiple funds, allocations, budget tracking)
- Fund transactions via purchase orders
- Payment plans for large balances
- Fine policies for different item types
"""
import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.fine import (
    Fine,
    FinePaymentHistory,
    FinePolicy,
    FineStatus,
    FineType,
    FinePolicyType,
    PaymentMethod,
    PaymentPlan,
    PaymentPlanFrequency,
    PaymentPlanStatus,
)
from app.models.acquisition import (
    Fund,
    FundStatus,
    Vendor,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)
from app.models.circulation import Checkout, CheckoutStatus
from app.models.catalog import CatalogItem

NOW = datetime.now(timezone.utc)


def days_ago(n: int) -> datetime:
    return NOW - timedelta(days=n)


import uuid

def receipt_num(prefix: str, idx: int) -> str:
    # Include short UUID to avoid duplicates on re-runs
    short_id = uuid.uuid4().hex[:6]
    return f"{prefix}-{NOW.strftime('%Y%m')}-{idx:04d}-{short_id}"


async def get_or_create_users(db):
    """Get existing patron and staff users, or note what's available."""
    result = await db.execute(
        select(User).where(User.role == UserRole.PATRON).limit(10)
    )
    patrons = list(result.scalars().all())

    result = await db.execute(
        select(User).where(User.role.in_([UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN])).limit(5)
    )
    staff = list(result.scalars().all())

    if not patrons or not staff:
        print("WARNING: No patron or staff users found. Run seed_test_accounts.py first.")
        return None, None

    return patrons, staff


async def get_checkouts(db):
    """Get existing checkout records."""
    result = await db.execute(select(Checkout).limit(20))
    return list(result.scalars().all())


async def get_catalog_items(db):
    """Get existing catalog items."""
    result = await db.execute(select(CatalogItem).limit(20))
    return list(result.scalars().all())


async def seed_fine_policies(db, staff):
    """Seed fine calculation policies for different item types."""
    print("\n--- Seeding Fine Policies ---")

    staff_user = staff[0]
    policies = [
        {
            "name": "Standard Book Fine",
            "description": "Standard daily fine for overdue books",
            "policy_type": FinePolicyType.daily_rate,
            "applies_to_item_types": "book,ebook",
            "applies_to_user_roles": "all",
            "fine_per_day": Decimal("0.25"),
            "maximum_cap": Decimal("10.00"),
            "grace_period_hours": 24,
            "minimum_fine_amount": Decimal("0.25"),
            "maximum_daily_fine": Decimal("5.00"),
            "is_active": True,
            "applies_on_weekends": False,
            "applies_on_holidays": False,
            "created_by_id": staff_user.id,
        },
        {
            "name": "DVD/Bluray Fine",
            "description": "Higher daily fine for AV materials due to demand",
            "policy_type": FinePolicyType.daily_rate,
            "applies_to_item_types": "dvd,bluray",
            "applies_to_user_roles": "all",
            "fine_per_day": Decimal("1.00"),
            "maximum_cap": Decimal("25.00"),
            "grace_period_hours": 0,
            "minimum_fine_amount": Decimal("1.00"),
            "maximum_daily_fine": Decimal("10.00"),
            "is_active": True,
            "applies_on_weekends": True,
            "applies_on_holidays": False,
            "created_by_id": staff_user.id,
        },
        {
            "name": "Tiered Overdue Fine",
            "description": "Progressive fine structure: escalates with duration",
            "policy_type": FinePolicyType.tiered,
            "applies_to_item_types": "all",
            "applies_to_user_roles": "PATRON",
            "fine_per_day": Decimal("0.25"),
            "tiered_configuration": '[{"days": [1, 7], "rate": 0.25}, {"days": [8, 14], "rate": 0.50}, {"days": [15, 999], "rate": 1.00}]',
            "maximum_cap": Decimal("25.00"),
            "grace_period_hours": 12,
            "minimum_fine_amount": Decimal("0.25"),
            "maximum_daily_fine": Decimal("25.00"),
            "is_active": True,
            "applies_on_weekends": True,
            "applies_on_holidays": False,
            "created_by_id": staff_user.id,
        },
        {
            "name": "Children's Materials Fine",
            "description": "Reduced fine rate for children's materials",
            "policy_type": FinePolicyType.daily_rate,
            "applies_to_item_types": "book,audiobook",
            "applies_to_user_roles": "CHILD",
            "fine_per_day": Decimal("0.10"),
            "maximum_cap": Decimal("5.00"),
            "grace_period_hours": 48,
            "minimum_fine_amount": Decimal("0.10"),
            "maximum_daily_fine": Decimal("2.00"),
            "is_active": True,
            "applies_on_weekends": False,
            "applies_on_holidays": False,
            "created_by_id": staff_user.id,
        },
        {
            "name": "Equipment Maximum Cap",
            "description": "Flat maximum cap for equipment regardless of days",
            "policy_type": FinePolicyType.maximum_cap,
            "applies_to_item_types": "equipment",
            "applies_to_user_roles": "all",
            "fine_per_day": Decimal("5.00"),
            "maximum_cap": Decimal("50.00"),
            "grace_period_hours": 0,
            "minimum_fine_amount": Decimal("5.00"),
            "maximum_daily_fine": Decimal("50.00"),
            "is_active": True,
            "applies_on_weekends": True,
            "applies_on_holidays": True,
            "created_by_id": staff_user.id,
        },
    ]

    created = 0
    for policy_data in policies:
        existing = await db.execute(
            select(FinePolicy).where(FinePolicy.name == policy_data["name"])
        )
        if existing.scalar_one_or_none():
            print(f"  SKIP: {policy_data['name']} (exists)")
            continue

        policy = FinePolicy(**policy_data)
        db.add(policy)
        created += 1
        print(f"  + {policy_data['name']} ({policy_data['policy_type'].value})")

    await db.flush()
    print(f"  Fine policies created: {created}")
    return created


async def seed_fines(db, patrons, staff, checkouts):
    """Seed fines at various amounts and statuses."""
    print("\n--- Seeding Fines ---")

    # Check if we already have seeded fines (avoid duplicates)
    existing_count = await db.execute(select(func.count(Fine.id)))
    if (existing_count.scalar() or 0) > 30:
        print("  SKIP: Fines already seeded (>30 exist). Returning existing fines.")
        result = await db.execute(select(Fine))
        return list(result.scalars().all())

    _ = staff[0]
    checkout_ids = [c.id for c in checkouts] if checkouts else [None]
    created_fines = []

    # === UNPAID OVERDUE FINES (various amounts) ===
    unpaid_overdue = [
        {"amount": Decimal("0.25"), "desc": "1 day overdue - The Great Gatsby", "days": 5},
        {"amount": Decimal("0.75"), "desc": "3 days overdue - To Kill a Mockingbird", "days": 10},
        {"amount": Decimal("1.75"), "desc": "7 days overdue - 1984 by George Orwell", "days": 15},
        {"amount": Decimal("3.25"), "desc": "10 days overdue - Pride and Prejudice", "days": 20},
        {"amount": Decimal("5.50"), "desc": "14 days overdue - The Catcher in the Rye", "days": 30},
        {"amount": Decimal("8.75"), "desc": "21 days overdue - Brave New World", "days": 45},
        {"amount": Decimal("12.00"), "desc": "25 days overdue - Lord of the Flies", "days": 60},
        {"amount": Decimal("25.00"), "desc": "Maximum cap reached - Equipment tripod", "days": 90},
    ]

    for i, data in enumerate(unpaid_overdue):
        patron = patrons[i % len(patrons)]
        fine = Fine(
            user_id=patron.id,
            checkout_id=random.choice(checkout_ids),
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=data["amount"],
            amount_paid=Decimal("0.00"),
            description=data["desc"],
            created_at=days_ago(data["days"]),
        )
        db.add(fine)
        created_fines.append(fine)
    print(f"  + {len(unpaid_overdue)} unpaid overdue fines ($0.25 - $25.00)")

    # === PAID FINES (with various payment records) ===
    paid_fines_data = [
        {"amount": Decimal("1.50"), "desc": "Overdue - Harry Potter and the Sorcerer's Stone", "days": 45, "method": PaymentMethod.cash},
        {"amount": Decimal("3.00"), "desc": "Overdue - The Hobbit", "days": 40, "method": PaymentMethod.card},
        {"amount": Decimal("5.00"), "desc": "Overdue - Dune by Frank Herbert", "days": 35, "method": PaymentMethod.online},
        {"amount": Decimal("7.50"), "desc": "Overdue - The Shining", "days": 50, "method": PaymentMethod.check},
        {"amount": Decimal("10.00"), "desc": "Overdue - Game of Thrones", "days": 55, "method": PaymentMethod.card},
        {"amount": Decimal("15.00"), "desc": "Overdue - Complete Works of Shakespeare", "days": 60, "method": PaymentMethod.online},
        {"amount": Decimal("2.25"), "desc": "Overdue - Cat in the Hat (children's)", "days": 30, "method": PaymentMethod.cash},
        {"amount": Decimal("4.75"), "desc": "Overdue - Hunger Games DVD", "days": 25, "method": PaymentMethod.card},
        {"amount": Decimal("6.00"), "desc": "Overdue - National Geographic Magazine set", "days": 38, "method": PaymentMethod.cash},
        {"amount": Decimal("20.00"), "desc": "Overdue - Laptop charger (equipment)", "days": 70, "method": PaymentMethod.online},
    ]

    for i, data in enumerate(paid_fines_data):
        patron = patrons[i % len(patrons)]
        paid_date = days_ago(data["days"] - 5)
        fine = Fine(
            user_id=patron.id,
            checkout_id=random.choice(checkout_ids),
            fine_type=FineType.overdue,
            status=FineStatus.paid,
            amount=data["amount"],
            amount_paid=data["amount"],
            description=data["desc"],
            created_at=days_ago(data["days"]),
            paid_at=paid_date,
        )
        db.add(fine)
        created_fines.append(fine)
    print(f"  + {len(paid_fines_data)} paid overdue fines ($1.50 - $20.00)")

    # === PARTIALLY PAID FINES ===
    partial_fines_data = [
        {"amount": Decimal("10.00"), "paid": Decimal("5.00"), "desc": "Partial - Overdue encyclopedia set", "days": 40},
        {"amount": Decimal("25.00"), "paid": Decimal("10.00"), "desc": "Partial - Overdue equipment (projector)", "days": 55},
        {"amount": Decimal("15.00"), "paid": Decimal("7.50"), "desc": "Partial - Overdue AV collection", "days": 35},
    ]

    for i, data in enumerate(partial_fines_data):
        patron = patrons[i % len(patrons)]
        fine = Fine(
            user_id=patron.id,
            checkout_id=random.choice(checkout_ids),
            fine_type=FineType.overdue,
            status=FineStatus.partial,
            amount=data["amount"],
            amount_paid=data["paid"],
            description=data["desc"],
            created_at=days_ago(data["days"]),
        )
        db.add(fine)
        created_fines.append(fine)
    print(f"  + {len(partial_fines_data)} partially paid fines")

    # === WAIVED FINES (with reasons) ===
    waived_fines_data = [
        {"amount": Decimal("2.50"), "desc": "Overdue - Weather emergency closure", "reason": "Library closed due to ice storm; patron could not return items", "days": 30},
        {"amount": Decimal("5.00"), "desc": "Overdue - Medical emergency", "reason": "Patron hospitalized; medical documentation provided", "days": 25},
        {"amount": Decimal("3.75"), "desc": "Overdue - First-time offender waiver", "reason": "First overdue fine per library goodwill policy; patron warned", "days": 20},
        {"amount": Decimal("1.50"), "desc": "Overdue - System error", "reason": "Due date was incorrectly set by system during catalog migration", "days": 15},
        {"amount": Decimal("8.00"), "desc": "Overdue - Senior citizen hardship", "reason": "Financial hardship waiver per board policy FIN-2024-03 for seniors", "days": 35},
        {"amount": Decimal("12.00"), "desc": "Overdue - Staff error at checkout", "reason": "Staff failed to scan renewal; patron had attempted renewal on time", "days": 40},
        {"amount": Decimal("4.25"), "desc": "Overdue - Community service exchange", "reason": "Patron completed 2 hours of library volunteer work in lieu of fine", "days": 22},
        {"amount": Decimal("6.50"), "desc": "Overdue - Reading program participant", "reason": "Waived as part of Summer Reading Program incentive per policy", "days": 18},
    ]

    for i, data in enumerate(waived_fines_data):
        patron = patrons[i % len(patrons)]
        waiver_staff = staff[i % len(staff)]
        waived_date = days_ago(data["days"] - 3)
        fine = Fine(
            user_id=patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.waived,
            amount=data["amount"],
            amount_paid=Decimal("0.00"),
            description=data["desc"],
            notes=data["reason"],
            created_at=days_ago(data["days"]),
            waived_at=waived_date,
            waived_by_id=waiver_staff.id,
        )
        db.add(fine)
        created_fines.append(fine)
    print(f"  + {len(waived_fines_data)} waived fines with reasons")

    # === LOST ITEM CHARGES ===
    lost_items_data = [
        {"amount": Decimal("25.00"), "desc": "Lost - The Alchemist by Paulo Coelho (replacement cost)", "status": FineStatus.unpaid, "days": 60},
        {"amount": Decimal("35.00"), "desc": "Lost - Bluray box set Game of Thrones S1", "status": FineStatus.unpaid, "days": 45},
        {"amount": Decimal("15.99"), "desc": "Lost - Where the Crawdads Sing (paperback)", "status": FineStatus.paid, "days": 80},
        {"amount": Decimal("29.95"), "desc": "Lost - JavaScript: The Good Parts", "status": FineStatus.paid, "days": 70},
        {"amount": Decimal("45.00"), "desc": "Lost - Chemistry textbook (reference)", "status": FineStatus.unpaid, "days": 30},
        {"amount": Decimal("12.99"), "desc": "Lost - Diary of a Wimpy Kid (children's)", "status": FineStatus.waived, "days": 50},
        {"amount": Decimal("89.95"), "desc": "Lost - TI-84 Calculator (equipment)", "status": FineStatus.unpaid, "days": 20},
        {"amount": Decimal("19.99"), "desc": "Lost - Becoming by Michelle Obama (audiobook CD)", "status": FineStatus.paid, "days": 65},
    ]

    for i, data in enumerate(lost_items_data):
        patron = patrons[i % len(patrons)]
        fine = Fine(
            user_id=patron.id,
            fine_type=FineType.lost_item,
            status=data["status"],
            amount=data["amount"],
            amount_paid=data["amount"] if data["status"] == FineStatus.paid else Decimal("0.00"),
            description=data["desc"],
            notes="Lost item charge per replacement cost policy" if data["status"] != FineStatus.waived else "Waived: Item was found and returned in good condition after charge was assessed",
            created_at=days_ago(data["days"]),
            paid_at=days_ago(data["days"] - 10) if data["status"] == FineStatus.paid else None,
            waived_at=days_ago(data["days"] - 5) if data["status"] == FineStatus.waived else None,
            waived_by_id=staff[0].id if data["status"] == FineStatus.waived else None,
        )
        db.add(fine)
        created_fines.append(fine)
    print(f"  + {len(lost_items_data)} lost item charges ($12.99 - $89.95)")

    # === DAMAGED ITEM CHARGES ===
    damaged_items_data = [
        {"amount": Decimal("6.25"), "desc": "Damaged - Water stain on Educated by Tara Westover (minor, 25% of $25)", "status": FineStatus.paid, "days": 55},
        {"amount": Decimal("12.50"), "desc": "Damaged - Broken spine on Atlas of the World (moderate, 50% of $25)", "status": FineStatus.unpaid, "days": 40},
        {"amount": Decimal("25.00"), "desc": "Damaged - DVD disc scratched beyond repair (destroyed, 100%)", "status": FineStatus.paid, "days": 30},
        {"amount": Decimal("3.75"), "desc": "Damaged - Torn dust jacket on novel (minor, 25% of $15)", "status": FineStatus.waived, "days": 20},
        {"amount": Decimal("17.50"), "desc": "Damaged - Coffee spill on cookbook (moderate, 50% of $35)", "status": FineStatus.unpaid, "days": 15},
        {"amount": Decimal("45.00"), "desc": "Damaged - Laptop charger frayed cable (destroyed, 100% of $45)", "status": FineStatus.partial, "days": 35},
        {"amount": Decimal("7.50"), "desc": "Damaged - Crayon marks in children's book (minor, 25% of $30)", "status": FineStatus.paid, "days": 50},
        {"amount": Decimal("50.00"), "desc": "Damaged - Projector lens cracked (major, 50% of $100)", "status": FineStatus.unpaid, "days": 25},
    ]

    for i, data in enumerate(damaged_items_data):
        patron = patrons[i % len(patrons)]
        fine = Fine(
            user_id=patron.id,
            fine_type=FineType.damaged_item,
            status=data["status"],
            amount=data["amount"],
            amount_paid=data["amount"] if data["status"] == FineStatus.paid else (Decimal("20.00") if data["status"] == FineStatus.partial else Decimal("0.00")),
            description=data["desc"],
            notes="Damage assessed per item condition policy" if data["status"] != FineStatus.waived else "Waived: Damage was pre-existing per staff inspection records",
            created_at=days_ago(data["days"]),
            paid_at=days_ago(data["days"] - 5) if data["status"] == FineStatus.paid else None,
            waived_at=days_ago(data["days"] - 3) if data["status"] == FineStatus.waived else None,
            waived_by_id=staff[0].id if data["status"] == FineStatus.waived else None,
        )
        db.add(fine)
        created_fines.append(fine)
    print(f"  + {len(damaged_items_data)} damaged item charges ($3.75 - $50.00)")

    # === OTHER/MISCELLANEOUS FINES ===
    other_fines_data = [
        {"amount": Decimal("5.00"), "desc": "Processing fee - Lost item claim processing", "status": FineStatus.paid, "days": 40},
        {"amount": Decimal("5.00"), "desc": "Processing fee - Interlibrary loan replacement", "status": FineStatus.unpaid, "days": 20},
        {"amount": Decimal("10.00"), "desc": "Replacement library card fee", "status": FineStatus.paid, "days": 60},
        {"amount": Decimal("2.00"), "desc": "Print job refund reversal - incorrect refund issued", "status": FineStatus.paid, "days": 15},
    ]

    for i, data in enumerate(other_fines_data):
        patron = patrons[i % len(patrons)]
        fine = Fine(
            user_id=patron.id,
            fine_type=FineType.other,
            status=data["status"],
            amount=data["amount"],
            amount_paid=data["amount"] if data["status"] == FineStatus.paid else Decimal("0.00"),
            description=data["desc"],
            created_at=days_ago(data["days"]),
            paid_at=days_ago(data["days"] - 3) if data["status"] == FineStatus.paid else None,
        )
        db.add(fine)
        created_fines.append(fine)
    print(f"  + {len(other_fines_data)} other/miscellaneous charges")

    await db.flush()
    total = len(created_fines)
    print(f"  Total fines created: {total}")
    return created_fines


async def seed_payment_history(db, fines, patrons, staff):
    """Seed detailed payment history for paid and partially paid fines."""
    print("\n--- Seeding Payment History ---")

    # Check if payment history already exists
    existing_count = await db.execute(select(func.count(FinePaymentHistory.id)))
    if (existing_count.scalar() or 0) > 10:
        print("  SKIP: Payment history already seeded (>10 exist)")
        return 0

    staff_user = staff[0]
    created = 0
    refund_count = 0

    # Get all paid and partial fines
    paid_fines = [f for f in fines if f.status in (FineStatus.paid, FineStatus.partial)]

    methods = [PaymentMethod.cash, PaymentMethod.card, PaymentMethod.online, PaymentMethod.check]

    for i, fine in enumerate(paid_fines):
        method = methods[i % len(methods)]

        if fine.status == FineStatus.paid:
            # Single full payment
            payment = FinePaymentHistory(
                fine_id=fine.id,
                user_id=fine.user_id,
                amount=fine.amount_paid,
                payment_method=method,
                notes=f"Full payment received via {method.value}",
                receipt_number=receipt_num("PAY", created + 1),
                processed_by_id=staff_user.id,
            )
            db.add(payment)
            created += 1

        elif fine.status == FineStatus.partial:
            # Multiple partial payments
            remaining = fine.amount_paid
            payment_num = 0
            while remaining > 0:
                payment_num += 1
                chunk = min(remaining, Decimal("5.00"))
                payment = FinePaymentHistory(
                    fine_id=fine.id,
                    user_id=fine.user_id,
                    amount=chunk,
                    payment_method=methods[(i + payment_num) % len(methods)],
                    notes=f"Partial payment {payment_num}",
                    receipt_number=receipt_num("PAY", created + 1),
                    processed_by_id=staff_user.id,
                )
                db.add(payment)
                created += 1
                remaining -= chunk

    print(f"  + {created} payment history records")

    # === REFUND RECORDS (overpayment corrections) ===
    # Refunds are recorded as negative payment history entries
    refund_data = [
        {
            "amount": Decimal("-5.00"),
            "notes": "Refund: Overpayment on fine - patron paid $10 on $5 fine, $5 returned via cash",
            "method": PaymentMethod.cash,
            "days": 25,
        },
        {
            "amount": Decimal("-15.99"),
            "notes": "Refund: Lost item found and returned in good condition; full charge reversed to card",
            "method": PaymentMethod.card,
            "days": 40,
        },
        {
            "amount": Decimal("-3.75"),
            "notes": "Refund: Damage charge reversed after staff re-inspection found pre-existing damage",
            "method": PaymentMethod.card,
            "days": 18,
        },
        {
            "amount": Decimal("-25.00"),
            "notes": "Refund: Lost item replacement cost refunded; item recovered from book drop at other branch",
            "method": PaymentMethod.check,
            "days": 55,
        },
        {
            "amount": Decimal("-2.00"),
            "notes": "Refund: System error double-charged fine; duplicate payment reversed",
            "method": PaymentMethod.online,
            "days": 10,
        },
    ]

    # Use paid fines for refund associations
    paid_fine_list = [f for f in fines if f.status == FineStatus.paid]
    for i, ref_data in enumerate(refund_data):
        if i >= len(paid_fine_list):
            break
        patron = patrons[i % len(patrons)]
        refund = FinePaymentHistory(
            fine_id=paid_fine_list[i].id,
            user_id=patron.id,
            amount=ref_data["amount"],
            payment_method=ref_data["method"],
            notes=ref_data["notes"],
            receipt_number=receipt_num("REF", i + 1),
            processed_by_id=staff[i % len(staff)].id,
        )
        db.add(refund)
        refund_count += 1

    print(f"  + {refund_count} refund records")

    await db.flush()
    return created + refund_count


async def seed_fee_exemptions(db, patrons, staff):
    """Seed fee exemption records as waived fines with specific policy reasons."""
    print("\n--- Seeding Fee Exemptions ---")

    exemptions = [
        {
            "amount": Decimal("5.00"),
            "desc": "Fee exemption - Senior citizen discount per Policy SEN-001",
            "reason": "EXEMPTION: Senior citizen (65+) fee waiver per board resolution 2025-12. Annual exemption for overdue fines up to $10.",
            "type": FineType.overdue,
        },
        {
            "amount": Decimal("3.50"),
            "desc": "Fee exemption - Low-income family program",
            "reason": "EXEMPTION: Qualified under Low-Income Family Library Access Program. Income verification on file. All fines under $5 waived per policy LIF-2025.",
            "type": FineType.overdue,
        },
        {
            "amount": Decimal("12.00"),
            "desc": "Fee exemption - Teacher/educator discount",
            "reason": "EXEMPTION: Verified K-12 educator. Annual fine forgiveness up to $25 per Educator Partnership Program agreement.",
            "type": FineType.overdue,
        },
        {
            "amount": Decimal("8.50"),
            "desc": "Fee exemption - Disability accommodation",
            "reason": "EXEMPTION: Patron has documented disability affecting ability to return items on time. Reasonable accommodation per ADA compliance policy.",
            "type": FineType.overdue,
        },
        {
            "amount": Decimal("25.00"),
            "desc": "Fee exemption - Lost item (natural disaster)",
            "reason": "EXEMPTION: Item lost due to house fire. Insurance claim documentation provided. Full replacement cost waived per Emergency Hardship Policy EHP-2025.",
            "type": FineType.lost_item,
        },
        {
            "amount": Decimal("6.25"),
            "desc": "Fee exemption - Military deployment",
            "reason": "EXEMPTION: Active military deployment. All accrued fines waived per Military Family Support Policy MIL-2024. Deployment orders verified.",
            "type": FineType.overdue,
        },
        {
            "amount": Decimal("15.00"),
            "desc": "Fee exemption - Amnesty week participant",
            "reason": "EXEMPTION: Fine Amnesty Week 2025. All overdue fines waived for patrons returning materials during amnesty period Jan 15-22.",
            "type": FineType.overdue,
        },
        {
            "amount": Decimal("4.00"),
            "desc": "Fee exemption - Student financial aid recipient",
            "reason": "EXEMPTION: Verified college student receiving financial aid. Fines under $5 waived per Student Access Initiative policy.",
            "type": FineType.overdue,
        },
    ]

    created = 0
    for i, exemption in enumerate(exemptions):
        patron = patrons[i % len(patrons)]
        waiver_staff = staff[i % len(staff)]
        fine = Fine(
            user_id=patron.id,
            fine_type=exemption["type"],
            status=FineStatus.waived,
            amount=exemption["amount"],
            amount_paid=Decimal("0.00"),
            description=exemption["desc"],
            notes=exemption["reason"],
            created_at=days_ago(random.randint(10, 60)),
            waived_at=days_ago(random.randint(5, 15)),
            waived_by_id=waiver_staff.id,
        )
        db.add(fine)
        created += 1

    await db.flush()
    print(f"  + {created} fee exemption records")
    return created


async def seed_payment_plans(db, patrons, staff):
    """Seed payment plans for patrons with large balances."""
    print("\n--- Seeding Payment Plans ---")

    plans_data = [
        {
            "total": Decimal("50.00"),
            "installment": Decimal("10.00"),
            "freq": PaymentPlanFrequency.monthly,
            "status": PaymentPlanStatus.active,
            "paid": Decimal("20.00"),
            "payments_made": 2,
            "total_expected": 5,
            "notes": "Payment plan for accumulated overdue fines. Patron in good standing.",
        },
        {
            "total": Decimal("89.95"),
            "installment": Decimal("22.49"),
            "freq": PaymentPlanFrequency.monthly,
            "status": PaymentPlanStatus.active,
            "paid": Decimal("22.49"),
            "payments_made": 1,
            "total_expected": 4,
            "notes": "Payment plan for lost TI-84 calculator replacement.",
        },
        {
            "total": Decimal("30.00"),
            "installment": Decimal("15.00"),
            "freq": PaymentPlanFrequency.biweekly,
            "status": PaymentPlanStatus.completed,
            "paid": Decimal("30.00"),
            "payments_made": 2,
            "total_expected": 2,
            "notes": "Completed plan for overdue fines. All payments received on time.",
        },
        {
            "total": Decimal("75.00"),
            "installment": Decimal("25.00"),
            "freq": PaymentPlanFrequency.monthly,
            "status": PaymentPlanStatus.defaulted,
            "paid": Decimal("25.00"),
            "payments_made": 1,
            "total_expected": 3,
            "notes": "Defaulted: Patron missed 2 consecutive payments. Account flagged for follow-up.",
        },
        {
            "total": Decimal("45.00"),
            "installment": Decimal("11.25"),
            "freq": PaymentPlanFrequency.weekly,
            "status": PaymentPlanStatus.active,
            "paid": Decimal("33.75"),
            "payments_made": 3,
            "total_expected": 4,
            "notes": "Weekly plan for damaged projector charge. One payment remaining.",
        },
        {
            "total": Decimal("20.00"),
            "installment": Decimal("10.00"),
            "freq": PaymentPlanFrequency.monthly,
            "status": PaymentPlanStatus.cancelled,
            "paid": Decimal("0.00"),
            "payments_made": 0,
            "total_expected": 2,
            "notes": "Cancelled: Fine was waived after patron provided documentation of hardship.",
        },
    ]

    created = 0
    for i, plan_data in enumerate(plans_data):
        patron = patrons[i % len(patrons)]
        creator = staff[i % len(staff)]
        start = days_ago(plan_data["payments_made"] * 30 + 10)

        plan = PaymentPlan(
            user_id=patron.id,
            total_amount=plan_data["total"],
            installment_amount=plan_data["installment"],
            frequency=plan_data["freq"],
            status=plan_data["status"],
            amount_paid=plan_data["paid"],
            payments_made=plan_data["payments_made"],
            total_payments_expected=plan_data["total_expected"],
            start_date=start,
            next_payment_date=start + timedelta(days=30) if plan_data["status"] == PaymentPlanStatus.active else None,
            completed_at=days_ago(5) if plan_data["status"] == PaymentPlanStatus.completed else None,
            reminder_enabled=plan_data["status"] == PaymentPlanStatus.active,
            notes=plan_data["notes"],
            created_by_id=creator.id,
        )
        db.add(plan)
        created += 1

    await db.flush()
    print(f"  + {created} payment plans")
    return created


async def seed_funds(db):
    """Seed multiple library funds with allocations and budget tracking."""
    print("\n--- Seeding Fund Management ---")

    fiscal_year = NOW.year
    funds_data = [
        {
            "code": f"GEN-{fiscal_year}",
            "name": "General Materials Fund",
            "description": "Primary fund for general collection development including fiction, non-fiction, and reference materials",
            "fiscal_year": fiscal_year,
            "allocated": Decimal("85000.00"),
            "encumbered": Decimal("12500.00"),
            "spent": Decimal("48750.00"),
            "status": FundStatus.ACTIVE,
        },
        {
            "code": f"YA-{fiscal_year}",
            "name": "Young Adult & Children's Fund",
            "description": "Dedicated fund for children's and young adult materials including picture books, early readers, and teen fiction",
            "fiscal_year": fiscal_year,
            "allocated": Decimal("35000.00"),
            "encumbered": Decimal("5200.00"),
            "spent": Decimal("18900.00"),
            "status": FundStatus.ACTIVE,
        },
        {
            "code": f"AV-{fiscal_year}",
            "name": "Audiovisual Materials Fund",
            "description": "Fund for DVDs, Blu-rays, CDs, vinyl records, and streaming content licenses",
            "fiscal_year": fiscal_year,
            "allocated": Decimal("25000.00"),
            "encumbered": Decimal("3800.00"),
            "spent": Decimal("14200.00"),
            "status": FundStatus.ACTIVE,
        },
        {
            "code": f"DIG-{fiscal_year}",
            "name": "Digital Resources Fund",
            "description": "Fund for e-books, digital audiobooks, online databases, and digital subscriptions",
            "fiscal_year": fiscal_year,
            "allocated": Decimal("40000.00"),
            "encumbered": Decimal("8000.00"),
            "spent": Decimal("22500.00"),
            "status": FundStatus.ACTIVE,
        },
        {
            "code": f"REF-{fiscal_year}",
            "name": "Reference & Research Fund",
            "description": "Fund for reference materials, academic journals, and research databases",
            "fiscal_year": fiscal_year,
            "allocated": Decimal("20000.00"),
            "encumbered": Decimal("2000.00"),
            "spent": Decimal("11800.00"),
            "status": FundStatus.ACTIVE,
        },
        {
            "code": f"EQP-{fiscal_year}",
            "name": "Equipment & Technology Fund",
            "description": "Fund for lendable equipment including laptops, chargers, hotspots, and makerspace tools",
            "fiscal_year": fiscal_year,
            "allocated": Decimal("15000.00"),
            "encumbered": Decimal("1500.00"),
            "spent": Decimal("9800.00"),
            "status": FundStatus.ACTIVE,
        },
        {
            "code": f"SPEC-{fiscal_year}",
            "name": "Special Collections Fund",
            "description": "Fund for local history, genealogy, rare books, and special collection acquisitions",
            "fiscal_year": fiscal_year,
            "allocated": Decimal("10000.00"),
            "encumbered": Decimal("0.00"),
            "spent": Decimal("6200.00"),
            "status": FundStatus.ACTIVE,
        },
        {
            "code": f"GEN-{fiscal_year - 1}",
            "name": "General Materials Fund (Prior Year)",
            "description": "Previous fiscal year general fund - closed",
            "fiscal_year": fiscal_year - 1,
            "allocated": Decimal("80000.00"),
            "encumbered": Decimal("0.00"),
            "spent": Decimal("78500.00"),
            "status": FundStatus.CLOSED,
        },
    ]

    created_funds = []
    for fund_data in funds_data:
        existing = await db.execute(
            select(Fund).where(Fund.code == fund_data["code"])
        )
        if existing.scalar_one_or_none():
            print(f"  SKIP: {fund_data['code']} (exists)")
            continue

        fund = Fund(
            code=fund_data["code"],
            name=fund_data["name"],
            description=fund_data["description"],
            fiscal_year=fund_data["fiscal_year"],
            allocated_amount=fund_data["allocated"],
            encumbered_amount=fund_data["encumbered"],
            spent_amount=fund_data["spent"],
            status=fund_data["status"].value if isinstance(fund_data["status"], FundStatus) else fund_data["status"],
        )
        db.add(fund)
        created_funds.append(fund)
        avail = fund_data["allocated"] - fund_data["encumbered"] - fund_data["spent"]
        print(f"  + {fund_data['code']}: {fund_data['name']} (allocated=${fund_data['allocated']}, available=${avail})")

    await db.flush()
    print(f"  Funds created: {len(created_funds)}")
    return created_funds


async def seed_vendors(db):
    """Seed vendor records for purchase orders."""
    print("\n--- Seeding Vendors ---")

    vendors_data = [
        {"name": "Ingram Content Group", "contact": "Sarah Johnson", "email": "orders@ingramcontent.example.com", "phone": "615-555-0100", "account": "ING-LIB-4521"},
        {"name": "Baker & Taylor", "contact": "Michael Chen", "email": "libsales@bakertaylor.example.com", "phone": "704-555-0200", "account": "BT-2024-889"},
        {"name": "Midwest Library Service", "contact": "Lisa Martinez", "email": "custserv@midwestls.example.com", "phone": "314-555-0300", "account": "MLS-7734"},
        {"name": "OverDrive Digital", "contact": "James Wilson", "email": "libraries@overdrive.example.com", "phone": "216-555-0400", "account": "OD-DIG-1122"},
        {"name": "Brodart Company", "contact": "Amy Thompson", "email": "orders@brodart.example.com", "phone": "570-555-0500", "account": "BRD-5567"},
    ]

    created_vendors = []
    for vdata in vendors_data:
        existing = await db.execute(
            select(Vendor).where(Vendor.name == vdata["name"])
        )
        if existing.scalar_one_or_none():
            print(f"  SKIP: {vdata['name']} (exists)")
            continue

        vendor = Vendor(
            name=vdata["name"],
            contact_name=vdata["contact"],
            email=vdata["email"],
            phone=vdata["phone"],
            account_number=vdata["account"],
            is_active=True,
        )
        db.add(vendor)
        created_vendors.append(vendor)
        print(f"  + {vdata['name']}")

    await db.flush()
    print(f"  Vendors created: {len(created_vendors)}")
    return created_vendors


async def seed_purchase_orders(db, funds, vendors, staff):
    """Seed purchase orders as fund transactions for budget tracking."""
    print("\n--- Seeding Fund Transactions (Purchase Orders) ---")

    if not funds or not vendors or not staff:
        print("  SKIP: Missing funds, vendors, or staff")
        return 0

    staff_user = staff[0]
    approver = staff[1] if len(staff) > 1 else staff[0]

    po_data = [
        {
            "po_number": f"PO-{NOW.strftime('%Y')}-0001",
            "fund_idx": 0, "vendor_idx": 0,
            "status": PurchaseOrderStatus.RECEIVED,
            "total": Decimal("2450.00"),
            "days_ago": 60,
            "items": [
                {"title": "New Fiction Titles - Q4 Batch", "author": "Various", "qty": 50, "price": Decimal("18.95")},
                {"title": "Non-Fiction Bestsellers Pack", "author": "Various", "qty": 25, "price": Decimal("22.50")},
                {"title": "Clearance Paperbacks", "author": "Various", "qty": 100, "price": Decimal("5.85")},
            ],
        },
        {
            "po_number": f"PO-{NOW.strftime('%Y')}-0002",
            "fund_idx": 1, "vendor_idx": 0,
            "status": PurchaseOrderStatus.RECEIVED,
            "total": Decimal("1875.00"),
            "days_ago": 45,
            "items": [
                {"title": "Picture Books Spring Collection", "author": "Various", "qty": 75, "price": Decimal("12.50")},
                {"title": "Young Adult Series Renewals", "author": "Various", "qty": 30, "price": Decimal("15.00")},
            ],
        },
        {
            "po_number": f"PO-{NOW.strftime('%Y')}-0003",
            "fund_idx": 2, "vendor_idx": 1,
            "status": PurchaseOrderStatus.PARTIALLY_RECEIVED,
            "total": Decimal("3200.00"),
            "days_ago": 30,
            "items": [
                {"title": "New Release DVDs - February", "author": "Various", "qty": 40, "price": Decimal("19.99")},
                {"title": "Blu-ray Classics Collection", "author": "Various", "qty": 20, "price": Decimal("24.99")},
                {"title": "Music CDs - Local Artists", "author": "Various", "qty": 30, "price": Decimal("12.99")},
                {"title": "Vinyl Records - Jazz Collection", "author": "Various", "qty": 15, "price": Decimal("28.95")},
            ],
        },
        {
            "po_number": f"PO-{NOW.strftime('%Y')}-0004",
            "fund_idx": 3, "vendor_idx": 3,
            "status": PurchaseOrderStatus.APPROVED,
            "total": Decimal("8000.00"),
            "days_ago": 10,
            "items": [
                {"title": "OverDrive E-book License Bundle (500 titles)", "author": "Various", "qty": 1, "price": Decimal("5000.00")},
                {"title": "Digital Audiobook Credits (200)", "author": "Various", "qty": 1, "price": Decimal("3000.00")},
            ],
        },
        {
            "po_number": f"PO-{NOW.strftime('%Y')}-0005",
            "fund_idx": 4, "vendor_idx": 2,
            "status": PurchaseOrderStatus.SUBMITTED,
            "total": Decimal("1950.00"),
            "days_ago": 5,
            "items": [
                {"title": "Academic Journal Subscriptions Renewal", "author": "Various", "qty": 5, "price": Decimal("250.00")},
                {"title": "Research Database Annual License", "author": "Various", "qty": 1, "price": Decimal("700.00")},
            ],
        },
        {
            "po_number": f"PO-{NOW.strftime('%Y')}-0006",
            "fund_idx": 0, "vendor_idx": 4,
            "status": PurchaseOrderStatus.DRAFT,
            "total": Decimal("1200.00"),
            "days_ago": 2,
            "items": [
                {"title": "Processing Supplies - Book Covers", "author": "N/A", "qty": 200, "price": Decimal("3.50")},
                {"title": "Spine Labels and Barcodes", "author": "N/A", "qty": 500, "price": Decimal("0.50")},
            ],
        },
        {
            "po_number": f"PO-{NOW.strftime('%Y')}-0007",
            "fund_idx": 5, "vendor_idx": 1,
            "status": PurchaseOrderStatus.RECEIVED,
            "total": Decimal("4500.00"),
            "days_ago": 75,
            "items": [
                {"title": "Chromebook Laptops (refurbished)", "author": "N/A", "qty": 5, "price": Decimal("350.00")},
                {"title": "Mobile Hotspot Devices", "author": "N/A", "qty": 10, "price": Decimal("125.00")},
                {"title": "USB-C Charging Cables", "author": "N/A", "qty": 50, "price": Decimal("8.00")},
            ],
        },
        {
            "po_number": f"PO-{NOW.strftime('%Y')}-0008",
            "fund_idx": 6, "vendor_idx": 2,
            "status": PurchaseOrderStatus.RECEIVED,
            "total": Decimal("980.00"),
            "days_ago": 50,
            "items": [
                {"title": "Local History Photographs (digitized)", "author": "County Archives", "qty": 1, "price": Decimal("500.00")},
                {"title": "Genealogy Reference Set", "author": "Heritage Press", "qty": 2, "price": Decimal("240.00")},
            ],
        },
    ]

    created = 0
    for po in po_data:
        existing = await db.execute(
            select(PurchaseOrder).where(PurchaseOrder.po_number == po["po_number"])
        )
        if existing.scalar_one_or_none():
            print(f"  SKIP: {po['po_number']} (exists)")
            continue

        fund = funds[po["fund_idx"]] if po["fund_idx"] < len(funds) else funds[0]
        vendor = vendors[po["vendor_idx"]] if po["vendor_idx"] < len(vendors) else vendors[0]

        order_date = days_ago(po["days_ago"]).date()
        is_approved = po["status"] not in (PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.PENDING_APPROVAL)

        purchase_order = PurchaseOrder(
            po_number=po["po_number"],
            vendor_id=vendor.id,
            fund_id=fund.id,
            order_date=order_date,
            expected_delivery=order_date + timedelta(days=14),
            actual_delivery=order_date + timedelta(days=12) if po["status"] == PurchaseOrderStatus.RECEIVED else None,
            status=po["status"],
            total_amount=po["total"],
            notes=f"Budget tracking PO for {fund.name}",
            approved_by_id=approver.id if is_approved else None,
            approved_at=days_ago(po["days_ago"] - 1) if is_approved else None,
            created_by_id=staff_user.id,
        )
        db.add(purchase_order)
        await db.flush()

        for item in po["items"]:
            received_qty = item["qty"] if po["status"] == PurchaseOrderStatus.RECEIVED else (item["qty"] // 2 if po["status"] == PurchaseOrderStatus.PARTIALLY_RECEIVED else 0)
            po_item = PurchaseOrderItem(
                purchase_order_id=purchase_order.id,
                title=item["title"],
                author=item.get("author"),
                quantity=item["qty"],
                unit_price=item["price"],
                received_quantity=received_qty,
            )
            db.add(po_item)

        created += 1
        print(f"  + {po['po_number']}: ${po['total']} ({po['status'].value}) -> {fund.code}")

    await db.flush()
    print(f"  Purchase orders created: {created}")
    return created


async def print_summary(db):
    """Print a summary of all seeded financial data."""
    print("\n" + "=" * 70)
    print("FINANCIAL SEED DATA SUMMARY")
    print("=" * 70)

    # Fine counts by status
    for status in FineStatus:
        result = await db.execute(
            select(func.count(Fine.id)).where(Fine.status == status)
        )
        count = result.scalar() or 0
        if count > 0:
            total_result = await db.execute(
                select(func.sum(Fine.amount)).where(Fine.status == status)
            )
            total = total_result.scalar() or Decimal("0")
            print(f"  Fines ({status.value}): {count} records, total ${total:.2f}")

    # Fine counts by type
    print()
    for ftype in FineType:
        result = await db.execute(
            select(func.count(Fine.id)).where(Fine.fine_type == ftype)
        )
        count = result.scalar() or 0
        if count > 0:
            print(f"  Fine type ({ftype.value}): {count} records")

    # Payment history
    result = await db.execute(select(func.count(FinePaymentHistory.id)))
    pay_count = result.scalar() or 0
    result = await db.execute(
        select(func.sum(FinePaymentHistory.amount)).where(FinePaymentHistory.amount > 0)
    )
    pay_total = result.scalar() or Decimal("0")
    result = await db.execute(
        select(func.count(FinePaymentHistory.id)).where(FinePaymentHistory.amount < 0)
    )
    refund_count = result.scalar() or 0
    print(f"\n  Payment history: {pay_count} records (${pay_total:.2f} collected)")
    print(f"  Refund records: {refund_count}")

    # Payment plans
    result = await db.execute(select(func.count(PaymentPlan.id)))
    plan_count = result.scalar() or 0
    print(f"  Payment plans: {plan_count}")

    # Fine policies
    result = await db.execute(select(func.count(FinePolicy.id)))
    policy_count = result.scalar() or 0
    print(f"  Fine policies: {policy_count}")

    # Funds
    result = await db.execute(select(func.count(Fund.id)))
    fund_count = result.scalar() or 0
    result = await db.execute(select(func.sum(Fund.allocated_amount)))
    fund_total = result.scalar() or Decimal("0")
    print(f"\n  Funds: {fund_count} (total allocated: ${fund_total:,.2f})")

    # Vendors
    result = await db.execute(select(func.count(Vendor.id)))
    vendor_count = result.scalar() or 0
    print(f"  Vendors: {vendor_count}")

    # Purchase orders
    result = await db.execute(select(func.count(PurchaseOrder.id)))
    po_count = result.scalar() or 0
    result = await db.execute(select(func.sum(PurchaseOrder.total_amount)))
    po_total = result.scalar() or Decimal("0")
    print(f"  Purchase orders: {po_count} (total: ${po_total:,.2f})")

    print("\n" + "=" * 70)


async def verify_financial_reports(db):
    """Verify that financial report queries can execute against seeded data."""
    print("\n--- Verifying Financial Reports ---")

    from app.services.financial_reports_service import FinancialReportsService

    service = FinancialReportsService(db)
    errors = []

    # Test each report
    reports = [
        ("Revenue Summary", lambda: service.get_revenue_summary(use_cache=False)),
        ("Fine Trends (90 days)", lambda: service.get_fine_trends(90, use_cache=False)),
        ("Payment Methods", lambda: service.get_payment_methods(use_cache=False)),
        ("Waived Fines", lambda: service.get_waived_fines(use_cache=False)),
        ("Outstanding Balances", lambda: service.get_outstanding_balances()),
        ("Budget vs Actual", lambda: service.get_budget_vs_actual(use_cache=False)),
        ("CSV Export (revenue_summary)", lambda: service.export_to_csv("revenue_summary")),
        ("CSV Export (payment_methods)", lambda: service.export_to_csv("payment_methods")),
        ("CSV Export (outstanding_balances)", lambda: service.export_to_csv("outstanding_balances")),
    ]

    for name, report_fn in reports:
        try:
            result = await report_fn()
            if result is None:
                errors.append(f"{name}: returned None")
                print(f"  WARNING: {name} returned None")
            else:
                # Show key metrics where available
                detail = ""
                if isinstance(result, dict):
                    if "total_revenue" in result:
                        detail = f" (revenue: ${result['total_revenue']:.2f})"
                    elif "total_collected" in result:
                        detail = f" (collected: ${result['total_collected']:.2f})"
                    elif "summary" in result:
                        summary = result["summary"]
                        if "total_waived_count" in summary:
                            detail = f" ({summary['total_waived_count']} waived, ${summary['total_waived_amount']:.2f})"
                    elif "aging_report" in result:
                        aging = result["aging_report"]
                        total_outstanding = sum(
                            cat["summary"]["total"]
                            for cat in aging.values()
                        )
                        detail = f" (outstanding: ${total_outstanding:.2f})"
                elif isinstance(result, str):
                    lines = result.strip().split("\n")
                    detail = f" ({len(lines)} lines)"
                print(f"  OK: {name}{detail}")
        except Exception as e:
            errors.append(f"{name}: {str(e)}")
            print(f"  FAIL: {name} - {str(e)}")

    if errors:
        print(f"\n  {len(errors)} report(s) had issues:")
        for err in errors:
            print(f"    - {err}")
    else:
        print(f"\n  All {len(reports)} financial reports verified successfully!")

    return len(errors) == 0


async def main():
    """Main entry point for seeding financial data."""
    print("=" * 70)
    print("LSC LIBRARY - FINANCIAL SEED DATA")
    print("=" * 70)

    async with AsyncSessionLocal() as db:
        try:
            # Get existing users
            patrons, staff = await get_or_create_users(db)
            if not patrons or not staff:
                print("\nERROR: Cannot seed financial data without users.")
                print("Run: python backend/scripts/seed_test_accounts.py first")
                return 1

            print(f"\nUsing {len(patrons)} patron(s) and {len(staff)} staff user(s)")

            # Get existing checkouts
            checkouts = await get_checkouts(db)
            print(f"Found {len(checkouts)} existing checkout(s)")

            # Seed in order
            await seed_fine_policies(db, staff)
            fines = await seed_fines(db, patrons, staff, checkouts)
            await seed_payment_history(db, fines, patrons, staff)
            await seed_fee_exemptions(db, patrons, staff)
            await seed_payment_plans(db, patrons, staff)
            funds = await seed_funds(db)
            vendors = await seed_vendors(db)
            await seed_purchase_orders(db, funds, vendors, staff)

            # Commit everything
            await db.commit()
            print("\n  All data committed successfully.")

            # Print summary
            await print_summary(db)

            # Verify reports (non-fatal - may fail due to lazy loading in async context)
            try:
                success = await verify_financial_reports(db)
                if success:
                    print("\nFINANCIAL SEED DATA COMPLETE - ALL REPORTS VERIFIED")
                else:
                    print("\nFINANCIAL SEED DATA COMPLETE - SOME REPORTS HAD ISSUES")
            except Exception as verify_err:
                print(f"\n⚠️  Report verification skipped: {verify_err}")
                print("FINANCIAL SEED DATA COMPLETE - DATA SEEDED SUCCESSFULLY")

            return 0

        except Exception as e:
            await db.rollback()
            print(f"\nERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
