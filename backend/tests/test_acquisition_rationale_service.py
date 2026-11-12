# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for RationaleService."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acquisition_rationale import BehaviorTag
from app.models.catalog import CatalogItem
from app.models.user import User
from app.schemas.acquisition_rationale import (
    AcquisitionRationaleCreate,
    AcquisitionRationaleUpdate,
)
from app.services.acquisition_rationale_service import RationaleService


async def _seed_tag(test_db: AsyncSession, slug: str = 'new_parent') -> BehaviorTag:
    tag = BehaviorTag(
        slug=slug,
        label=slug.replace('_', ' ').title(),
        category='life_stage',
    )
    test_db.add(tag)
    await test_db.flush()
    return tag


async def _seed_item(test_db: AsyncSession, **overrides) -> CatalogItem:
    defaults = {'title': 'Test', 'author': 'A'}
    defaults.update(overrides)
    item = CatalogItem(**defaults)
    test_db.add(item)
    await test_db.flush()
    return item


async def _seed_user(test_db: AsyncSession, email: str = 'svc-test@example.com') -> User:
    user = User(email=email, first_name='Svc', last_name='Test')
    test_db.add(user)
    await test_db.flush()
    return user


@pytest.mark.asyncio
async def test_create_rationale(test_db: AsyncSession):
    await _seed_tag(test_db)
    item = await _seed_item(test_db)
    user = await _seed_user(test_db)
    svc = RationaleService(test_db)

    rat = await svc.create(
        item.id,
        user.id,
        AcquisitionRationaleCreate(
            signal_type='gap_in_collection',
            primary_use_case_slug='new_parent',
            weeding_condition='current_5yr',
        ),
    )
    assert rat.id is not None
    assert rat.catalog_item_id == item.id
    assert rat.created_by_id == user.id


@pytest.mark.asyncio
async def test_get_by_catalog_item_returns_rationale(test_db: AsyncSession):
    await _seed_tag(test_db)
    item = await _seed_item(test_db)
    svc = RationaleService(test_db)
    await svc.create(
        item.id,
        None,
        AcquisitionRationaleCreate(
            signal_type='other',
            primary_use_case_slug='new_parent',
            weeding_condition='current_5yr',
        ),
    )
    fetched = await svc.get_by_catalog_item(item.id)
    assert fetched is not None
    assert fetched.catalog_item_id == item.id


@pytest.mark.asyncio
async def test_get_by_catalog_item_returns_none_when_missing(test_db: AsyncSession):
    svc = RationaleService(test_db)
    assert await svc.get_by_catalog_item(99999999) is None


@pytest.mark.asyncio
async def test_update_rationale(test_db: AsyncSession):
    await _seed_tag(test_db, 'new_parent')
    await _seed_tag(test_db, 'grief_loss')
    item = await _seed_item(test_db)
    svc = RationaleService(test_db)
    await svc.create(
        item.id,
        None,
        AcquisitionRationaleCreate(
            signal_type='other',
            primary_use_case_slug='new_parent',
            weeding_condition='current_5yr',
        ),
    )
    updated = await svc.update(
        item.id,
        AcquisitionRationaleUpdate(
            signal_type='other',
            primary_use_case_slug='grief_loss',
            weeding_condition='foundational_indefinite',
            policy_clause='CDP-7.1',
        ),
    )
    assert updated is not None
    assert updated.primary_use_case_slug == 'grief_loss'
    assert updated.policy_clause == 'CDP-7.1'


@pytest.mark.asyncio
async def test_update_returns_none_when_missing(test_db: AsyncSession):
    svc = RationaleService(test_db)
    result = await svc.update(
        99999999,
        AcquisitionRationaleUpdate(
            signal_type='other',
            primary_use_case_slug='x',
            weeding_condition='current_5yr',
        ),
    )
    assert result is None


@pytest.mark.asyncio
async def test_list_missing_rationale_returns_only_unrationale_items(test_db: AsyncSession):
    await _seed_tag(test_db)
    item_with = await _seed_item(test_db, title='With rationale')
    item_without = await _seed_item(test_db, title='No rationale')
    svc = RationaleService(test_db)
    await svc.create(
        item_with.id,
        None,
        AcquisitionRationaleCreate(
            signal_type='other',
            primary_use_case_slug='new_parent',
            weeding_condition='current_5yr',
        ),
    )
    missing_ids = await svc.list_missing_rationale_items(limit=1000)
    assert item_without.id in missing_ids
    assert item_with.id not in missing_ids
