# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_agents import AgentConversation
from app.models.catalog import CatalogItem
from app.models.purchase_request import PatronPurchaseRequest
from app.models.usage_statistics import ReferenceQuestion


@dataclass
class SignalCandidate:

    table_name: str
    record_id: int
    summary: str
    matched_on: str


class SignalLinkService:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_candidates_for_item(
        self, catalog_item_id: int, limit: int = 10,
    ) -> list[SignalCandidate]:
        item = await self.session.get(CatalogItem, catalog_item_id)
        if item is None:
            return []
        candidates: list[SignalCandidate] = []

        # 1. Purchase requests: ISBN or title match.
        if item.title or item.isbn:
            conds = []
            if item.isbn:
                conds.append(PatronPurchaseRequest.isbn == item.isbn)
            if item.title:
                conds.append(PatronPurchaseRequest.title.ilike(f'%{item.title}%'))
            if conds:
                rows = (await self.session.execute(
                    select(PatronPurchaseRequest).where(or_(*conds)).limit(limit)
                )).scalars().all()
                for r in rows:
                    matched_on = 'isbn' if (item.isbn and r.isbn == item.isbn) else 'title'
                    candidates.append(SignalCandidate(
                        table_name='patron_purchase_requests',
                        record_id=r.id,
                        summary=f'{r.title} (status={r.status})',
                        matched_on=matched_on,
                    ))

        # 2. Reference questions: subject overlap. catalog_items.subjects is
        # free-text, comma/semicolon-delimited (and prod has a few {a,b,c}
        # array-literal stragglers). Pick the first non-empty token.
        if item.subjects:
            first = item.subjects.replace(';', ',').split(',')[0]
            first = first.strip().strip('{').strip('}').strip('"').lower()
            if first:
                rows = (await self.session.execute(
                    select(ReferenceQuestion).where(
                        or_(
                            ReferenceQuestion.subject_area.ilike(f'%{first}%'),
                            ReferenceQuestion.notes.ilike(f'%{first}%'),
                        )
                    ).limit(limit)
                )).scalars().all()
                for r in rows:
                    snippet = (r.notes or '')[:60]
                    candidates.append(SignalCandidate(
                        table_name='reference_questions',
                        record_id=r.id,
                        summary=f'{r.subject_area or "?"}: {snippet}',
                        matched_on='subject',
                    ))

        # 3. Agent conversations: first word of title (>=4 chars) appears in
        # user_message. Coarse, but useful as a discovery hint.
        if item.title:
            tokens = item.title.split()
            first_word = tokens[0].lower() if tokens else ''
            if len(first_word) >= 4:
                rows = (await self.session.execute(
                    select(AgentConversation).where(
                        AgentConversation.user_message.ilike(f'%{first_word}%')
                    ).limit(limit)
                )).scalars().all()
                for r in rows:
                    candidates.append(SignalCandidate(
                        table_name='agent_conversations',
                        record_id=r.id,
                        summary=(r.user_message or '')[:80],
                        matched_on='user_message',
                    ))

        return candidates[:limit]

    async def resolve(
        self, table_name: str, record_id: int,
    ) -> Optional[dict[str, Any]]:
        if table_name == 'reference_questions':
            r = await self.session.get(ReferenceQuestion, record_id)
            if not r:
                return None
            return {
                'table': 'reference_questions',
                'id': r.id,
                'asked_at_month': r.asked_at.strftime('%Y-%m') if r.asked_at else None,
                'subject_area': r.subject_area,
                'question_type': r.question_type,
                'patron_type': r.patron_type,
                'notes': (r.notes or '')[:200],
            }
        if table_name == 'patron_purchase_requests':
            r = await self.session.get(PatronPurchaseRequest, record_id)
            if not r:
                return None
            return {
                'table': 'patron_purchase_requests',
                'id': r.id,
                'title': r.title,
                'author': r.author,
                'status': r.status,
            }
        if table_name == 'agent_conversations':
            r = await self.session.get(AgentConversation, record_id)
            if not r:
                return None
            return {
                'table': 'agent_conversations',
                'id': r.id,
                'detected_intent': r.detected_intent,
                'user_message': (r.user_message or '')[:200],
            }
        return None
