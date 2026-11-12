# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
import os
from io import BytesIO
from typing import Optional

logger = get_logger(__name__)

# Magic byte signatures for allowed file types
ALLOWED_SIGNATURES = {
    b'%PDF': 'application/pdf',
    b'PK\x03\x04': 'application/epub+zip',  # EPUB (ZIP-based)
    b'\x89PNG': 'image/png',
    b'\xff\xd8\xff': 'image/jpeg',
    b'GIF87a': 'image/gif',
    b'GIF89a': 'image/gif',
    b'ID3': 'audio/mpeg',                   # MP3 with ID3 tag
    b'\xff\xfb': 'audio/mpeg',              # MP3 frame sync (no ID3)
    b'\xff\xf3': 'audio/mpeg',              # MP3 frame sync (MPEG-2)
    b'OggS': 'audio/ogg',                   # Ogg container (Vorbis/Opus)
    # Note: WebP and WAV are special-cased in validate_file_type()
    # since they require checking both RIFF header AND format signature at offset 8
}

# Maximum file sizes by category (in bytes)
MAX_FILE_SIZES = {
    'manuscript': 50 * 1024 * 1024,    # 50MB for PDFs/EPUBs
    'image': 10 * 1024 * 1024,          # 10MB for images
    'document': 25 * 1024 * 1024,        # 25MB for general documents
    'print': 25 * 1024 * 1024,           # 25MB for print job uploads
    'audio': 10 * 1024 * 1024,           # 10MB for audio (nginx client_max_body_size limit)
    'default': 10 * 1024 * 1024,         # 10MB default
}

ALLOWED_EXTENSIONS = {
    '.pdf', '.epub', '.mobi',
    '.png', '.jpg', '.jpeg', '.gif', '.webp',
    '.mp3', '.wav', '.ogg', '.oga',
}


def validate_file_type(content_start: bytes, filename: str) -> Optional[str]:
    # Check extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning("Rejected file with disallowed extension: %s", ext)
        return None

    # Special case: WebP requires both RIFF header AND WEBP signature at offset 8
    # (RIFF is shared with WAV, AVI, and other formats)
    if ext == '.webp':
        if (len(content_start) >= 12 and
            content_start[:4] == b'RIFF' and
            content_start[8:12] == b'WEBP'):
            return 'image/webp'
        logger.warning(
            f"Rejected file {filename}: RIFF file without WEBP signature at offset 8"
        )
        return None

    # WAV: RIFF header + WAVE signature at offset 8
    if ext == '.wav':
        if (len(content_start) >= 12 and
            content_start[:4] == b'RIFF' and
            content_start[8:12] == b'WAVE'):
            return 'audio/wav'
        logger.warning(
            f"Rejected file {filename}: RIFF file without WAVE signature at offset 8"
        )
        return None

    # Check magic bytes for other types
    for signature, mime_type in ALLOWED_SIGNATURES.items():
        if content_start.startswith(signature):
            return mime_type

    logger.warning(
        f"Rejected file {filename}: magic bytes don't match any allowed type"
    )
    return None


def validate_file_size(size: int, category: str = 'default') -> bool:
    max_size = MAX_FILE_SIZES.get(category, MAX_FILE_SIZES['default'])
    if size > max_size:
        logger.warning(
            f"Rejected file: size {size} exceeds {category} limit of {max_size}"
        )
        return False
    return True


def extract_pdf_page_count(file_bytes: bytes) -> Optional[int]:
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(file_bytes))
        count = len(reader.pages)
        return count if count > 0 else None
    except Exception as e:  # noqa: BLE001  # pypdf parse boundary — any failure on attacker-controlled bytes returns None
        logger.warning("Failed to extract PDF page count: %s", e)
        return None


def extract_page_count(file_bytes: bytes, mime_type: str) -> Optional[int]:
    if mime_type == 'application/pdf':
        return extract_pdf_page_count(file_bytes)
    if mime_type.startswith('image/'):
        return 1
    return None
