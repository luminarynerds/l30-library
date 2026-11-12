# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import re
from typing import Optional, Dict, List, Tuple, Any
from enum import StrEnum


class NameOrder(StrEnum):
    FAMILY_GIVEN = "family_given"  # Japanese standard: 手塚 治虫
    GIVEN_FAMILY = "given_family"  # Western standard: Osamu Tezuka


class RomanizationSystem(StrEnum):
    HEPBURN = "hepburn"  # Modified Hepburn: Tezuka Osamu
    NIHON = "nihon"  # Nihon-shiki: Tezuka Osamu (similar for names)
    KUNREI = "kunrei"  # Kunrei-shiki: Tezuka Osamu (similar for names)


class JapaneseName:

    def __init__(
        self,
        family_name_kanji: Optional[str] = None,
        given_name_kanji: Optional[str] = None,
        family_name_hiragana: Optional[str] = None,
        given_name_hiragana: Optional[str] = None,
        family_name_romaji: Optional[str] = None,
        given_name_romaji: Optional[str] = None,
        preferred_order: NameOrder = NameOrder.FAMILY_GIVEN,
        preferred_romanization: RomanizationSystem = RomanizationSystem.HEPBURN,
    ):
        self.family_name_kanji = family_name_kanji
        self.given_name_kanji = given_name_kanji
        self.family_name_hiragana = family_name_hiragana
        self.given_name_hiragana = given_name_hiragana
        self.family_name_romaji = family_name_romaji
        self.given_name_romaji = given_name_romaji
        self.preferred_order = preferred_order
        self.preferred_romanization = preferred_romanization

    @classmethod
    def from_display_name(
        cls,
        display_name: str,
        current_order: NameOrder = NameOrder.FAMILY_GIVEN,
    ) -> 'JapaneseName':
        instance = cls()
        display_name = display_name.strip()

        # Handle inverted "Family, Given" format (see parse_japanese_name for
        # the same handling): a plain whitespace split would otherwise leave
        # the comma stuck to the family name ("Tezuka,").
        if "," in display_name:
            parts = [p.strip() for p in display_name.split(",")]
        else:
            parts = display_name.split()

        if len(parts) >= 2:
            if current_order == NameOrder.FAMILY_GIVEN:
                instance.family_name_romaji = parts[0]
                instance.given_name_romaji = parts[1]
            else:  # GIVEN_FAMILY
                instance.given_name_romaji = parts[0]
                instance.family_name_romaji = parts[1]
        elif len(parts) == 1:
            # Single name - treat as full name
            instance.family_name_romaji = display_name

        instance.preferred_order = current_order
        return instance

    def get_display_name(
        self,
        order: Optional[NameOrder] = None,
        include_kanji: bool = False,
    ) -> str:
        order = order or self.preferred_order
        family = self.family_name_romaji or ""
        given = self.given_name_romaji or ""

        if not family and not given:
            return ""

        if order == NameOrder.FAMILY_GIVEN:
            name = f"{family} {given}".strip()
        else:  # GIVEN_FAMILY
            name = f"{given} {family}".strip()

        if include_kanji:
            kanji_parts = []
            if self.family_name_kanji:
                kanji_parts.append(self.family_name_kanji)
            if self.given_name_kanji:
                kanji_parts.append(self.given_name_kanji)

            if kanji_parts:
                kanji = "".join(kanji_parts)
                name = f"{name} ({kanji})"

        return name

    def get_inverted_name(self, include_kanji: bool = False) -> str:
        family = self.family_name_romaji or ""
        given = self.given_name_romaji or ""

        if not family and not given:
            return ""

        name = f"{family}, {given}".strip(",").strip()

        if include_kanji and (self.family_name_kanji or self.given_name_kanji):
            kanji_parts = []
            if self.family_name_kanji:
                kanji_parts.append(self.family_name_kanji)
            if self.given_name_kanji:
                kanji_parts.append(self.given_name_kanji)
            kanji = "".join(kanji_parts)
            name = f"{name} ({kanji})"

        return name

    def get_sort_name(self) -> str:
        return self.get_inverted_name(include_kanji=False)

    def get_all_variations(self) -> List[str]:
        variations = set()

        # Romaji versions
        if self.family_name_romaji and self.given_name_romaji:
            # Family-given order
            variations.add(f"{self.family_name_romaji} {self.given_name_romaji}")
            variations.add(f"{self.family_name_romaji} {self.given_name_romaji}".lower())

            # Given-family order (Western)
            variations.add(f"{self.given_name_romaji} {self.family_name_romaji}")
            variations.add(f"{self.given_name_romaji} {self.family_name_romaji}".lower())

            # Inverted format
            variations.add(f"{self.family_name_romaji}, {self.given_name_romaji}")
            variations.add(f"{self.family_name_romaji}, {self.given_name_romaji}".lower())

        # Kanji versions
        if self.family_name_kanji and self.given_name_kanji:
            variations.add(f"{self.family_name_kanji}{self.given_name_kanji}")
            variations.add(f"{self.family_name_kanji} {self.given_name_kanji}")

        # Hiragana versions
        if self.family_name_hiragana and self.given_name_hiragana:
            variations.add(f"{self.family_name_hiragana}{self.given_name_hiragana}")
            variations.add(f"{self.family_name_hiragana} {self.given_name_hiragana}")

        # Individual parts
        if self.family_name_romaji:
            variations.add(self.family_name_romaji)
            variations.add(self.family_name_romaji.lower())
        if self.given_name_romaji:
            variations.add(self.given_name_romaji)
            variations.add(self.given_name_romaji.lower())

        return list(variations)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "family_name_kanji": self.family_name_kanji,
            "given_name_kanji": self.given_name_kanji,
            "family_name_hiragana": self.family_name_hiragana,
            "given_name_hiragana": self.given_name_hiragana,
            "family_name_romaji": self.family_name_romaji,
            "given_name_romaji": self.given_name_romaji,
            "preferred_order": self.preferred_order.value,
            "preferred_romanization": self.preferred_romanization.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JapaneseName':
        return cls(
            family_name_kanji=data.get("family_name_kanji"),
            given_name_kanji=data.get("given_name_kanji"),
            family_name_hiragana=data.get("family_name_hiragana"),
            given_name_hiragana=data.get("given_name_hiragana"),
            family_name_romaji=data.get("family_name_romaji"),
            given_name_romaji=data.get("given_name_romaji"),
            preferred_order=NameOrder(data.get("preferred_order", "family_given")),
            preferred_romanization=RomanizationSystem(data.get("preferred_romanization", "hepburn")),
        )


