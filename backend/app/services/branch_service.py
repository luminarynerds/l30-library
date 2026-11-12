# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.timezone_utils import utc_to_local
from app.models.multi_branch import (
    Branch,
    BranchClosure,
    BranchHours,
    BranchItemCopy,
    BranchSettings,
    BranchStatistics,
    BranchStatus,
    BranchType,
    DayOfWeek,
    FloatingCollectionType,
    LibrarySystem,
    TransitPriority,
    TransitReason,
    TransitRequest,
    TransitStatus,
    Region,
    SettingDefinition,
    SettingOverride,
    SettingScopeLevel,
    SystemSettings,
)
from app.models.inventory import ItemCopy
from app.models.user import User


class BranchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # LIBRARY SYSTEM MANAGEMENT
    # =========================================================================

    async def create_library_system(self, code: str, name: str, **kwargs) -> LibrarySystem:
        system = LibrarySystem(code=code.upper(), name=name, **kwargs)
        self.db.add(system)
        await self.db.flush()

        # Create default system settings
        settings = SystemSettings(library_system_id=system.id)
        self.db.add(settings)
        await self.db.commit()
        await self.db.refresh(system)

        return system

    async def get_library_system(self, system_id: int) -> LibrarySystem | None:
        result = await self.db.execute(
            select(LibrarySystem)
            .options(
                selectinload(LibrarySystem.regions),
                selectinload(LibrarySystem.branches),
                selectinload(LibrarySystem.system_settings),
            )
            .where(LibrarySystem.id == system_id)
        )
        return result.scalar_one_or_none()

    async def get_library_system_by_code(self, code: str) -> LibrarySystem | None:
        result = await self.db.execute(
            select(LibrarySystem).where(LibrarySystem.code == code.upper())
        )
        return result.scalar_one_or_none()

    async def list_library_systems(self, active_only: bool = True) -> list[LibrarySystem]:
        query = select(LibrarySystem)
        if active_only:
            query = query.where(LibrarySystem.is_active == True)
        query = query.order_by(LibrarySystem.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_library_system(self, system_id: int, **kwargs) -> LibrarySystem | None:
        system = await self.get_library_system(system_id)
        if not system:
            return None

        for key, value in kwargs.items():
            if hasattr(system, key):
                setattr(system, key, value)

        await self.db.commit()
        await self.db.refresh(system)
        return system

    # =========================================================================
    # REGION MANAGEMENT
    # =========================================================================

    async def create_region(self, library_system_id: int, code: str, name: str, **kwargs) -> Region:
        region = Region(library_system_id=library_system_id, code=code.upper(), name=name, **kwargs)
        self.db.add(region)
        await self.db.commit()
        await self.db.refresh(region)
        return region

    async def get_region(self, region_id: int) -> Region | None:
        result = await self.db.execute(
            select(Region).options(selectinload(Region.branches)).where(Region.id == region_id)
        )
        return result.scalar_one_or_none()

    async def list_regions(self, library_system_id: int, active_only: bool = True) -> list[Region]:
        query = select(Region).where(Region.library_system_id == library_system_id)
        if active_only:
            query = query.where(Region.is_active == True)
        query = query.order_by(Region.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # BRANCH MANAGEMENT
    # =========================================================================

    async def create_branch(
        self,
        library_system_id: int,
        code: str,
        name: str,
        branch_type: BranchType = BranchType.BRANCH,
        region_id: int | None = None,
        **kwargs,
    ) -> Branch:
        branch = Branch(
            library_system_id=library_system_id,
            region_id=region_id,
            code=code.upper(),
            name=name,
            branch_type=branch_type,
            **kwargs,
        )
        self.db.add(branch)
        await self.db.flush()

        # Create default branch settings
        settings = BranchSettings(branch_id=branch.id)
        self.db.add(settings)

        await self.db.commit()
        await self.db.refresh(branch)
        return branch

    async def get_branch(self, branch_id: int) -> Branch | None:
        result = await self.db.execute(
            select(Branch)
            .options(
                joinedload(Branch.library_system),
                joinedload(Branch.region),
            )
            .where(Branch.id == branch_id)
        )
        branch = result.unique().scalar_one_or_none()
        if not branch:
            return None

        # Load hours manually (relationship is disabled on the model)
        hours_result = await self.db.execute(
            select(BranchHours).where(BranchHours.branch_id == branch_id)
        )
        branch.hours = list(hours_result.scalars().all())

        # Load closures manually
        closures_result = await self.db.execute(
            select(BranchClosure).where(BranchClosure.branch_id == branch_id)
        )
        branch.closures = list(closures_result.scalars().all())

        # Load settings manually
        settings_result = await self.db.execute(
            select(BranchSettings).where(BranchSettings.branch_id == branch_id)
        )
        branch.settings = settings_result.scalar_one_or_none()

        return branch

    async def get_branch_by_code(self, library_system_id: int, code: str) -> Branch | None:
        result = await self.db.execute(
            select(Branch).where(
                and_(Branch.library_system_id == library_system_id, Branch.code == code.upper())
            )
        )
        return result.scalar_one_or_none()

    async def list_branches(
        self,
        library_system_id: int | None = None,
        region_id: int | None = None,
        branch_type: BranchType | None = None,
        status: BranchStatus | None = None,
        active_only: bool = True,
    ) -> list[Branch]:
        query = select(Branch)

        if library_system_id:
            query = query.where(Branch.library_system_id == library_system_id)
        if region_id:
            query = query.where(Branch.region_id == region_id)
        if branch_type:
            query = query.where(Branch.branch_type == branch_type)
        if status:
            query = query.where(Branch.status == status)
        if active_only:
            query = query.where(Branch.status == BranchStatus.ACTIVE)

        query = query.order_by(Branch.display_order, Branch.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_branch(self, branch_id: int, **kwargs) -> Branch | None:
        branch = await self.get_branch(branch_id)
        if not branch:
            return None

        for key, value in kwargs.items():
            if hasattr(branch, key):
                setattr(branch, key, value)

        await self.db.commit()
        await self.db.refresh(branch)
        return branch

    # =========================================================================
    # BRANCH HOURS
    # =========================================================================

    async def set_branch_hours(
        self,
        branch_id: int,
        day_of_week: DayOfWeek,
        is_closed: bool = False,
        open_time: time | None = None,
        close_time: time | None = None,
        effective_from: date | None = None,
        effective_until: date | None = None,
        **kwargs,
    ) -> BranchHours:
        # Check if hours already exist for this day
        result = await self.db.execute(
            select(BranchHours).where(
                and_(
                    BranchHours.branch_id == branch_id,
                    BranchHours.day_of_week == day_of_week,
                    BranchHours.effective_from == effective_from,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.is_closed = is_closed
            existing.open_time = open_time
            existing.close_time = close_time
            existing.effective_until = effective_until
            for key, value in kwargs.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            hours = existing
        else:
            hours = BranchHours(
                branch_id=branch_id,
                day_of_week=day_of_week,
                is_closed=is_closed,
                open_time=open_time,
                close_time=close_time,
                effective_from=effective_from,
                effective_until=effective_until,
                **kwargs,
            )
            self.db.add(hours)

        await self.db.commit()
        await self.db.refresh(hours)
        return hours

    async def get_branch_hours(
        self, branch_id: int, effective_date: date | None = None
    ) -> list[BranchHours]:
        query = select(BranchHours).where(BranchHours.branch_id == branch_id)

        if effective_date:
            query = query.where(
                or_(
                    BranchHours.effective_from.is_(None),
                    BranchHours.effective_from <= effective_date,
                )
            ).where(
                or_(
                    BranchHours.effective_until.is_(None),
                    BranchHours.effective_until >= effective_date,
                )
            )

        query = query.order_by(BranchHours.day_of_week)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def is_branch_open(
        self, branch_id: int, check_datetime: datetime | None = None
    ) -> tuple[bool, str | None]:
        if check_datetime is None:
            check_datetime = datetime.now(timezone.utc)

        # Fetch branch with library_system to get timezone
        result = await self.db.execute(
            select(Branch).options(joinedload(Branch.library_system)).where(Branch.id == branch_id)
        )
        branch = result.scalar_one_or_none()

        if not branch:
            return False, "Branch not found"

        # Get branch timezone from library_system, default to UTC if not set
        branch_timezone = (
            branch.library_system.timezone
            if branch.library_system and branch.library_system.timezone
            else "UTC"
        )

        # Convert UTC datetime to branch's local timezone before extracting date/time
        local_datetime = utc_to_local(check_datetime, branch_timezone)
        check_date = local_datetime.date()
        check_time = local_datetime.time()

        # First check for closures
        result = await self.db.execute(
            select(BranchClosure).where(
                and_(
                    BranchClosure.branch_id == branch_id,
                    BranchClosure.start_date <= check_date,
                    BranchClosure.end_date >= check_date,
                )
            )
        )
        closure = result.scalar_one_or_none()

        if closure:
            # Check if it's a partial day closure
            if closure.start_time and closure.end_time:
                if closure.start_time <= check_time <= closure.end_time:
                    return False, closure.reason
            else:
                return False, closure.reason

        # Get today's hours (use local datetime for correct day of week)
        day_name = local_datetime.strftime("%A").lower()
        day_of_week = DayOfWeek(day_name)

        hours = await self.get_branch_hours(branch_id, check_date)
        day_hours = next((h for h in hours if h.day_of_week == day_of_week), None)

        if not day_hours:
            return False, "No hours set"

        if day_hours.is_closed:
            return False, "Closed today"

        if day_hours.open_time and day_hours.close_time:
            if day_hours.open_time <= check_time <= day_hours.close_time:
                return True, None

            # Check second shift if exists
            if day_hours.open_time_2 and day_hours.close_time_2:
                if day_hours.open_time_2 <= check_time <= day_hours.close_time_2:
                    return True, None

        return False, "Outside operating hours"

    # =========================================================================
    # BRANCH CLOSURES
    # =========================================================================

    async def create_closure(
        self,
        branch_id: int,
        start_date: date,
        end_date: date,
        reason: str,
        created_by_id: int,
        **kwargs,
    ) -> BranchClosure:
        closure = BranchClosure(
            branch_id=branch_id,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            created_by_id=created_by_id,
            **kwargs,
        )
        self.db.add(closure)
        await self.db.commit()
        await self.db.refresh(closure)
        return closure

    async def get_upcoming_closures(
        self,
        branch_id: int | None = None,
        library_system_id: int | None = None,
        days_ahead: int = 30,
    ) -> list[BranchClosure]:
        # Determine "today" based on the appropriate timezone
        if branch_id:
            # Get the branch's timezone from its library system
            result = await self.db.execute(
                select(Branch)
                .options(joinedload(Branch.library_system))
                .where(Branch.id == branch_id)
            )
            branch = result.scalar_one_or_none()

            if branch and branch.library_system and branch.library_system.timezone:
                branch_tz = ZoneInfo(branch.library_system.timezone)
                today = datetime.now(branch_tz).date()
            else:
                # Fallback to UTC if branch not found or no timezone set
                today = datetime.now(timezone.utc).date()
        else:
            # For system-wide queries, use UTC as a reasonable default
            today = datetime.now(timezone.utc).date()

        # Calculate the end of the date range using days_ahead
        end_date = today + timedelta(days=days_ahead)

        # Build query: closures that haven't ended yet AND start within the date range
        query = select(BranchClosure).where(
            and_(BranchClosure.end_date >= today, BranchClosure.start_date <= end_date)
        )

        if branch_id:
            query = query.where(BranchClosure.branch_id == branch_id)
        elif library_system_id:
            query = query.join(Branch).where(Branch.library_system_id == library_system_id)

        query = query.order_by(BranchClosure.start_date)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # BRANCH SETTINGS / POLICY INHERITANCE
    # =========================================================================

    async def get_effective_setting(
        self,
        setting_key: str,
        branch_id: int | None = None,
        region_id: int | None = None,
        library_system_id: int | None = None,
        consortium_id: int | None = None,
    ) -> Any:
        # Get the setting definition
        result = await self.db.execute(
            select(SettingDefinition).where(SettingDefinition.key == setting_key)
        )
        definition = result.scalar_one_or_none()

        if not definition:
            return None

        # Check overrides from most specific to least specific
        scopes_to_check = []

        if branch_id:
            scopes_to_check.append((SettingScopeLevel.BRANCH, branch_id, "branch_id"))
        if region_id:
            scopes_to_check.append((SettingScopeLevel.REGION, region_id, "region_id"))
        if library_system_id:
            scopes_to_check.append(
                (SettingScopeLevel.SYSTEM, library_system_id, "library_system_id")
            )
        if consortium_id:
            scopes_to_check.append((SettingScopeLevel.CONSORTIUM, consortium_id, "consortium_id"))

        for scope_level, scope_id, id_field in scopes_to_check:
            result = await self.db.execute(
                select(SettingOverride).where(
                    and_(
                        SettingOverride.setting_definition_id == definition.id,
                        SettingOverride.scope_level == scope_level,
                        getattr(SettingOverride, id_field) == scope_id,
                    )
                )
            )
            override = result.scalar_one_or_none()

            if override:
                # Check effective dates
                now = datetime.now(timezone.utc)
                if override.effective_from and now < override.effective_from:
                    continue
                if override.effective_until and now > override.effective_until:
                    continue

                return self._parse_setting_value(override.value, definition.data_type)

        # Return default value
        return self._parse_setting_value(definition.default_value, definition.data_type)

    def _parse_setting_value(self, value: str | None, data_type: str) -> Any:
        if value is None:
            return None

        if data_type == "integer":
            return int(value)
        elif data_type == "decimal":
            return Decimal(value)
        elif data_type == "boolean":
            return value.lower() in ("true", "1", "yes")
        elif data_type == "json":
            import json

            return json.loads(value)
        else:
            return value

    async def set_setting_override(
        self,
        setting_key: str,
        value: Any,
        scope_level: SettingScopeLevel,
        scope_id: int,
        set_by_id: int,
        effective_from: datetime | None = None,
        effective_until: datetime | None = None,
    ) -> SettingOverride:
        # Get the setting definition
        result = await self.db.execute(
            select(SettingDefinition).where(SettingDefinition.key == setting_key)
        )
        definition = result.scalar_one_or_none()

        if not definition:
            raise ValueError(f"Unknown setting: {setting_key}")

        # Check if override is allowed at this level
        scope_order = [
            SettingScopeLevel.CONSORTIUM,
            SettingScopeLevel.SYSTEM,
            SettingScopeLevel.REGION,
            SettingScopeLevel.BRANCH,
        ]

        min_index = scope_order.index(definition.min_scope_level)
        requested_index = scope_order.index(scope_level)

        if requested_index < min_index:
            raise ValueError(
                f"Setting {setting_key} cannot be configured at {scope_level.value} level"
            )

        # Determine which ID field to use
        id_field_map = {
            SettingScopeLevel.CONSORTIUM: "consortium_id",
            SettingScopeLevel.SYSTEM: "library_system_id",
            SettingScopeLevel.REGION: "region_id",
            SettingScopeLevel.BRANCH: "branch_id",
        }
        id_field = id_field_map[scope_level]

        # Check for existing override
        result = await self.db.execute(
            select(SettingOverride).where(
                and_(
                    SettingOverride.setting_definition_id == definition.id,
                    SettingOverride.scope_level == scope_level,
                    getattr(SettingOverride, id_field) == scope_id,
                )
            )
        )
        existing = result.scalar_one_or_none()

        # Convert value to string
        if isinstance(value, bool):
            str_value = "true" if value else "false"
        elif isinstance(value, (dict, list)):
            import json

            str_value = json.dumps(value)
        else:
            str_value = str(value)

        if existing:
            existing.value = str_value
            existing.set_by_id = set_by_id
            existing.set_at = datetime.now(timezone.utc)
            existing.effective_from = effective_from
            existing.effective_until = effective_until
            override = existing
        else:
            override = SettingOverride(
                setting_definition_id=definition.id,
                scope_level=scope_level,
                value=str_value,
                set_by_id=set_by_id,
                effective_from=effective_from,
                effective_until=effective_until,
                **{id_field: scope_id},
            )
            self.db.add(override)

        await self.db.commit()
        await self.db.refresh(override)
        return override

    # =========================================================================
    # ITEM BRANCH ASSIGNMENT
    # =========================================================================

    async def assign_item_to_branch(
        self,
        item_copy_id: int,
        branch_id: int,
        is_floating: bool = False,
        float_scope: FloatingCollectionType = FloatingCollectionType.NO_FLOAT,
        shelving_location: str | None = None,
        set_as_home: bool = True,
    ) -> BranchItemCopy:
        # Check if assignment already exists
        result = await self.db.execute(
            select(BranchItemCopy).where(BranchItemCopy.item_copy_id == item_copy_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.current_branch_id = branch_id
            if set_as_home:
                existing.home_branch_id = branch_id
            existing.is_floating = is_floating
            existing.float_scope = float_scope
            existing.shelving_location = shelving_location
            existing.last_seen_at = datetime.now(timezone.utc)
            assignment = existing
        else:
            assignment = BranchItemCopy(
                item_copy_id=item_copy_id,
                home_branch_id=branch_id if set_as_home else None,
                current_branch_id=branch_id,
                is_floating=is_floating,
                float_scope=float_scope,
                shelving_location=shelving_location,
                last_seen_at=datetime.now(timezone.utc),
            )
            self.db.add(assignment)

        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def update_item_location(
        self,
        item_copy_id: int,
        current_branch_id: int,
        shelving_location: str | None = None,
        circulated: bool = False,
    ) -> BranchItemCopy | None:
        result = await self.db.execute(
            select(BranchItemCopy).where(BranchItemCopy.item_copy_id == item_copy_id)
        )
        assignment = result.scalar_one_or_none()

        if not assignment:
            return None

        assignment.current_branch_id = current_branch_id
        if shelving_location:
            assignment.shelving_location = shelving_location
        assignment.last_seen_at = datetime.now(timezone.utc)

        if circulated:
            assignment.last_circulated_branch_id = current_branch_id

        # Handle floating collections
        if assignment.is_floating:
            # Floating items stay at whatever branch they're checked in at.
            # Update home branch to current branch so shelving is local.
            assignment.home_branch_id = current_branch_id
        elif (
            assignment.float_scope == FloatingCollectionType.NO_FLOAT
            and assignment.home_branch_id
            and assignment.home_branch_id != current_branch_id
        ):
            # Non-floating items checked in at wrong branch need transit home.
            # Create a transit request to route the item back.
            transit = TransitRequest(
                item_copy_id=item_copy_id,
                from_branch_id=current_branch_id,
                to_branch_id=assignment.home_branch_id,
                reason=TransitReason.RETURN_TO_HOME,
                priority=TransitPriority.NORMAL,
                status=TransitStatus.REQUESTED,
                # System-generated: no user requested this transit. The old
                # hardcoded id 1 assumed a user that need not exist (fresh
                # install, or the first user was deleted) and tripped the
                # users FK.
                requested_by_id=None,
            )
            self.db.add(transit)

        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def get_branch_inventory(
        self, branch_id: int, include_in_transit: bool = False
    ) -> list[BranchItemCopy]:
        query = select(BranchItemCopy).where(BranchItemCopy.current_branch_id == branch_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_items_away_from_home(self, branch_id: int) -> list[BranchItemCopy]:
        result = await self.db.execute(
            select(BranchItemCopy).where(
                and_(
                    BranchItemCopy.home_branch_id == branch_id,
                    BranchItemCopy.current_branch_id != branch_id,
                    BranchItemCopy.is_floating == False,
                )
            )
        )
        return list(result.scalars().all())

    # =========================================================================
    # STAFF BRANCH ASSIGNMENT
    # =========================================================================

    async def assign_staff_to_branch(self, user_id: int, branch_id: int) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        user.work_branch_id = branch_id
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_branch_staff(self, branch_id: int) -> list[User]:
        result = await self.db.execute(select(User).where(User.work_branch_id == branch_id))
        return list(result.scalars().all())

    # =========================================================================
    # PATRON HOME BRANCH
    # =========================================================================

    async def set_patron_home_branch(self, user_id: int, branch_id: int) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        # Get the branch to find the system
        branch = await self.get_branch(branch_id)
        if not branch:
            raise ValueError(f"Branch {branch_id} not found")

        user.home_branch_id = branch_id
        user.home_library_system_id = branch.library_system_id
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_branch_patrons(self, branch_id: int, active_only: bool = True) -> list[User]:
        query = select(User).where(User.home_branch_id == branch_id)
        if active_only:
            query = query.where(User.is_active == True)

        result = await self.db.execute(query)
        return list(result.scalars().all())
