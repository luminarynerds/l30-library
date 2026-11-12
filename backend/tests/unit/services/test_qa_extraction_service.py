# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_extract_qa_from_text():
    from app.services.qa_extraction_service import QAExtractionService
    service = QAExtractionService()
    mock_response = '[{"question": "What is the borrowing limit?", "answer": "Patrons may borrow up to 50 items."}]'
    with patch.object(service, '_call_ollama', new_callable=AsyncMock, return_value=mock_response):
        pairs = await service.extract_from_text("Library Policy: Patrons may borrow up to 50 items.")
        assert len(pairs) == 1
        assert "borrowing" in pairs[0]["question"].lower() or "borrow" in pairs[0]["answer"].lower()


@pytest.mark.asyncio
async def test_extract_qa_handles_malformed_json():
    from app.services.qa_extraction_service import QAExtractionService
    service = QAExtractionService()
    with patch.object(service, '_call_ollama', new_callable=AsyncMock, return_value="not valid json"):
        pairs = await service.extract_from_text("Some text")
        assert pairs == []


@pytest.mark.asyncio
async def test_extract_qa_handles_ollama_failure():
    from app.services.qa_extraction_service import QAExtractionService
    service = QAExtractionService()
    with patch.object(service, '_call_ollama', new_callable=AsyncMock, side_effect=Exception("connection refused")):
        pairs = await service.extract_from_text("Some text")
        assert pairs == []


@pytest.mark.asyncio
async def test_extract_qa_handles_markdown_code_block():
    from app.services.qa_extraction_service import QAExtractionService
    service = QAExtractionService()
    mock_response = '```json\n[{"question": "When do you close?", "answer": "8pm on weekdays."}]\n```'
    with patch.object(service, '_call_ollama', new_callable=AsyncMock, return_value=mock_response):
        pairs = await service.extract_from_text("We close at 8pm on weekdays.")
        assert len(pairs) == 1


@pytest.mark.asyncio
async def test_extract_qa_filters_invalid_pairs():
    from app.services.qa_extraction_service import QAExtractionService
    service = QAExtractionService()
    mock_response = '[{"question": "Valid?", "answer": "Yes"}, {"invalid": "no answer key"}, "not a dict"]'
    with patch.object(service, '_call_ollama', new_callable=AsyncMock, return_value=mock_response):
        pairs = await service.extract_from_text("Some text")
        assert len(pairs) == 1


@pytest.mark.asyncio
async def test_extract_qa_handles_none_response():
    from app.services.qa_extraction_service import QAExtractionService
    service = QAExtractionService()
    with patch.object(service, '_call_ollama', new_callable=AsyncMock, return_value=None):
        pairs = await service.extract_from_text("Some text")
        assert pairs == []
