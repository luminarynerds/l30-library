# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.rate_limit import limiter
from ....models.circulation import Checkout
from ....models.favorite import Favorite
from ....models.reading_list import ListItem, ReadingList
from ....models.reading_status import ReadingStatus, ShelfStatus
from ....models.review import Review
from ....models.user import User
from ..auth import get_current_user

logger = get_logger(__name__)
router = APIRouter()

class ActivityEvent(BaseModel):
    type: str
    date: str
    detail: str


class MyActivityResponse(BaseModel):
    events: List[ActivityEvent]


SHELF_LABELS = {
    ShelfStatus.want_to_read: "Want to Read",
    ShelfStatus.currently_reading: "Currently Reading",
    ShelfStatus.on_hold: "On Hold",
    ShelfStatus.finished: "Finished",
    ShelfStatus.did_not_finish: "Did Not Finish",
}


def _fmt(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    return dt.date().isoformat()


@router.get("/items/{item_id}/my-activity", response_model=MyActivityResponse)
@limiter.limit("60/minute")
async def get_my_activity(
    request: Request,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    events: list[ActivityEvent] = []

    # Checkouts
    checkouts = (
        await db.execute(
            select(Checkout)
            .where(Checkout.user_id == current_user.id, Checkout.item_id == item_id)
            .order_by(Checkout.checked_out_at.desc())
        )
    ).scalars().all()

    for co in checkouts:
        events.append(ActivityEvent(
            type="checkout",
            date=_fmt(co.checked_out_at),
            detail="Checked out",
        ))
        if co.returned_at:
            events.append(ActivityEvent(
                type="return",
                date=_fmt(co.returned_at),
                detail="Returned",
            ))

    # Reading status
    rs = (
        await db.execute(
            select(ReadingStatus).where(
                ReadingStatus.user_id == current_user.id,
                ReadingStatus.catalog_item_id == item_id,
            )
        )
    ).scalar_one_or_none()

    if rs:
        label = SHELF_LABELS.get(rs.status, str(rs.status))
        events.append(ActivityEvent(
            type="shelf",
            date=_fmt(rs.updated_at),
            detail=f"Marked as {label}",
        ))

    # Review / rating
    review = (
        await db.execute(
            select(Review).where(
                Review.user_id == current_user.id,
                Review.catalog_item_id == item_id,
            )
        )
    ).scalar_one_or_none()

    if review and review.rating:
        stars = "star" if review.rating == 1 else "stars"
        events.append(ActivityEvent(
            type="rated",
            date=_fmt(review.created_at),
            detail=f"Rated {review.rating} {stars}",
        ))

    # Favorites
    fav = (
        await db.execute(
            select(Favorite).where(
                Favorite.user_id == current_user.id,
                Favorite.catalog_item_id == item_id,
            )
        )
    ).scalar_one_or_none()

    if fav:
        events.append(ActivityEvent(
            type="favorite",
            date=_fmt(fav.created_at),
            detail="Added to favorites",
        ))

    # Reading list additions
    list_items = (
        await db.execute(
            select(ListItem, ReadingList.name)
            .join(ReadingList, ListItem.list_id == ReadingList.id)
            .where(
                ReadingList.user_id == current_user.id,
                ListItem.catalog_item_id == item_id,
            )
        )
    ).all()

    for li, list_name in list_items:
        events.append(ActivityEvent(
            type="list",
            date=_fmt(li.added_at),
            detail=f'Added to list "{list_name}"',
        ))

    # Sort descending by date
    events.sort(key=lambda e: e.date, reverse=True)

    return MyActivityResponse(events=events)