class JapaneseNameHandler:

    # Common Japanese kanji characters for last names
    COMMON_FAMILY_KANJI = {
        "田", "中", "山", "佐", "鈴", "高", "木", "渡", "三", "石",
        "手", "塚", "藤", "岡", "井", "川", "河", "小", "大", "村",
        "水", "火", "土", "金", "木", "日", "月", "星", "海", "山",
    }

    @staticmethod
    def is_likely_kanji(text: str) -> bool:
        if not text:
            return False

        # Kanji Unicode ranges: CJK Unified Ideographs (4E00-9FFF)
        kanji_pattern = re.compile(r'[\u4E00-\u9FFF]')
        return bool(kanji_pattern.search(text))

    @staticmethod
    def is_hiragana(text: str) -> bool:
        if not text:
            return False
        hiragana_pattern = re.compile(r'^[\u3040-\u309F]+$')
        return bool(hiragana_pattern.match(text))

    @staticmethod
    def is_katakana(text: str) -> bool:
        if not text:
            return False
        katakana_pattern = re.compile(r'^[\u30A0-\u30FF]+$')
        return bool(katakana_pattern.match(text))

    @staticmethod
    def hiragana_to_katakana(text: str) -> str:
        if not text:
            return text

        hiragana_chars = "ぁあぃいぅうぇえぉおかがきぎくぐけげこさざしじすずせぜそただちぢつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもやゃゆゅよらりるれろわをん"
        katakana_chars = "ァアィイゥウェエォオカガキギクグケゲコサザシジスズセゼソタダチヂツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモヤャユュヨラリルレロワヲン"

        trans_table = str.maketrans(hiragana_chars, katakana_chars)
        return text.translate(trans_table)

    @staticmethod
    def katakana_to_hiragana(text: str) -> str:
        if not text:
            return text

        katakana_chars = "ァアィイゥウェエォオカガキギクグケゲコサザシジスズセゼソタダチヂツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモヤャユュヨラリルレロワヲン"
        hiragana_chars = "ぁあぃいぅうぇえぉおかがきぎくぐけげこさざしじすずせぜそただちぢつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもやゃゆゅよらりるれろわをん"

        trans_table = str.maketrans(katakana_chars, hiragana_chars)
        return text.translate(trans_table)

    @classmethod
    def parse_japanese_name(
        cls,
        display_name: str,
    ) -> JapaneseName:
        name_obj = JapaneseName()
        display_name = display_name.strip()

        if not display_name:
            return name_obj

        # Check if it contains kanji
        if cls.is_likely_kanji(display_name):
            # Japanese format
            parts = display_name.split()
            if len(parts) >= 2:
                name_obj.family_name_kanji = parts[0]
                name_obj.given_name_kanji = parts[1]
            else:
                name_obj.family_name_kanji = display_name
            name_obj.preferred_order = NameOrder.FAMILY_GIVEN
        else:
            # Romaji format
            # Handle inverted format "Lastname, Firstname"
            if "," in display_name:
                parts = [p.strip() for p in display_name.split(",")]
                if len(parts) >= 2:
                    name_obj.family_name_romaji = parts[0]
                    name_obj.given_name_romaji = parts[1]
                    name_obj.preferred_order = NameOrder.FAMILY_GIVEN
            else:
                parts = display_name.split()
                if len(parts) >= 2:
                    # Assume family-given order for now (can be adjusted with context)
                    name_obj.family_name_romaji = parts[0]
                    name_obj.given_name_romaji = parts[1]
                    name_obj.preferred_order = NameOrder.FAMILY_GIVEN
                else:
                    name_obj.family_name_romaji = display_name

        return name_obj

    @staticmethod
    def normalize_for_search(text: str) -> str:
        if not text:
            return ""

        # Remove spaces and hyphens
        text = text.replace(" ", "").replace("-", "").replace("　", "")

        # Lowercase for comparison
        text = text.lower()

        # Basic diacritic removal (é -> e, etc.)
        diacritics_map = {
            'á': 'a', 'à': 'a', 'ä': 'a',
            'é': 'e', 'è': 'e', 'ë': 'e',
            'í': 'i', 'ì': 'i', 'ï': 'i',
            'ó': 'o', 'ò': 'o', 'ö': 'o',
            'ú': 'u', 'ù': 'u', 'ü': 'u',
        }
        for diacritic, base in diacritics_map.items():
            text = text.replace(diacritic, base)

        return text

    @staticmethod
    def find_matching_names(
        search_term: str,
        japanese_names: List[JapaneseName],
    ) -> List[Tuple[JapaneseName, float]]:
        normalized_search = JapaneseNameHandler.normalize_for_search(search_term)
        results = []

        for name in japanese_names:
            variations = name.get_all_variations()
            max_score = 0.0

            for variation in variations:
                normalized_var = JapaneseNameHandler.normalize_for_search(variation)

                # Exact match
                if normalized_var == normalized_search:
                    max_score = max(max_score, 1.0)
                # Substring match
                elif normalized_search in normalized_var:
                    max_score = max(max_score, 0.8)
                # Partial match
                elif normalized_var.startswith(normalized_search):
                    max_score = max(max_score, 0.6)

            if max_score > 0:
                results.append((name, max_score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results


# Pseudonym/pen name mapping
class PenNameRecord:

    def __init__(
        self,
        primary_name: JapaneseName,
        pen_names: Optional[List[JapaneseName]] = None,
        real_names: Optional[List[JapaneseName]] = None,
        viaf_id: Optional[str] = None,
        lcnaf_id: Optional[str] = None,
    ):
        self.primary_name = primary_name
        self.pen_names = pen_names or []
        self.real_names = real_names or []
        self.viaf_id = viaf_id
        self.lcnaf_id = lcnaf_id

    def get_all_names(self) -> List[JapaneseName]:
        return [self.primary_name] + self.pen_names + self.real_names

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_name": self.primary_name.to_dict(),
            "pen_names": [name.to_dict() for name in self.pen_names],
            "real_names": [name.to_dict() for name in self.real_names],
            "viaf_id": self.viaf_id,
            "lcnaf_id": self.lcnaf_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PenNameRecord':
        return cls(
            primary_name=JapaneseName.from_dict(data["primary_name"]),
            pen_names=[JapaneseName.from_dict(n) for n in data.get("pen_names", [])],
            real_names=[JapaneseName.from_dict(n) for n in data.get("real_names", [])],
            viaf_id=data.get("viaf_id"),
            lcnaf_id=data.get("lcnaf_id"),
        )
