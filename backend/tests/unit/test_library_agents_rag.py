# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for RAG context injection in library agent chat."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai_guardrails_service import GuardrailResult


def make_agent(name="Mrs. Delacroix", role="Head Librarian", department="Reference"):
    agent = MagicMock()
    agent.name = name
    agent.role = role
    agent.department = department
    agent.bio = (
        "Experienced librarian with a passion for connecting patrons with the right resources."
    )
    agent.personality = "friendly"
    agent.tone = "warm"
    agent.specialties = ["reference", "research"]
    agent.can_help_with = ["finding books", "research help"]
    return agent


@pytest.mark.unit
class TestLibraryAgentRAGInjection:
    """Tests for RAG context injection into library agent chat."""

    @pytest.mark.asyncio
    async def test_rag_context_injected_when_results_returned(self):
        """RAG context is appended to system prompt when KB has relevant entries."""
        agent = make_agent()
        db = AsyncMock()

        rag_result = {
            "results": [
                {
                    "text_content": "The library is open Monday-Thursday 9am-8pm.",
                    "similarity": 0.92,
                },
                {"text_content": "Elmdale branch closes at 6pm on weekdays.", "similarity": 0.87},
            ]
        }

        with (
            patch("app.api.v1.library_agents.FAQChatbotService") as MockFAQ,
            patch("app.api.v1.library_agents.get_ollama_service") as mock_ollama_factory,
        ):
            mock_faq_instance = AsyncMock()
            mock_faq_instance._semantic_search.return_value = rag_result
            MockFAQ.return_value = mock_faq_instance

            mock_ollama = AsyncMock()
            mock_ollama.is_available.return_value = True
            mock_ollama.chat.return_value = {
                "response": "We are open Monday through Thursday 9am to 8pm.",
                "model": "llama3.2",
                "generation_time_ms": 150,
                "prompt_tokens": 100,
                "completion_tokens": 30,
            }
            mock_ollama_factory.return_value = mock_ollama

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            db.execute.return_value = mock_result

            from app.api.v1.library_agents import generate_agent_response

            response, intent, mode = await generate_agent_response(
                agent, "What are your hours?", {}, db, GuardrailResult()
            )

        assert response == "We are open Monday through Thursday 9am to 8pm."
        call_kwargs = mock_ollama.chat.call_args
        system_prompt_used = call_kwargs.kwargs.get("system_prompt", "")
        assert "Relevant library knowledge" in system_prompt_used
        assert "The library is open Monday-Thursday 9am-8pm." in system_prompt_used
        assert "Elmdale branch closes at 6pm on weekdays." in system_prompt_used

    @pytest.mark.asyncio
    async def test_agent_works_when_semantic_search_returns_empty(self):
        """Agent still responds normally when semantic search returns no results."""
        agent = make_agent()
        db = AsyncMock()

        rag_result = {"results": []}

        with (
            patch("app.api.v1.library_agents.FAQChatbotService") as MockFAQ,
            patch("app.api.v1.library_agents.get_ollama_service") as mock_ollama_factory,
        ):
            mock_faq_instance = AsyncMock()
            mock_faq_instance._semantic_search.return_value = rag_result
            MockFAQ.return_value = mock_faq_instance

            mock_ollama = AsyncMock()
            mock_ollama.is_available.return_value = True
            mock_ollama.chat.return_value = {
                "response": "I can help you with that!",
                "model": "llama3.2",
                "generation_time_ms": 100,
                "prompt_tokens": 80,
                "completion_tokens": 15,
            }
            mock_ollama_factory.return_value = mock_ollama

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            db.execute.return_value = mock_result

            from app.api.v1.library_agents import generate_agent_response

            response, intent, mode = await generate_agent_response(
                agent, "Can you help me?", {}, db, GuardrailResult()
            )

        assert response == "I can help you with that!"
        call_kwargs = mock_ollama.chat.call_args
        system_prompt_used = call_kwargs.kwargs.get("system_prompt", "")
        assert "Relevant library knowledge" not in system_prompt_used

    @pytest.mark.asyncio
    async def test_agent_works_when_semantic_search_raises_exception(self):
        """Agent still responds normally when semantic search throws an exception."""
        agent = make_agent()
        db = AsyncMock()

        with (
            patch("app.api.v1.library_agents.FAQChatbotService") as MockFAQ,
            patch("app.api.v1.library_agents.get_ollama_service") as mock_ollama_factory,
        ):
            mock_faq_instance = AsyncMock()
            mock_faq_instance._semantic_search.side_effect = Exception("pgvector unavailable")
            MockFAQ.return_value = mock_faq_instance

            mock_ollama = AsyncMock()
            mock_ollama.is_available.return_value = True
            mock_ollama.chat.return_value = {
                "response": "Here is what I know about that topic.",
                "model": "llama3.2",
                "generation_time_ms": 120,
                "prompt_tokens": 80,
                "completion_tokens": 20,
            }
            mock_ollama_factory.return_value = mock_ollama

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            db.execute.return_value = mock_result

            from app.api.v1.library_agents import generate_agent_response

            response, intent, mode = await generate_agent_response(
                agent, "Tell me about digital resources.", {}, db, GuardrailResult()
            )

        assert response == "Here is what I know about that topic."
        call_kwargs = mock_ollama.chat.call_args
        system_prompt_used = call_kwargs.kwargs.get("system_prompt", "")
        assert "Relevant library knowledge" not in system_prompt_used
