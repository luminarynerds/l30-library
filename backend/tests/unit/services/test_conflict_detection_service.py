# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch


def test_cosine_similarity_math():
    """Verify our understanding of cosine distance vs similarity."""
    # Two identical vectors should have distance 0 (similarity 1.0)
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([1.0, 0.0, 0.0])
    distance = 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    similarity = 1 - distance
    assert similarity == pytest.approx(1.0)

    # Orthogonal vectors should have distance 1 (similarity 0.0)
    c = np.array([0.0, 1.0, 0.0])
    distance2 = 1 - np.dot(a, c) / (np.linalg.norm(a) * np.linalg.norm(c))
    similarity2 = 1 - distance2
    assert similarity2 == pytest.approx(0.0)

    # Nearly identical vectors should have high similarity
    d = np.array([1.0, 0.01, 0.0])
    distance3 = 1 - np.dot(a, d) / (np.linalg.norm(a) * np.linalg.norm(d))
    similarity3 = 1 - distance3
    assert similarity3 > 0.99


@pytest.mark.asyncio
async def test_check_entry_returns_empty_without_embedding():
    from app.services.conflict_detection_service import ConflictDetectionService
    service = ConflictDetectionService()
    mock_db = AsyncMock()
    entry = MagicMock(embedding_id=None)
    result = await service.check_entry(mock_db, entry)
    assert result == []


@pytest.mark.asyncio
async def test_scan_all_deduplicates_pairs():
    from app.services.conflict_detection_service import ConflictDetectionService
    service = ConflictDetectionService()
    mock_db = AsyncMock()

    entry_a = MagicMock(id=1, title="A", persona_domain="shared", review_status="approved", embedding_id=1)
    entry_b = MagicMock(id=2, title="B", persona_domain="shared", review_status="approved", embedding_id=2)

    # Mock scan_all's internal query to return both entries
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [entry_a, entry_b]
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Mock check_entry to return cross-references
    async def mock_check(db, entry):
        if entry.id == 1:
            return [{"entry_id": 2, "title": "B", "content": "B content", "similarity": 0.95, "persona_domain": "shared"}]
        elif entry.id == 2:
            return [{"entry_id": 1, "title": "A", "content": "A content", "similarity": 0.95, "persona_domain": "shared"}]
        return []

    with patch.object(service, 'check_entry', side_effect=mock_check):
        conflicts = await service.scan_all(mock_db)
        # Should only have 1 pair, not 2 (deduplication)
        assert len(conflicts) == 1
        pair = conflicts[0]
        assert {pair["entry_a_id"], pair["entry_b_id"]} == {1, 2}
