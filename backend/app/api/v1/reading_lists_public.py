# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public reading lists browse and discovery API endpoints.

Allows patrons to discover, search, and browse public reading lists
created by other library patrons. Includes search, filtering, sorting,
and pagination functionality.
"""

from typing import List, Optional
from enum import StrEnum
from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.exceptions import InternalServerError
from ...core.error_codes import ErrorCode
from ...models.reading_list import ReadingList, ListItem
from ...models.user import User, name_search_clause
from ...models.social_sharing import ShareStatistics, ShareableResourceType

logger = get_logger(__name__)

router = APIRouter(prefix="/reading-lists", tags=["reading-lists-public"])


# Sort options for public reading lists
class SortBy(StrEnum):
    newest = "newest"
    most_popular = "most_popular"
    alphabetical = "alphabetical"
    most_shared = "most_shared"


class PublicReadingListPreview:

    def __init__(
        self,
        list_id: int,
        name: str,
        description: Optional[str],
        creator_name: str,
        creator_id: int,
        creator_avatar: Optional[str],
        item_count: int,
        share_count: int,
        created_at: str,
        rating: Optional[float],
        rating_count: int,
    ):
        self.id = list_id
        self.name = name
        self.description = description
        self.creator = {
            "id": creator_id,
            "name": creator_name,
            "avatar": creator_avatar,
        }
        self.item_count = item_count
        self.share_count = share_count
        self.created_at = created_at
        self.rating = rating
        self.rating_count = rating_count


@router.get("/public", response_model=dict)
async def browse_public_reading_lists(
    search: Optional[str] = Query(None, min_length=1, max_length=200, description="Search by list name, creator name, or keywords"),
    sort: SortBy = Query(SortBy.newest, description="Sort by newest, most_popular, alphabetical, or most_shared"),
    creator_id: Optional[int] = Query(None, description="Filter by creator ID"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=5, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Browse and search public reading lists.

    Query Parameters:
    - **search**: Search term for list name, creator name, or keywords (optional)
    - **sort**: Sort order - newest, most_popular, alphabetical, most_shared (default: newest)
    - **creator_id**: Filter by creator ID (optional)
    - **page**: Page number for pagination (default: 1)
    - **per_page**: Items per page, 5-100 (default: 20)

    Returns paginated public reading lists with:
    - List metadata (name, description)
    - Creator info (name, ID, avatar)
    - Item count
    - Share count and statistics
    - Created date
    - User ratings
    """
    try:
        # Build base query for public reading lists
        query = (
            select(
                ReadingList,
                # Names are encrypted; select columns (auto-decrypted) and
                # concat app-side instead of DB-concat of ciphertext.
                User.first_name,
                User.last_name,
                User.photo_url,
                func.count(ListItem.id).label("item_count"),
            )
            .select_from(ReadingList)
            .join(User, ReadingList.user_id == User.id)
            .outerjoin(ListItem, ReadingList.id == ListItem.list_id)
            .where(ReadingList.is_public == True)  # Only public lists
            .group_by(ReadingList.id, User.id)
        )

        # Apply search filters
        if search:
            search_term = f"%{search.lower()}%"
            # Name match via blind index (encrypted); list name/description stay substring.
            _name_clause = name_search_clause(search)
            _name_filters = [_name_clause] if _name_clause is not None else []
            query = query.where(
                or_(
                    func.lower(ReadingList.name).like(search_term),
                    func.lower(ReadingList.description).like(search_term),
                    *_name_filters,
                )
            )

        # Apply creator filter
        if creator_id:
            query = query.where(ReadingList.user_id == creator_id)

        # Apply sorting
        if sort == SortBy.newest:
            query = query.order_by(ReadingList.created_at.desc())
        elif sort == SortBy.most_popular:
            query = query.order_by(ReadingList.share_count.desc(), ReadingList.created_at.desc())
        elif sort == SortBy.alphabetical:
            query = query.order_by(ReadingList.name.asc())
        elif sort == SortBy.most_shared:
            query = query.order_by(ReadingList.share_count.desc())

        # Get total count before pagination
        count_query = select(func.count()).select_from(
            select(ReadingList.id)
            .select_from(ReadingList)
            .join(User, ReadingList.user_id == User.id)
            .where(ReadingList.is_public == True)
        )

        if search:
            _cname_clause = name_search_clause(search)
            _cname_filters = [_cname_clause] if _cname_clause is not None else []
            count_query = count_query.where(
                or_(
                    func.lower(ReadingList.name).like(f"%{search.lower()}%"),
                    func.lower(ReadingList.description).like(f"%{search.lower()}%"),
                    *_cname_filters,
                )
            )

        if creator_id:
            count_query = count_query.where(ReadingList.user_id == creator_id)

        total_count_result = await db.execute(count_query)
        total_count = total_count_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)

        # Execute query
        result = await db.execute(query)
        rows = result.fetchall()

        # Get list IDs for efficient share statistics lookup
        list_ids = [row[0].id for row in rows]

        # Fetch all share statistics in a single query (avoid N+1)
        share_stats_dict = {}
        if list_ids:
            share_stats_result = await db.execute(
                select(ShareStatistics).where(
                    and_(
                        ShareStatistics.resource_type == ShareableResourceType.reading_list,
                        ShareStatistics.resource_id.in_(list_ids),
                    )
                )
            )
            for stat in share_stats_result.scalars():
                share_stats_dict[stat.resource_id] = stat

        # Build response data
        lists = []
        for row in rows:
            reading_list = row[0]
            creator_name = f"{row[1] or ''} {row[2] or ''}".strip()
            creator_avatar = row[3]
            item_count = row[4] or 0

            # Get share statistics from dictionary (already loaded)
            share_stat = share_stats_dict.get(reading_list.id)

            list_preview = {
                "id": reading_list.id,
                "name": reading_list.name,
                "description": reading_list.description,
                "creator": {
                    "id": reading_list.user_id,
                    "name": creator_name,
                    "avatar": creator_avatar,
                },
                "item_count": item_count,
                "share_count": reading_list.share_count,
                "share_stats": {
                    "total_shares": share_stat.total_shares if share_stat else 0,
                    "facebook_shares": share_stat.facebook_shares if share_stat else 0,
                    "twitter_shares": share_stat.twitter_shares if share_stat else 0,
                    "email_shares": share_stat.email_shares if share_stat else 0,
                } if share_stat else None,
                "created_at": reading_list.created_at.isoformat() if reading_list.created_at else None,
                "updated_at": reading_list.updated_at.isoformat() if reading_list.updated_at else None,
            }
            lists.append(list_preview)

        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page

        return {
            "success": True,
            "data": lists,
            "pagination": {
                "total_count": total_count,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
            "filters": {
                "search": search,
                "sort": sort,
                "creator_id": creator_id,
            },
        }

    except Exception:
        logger.exception("Failed to fetch public reading lists")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.get("/public/search/creators")
async def search_creators(
    query: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Search for creators who have public reading lists.

    Used for the creator filter dropdown.
    """
    try:
        # Find users with public reading lists matching the query
        result = await db.execute(
            select(User.id, User.first_name, User.last_name, User.photo_url)
            .distinct()
            .join(ReadingList, User.id == ReadingList.user_id)
            .where(
                and_(
                    ReadingList.is_public == True,
                    name_search_clause(query) if name_search_clause(query) is not None else false(),
                )
            )
            .limit(limit)
        )

        creators = []
        for row in result:
            creators.append({
                "id": row[0],
                "name": f"{row[1] or ''} {row[2] or ''}".strip(),
                "avatar": row[3],
                "public_lists_count": await _get_creator_public_list_count(db, row[0]),
            })

        return {
            "success": True,
            "creators": creators,
            "count": len(creators),
        }

    except Exception:
        logger.exception("Failed to search creators")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.get("/public/{list_id}/preview")
async def get_public_list_preview(
    list_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get detailed preview of a public reading list.

    Shows all items in the list along with list metadata.
    Only works for public lists.
    """
    try:
        # Fetch the reading list with all items
        result = await db.execute(
            select(ReadingList)
            .options(
                selectinload(ReadingList.items).selectinload(ListItem.catalog_item),
                selectinload(ReadingList.user),
            )
            .where(
                and_(
                    ReadingList.id == list_id,
                    ReadingList.is_public == True,
                )
            )
        )

        reading_list = result.scalar_one_or_none()
        if not reading_list:
            raise HTTPException(
                status_code=404,
                detail="Public reading list not found",
            )

        # Get share statistics
        share_stats = await db.execute(
            select(ShareStatistics).where(
                and_(
                    ShareStatistics.resource_type == ShareableResourceType.reading_list,
                    ShareStatistics.resource_id == list_id,
                )
            )
        )
        share_stat = share_stats.scalar_one_or_none()

        # Build items list
        items = []
        for list_item in reading_list.items:
            if list_item.catalog_item:
                items.append({
                    "id": list_item.id,
                    "catalog_item_id": list_item.catalog_item_id,
                    "title": list_item.catalog_item.title,
                    "author": list_item.catalog_item.author,
                    "isbn": list_item.catalog_item.isbn,
                    "cover_image": list_item.catalog_item.cover_url,
                    "added_at": list_item.added_at.isoformat() if list_item.added_at else None,
                })

        return {
            "success": True,
            "list": {
                "id": reading_list.id,
                "name": reading_list.name,
                "description": reading_list.description,
                "creator": {
                    "id": reading_list.user.id,
                    "name": f"{reading_list.user.first_name} {reading_list.user.last_name}",
                    "avatar": reading_list.user.photo_url,
                },
                "item_count": len(items),
                "share_count": reading_list.share_count,
                "share_stats": {
                    "total_shares": share_stat.total_shares if share_stat else 0,
                    "facebook_shares": share_stat.facebook_shares if share_stat else 0,
                    "twitter_shares": share_stat.twitter_shares if share_stat else 0,
                    "email_shares": share_stat.email_shares if share_stat else 0,
                } if share_stat else None,
                "created_at": reading_list.created_at.isoformat() if reading_list.created_at else None,
                "updated_at": reading_list.updated_at.isoformat() if reading_list.updated_at else None,
                "items": items,
            },
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch public reading list preview")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.get("/public/stats/trending")
async def get_trending_lists(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get trending public reading lists based on recent shares.

    Parameters:
    - **limit**: Number of lists to return (default: 10, max: 50)
    - **days**: Time window in days for trending calculation (default: 30)
    """
    try:
        # Get most shared lists in the specified time period
        result = await db.execute(
            select(
                ReadingList,
                User.first_name,
                User.last_name,
                User.photo_url,
                func.count(ListItem.id).label("item_count"),
            )
            .select_from(ReadingList)
            .join(User, ReadingList.user_id == User.id)
            .outerjoin(ListItem, ReadingList.id == ListItem.list_id)
            .where(ReadingList.is_public == True)
            .group_by(ReadingList.id, User.id)
            .order_by(ReadingList.share_count.desc())
            .limit(limit)
        )

        trending = []
        for row in result:
            reading_list = row[0]
            creator_name = f"{row[1] or ''} {row[2] or ''}".strip()
            creator_avatar = row[3]
            item_count = row[4] or 0

            trending.append({
                "id": reading_list.id,
                "name": reading_list.name,
                "creator": {
                    "id": reading_list.user_id,
                    "name": creator_name,
                    "avatar": creator_avatar,
                },
                "item_count": item_count,
                "share_count": reading_list.share_count,
                "created_at": reading_list.created_at.isoformat() if reading_list.created_at else None,
            })

        return {
            "success": True,
            "trending": trending,
            "count": len(trending),
        }

    except Exception:
        logger.exception("Failed to fetch trending lists")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


async def _get_creator_public_list_count(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count(ReadingList.id)).where(
            and_(
                ReadingList.user_id == user_id,
                ReadingList.is_public == True,
            )
        )
    )
    return result.scalar() or 0
