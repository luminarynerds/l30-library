# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for AcquisitionRationale model."""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.acquisition_rationale import (
    AcquisitionRationale,
    BehaviorTag,
    SignalType,
    WeedingCondition,
)
from app.models.catalog import CatalogItem
from app.models.user import User


async def _seed_tag(test_db: AsyncSession, slug: str = 'new_parent') -> BehaviorTag:
    tag = BehaviorTag(
        slug=slug,
        label=slug.replace('_', ' ').title(),
        category='life_stage',
    )
    test_db.add(tag)
    await test_db.flush()
    return tag


async def _seed_catalog_item(test_db: AsyncSession) -> CatalogItem:
    item = CatalogItem(title='Test Item')
    test_db.add(item)
    await test_db.flush()
    return item


async def _seed_user(test_db: AsyncSession) -> User:
    user = User(
        email='catalog-test@example.com',
        first_name='Test',
        last_name='User',
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest.mark.asyncio
async def test_create_rationale_with_required_fields(test_db: AsyncSession):
    await _seed_tag(test_db, 'new_parent')
    item = await _seed_catalog_item(test_db)
    user = await _seed_user(test_db)

    rat = AcquisitionRationale(
        catalog_item_id=item.id,
        created_by_id=user.id,
        signal_type=SignalType.GAP_IN_COLLECTION,
        primary_use_case_slug='new_parent',
        weeding_condition=WeedingCondition.CURRENT_5YR,
    )
    test_db.add(rat)
    await test_db.commit()

    fetched = await test_db.scalar(
        select(AcquisitionRationale)
        .where(AcquisitionRationale.catalog_item_id == item.id)
        .options(selectinload(AcquisitionRationale.catalog_item))
    )
    assert fetched is not None
    assert fetched.signal_type == SignalType.GAP_IN_COLLECTION
    assert fetched.primary_use_case_slug == 'new_parent'
    assert fetched.secondary_use_case_slugs == []
    assert fetched.anticipated_challenge_reasons == []
    assert fetched.anticipated_challenge_acknowledged is False
    assert fetched.patron_visible is False
    assert fetched.catalog_item.id == item.id


@pytest.mark.asyncio
async def test_one_rationale_per_catalog_item(test_db: AsyncSession):
    await _seed_tag(test_db, 'new_parent')
    item = await _seed_catalog_item(test_db)

    test_db.add(AcquisitionRationale(
        catalog_item_id=item.id,
        signal_type=SignalType.OTHER,
        primary_use_case_slug='new_parent',
        weeding_condition=WeedingCondition.CURRENT_5YR,
    ))
    await test_db.flush()
    test_db.add(AcquisitionRationale(
        catalog_item_id=item.id,
        signal_type=SignalType.OTHER,
        primary_use_case_slug='new_parent',
        weeding_condition=WeedingCondition.CURRENT_5YR,
    ))
    try:
        with pytest.raises(IntegrityError):
            await test_db.flush()
    finally:
        await test_db.rollback()
