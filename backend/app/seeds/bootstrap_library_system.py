# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from app.core.logging import get_logger
import sys
from datetime import datetime, time
from argparse import ArgumentParser
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branding import branding
from app.core.database import AsyncSessionLocal
from app.models.multi_branch import (
    LibrarySystem,
    SystemSettings,
    Region,
    Branch,
    BranchType,
    BranchStatus,
    BranchHours,
    BranchSettings,
    DayOfWeek,
    FloatingCollectionType,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = get_logger(__name__)


class LibrarySystemBootstrap:

    def __init__(self, session: AsyncSession, dry_run: bool = False, verbose: bool = False):
        self.session = session
        self.dry_run = dry_run
        self.verbose = verbose
        self.created_count = {
            "systems": 0,
            "regions": 0,
            "branches": 0,
            "hours": 0,
        }

    async def system_exists(self) -> bool:
        result = await self.session.execute(select(LibrarySystem).limit(1))
        return result.scalar_one_or_none() is not None

    async def create_library_system(self) -> Optional[LibrarySystem]:
        if await self.system_exists():
            logger.info(f"Library system {branding.library_name!r} already exists")
            result = await self.session.execute(
                select(LibrarySystem).where(LibrarySystem.code == branding.CARD_PREFIX)
            )
            return result.scalar_one()

        logger.info(f"Creating library system {branding.library_name!r}")

        system = LibrarySystem(
            code=branding.CARD_PREFIX,
            name=branding.library_name,
            legal_name=branding.legal_name or branding.library_name,
            website=branding.PRODUCT_URL,
            email=branding.contact_email,
            phone=branding.phone,
            fax=branding.fax or None,
            address_line1=branding.address_line1,
            city=branding.city,
            state=branding.state,
            zip_code=branding.zip_code,
            country=branding.country,
            tax_id=branding.tax_id or None,
            state_library_id=branding.state_library_id or None,
            governance_type=branding.governance_type,
            fiscal_year_start_month=branding.fiscal_year_start_month,
            timezone=branding.timezone,
            is_active=True,
        )

        self.session.add(system)
        await self.session.flush()  # Flush to get auto-generated ID
        self.created_count["systems"] += 1

        if self.verbose:
            logger.debug(f"System object created: {system.code} - {system.name}")

        # Create system-wide settings
        await self._create_system_settings(system)

        return system

    async def _create_system_settings(self, system: LibrarySystem) -> None:
        logger.info("Creating system-wide settings")

        settings = SystemSettings(
            library_system_id=system.id,
            # Circulation defaults
            default_loan_period_days=21,
            default_renewal_limit=2,
            default_hold_limit=15,
            default_checkout_limit=50,
            # Fine policies
            default_overdue_fine_per_day=0.25,
            default_max_fine=15.00,
            grace_period_days=0,
            fine_free_juvenile=False,
            # Lost item policies
            lost_item_threshold_days=30,
            default_replacement_cost=20.00,
            processing_fee=3.00,
            # Hold policies
            hold_pickup_days=7,
            allow_hold_on_available=True,
            # Transit policies
            transit_time_estimate_days=3,
            auto_approve_transit=True,
            # Patron policies
            require_address_verification=True,
            allow_self_registration=True,
            card_expiry_years=3,
            age_transition_threshold=18,
            auto_transition_enabled=True,
            forgive_reading_minutes_on_transition=True,
            # Notifications
            overdue_notice_days=[1, 7, 14],
            courtesy_notice_days=3,
            # Features
            enable_floating_collections=False,
            enable_reciprocal_borrowing=False,
            enable_self_checkout=True,
            setup_complete=False,
        )

        self.session.add(settings)
        if self.verbose:
            logger.debug("System settings created")

    async def create_regions(self, system: LibrarySystem) -> dict:
        regions_data = [
            {
                "code": "MAIN",
                "name": "Main City",
                "description": "Central library location and downtown area branches",
            },
            {
                "code": "NORTH",
                "name": "Northern Suburbs",
                "description": "Suburban branches serving the northern communities",
            },
            {
                "code": "SOUTH",
                "name": "Southern Region",
                "description": "Branches serving the southern and rural areas",
            },
        ]

        regions = {}

        for region_data in regions_data:
            # Check if region already exists
            result = await self.session.execute(
                select(Region).where(
                    (Region.library_system_id == system.id) &
                    (Region.code == region_data["code"])
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"Region '{region_data['name']}' already exists")
                regions[region_data["code"]] = existing
                continue

            logger.info(f"Creating region: {region_data['name']}")

            region = Region(
                library_system_id=system.id,
                code=region_data["code"],
                name=region_data["name"],
                description=region_data["description"],
                is_active=True,
            )

            self.session.add(region)
            await self.session.flush()  # Flush to get auto-generated ID
            regions[region_data["code"]] = region
            self.created_count["regions"] += 1

            if self.verbose:
                logger.debug(f"Region created: {region.code} - {region.name}")

        return regions

    async def create_branches(self, system: LibrarySystem, regions: dict) -> dict:
        # Derive branch email domain from contact_email
        _email_domain = branding.contact_email.split("@")[-1]

        branches_data = [
            {
                "code": "MAIN",
                "region_code": "MAIN",
                "name": "Main Branch",
                "short_name": "Main",
                "branch_type": BranchType.MAIN,
                "address_line1": branding.address_line1,
                "city": branding.city,
                "state": branding.state,
                "zip_code": branding.zip_code,
                "phone": branding.phone,
                "email": f"main@{_email_domain}",
                "website": branding.PRODUCT_URL,
                "latitude": 43.5890,
                "longitude": -79.6441,
                "square_footage": 12000,
                "parking_spaces": 45,
                "is_ada_accessible": True,
                "has_meeting_rooms": True,
                "has_computer_lab": True,
                "has_makerspace": True,
                "has_drive_through": False,
                "has_book_drop": True,
                "has_self_checkout": True,
                "ils_location_code": "MAIN",
                "display_order": 1,
                "hours": {
                    "monday": (time(9, 0), time(18, 0)),
                    "tuesday": (time(9, 0), time(18, 0)),
                    "wednesday": (time(9, 0), time(20, 0)),
                    "thursday": (time(9, 0), time(18, 0)),
                    "friday": (time(9, 0), time(18, 0)),
                    "saturday": (time(10, 0), time(16, 0)),
                    "sunday": (time(12, 0), time(16, 0)),
                },
            },
            {
                "code": "NORTH1",
                "region_code": "NORTH",
                "name": "Elmdale Branch",
                "short_name": "Elmdale",
                "branch_type": BranchType.BRANCH,
                "address_line1": "156 Oak Avenue",
                "city": branding.city,
                "state": branding.state,
                "zip_code": branding.zip_code,
                "phone": branding.phone,
                "email": f"north@{_email_domain}",
                "latitude": 43.6890,
                "longitude": -79.5441,
                "square_footage": 8500,
                "parking_spaces": 30,
                "is_ada_accessible": True,
                "has_meeting_rooms": False,
                "has_computer_lab": True,
                "has_makerspace": False,
                "has_drive_through": True,
                "has_book_drop": True,
                "has_self_checkout": True,
                "ils_location_code": "NORTH1",
                "display_order": 2,
                "hours": {
                    "monday": (time(10, 0), time(17, 0)),
                    "tuesday": (time(10, 0), time(17, 0)),
                    "wednesday": (time(10, 0), time(19, 0)),
                    "thursday": (time(10, 0), time(17, 0)),
                    "friday": (time(10, 0), time(17, 0)),
                    "saturday": (time(11, 0), time(15, 0)),
                    "sunday": None,  # Closed
                },
            },
            {
                "code": "SOUTH1",
                "region_code": "SOUTH",
                "name": "Community Annex",
                "short_name": "Annex",
                "branch_type": BranchType.BRANCH,
                "address_line1": "289 Pine Road",
                "city": branding.city,
                "state": branding.state,
                "zip_code": branding.zip_code,
                "phone": branding.phone,
                "email": f"south@{_email_domain}",
                "latitude": 43.4890,
                "longitude": -79.7441,
                "square_footage": 6500,
                "parking_spaces": 20,
                "is_ada_accessible": True,
                "has_meeting_rooms": False,
                "has_computer_lab": True,
                "has_makerspace": False,
                "has_drive_through": False,
                "has_book_drop": True,
                "has_self_checkout": True,
                "ils_location_code": "SOUTH1",
                "display_order": 3,
                "hours": {
                    "monday": (time(10, 0), time(17, 0)),
                    "tuesday": (time(10, 0), time(17, 0)),
                    "wednesday": (time(10, 0), time(19, 0)),
                    "thursday": (time(10, 0), time(17, 0)),
                    "friday": (time(10, 0), time(17, 0)),
                    "saturday": (time(10, 0), time(14, 0)),
                    "sunday": None,  # Closed
                },
            },
            {
                "code": "NORTH2",
                "region_code": "NORTH",
                "name": "Bookmobile",
                "short_name": "Bookmobile",
                "branch_type": BranchType.BOOKMOBILE,
                "address_line1": branding.address_line1,
                "city": branding.city,
                "state": branding.state,
                "zip_code": branding.zip_code,
                "phone": branding.phone,
                "email": f"bookmobile@{_email_domain}",
                "latitude": 43.7290,
                "longitude": -79.4441,
                "square_footage": 5500,
                "parking_spaces": 15,
                "is_ada_accessible": True,
                "has_meeting_rooms": False,
                "has_computer_lab": True,
                "has_makerspace": False,
                "has_drive_through": False,
                "has_book_drop": True,
                "has_self_checkout": True,
                "ils_location_code": "NORTH2",
                "display_order": 4,
                "hours": {
                    "monday": (time(9, 0), time(17, 0)),
                    "tuesday": (time(9, 0), time(17, 0)),
                    "wednesday": (time(9, 0), time(17, 0)),
                    "thursday": (time(9, 0), time(17, 0)),
                    "friday": (time(9, 0), time(17, 0)),
                    "saturday": (time(10, 0), time(14, 0)),
                    "sunday": None,  # Closed
                },
            },
        ]

        branches = {}

        for branch_data in branches_data:
            hours = branch_data.pop("hours")
            region_code = branch_data.pop("region_code")

            # Check if branch already exists
            result = await self.session.execute(
                select(Branch).where(
                    (Branch.library_system_id == system.id) &
                    (Branch.code == branch_data["code"])
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"Branch '{branch_data['name']}' already exists")
                branches[branch_data["code"]] = existing
                continue

            logger.info(f"Creating branch: {branch_data['name']}")

            branch = Branch(
                library_system_id=system.id,
                region_id=regions[region_code].id,
                status=BranchStatus.ACTIVE,
                **branch_data,
            )

            self.session.add(branch)
            await self.session.flush()  # Flush to get auto-generated ID
            branches[branch_data["code"]] = branch
            self.created_count["branches"] += 1

            # Add branch hours
            await self._create_branch_hours(branch, hours)

            # Add branch settings
            await self._create_branch_settings(branch)

            if self.verbose:
                logger.debug(f"Branch created: {branch.code} - {branch.name}")

        return branches

    async def _create_branch_hours(self, branch: Branch, hours: dict) -> None:
        day_mapping = {
            "monday": DayOfWeek.MONDAY,
            "tuesday": DayOfWeek.TUESDAY,
            "wednesday": DayOfWeek.WEDNESDAY,
            "thursday": DayOfWeek.THURSDAY,
            "friday": DayOfWeek.FRIDAY,
            "saturday": DayOfWeek.SATURDAY,
            "sunday": DayOfWeek.SUNDAY,
        }

        for day_name, times in hours.items():
            if times is None:
                # Branch is closed this day
                branch_hours = BranchHours(
                    branch_id=branch.id,
                    day_of_week=day_mapping[day_name],
                    is_closed=True,
                )
            else:
                open_time, close_time = times
                branch_hours = BranchHours(
                    branch_id=branch.id,
                    day_of_week=day_mapping[day_name],
                    is_closed=False,
                    open_time=open_time,
                    close_time=close_time,
                )

            self.session.add(branch_hours)
            self.created_count["hours"] += 1

    async def _create_branch_settings(self, branch: Branch) -> None:
        settings = BranchSettings(
            branch_id=branch.id,
            # Use system defaults (null values)
            loan_period_days=None,
            renewal_limit=None,
            hold_limit=None,
            checkout_limit=None,
            overdue_fine_per_day=None,
            max_fine=None,
            fine_free=None,
            allow_ill_pickup=True,
            allow_hold_pickup=True,
            allow_returns=True,
            floating_type=FloatingCollectionType.NO_FLOAT,
            default_pickup_branch=(branch.branch_type == BranchType.MAIN),
            hold_shelf_capacity=500,
            hold_shelf_warning_threshold=80,
        )

        self.session.add(settings)

    async def run(self) -> bool:
        try:
            logger.info("=" * 60)
            logger.info(f"{branding.library_name} - Bootstrap Seeding")
            logger.info("=" * 60)

            if self.dry_run:
                logger.warning("DRY RUN MODE - No changes will be committed")

            # Create library system
            system = await self.create_library_system()
            if not system:
                logger.info("Skipping seed - system already fully initialized")
                return True

            # Create regions
            regions = await self.create_regions(system)

            # Create branches
            branches = await self.create_branches(system, regions)

            if not self.dry_run:
                await self.session.commit()
                logger.info("Database changes committed successfully")
            else:
                await self.session.rollback()
                logger.info("DRY RUN: Changes rolled back (not committed)")

            # Summary
            logger.info("=" * 60)
            logger.info("Bootstrap Seeding Summary:")
            logger.info(f"  Library Systems: {self.created_count['systems']}")
            logger.info(f"  Regions: {self.created_count['regions']}")
            logger.info(f"  Branches: {self.created_count['branches']}")
            logger.info(f"  Branch Hours: {self.created_count['hours']}")
            logger.info("=" * 60)

            return True

        except Exception as e:
            logger.error(f"Error during bootstrap seeding: {e}", exc_info=True)
            await self.session.rollback()
            return False


async def bootstrap(dry_run: bool = False, verbose: bool = False) -> bool:
    async with AsyncSessionLocal() as session:
        seeder = LibrarySystemBootstrap(session, dry_run=dry_run, verbose=verbose)
        return await seeder.run()


async def main():
    parser = ArgumentParser(
        description=f"Bootstrap the {branding.library_name} system"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate seeding without committing changes"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    success = await bootstrap(dry_run=args.dry_run, verbose=args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
