# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import re
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class ParsedLCCallNumber:

    class_letters: str
    class_number: Optional[float]
    cutter1_letter: Optional[str]
    cutter1_number: Optional[float]
    cutter2_letter: Optional[str]
    cutter2_number: Optional[float]
    cutter3_letter: Optional[str]
    cutter3_number: Optional[float]
    year: Optional[int]
    volume: Optional[str]
    copy: Optional[int]
    raw: str

    def sort_key(self) -> Tuple:
        return (
            self.class_letters or "",
            self.class_number or 0,
            self.cutter1_letter or "",
            self.cutter1_number or 0,
            self.cutter2_letter or "",
            self.cutter2_number or 0,
            self.cutter3_letter or "",
            self.cutter3_number or 0,
            self.year or 0,
            self.volume or "",
            self.copy or 0,
        )


@dataclass
class ParsedDeweyCallNumber:

    class_number: float
    cutter_letter: Optional[str]
    cutter_number: Optional[float]
    cutter2_letter: Optional[str]
    cutter2_number: Optional[float]
    year: Optional[int]
    volume: Optional[str]
    copy: Optional[int]
    raw: str

    def sort_key(self) -> Tuple:
        return (
            self.class_number,
            self.cutter_letter or "",
            self.cutter_number or 0,
            self.cutter2_letter or "",
            self.cutter2_number or 0,
            self.year or 0,
            self.volume or "",
            self.copy or 0,
        )


@dataclass
class ParsedMangaCallNumber:

    prefix: str  # GN, MANGA, COMIC
    series_name: str  # Series or author name
    volume_number: Optional[int]  # Volume number (numeric for proper sorting)
    year: Optional[int]
    copy: Optional[int]
    raw: str

    def sort_key(self) -> Tuple:
        return (
            self.prefix,  # GN, MANGA, COMIC
            self.series_name.lower(),  # Series name, case-insensitive
            self.volume_number or 0,  # Volume number (0 if not specified)
            self.year or 0,  # Year
            self.copy or 0,  # Copy number
        )


