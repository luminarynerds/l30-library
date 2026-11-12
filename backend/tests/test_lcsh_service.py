# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for LCSH (Library of Congress Subject Headings) Service

LCSHService (app/services/lcsh_service.py) is a small in-memory/static
service backed by the COMMON_LCSH word list -- it is synchronous, takes no
db session, and returns plain strings (not dicts with a "heading" key):

  - autocomplete(query, limit=10) -> list[str]
  - validate(subject) -> bool
  - get_similar(subject, limit=5) -> list[str]  (substring word match, no
    fuzzy/typo correction)
  - get_all_starting_with(prefix, limit=50) -> list[str]

The API (app/api/v1/lcsh.py) is mounted at /api/v1/cataloging/subjects/...
(not /api/v1/catalog/lcsh/...), is staff-only (require_staff) on every
route, and has no standalone /suggest endpoint -- /validate folds
suggestions into its response when the term is invalid.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.models.user import User, UserRole
from app.services.lcsh_service import LCSHService


class TestLCSHAutocomplete:
    """Test LCSH autocomplete functionality"""

    def test_autocomplete_returns_matching_subjects(self):
        """Test that autocomplete returns matching subject headings"""
        service = LCSHService()

        results = service.autocomplete("Program")

        assert isinstance(results, list)
        assert len(results) > 0
        assert all("program" in result.lower() for result in results)

    def test_autocomplete_limits_results(self):
        """Test that autocomplete limits number of results"""
        service = LCSHService()

        results = service.autocomplete("C", limit=5)

        assert len(results) <= 5

    def test_autocomplete_is_case_insensitive(self):
        """Test that autocomplete is case-insensitive"""
        service = LCSHService()

        results_lower = service.autocomplete("science")
        results_upper = service.autocomplete("SCIENCE")
        results_mixed = service.autocomplete("ScIeNcE")

        # Should all return same results
        assert len(results_lower) > 0
        assert results_lower == results_upper == results_mixed

    def test_autocomplete_handles_partial_matches(self):
        """Test that autocomplete handles partial word matches"""
        service = LCSHService()

        results = service.autocomplete("Prog")

        assert len(results) > 0
        assert any("Program" in result for result in results)


class TestLCSHValidation:
    """Test LCSH validation functionality"""

    def test_validation_confirms_valid_lcsh_term(self):
        """Test that validation confirms valid LCSH terms"""
        service = LCSHService()

        is_valid = service.validate("Computer science")

        assert is_valid is True

    def test_validation_rejects_invalid_term(self):
        """Test that validation rejects invalid terms"""
        service = LCSHService()

        is_valid = service.validate("This is definitely not a valid LCSH term xyz123")

        assert is_valid is False

    def test_validation_is_case_insensitive(self):
        """Test that validation is case-insensitive"""
        service = LCSHService()

        valid_lower = service.validate("fiction")
        valid_upper = service.validate("FICTION")
        valid_title = service.validate("Fiction")

        # All should be valid
        assert valid_lower is True
        assert valid_upper is True
        assert valid_title is True


class TestLCSHBrowse:
    """Test LCSH browse-by-prefix functionality (get_all_starting_with)"""

    def test_browse_returns_subjects_by_prefix(self):
        """Test that browse returns subjects starting with prefix"""
        service = LCSHService()

        results = service.get_all_starting_with("Science")

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(result.startswith("Science") for result in results)

    def test_browse_returns_alphabetically_sorted(self):
        """Test that browse results are alphabetically sorted.

        self.subjects is built as sorted(COMMON_LCSH), and
        get_all_starting_with walks it in order, so prefix results come
        back already sorted.
        """
        service = LCSHService()

        results = service.get_all_starting_with("Computer")

        assert results == sorted(results)

    def test_browse_limits_results(self):
        """Test that browse respects the limit parameter.

        get_all_starting_with(prefix, limit=...) has no page/per_page
        pagination -- just a flat limit.
        """
        service = LCSHService()

        limited = service.get_all_starting_with("C", limit=2)

        assert len(limited) <= 2


class TestLCSHSuggestions:
    """Test get_similar (word-substring match, not fuzzy/typo correction)."""

    def test_returns_suggestions_for_partial_word(self):
        """get_similar matches subjects containing any word of the input."""
        service = LCSHService()

        suggestions = service.get_similar("Computer")

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert any("Computer" in s for s in suggestions)

    def test_suggestions_do_not_include_the_exact_term_itself(self):
        """The subject being looked up is excluded from its own suggestions."""
        service = LCSHService()

        suggestions = service.get_similar("Fiction")

        assert "Fiction" not in suggestions

    def test_suggestions_limit_results(self):
        """Test that suggestions limit number of results"""
        service = LCSHService()

        suggestions = service.get_similar("Science", limit=5)

        assert len(suggestions) <= 5


