# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from app.core.logging import get_logger
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.circulation_config import LOAN_PERIOD_DAYS, OVERDUE_FINE_PER_DAY
from ..models.catalog import CatalogItem, ItemType
from ..models.circulation_policy import BookBinding, CirculationPolicy
from ..models.multi_branch import SystemSettings
from ..models.user import User, UserRole


logger = get_logger(__name__)


@dataclass
class ResolvedPolicy:

    loan_period_days: int
    max_renewals: int
    overdue_fine_per_day: Decimal
    max_fine: Decimal
    grace_period_days: int
    hold_pickup_days: int
    fine_free: bool


@dataclass
class FieldProvenance:

    source: str
    policy_id: Optional[int]
    scope: str


_POLICY_FIELDS = (
    "loan_period_days",
    "max_renewals",
    "overdue_fine_per_day",
    "max_fine",
    "grace_period_days",
    "hold_pickup_days",
    "fine_free",
)


async def resolve(
    *,
    user: User,
    item: CatalogItem,
    db: AsyncSession,
    collection_id: Optional[int] = None,
    library_system_id: Optional[int] = None,
) -> ResolvedPolicy:
    sys_id = (
        library_system_id
        or getattr(user, "library_system_id", None)
        or getattr(user, "home_library_system_id", None)
    )
    if sys_id is None:
        # No user/system context at all (e.g. resolver smoke tests with synthetic
        # users): pick the only system_settings row. Works as long as L30 stays
        # single-system.
        sys_id = await _default_library_system_id(db)
    if sys_id is None:
        # Unconfigured install: no system_settings row anywhere. Circulate on
        # the built-in defaults rather than refusing every checkout until the
        # setup wizard has run.
        logger.warning(
            "circulation_policy.resolve: no system_settings row; using built-in defaults"
        )
        return ResolvedPolicy(**_system_defaults(None))  # type: ignore[arg-type]

    candidates = await _load_candidates(
        db=db,
        library_system_id=sys_id,
        role=user.role,
        item_type=item.item_type,
        binding=getattr(item, "binding", None),
        collection_id=collection_id,
    )
    # Order candidates by precedence rank (lower index = more specific).
    candidates_by_rank = sorted(candidates, key=_precedence_rank)

    # Per-field walk: take the most-specific non-NULL value for each field.
    resolved: dict[str, object] = {}
    for field_name in _POLICY_FIELDS:
        for policy in candidates_by_rank:
            val = getattr(policy, field_name)
            if val is not None:
                resolved[field_name] = val
                break

    # Fallback to system_settings + hardcoded defaults for any field still missing.
    settings = await _load_system_settings(db, sys_id)
    defaults = _system_defaults(settings)
    for field_name in _POLICY_FIELDS:
        resolved.setdefault(field_name, defaults[field_name])

    return ResolvedPolicy(**resolved)  # type: ignore[arg-type]


# Convenience wrappers preserving the get_user_loan_period signature so
# checkout_service.py can swap in without ceremony.
async def get_loan_period_days(
    user: User, item: CatalogItem, db: AsyncSession, collection_id: Optional[int] = None
) -> int:
    policy = await resolve(user=user, item=item, db=db, collection_id=collection_id)
    return policy.loan_period_days


async def get_overdue_fine_per_day(
    user: User, item: CatalogItem, db: AsyncSession, collection_id: Optional[int] = None
) -> Decimal:
    policy = await resolve(user=user, item=item, db=db, collection_id=collection_id)
    if policy.fine_free:
        return Decimal("0.00")
    return policy.overdue_fine_per_day


async def resolve_with_provenance(
    *,
    user: User,
    item: CatalogItem,
    db: AsyncSession,
    collection_id: Optional[int] = None,
    library_system_id: Optional[int] = None,
) -> tuple[ResolvedPolicy, dict[str, FieldProvenance]]:
    sys_id = (
        library_system_id
        or getattr(user, "library_system_id", None)
        or getattr(user, "home_library_system_id", None)
    )
    if sys_id is None:
        sys_id = await _default_library_system_id(db)
    if sys_id is None:
        # Unconfigured install: no system_settings row anywhere. Report the
        # factory defaults rather than failing the provenance view.
        defaults = _system_defaults(None)
        return (
            ResolvedPolicy(**defaults),  # type: ignore[arg-type]
            {
                field_name: FieldProvenance(
                    source="default", policy_id=None, scope="factory default"
                )
                for field_name in _POLICY_FIELDS
            },
        )

    candidates = await _load_candidates(
        db=db,
        library_system_id=sys_id,
        role=user.role,
        item_type=item.item_type,
        binding=getattr(item, "binding", None),
        collection_id=collection_id,
    )
    candidates_by_rank = sorted(candidates, key=_precedence_rank)

    resolved: dict[str, object] = {}
    provenance: dict[str, FieldProvenance] = {}
    for field_name in _POLICY_FIELDS:
        for policy in candidates_by_rank:
            val = getattr(policy, field_name)
            if val is not None:
                resolved[field_name] = val
                provenance[field_name] = FieldProvenance(
                    source="policy",
                    policy_id=policy.id,
                    scope=_describe_policy_scope(policy),
                )
                break

    settings = await _load_system_settings(db, sys_id)
    defaults = _system_defaults(settings)
    for field_name in _POLICY_FIELDS:
        if field_name not in resolved:
            resolved[field_name] = defaults[field_name]
            provenance[field_name] = FieldProvenance(
                source="system_settings" if settings is not None else "default",
                policy_id=None,
                scope=(
                    "site-wide settings"
                    if settings is not None
                    else "factory default"
                ),
            )

    return ResolvedPolicy(**resolved), provenance  # type: ignore[arg-type]


