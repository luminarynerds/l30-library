# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff admin API for the circulation_policy sparse matrix.

Powers the Phase 2 admin UI that lets directors/admins edit per-(role,
item_type, binding, collection) circulation knobs. Read endpoints support
filter query params and deterministic specificity ordering. The ``/preview``
endpoint reuses ``services.circulation_policy.resolve_with_provenance`` to
surface "where does this value come from?" tooltips.

Permissions: all endpoints require ADMIN/SUPER_ADMIN/DIRECTOR via
``require_admin``. Editing circulation policy can change fines and loan
periods for every patron; this is not a routine-desk operation.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.catalog import CatalogItem, ItemType
from ....models.circulation_policy import BookBinding, CirculationPolicy
from ....models.user import User, UserRole
from ....schemas.circulation_policy import (
    CirculationPolicyCreate,
    CirculationPolicyResponse,
    CirculationPolicyUpdate,
    ProvenanceEntry,
    ResolvedPolicyResponse,
)
from ....services.circulation_policy import (
    _default_library_system_id,  # internal helper, intentionally reused
    resolve_with_provenance,
)
from ..dependencies import require_admin

router = APIRouter(
    prefix="/staff/circulation-policies",
    tags=["staff-circulation-policies"],
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _specificity_rank(p: CirculationPolicy) -> int:
    score = 0
    if p.collection_id is not None:
        score += 8
    if p.item_type is not None:
        score += 4
    if p.role is not None:
        score += 2
    if p.binding is not None:
        score += 1
    return -score


def _validate_binding_for_item_type(
    item_type: Optional[ItemType], binding: Optional[BookBinding]
) -> None:
    if binding is not None and item_type is not None and item_type != ItemType.book:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "binding can only be set when item_type is 'book' or NULL "
                f"(got item_type='{item_type.value}')"
            ),
        )


async def _resolve_library_system_id(
    db: AsyncSession, requested: Optional[int], caller: Optional[User] = None
) -> int:
    if requested is not None:
        return requested
    if caller is not None:
        home_id = getattr(caller, "home_library_system_id", None)
        if home_id is not None:
            return home_id
    sys_id = await _default_library_system_id(db)
    if sys_id is None:
        # Policy administration needs a configured system; checkout itself
        # degrades to built-in defaults instead (circulation_policy.resolve).
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No library system is configured yet. Run setup before managing circulation policies.",
        )
    return sys_id


# ---------------------------------------------------------------------------
# list / fetch
# ---------------------------------------------------------------------------


