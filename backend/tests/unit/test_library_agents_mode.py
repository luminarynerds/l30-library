# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the response-mode signal returned by generate_agent_response."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_guardrails_service import GuardrailResult


def _agent():
    agent = MagicMock()
    agent.name = "Marlene"
    agent.role = "genealogy"
    agent.department = "shared"
    return agent


class TestResponseMode:
    async def test_reports_rule_based_when_llm_disabled(self):
        from app.api.v1.library_agents import generate_agent_response

        with patch.dict(os.environ, {"DISABLE_AGENT_LLM": "1"}):
            response, intent, mode = await generate_agent_response(
                _agent(), "what are your hours", {}, AsyncMock(), GuardrailResult()
            )

        assert mode == "rule_based"
        assert response

    async def test_reports_llm_when_model_answers(self):
        from app.api.v1.library_agents import generate_agent_response

        ollama = MagicMock()
        ollama.is_available = AsyncMock(return_value=True)
        ollama.chat = AsyncMock(return_value={"response": "We open at nine."})
        ollama.base_url = "http://x:11434"
        ollama.model = "qwen2.5:3b"

        db = AsyncMock()
        db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        with (
            patch.dict(os.environ, {"DISABLE_AGENT_LLM": ""}),
            patch("app.api.v1.library_agents.get_ollama_service", return_value=ollama),
            patch("app.api.v1.library_agents.FAQChatbotService") as faq,
        ):
            faq.return_value._semantic_search = AsyncMock(return_value={"results": []})
            response, intent, mode = await generate_agent_response(
                _agent(), "what time do you open", {"history": []}, db, GuardrailResult()
            )

        assert mode == "llm"
        assert response == "We open at nine."

    async def test_reports_rule_based_when_model_unreachable(self):
        from app.api.v1.library_agents import generate_agent_response

        ollama = MagicMock()
        ollama.is_available = AsyncMock(side_effect=RuntimeError("connection refused"))

        with (
            patch.dict(os.environ, {"DISABLE_AGENT_LLM": ""}),
            patch("app.api.v1.library_agents.get_ollama_service", return_value=ollama),
        ):
            response, intent, mode = await generate_agent_response(
                _agent(), "what are your hours", {"history": []}, AsyncMock(), GuardrailResult()
            )

        assert mode == "rule_based"
        assert response
