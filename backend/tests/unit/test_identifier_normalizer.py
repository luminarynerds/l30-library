# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.utils.identifier_normalizer import IdentifierNormalizer


def test_validate_isbn10_checksum_supports_x_check_digit():
    assert IdentifierNormalizer.validate_isbn_checksum("097522980X")


def test_validate_isbn10_checksum_rejects_invalid_values():
    assert not IdentifierNormalizer.validate_isbn_checksum("0975229800")


def test_validate_isbn_checksum_rejects_placeholder_zero_values():
    assert not IdentifierNormalizer.validate_isbn_checksum("0000000000")
    assert not IdentifierNormalizer.validate_isbn_checksum("0000000000000")


def test_isbn13_to_isbn10_uses_isbn10_check_algorithm():
    isbn10, isbn13 = IdentifierNormalizer.normalize_isbn("978-0-486-65088-3")

    assert isbn13 == "9780486650883"
    assert isbn10 == "048665088X"
