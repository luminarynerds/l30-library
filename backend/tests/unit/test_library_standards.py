# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for library industry standard integrations.

Tests for:
- Call number sorting (LC and Dewey)
- Barcode format validation
- ISSN check digit validation
"""

import pytest
from datetime import datetime


class TestCallNumberSorting:
    """Tests for call number sorting algorithms."""

    def test_parse_lc_call_number_basic(self):
        """Test parsing basic LC call number."""
        from app.services.call_number_service import CallNumberService

        parsed = CallNumberService.parse_lc_call_number("PS3557.R3355")
        assert parsed.class_letters == "PS"
        assert parsed.class_number == 3557.0
        assert parsed.cutter1_letter == "R"
        assert parsed.cutter1_number == pytest.approx(0.3355)

    def test_parse_lc_call_number_with_year(self):
        """Test parsing LC call number with year."""
        from app.services.call_number_service import CallNumberService

        parsed = CallNumberService.parse_lc_call_number("QA76.73.P98 W35 2020")
        assert parsed.class_letters == "QA"
        assert parsed.class_number == 76.73
        assert parsed.year == 2020

    def test_parse_dewey_call_number_basic(self):
        """Test parsing basic Dewey call number."""
        from app.services.call_number_service import CallNumberService

        parsed = CallNumberService.parse_dewey_call_number("813.54 S655")
        assert parsed.class_number == 813.54
        assert parsed.cutter_letter == "S"
        assert parsed.cutter_number == pytest.approx(0.655)

    def test_is_lc_call_number(self):
        """Test LC call number detection."""
        from app.services.call_number_service import CallNumberService

        assert CallNumberService.is_lc_call_number("PS3557.R3355")
        assert CallNumberService.is_lc_call_number("QA 76.73")
        assert not CallNumberService.is_lc_call_number("813.54")
        assert not CallNumberService.is_lc_call_number("")

    def test_is_dewey_call_number(self):
        """Test Dewey call number detection."""
        from app.services.call_number_service import CallNumberService

        assert CallNumberService.is_dewey_call_number("813.54")
        assert CallNumberService.is_dewey_call_number("025.04")
        assert not CallNumberService.is_dewey_call_number("PS3557")
        assert not CallNumberService.is_dewey_call_number("")

    def test_sort_lc_call_numbers(self):
        """Test sorting LC call numbers in shelf order."""
        from app.services.call_number_service import CallNumberService

        call_numbers = [
            "PS3557.R3355",
            "PS3557.A44",
            "QA76.73.P98",
            "A1.B2",
            "PS3600.Z99",
        ]

        sorted_numbers = CallNumberService.sort_call_numbers(call_numbers)

        # A should come before PS, PS3557.A44 before PS3557.R3355
        assert sorted_numbers[0] == "A1.B2"
        assert sorted_numbers.index("PS3557.A44") < sorted_numbers.index("PS3557.R3355")
        assert sorted_numbers.index("PS3557.R3355") < sorted_numbers.index("PS3600.Z99")

    def test_sort_dewey_call_numbers(self):
        """Test sorting Dewey call numbers in shelf order."""
        from app.services.call_number_service import CallNumberService

        call_numbers = [
            "813.54 S655",
            "025.04 C737",
            "813.54 A123",
            "999.99 Z999",
        ]

        sorted_numbers = CallNumberService.sort_call_numbers(call_numbers)

        # 025 should come before 813, A123 before S655
        assert sorted_numbers.index("025.04 C737") < sorted_numbers.index("813.54 S655")
        assert sorted_numbers.index("813.54 A123") < sorted_numbers.index("813.54 S655")

    def test_compare_call_numbers(self):
        """Test call number comparison."""
        from app.services.call_number_service import CallNumberService

        # PS comes before QA
        assert CallNumberService.compare_call_numbers("PS3557", "QA76") == -1
        # Same call number
        assert CallNumberService.compare_call_numbers("PS3557", "PS3557") == 0
        # QA comes after PS
        assert CallNumberService.compare_call_numbers("QA76", "PS3557") == 1

    def test_mixed_lc_dewey_sorting(self):
        """Test sorting mixed LC and Dewey numbers."""
        from app.services.call_number_service import CallNumberService

        call_numbers = [
            "813.54",      # Dewey
            "PS3557",      # LC
            "025.04",      # Dewey
            "QA76.73",     # LC
        ]

        sorted_numbers = CallNumberService.sort_call_numbers(call_numbers)

        # LC should come before Dewey in mixed sorting
        lc_indices = [sorted_numbers.index(cn) for cn in ["PS3557", "QA76.73"]]
        dewey_indices = [sorted_numbers.index(cn) for cn in ["813.54", "025.04"]]

        # All LC should come before all Dewey
        assert max(lc_indices) < min(dewey_indices)

    def test_parse_manga_call_number_basic(self):
        """Test parsing basic Manga call number."""
        from app.services.call_number_service import CallNumberService

        parsed = CallNumberService.parse_manga_call_number("GN NARUTO v.1")
        assert parsed.prefix == "GN"
        assert parsed.series_name == "NARUTO"
        assert parsed.volume_number == 1
        assert parsed.year is None

    def test_parse_manga_call_number_with_quotes(self):
        """Test parsing Manga call number with quoted series name."""
        from app.services.call_number_service import CallNumberService

        parsed = CallNumberService.parse_manga_call_number('MANGA "Attack on Titan" v.3')
        assert parsed.prefix == "MANGA"
        assert parsed.series_name == "Attack on Titan"
        assert parsed.volume_number == 3

    def test_parse_manga_call_number_comic_format(self):
        """Test parsing COMIC prefix format."""
        from app.services.call_number_service import CallNumberService

        parsed = CallNumberService.parse_manga_call_number("COMIC Spider-Man v.42 2020")
        assert parsed.prefix == "COMIC"
        assert parsed.series_name == "Spider-Man"
        assert parsed.volume_number == 42
        assert parsed.year == 2020

    def test_is_manga_call_number(self):
        """Test Manga call number detection."""
        from app.services.call_number_service import CallNumberService

        assert CallNumberService.is_manga_call_number("GN NARUTO v.1")
        assert CallNumberService.is_manga_call_number("MANGA Attack on Titan v.3")
        assert CallNumberService.is_manga_call_number("COMIC Spider-Man v.42")
        assert not CallNumberService.is_manga_call_number("PS3557")
        assert not CallNumberService.is_manga_call_number("813.54")
        assert not CallNumberService.is_manga_call_number("")

    def test_sort_manga_call_numbers_by_volume(self):
        """Test sorting Manga call numbers respects volume order."""
        from app.services.call_number_service import CallNumberService

        call_numbers = [
            "GN NARUTO v.5",
            "GN NARUTO v.1",
            "GN NARUTO v.3",
            "GN NARUTO v.10",  # Numeric sort, not string sort
        ]

        sorted_numbers = CallNumberService.sort_call_numbers(call_numbers)

        # Verify numeric volume sorting (v.1, v.3, v.5, v.10 not v.1, v.10, v.3, v.5)
        assert sorted_numbers[0] == "GN NARUTO v.1"
        assert sorted_numbers[1] == "GN NARUTO v.3"
        assert sorted_numbers[2] == "GN NARUTO v.5"
        assert sorted_numbers[3] == "GN NARUTO v.10"

    def test_sort_manga_multiple_series(self):
        """Test sorting Manga call numbers across different series."""
        from app.services.call_number_service import CallNumberService

        call_numbers = [
            "MANGA Bleach v.2",
            "GN Naruto v.2",
            "MANGA Bleach v.1",
            "GN Naruto v.1",
        ]

        sorted_numbers = CallNumberService.sort_call_numbers(call_numbers)

        # GN should come before MANGA (alphabetically)
        gn_indices = [i for i, cn in enumerate(sorted_numbers) if cn.startswith("GN")]
        manga_indices = [i for i, cn in enumerate(sorted_numbers) if cn.startswith("MANGA")]
        assert max(gn_indices) < min(manga_indices)

        # Within MANGA prefix, Bleach volumes should be ordered numerically
        assert sorted_numbers.index("MANGA Bleach v.1") < sorted_numbers.index("MANGA Bleach v.2")

    def test_normalize_manga_call_number(self):
        """Test normalizing Manga call numbers."""
        from app.services.call_number_service import CallNumberService

        normalized = CallNumberService.normalize_manga_call_number("gn naruto v.1")
        assert normalized == "GN naruto v.1"

        normalized = CallNumberService.normalize_manga_call_number('manga "attack on titan" v.3 2020')
        assert normalized == 'MANGA attack on titan v.3 2020'

    def test_format_manga_spine_label(self):
        """Test formatting Manga call numbers for spine labels."""
        from app.services.call_number_service import CallNumberService

        label = CallNumberService.format_manga_spine_label("GN NARUTO v.1")
        lines = label.split("\n")
        assert lines[0] == "GN"
        assert lines[1] == "NARUTO"
        assert lines[2] == "v.1"

        label = CallNumberService.format_manga_spine_label("MANGA Attack on Titan v.3")
        lines = label.split("\n")
        assert lines[0] == "MANGA"
        assert lines[1] == "ATTACK ON TITAN"
        assert lines[2] == "v.3"

    def test_generate_manga_call_number_series_and_author_modes(self):
        """Test manga call number generation for series and author shelving modes."""
        from app.services.call_number_service import CallNumberService

        series_call_number = CallNumberService.generate_manga_call_number(
            prefix="GN",
            series_title="Naruto",
            volume_number=12,
            shelve_by_series=True,
        )
        assert series_call_number == "GN Naruto v.12"

        author_call_number = CallNumberService.generate_manga_call_number(
            prefix="MANGA",
            series_title="One Piece",
            author_name="Eiichiro Oda",
            volume_number=7,
            shelve_by_series=False,
        )
        assert author_call_number == "MANGA ODA v.7"

    def test_get_manga_shelving_location_display(self):
        """Test shelving location display labels for manga/GN prefixes."""
        from app.services.call_number_service import CallNumberService

        assert CallNumberService.get_manga_shelving_location("GN", "teen") == "Teen GN"
        assert CallNumberService.get_manga_shelving_location("MANGA", "adult") == "Adult Manga"
        assert CallNumberService.get_manga_shelving_location("COMIC", "teen") == "Teen Comics"

    def test_get_browse_shelf_neighbors(self):
        """Test browse shelf neighbors returns adjacent sorted titles."""
        from app.services.call_number_service import CallNumberService

        call_numbers = [
            "GN NARUTO v.1",
            "GN NARUTO v.2",
            "GN NARUTO v.3",
            "GN NARUTO v.4",
            "GN NARUTO v.5",
        ]
        neighbors = CallNumberService.get_browse_shelf_neighbors(call_numbers, "GN NARUTO v.3", window=1)
        assert neighbors == ["GN NARUTO v.2", "GN NARUTO v.3", "GN NARUTO v.4"]

    def test_get_shelf_location_range_manga(self):
        """Test getting shelf location ranges for Manga call numbers."""
        from app.services.call_number_service import CallNumberService

        # Class level (just the prefix)
        start, end = CallNumberService.get_shelf_location_range("GN NARUTO v.1", "class")
        assert start == "GN" and end == "GN"

        # Subclass level (prefix + first letter)
        start, end = CallNumberService.get_shelf_location_range("GN NARUTO v.1", "subclass")
        assert start == "GN N" and end == "GN N"

        # Number level (series name)
        start, end = CallNumberService.get_shelf_location_range("GN NARUTO v.1", "number")
        assert start == "NARUTO" and end == "NARUTO"

    def test_mixed_format_sorting(self):
        """Test sorting mixed Manga, LC, and Dewey call numbers."""
        from app.services.call_number_service import CallNumberService

        call_numbers = [
            "813.54 S655",       # Dewey
            "GN NARUTO v.1",     # Manga
            "PS3557.R3355",      # LC
            "MANGA Bleach v.2",  # Manga
            "025.04 C737",       # Dewey
        ]

        sorted_numbers = CallNumberService.sort_call_numbers(call_numbers)

        # Manga should come first, then LC, then Dewey
        manga_indices = [i for i, cn in enumerate(sorted_numbers) if cn.startswith("GN") or cn.startswith("MANGA")]
        lc_indices = [i for i, cn in enumerate(sorted_numbers) if cn[0].isalpha() and not cn.startswith("GN") and not cn.startswith("MANGA")]
        dewey_indices = [i for i, cn in enumerate(sorted_numbers) if cn[0].isdigit()]

        if manga_indices:
            assert max(manga_indices) < min(lc_indices) if lc_indices else True
        if lc_indices and dewey_indices:
            assert max(lc_indices) < min(dewey_indices)