@router.get("", response_model=list[CirculationPolicyResponse])
async def list_policies(
    role: Optional[UserRole] = Query(default=None),
    item_type: Optional[ItemType] = Query(default=None),
    binding: Optional[BookBinding] = Query(default=None),
    collection_id: Optional[int] = Query(default=None),
    active: Optional[bool] = Query(
        default=None,
        description="If omitted, returns active+inactive rows.",
    ),
    library_system_id: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[CirculationPolicy]:
    """List circulation policies for the deployment.

    Filters match by exact value (no wildcard expansion -- the resolver does
    that at runtime). Results are ordered most-specific first, then by id.
    """
    sys_id = await _resolve_library_system_id(db, library_system_id, current_user)

    conds = [CirculationPolicy.library_system_id == sys_id]
    if role is not None:
        conds.append(CirculationPolicy.role == role)
    if item_type is not None:
        conds.append(CirculationPolicy.item_type == item_type)
    if binding is not None:
        conds.append(CirculationPolicy.binding == binding)
    if collection_id is not None:
        conds.append(CirculationPolicy.collection_id == collection_id)
    if active is not None:
        conds.append(CirculationPolicy.active.is_(active))

    stmt = select(CirculationPolicy).where(and_(*conds))
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    rows.sort(key=lambda p: (_specificity_rank(p), p.id))
    return rows


@router.get("/preview", response_model=ResolvedPolicyResponse)
async def preview_resolution(
    # ID-pair mode: look up real records.
    user_id: Optional[int] = Query(default=None),
    item_id: Optional[int] = Query(default=None),
    # Scope-axes mode: pass the axes directly for hypothetical lookups
    # ("what would a child see for a hardback book?"). All four axes optional;
    # NULL means "any" for that axis -- same semantics as the policy table.
    role: Optional[UserRole] = Query(default=None),
    item_type: Optional[ItemType] = Query(default=None),
    binding: Optional[BookBinding] = Query(default=None),
    library_system_id: Optional[int] = Query(default=None),
    collection_id: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ResolvedPolicyResponse:
    """Run the resolver and report per-field provenance.

    Two modes:
    - Pass user_id + item_id to resolve against real records.
    - Pass any of role / item_type / binding / library_system_id
      to synthesize a lookup (admin UI's "pick a sample patron" dropdown).
    Mixing modes is allowed; explicit scope axes win over the lookup user/item.
    """
    # Resolve user: real record or synthetic stand-in carrying just the role
    # the resolver inspects (User.role + User.library_system_id).
    if user_id is not None:
        user = await db.get(User, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
    else:
        user = User()
        user.id = 0
    if role is not None:
        user.role = role
    elif user_id is None:
        # No real user and no explicit role -> default to patron for the resolver
        # (so the (role=NULL) format rows win).
        user.role = UserRole.PATRON
    if library_system_id is not None:
        user.library_system_id = library_system_id

    # Resolve item: real record or synthetic stand-in carrying item_type + binding.
    if item_id is not None:
        item = await db.get(CatalogItem, item_id)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found"
            )
    elif item_type is not None:
        item = CatalogItem()
        item.id = 0
        item.item_type = item_type
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide item_id or item_type for preview",
        )
    if binding is not None:
        item.binding = binding

    resolved, provenance = await resolve_with_provenance(
        user=user,
        item=item,
        db=db,
        collection_id=collection_id,
        library_system_id=library_system_id,
    )

    return ResolvedPolicyResponse(
        loan_period_days=resolved.loan_period_days,
        max_renewals=resolved.max_renewals,
        overdue_fine_per_day=resolved.overdue_fine_per_day,
        max_fine=resolved.max_fine,
        grace_period_days=resolved.grace_period_days,
        hold_pickup_days=resolved.hold_pickup_days,
        fine_free=resolved.fine_free,
        provenance={
            field: ProvenanceEntry(
                source=fp.source, policy_id=fp.policy_id, scope=fp.scope
            )
            for field, fp in provenance.items()
        },
    )


@router.get("/{policy_id}", response_model=CirculationPolicyResponse)
async def get_policy(
    policy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> CirculationPolicy:
    """Fetch a single circulation_policy row."""
    policy = await db.get(CirculationPolicy, policy_id)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circulation policy {policy_id} not found",
        )
    return policy


# ---------------------------------------------------------------------------
# create / update / delete
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=CirculationPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_policy(
    data: CirculationPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> CirculationPolicy:
    """Create a new circulation_policy row.

    Validation:
      - At least one knob must be set (enforced in the Pydantic model).
      - binding may only be set when item_type is 'book' or NULL.
      - (library_system_id, role, item_type, binding, collection_id) is
        unique; duplicates return 409.
    """
    _validate_binding_for_item_type(data.item_type, data.binding)

    sys_id = await _resolve_library_system_id(db, data.library_system_id, current_user)

    payload = data.model_dump(exclude_unset=False)
    payload["library_system_id"] = sys_id

    policy = CirculationPolicy(**payload)
    db.add(policy)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A circulation policy already exists for this scope "
                "(library_system_id, role, item_type, binding, collection_id). "
                "Edit the existing row instead."
            ),
        ) from None
    await db.refresh(policy)
    return policy


@router.put("/{policy_id}", response_model=CirculationPolicyResponse)
async def update_policy(
    policy_id: int,
    data: CirculationPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> CirculationPolicy:
    """Partially update a policy. library_system_id is immutable here."""
    policy = await db.get(CirculationPolicy, policy_id)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circulation policy {policy_id} not found",
        )

    update_fields = data.model_dump(exclude_unset=True)

    # Compute the effective (item_type, binding) post-update for cross-field check.
    effective_item_type = update_fields.get("item_type", policy.item_type)
    effective_binding = update_fields.get("binding", policy.binding)
    _validate_binding_for_item_type(effective_item_type, effective_binding)

    for k, v in update_fields.items():
        setattr(policy, k, v)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Update would collide with an existing policy for "
                "(library_system_id, role, item_type, binding, collection_id)."
            ),
        ) from None
    await db.refresh(policy)
    return policy


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    """Hard-delete a circulation_policy row. Operators can re-create."""
    policy = await db.get(CirculationPolicy, policy_id)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circulation policy {policy_id} not found",
        )
    await db.delete(policy)
    await db.commit()
    return None
