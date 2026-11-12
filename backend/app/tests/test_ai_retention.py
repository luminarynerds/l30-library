# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Retention for the AI conversation + usage tables.

Patron chatbot transcripts and AI tool usage logs hold confidential,
identity-linked text. They must expire instead of accumulating forever.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.ai_agents import AgentConversation, LibraryAgent
from app.models.ai_guardrails import AIUsageLog
from app.services.data_retention_service import (
    cleanup_ai_usage_logs,
    cleanup_old_agent_conversations,
)


def _days_ago(n):
    return datetime.now(timezone.utc) - timedelta(days=n)


async def _make_agent(db):
    agent = LibraryAgent(
        name="Retention Test Agent",
        role="Tester",
        department="ref",
        bio="x",
        system_prompt="x",
    )
    db.add(agent)
    await db.flush()
    return agent


@pytest.mark.asyncio
async def test_old_agent_conversations_deleted_recent_kept(db):
    agent = await _make_agent(db)
    old = AgentConversation(agent_id=agent.id, session_id="s1", user_message="old q", agent_response="a", created_at=_days_ago(100))
    recent = AgentConversation(agent_id=agent.id, session_id="s2", user_message="new q", agent_response="a", created_at=_days_ago(5))
    db.add_all([old, recent])
    await db.flush()

    deleted = await cleanup_old_agent_conversations(db)
    assert deleted == 1

    rows = (await db.execute(select(AgentConversation))).scalars().all()
    assert [r.session_id for r in rows] == ["s2"]


@pytest.mark.asyncio
async def test_ai_usage_logs_scrubbed_then_deleted(db):
    very_old = AIUsageLog(prompt_preview="secret q1", response_preview="r1", system_prompt_used="sp", was_blocked=False, success=True, created_at=_days_ago(100))
    mid = AIUsageLog(prompt_preview="secret q2", response_preview="r2", system_prompt_used="sp", was_blocked=False, success=True, created_at=_days_ago(45))
    recent = AIUsageLog(prompt_preview="secret q3", response_preview="r3", system_prompt_used="sp", was_blocked=False, success=True, created_at=_days_ago(2))
    db.add_all([very_old, mid, recent])
    await db.flush()

    deleted = await cleanup_ai_usage_logs(db)
    assert deleted == 1  # only the 100-day row is hard-deleted

    rows = {r.created_at.date(): r for r in (await db.execute(select(AIUsageLog))).scalars().all()}
    assert len(rows) == 2  # mid + recent survive
    mid_row = rows[_days_ago(45).date()]
    assert mid_row.prompt_preview is None  # text scrubbed at 30 days
    assert mid_row.response_preview is None
    recent_row = rows[_days_ago(2).date()]
    assert recent_row.prompt_preview == "secret q3"  # recent text intact
