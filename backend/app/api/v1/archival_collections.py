# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Archival collection cataloging API.

DACS-aligned hierarchical collection management. Supports collection
CRUD, tree traversal, item assignment, finding-aid render, and EAD3
XML export.
"""
from __future__ import annotations

from app.core.logging import get_logger
from typing import Optional

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.catalog import CatalogItem
from ...models.user import User
from ...schemas.collection import (
    CollectionCreate,
    CollectionItemAdd,
    CollectionItemResponse,
    CollectionMoveRequest,
    CollectionResponse,
    CollectionTreeNode,
    CollectionUpdate,
)
from ...services import archival_collection_service as svc
from .dependencies import require_staff


logger = get_logger(__name__)
router = APIRouter(prefix="/archival-collections", tags=["archival-collections"])


def _link_response(link, item) -> CollectionItemResponse:
    return CollectionItemResponse(
        id=link.id,
        collection_id=link.collection_id,
        catalog_item_id=link.catalog_item_id,
        position=link.position,
        component_label=link.component_label,
        note=link.note,
        added_at=link.added_at,
        catalog_item_title=item.title,
        catalog_item_author=item.author,
    )


@router.get("", response_model=list[CollectionResponse])
async def list_roots(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_staff),
) -> list[CollectionResponse]:
    """List top-level collections (no parent)."""
    rows = await svc.list_root_collections(db)
    return [CollectionResponse.model_validate(r) for r in rows]


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_one(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_staff),
) -> CollectionResponse:
    row = await svc.get_collection(db, collection_id)
    return CollectionResponse.model_validate(row)


@router.get("/{collection_id}/tree", response_model=CollectionTreeNode)
async def get_tree(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_staff),
) -> CollectionTreeNode:
    return await svc.get_subtree(db, collection_id)


@router.post(
    "",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    payload: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> CollectionResponse:
    row = await svc.create_collection(db, payload)
    logger.info("Collection created id=%s by user_id=%s", row.id, user.id)
    return CollectionResponse.model_validate(row)


@router.patch("/{collection_id}", response_model=CollectionResponse)
async def update(
    collection_id: int,
    payload: CollectionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> CollectionResponse:
    row = await svc.update_collection(db, collection_id, payload)
    logger.info("Collection updated id=%s by user_id=%s", row.id, user.id)
    return CollectionResponse.model_validate(row)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> Response:
    await svc.delete_collection(db, collection_id)
    logger.info("Collection deleted id=%s by user_id=%s", collection_id, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{collection_id}/move", response_model=CollectionResponse)
async def move(
    collection_id: int,
    payload: CollectionMoveRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_staff),
) -> CollectionResponse:
    row = await svc.move_collection(
        db, collection_id, payload.new_parent_id, payload.position
    )
    return CollectionResponse.model_validate(row)


@router.get(
    "/{collection_id}/items",
    response_model=list[CollectionItemResponse],
)
async def list_collection_items(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_staff),
) -> list[CollectionItemResponse]:
    rows = await svc.list_items(db, collection_id)
    return [_link_response(link, item) for link, item in rows]


@router.post(
    "/{collection_id}/items",
    response_model=CollectionItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_item_to_collection(
    collection_id: int,
    payload: CollectionItemAdd,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_staff),
) -> CollectionItemResponse:
    link = await svc.add_item(
        db,
        collection_id,
        payload.catalog_item_id,
        position=payload.position,
        component_label=payload.component_label,
        note=payload.note,
    )
    item = link.catalog_item or await db.get(CatalogItem, payload.catalog_item_id)
    return _link_response(link, item)


@router.delete(
    "/{collection_id}/items/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_item_from_collection(
    collection_id: int,
    link_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_staff),
) -> Response:
    await svc.remove_item(db, collection_id, link_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{collection_id}/ead.xml",
    response_class=Response,
    responses={200: {"content": {"application/xml": {}}}},
)
async def export_ead(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_staff),
) -> Response:
    """Render the collection (with descendants) as EAD3 XML."""
    xml = await svc.render_ead3(db, collection_id)
    filename = f"collection-{collection_id}-ead.xml"
    return Response(
        content=xml,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
