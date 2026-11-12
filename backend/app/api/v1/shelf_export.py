# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shelf data export endpoint — CSV and JSON export of patron reading data."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.reading_goal import ReadingGoal
from ...models.reading_progress import ReadingProgress
from ...models.reading_status import ReadingStatus
from ...models.user import User
from ...utils.report_export import export_csv
from .auth import get_current_user

router = APIRouter(tags=["shelf-export"])


@router.get("/shelf-export")
async def export_shelf_data(
    format: str = Query("json", pattern="^(csv|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export all patron shelf data as CSV or JSON.

    Includes reading statuses (with catalog item title, author, ISBN),
    private notes, ratings, and reading goals.
    """
    # Fetch reading statuses with catalog items
    statuses_result = await db.execute(
        select(ReadingStatus)
        .options(selectinload(ReadingStatus.catalog_item))
        .where(ReadingStatus.user_id == current_user.id)
        .order_by(ReadingStatus.updated_at.desc())
    )
    statuses = statuses_result.scalars().all()

    # Fetch reading progress entries
    progress_result = await db.execute(
        select(ReadingProgress)
        .where(ReadingProgress.user_id == current_user.id)
        .order_by(ReadingProgress.catalog_item_id, ReadingProgress.logged_at.desc())
    )
    all_progress = progress_result.scalars().all()

    # Build progress map: catalog_item_id -> list of entries
    progress_map: dict[int, list] = {}
    for p in all_progress:
        progress_map.setdefault(p.catalog_item_id, []).append(p)

    # Fetch reading goals
    goals_result = await db.execute(
        select(ReadingGoal)
        .where(ReadingGoal.user_id == current_user.id)
        .order_by(ReadingGoal.year.desc())
    )
    goals = goals_result.scalars().all()

    def _iso(dt):
        return dt.isoformat() if dt else None

    # Build export data
    shelf_items = []
    for s in statuses:
        item = s.catalog_item
        latest_progress = progress_map.get(s.catalog_item_id, [None])[0]
        entry = {
            "title": item.title if item else "Unknown",
            "author": item.author if item else None,
            "isbn": getattr(item, "isbn", None),
            "item_type": item.item_type if item else None,
            "shelf_status": str(s.status),
            "started_at": _iso(s.started_at),
            "finished_at": _iso(s.finished_at),
            "private_notes": s.private_notes,
            "personal_tags": ",".join(s.personal_tags) if s.personal_tags else "",
            "current_page": latest_progress.current_page if latest_progress else None,
            "total_pages": latest_progress.total_pages if latest_progress else None,
            "percent": latest_progress.percent if latest_progress else None,
            "added_at": _iso(s.created_at),
            "updated_at": _iso(s.updated_at),
        }
        shelf_items.append(entry)

    goal_items = [
        {"year": g.year, "target_books": g.target_books}
        for g in goals
    ]

    if format == "csv":
        # CSV exports shelf items only (flat tabular data)
        content = export_csv(shelf_items, title="My Reading Shelf")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="reading_shelf_{timestamp}.csv"'
            },
        )

    # JSON format — full structured export with progress arrays
    json_shelf_items = []
    for s in statuses:
        item = s.catalog_item
        progress_entries = progress_map.get(s.catalog_item_id, [])
        json_shelf_items.append({
            "title": item.title if item else "Unknown",
            "author": item.author if item else None,
            "isbn": getattr(item, "isbn", None),
            "item_type": item.item_type if item else None,
            "shelf_status": str(s.status),
            "started_at": _iso(s.started_at),
            "finished_at": _iso(s.finished_at),
            "private_notes": s.private_notes,
            "personal_tags": list(s.personal_tags) if s.personal_tags else [],
            "progress": [
                {
                    "current_page": p.current_page,
                    "total_pages": p.total_pages,
                    "percent": p.percent,
                    "note": p.note,
                    "logged_at": _iso(p.logged_at),
                }
                for p in progress_entries
            ],
            "added_at": _iso(s.created_at),
            "updated_at": _iso(s.updated_at),
        })

    export_data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "patron_id": current_user.id,
        "shelf_items": json_shelf_items,
        "reading_goals": goal_items,
        "total_items": len(json_shelf_items),
    }
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return Response(
        content=json.dumps(export_data, indent=2, default=str),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="reading_shelf_{timestamp}.json"'
        },
    )
