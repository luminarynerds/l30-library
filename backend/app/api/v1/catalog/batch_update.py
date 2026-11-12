# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Batch Field-Update Tool for Catalog Records

Power tool for admin/director users to update a field across multiple
catalog records at once. Supports dry-run preview before committing changes.

Safety: Only a strict whitelist of fields can be updated in batch.
Title, author, ISBN, and other bibliographic identity fields are excluded.
"""
from app.core.logging import get_logger
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.audit_log import audit_log_event
from ....core.cache import invalidate_catalog_cache
from ....core.database import AsyncSessionLocal, get_db
from ....core.rate_limit import limiter
from ....models.catalog import (
    CatalogItem,
    CatalogingStatus,
    ItemStatus,
    ItemType,
    SensitivityLevel,
)
from ....models.user import User
from ....services.catalog_bibframe_sync import CatalogBibframeSync
from ..dependencies import require_admin

logger = get_logger(__name__)

router = APIRouter()

# Strict whitelist -- only these fields can be batch-updated.
# Bibliographic identity fields (title, author, ISBN, LCCN, OCLC#) are
# deliberately excluded to prevent accidental data corruption.
ALLOWED_UPDATE_FIELDS = {
    "location",
    "status",
    "call_number",
    "subjects",
    "publisher",
    "sensitivity_level",
    "cataloging_status",
}

# Enum fields that need validation before assignment
ENUM_FIELDS = {
    "status": ItemStatus,
    "sensitivity_level": SensitivityLevel,
    "cataloging_status": CatalogingStatus,
}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BatchUpdateFilter(BaseModel):
    item_type: Optional[str] = Field(None, description="Filter by item type")
    status: Optional[str] = Field(None, description="Filter by current status")
    location: Optional[str] = Field(None, description="Filter by current location")
    publisher: Optional[str] = Field(None, description="Filter by publisher (substring match)")
    subject: Optional[str] = Field(None, description="Filter by subject (substring match)")
    publication_year_min: Optional[int] = Field(None, description="Minimum publication year")
    publication_year_max: Optional[int] = Field(None, description="Maximum publication year")


class BatchUpdateRequest(BaseModel):
    filter: BatchUpdateFilter
    updates: dict[str, str] = Field(
        ...,
        description="Field:value pairs to apply. Allowed fields: "
        "location, status, call_number, subjects, publisher, "
        "sensitivity_level, cataloging_status",
    )
    dry_run: bool = Field(True, description="If true, preview changes without applying")


class BatchUpdateSampleItem(BaseModel):
    id: int
    title: str
    author: Optional[str] = None
    item_type: str
    status: str
    location: Optional[str] = None

    model_config = {"from_attributes": True}


class BatchUpdateResponse(BaseModel):
    updated_count: int = Field(..., description="Number of records affected (or would be affected)")
    filter_used: dict = Field(..., description="Filter criteria that was applied")
    fields_updated: dict = Field(..., description="Field:value pairs applied (or previewed)")
    dry_run: bool = Field(..., description="Whether this was a dry run")
    sample: list[BatchUpdateSampleItem] = Field(
        default_factory=list,
        description="Sample of matching records (up to 5)",
    )


class BatchUpdatePreviewResponse(BaseModel):
    count: int = Field(..., description="Number of records matching the filter")
    filter_used: dict = Field(..., description="Filter criteria applied")
    sample: list[BatchUpdateSampleItem] = Field(
        default_factory=list,
        description="Sample of matching records (up to 5)",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_filter_query(fltr: BatchUpdateFilter):
    query = select(CatalogItem)

    if fltr.item_type:
        try:
            item_type_enum = ItemType(fltr.item_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid item_type: {fltr.item_type}") from None
        query = query.where(CatalogItem.item_type == item_type_enum)

    if fltr.status:
        try:
            status_enum = ItemStatus(fltr.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {fltr.status}") from None
        query = query.where(CatalogItem.status == status_enum)

    if fltr.location:
        query = query.where(CatalogItem.location == fltr.location)

    if fltr.publisher:
        query = query.where(CatalogItem.publisher.ilike(f"%{fltr.publisher}%"))

    if fltr.subject:
        query = query.where(CatalogItem.subjects.ilike(f"%{fltr.subject}%"))

    if fltr.publication_year_min is not None:
        query = query.where(CatalogItem.publication_year >= fltr.publication_year_min)

    if fltr.publication_year_max is not None:
        query = query.where(CatalogItem.publication_year <= fltr.publication_year_max)

    return query


def _validate_updates(updates: dict[str, str]) -> None:
    if not updates:
        raise HTTPException(status_code=400, detail="Please specify at least one field to update.")

    invalid_fields = set(updates.keys()) - ALLOWED_UPDATE_FIELDS
    if invalid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Fields not allowed for batch update: {', '.join(sorted(invalid_fields))}. "
            f"Allowed: {', '.join(sorted(ALLOWED_UPDATE_FIELDS))}",
        )

    # Validate enum values
    for field_name, enum_cls in ENUM_FIELDS.items():
        if field_name in updates:
            try:
                enum_cls(updates[field_name])
            except ValueError:
                valid = [e.value for e in enum_cls]
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid value for {field_name}: '{updates[field_name]}'. "
                    f"Valid values: {', '.join(valid)}",
                ) from None


def _item_to_sample(item: CatalogItem) -> BatchUpdateSampleItem:
    return BatchUpdateSampleItem(
        id=item.id,
        title=item.title,
        author=item.author,
        item_type=item.item_type.value if hasattr(item.item_type, "value") else str(item.item_type),
        status=item.status.value if hasattr(item.status, "value") else str(item.status),
        location=item.location,
    )


async def _sync_bibframe_background(item_id: int) -> None:
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(CatalogItem).where(CatalogItem.id == item_id)
            )
            item = result.scalar_one_or_none()
            if item:
                await CatalogBibframeSync.update_from_catalog(db, item)
                await db.commit()
    except Exception:
        logger.exception("Failed to sync batch-updated item %d to BIBFRAME", item_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/batch-update", response_model=BatchUpdateResponse)
@limiter.limit("10/minute")
async def batch_update_catalog(
    request: Request,
    body: BatchUpdateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Batch-update a field across multiple catalog records.

    **Admin/Director only.** Defaults to dry_run=true for safety.

    Allowed update fields: location, status, call_number, subjects,
    publisher, sensitivity_level, cataloging_status.
    """
    _validate_updates(body.updates)

    query = _build_filter_query(body.filter)

    # Count matching records
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    if total == 0:
        return BatchUpdateResponse(
            updated_count=0,
            filter_used=body.filter.model_dump(exclude_none=True),
            fields_updated=body.updates,
            dry_run=body.dry_run,
            sample=[],
        )

    # Get sample of up to 5 records
    sample_result = await db.execute(query.limit(5))
    sample_items = [_item_to_sample(item) for item in sample_result.scalars().all()]

    if body.dry_run:
        return BatchUpdateResponse(
            updated_count=total,
            filter_used=body.filter.model_dump(exclude_none=True),
            fields_updated=body.updates,
            dry_run=True,
            sample=sample_items,
        )

    # Execute mode -- apply updates
    result = await db.execute(query)
    items = result.scalars().all()

    updated_ids = []
    for item in items:
        for field_name, value in body.updates.items():
            if field_name in ENUM_FIELDS:
                setattr(item, field_name, ENUM_FIELDS[field_name](value))
            else:
                setattr(item, field_name, value)
        updated_ids.append(item.id)

    await db.commit()
    await invalidate_catalog_cache()

    # Queue BIBFRAME sync for each updated record
    for item_id in updated_ids:
        background_tasks.add_task(_sync_bibframe_background, item_id)

    # Audit log
    audit_log_event(
        event_type="BATCH_CATALOG_UPDATE",
        user_id=current_user.id,
        email=current_user.email,
        severity="WARNING",
        details={
            "filter": body.filter.model_dump(exclude_none=True),
            "updates": body.updates,
            "affected_count": len(updated_ids),
            "affected_ids": updated_ids[:100],
        },
    )

    logger.info(
        "Batch catalog update by user %d: %d records, fields=%s",
        current_user.id,
        len(updated_ids),
        list(body.updates.keys()),
    )

    return BatchUpdateResponse(
        updated_count=len(updated_ids),
        filter_used=body.filter.model_dump(exclude_none=True),
        fields_updated=body.updates,
        dry_run=False,
        sample=sample_items,
    )


@router.get("/batch-update/preview", response_model=BatchUpdatePreviewResponse)
@limiter.limit("30/minute")
async def batch_update_preview(
    request: Request,
    item_type: Optional[str] = Query(None, description="Filter by item type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    location: Optional[str] = Query(None, description="Filter by location"),
    publisher: Optional[str] = Query(None, description="Filter by publisher (substring)"),
    subject: Optional[str] = Query(None, description="Filter by subject (substring)"),
    publication_year_min: Optional[int] = Query(None, description="Min publication year"),
    publication_year_max: Optional[int] = Query(None, description="Max publication year"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Preview which catalog records match a filter, without modifying anything.

    **Admin/Director only.**
    """
    fltr = BatchUpdateFilter(
        item_type=item_type,
        status=status,
        location=location,
        publisher=publisher,
        subject=subject,
        publication_year_min=publication_year_min,
        publication_year_max=publication_year_max,
    )

    query = _build_filter_query(fltr)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    sample_result = await db.execute(query.limit(5))
    sample_items = [_item_to_sample(item) for item in sample_result.scalars().all()]

    return BatchUpdatePreviewResponse(
        count=total,
        filter_used=fltr.model_dump(exclude_none=True),
        sample=sample_items,
    )
