# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import re
from typing import Optional, Tuple


class IdentifierNormalizer:

    @staticmethod
    def normalize_isbn(isbn: str) -> Tuple[Optional[str], Optional[str]]:
        if not isbn:
            return None, None

        # Clean input: remove hyphens, spaces, but keep X for check digit
        isbn_clean = re.sub(r"[^0-9Xx]", "", str(isbn))

        isbn_10 = None
        isbn_13 = None

        # Check if it's a valid 13-digit ISBN
        if len(isbn_clean) == 13 and isbn_clean.isdigit():
            if IdentifierNormalizer.validate_isbn_checksum(isbn_clean):
                isbn_13 = isbn_clean
                # Try to convert to ISBN-10
                if isbn_clean.startswith("978"):
                    isbn_10 = IdentifierNormalizer._isbn13_to_isbn10(isbn_clean)

        # Check if it's a valid 10-digit ISBN
        elif len(isbn_clean) == 10:
            # Check digit may be X for 10-digit ISBNs
            if isbn_clean[:9].isdigit() and (isbn_clean[-1].isdigit() or isbn_clean[-1] in "Xx"):
                if IdentifierNormalizer.validate_isbn_checksum(isbn_clean):
                    isbn_10 = isbn_clean.upper()
                    # Convert to ISBN-13
                    isbn_13 = IdentifierNormalizer._isbn10_to_isbn13(isbn_clean)

        return isbn_10, isbn_13

    @staticmethod
    def validate_isbn_checksum(isbn: str) -> bool:
        isbn = str(isbn).strip().upper()

        if len(isbn) == 10:
            # ISBN-10 checksum validation
            if not re.match(r'^\d{9}[0-9X]$', isbn):
                return False

            # Guard against placeholder values like 0000000000
            if isbn == "0000000000":
                return False

            total = 0
            for i, digit in enumerate(isbn[:9]):
                total += int(digit) * (10 - i)

            check_digit = isbn[9]
            check_digit_val = 10 if check_digit == 'X' else int(check_digit)

            # ISBN-10 is valid when weighted sum (including check digit) is divisible by 11
            total += check_digit_val
            return total % 11 == 0

        elif len(isbn) == 13:
            # ISBN-13 checksum validation
            if not isbn.isdigit():
                return False

            # Guard against placeholder values like 0000000000000
            if isbn == "0000000000000":
                return False

            total = 0
            for i, digit in enumerate(isbn[:12]):
                weight = 1 if i % 2 == 0 else 3
                total += int(digit) * weight

            check_digit = int(isbn[12])
            calculated_check = (10 - (total % 10)) % 10
            return check_digit == calculated_check

        return False

    @staticmethod
    def _isbn10_to_isbn13(isbn10: str) -> Optional[str]:
        if len(isbn10) != 10:
            return None

        # Remove check digit from ISBN-10, add 978 prefix
        isbn12 = "978" + isbn10[:-1]

        # Calculate new check digit
        total = 0
        for i, digit in enumerate(isbn12):
            if digit.isdigit():
                weight = 1 if i % 2 == 0 else 3
                total += int(digit) * weight

        check = (10 - (total % 10)) % 10
        return isbn12 + str(check)

    @staticmethod
    def _isbn13_to_isbn10(isbn13: str) -> Optional[str]:
        if not isbn13.startswith("978"):
            return None

        # Remove 978 prefix and previous check digit
        isbn9 = isbn13[3:-1]

        # Calculate ISBN-10 check digit
        total = 0
        for i, digit in enumerate(isbn9):
            if digit.isdigit():
                total += int(digit) * (10 - i)

        check = (11 - (total % 11)) % 11
        if check == 10:
            return isbn9 + "X"
        return isbn9 + str(check)

    @staticmethod
    def normalize_lccn(lccn: str) -> str:
        if not lccn:
            return ""
        return re.sub(r"\s+", "", str(lccn))

    @staticmethod
    def normalize_issn(issn: str) -> str:
        if not issn:
            return ""

        # Remove all non-alphanumeric characters
        issn_clean = re.sub(r"[^0-9Xx]", "", str(issn))

        # Validate: should be 8 characters
        if len(issn_clean) != 8:
            return ""

        # Check that first 7 are digits and last is digit or X
        if not (issn_clean[:7].isdigit() and (issn_clean[7].isdigit() or issn_clean[7] in "Xx")):
            return ""

        # Return in standard format
        return f"{issn_clean[:4]}-{issn_clean[4:].upper()}"

    @staticmethod
    def normalize_oclc(oclc: str) -> Optional[str]:
        if not oclc:
            return None

        # Extract numeric portion
        oclc_str = str(oclc).strip()

        # Remove (OCoLC) prefix if present
        oclc_str = re.sub(r"^\(OCoLC\)", "", oclc_str)

        # Remove common prefixes
        oclc_str = re.sub(r"^(ocm|ocn|on)", "", oclc_str)

        # Extract only digits
        digits = re.sub(r"\D", "", oclc_str)

        return digits if digits else None


# Singleton convenience functions for import
def normalize_isbn(isbn: str) -> Tuple[Optional[str], Optional[str]]:
    return IdentifierNormalizer.normalize_isbn(isbn)


def normalize_lccn(lccn: str) -> str:
    return IdentifierNormalizer.normalize_lccn(lccn)


def normalize_issn(issn: str) -> str:
    return IdentifierNormalizer.normalize_issn(issn)


def validate_isbn_checksum(isbn: str) -> bool:
    return IdentifierNormalizer.validate_isbn_checksum(isbn)
