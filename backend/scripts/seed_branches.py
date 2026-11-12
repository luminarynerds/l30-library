#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive Branch and Location Seeding Script for LSC

This script creates a complete multi-branch library system with:
- Library System (top-level organization)
- Regions (optional grouping)
- Main Branch
- Additional Branches (Downtown, Elmdale)
- Bookmobile
- Outreach Location

For each location, includes:
- Complete address and contact information
- Operating hours (regular hours with variations)
- Holiday closures and seasonal variations
- Branch-specific settings
- Branch statistics templates
"""

import asyncio
import sys
from pathlib import Path
from datetime import date, time, datetime, timezone, timedelta

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal
from app.models.multi_branch import (
    LibrarySystem,
    SystemSettings,
    Region,
    Branch,
    BranchType,
    BranchStatus,
    BranchHours,
    BranchClosure,
    DayOfWeek,
    BranchSettings,
    FloatingCollectionType,
    BranchStatistics,
)


async def create_library_system(db):
    """Create the main library system"""
    print("\n" + "=" * 70)
    print("CREATING LIBRARY SYSTEM")
    print("=" * 70 + "\n")

    # Check if system already exists
    result = await db.execute(
        select(LibrarySystem).where(LibrarySystem.code == "LSC")
    )
    existing = result.scalar_one_or_none()

    if existing:
        print(f"✓ Library System already exists: {existing.name}")
        return existing

    # Create new system
    system = LibrarySystem(
        code="LSC",
        name="Bébé Memorial Library System",
        legal_name="Bébé Memorial Library System",
        website="https://library.lsc.example.com",
        email="info@lsc.example.com",
        phone="(555) 123-4567",
        fax="(555) 123-4568",
        address_line1="100 Library Lane",
        address_line2="Suite 200",
        city="Somewhere Up North",
        state="ON",
        zip_code="K1A 0B1",
        country="Canada",
        tax_id="12-3456789",
        state_library_id="ON-LSC-001",
        governance_type="regional",
        fiscal_year_start_month=7,
        timezone="America/Toronto",
    )

    db.add(system)
    await db.flush()

    # Create system settings
    settings = SystemSettings(
        library_system_id=system.id,
        default_loan_period_days=21,
        default_renewal_limit=2,
        default_hold_limit=10,
        default_checkout_limit=50,
        default_overdue_fine_per_day=0.25,
        default_max_fine=10.00,
        grace_period_days=0,
        lost_item_threshold_days=30,
        default_replacement_cost=25.00,
        hold_pickup_days=7,
        allow_hold_on_available=True,
        transit_time_estimate_days=2,
        auto_approve_transit=True,
        enable_floating_collections=True,
        enable_reciprocal_borrowing=False,
        enable_self_checkout=True,
    )
    db.add(settings)

    print(f"✓ CREATED: {system.name}")
    print(f"  Code: {system.code}")
    print(f"  Address: {system.address_line1}, {system.city}, {system.state} {system.zip_code}")
    print(f"  Phone: {system.phone}\n")

    return system


async def create_regions(db, system_id):
    """Create regions for branch organization"""
    print("=" * 70)
    print("CREATING REGIONS")
    print("=" * 70 + "\n")

    regions_data = [
        {
            "code": "DOWNTOWN",
            "name": "Downtown District",
            "description": "Urban core locations serving the downtown area",
        },
        {
            "code": "SUBURBS",
            "name": "Suburban Services",
            "description": "Suburban branch locations",
        },
    ]

    regions = {}
    for region_data in regions_data:
        # Check if exists
        result = await db.execute(
            select(Region).where(
                (Region.library_system_id == system_id)
                & (Region.code == region_data["code"])
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"✓ Region already exists: {existing.name}")
            regions[region_data["code"]] = existing
            continue

        region = Region(
            library_system_id=system_id,
            code=region_data["code"],
            name=region_data["name"],
            description=region_data["description"],
            is_active=True,
        )
        db.add(region)
        await db.flush()
        regions[region_data["code"]] = region

        print(f"✓ CREATED: {region.name} ({region.code})\n")

    return regions


async def create_branches(db, system_id, regions):
    """Create all branch locations"""
    print("=" * 70)
    print("CREATING BRANCHES")
    print("=" * 70 + "\n")

    branches_data = [
        {
            "code": "MAIN",
            "name": "Main Library",
            "short_name": "Main",
            "type": BranchType.MAIN,
            "region_code": "DOWNTOWN",
            "address_line1": "100 Library Lane",
            "address_line2": "Suite 100",
            "city": "Somewhere Up North",
            "state": "ON",
            "zip_code": "K1A 0B1",
            "phone": "(555) 123-4567",
            "fax": "(555) 123-4568",
            "email": "main@lsc.example.com",
            "website": "https://main.lsc.example.com",
            "latitude": 45.4215,
            "longitude": -75.6972,
            "square_footage": 45000,
            "parking_spaces": 150,
            "is_ada_accessible": True,
            "has_meeting_rooms": True,
            "has_computer_lab": True,
            "has_makerspace": True,
            "has_drive_through": False,
            "has_book_drop": True,
            "has_self_checkout": True,
            "opened_date": date(1995, 9, 15),
        },
        {
            "code": "DOWNTOWN",
            "name": "Downtown Branch",
            "short_name": "Downtown",
            "type": BranchType.BRANCH,
            "region_code": "DOWNTOWN",
            "address_line1": "250 Main Street",
            "address_line2": "",
            "city": "Somewhere Up North",
            "state": "ON",
            "zip_code": "K1A 0B2",
            "phone": "(555) 234-5678",
            "fax": "(555) 234-5679",
            "email": "downtown@lsc.example.com",
            "website": "https://downtown.lsc.example.com",
            "latitude": 45.4225,
            "longitude": -75.6962,
            "square_footage": 28000,
            "parking_spaces": 75,
            "is_ada_accessible": True,
            "has_meeting_rooms": True,
            "has_computer_lab": True,
            "has_makerspace": False,
            "has_drive_through": True,
            "has_book_drop": True,
            "has_self_checkout": True,
            "opened_date": date(2005, 3, 20),
        },
        {
            "code": "ELMDALE",
            "name": "Elmdale Branch",
            "short_name": "Elmdale",
            "type": BranchType.BRANCH,
            "region_code": "SUBURBS",
            "address_line1": "500 Elm Street",
            "address_line2": "",
            "city": "Elmdale",
            "state": "ON",
            "zip_code": "K1A 1A1",
            "phone": "(555) 345-6789",
            "fax": "(555) 345-6790",
            "email": "elmdale@lsc.example.com",
            "website": "https://elmdale.lsc.example.com",
            "latitude": 45.3815,
            "longitude": -75.7572,
            "square_footage": 18000,
            "parking_spaces": 50,
            "is_ada_accessible": True,
            "has_meeting_rooms": False,
            "has_computer_lab": True,
            "has_makerspace": False,
            "has_drive_through": False,
            "has_book_drop": True,
            "has_self_checkout": True,
            "opened_date": date(2010, 6, 10),
        },
        {
            "code": "BOOKMOBILE",
            "name": "LSC Bookmobile",
            "short_name": "Bookmobile",
            "type": BranchType.BOOKMOBILE,
            "region_code": None,
            "address_line1": "Mobile Unit #1",
            "address_line2": "",
            "city": "Somewhere Up North",
            "state": "ON",
            "zip_code": "K1A 0B1",
            "phone": "(555) 456-7890",
            "fax": "",
            "email": "bookmobile@lsc.example.com",
            "website": "https://bookmobile.lsc.example.com",
            "latitude": 45.4215,
            "longitude": -75.6972,
            "square_footage": 350,
            "parking_spaces": 0,
            "is_ada_accessible": True,
            "has_meeting_rooms": False,
            "has_computer_lab": False,
            "has_makerspace": False,
            "has_drive_through": False,
            "has_book_drop": False,
            "has_self_checkout": False,
            "opened_date": date(2015, 1, 5),
        },
        {
            "code": "OUTREACH",
            "name": "Outreach Services",
            "short_name": "Outreach",
            "type": BranchType.OUTREACH,
            "region_code": None,
            "address_line1": "Community Center, 75 Park Avenue",
            "address_line2": "HomeDelivery Services Office",
            "city": "Somewhere Up North",
            "state": "ON",
            "zip_code": "K1A 0B3",
            "phone": "(555) 567-8901",
            "fax": "(555) 567-8902",
            "email": "outreach@lsc.example.com",
            "website": "https://outreach.lsc.example.com",
            "latitude": 45.4305,
            "longitude": -75.6852,
            "square_footage": 2000,
            "parking_spaces": 10,
            "is_ada_accessible": True,
            "has_meeting_rooms": False,
            "has_computer_lab": False,
            "has_makerspace": False,
            "has_drive_through": False,
            "has_book_drop": False,
            "has_self_checkout": False,
            "opened_date": date(2018, 9, 1),
        },
    ]

    branches = {}
    for branch_data in branches_data:
        # Check if exists
        result = await db.execute(
            select(Branch).where(
                (Branch.library_system_id == system_id)
                & (Branch.code == branch_data["code"])
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"✓ Branch already exists: {existing.name}")
            branches[branch_data["code"]] = existing
            continue

        region_id = None
        if branch_data["region_code"]:
            region_id = regions[branch_data["region_code"]].id

        branch = Branch(
            library_system_id=system_id,
            region_id=region_id,
            code=branch_data["code"],
            name=branch_data["name"],
            short_name=branch_data["short_name"],
            branch_type=branch_data["type"],
            status=BranchStatus.ACTIVE,
            phone=branch_data["phone"],
            fax=branch_data.get("fax"),
            email=branch_data["email"],
            website=branch_data.get("website"),
            address_line1=branch_data["address_line1"],
            address_line2=branch_data.get("address_line2"),
            city=branch_data["city"],
            state=branch_data["state"],
            zip_code=branch_data["zip_code"],
            country="Canada",
            latitude=branch_data["latitude"],
            longitude=branch_data["longitude"],
            square_footage=branch_data["square_footage"],
            parking_spaces=branch_data["parking_spaces"],
            is_ada_accessible=branch_data["is_ada_accessible"],
            has_meeting_rooms=branch_data["has_meeting_rooms"],
            has_computer_lab=branch_data["has_computer_lab"],
            has_makerspace=branch_data["has_makerspace"],
            has_drive_through=branch_data["has_drive_through"],
            has_book_drop=branch_data["has_book_drop"],
            has_self_checkout=branch_data["has_self_checkout"],
            opened_date=branch_data.get("opened_date"),
        )

        db.add(branch)
        await db.flush()
        branches[branch_data["code"]] = branch

        print(f"✓ CREATED: {branch.name} ({branch.code})")
        print(f"  Type: {branch.branch_type.value}")
        print(f"  Address: {branch.full_address}")
        print(f"  Phone: {branch.phone}\n")

    return branches


async def create_branch_hours(db, branches):
    """Create operating hours for all branches"""
    print("=" * 70)
    print("CREATING BRANCH OPERATING HOURS")
    print("=" * 70 + "\n")

    # Standard hours: Monday-Friday 9-6, Saturday 10-5, Sunday closed
    hours_config = {
        "MAIN": {
            "monday": {"open": "09:00", "close": "21:00"},
            "tuesday": {"open": "09:00", "close": "21:00"},
            "wednesday": {"open": "09:00", "close": "21:00"},
            "thursday": {"open": "09:00", "close": "21:00"},
            "friday": {"open": "09:00", "close": "21:00"},
            "saturday": {"open": "10:00", "close": "17:00"},
            "sunday": {"open": "12:00", "close": "17:00"},
        },
        "DOWNTOWN": {
            "monday": {"open": "10:00", "close": "18:00"},
            "tuesday": {"open": "10:00", "close": "18:00"},
            "wednesday": {"open": "10:00", "close": "18:00"},
            "thursday": {"open": "10:00", "close": "20:00"},
            "friday": {"open": "10:00", "close": "18:00"},
            "saturday": {"open": "11:00", "close": "16:00"},
            "sunday": {"closed": True},
        },
        "ELMDALE": {
            "monday": {"open": "14:00", "close": "20:00"},
            "tuesday": {"open": "14:00", "close": "20:00"},
            "wednesday": {"open": "14:00", "close": "20:00"},
            "thursday": {"open": "10:00", "close": "20:00"},
            "friday": {"open": "10:00", "close": "20:00"},
            "saturday": {"open": "10:00", "close": "16:00"},
            "sunday": {"closed": True},
        },
        "BOOKMOBILE": {
            "monday": {"open": "10:00", "close": "12:00", "open_2": "14:00", "close_2": "17:00"},
            "tuesday": {"open": "14:00", "close": "18:00"},
            "wednesday": {"open": "10:00", "close": "14:00"},
            "thursday": {"open": "14:00", "close": "18:00"},
            "friday": {"open": "10:00", "close": "14:00"},
            "saturday": {"open": "10:00", "close": "14:00"},
            "sunday": {"closed": True},
        },
        "OUTREACH": {
            "monday": {"open": "09:00", "close": "17:00"},
            "tuesday": {"open": "09:00", "close": "17:00"},
            "wednesday": {"open": "09:00", "close": "17:00"},
            "thursday": {"open": "09:00", "close": "17:00"},
            "friday": {"open": "09:00", "close": "17:00"},
            "saturday": {"closed": True},
            "sunday": {"closed": True},
        },
    }

    day_enum_map = {
        "monday": DayOfWeek.MONDAY,
        "tuesday": DayOfWeek.TUESDAY,
        "wednesday": DayOfWeek.WEDNESDAY,
        "thursday": DayOfWeek.THURSDAY,
        "friday": DayOfWeek.FRIDAY,
        "saturday": DayOfWeek.SATURDAY,
        "sunday": DayOfWeek.SUNDAY,
    }

    for branch_code, hours_data in hours_config.items():
        branch = branches[branch_code]
        print(f"Creating hours for {branch.name}:")

        for day_name, day_hours in hours_data.items():
            day_enum = day_enum_map[day_name]

            # Check if already exists
            result = await db.execute(
                select(BranchHours).where(
                    (BranchHours.branch_id == branch.id)
                    & (BranchHours.day_of_week == day_enum)
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  ✓ {day_name.capitalize()} already exists")
                continue

            if day_hours.get("closed"):
                hours = BranchHours(
                    branch_id=branch.id,
                    day_of_week=day_enum,
                    is_closed=True,
                )
            else:
                hours = BranchHours(
                    branch_id=branch.id,
                    day_of_week=day_enum,
                    is_closed=False,
                    open_time=datetime.strptime(day_hours["open"], "%H:%M").time(),
                    close_time=datetime.strptime(day_hours["close"], "%H:%M").time(),
                )

                if "open_2" in day_hours:
                    hours.open_time_2 = datetime.strptime(day_hours["open_2"], "%H:%M").time()
                    hours.close_time_2 = datetime.strptime(day_hours["close_2"], "%H:%M").time()

            db.add(hours)
            print(f"  ✓ {day_name.capitalize()}: {day_hours.get('open', 'Closed')}")

        print()


async def create_branch_closures(db, branches):
    """Create holiday closures for branches"""
    print("=" * 70)
    print("CREATING BRANCH HOLIDAY CLOSURES")
    print("=" * 70 + "\n")

    current_year = date.today().year

    # Standard holiday closures (Canadian)
    closures = [
        {
            "reason": "New Year's Day",
            "start": date(current_year, 1, 1),
            "end": date(current_year, 1, 1),
            "is_annual": True,
            "branches": ["MAIN", "DOWNTOWN", "ELMDALE"],
        },
        {
            "reason": "Family Day",
            "start": date(current_year, 2, 17),
            "end": date(current_year, 2, 17),
            "is_annual": True,
            "branches": ["MAIN", "DOWNTOWN", "ELMDALE"],
        },
        {
            "reason": "Good Friday",
            "start": date(current_year, 4, 18),
            "end": date(current_year, 4, 18),
            "is_annual": False,
            "branches": ["MAIN", "DOWNTOWN", "ELMDALE"],
        },
        {
            "reason": "Victoria Day",
            "start": date(current_year, 5, 19),
            "end": date(current_year, 5, 19),
            "is_annual": True,
            "branches": ["MAIN", "DOWNTOWN", "ELMDALE"],
        },
        {
            "reason": "Canada Day",
            "start": date(current_year, 7, 1),
            "end": date(current_year, 7, 1),
            "is_annual": True,
            "branches": ["MAIN", "DOWNTOWN", "ELMDALE"],
        },
        {
            "reason": "Civic Holiday",
            "start": date(current_year, 8, 4),
            "end": date(current_year, 8, 4),
            "is_annual": True,
            "branches": ["MAIN", "DOWNTOWN", "ELMDALE"],
        },
        {
            "reason": "Labour Day",
            "start": date(current_year, 9, 2),
            "end": date(current_year, 9, 2),
            "is_annual": True,
            "branches": ["MAIN", "DOWNTOWN", "ELMDALE"],
        },
        {
            "reason": "Thanksgiving",
            "start": date(current_year, 10, 14),
            "end": date(current_year, 10, 14),
            "is_annual": True,
            "branches": ["MAIN", "DOWNTOWN", "ELMDALE"],
        },
        {
            "reason": "Christmas Day",
            "start": date(current_year, 12, 25),
            "end": date(current_year, 12, 25),
            "is_annual": True,
            "branches": ["MAIN", "DOWNTOWN", "ELMDALE"],
        },
        {
            "reason": "Boxing Day",
            "start": date(current_year, 12, 26),
            "end": date(current_year, 12, 26),
            "is_annual": True,
            "branches": ["MAIN", "DOWNTOWN", "ELMDALE"],
        },
        {
            "reason": "Building Renovation - Main Branch",
            "start": date(current_year + 1, 7, 1),
            "end": date(current_year + 1, 8, 31),
            "is_annual": False,
            "is_system_wide": False,
            "branches": ["MAIN"],
            "description": "Major HVAC and electrical system upgrades",
        },
    ]

    for closure_data in closures:
        for branch_code in closure_data["branches"]:
            branch = branches[branch_code]

            # Check if already exists
            result = await db.execute(
                select(BranchClosure).where(
                    (BranchClosure.branch_id == branch.id)
                    & (BranchClosure.start_date == closure_data["start"])
                    & (BranchClosure.end_date == closure_data["end"])
                    & (BranchClosure.reason == closure_data["reason"])
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                continue

            closure = BranchClosure(
                branch_id=branch.id,
                start_date=closure_data["start"],
                end_date=closure_data["end"],
                reason=closure_data["reason"],
                description=closure_data.get("description"),
                is_system_wide=closure_data.get("is_system_wide", False),
                is_annual=closure_data["is_annual"],
            )
            db.add(closure)

            print(f"✓ {branch.name}: {closure_data['reason']} ({closure_data['start']})")

    print()


async def create_branch_settings(db, branches):
    """Create branch-specific settings"""
    print("=" * 70)
    print("CREATING BRANCH SETTINGS")
    print("=" * 70 + "\n")

    settings_config = {
        "MAIN": {
            "allow_ill_pickup": True,
            "allow_hold_pickup": True,
            "allow_returns": True,
            "floating_type": FloatingCollectionType.SYSTEM_FLOAT,
            "default_pickup_branch": True,
            "hold_shelf_capacity": 1000,
        },
        "DOWNTOWN": {
            "allow_ill_pickup": True,
            "allow_hold_pickup": True,
            "allow_returns": True,
            "floating_type": FloatingCollectionType.NO_FLOAT,
            "default_pickup_branch": False,
            "hold_shelf_capacity": 500,
        },
        "ELMDALE": {
            "allow_ill_pickup": False,
            "allow_hold_pickup": True,
            "allow_returns": True,
            "floating_type": FloatingCollectionType.NO_FLOAT,
            "default_pickup_branch": False,
            "hold_shelf_capacity": 300,
        },
        "BOOKMOBILE": {
            "allow_ill_pickup": False,
            "allow_hold_pickup": False,
            "allow_returns": False,
            "floating_type": FloatingCollectionType.NO_FLOAT,
            "default_pickup_branch": False,
            "hold_shelf_capacity": 50,
        },
        "OUTREACH": {
            "allow_ill_pickup": True,
            "allow_hold_pickup": True,
            "allow_returns": False,
            "floating_type": FloatingCollectionType.NO_FLOAT,
            "default_pickup_branch": False,
            "hold_shelf_capacity": 100,
        },
    }

    for branch_code, settings_data in settings_config.items():
        branch = branches[branch_code]

        # Check if settings already exist
        result = await db.execute(
            select(BranchSettings).where(BranchSettings.branch_id == branch.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"✓ Settings already exist for {branch.name}")
            continue

        settings = BranchSettings(
            branch_id=branch.id,
            allow_ill_pickup=settings_data["allow_ill_pickup"],
            allow_hold_pickup=settings_data["allow_hold_pickup"],
            allow_returns=settings_data["allow_returns"],
            floating_type=settings_data["floating_type"],
            default_pickup_branch=settings_data["default_pickup_branch"],
            hold_shelf_capacity=settings_data["hold_shelf_capacity"],
            checkout_message=f"Welcome to {branch.name}! Thank you for using our library.",
            hold_pickup_message=f"Your hold is ready for pickup at {branch.name}. Please bring your library card.",
        )
        db.add(settings)

        print(f"✓ CREATED: Settings for {branch.name}")
        print(f"  Hold Pickup: {settings_data['allow_hold_pickup']}")
        print(f"  ILL Pickup: {settings_data['allow_ill_pickup']}")
        print(f"  Floating Type: {settings_data['floating_type'].value}\n")


async def create_branch_statistics(db, branches):
    """Create initial branch statistics records"""
    print("=" * 70)
    print("CREATING BRANCH STATISTICS")
    print("=" * 70 + "\n")

    # Create stats for the current month
    today = date.today()
    period_start = date(today.year, today.month, 1)

    # Last day of current month
    if today.month == 12:
        period_end = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        period_end = date(today.year, today.month + 1, 1) - timedelta(days=1)

    for branch_code, branch in branches.items():
        # Check if statistics already exist
        result = await db.execute(
            select(BranchStatistics).where(
                (BranchStatistics.branch_id == branch.id)
                & (BranchStatistics.period_start == period_start)
                & (BranchStatistics.period_end == period_end)
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"✓ Statistics already exist for {branch.name}")
            continue

        # Base stats vary by branch type
        if branch.branch_type == BranchType.MAIN:
            stats = BranchStatistics(
                branch_id=branch.id,
                period_start=period_start,
                period_end=period_end,
                total_checkouts=1250,
                total_renewals=450,
                total_checkins=1280,
                total_holds_placed=180,
                total_holds_filled=165,
                items_owned=35000,
                items_added=250,
                items_withdrawn=50,
                items_sent_to_other_branches=120,
                items_received_from_other_branches=95,
                active_patrons=8500,
                new_registrations=85,
                fines_assessed=450.75,
                fines_collected=380.25,
                fines_waived=20.00,
                door_count=12500,
            )
        elif branch.branch_type == BranchType.BRANCH:
            stats = BranchStatistics(
                branch_id=branch.id,
                period_start=period_start,
                period_end=period_end,
                total_checkouts=650,
                total_renewals=200,
                total_checkins=680,
                total_holds_placed=90,
                total_holds_filled=82,
                items_owned=15000,
                items_added=100,
                items_withdrawn=25,
                items_sent_to_other_branches=75,
                items_received_from_other_branches=60,
                active_patrons=3500,
                new_registrations=35,
                fines_assessed=225.50,
                fines_collected=190.00,
                fines_waived=10.00,
                door_count=5500,
            )
        elif branch.branch_type == BranchType.BOOKMOBILE:
            stats = BranchStatistics(
                branch_id=branch.id,
                period_start=period_start,
                period_end=period_end,
                total_checkouts=180,
                total_renewals=30,
                total_checkins=185,
                total_holds_placed=15,
                total_holds_filled=12,
                items_owned=3500,
                items_added=25,
                items_withdrawn=5,
                items_sent_to_other_branches=20,
                items_received_from_other_branches=15,
                active_patrons=450,
                new_registrations=8,
                fines_assessed=35.25,
                fines_collected=25.00,
                fines_waived=2.00,
                door_count=800,
            )
        elif branch.branch_type == BranchType.OUTREACH:
            stats = BranchStatistics(
                branch_id=branch.id,
                period_start=period_start,
                period_end=period_end,
                total_checkouts=95,
                total_renewals=15,
                total_checkins=100,
                total_holds_placed=8,
                total_holds_filled=7,
                items_owned=1200,
                items_added=20,
                items_withdrawn=3,
                items_sent_to_other_branches=30,
                items_received_from_other_branches=25,
                active_patrons=200,
                new_registrations=5,
                fines_assessed=15.00,
                fines_collected=10.00,
                fines_waived=1.00,
                door_count=250,
            )

        db.add(stats)

        print(f"✓ CREATED: Statistics for {branch.name}")
        print(f"  Checkouts: {stats.total_checkouts}")
        print(f"  Items: {stats.items_owned}")
        print(f"  Active Patrons: {stats.active_patrons}\n")


async def seed_branches():
    """Main seeding function"""
    async with AsyncSessionLocal() as db:
        try:
            print("\n" + "=" * 70)
            print("LSC BRANCH AND LOCATION SEEDING")
            print("=" * 70)

            # Create library system
            system = await create_library_system(db)

            # Create regions
            regions = await create_regions(db, system.id)

            # Create branches
            branches = await create_branches(db, system.id, regions)

            # Create branch hours
            await create_branch_hours(db, branches)

            # Create holiday closures
            await create_branch_closures(db, branches)

            # Create branch settings
            await create_branch_settings(db, branches)

            # Create branch statistics
            await create_branch_statistics(db, branches)

            # Commit all changes
            await db.commit()

            print("=" * 70)
            print("✓ BRANCH SEEDING COMPLETED SUCCESSFULLY")
            print("=" * 70)
            print("\nCreated:")
            print("  • 1 Library System (LSC)")
            print("  • 2 Regions (Downtown, Suburbs)")
            print("  • 5 Branch Locations:")
            print("    - 1 Main Library")
            print("    - 2 Additional Branches (Downtown, Elmdale)")
            print("    - 1 Bookmobile")
            print("    - 1 Outreach Location")
            print("  • Operating hours for all locations")
            print("  • Holiday closures (annual and special)")
            print("  • Branch-specific settings")
            print("  • Monthly branch statistics\n")

            return 0

        except Exception as e:
            await db.rollback()
            print(f"\n✗ ERROR: {str(e)}\n")
            import traceback
            traceback.print_exc()
            return 1


async def main():
    """Entry point"""
    try:
        exit_code = await seed_branches()
        return exit_code
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