# Friendly audience names for the provenance label.
# Roles not listed fall through to the .replace('_', ' ') fallback.
_ROLE_LABELS = {
    "super_admin": "super admins",
    "admin": "admins",
    "director": "directors",
    "legal": "legal staff",
    "staff": "staff",
    "patron": "patrons",
    "teacher": "teachers",
    "child": "children",
    "bookmobile": "bookmobile patrons",
    "homebond": "homebound patrons",
}

_ITEM_TYPE_LABELS = {
    "book": "books",
    "audiobook": "audiobooks",
    "ebook": "eBooks",
    "dvd": "DVDs",
    "bluray": "Blu-rays",
    "cd": "CDs",
    "vinyl": "vinyl records",
    "magazine": "magazines",
    "game": "games",
    "equipment": "equipment",
    "kit": "kits",
    "tool": "tools",
    "other": "other items",
}

_BINDING_LABELS = {
    "hardback": "hardback",
    "paperback": "paperback",
    "mass_market": "mass-market paperback",
    "board_book": "board books",
    "spiral": "spiral-bound",
    "library_binding": "library binding",
    "other": "other binding",
}


def _describe_policy_scope(policy: CirculationPolicy) -> str:
    role = (
        _ROLE_LABELS.get(policy.role.value, policy.role.value.replace("_", " "))
        if policy.role is not None
        else None
    )
    item_type = (
        _ITEM_TYPE_LABELS.get(policy.item_type.value, policy.item_type.value)
        if policy.item_type is not None
        else None
    )
    binding = (
        _BINDING_LABELS.get(policy.binding.value, policy.binding.value)
        if policy.binding is not None
        else None
    )

    # When binding is set alongside item_type=book, render as "hardback books"
    # rather than two separate phrases.
    if binding and item_type == "books":
        format_phrase = f"{binding} books"
    elif binding and item_type:
        format_phrase = f"{item_type} ({binding})"
    elif binding:
        format_phrase = binding
    else:
        format_phrase = item_type

    parts = []
    if policy.collection_id is not None:
        parts.append(f"collection #{policy.collection_id}")
    if format_phrase:
        parts.append(format_phrase)
    if role:
        parts.append(role)

    if not parts:
        return "all formats, all patrons"
    return ", ".join(parts)


# --- internals -------------------------------------------------------------


async def _load_candidates(
    *,
    db: AsyncSession,
    library_system_id: int,
    role: UserRole,
    item_type: ItemType,
    binding: Optional[BookBinding],
    collection_id: Optional[int],
) -> list[CirculationPolicy]:
    conds = [
        CirculationPolicy.library_system_id == library_system_id,
        CirculationPolicy.active.is_(True),
        or_(CirculationPolicy.role.is_(None), CirculationPolicy.role == role),
        or_(
            CirculationPolicy.item_type.is_(None),
            CirculationPolicy.item_type == item_type,
        ),
    ]
    if binding is None:
        conds.append(CirculationPolicy.binding.is_(None))
    else:
        conds.append(
            or_(
                CirculationPolicy.binding.is_(None),
                CirculationPolicy.binding == binding,
            )
        )
    if collection_id is None:
        conds.append(CirculationPolicy.collection_id.is_(None))
    else:
        conds.append(
            or_(
                CirculationPolicy.collection_id.is_(None),
                CirculationPolicy.collection_id == collection_id,
            )
        )

    stmt = select(CirculationPolicy).where(and_(*conds))
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _precedence_rank(policy: CirculationPolicy) -> int:
    score = 0
    if policy.collection_id is not None:
        score += 8
    if policy.item_type is not None:
        score += 4
    if policy.role is not None:
        score += 2
    if policy.binding is not None:
        score += 1
    return -score


async def _load_system_settings(
    db: AsyncSession, library_system_id: int
) -> Optional[SystemSettings]:
    stmt = select(SystemSettings).where(
        SystemSettings.library_system_id == library_system_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _default_library_system_id(db: AsyncSession) -> Optional[int]:
    stmt = select(SystemSettings.library_system_id).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _system_defaults(settings: Optional[SystemSettings]) -> dict[str, object]:
    if settings is None:
        return {
            "loan_period_days": LOAN_PERIOD_DAYS,
            "max_renewals": 2,
            "overdue_fine_per_day": OVERDUE_FINE_PER_DAY,
            "max_fine": Decimal("25.00"),
            "grace_period_days": 0,
            "hold_pickup_days": 7,
            "fine_free": False,
        }
    return {
        "loan_period_days": settings.default_loan_period_days or LOAN_PERIOD_DAYS,
        "max_renewals": settings.default_renewal_limit or 2,
        "overdue_fine_per_day": settings.default_overdue_fine_per_day
        or OVERDUE_FINE_PER_DAY,
        "max_fine": settings.default_max_fine or Decimal("25.00"),
        "grace_period_days": settings.grace_period_days or 0,
        "hold_pickup_days": settings.hold_pickup_days or 7,
        "fine_free": bool(settings.fine_free_juvenile),
    }