class TestLCSHAPI:
    """Test LCSH API endpoints (mounted at /api/v1/cataloging/subjects)"""

    @pytest.mark.asyncio
    async def test_autocomplete_endpoint(self, test_staff: User, staff_client):
        """Test LCSH autocomplete API endpoint"""
        response = await staff_client.get(
            "/api/v1/cataloging/subjects/autocomplete",
            params={"q": "Computer", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) <= 10

    @pytest.mark.asyncio
    async def test_validate_endpoint(self, test_staff: User, staff_client):
        """Test LCSH validation API endpoint"""
        response = await staff_client.get(
            "/api/v1/cataloging/subjects/validate",
            params={"subject": "Fiction"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data
        assert isinstance(data["is_valid"], bool)

    @pytest.mark.asyncio
    async def test_validate_endpoint_suggests_when_invalid(self, test_staff: User, staff_client):
        """An invalid term gets `suggestions` folded into the response."""
        response = await staff_client.get(
            "/api/v1/cataloging/subjects/validate",
            params={"subject": "Zzzznotarealheading"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert "suggestions" in data

    @pytest.mark.asyncio
    async def test_browse_endpoint(self, test_staff: User, staff_client):
        """Test LCSH browse API endpoint"""
        response = await staff_client.get(
            "/api/v1/cataloging/subjects/browse",
            params={"prefix": "Science", "limit": 20},
        )

        assert response.status_code == 200
        data = response.json()
        assert "subjects" in data
        assert isinstance(data["subjects"], list)


class TestLCSHAuthentication:
    """Test LCSH API authentication -- every route is require_staff."""

    @pytest.mark.asyncio
    async def test_requires_authentication(self, client):
        """Test that LCSH endpoints require authentication"""
        response = await client.get(
            "/api/v1/cataloging/subjects/autocomplete",
            params={"q": "Computer"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_patron_cannot_access_autocomplete(self, test_patron: User, client):
        """Patrons are not staff, so autocomplete (require_staff) is 403 for them."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_patron.email, "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/cataloging/subjects/autocomplete",
            params={"q": "Fiction"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403


class TestLCSHDataSource:
    """Test the in-memory LCSH data set."""

    def test_lcsh_data_is_loaded(self):
        """Test that the LCSH word list is populated."""
        service = LCSHService()

        assert len(service.subjects) > 0

    def test_common_subjects_exist(self):
        """Test that common subject headings exist"""
        service = LCSHService()

        common_subjects = [
            "Fiction",
            "Science",
            "History",
            "Computer science",
            "Education",
        ]

        for subject in common_subjects:
            is_valid = service.validate(subject)
            assert is_valid is True, f"Common subject '{subject}' should be valid"


class TestLCSHPerformance:
    """Test LCSH service performance"""

    def test_autocomplete_is_fast(self):
        """Test that autocomplete queries are fast"""
        import time

        service = LCSHService()

        start = time.perf_counter()
        results = service.autocomplete("Computer", limit=10)
        end = time.perf_counter()

        query_time = (end - start) * 1000  # milliseconds

        # Autocomplete should be under 100ms
        assert query_time < 100
        assert len(results) > 0

    def test_validation_is_fast(self):
        """Test that validation queries are fast"""
        import time

        service = LCSHService()

        start = time.perf_counter()
        is_valid = service.validate("Fiction")
        end = time.perf_counter()

        query_time = (end - start) * 1000  # milliseconds

        # Validation should be under 50ms
        assert query_time < 50
        assert isinstance(is_valid, bool)


class TestLCSHEdgeCases:
    """Test LCSH edge cases"""

    def test_empty_query_returns_empty_results(self):
        """Test that empty query returns empty results"""
        service = LCSHService()

        results = service.autocomplete("")

        assert results == []

    def test_special_characters_in_query(self):
        """Test handling of special characters in query"""
        service = LCSHService()

        # Query with special characters
        results = service.autocomplete("C++ programming")

        # Should not raise exception
        assert isinstance(results, list)

    def test_very_long_query(self):
        """Test handling of very long queries"""
        service = LCSHService()

        # Very long query
        long_query = "Computer programming " * 50

        results = service.autocomplete(long_query[:200])  # Truncate to reasonable length

        # Should not raise exception
        assert isinstance(results, list)
