# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.homepage_quote import HomepageQuote


async def list_active_for_locale(db: AsyncSession, locale: str) -> List[HomepageQuote]:
    result = await db.execute(
        select(HomepageQuote)
        .where(HomepageQuote.locale == locale)
        .where(HomepageQuote.is_active.is_(True))
        .order_by(HomepageQuote.display_order, HomepageQuote.id)
    )
    return list(result.scalars().all())


async def list_all(
    db: AsyncSession, locale: Optional[str] = None
) -> List[HomepageQuote]:
    query = select(HomepageQuote).order_by(
        HomepageQuote.locale, HomepageQuote.display_order, HomepageQuote.id
    )
    if locale:
        query = query.where(HomepageQuote.locale == locale)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, quote_id: int) -> Optional[HomepageQuote]:
    result = await db.execute(
        select(HomepageQuote).where(HomepageQuote.id == quote_id)
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    locale: str,
    quote_text: str,
    attribution: Optional[str],
    is_active: bool,
    display_order: int,
) -> HomepageQuote:
    quote = HomepageQuote(
        locale=locale,
        quote_text=quote_text,
        attribution=attribution,
        is_active=is_active,
        display_order=display_order,
    )
    db.add(quote)
    await db.commit()
    await db.refresh(quote)
    return quote


async def update(
    db: AsyncSession, quote: HomepageQuote, **fields
) -> HomepageQuote:
    for key, value in fields.items():
        if value is not None:
            setattr(quote, key, value)
    await db.commit()
    await db.refresh(quote)
    return quote


async def delete(db: AsyncSession, quote: HomepageQuote) -> None:
    await db.delete(quote)
    await db.commit()
