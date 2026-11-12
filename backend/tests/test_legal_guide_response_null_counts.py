# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression: legal guide detail must serialize when feedback counts are NULL.

Bug: GET /api/v1/legal/guides/{id} and /guides/slug/{slug} returned HTTP 500 for
every seeded guide. LegalGuideResponse typed helpful_count / not_helpful_count as
required ``int``, but the columns are NULL on seeded rows (model default=0 is
Python-side only, no server_default), and guides.py::_guide_to_response passes
those NULLs straight through -> ResponseValidationError. The sibling
LegalCollectionResponse already tolerates NULL counts; this aligns the guide schema.
"""
from __future__ import annotations

from app.schemas.legal import LegalGuideResponse


def _payload(**overrides) -> dict:
    payload = {
        "id": 1,
        "title": "Expungement in Ohio",
        "slug": "expungement-in-ohio",
        "helpful_count": None,
        "not_helpful_count": None,
        "view_count": None,
    }
    payload.update(overrides)
    return payload


def test_null_feedback_counts_serialize_without_error():
    # Pre-fix this raised ValidationError (2 errors, int_type on the count fields).
    resp = LegalGuideResponse.model_validate(_payload())
    assert resp.helpful_count in (0, None)
    assert resp.not_helpful_count in (0, None)
    assert resp.view_count in (0, None)


def test_real_integer_counts_preserved():
    resp = LegalGuideResponse.model_validate(
        _payload(helpful_count=7, not_helpful_count=2, view_count=87)
    )
    assert resp.helpful_count == 7
    assert resp.not_helpful_count == 2
    assert resp.view_count == 87
