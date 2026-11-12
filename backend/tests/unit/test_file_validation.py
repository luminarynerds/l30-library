# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for file upload validation utilities.

Validates magic-byte checking, extension validation, and file size enforcement
implemented in backend/app/core/file_validation.py.
"""
import pytest

from app.core.file_validation import (
    ALLOWED_EXTENSIONS,
    ALLOWED_SIGNATURES,
    MAX_FILE_SIZES,
    validate_file_type,
    validate_file_size,
)


# ---------------------------------------------------------------------------
# Magic-byte fixtures
# ---------------------------------------------------------------------------

PDF_MAGIC = b"%PDF-1.7 fake pdf content beyond 16 bytes"
EPUB_MAGIC = b"PK\x03\x04" + b"\x00" * 12  # ZIP-based EPUB
JPEG_MAGIC = b"\xff\xd8\xff\xe0" + b"\x00" * 12
PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
GIF87A_MAGIC = b"GIF87a" + b"\x00" * 10
GIF89A_MAGIC = b"GIF89a" + b"\x00" * 10
WEBP_MAGIC = b"RIFF" + b"\x00" * 4 + b"WEBP"  # Proper WebP: RIFF header + size + WEBP signature

# Malicious / disallowed magic bytes
EXE_MAGIC = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
ELF_MAGIC = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8
RANDOM_MAGIC = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f"


# ---------------------------------------------------------------------------
# validate_file_type - accepted files
# ---------------------------------------------------------------------------

class TestValidateFileTypeAccepted:
    """Files with correct extension AND matching magic bytes should be accepted."""

    def test_pdf_magic_bytes_accepted(self):
        result = validate_file_type(PDF_MAGIC, "manuscript.pdf")
        assert result == "application/pdf"

    def test_epub_magic_bytes_accepted(self):
        result = validate_file_type(EPUB_MAGIC, "book.epub")
        assert result == "application/epub+zip"

    def test_jpeg_magic_bytes_accepted(self):
        result = validate_file_type(JPEG_MAGIC, "cover.jpg")
        assert result == "image/jpeg"

    def test_jpeg_extension_accepted(self):
        result = validate_file_type(JPEG_MAGIC, "cover.jpeg")
        assert result == "image/jpeg"

    def test_png_magic_bytes_accepted(self):
        result = validate_file_type(PNG_MAGIC, "image.png")
        assert result == "image/png"

    def test_gif87a_magic_bytes_accepted(self):
        result = validate_file_type(GIF87A_MAGIC, "animation.gif")
        assert result == "image/gif"

    def test_gif89a_magic_bytes_accepted(self):
        result = validate_file_type(GIF89A_MAGIC, "animation.gif")
        assert result == "image/gif"

    def test_webp_magic_bytes_accepted(self):
        result = validate_file_type(WEBP_MAGIC, "photo.webp")
        assert result == "image/webp"


# ---------------------------------------------------------------------------
# validate_file_type - rejected files
# ---------------------------------------------------------------------------

class TestValidateFileTypeRejected:
    """Files with bad extension or mismatched magic bytes should be rejected."""

    def test_exe_magic_bytes_rejected(self):
        """An EXE file (even with .pdf extension) must be rejected."""
        result = validate_file_type(EXE_MAGIC, "malware.pdf")
        assert result is None

    def test_elf_magic_bytes_rejected(self):
        result = validate_file_type(ELF_MAGIC, "binary.pdf")
        assert result is None

    def test_disallowed_extension_rejected(self):
        """A .exe extension must be rejected regardless of content."""
        result = validate_file_type(PDF_MAGIC, "file.exe")
        assert result is None

    def test_disallowed_extension_sh_rejected(self):
        result = validate_file_type(PDF_MAGIC, "script.sh")
        assert result is None

    def test_disallowed_extension_bat_rejected(self):
        result = validate_file_type(PDF_MAGIC, "script.bat")
        assert result is None

    def test_disallowed_extension_dll_rejected(self):
        result = validate_file_type(RANDOM_MAGIC, "library.dll")
        assert result is None

    def test_pdf_extension_with_exe_magic_rejected(self):
        """A file named .pdf but containing EXE magic bytes must be rejected."""
        result = validate_file_type(EXE_MAGIC, "trojan.pdf")
        assert result is None

    def test_jpg_extension_with_exe_magic_rejected(self):
        result = validate_file_type(EXE_MAGIC, "trojan.jpg")
        assert result is None

    def test_random_bytes_with_allowed_extension_rejected(self):
        """Random content with an allowed extension should be rejected."""
        result = validate_file_type(RANDOM_MAGIC, "document.pdf")
        assert result is None

    def test_empty_content_rejected(self):
        result = validate_file_type(b"", "empty.pdf")
        assert result is None

    def test_no_extension_rejected(self):
        result = validate_file_type(PDF_MAGIC, "noextension")
        assert result is None

    def test_wav_file_as_webp_rejected(self):
        """A WAV file (RIFF+WAVE) with .webp extension must be rejected.

        This validates the fix for the WebP validation bypass where only the
        RIFF header was checked, allowing WAV files to pass as WebP images.
        """
        wav_magic = b"RIFF" + b"\x00" * 4 + b"WAVE"  # WAV file structure
        result = validate_file_type(wav_magic, "audio.webp")
        assert result is None


# ---------------------------------------------------------------------------
# validate_file_size
# ---------------------------------------------------------------------------

class TestValidateFileSize:
    """File size limits must be enforced per category."""

    def test_manuscript_within_limit(self):
        assert validate_file_size(10 * 1024 * 1024, "manuscript") is True

    def test_manuscript_at_limit(self):
        assert validate_file_size(50 * 1024 * 1024, "manuscript") is True

    def test_manuscript_over_limit(self):
        assert validate_file_size(50 * 1024 * 1024 + 1, "manuscript") is False

    def test_image_within_limit(self):
        assert validate_file_size(5 * 1024 * 1024, "image") is True

    def test_image_over_limit(self):
        assert validate_file_size(10 * 1024 * 1024 + 1, "image") is False

    def test_document_within_limit(self):
        assert validate_file_size(20 * 1024 * 1024, "document") is True

    def test_document_over_limit(self):
        assert validate_file_size(25 * 1024 * 1024 + 1, "document") is False

    def test_default_category_within_limit(self):
        assert validate_file_size(5 * 1024 * 1024, "default") is True

    def test_default_category_over_limit(self):
        assert validate_file_size(10 * 1024 * 1024 + 1, "default") is False

    def test_unknown_category_uses_default(self):
        """An unknown category should fall back to the default limit."""
        assert validate_file_size(10 * 1024 * 1024, "unknown_category") is True
        assert validate_file_size(10 * 1024 * 1024 + 1, "unknown_category") is False

    def test_zero_size_allowed(self):
        assert validate_file_size(0, "image") is True

    def test_negative_size_allowed(self):
        # Edge case: negative sizes should technically pass (no lower bound)
        assert validate_file_size(-1, "image") is True
