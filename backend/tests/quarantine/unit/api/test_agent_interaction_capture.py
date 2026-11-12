# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for auto-capture of patron interactions into the knowledge pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def make_agent(department="Reference"):
    agent = MagicMock()
    agent.id = 1
    agent.name = "Mrs. Delacroix"
    agent.role = "Head Librarian"
    agent.department = department
    agent.bio = "Experienced librarian."
    agent.personality = "friendly"
    agent.tone = "warm"
    agent.specialties = []
    agent.can_help_with = []
    agent.greeting_message = None
    agent.is_active = True
    return agent


def make_db_mock(agent):
    """Return an AsyncMock db where execute().scalar_one_or_none() returns the agent."""
    db = AsyncMock()

    # First execute() call: agent lookup
    agent_result = MagicMock()
    agent_result.scalar_one_or_none.return_value = agent

    # Second execute() call: conversation history (no existing session)
    history_result = MagicMock()
    history_result.scalars.return_value.all.return_value = []

    db.execute.side_effect = [agent_result, history_result]

    # Simulate conversation saved and refreshed
    saved_conv = MagicMock()
    saved_conv.id = 42

    async def fake_refresh(obj):
        obj.id = 42

    db.refresh.side_effect = fake_refresh
    return db


@pytest.mark.unit
class TestPatronInteractionCapture:
    """Feature-flag-gated capture of patron Q&A into the knowledge pipeline."""

    @pytest.mark.asyncio
    async def test_capture_called_when_flag_enabled(self, monkeypatch):
        """When KNOWLEDGE_PIPELINE_CAPTURE_ENABLED=true, ingest_patron_interaction is called."""
        monkeypatch.setenv("KNOWLEDGE_PIPELINE_CAPTURE_ENABLED", "true")

        agent = make_agent()
        db = make_db_mock(agent)

        mock_pipeline_instance = AsyncMock()
        mock_pipeline_instance.ingest_patron_interaction.return_value = MagicMock()

        with patch(
            "app.api.v1.library_agents.generate_agent_response",
            new=AsyncMock(return_value=("The library opens at 9am.", "hours_inquiry")),
        ), patch(
            "app.api.v1.library_agents.KnowledgePipelineService",
            return_value=mock_pipeline_instance,
        ), patch(
            "app.api.v1.library_agents.get_suggested_followups",
            return_value=[],
        ):
            from app.api.v1.library_agents import chat_with_agent, MessageRequest

            request = MessageRequest(message="What time do you open?")
            response = await chat_with_agent(
                agent_id=1, message_req=request, db=db, current_user=None
            )

        assert response.response == "The library opens at 9am."
        mock_pipeline_instance.ingest_patron_interaction.assert_called_once()
        call_kwargs = mock_pipeline_instance.ingest_patron_interaction.call_args.kwargs
        assert call_kwargs["category"] == "patron_chat"
        assert "What time do you open?" in call_kwargs["title"]
        assert call_kwargs["persona_domain"] == "Reference"

    @pytest.mark.asyncio
    async def test_capture_not_called_when_flag_disabled(self, monkeypatch):
        """When KNOWLEDGE_PIPELINE_CAPTURE_ENABLED=false (default), ingest_patron_interaction is NOT called."""
        monkeypatch.setenv("KNOWLEDGE_PIPELINE_CAPTURE_ENABLED", "false")

        agent = make_agent()
        db = make_db_mock(agent)

        mock_pipeline_instance = AsyncMock()

        with patch(
            "app.api.v1.library_agents.generate_agent_response",
            new=AsyncMock(return_value=("Happy to help!", "general")),
        ), patch(
            "app.api.v1.library_agents.KnowledgePipelineService",
            return_value=mock_pipeline_instance,
        ), patch(
            "app.api.v1.library_agents.get_suggested_followups",
            return_value=[],
        ):
            from app.api.v1.library_agents import chat_with_agent, MessageRequest

            request = MessageRequest(message="Can you help me?")
            response = await chat_with_agent(
                agent_id=1, message_req=request, db=db, current_user=None
            )

        assert response.response == "Happy to help!"
        mock_pipeline_instance.ingest_patron_interaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_capture_not_called_when_flag_absent(self, monkeypatch):
        """When env var is not set at all, capture does not run."""
        monkeypatch.delenv("KNOWLEDGE_PIPELINE_CAPTURE_ENABLED", raising=False)

        agent = make_agent()
        db = make_db_mock(agent)

        mock_pipeline_instance = AsyncMock()

        with patch(
            "app.api.v1.library_agents.generate_agent_response",
            new=AsyncMock(return_value=("Here is the info.", "general")),
        ), patch(
            "app.api.v1.library_agents.KnowledgePipelineService",
            return_value=mock_pipeline_instance,
        ), patch(
            "app.api.v1.library_agents.get_suggested_followups",
            return_value=[],
        ):
            from app.api.v1.library_agents import chat_with_agent, MessageRequest

            request = MessageRequest(message="Tell me about eBooks.")
            response = await chat_with_agent(
                agent_id=1, message_req=request, db=db, current_user=None
            )

        assert response.response == "Here is the info."
        mock_pipeline_instance.ingest_patron_interaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_chat_succeeds_when_capture_raises(self, monkeypatch):
        """When capture throws an exception, the chat response still succeeds."""
        monkeypatch.setenv("KNOWLEDGE_PIPELINE_CAPTURE_ENABLED", "true")

        agent = make_agent()
        db = make_db_mock(agent)

        mock_pipeline_instance = AsyncMock()
        mock_pipeline_instance.ingest_patron_interaction.side_effect = Exception(
            "Database connection lost"
        )

        with patch(
            "app.api.v1.library_agents.generate_agent_response",
            new=AsyncMock(return_value=("We have over 10,000 eBooks.", "catalog")),
        ), patch(
            "app.api.v1.library_agents.KnowledgePipelineService",
            return_value=mock_pipeline_instance,
        ), patch(
            "app.api.v1.library_agents.get_suggested_followups",
            return_value=[],
        ):
            from app.api.v1.library_agents import chat_with_agent, MessageRequest

            request = MessageRequest(message="How many eBooks do you have?")
            # Should not raise despite pipeline failure
            response = await chat_with_agent(
                agent_id=1, message_req=request, db=db, current_user=None
            )

        assert response.response == "We have over 10,000 eBooks."
        mock_pipeline_instance.ingest_patron_interaction.assert_called_once()
