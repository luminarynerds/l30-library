# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Any, TypeVar, Generic

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

logger = get_logger(__name__)

T = TypeVar("T", bound=DeclarativeBase)


class BaseMakerspaceService(Generic[T]):

    model: type[T]

    @classmethod
    async def get_all_paginated(
        cls,
        db: AsyncSession,
        *,
        filters: list | None = None,
        order_by: Any | None = None,
        page: int = 1,
        per_page: int = 20,
        options: list | None = None,
    ) -> tuple[list[T], int]:
        query = select(cls.model)
        count_query = select(func.count(cls.model.id))

        if filters:
            for f in filters:
                query = query.where(f)
                count_query = count_query.where(f)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)

        if order_by is not None:
            query = query.order_by(order_by)

        if options:
            for opt in options:
                query = query.options(opt)

        result = await db.execute(query)
        records = list(result.scalars().all())

        return records, total

    @classmethod
    async def get_by_id(
        cls,
        db: AsyncSession,
        record_id: int,
        options: list | None = None,
    ) -> T | None:
        query = select(cls.model).where(cls.model.id == record_id)

        if options:
            for opt in options:
                query = query.options(opt)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def create(
        cls,
        db: AsyncSession,
        data: dict,
        **extra_fields: Any,
    ) -> T:
        record = cls.model(**data, **extra_fields)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @classmethod
    async def update(
        cls,
        db: AsyncSession,
        record: T,
        data: dict,
    ) -> T:
        for key, value in data.items():
            if value is not None:
                setattr(record, key, value)
        await db.commit()
        await db.refresh(record)
        return record

    @classmethod
    async def delete(
        cls,
        db: AsyncSession,
        record: T,
    ) -> None:
        await db.delete(record)
        await db.commit()
