# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for SignalLinkService."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem
from app.models.purchase_request import PatronPurchaseRequest
from app.models.usage_statistics import ReferenceQuestion
from app.models.user import User
from app.services.signal_link_service import SignalLinkService


async def _seed_user(test_db: AsyncSession, email: str = 'signal-test@example.com') -> User:
    user = User(email=email, first_name='Signal', last_name='Test')
    test_db.add(user)
    await test_db.flush()
    return user


@pytest.mark.asyncio
async def test_search_candidates_matches_purchase_request_by_title(test_db: AsyncSession):
    item = CatalogItem(title='Specific Title XYZ Unique', author='A')
    test_db.add(item)
    await test_db.flush()

    patron = await _seed_user(test_db, email='patron-pr@example.com')
    pr = PatronPurchaseRequest(
        title='Specific Title XYZ Unique',
        patron_id=patron.id,
        material_type='book',
        status='pending',
    )
    test_db.add(pr)
    await test_db.flush()

    svc = SignalLinkService(test_db)
    candidates = await svc.search_candidates_for_item(item.id, limit=10)
    assert any(c.table_name == 'patron_purchase_requests' for c in candidates)


@pytest.mark.asyncio
async def test_resolve_reference_question_returns_summary(test_db: AsyncSession):
    rq = ReferenceQuestion(
        was_referred=False,
        subject_area='cooking',
        notes='Asking about canning',
        question_type='reference',
        contact_method='in_person',
    )
    test_db.add(rq)
    await test_db.flush()

    svc = SignalLinkService(test_db)
    resolved = await svc.resolve('reference_questions', rq.id)
    assert resolved is not None
    assert resolved['table'] == 'reference_questions'
    assert resolved['subject_area'] == 'cooking'
    assert 'canning' in resolved['notes']


@pytest.mark.asyncio
async def test_resolve_unknown_table_returns_none(test_db: AsyncSession):
    svc = SignalLinkService(test_db)
    assert await svc.resolve('unknown_table', 1) is None
