# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for Japanese name handling in LSC.

Tests cover:
- Name order flexibility (family-given vs given-family)
- Romanization variations
- Kanji/hiragana display options
- Pseudonym linking
- Author search across name variations
- Authority record linking to VIAF/LC/NDLSH
"""

import pytest
from app.utils.japanese_name_handler import (
    JapaneseName,
    JapaneseNameHandler,
    NameOrder,
    RomanizationSystem,
    PenNameRecord,
)


class TestJapaneseNameBasics:
    """Test basic Japanese name functionality."""

    def test_create_with_kanji(self):
        """Test creating a Japanese name with kanji."""
        name = JapaneseName(
            family_name_kanji="手塚",
            given_name_kanji="治虫",
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
        )

        assert name.family_name_kanji == "手塚"
        assert name.given_name_kanji == "治虫"
        assert name.family_name_romaji == "Tezuka"
        assert name.given_name_romaji == "Osamu"

    def test_create_with_hiragana(self):
        """Test creating a Japanese name with hiragana."""
        name = JapaneseName(
            family_name_hiragana="てづか",
            given_name_hiragana="はるむし",
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
        )

        assert name.family_name_hiragana == "てづか"
        assert name.given_name_hiragana == "はるむし"


class TestNameOrder:
    """Test name order flexibility."""

    def test_display_family_given_order(self):
        """Test displaying name in family-given order (Japanese)."""
        name = JapaneseName(
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
            preferred_order=NameOrder.FAMILY_GIVEN,
        )

        display = name.get_display_name(order=NameOrder.FAMILY_GIVEN)
        assert display == "Tezuka Osamu"

    def test_display_given_family_order(self):
        """Test displaying name in given-family order (Western)."""
        name = JapaneseName(
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
            preferred_order=NameOrder.FAMILY_GIVEN,
        )

        display = name.get_display_name(order=NameOrder.GIVEN_FAMILY)
        assert display == "Osamu Tezuka"

    def test_inverted_format(self):
        """Test getting name in inverted format."""
        name = JapaneseName(
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
        )

        inverted = name.get_inverted_name()
        assert inverted == "Tezuka, Osamu"

    def test_sort_name(self):
        """Test getting sortable name."""
        name = JapaneseName(
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
        )

        sort_name = name.get_sort_name()
        assert sort_name == "Tezuka, Osamu"


class TestRomanizationVariations:
    """Test different romanization variations."""

    def test_all_variations_family_given(self):
        """Test getting all name variations (family-given order)."""
        name = JapaneseName(
            family_name_kanji="手塚",
            given_name_kanji="治虫",
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
        )

        variations = name.get_all_variations()

        # Should include both family-given and given-family romaji
        assert "Tezuka Osamu" in variations
        assert "osamu tezuka" in variations  # lowercase
        assert "Osamu Tezuka" in variations
        assert "Tezuka, Osamu" in variations

        # Should include kanji
        assert "手塚治虫" in variations
        assert "手塚 治虫" in variations

        # Should include individual names
        assert "Tezuka" in variations
        assert "Osamu" in variations

    def test_all_variations_with_hiragana(self):
        """Test variations including hiragana."""
        name = JapaneseName(
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
            family_name_hiragana="てづか",
            given_name_hiragana="はるむし",
        )

        variations = name.get_all_variations()

        # Should include hiragana
        assert "てづかはるむし" in variations
        assert "てづか はるむし" in variations

    def test_from_display_name_family_given(self):
        """Test parsing a display name in family-given order."""
        name = JapaneseName.from_display_name(
            "Tezuka Osamu",
            current_order=NameOrder.FAMILY_GIVEN,
        )

        assert name.family_name_romaji == "Tezuka"
        assert name.given_name_romaji == "Osamu"
        assert name.preferred_order == NameOrder.FAMILY_GIVEN

    def test_from_display_name_given_family(self):
        """Test parsing a display name in given-family order."""
        name = JapaneseName.from_display_name(
            "Osamu Tezuka",
            current_order=NameOrder.GIVEN_FAMILY,
        )

        assert name.given_name_romaji == "Osamu"
        assert name.family_name_romaji == "Tezuka"
        assert name.preferred_order == NameOrder.GIVEN_FAMILY

    def test_from_display_name_inverted(self):
        """Test parsing inverted format."""
        name = JapaneseName.from_display_name(
            "Tezuka, Osamu",
            current_order=NameOrder.FAMILY_GIVEN,
        )

        # Should handle inverted format in parsing
        assert name.family_name_romaji == "Tezuka"
        assert name.given_name_romaji == "Osamu"


class TestKanjiDisplay:
    """Test kanji/hiragana display options."""

    def test_display_with_kanji(self):
        """Test displaying name with kanji in parentheses."""
        name = JapaneseName(
            family_name_kanji="手塚",
            given_name_kanji="治虫",
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
        )

        display = name.get_display_name(include_kanji=True)
        assert "Tezuka Osamu" in display
        assert "手塚治虫" in display
        assert "(" in display
        assert ")" in display

    def test_inverted_with_kanji(self):
        """Test inverted name with kanji."""
        name = JapaneseName(
            family_name_kanji="手塚",
            given_name_kanji="治虫",
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
        )

        inverted = name.get_inverted_name(include_kanji=True)
        assert "Tezuka, Osamu" in inverted
        assert "手塚治虫" in inverted


class TestNameDetection:
    """Test language/script detection utilities."""

    def test_is_kanji(self):
        """Test kanji detection."""
        assert JapaneseNameHandler.is_likely_kanji("手塚")
        assert JapaneseNameHandler.is_likely_kanji("治虫")
        assert not JapaneseNameHandler.is_likely_kanji("Tezuka")
        assert not JapaneseNameHandler.is_likely_kanji("Osamu")

    def test_is_hiragana(self):
        """Test hiragana detection."""
        assert JapaneseNameHandler.is_hiragana("てづか")
        assert JapaneseNameHandler.is_hiragana("はるむし")
        assert not JapaneseNameHandler.is_hiragana("Tezuka")
        assert not JapaneseNameHandler.is_hiragana("テヅカ")

    def test_is_katakana(self):
        """Test katakana detection."""
        assert JapaneseNameHandler.is_katakana("テヅカ")
        assert JapaneseNameHandler.is_katakana("ハルムシ")
        assert not JapaneseNameHandler.is_katakana("てづか")
        assert not JapaneseNameHandler.is_katakana("Tezuka")

    def test_hiragana_to_katakana(self):
        """Test hiragana to katakana conversion."""
        result = JapaneseNameHandler.hiragana_to_katakana("てづか")
        assert result == "テヅカ"

    def test_katakana_to_hiragana(self):
        """Test katakana to hiragana conversion."""
        result = JapaneseNameHandler.katakana_to_hiragana("テヅカ")
        assert result == "てづか"


class TestNameParsing:
    """Test name parsing from display names."""

    def test_parse_romaji_family_given(self):
        """Test parsing romaji in family-given order."""
        name = JapaneseNameHandler.parse_japanese_name("Tezuka Osamu")

        assert name.family_name_romaji == "Tezuka"
        assert name.given_name_romaji == "Osamu"
        assert name.preferred_order == NameOrder.FAMILY_GIVEN

    def test_parse_kanji(self):
        """Test parsing kanji name."""
        name = JapaneseNameHandler.parse_japanese_name("手塚 治虫")

        assert name.family_name_kanji == "手塚"
        assert name.given_name_kanji == "治虫"
        assert name.preferred_order == NameOrder.FAMILY_GIVEN

    def test_parse_kanji_no_space(self):
        """Test parsing kanji name without space."""
        name = JapaneseNameHandler.parse_japanese_name("手塚治虫")

        assert name.family_name_kanji == "手塚治虫"

    def test_parse_inverted_format(self):
        """Test parsing inverted format."""
        name = JapaneseNameHandler.parse_japanese_name("Tezuka, Osamu")

        assert name.family_name_romaji == "Tezuka"
        assert name.given_name_romaji == "Osamu"


class TestSearchNormalization:
    """Test search normalization and matching."""

    def test_normalize_removes_spaces(self):
        """Test that normalization removes spaces."""
        normalized = JapaneseNameHandler.normalize_for_search("Tezuka Osamu")
        assert " " not in normalized
        assert normalized == "tezukaosamu"

    def test_normalize_removes_hyphens(self):
        """Test that normalization removes hyphens."""
        normalized = JapaneseNameHandler.normalize_for_search("Mary-Jane Smith")
        assert "-" not in normalized

    def test_normalize_lowercase(self):
        """Test that normalization converts to lowercase."""
        normalized = JapaneseNameHandler.normalize_for_search("TEZUKA OSAMU")
        assert normalized == normalized.lower()

    def test_normalize_removes_diacritics(self):
        """Test that normalization removes diacritics."""
        normalized = JapaneseNameHandler.normalize_for_search("José García")
        assert "é" not in normalized
        assert "í" not in normalized

    def test_find_exact_match(self):
        """Test finding exact name match."""
        name = JapaneseName(
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
        )

        results = JapaneseNameHandler.find_matching_names(
            "Tezuka Osamu",
            [name],
        )

        assert len(results) == 1
        assert results[0][1] == 1.0  # Perfect score

    def test_find_substring_match(self):
        """Test finding substring match."""
        name = JapaneseName(
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
        )

        results = JapaneseNameHandler.find_matching_names("Tezuka", [name])

        assert len(results) == 1
        assert results[0][1] > 0.5

    def test_find_given_family_match(self):
        """Test finding match with different name order."""
        name = JapaneseName(
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
        )

        results = JapaneseNameHandler.find_matching_names(
            "Osamu Tezuka",
            [name],
        )

        assert len(results) == 1
        assert results[0][1] == 1.0  # Should match the given-family variation

    def test_find_inverted_match(self):
        """Test finding match with inverted format."""
        name = JapaneseName(
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
        )

        results = JapaneseNameHandler.find_matching_names(
            "Tezuka, Osamu",
            [name],
        )

        assert len(results) == 1
        assert results[0][1] == 1.0


class TestPenNames:
    """Test pseudonym and pen name handling."""

    def test_create_pen_name_record(self):
        """Test creating a pen name record."""
        primary_name = JapaneseName(
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
        )

        pen_name = JapaneseName(
            family_name_romaji="Tezuka",
            given_name_romaji="Oomuto",  # Alternative reading
        )

        record = PenNameRecord(
            primary_name=primary_name,
            pen_names=[pen_name],
            viaf_id="59879802",
        )

        assert record.primary_name.family_name_romaji == "Tezuka"
        assert len(record.pen_names) == 1
        assert record.viaf_id == "59879802"

    def test_pen_name_record_all_names(self):
        """Test getting all names from a pen name record."""
        primary = JapaneseName(
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
        )

        pen_name = JapaneseName(
            family_name_romaji="Anonymous",
            given_name_romaji="",
        )

        real_name = JapaneseName(
            family_name_kanji="手塚",
            given_name_kanji="治虫",
        )

        record = PenNameRecord(
            primary_name=primary,
            pen_names=[pen_name],
            real_names=[real_name],
        )

        all_names = record.get_all_names()
        assert len(all_names) == 3

    def test_pen_name_serialization(self):
        """Test serializing and deserializing pen name record."""
        primary = JapaneseName(
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
        )

        record = PenNameRecord(
            primary_name=primary,
            viaf_id="59879802",
        )

        serialized = record.to_dict()
        deserialized = PenNameRecord.from_dict(serialized)

        assert deserialized.primary_name.family_name_romaji == "Tezuka"
        assert deserialized.viaf_id == "59879802"


class TestMangakaExamples:
    """Test with popular mangaka names."""

    def test_tezuka_osamu(self):
        """Test Tezuka Osamu (手塚 治虫)."""
        name = JapaneseName(
            family_name_kanji="手塚",
            given_name_kanji="治虫",
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
        )

        # Both Western and Japanese name orders should work
        display_western = name.get_display_name(order=NameOrder.GIVEN_FAMILY)
        display_japanese = name.get_display_name(order=NameOrder.FAMILY_GIVEN)

        assert display_western == "Osamu Tezuka"
        assert display_japanese == "Tezuka Osamu"

        # Search should find all variations
        results_western = JapaneseNameHandler.find_matching_names(
            "Osamu Tezuka",
            [name],
        )
        results_japanese = JapaneseNameHandler.find_matching_names(
            "Tezuka Osamu",
            [name],
        )
        results_kanji = JapaneseNameHandler.find_matching_names(
            "手塚治虫",
            [name],
        )

        assert len(results_western) == 1
        assert len(results_japanese) == 1
        assert len(results_kanji) == 1

    def test_akira_toriyama(self):
        """Test Akira Toriyama (鳥山 明)."""
        name = JapaneseName(
            family_name_kanji="鳥山",
            given_name_kanji="明",
            family_name_romaji="Toriyama",
            given_name_romaji="Akira",
        )

        variations = name.get_all_variations()

        # Should match both name orders
        assert "Toriyama Akira" in variations
        assert "Akira Toriyama" in variations
        assert "鳥山明" in variations

    def test_aoda_manga_search(self):
        """Test searching for author with both name orders."""
        # Create a catalog with popular mangaka
        mangaka = [
            JapaneseName(
                family_name_kanji="手塚",
                given_name_kanji="治虫",
                family_name_romaji="Tezuka",
                given_name_romaji="Osamu",
            ),
            JapaneseName(
                family_name_kanji="鳥山",
                given_name_kanji="明",
                family_name_romaji="Toriyama",
                given_name_romaji="Akira",
            ),
            JapaneseName(
                family_name_kanji="尾田",
                given_name_kanji="栄一郎",
                family_name_romaji="Oda",
                given_name_romaji="Eiichiro",
            ),
        ]

        # Test searching in both orders
        for author in mangaka:
            results_family_given = JapaneseNameHandler.find_matching_names(
                author.get_display_name(order=NameOrder.FAMILY_GIVEN),
                mangaka,
            )
            results_given_family = JapaneseNameHandler.find_matching_names(
                author.get_display_name(order=NameOrder.GIVEN_FAMILY),
                mangaka,
            )

            # Both should find the same author
            assert len(results_family_given) > 0
            assert len(results_given_family) > 0


class TestNameSerialization:
    """Test serialization and deserialization."""

    def test_serialize_japanese_name(self):
        """Test serializing a Japanese name."""
        name = JapaneseName(
            family_name_kanji="手塚",
            given_name_kanji="治虫",
            family_name_romaji="Tezuka",
            given_name_romaji="Osamu",
            preferred_order=NameOrder.FAMILY_GIVEN,
            preferred_romanization=RomanizationSystem.HEPBURN,
        )

        serialized = name.to_dict()

        assert serialized["family_name_kanji"] == "手塚"
        assert serialized["given_name_kanji"] == "治虫"
        assert serialized["family_name_romaji"] == "Tezuka"
        assert serialized["given_name_romaji"] == "Osamu"

    def test_deserialize_japanese_name(self):
        """Test deserializing a Japanese name."""
        data = {
            "family_name_kanji": "手塚",
            "given_name_kanji": "治虫",
            "family_name_romaji": "Tezuka",
            "given_name_romaji": "Osamu",
            "preferred_order": "family_given",
            "preferred_romanization": "hepburn",
        }

        name = JapaneseName.from_dict(data)

        assert name.family_name_kanji == "手塚"
        assert name.given_name_kanji == "治虫"
        assert name.family_name_romaji == "Tezuka"
        assert name.given_name_romaji == "Osamu"
        assert name.preferred_order == NameOrder.FAMILY_GIVEN
        assert name.preferred_romanization == RomanizationSystem.HEPBURN
