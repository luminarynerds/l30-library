# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for guardrail enforcement in the patron-facing chat_with_agent route.

Mirrors tests/unit/test_library_agents_mode.py conventions (bare async def under
asyncio_mode=auto, no explicit markers). Guardrail functions are locally imported
inside chat_with_agent from app.services.ai_guardrails_service, so they must be
patched at that source module, not on app.api.v1.library_agents.
"""

import os
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from starlette.requests import Request

from app.models.ai_agents import LibraryAgent
from app.models.ai_guardrails import AIUsageLimit, AIUsageLog
from app.models.user import UserRole
from app.services.ai_guardrails_service import GuardrailResult


def make_agent():
    agent = MagicMock()
    agent.id = 1
    agent.name = "Marlene"
    agent.role = "genealogy"
    agent.department = "shared"
    agent.bio = "Loves local history."
    agent.personality = "friendly"
    agent.tone = "warm"
    agent.specialties = []
    agent.can_help_with = []
    agent.greeting_message = None
    agent.is_active = True
    # check_minor_access() is now unconditionally wired into chat_with_agent, so
    # every test's agent needs these explicitly False/empty -- otherwise a
    # MagicMock auto-attribute (truthy by default) would make block_for_minors
    # look "on" and block every one of these unrelated tests.
    agent.block_for_minors = False
    agent.requires_parental_consent = False
    agent.block_for_patron_types = []
    return agent


def _request(headers=None) -> Request:
    """A real Starlette Request (not a MagicMock) so client_ip() -- now called
    unconditionally by chat_with_agent -- resolves a real string instead of an
    auto-generated MagicMock attribute."""
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "headers": raw, "client": ("203.0.113.1", 12345)})


def make_db_mock(agent, configured_model=None):
    """AsyncMock db: first execute() returns the agent lookup; a second
    returns the "agent_chat" AIConfiguration lookup chat_with_agent now runs
    for the model-allowlist guardrail (None = no admin override configured,
    the common case in these tests). None of these tests send a session_id,
    so the conversation-history lookup branch is never entered."""
    db = AsyncMock()

    agent_result = MagicMock()
    agent_result.scalar_one_or_none.return_value = agent

    agent_chat_config_result = MagicMock()
    if configured_model is None:
        agent_chat_config_result.scalar_one_or_none.return_value = None
    else:
        config_row = MagicMock()
        config_row.config_value = {"model": configured_model}
        agent_chat_config_result.scalar_one_or_none.return_value = config_row

    db.execute.side_effect = [agent_result, agent_chat_config_result]

    async def fake_refresh(obj):
        obj.id = 42

    db.refresh.side_effect = fake_refresh
    return db


def make_patron():
    user = MagicMock()
    user.id = 7
    user.role = UserRole.PATRON
    user.is_minor = False
    user.patron_type = "adult"
    return user


class TestGuardrailEnforcement:
    async def test_blocked_prompt_is_blocked_and_model_not_called(self):
        agent = make_agent()
        db = make_db_mock(agent)

        blocked_result = GuardrailResult()
        blocked_result.blocked = True
        blocked_result.block_reason = "That topic is not available."

        with (
            patch(
                "app.api.v1.library_agents._check_anonymous_usage_limit",
                new=AsyncMock(return_value=(True, None)),
            ),
            patch(
                "app.services.ai_guardrails_service.check_prompt_guardrails",
                new=AsyncMock(return_value=blocked_result),
            ),
            patch(
                "app.api.v1.library_agents.generate_agent_response", new=AsyncMock()
            ) as mock_generate,
        ):
            from app.api.v1.library_agents import MessageRequest, chat_with_agent

            msg_req = MessageRequest(message="tell me something dangerous")
            response = await chat_with_agent(
                agent_id=1, message_req=msg_req, request=_request(), db=db, current_user=None
            )

        mock_generate.assert_not_called()
        assert response.response == "That topic is not available."
        assert response.mode == "rule_based"
        # Guardrail hit must be visible in the audit log, not just enforced silently.
        logged = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], AIUsageLog)]
        assert len(logged) == 1
        assert logged[0].was_blocked is True
        assert logged[0].block_reason == "That topic is not available."

    async def test_usage_limit_exceeded_blocks_authenticated_patron(self):
        agent = make_agent()
        db = make_db_mock(agent)
        user = make_patron()
        reason = "Hourly AI usage limit reached (10 requests/hour). Please try again later."

        with (
            patch(
                "app.services.ai_guardrails_service.check_usage_limits",
                new=AsyncMock(return_value=(False, reason)),
            ),
            patch(
                "app.services.ai_guardrails_service.check_prompt_guardrails",
                new=AsyncMock(side_effect=AssertionError("must short-circuit before prompt check")),
            ),
            patch(
                "app.api.v1.library_agents.generate_agent_response", new=AsyncMock()
            ) as mock_generate,
        ):
            from app.api.v1.library_agents import MessageRequest, chat_with_agent

            msg_req = MessageRequest(message="what are your hours")
            response = await chat_with_agent(
                agent_id=1, message_req=msg_req, request=_request(), db=db, current_user=user
            )

        mock_generate.assert_not_called()
        assert response.response == reason
        assert response.mode == "rule_based"
        logged = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], AIUsageLog)]
        assert len(logged) == 1
        assert logged[0].was_blocked is True
        # Patron chat rows never carry user_id, even for a signed-in patron --
        # see TestMinorGatingRealRows.test_patron_chat_log_row_has_no_prompt_preview_or_user_id.
        assert logged[0].user_id is None

    async def test_anonymous_patron_chat_applies_child_rate_usage_limit(self):
        """Unknown age is treated as a minor: anonymous callers must still be
        rate-limited at the "child" rate -- not exempted -- but never through
        the DB-backed, user_id-keyed check_usage_limits (there is no user_id
        to key on, and privacy rules forbid inventing one). Real end-to-end
        coverage of _check_anonymous_usage_limit's slowapi-based mechanism is
        in TestMinorGatingRealRows."""
        agent = make_agent()
        db = make_db_mock(agent)

        with (
            patch(
                "app.services.ai_guardrails_service.check_usage_limits",
                new=AsyncMock(
                    side_effect=AssertionError("anonymous must not hit the DB-backed check")
                ),
            ),
            patch(
                "app.api.v1.library_agents._check_anonymous_usage_limit",
                new=AsyncMock(return_value=(True, None)),
            ) as mock_anon_usage,
            patch(
                "app.services.ai_guardrails_service.check_prompt_guardrails",
                new=AsyncMock(return_value=GuardrailResult()),
            ),
            patch(
                "app.api.v1.library_agents.generate_agent_response",
                new=AsyncMock(return_value=("We open at nine.", "hours_question", "rule_based")),
            ),
        ):
            from app.api.v1.library_agents import MessageRequest, chat_with_agent

            msg_req = MessageRequest(message="what time do you open")
            response = await chat_with_agent(
                agent_id=1, message_req=msg_req, request=_request(), db=db, current_user=None
            )

        mock_anon_usage.assert_called_once()
        assert mock_anon_usage.call_args.args[0] is db
        assert response.response == "We open at nine."
        assert response.conversation_id == 42

    async def test_prompt_guardrail_check_exception_fails_open_and_is_audited(self):
        """A DB hiccup in the guardrail check must not take the whole chat down --
        but the audit row must record that the check did NOT run, distinct from
        a genuinely clean pass (which would have error_message=None)."""
        agent = make_agent()
        db = make_db_mock(agent)

        with (
            patch(
                "app.api.v1.library_agents._check_anonymous_usage_limit",
                new=AsyncMock(return_value=(True, None)),
            ),
            patch(
                "app.services.ai_guardrails_service.check_prompt_guardrails",
                new=AsyncMock(side_effect=SQLAlchemyError("ai_guardrails table unavailable")),
            ),
            patch(
                "app.api.v1.library_agents.generate_agent_response",
                new=AsyncMock(return_value=("Here to help!", "general_inquiry", "rule_based")),
            ) as mock_generate,
        ):
            from app.api.v1.library_agents import MessageRequest, chat_with_agent

            msg_req = MessageRequest(message="hello")
            response = await chat_with_agent(
                agent_id=1, message_req=msg_req, request=_request(), db=db, current_user=None
            )

        mock_generate.assert_called_once()
        assert response.response == "Here to help!"

        logged = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], AIUsageLog)]
        assert len(logged) == 1
        # The chat itself succeeded (patron got a reply) -- but the row must not
        # look like a clean, checked pass.
        assert logged[0].success is True
        assert logged[0].was_blocked is False
        assert logged[0].error_message is not None
        assert "prompt guardrail check did not run" in logged[0].error_message

    async def test_response_guardrails_applied_to_generated_reply(self):
        trimmed = GuardrailResult()
        trimmed.max_response_length = 10
        agent = make_agent()
        db = make_db_mock(agent)

        with (
            patch(
                "app.api.v1.library_agents._check_anonymous_usage_limit",
                new=AsyncMock(return_value=(True, None)),
            ),
            patch(
                "app.services.ai_guardrails_service.check_prompt_guardrails",
                new=AsyncMock(return_value=trimmed),
            ),
            patch(
                "app.api.v1.library_agents.generate_agent_response",
                new=AsyncMock(
                    return_value=(
                        "This is a much longer reply than allowed.",
                        "general_inquiry",
                        "llm",
                    )
                ),
            ),
        ):
            from app.api.v1.library_agents import MessageRequest, chat_with_agent

            msg_req = MessageRequest(message="tell me a long story")
            response = await chat_with_agent(
                agent_id=1, message_req=msg_req, request=_request(), db=db, current_user=None
            )

        assert response.response == "This is a ..."
        assert response.mode == "llm"

    async def test_minor_access_check_now_wired_blocks_minor(self):
        """check_minor_access is now wired into chat_with_agent (LibraryAgent
        got real block_for_minors / requires_parental_consent /
        block_for_patron_types columns -- see the library_agent_minor_gating_001
        migration), so a minor hitting a block_for_minors agent must be
        refused before generate_agent_response ever runs. Real-row coverage of
        the block/allow behavior itself lives in TestMinorGatingRealRows."""
        agent = make_agent()
        agent.block_for_minors = True
        db = make_db_mock(agent)
        minor = MagicMock()
        minor.id = 9
        minor.role = UserRole.CHILD
        minor.is_minor = True
        minor.patron_type = "child"

        with (
            patch(
                "app.api.v1.library_agents.generate_agent_response", new=AsyncMock()
            ) as mock_generate,
        ):
            from app.api.v1.library_agents import MessageRequest, chat_with_agent

            msg_req = MessageRequest(message="hi")
            response = await chat_with_agent(
                agent_id=1, message_req=msg_req, request=_request(), db=db, current_user=minor
            )

        mock_generate.assert_not_called()
        assert response.response == "This AI tool isn't available for younger users."

    async def test_disallowed_configured_model_blocks_message(self):
        """agent_chat_config.config_value["model"] is admin-editable and picks
        the model generate_agent_response will call Ollama with; it must get
        the same allowlist check AITool.model already gets on the staff path."""
        agent = make_agent()
        db = make_db_mock(agent, configured_model="uncensored-model:latest")
        reason = "Model 'uncensored-model:latest' is not on the approved model list."

        with (
            patch(
                "app.api.v1.library_agents._check_anonymous_usage_limit",
                new=AsyncMock(return_value=(True, None)),
            ),
            patch(
                "app.services.ai_guardrails_service.check_model_allowed",
                new=AsyncMock(return_value=(False, reason)),
            ) as mock_model_allowed,
            patch(
                "app.api.v1.library_agents.generate_agent_response", new=AsyncMock()
            ) as mock_generate,
        ):
            from app.api.v1.library_agents import MessageRequest, chat_with_agent

            msg_req = MessageRequest(message="hi")
            response = await chat_with_agent(
                agent_id=1, message_req=msg_req, request=_request(), db=db, current_user=None
            )

        mock_model_allowed.assert_called_once_with(db, "uncensored-model:latest")
        mock_generate.assert_not_called()
        assert response.response == reason
        assert response.mode == "rule_based"


class TestLogAiUsageContentGate:
    """Pins log_ai_usage's log_content behavior directly -- the shared function
    both the patron chat path (log_content=False) and the staff AI-tool path
    (log_content left at its default) call. This is what stops someone
    "simplifying" this later by changing the shared function's default."""

    async def test_log_content_false_omits_identity_and_content(self):
        from app.models.ai_guardrails import AIUsageLog
        from app.services.ai_guardrails_service import GuardrailResult, log_ai_usage

        db = AsyncMock()
        result = GuardrailResult()
        result.triggered_ids = [3]

        await log_ai_usage(
            db,
            42,
            "library_agent",
            None,
            "what time do you close",
            "we close at nine",
            120,
            guardrail_result=result,
            success=True,
            system_prompt="Be helpful.",
            was_minor=True,
            patron_type_at_request="child",
            log_content=False,
        )

        logged = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], AIUsageLog)]
        assert len(logged) == 1
        row = logged[0]
        assert row.user_id is None
        assert row.prompt_preview is None
        assert row.response_preview is None
        assert row.system_prompt_used is None
        assert row.was_minor is False
        assert row.patron_type_at_request is None
        # Metadata-only fields still come through.
        assert row.guardrails_triggered == [3]
        assert row.success is True

    async def test_log_content_default_true_preserves_staff_previews(self):
        """The staff AI-tool path (ai_tools.py) never passes log_content --
        it relies on this default staying True. Regression guard: if this
        default ever flips, staff audit logging silently goes blind."""
        from app.models.ai_guardrails import AIUsageLog
        from app.services.ai_guardrails_service import log_ai_usage

        db = AsyncMock()

        await log_ai_usage(
            db,
            42,
            "ernie",
            "llama3.2:3b",
            "what are your hours",
            "we open at nine",
            120,
            success=True,
            was_minor=False,
            patron_type_at_request="adult",
        )

        logged = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], AIUsageLog)]
        assert len(logged) == 1
        row = logged[0]
        assert row.user_id == 42
        assert row.prompt_preview == "what are your hours"
        assert row.response_preview == "we open at nine"
        assert row.was_minor is False
        assert row.patron_type_at_request == "adult"


