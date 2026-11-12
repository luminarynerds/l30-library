# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Type, TypeVar

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

T = TypeVar("T")


async def get_or_404(
    db: AsyncSession,
    model: Type[T],
    id: object,
    error_msg: str = "Resource not found",
) -> T:
    obj = await db.get(model, id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_msg,
        )
    return obj


def get_or_404_sync(
    db: Session,
    model: Type[T],
    id: object,
    error_msg: str = "Resource not found",
) -> T:
    obj = db.get(model, id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_msg,
        )
    return obj
