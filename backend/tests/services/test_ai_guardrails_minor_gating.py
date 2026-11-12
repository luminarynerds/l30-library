# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for minor / patron-type gating in the AI guardrails service."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ai_guardrails_service import (
    GuardrailResult,
    check_minor_access,
    check_prompt_guardrails,
)


def _guardrail(
    *,
    rule_type="blocked_topic",
    keywords=None,
    audience_minor="all",
    audience_patron_types=None,
    applies_to_tools=None,
    priority=0,
    rule_id=1,
):
    return SimpleNamespace(
        id=rule_id,
        enabled=True,
        rule_type=rule_type,
        rule_config={"keywords": keywords or [], "message": "blocked"},
        applies_to_tools=applies_to_tools or [],
        audience_minor=audience_minor,
        audience_patron_types=audience_patron_types or [],
        priority=priority,
    )


def _make_db(guardrails):
    """Build a mock AsyncSession.execute() that yields the given guardrails."""
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=guardrails)
    result = MagicMock()
    result.scalars = MagicMock(return_value=scalars)
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    return db


# ---------- check_minor_access ----------


def test_minor_access_allows_adult_when_block_for_minors():
    tool = SimpleNamespace(block_for_minors=True, requires_parental_consent=False, block_for_patron_types=[])
    user = SimpleNamespace(is_minor=False, patron_type="adult", parental_consent_given=False)
    allowed, reason = check_minor_access(tool, user)
    assert allowed is True
    assert reason is None


def test_minor_access_blocks_minor_on_minor_blocked_tool():
    tool = SimpleNamespace(block_for_minors=True, requires_parental_consent=False, block_for_patron_types=[])
    user = SimpleNamespace(is_minor=True, patron_type="child", parental_consent_given=False)
    allowed, reason = check_minor_access(tool, user)
    assert allowed is False
    assert "younger" in reason.lower()


def test_minor_access_blocks_anon_when_age_required():
    tool = SimpleNamespace(block_for_minors=True, requires_parental_consent=False, block_for_patron_types=[])
    allowed, reason = check_minor_access(tool, None)
    assert allowed is False
    assert "sign in" in reason.lower()


def test_minor_access_allows_anon_on_open_tool():
    tool = SimpleNamespace(block_for_minors=False, requires_parental_consent=False, block_for_patron_types=[])
    allowed, reason = check_minor_access(tool, None)
    assert allowed is True
    assert reason is None


def test_minor_access_blocks_patron_type():
    tool = SimpleNamespace(block_for_minors=False, requires_parental_consent=False, block_for_patron_types=["teen"])
    user = SimpleNamespace(is_minor=False, patron_type="teen", parental_consent_given=True)
    allowed, _ = check_minor_access(tool, user)
    assert allowed is False


def test_minor_access_requires_consent_for_minor_without_consent():
    tool = SimpleNamespace(block_for_minors=False, requires_parental_consent=True, block_for_patron_types=[])
    user = SimpleNamespace(is_minor=True, patron_type="child", parental_consent_given=False)
    allowed, reason = check_minor_access(tool, user)
    assert allowed is False
    assert "consent" in reason.lower()


def test_minor_access_consent_satisfied_allows_minor():
    tool = SimpleNamespace(block_for_minors=False, requires_parental_consent=True, block_for_patron_types=[])
    user = SimpleNamespace(is_minor=True, patron_type="child", parental_consent_given=True)
    allowed, _ = check_minor_access(tool, user)
    assert allowed is True


# ---------- check_prompt_guardrails audience filtering ----------


@pytest.mark.asyncio
async def test_prompt_guardrails_minors_only_rule_skipped_for_adult():
    rule = _guardrail(keywords=["scary"], audience_minor="minors_only")
    db = _make_db([rule])
    result = await check_prompt_guardrails(db, "tell me a scary story", is_minor=False)
    assert result.blocked is False


@pytest.mark.asyncio
async def test_prompt_guardrails_minors_only_rule_fires_for_minor():
    rule = _guardrail(keywords=["scary"], audience_minor="minors_only")
    db = _make_db([rule])
    result = await check_prompt_guardrails(db, "tell me a scary story", is_minor=True)
    assert result.blocked is True
    assert rule.id in result.triggered_ids


@pytest.mark.asyncio
async def test_prompt_guardrails_adults_only_rule_skipped_for_minor():
    rule = _guardrail(keywords=["wine"], audience_minor="adults_only")
    db = _make_db([rule])
    result = await check_prompt_guardrails(db, "recommend a wine", is_minor=True)
    assert result.blocked is False


@pytest.mark.asyncio
async def test_prompt_guardrails_patron_type_scope():
    rule = _guardrail(keywords=["dating"], audience_patron_types=["teen"])
    db = _make_db([rule])

    # patron_type matches -> blocks
    blocked = await check_prompt_guardrails(db, "dating tips", patron_type="teen")
    assert blocked.blocked is True

    # patron_type doesn't match -> allowed
    allowed = await check_prompt_guardrails(db, "dating tips", patron_type="adult")
    assert allowed.blocked is False


@pytest.mark.asyncio
async def test_prompt_guardrails_default_rule_applies_to_everyone():
    rule = _guardrail(keywords=["banned"])
    db = _make_db([rule])

    minor_result = await check_prompt_guardrails(db, "the banned word", is_minor=True)
    adult_result = await check_prompt_guardrails(db, "the banned word", is_minor=False)
    assert minor_result.blocked is True
    assert adult_result.blocked is True