def _adult_dob() -> date:
    today = date.today()
    return date(today.year - 30, 1, 1)


def _minor_dob() -> date:
    today = date.today()
    return date(today.year - 10, 1, 1)


class TestMinorGatingRealRows:
    """Exercises real LibraryAgent / User / AIUsageLimit / AIUsageLog rows
    (not mocks) against the real ai_guardrails_service functions, per the
    review note that mock-only assertions on this service prove nothing."""

    @staticmethod
    async def _make_user(test_db, *, minor: bool, patron_type: str):
        from app.core.security import hash_password
        from app.models.user import User

        user = User(
            email=f"{patron_type}-minor-gating@example.test",
            password_hash=hash_password("TestPwd123!"),
            first_name="Test",
            last_name="Patron",
            role=UserRole.CHILD if minor else UserRole.PATRON,
            patron_type=patron_type,
            date_of_birth=_minor_dob() if minor else _adult_dob(),
            is_active=True,
            email_verified=True,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        return user

    async def test_block_for_minors_agent_blocks_real_minor_allows_real_adult(self, test_db):
        agent = LibraryAgent(
            name="Gate-Kept Agent",
            role="Reference",
            department="reference",
            bio="Only for grown-ups.",
            system_prompt="Be helpful.",
            block_for_minors=True,
        )
        test_db.add(agent)
        await test_db.commit()
        await test_db.refresh(agent)

        minor = await self._make_user(test_db, minor=True, patron_type="child")
        adult = await self._make_user(test_db, minor=False, patron_type="adult")

        from app.api.v1.library_agents import MessageRequest, chat_with_agent

        with patch(
            "app.api.v1.library_agents.generate_agent_response", new=AsyncMock()
        ) as mock_generate:
            blocked_response = await chat_with_agent(
                agent_id=agent.id,
                message_req=MessageRequest(message="hi"),
                request=_request(),
                db=test_db,
                current_user=minor,
            )
        mock_generate.assert_not_called()
        assert blocked_response.response == "This AI tool isn't available for younger users."

        with patch(
            "app.api.v1.library_agents.generate_agent_response",
            new=AsyncMock(return_value=("Welcome back!", "greeting", "rule_based")),
        ) as mock_generate:
            allowed_response = await chat_with_agent(
                agent_id=agent.id,
                message_req=MessageRequest(message="hi"),
                request=_request(),
                db=test_db,
                current_user=adult,
            )
        mock_generate.assert_called_once()
        assert allowed_response.response == "Welcome back!"

    async def test_patron_chat_log_row_has_no_prompt_preview_or_user_id(self, test_db):
        """Maintainer privacy ruling: patron chat questions are a reading-history
        record, so the ai_usage_logs audit row must carry no content and no
        patron link -- even for a signed-in patron whose user_id is otherwise
        known. Contrast test_log_content_default_true_preserves_staff_previews,
        which pins that the staff path keeps writing full previews."""
        from app.models.ai_guardrails import AIUsageLog

        agent = LibraryAgent(
            name="Open Agent Privacy Check",
            role="Reference",
            department="reference",
            bio="Open to everyone.",
            system_prompt="Be helpful.",
        )
        test_db.add(agent)
        await test_db.commit()
        await test_db.refresh(agent)

        adult = await self._make_user(test_db, minor=False, patron_type="adult")

        from app.api.v1.library_agents import MessageRequest, chat_with_agent

        with patch(
            "app.api.v1.library_agents.generate_agent_response",
            new=AsyncMock(return_value=("Sure, here you go.", "general_inquiry", "rule_based")),
        ):
            response = await chat_with_agent(
                agent_id=agent.id,
                message_req=MessageRequest(
                    message="what medications does the library carry info on"
                ),
                request=_request(),
                db=test_db,
                current_user=adult,
            )

        assert response.response == "Sure, here you go."

        result = await test_db.execute(
            select(AIUsageLog).where(AIUsageLog.tool_id == "library_agent")
        )
        row = result.scalar_one()

        assert row.user_id is None
        assert row.prompt_preview is None
        assert row.response_preview is None
        assert row.system_prompt_used is None
        assert row.was_minor is False
        assert row.patron_type_at_request is None
        # Metadata is still recorded -- this isn't a no-op audit row.
        assert row.was_blocked is False
        assert row.success is True
        assert row.created_at is not None

    async def test_anonymous_caller_treated_as_minor_on_block_for_minors_agent(self, test_db):
        agent = LibraryAgent(
            name="Gate-Kept Agent Anon",
            role="Reference",
            department="reference",
            bio="Only for grown-ups.",
            system_prompt="Be helpful.",
            block_for_minors=True,
        )
        test_db.add(agent)
        await test_db.commit()
        await test_db.refresh(agent)

        from app.api.v1.library_agents import MessageRequest, chat_with_agent

        with patch(
            "app.api.v1.library_agents.generate_agent_response", new=AsyncMock()
        ) as mock_generate:
            response = await chat_with_agent(
                agent_id=agent.id,
                message_req=MessageRequest(message="hi"),
                request=_request(),
                db=test_db,
                current_user=None,
            )

        mock_generate.assert_not_called()
        assert response.response == "Sign in is required to use this AI tool."

    async def test_anonymous_caller_subject_to_child_rate_usage_limit_keyed_by_ip(self, test_db):
        """_check_anonymous_usage_limit calls limiter.limiter.hit() directly,
        bypassing slowapi's own enabled=False / swallow_errors handling (those
        only wrap the decorator path). This test swaps in a fresh, real,
        in-memory-backed limiter for its duration so the assertion is a real
        enforcement check regardless of whatever REDIS_URL the ambient test
        environment has (unreachable "redis" hostname from a host venv would
        otherwise make every hit() fail open, and the assertions below fail
        loudly rather than silently)."""
        from app.core.rate_limit import ResilientLimiter, _client_identity

        agent = LibraryAgent(
            name="Open Agent",
            role="Reference",
            department="reference",
            bio="Open to everyone.",
            system_prompt="Be helpful.",
        )
        test_db.add(agent)
        limit = AIUsageLimit(role="child", hourly_limit=1, daily_limit=5, enabled=True)
        test_db.add(limit)
        await test_db.commit()
        await test_db.refresh(agent)

        from app.api.v1.library_agents import MessageRequest, chat_with_agent

        test_limiter = ResilientLimiter(
            key_func=_client_identity,
            storage_uri="memory://",
            strategy="fixed-window",
            enabled=True,
            swallow_errors=False,
        )

        reply = AsyncMock(return_value=("Sure, here you go.", "general_inquiry", "rule_based"))
        with (
            patch("app.api.v1.library_agents.generate_agent_response", new=reply),
            patch("app.api.v1.library_agents.limiter", new=test_limiter),
        ):
            # First call from IP #1 -- under the hourly limit of 1, allowed.
            first = await chat_with_agent(
                agent_id=agent.id,
                message_req=MessageRequest(message="hi"),
                request=_request({"cf-connecting-ip": "198.51.100.9"}),
                db=test_db,
                current_user=None,
            )
            # Second call, same IP #1 within the same hour -- limit exceeded.
            second = await chat_with_agent(
                agent_id=agent.id,
                message_req=MessageRequest(message="hi again"),
                request=_request({"cf-connecting-ip": "198.51.100.9"}),
                db=test_db,
                current_user=None,
            )
            # A different IP is a separate bucket -- not exempted globally,
            # but not caught by IP #1's limit either.
            third = await chat_with_agent(
                agent_id=agent.id,
                message_req=MessageRequest(message="hi"),
                request=_request({"cf-connecting-ip": "198.51.100.55"}),
                db=test_db,
                current_user=None,
            )

        assert first.response == "Sure, here you go."
        assert (
            second.response
            == "Hourly AI usage limit reached (1 requests/hour). Please try again later."
        )
        assert third.response == "Sure, here you go."

    async def test_existing_library_agent_row_gets_migration_column_defaults(self, test_db):
        """Simulates a row that existed before library_agent_minor_gating_001
        ran: insert without the new columns, exactly like a pre-migration row,
        and confirm the migration's server_default (not just the ORM-level
        default=) populated them -- a plain add_column with only a Python-side
        default would have left these NULL on existing rows.

        Requires Postgres: this suite's SQLite fallback builds its schema via
        Base.metadata.create_all() (see tests/database_setup.py), bypassing
        Alembic -- and with it the migration's server_default -- entirely, so
        under SQLite this insert would fail a NOT NULL constraint regardless
        of whether the migration is correct. Separately verified against a
        real Postgres instance by running library_agent_minor_gating_001's
        upgrade()/downgrade() directly (see task report)."""
        if test_db.bind.dialect.name != "postgresql":
            pytest.skip(
                "server_default backfill requires Postgres + Alembic, not the SQLite create_all() fallback"
            )

        from sqlalchemy import text

        await test_db.execute(
            text(
                "INSERT INTO library_agents (name, role, department, bio, system_prompt) "
                "VALUES (:name, :role, :department, :bio, :system_prompt)"
            ),
            {
                "name": "Pre-Migration Agent",
                "role": "Reference",
                "department": "reference",
                "bio": "Existed before the minor-gating columns were added.",
                "system_prompt": "Be helpful.",
            },
        )
        await test_db.commit()

        result = await test_db.execute(
            select(LibraryAgent).where(LibraryAgent.name == "Pre-Migration Agent")
        )
        agent = result.scalar_one()

        assert agent.block_for_minors is False
        assert agent.requires_parental_consent is False
        assert agent.block_for_patron_types == []

    async def test_real_minor_gets_age_appropriate_instruction_in_llm_system_prompt(self, test_db):
        """generate_agent_response must actually thread guardrail_result into the
        prompt handed to ollama.chat -- not just have it computed and dropped in
        chat_with_agent. Mocks only the Ollama service (not generate_agent_response
        itself), so this exercises the real build_guarded_system_prompt call."""
        agent = LibraryAgent(
            name="Open Agent Minor Prompt",
            role="Reference",
            department="reference",
            bio="Open to everyone.",
            system_prompt="Be helpful.",
        )
        test_db.add(agent)
        await test_db.commit()
        await test_db.refresh(agent)

        minor = await self._make_user(test_db, minor=True, patron_type="child")

        ollama = MagicMock()
        ollama.is_available = AsyncMock(return_value=True)
        ollama.chat = AsyncMock(return_value={"response": "Sure!"})
        ollama.base_url = "http://x:11434"
        ollama.model = "qwen2.5:3b"

        from app.api.v1.library_agents import MessageRequest, chat_with_agent

        with (
            patch.dict(os.environ, {"DISABLE_AGENT_LLM": ""}),
            patch("app.api.v1.library_agents.get_ollama_service", return_value=ollama),
            patch("app.api.v1.library_agents.FAQChatbotService") as faq,
        ):
            faq.return_value._semantic_search = AsyncMock(return_value={"results": []})
            response = await chat_with_agent(
                agent_id=agent.id,
                message_req=MessageRequest(message="hi"),
                request=_request(),
                db=test_db,
                current_user=minor,
            )

        assert response.response == "Sure!"
        system_prompt_used = ollama.chat.call_args.kwargs.get("system_prompt", "")
        assert "current user is a minor" in system_prompt_used

    async def test_anonymous_caller_gets_age_appropriate_instruction_in_llm_system_prompt(
        self, test_db
    ):
        """Same as above but for an anonymous caller (unknown age treated as a
        minor) -- the apply_youth_guardrails call-site substitute in
        chat_with_agent must also reach ollama.chat, not just chat_with_agent's
        own guardrail_result object."""
        agent = LibraryAgent(
            name="Open Agent Anon Prompt",
            role="Reference",
            department="reference",
            bio="Open to everyone.",
            system_prompt="Be helpful.",
        )
        test_db.add(agent)
        await test_db.commit()
        await test_db.refresh(agent)

        ollama = MagicMock()
        ollama.is_available = AsyncMock(return_value=True)
        ollama.chat = AsyncMock(return_value={"response": "Sure!"})
        ollama.base_url = "http://x:11434"
        ollama.model = "qwen2.5:3b"

        from app.api.v1.library_agents import MessageRequest, chat_with_agent

        with (
            patch.dict(os.environ, {"DISABLE_AGENT_LLM": ""}),
            patch("app.api.v1.library_agents.get_ollama_service", return_value=ollama),
            patch("app.api.v1.library_agents.FAQChatbotService") as faq,
        ):
            faq.return_value._semantic_search = AsyncMock(return_value={"results": []})
            response = await chat_with_agent(
                agent_id=agent.id,
                message_req=MessageRequest(message="hi"),
                request=_request(),
                db=test_db,
                current_user=None,
            )

        assert response.response == "Sure!"
        system_prompt_used = ollama.chat.call_args.kwargs.get("system_prompt", "")
        assert "current user is a minor" in system_prompt_used
