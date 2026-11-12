# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Joy Capture API"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ...core.database import get_db
from .dependencies import require_staff, require_admin, get_current_user
from ...models.joy_capture import (
    BrightSpot,
    JoyJarEntry,
    JoyMomentType,
    JoyVisibility,
    MoodType,
    PatronThankYou,
)
from ...models.user import User

router = APIRouter()

@router.post("/staff/bright-spots")
async def log_bright_spot(
    description: str,
    mood: MoodType = MoodType.DELIGHTFUL,
    visibility: JoyVisibility = JoyVisibility.TEAM,
    is_featured: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    spot = BrightSpot(
        organization_id=(current_user.home_library_system_id or 1),
        user_id=current_user.id,
        description=description,
        moment_type=JoyMomentType.BRIGHT_SPOT,
        mood=mood,
        visibility=visibility,
        is_featured=is_featured,
    )
    db.add(spot)
    await db.commit()
    return {"message": "Bright spot captured!"}

@router.post("/staff/patron-thank-yous")
async def log_thank_you(
    message: str,
    patron_name: str = None,
    can_share: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    thank_you = PatronThankYou(
        organization_id=(current_user.home_library_system_id or 1),
        staff_id=current_user.id,
        patron_name=patron_name,
        message=message,
        can_share=can_share,
    )
    db.add(thank_you)
    await db.commit()
    return {"message": "Thank you archived!"}

@router.post("/staff/joy-jar")
async def add_joy_jar_entry(
    entry_text: str,
    is_anonymous: bool = False,
    mood: MoodType = MoodType.GRATEFUL,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    entry = JoyJarEntry(
        organization_id=(current_user.home_library_system_id or 1),
        user_id=None if is_anonymous else current_user.id,
        entry_text=entry_text,
        is_anonymous=is_anonymous,
        mood=mood,
    )
    db.add(entry)
    await db.commit()
    return {"message": "Joy captured!"}


@router.post("/staff/funny-moments")
async def share_funny_moment(
    description: str,
    visibility: JoyVisibility = JoyVisibility.TEAM,
    is_featured: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    moment = BrightSpot(
        organization_id=(current_user.home_library_system_id or 1),
        user_id=current_user.id,
        description=description,
        moment_type=JoyMomentType.FUNNY_MOMENT,
        mood=MoodType.FUNNY,
        visibility=visibility,
        is_featured=is_featured,
    )
    db.add(moment)
    await db.commit()
    return {"message": "Funny moment shared!"}


@router.post("/staff/kid-drawings")
async def save_kid_drawing(
    description: str,
    artist_name: str | None = None,
    drawing_url: str | None = None,
    visibility: JoyVisibility = JoyVisibility.ORGANIZATION,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    drawing = BrightSpot(
        organization_id=(current_user.home_library_system_id or 1),
        user_id=current_user.id,
        description=description,
        moment_type=JoyMomentType.KID_DRAWING,
        mood=MoodType.HEARTWARMING,
        visibility=visibility,
        metadata_json={"artist_name": artist_name, "drawing_url": drawing_url},
    )
    db.add(drawing)
    await db.commit()
    return {"message": "Kid drawing saved to the collection!"}


@router.post("/staff/community-love-letters")
async def archive_community_love_letter(
    message: str,
    sender_name: str | None = None,
    visibility: JoyVisibility = JoyVisibility.ORGANIZATION,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    letter = BrightSpot(
        organization_id=(current_user.home_library_system_id or 1),
        user_id=current_user.id,
        description=message,
        moment_type=JoyMomentType.COMMUNITY_LOVE_LETTER,
        mood=MoodType.GRATEFUL,
        visibility=visibility,
        metadata_json={"sender_name": sender_name},
    )
    db.add(letter)
    await db.commit()
    return {"message": "Community love letter archived!"}


@router.post("/staff/memory-book")
async def add_memory_book_entry(
    memory: str,
    happened_on: date | None = None,
    visibility: JoyVisibility = JoyVisibility.ORGANIZATION,
    is_featured: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    entry = BrightSpot(
        organization_id=(current_user.home_library_system_id or 1),
        user_id=current_user.id,
        description=memory,
        moment_type=JoyMomentType.STAFF_MEMORY,
        mood=MoodType.INSPIRING,
        visibility=visibility,
        is_featured=is_featured,
        metadata_json={"happened_on": happened_on.isoformat() if happened_on else None},
    )
    db.add(entry)
    await db.commit()
    return {"message": "Staff memory added to the book!"}

@router.get("/staff/bright-spots")
async def get_bright_spots(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    result = await db.execute(
        select(BrightSpot).where(BrightSpot.organization_id == (current_user.home_library_system_id or 1)).order_by(BrightSpot.created_at.desc()).limit(20)
    )
    spots = result.scalars().all()
    return {
        "bright_spots": [
            {
                "id": s.id,
                "description": s.description,
                "moment_type": s.moment_type,
                "mood": s.mood,
                "visibility": s.visibility,
                "is_featured": s.is_featured,
                "metadata": s.metadata_json,
                "created_at": s.created_at.isoformat(),
            }
            for s in spots
        ]
    }


@router.get("/staff/favorite-moment-anniversaries")
async def get_favorite_moment_anniversaries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    today = date.today()
    result = await db.execute(
        select(BrightSpot)
        .where(BrightSpot.organization_id == (current_user.home_library_system_id or 1))
        .where(BrightSpot.is_featured.is_(True))
        .where(extract("month", BrightSpot.created_at) == today.month)
        .where(extract("day", BrightSpot.created_at) == today.day)
        .order_by(BrightSpot.created_at.asc())
    )
    moments = result.scalars().all()
    return {
        "anniversary_date": today.isoformat(),
        "favorite_moments": [
            {
                "id": moment.id,
                "description": moment.description,
                "moment_type": moment.moment_type,
                "years_ago": today.year - moment.created_at.date().year,
                "created_at": moment.created_at.isoformat(),
            }
            for moment in moments
        ],
    }


@router.get("/staff/end-of-year-joy-review")
async def get_end_of_year_joy_review(
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    base_query = select(BrightSpot).where(
        BrightSpot.organization_id == (current_user.home_library_system_id or 1),
        extract("year", BrightSpot.created_at) == year,
    )
    total_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    by_type_result = await db.execute(
        select(BrightSpot.moment_type, func.count(BrightSpot.id))
        .where(
            BrightSpot.organization_id == (current_user.home_library_system_id or 1),
            extract("year", BrightSpot.created_at) == year,
        )
        .group_by(BrightSpot.moment_type)
        .order_by(func.count(BrightSpot.id).desc())
    )
    by_mood_result = await db.execute(
        select(BrightSpot.mood, func.count(BrightSpot.id))
        .where(
            BrightSpot.organization_id == (current_user.home_library_system_id or 1),
            extract("year", BrightSpot.created_at) == year,
        )
        .group_by(BrightSpot.mood)
        .order_by(func.count(BrightSpot.id).desc())
    )
    featured_result = await db.execute(
        select(BrightSpot)
        .where(
            BrightSpot.organization_id == (current_user.home_library_system_id or 1),
            extract("year", BrightSpot.created_at) == year,
            BrightSpot.is_featured.is_(True),
        )
        .order_by(BrightSpot.created_at.desc())
        .limit(10)
    )

    return {
        "year": year,
        "headline": "Capture the moments that make it worth it.",
        "total_moments": total_result.scalar() or 0,
        "moments_by_type": [
            {"moment_type": moment_type, "count": count}
            for moment_type, count in by_type_result.all()
        ],
        "moments_by_mood": [
            {"mood": mood, "count": count}
            for mood, count in by_mood_result.all()
        ],
        "featured_highlights": [
            {
                "id": m.id,
                "description": m.description,
                "moment_type": m.moment_type,
                "created_at": m.created_at.isoformat(),
            }
            for m in featured_result.scalars().all()
        ],
    }
