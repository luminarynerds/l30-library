# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test data cleanup endpoint.

Only available when TESTING_ENABLED=true env var is set.
Deletes all records tagged with a specific test run_id prefix.
"""

from app.core.logging import get_logger

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.catalog import CatalogItem
from ...models.circulation import Checkout, Hold
from ...models.event import Event
from ...models.event_registration import EventRegistration
from ...models.review import Review
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/test", tags=["testing"])


class CleanupRequest(BaseModel):
    run_id: str


class CleanupResponse(BaseModel):
    deleted: dict[str, int]


@router.delete("/cleanup", response_model=CleanupResponse)
async def cleanup_test_data(
    body: CleanupRequest,
    staff: None = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete all test data tagged with the given run_id.

    Records are identified by the prefix [TEST:{run_id}] in their
    title, pen_name, or notes field. Deletes in FK-dependency order.
    """
    prefix = f"[TEST:{body.run_id}]"
    deleted: dict[str, int] = {}

    # 1. Find test catalog items (needed to cascade checkouts/holds/reviews)
    cat_ids_q = select(CatalogItem.id).where(CatalogItem.title.startswith(prefix))
    cat_ids_result = await db.execute(cat_ids_q)
    cat_ids = [row[0] for row in cat_ids_result.all()]

    # 2. Find test events (needed to cascade registrations)
    event_ids_q = select(Event.id).where(Event.title.startswith(prefix))
    event_ids_result = await db.execute(event_ids_q)
    event_ids = [row[0] for row in event_ids_result.all()]

    # 3. Delete event registrations for test events
    if event_ids:
        result = await db.execute(
            delete(EventRegistration).where(
                EventRegistration.event_id.in_(event_ids)
            )
        )
        deleted["event_registrations"] = result.rowcount

    # 4. Delete reviews on test catalog items + reviews with test prefix
    if cat_ids:
        result = await db.execute(
            delete(Review).where(Review.catalog_item_id.in_(cat_ids))
        )
        deleted["reviews"] = result.rowcount
    # Also delete reviews by title prefix (patron reviews)
    result = await db.execute(
        delete(Review).where(Review.title.startswith(prefix))
    )
    deleted["reviews"] = deleted.get("reviews", 0) + result.rowcount

    # 5. Delete holds on test catalog items
    if cat_ids:
        result = await db.execute(
            delete(Hold).where(Hold.item_id.in_(cat_ids))
        )
        deleted["holds"] = result.rowcount

    # 6. Delete checkouts on test catalog items
    if cat_ids:
        result = await db.execute(
            delete(Checkout).where(Checkout.item_id.in_(cat_ids))
        )
        deleted["checkouts"] = result.rowcount

    # 9. Delete test events
    if event_ids:
        result = await db.execute(
            delete(Event).where(Event.id.in_(event_ids))
        )
        deleted["events"] = result.rowcount

    # 10. Delete test catalog items
    if cat_ids:
        result = await db.execute(
            delete(CatalogItem).where(CatalogItem.id.in_(cat_ids))
        )
        deleted["catalog_items"] = result.rowcount

    await db.commit()
    logger.info("Test cleanup for run_id=%s: %s", body.run_id, deleted)
    return CleanupResponse(deleted=deleted)
