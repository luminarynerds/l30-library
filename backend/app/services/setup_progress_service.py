# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Derived getting-started progress for a library admin.

Completion is computed live from system state, never stored. Steps that map to
org-scoped tables (users, circulation_policy) filter by library_system_id; the
rest (catalog_items, item_copies, checkouts) are global existence checks because
those tables carry no org column in this deployment.
"""
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem
from app.models.circulation import Checkout
from app.models.circulation_policy import CirculationPolicy
from app.models.inventory import ItemCopy
from app.models.user import User, UserRole

_STAFF_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.DIRECTOR,
    UserRole.LIBRARY_ADMIN,
    UserRole.STAFF,
)


@dataclass(frozen=True)
class StepMeta:
    id: str
    title: str
    description: str
    action: str
    icon: str


STEPS: list[StepMeta] = [
    StepMeta("add_team", "Add your team",
             "Invite the staff who will run circulation, cataloging, and the desk.",
             "/staff/admin/users", "users"),
    StepMeta("set_policies", "Set circulation policies",
             "Define loan periods, renewals, holds, and fines.",
             "/staff/admin/circulation-policy-dashboard", "scale"),
    StepMeta("build_catalog", "Build your catalog",
             "Import MARC/CSV or copy-catalog your first records.",
             "/staff/cataloging", "book"),
    StepMeta("add_holdings", "Add copies / holdings",
             "Attach physical copies with barcodes so items can circulate.",
             "/staff/inventory", "layers"),
    StepMeta("add_patrons", "Add patrons",
             "Import your patron list or open card applications.",
             "/staff/patrons", "user-plus"),
    StepMeta("first_checkout", "Record your first checkout",
             "Check an item out to a patron; you are live.",
             "/staff", "check-circle"),
]


async def _exists(db: AsyncSession, stmt) -> bool:
    return (await db.scalar(stmt.limit(1))) is not None


async def compute_setup_progress(db: AsyncSession, library_system_id: int) -> list[dict]:
    team_count = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.role.in_(_STAFF_ROLES),
            User.home_library_system_id == library_system_id,
            User.is_active.is_(True),
        )
    ) or 0

    completion: dict[str, tuple[bool, int | None]] = {
        "add_team": (team_count > 1, team_count),
        "set_policies": (
            await _exists(db, select(CirculationPolicy.id).where(
                CirculationPolicy.library_system_id == library_system_id)),
            None,
        ),
        "build_catalog": (await _exists(db, select(CatalogItem.id)), None),
        "add_holdings": (await _exists(db, select(ItemCopy.id)), None),
        "add_patrons": (
            await _exists(db, select(User.id).where(
                User.role == UserRole.PATRON,
                User.home_library_system_id == library_system_id)),
            None,
        ),
        "first_checkout": (await _exists(db, select(Checkout.id)), None),
    }

    steps: list[dict] = []
    for meta in STEPS:
        completed, count = completion[meta.id]
        item = {
            "id": meta.id,
            "title": meta.title,
            "description": meta.description,
            "action": meta.action,
            "icon": meta.icon,
            "completed": completed,
        }
        if count is not None:
            item["count"] = count
        steps.append(item)
    return steps
