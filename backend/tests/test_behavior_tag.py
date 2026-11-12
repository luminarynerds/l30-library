# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for BehaviorTag model."""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acquisition_rationale import BehaviorTag


@pytest.mark.asyncio
async def test_behavior_tag_persists(test_db: AsyncSession):
    tag = BehaviorTag(slug='new_parent', label='New parent', category='life_stage')
    test_db.add(tag)
    await test_db.commit()
    result = await test_db.execute(
        select(BehaviorTag).where(BehaviorTag.slug == 'new_parent')
    )
    fetched = result.scalar_one()
    assert fetched.label == 'New parent'
    assert fetched.category == 'life_stage'
    assert fetched.active is True
    assert fetched.sort_order == 100


@pytest.mark.asyncio
async def test_behavior_tag_slug_unique(test_db: AsyncSession):
    """Two rows with the same slug should violate the UNIQUE constraint.

    Uses flush() rather than two separate commit() calls to stay on a single
    DB connection and avoid known pytest-asyncio cross-event-loop flakes
    with the postgres async pool.
    """
    test_db.add(BehaviorTag(slug='dup', label='A', category='x'))
    await test_db.flush()
    test_db.add(BehaviorTag(slug='dup', label='B', category='x'))
    try:
        with pytest.raises(IntegrityError):
            await test_db.flush()
    finally:
        await test_db.rollback()
