# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff API for acquisition rationale CRUD + signal candidate suggestions.

Route ordering note: literal paths (``/catalog-items/missing-rationale``) are
registered BEFORE parameterised ones (``/catalog-items/{catalog_item_id}/...``)
so FastAPI dispatch resolves them first. If a sibling staff router ever owns a
wildcard ``/catalog-items/{id}`` pattern, this router must be included
*before* it in registry.py to avoid path shadowing.
"""

from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import get_settings
from ....core.database import get_db
from ....models.acquisition_rationale import AcquisitionRationale, BehaviorTag
from ....models.catalog import CatalogItem
from ....models.user import User
from ....schemas.acquisition_rationale import (
    AcquisitionRationaleCreate,
    AcquisitionRationaleRead,
    AcquisitionRationaleUpdate,
    BehaviorTagRead,
)
from ....services.acquisition_rationale_service import RationaleService
from ....services.librarian_agent_client import LibrarianAgentClient
from ....services.signal_link_service import SignalLinkService
from ..dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/staff", tags=["acquisition-rationale"])


async def _emit_rationale_to_kb(
    db: AsyncSession,
    catalog_item_id: int,
    rat: AcquisitionRationale,
) -> None:
    try:
        catalog_item = await db.get(CatalogItem, catalog_item_id)
        if catalog_item is None:
            # Save succeeded but item was concurrently deleted — nothing to emit.
            return
        client = LibrarianAgentClient(get_settings())
        await client.emit_rationale_aku(catalog_item=catalog_item, rationale=rat)
    except Exception as e:  # noqa: BLE001  # librarian-agent emit best-effort — rationale already saved
        logger.warning(
            "librarian-agent emit failed for rationale %s: %s",
            getattr(rat, "id", "?"), e,
        )


@router.get("/behavior-tags")
async def list_behavior_tags(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return all active behavior tags ordered by category and sort_order."""
    result = await db.execute(
        select(BehaviorTag)
        .where(BehaviorTag.active.is_(True))
        .order_by(BehaviorTag.category, BehaviorTag.sort_order)
    )
    rows = result.scalars().all()
    return {"tags": [BehaviorTagRead.model_validate(r).model_dump() for r in rows]}


@router.get("/catalog-items/missing-rationale")
async def list_missing_rationale_items(
    limit: int = 50,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Backfill helper: catalog items with no acquisition rationale recorded."""
    svc = RationaleService(db)
    ids = await svc.list_missing_rationale_items(limit=limit)
    return {"catalog_item_ids": ids, "count": len(ids)}


@router.get(
    "/catalog-items/{catalog_item_id}/acquisition-rationale",
    response_model=AcquisitionRationaleRead,
)
async def get_rationale(
    catalog_item_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    svc = RationaleService(db)
    rat = await svc.get_by_catalog_item(catalog_item_id)
    if rat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No rationale recorded for this item",
        )
    return rat


@router.post(
    "/catalog-items/{catalog_item_id}/acquisition-rationale",
    response_model=AcquisitionRationaleRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_rationale(
    catalog_item_id: int,
    data: AcquisitionRationaleCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    svc = RationaleService(db)
    existing = await svc.get_by_catalog_item(catalog_item_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Rationale already exists; use PUT to update",
        )
    rat = await svc.create(catalog_item_id, staff_user.id, data)
    await db.commit()
    await db.refresh(rat)
    await _emit_rationale_to_kb(db, catalog_item_id, rat)
    return rat


@router.put(
    "/catalog-items/{catalog_item_id}/acquisition-rationale",
    response_model=AcquisitionRationaleRead,
)
async def update_rationale(
    catalog_item_id: int,
    data: AcquisitionRationaleUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    svc = RationaleService(db)
    updated = await svc.update(catalog_item_id, data)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No rationale to update",
        )
    await db.commit()
    await db.refresh(updated)
    await _emit_rationale_to_kb(db, catalog_item_id, updated)
    return updated


@router.get("/catalog-items/{catalog_item_id}/signal-candidates")
async def signal_candidates(
    catalog_item_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Suggest possible signal source records for the given catalog item."""
    svc = SignalLinkService(db)
    candidates = await svc.search_candidates_for_item(catalog_item_id, limit=10)
    return {
        "candidates": [
            {
                "table_name": c.table_name,
                "record_id": c.record_id,
                "summary": c.summary,
                "matched_on": c.matched_on,
            }
            for c in candidates
        ]
    }


@router.get("/acquisition-rationale/similar")
async def find_similar_rationales(
    query: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=25),
    staff_user: User = Depends(require_staff),
):
    """Semantic search across emitted rationale AKUs in librarian-kb.

    Returns an empty list if librarian-agent is unreachable or returns no
    hits. Never raises — the underlying client is best-effort.

    Literal path ``/acquisition-rationale/similar`` does not collide with the
    ``/catalog-items/{id}/acquisition-rationale`` parameterised routes above
    because the prefix segments differ.
    """
    client = LibrarianAgentClient(get_settings())
    hits = await client.search_similar_rationales(query=query, limit=limit)
    if not hits:
        logger.info(
            "rationale similar: 0 hits for query=%r limit=%d staff=%s",
            query[:80], limit, staff_user.id,
        )
    return {"hits": hits, "query": query}