class CallNumberService:

    # LC call number regex pattern
    # Matches: PS3557.R3355 A44 2020 v.1 c.2
    LC_PATTERN = re.compile(
        r"""
        ^
        (?P<class_letters>[A-Z]{1,3})     # Class letters: A, AB, ABC
        \s*
        (?P<class_number>\d+(?:\.\d+)?)? # Class number: 123 or 123.45
        \s*
        (?:\.?(?P<cutter1>[A-Z])          # First cutter letter
        (?P<cutter1_num>\d+)?)?           # First cutter number
        \s*
        (?:\.?(?P<cutter2>[A-Z])          # Second cutter letter
        (?P<cutter2_num>\d+)?)?           # Second cutter number
        \s*
        (?:\.?(?P<cutter3>[A-Z])          # Third cutter letter
        (?P<cutter3_num>\d+)?)?           # Third cutter number
        \s*
        (?P<year>\d{4})?                  # Year
        \s*
        (?:v\.?\s*(?P<volume>\d+))?       # Volume
        \s*
        (?:c\.?\s*(?P<copy>\d+))?         # Copy number
        \s*
        $
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    # Dewey call number regex pattern
    # Matches: 813.54 S655m 2020 v.1 c.2
    DEWEY_PATTERN = re.compile(
        r"""
        ^
        (?P<class_number>\d{3}(?:\.\d+)?) # Dewey number: 813 or 813.54
        \s*
        (?:(?P<cutter1>[A-Z])              # First cutter letter
        (?P<cutter1_num>\d+)?              # First cutter number
        (?P<cutter1_work>[a-z]+)?)?        # Work letter (lowercase)
        \s*
        (?:(?P<cutter2>[A-Z])              # Second cutter letter
        (?P<cutter2_num>\d+)?)?            # Second cutter number
        \s*
        (?P<year>\d{4})?                   # Year
        \s*
        (?:v\.?\s*(?P<volume>\d+))?        # Volume
        \s*
        (?:c\.?\s*(?P<copy>\d+))?          # Copy number
        \s*
        $
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    # Manga/Graphic Novel call number regex pattern
    # Matches: GN NARUTO v.1, MANGA "Attack on Titan" v.3, COMIC Spider-Man v.42 2020
    MANGA_PATTERN = re.compile(
        r"""
        ^
        (?P<prefix>GN|MANGA|COMIC)         # Prefix: GN, MANGA, or COMIC
        \s+
        (?:["']?(?P<series_name>[^"'\d]+?)["']?)  # Series/author name
        \s*
        (?:v\.?\s*(?P<volume>\d+))?        # Volume number
        \s*
        (?P<year>\d{4})?                   # Year
        \s*
        (?:c\.?\s*(?P<copy>\d+))?          # Copy number
        \s*
        $
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    @classmethod
    def parse_lc_call_number(cls, call_number: str) -> ParsedLCCallNumber:
        call_number = call_number.strip().upper()
        match = cls.LC_PATTERN.match(call_number)

        if not match:
            # Return a minimal parsed result for non-matching strings
            return ParsedLCCallNumber(
                class_letters=call_number[:3].strip() if call_number else "",
                class_number=None,
                cutter1_letter=None,
                cutter1_number=None,
                cutter2_letter=None,
                cutter2_number=None,
                cutter3_letter=None,
                cutter3_number=None,
                year=None,
                volume=None,
                copy=None,
                raw=call_number,
            )

        # Parse cutter numbers as decimals (e.g., R3355 = 0.3355)
        def parse_cutter_num(num_str: Optional[str]) -> Optional[float]:
            if num_str:
                return float(f"0.{num_str}")
            return None

        return ParsedLCCallNumber(
            class_letters=match.group("class_letters").upper(),
            class_number=float(match.group("class_number")) if match.group("class_number") else None,
            cutter1_letter=match.group("cutter1").upper() if match.group("cutter1") else None,
            cutter1_number=parse_cutter_num(match.group("cutter1_num")),
            cutter2_letter=match.group("cutter2").upper() if match.group("cutter2") else None,
            cutter2_number=parse_cutter_num(match.group("cutter2_num")),
            cutter3_letter=match.group("cutter3").upper() if match.group("cutter3") else None,
            cutter3_number=parse_cutter_num(match.group("cutter3_num")),
            year=int(match.group("year")) if match.group("year") else None,
            volume=match.group("volume"),
            copy=int(match.group("copy")) if match.group("copy") else None,
            raw=call_number,
        )

    @classmethod
    def parse_dewey_call_number(cls, call_number: str) -> ParsedDeweyCallNumber:
        call_number = call_number.strip()
        match = cls.DEWEY_PATTERN.match(call_number)

        if not match:
            # Try to extract just the numeric part
            numeric_match = re.match(r"(\d+(?:\.\d+)?)", call_number)
            class_num = float(numeric_match.group(1)) if numeric_match else 0

            return ParsedDeweyCallNumber(
                class_number=class_num,
                cutter_letter=None,
                cutter_number=None,
                cutter2_letter=None,
                cutter2_number=None,
                year=None,
                volume=None,
                copy=None,
                raw=call_number,
            )

        # Parse cutter numbers as decimals
        def parse_cutter_num(num_str: Optional[str]) -> Optional[float]:
            if num_str:
                return float(f"0.{num_str}")
            return None

        return ParsedDeweyCallNumber(
            class_number=float(match.group("class_number")),
            cutter_letter=match.group("cutter1").upper() if match.group("cutter1") else None,
            cutter_number=parse_cutter_num(match.group("cutter1_num")),
            cutter2_letter=match.group("cutter2").upper() if match.group("cutter2") else None,
            cutter2_number=parse_cutter_num(match.group("cutter2_num")),
            year=int(match.group("year")) if match.group("year") else None,
            volume=match.group("volume"),
            copy=int(match.group("copy")) if match.group("copy") else None,
            raw=call_number,
        )

    @classmethod
    def parse_manga_call_number(cls, call_number: str) -> ParsedMangaCallNumber:
        call_number = call_number.strip()
        match = cls.MANGA_PATTERN.match(call_number)

        if not match:
            # Return a minimal parsed result for non-matching strings
            return ParsedMangaCallNumber(
                prefix="GN",
                series_name=call_number,
                volume_number=None,
                year=None,
                copy=None,
                raw=call_number,
            )

        series_name = match.group("series_name")
        if series_name:
            series_name = series_name.strip()
        else:
            series_name = ""

        volume_str = match.group("volume")
        volume_number = int(volume_str) if volume_str else None

        return ParsedMangaCallNumber(
            prefix=match.group("prefix").upper(),
            series_name=series_name,
            volume_number=volume_number,
            year=int(match.group("year")) if match.group("year") else None,
            copy=int(match.group("copy")) if match.group("copy") else None,
            raw=call_number,
        )

    @classmethod
    def is_lc_call_number(cls, call_number: str) -> bool:
        if not call_number:
            return False
        call_number = call_number.strip()
        # LC starts with letters, Dewey starts with numbers
        return bool(re.match(r"^[A-Za-z]{1,3}\s*\d", call_number))

    @classmethod
    def is_dewey_call_number(cls, call_number: str) -> bool:
        if not call_number:
            return False
        call_number = call_number.strip()
        # Dewey starts with 3 digits
        return bool(re.match(r"^\d{3}", call_number))

    @classmethod
    def is_manga_call_number(cls, call_number: str) -> bool:
        if not call_number:
            return False
        call_number = call_number.strip()
        # Manga/GN starts with GN, MANGA, or COMIC
        return bool(re.match(r"^(GN|MANGA|COMIC)\s", call_number, re.IGNORECASE))

    @classmethod
    def get_sort_key(cls, call_number: str) -> Tuple:
        if not call_number:
            return ("ZZZ", 0)  # Empty sorts to end

        if cls.is_manga_call_number(call_number):
            parsed = cls.parse_manga_call_number(call_number)
            # Prefix with 'A' to sort Manga first
            return ("A",) + parsed.sort_key()
        elif cls.is_lc_call_number(call_number):
            parsed = cls.parse_lc_call_number(call_number)
            # Prefix with 'B' to sort LC after Manga
            return ("B",) + parsed.sort_key()
        elif cls.is_dewey_call_number(call_number):
            parsed = cls.parse_dewey_call_number(call_number)
            # Prefix with 'C' to sort Dewey after LC
            return ("C",) + parsed.sort_key()
        else:
            # Unknown format - sort alphabetically at end
            return ("Z", call_number)

    @classmethod
    def sort_call_numbers(cls, call_numbers: list[str]) -> list[str]:
        return sorted(call_numbers, key=cls.get_sort_key)

    @classmethod
    def compare_call_numbers(cls, cn1: str, cn2: str) -> int:
        key1 = cls.get_sort_key(cn1)
        key2 = cls.get_sort_key(cn2)

        if key1 < key2:
            return -1
        elif key1 > key2:
            return 1
        return 0

    @classmethod
    def normalize_lc_call_number(cls, call_number: str) -> str:
        parsed = cls.parse_lc_call_number(call_number)

        parts = [parsed.class_letters]
        if parsed.class_number is not None:
            # Format number without trailing zeros after decimal
            num_str = f"{parsed.class_number:g}"
            parts.append(num_str)

        if parsed.cutter1_letter:
            cutter = f".{parsed.cutter1_letter}"
            if parsed.cutter1_number is not None:
                # Remove "0." prefix from cutter number
                cutter += str(parsed.cutter1_number)[2:]
            parts.append(cutter)

        if parsed.cutter2_letter:
            cutter = f" {parsed.cutter2_letter}"
            if parsed.cutter2_number is not None:
                cutter += str(parsed.cutter2_number)[2:]
            parts.append(cutter)

        if parsed.cutter3_letter:
            cutter = f" {parsed.cutter3_letter}"
            if parsed.cutter3_number is not None:
                cutter += str(parsed.cutter3_number)[2:]
            parts.append(cutter)

        if parsed.year:
            parts.append(f" {parsed.year}")

        if parsed.volume:
            parts.append(f" v.{parsed.volume}")

        if parsed.copy:
            parts.append(f" c.{parsed.copy}")

        return "".join(parts)

    @classmethod
    def normalize_dewey_call_number(cls, call_number: str) -> str:
        parsed = cls.parse_dewey_call_number(call_number)

        # Format the class number with proper decimal places
        parts = [f"{parsed.class_number:g}"]

        if parsed.cutter_letter:
            cutter = f" {parsed.cutter_letter}"
            if parsed.cutter_number is not None:
                cutter += str(parsed.cutter_number)[2:]
            parts.append(cutter)

        if parsed.cutter2_letter:
            cutter = f" {parsed.cutter2_letter}"
            if parsed.cutter2_number is not None:
                cutter += str(parsed.cutter2_number)[2:]
            parts.append(cutter)

        if parsed.year:
            parts.append(f" {parsed.year}")

        if parsed.volume:
            parts.append(f" v.{parsed.volume}")

        if parsed.copy:
            parts.append(f" c.{parsed.copy}")

        return "".join(parts)

    @classmethod
    def normalize_manga_call_number(cls, call_number: str) -> str:
        parsed = cls.parse_manga_call_number(call_number)

        parts = [parsed.prefix]
        parts.append(f" {parsed.series_name}")

        if parsed.volume_number is not None:
            parts.append(f" v.{parsed.volume_number}")

        if parsed.year:
            parts.append(f" {parsed.year}")

        if parsed.copy:
            parts.append(f" c.{parsed.copy}")

        return "".join(parts)

    @classmethod
    def format_manga_spine_label(cls, call_number: str) -> str:
        parsed = cls.parse_manga_call_number(call_number)

        # Multi-line format for spine labels
        lines = [parsed.prefix]
        lines.append(parsed.series_name.upper() if parsed.series_name else "")

        if parsed.volume_number is not None:
            lines.append(f"v.{parsed.volume_number}")

        return "\n".join(line for line in lines if line)

    @classmethod
    def generate_manga_call_number(
        cls,
        prefix: str,
        series_title: str,
        volume_number: Optional[int] = None,
        author_name: Optional[str] = None,
        shelve_by_series: bool = True,
    ) -> str:
        normalized_prefix = prefix.strip().upper()
        if normalized_prefix not in {"GN", "MANGA", "COMIC"}:
            raise ValueError("prefix must be GN, MANGA, or COMIC")

        if shelve_by_series:
            base = series_title.strip()
        else:
            if not author_name:
                raise ValueError("author_name is required when shelve_by_series is False")
            # Basic author cutter: first three letters of surname.
            surname = author_name.strip().split()[-1]
            base = "".join(ch for ch in surname.upper() if ch.isalpha())[:3] or surname[:3].upper()

        call_number = f"{normalized_prefix} {base}".strip()
        if volume_number is not None:
            call_number += f" v.{volume_number}"
        return call_number

    @classmethod
    def get_manga_shelving_location(cls, prefix: str, audience: str = "adult") -> str:
        normalized_prefix = prefix.strip().upper()
        normalized_audience = audience.strip().lower()

        audience_label = "Teen" if normalized_audience == "teen" else "Adult"
        suffix_map = {
            "GN": "GN",
            "MANGA": "Manga",
            "COMIC": "Comics",
        }
        if normalized_prefix not in suffix_map:
            raise ValueError("prefix must be GN, MANGA, or COMIC")

        return f"{audience_label} {suffix_map[normalized_prefix]}"

    @classmethod
    def get_browse_shelf_neighbors(
        cls,
        call_numbers: list[str],
        target_call_number: str,
        window: int = 2,
    ) -> list[str]:
        sorted_numbers = cls.sort_call_numbers(call_numbers)

        try:
            idx = sorted_numbers.index(target_call_number)
        except ValueError:
            return []

        start = max(0, idx - window)
        end = min(len(sorted_numbers), idx + window + 1)
        return sorted_numbers[start:end]

    @classmethod
    def get_shelf_location_range(
        cls,
        call_number: str,
        range_type: str = "class",
    ) -> Tuple[str, str]:
        if cls.is_lc_call_number(call_number):
            parsed = cls.parse_lc_call_number(call_number)
            letters = parsed.class_letters

            if range_type == "class":
                # Return the single-letter class
                return (letters[0], letters[0])
            elif range_type == "subclass":
                # Return the full class letters
                return (letters, letters)
            else:
                # Return the number range
                if parsed.class_number:
                    num = int(parsed.class_number)
                    start_num = (num // 100) * 100
                    end_num = start_num + 99
                    return (f"{letters}{start_num}", f"{letters}{end_num}")
                return (letters, letters)

        elif cls.is_dewey_call_number(call_number):
            parsed = cls.parse_dewey_call_number(call_number)
            num = int(parsed.class_number)

            if range_type == "class":
                # Return hundred class (000, 100, 200, etc.)
                start = (num // 100) * 100
                return (f"{start:03d}", f"{start + 99:03d}")
            elif range_type == "subclass":
                # Return ten class (010, 020, etc.)
                start = (num // 10) * 10
                return (f"{start:03d}", f"{start + 9:03d}")
            else:
                # Return unit range
                return (f"{num:03d}", f"{num:03d}")

        elif cls.is_manga_call_number(call_number):
            parsed = cls.parse_manga_call_number(call_number)

            if range_type == "class":
                # Return the prefix (GN, MANGA, COMIC)
                return (parsed.prefix, parsed.prefix)
            elif range_type == "subclass":
                # Return prefix + first letter of series
                first_letter = parsed.series_name[0].upper() if parsed.series_name else ""
                label = f"{parsed.prefix} {first_letter}"
                return (label, label)
            else:
                # Return series name range
                return (parsed.series_name, parsed.series_name)

        return (call_number, call_number)


def lc_sort_key(call_number: str) -> Tuple:
    return CallNumberService.parse_lc_call_number(call_number).sort_key()


def dewey_sort_key(call_number: str) -> Tuple:
    return CallNumberService.parse_dewey_call_number(call_number).sort_key()


def call_number_sort_key(call_number: str) -> Tuple:
    return CallNumberService.get_sort_key(call_number)
