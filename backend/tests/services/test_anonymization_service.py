# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for AnonymizationService."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.anonymization_service import AnonymizationService, AnonymizationResult


@pytest.fixture
def service():
    return AnonymizationService()


def _mock_ollama_unavailable(service):
    """Helper to mock Ollama as unavailable."""
    return patch.object(service, '_get_ollama', return_value=MagicMock(
        is_available=AsyncMock(return_value=False)
    ))


class TestRegexAnonymization:
    @pytest.mark.asyncio
    async def test_email_detected(self, service):
        with _mock_ollama_unavailable(service):
            result = await service.anonymize("My email is john.doe@example.com")
        assert "[EMAIL]" in result.cleaned_text
        assert "john.doe@example.com" not in result.cleaned_text
        assert "email" in result.detected_pii_types

    @pytest.mark.asyncio
    async def test_phone_formats(self, service):
        cases = [
            "Call me at (555) 123-4567",
            "My number is 555-123-4567",
            "Phone: 555.123.4567",
        ]
        with _mock_ollama_unavailable(service):
            for text in cases:
                result = await service.anonymize(text)
                assert "[PHONE]" in result.cleaned_text, f"Failed for: {text}"

    @pytest.mark.asyncio
    async def test_card_number(self, service):
        with _mock_ollama_unavailable(service):
            result = await service.anonymize("My card is LSC-A1B2C3")
        assert "[CARD_NUMBER]" in result.cleaned_text
        assert "LSC-A1B2C3" not in result.cleaned_text

    @pytest.mark.asyncio
    async def test_ssn(self, service):
        with _mock_ollama_unavailable(service):
            result = await service.anonymize("My SSN is 123-45-6789")
        assert "[SSN]" in result.cleaned_text
        assert "123-45-6789" not in result.cleaned_text

    @pytest.mark.asyncio
    async def test_dob_with_keyword(self, service):
        with _mock_ollama_unavailable(service):
            result = await service.anonymize("Date of birth: 03/15/1990")
        assert "[DOB]" in result.cleaned_text
        assert "03/15/1990" not in result.cleaned_text

    @pytest.mark.asyncio
    async def test_multiple_pii(self, service):
        text = "Card LSC-AB12CD, email jane@test.org, phone 555-111-2222"
        with _mock_ollama_unavailable(service):
            result = await service.anonymize(text)
        assert "LSC-AB12CD" not in result.cleaned_text
        assert "jane@test.org" not in result.cleaned_text
        assert len(result.detected_pii_types) >= 3

    @pytest.mark.asyncio
    async def test_no_pii_unchanged(self, service):
        text = "What are your library hours on Saturday?"
        with _mock_ollama_unavailable(service):
            result = await service.anonymize(text)
        assert result.cleaned_text == text
        assert result.detected_pii_types == []

    @pytest.mark.asyncio
    async def test_empty_text(self, service):
        with _mock_ollama_unavailable(service):
            result = await service.anonymize("")
        assert result.cleaned_text == ""


def _mock_httpx_client(ner_response):
    """_apply_ner calls httpx.AsyncClient(...).post(...) directly against
    Ollama's /api/generate, not service.generate(); patch at the httpx layer."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value={"response": ner_response})

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    return patch("httpx.AsyncClient", return_value=mock_client)


class TestNERAnonymization:
    @pytest.mark.asyncio
    async def test_ner_detects_person(self, service):
        ner_response = '[{"entity": "Sarah Johnson", "label": "person"}]'
        mock_svc = MagicMock()
        mock_svc.is_available = AsyncMock(return_value=True)

        with patch.object(service, '_get_ollama', return_value=mock_svc), _mock_httpx_client(ner_response):
            result = await service.anonymize("Books for Sarah Johnson please.")
        assert "Sarah Johnson" not in result.cleaned_text
        assert "[PATRON]" in result.cleaned_text
        assert result.ollama_enhanced is True

    @pytest.mark.asyncio
    async def test_ner_detects_address(self, service):
        ner_response = '[{"entity": "123 Oak Street, Springfield IL 62704", "label": "address"}]'
        mock_svc = MagicMock()
        mock_svc.is_available = AsyncMock(return_value=True)

        with patch.object(service, '_get_ollama', return_value=mock_svc), _mock_httpx_client(ner_response):
            result = await service.anonymize("Send to 123 Oak Street, Springfield IL 62704.")
        assert "123 Oak Street" not in result.cleaned_text
        assert "[ADDRESS]" in result.cleaned_text

    @pytest.mark.asyncio
    async def test_ner_fallback_on_bad_json(self, service):
        mock_svc = MagicMock()
        mock_svc.is_available = AsyncMock(return_value=True)
        mock_svc.generate = AsyncMock(return_value={"response": "I found no PII."})

        with patch.object(service, '_get_ollama', return_value=mock_svc):
            result = await service.anonymize("Help me find a book.")
        assert result.cleaned_text == "Help me find a book."
        assert result.ollama_enhanced is False

    @pytest.mark.asyncio
    async def test_ner_fallback_when_ollama_down(self, service):
        with patch.object(service, '_get_ollama', side_effect=Exception("connection refused")):
            result = await service.anonymize("Email is test@example.com")
        assert "[EMAIL]" in result.cleaned_text  # Regex still works
        assert result.ollama_enhanced is False
