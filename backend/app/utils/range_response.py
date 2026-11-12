# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import mimetypes
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator, List, Optional, Tuple, Union

from fastapi import HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse


# ============================================================================
# Constants
# ============================================================================

# Default chunk size for streaming (64KB)
DEFAULT_CHUNK_SIZE = 64 * 1024

# Boundary string for multipart responses
MULTIPART_BOUNDARY = "LSC_RANGE_BOUNDARY"

# Maximum number of ranges allowed in a single request
MAX_RANGES = 10


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ByteRange:
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start + 1

    def content_range_header(self, total_size: int) -> str:
        return f"bytes {self.start}-{self.end}/{total_size}"


@dataclass
class RangeRequest:
    ranges: List[ByteRange]
    is_satisfiable: bool = True
    error_message: Optional[str] = None


# ============================================================================
# Range Header Parsing
# ============================================================================

def parse_range_header(
    range_header: Optional[str],
    file_size: int
) -> RangeRequest:
    if not range_header:
        return RangeRequest(ranges=[], is_satisfiable=True)

    # Validate format: must start with "bytes="
    if not range_header.startswith("bytes="):
        return RangeRequest(
            ranges=[],
            is_satisfiable=False,
            error_message="Invalid range unit, only 'bytes' is supported"
        )

    # Extract the range specs
    range_spec = range_header[6:]  # Remove "bytes="
    range_parts = [r.strip() for r in range_spec.split(",")]

    # Limit number of ranges to prevent abuse
    if len(range_parts) > MAX_RANGES:
        return RangeRequest(
            ranges=[],
            is_satisfiable=False,
            error_message=f"Too many ranges requested (max {MAX_RANGES})"
        )

    parsed_ranges: List[ByteRange] = []

    for part in range_parts:
        byte_range = _parse_single_range(part, file_size)

        if byte_range is None:
            return RangeRequest(
                ranges=[],
                is_satisfiable=False,
                error_message=f"Invalid range format: {part}"
            )

        # Check if range is satisfiable
        if byte_range.start >= file_size:
            return RangeRequest(
                ranges=[],
                is_satisfiable=False,
                error_message=f"Range start ({byte_range.start}) exceeds file size ({file_size})"
            )

        parsed_ranges.append(byte_range)

    # Coalesce overlapping ranges
    parsed_ranges = _coalesce_ranges(parsed_ranges)

    return RangeRequest(ranges=parsed_ranges, is_satisfiable=True)


def _parse_single_range(range_spec: str, file_size: int) -> Optional[ByteRange]:
    # Match patterns: "start-end", "start-", "-suffix"
    match = re.match(r'^(\d*)-(\d*)$', range_spec.strip())

    if not match:
        return None

    start_str, end_str = match.groups()

    # Case: "-suffix" (last N bytes)
    if not start_str and end_str:
        suffix_length = int(end_str)
        if suffix_length == 0:
            return None
        start = max(0, file_size - suffix_length)
        end = file_size - 1
        return ByteRange(start=start, end=end)

    # Case: "start-" (from start to end)
    if start_str and not end_str:
        start = int(start_str)
        end = file_size - 1
        return ByteRange(start=start, end=end)

    # Case: "start-end" (explicit range)
    if start_str and end_str:
        start = int(start_str)
        end = min(int(end_str), file_size - 1)

        if start > end:
            return None

        return ByteRange(start=start, end=end)

    return None


def _coalesce_ranges(ranges: List[ByteRange]) -> List[ByteRange]:
    if not ranges:
        return []

    # Sort by start position
    sorted_ranges = sorted(ranges, key=lambda r: r.start)

    coalesced: List[ByteRange] = [sorted_ranges[0]]

    for current in sorted_ranges[1:]:
        previous = coalesced[-1]

        # Check for overlap or adjacency
        if current.start <= previous.end + 1:
            # Merge ranges
            coalesced[-1] = ByteRange(
                start=previous.start,
                end=max(previous.end, current.end)
            )
        else:
            coalesced.append(current)

    return coalesced


# ============================================================================
# ETag Generation
# ============================================================================

def generate_etag(file_path: Union[str, Path], file_size: int, mtime: float) -> str:
    # Create a hash from path, size, and mtime
    etag_data = f"{file_path}:{file_size}:{mtime}"
    etag_hash = hashlib.md5(etag_data.encode()).hexdigest()[:16]
    return f'W/"{etag_hash}"'


def check_etag_match(
    request: Request,
    etag: str
) -> Tuple[bool, bool]:
    # Check If-Match (for conditional requests)
    if_match = request.headers.get("if-match")
    if if_match:
        # "*" matches any ETag
        if if_match != "*" and if_match.strip('"') != etag.strip('W/"'):
            return (False, False)

    # Check If-None-Match (for cache validation)
    if_none_match = request.headers.get("if-none-match")
    if if_none_match:
        # "*" matches any ETag
        if if_none_match == "*" or if_none_match.strip('"') == etag.strip('W/"'):
            return (True, True)

    return (True, False)


# ============================================================================
# Streaming Generators
# ============================================================================

async def stream_file_range(
    file_path: Union[str, Path],
    start: int,
    end: int,
    chunk_size: int = DEFAULT_CHUNK_SIZE
) -> AsyncGenerator[bytes, None]:
    import aiofiles

    async with aiofiles.open(file_path, "rb") as f:
        await f.seek(start)
        remaining = end - start + 1

        while remaining > 0:
            read_size = min(chunk_size, remaining)
            chunk = await f.read(read_size)

            if not chunk:
                break

            remaining -= len(chunk)
            yield chunk


async def stream_multipart_ranges(
    file_path: Union[str, Path],
    ranges: List[ByteRange],
    file_size: int,
    media_type: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE
) -> AsyncGenerator[bytes, None]:
    import aiofiles

    boundary = MULTIPART_BOUNDARY.encode()

    async with aiofiles.open(file_path, "rb") as f:
        for i, byte_range in enumerate(ranges):
            # Send boundary
            if i == 0:
                yield b"--" + boundary + b"\r\n"
            else:
                yield b"\r\n--" + boundary + b"\r\n"

            # Send headers for this part
            yield f"Content-Type: {media_type}\r\n".encode()
            yield f"Content-Range: {byte_range.content_range_header(file_size)}\r\n".encode()
            yield b"\r\n"

            # Send content for this range
            await f.seek(byte_range.start)
            remaining = byte_range.length

            while remaining > 0:
                read_size = min(chunk_size, remaining)
                chunk = await f.read(read_size)

                if not chunk:
                    break

                remaining -= len(chunk)
                yield chunk

        # Send closing boundary
        yield b"\r\n--" + boundary + b"--\r\n"


def calculate_multipart_content_length(
    ranges: List[ByteRange],
    file_size: int,
    media_type: str
) -> int:
    boundary_length = len(MULTIPART_BOUNDARY)
    total = 0

    for i, byte_range in enumerate(ranges):
        # Boundary
        if i == 0:
            total += 2 + boundary_length + 2  # "--boundary\r\n"
        else:
            total += 2 + 2 + boundary_length + 2  # "\r\n--boundary\r\n"

        # Headers
        content_type_header = f"Content-Type: {media_type}\r\n"
        content_range_header = f"Content-Range: {byte_range.content_range_header(file_size)}\r\n"
        total += len(content_type_header)
        total += len(content_range_header)
        total += 2  # Empty line after headers

        # Content
        total += byte_range.length

    # Closing boundary
    total += 2 + 2 + boundary_length + 2 + 2  # "\r\n--boundary--\r\n"

    return total


# ============================================================================
# Response Creation
# ============================================================================

async def create_range_response(
    request: Request,
    file_path: Union[str, Path],
    media_type: Optional[str] = None,
    filename: Optional[str] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    include_etag: bool = True
) -> Response:
    file_path = Path(file_path)

    # Verify file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Get file info
    file_stat = file_path.stat()
    file_size = file_stat.st_size
    mtime = file_stat.st_mtime

    # Determine media type
    if media_type is None:
        media_type, _ = mimetypes.guess_type(str(file_path))
        media_type = media_type or "application/octet-stream"

    # Generate ETag
    etag = generate_etag(file_path, file_size, mtime) if include_etag else None

    # Check ETag conditions
    if etag:
        matches_if_match, matches_if_none_match = check_etag_match(request, etag)

        if not matches_if_match:
            raise HTTPException(
                status_code=status.HTTP_412_PRECONDITION_FAILED,
                detail="Precondition failed"
            )

        if matches_if_none_match:
            return Response(
                status_code=status.HTTP_304_NOT_MODIFIED,
                headers={
                    "ETag": etag,
                    "Accept-Ranges": "bytes"
                }
            )

    # Build common headers
    headers = {
        "Accept-Ranges": "bytes",
        "Last-Modified": _format_http_date(mtime),
    }

    if etag:
        headers["ETag"] = etag

    if filename:
        # Encode filename for Content-Disposition
        safe_filename = filename.replace('"', '\\"')
        headers["Content-Disposition"] = f'attachment; filename="{safe_filename}"'

    # Parse Range header
    range_header = request.headers.get("range")
    range_request = parse_range_header(range_header, file_size)

    # Handle unsatisfiable range
    if not range_request.is_satisfiable:
        headers["Content-Range"] = f"bytes */{file_size}"
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail=range_request.error_message or "Range not satisfiable",
            headers=headers
        )

    # No range requested - return full file
    if not range_request.ranges:
        headers["Content-Length"] = str(file_size)

        return StreamingResponse(
            content=stream_file_range(file_path, 0, file_size - 1, chunk_size),
            status_code=status.HTTP_200_OK,
            media_type=media_type,
            headers=headers
        )

    # Single range requested
    if len(range_request.ranges) == 1:
        byte_range = range_request.ranges[0]

        headers["Content-Length"] = str(byte_range.length)
        headers["Content-Range"] = byte_range.content_range_header(file_size)

        return StreamingResponse(
            content=stream_file_range(
                file_path, byte_range.start, byte_range.end, chunk_size
            ),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            media_type=media_type,
            headers=headers
        )

    # Multiple ranges requested - multipart response
    multipart_media_type = f"multipart/byteranges; boundary={MULTIPART_BOUNDARY}"
    content_length = calculate_multipart_content_length(
        range_request.ranges, file_size, media_type
    )

    headers["Content-Length"] = str(content_length)

    return StreamingResponse(
        content=stream_multipart_ranges(
            file_path, range_request.ranges, file_size, media_type, chunk_size
        ),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        media_type=multipart_media_type,
        headers=headers
    )


def _format_http_date(timestamp: float) -> str:
    from datetime import datetime, timezone

    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    # HTTP date format: Wed, 21 Oct 2015 07:28:00 GMT
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


# ============================================================================
# Convenience Functions
# ============================================================================

def supports_range_requests(request: Request) -> bool:
    return "range" in request.headers


def get_if_range_header(request: Request) -> Optional[str]:
    return request.headers.get("if-range")


async def create_range_response_for_bytes(
    request: Request,
    data: bytes,
    media_type: str = "application/octet-stream",
    filename: Optional[str] = None,
    etag: Optional[str] = None
) -> Response:
    file_size = len(data)

    # Build headers
    headers = {
        "Accept-Ranges": "bytes",
    }

    if etag:
        headers["ETag"] = etag

        # Check If-None-Match
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and (if_none_match == "*" or if_none_match.strip('"') == etag.strip('W/"')):
            return Response(
                status_code=status.HTTP_304_NOT_MODIFIED,
                headers=headers
            )

    if filename:
        safe_filename = filename.replace('"', '\\"')
        headers["Content-Disposition"] = f'attachment; filename="{safe_filename}"'

    # Parse Range header
    range_header = request.headers.get("range")
    range_request = parse_range_header(range_header, file_size)

    # Handle unsatisfiable range
    if not range_request.is_satisfiable:
        headers["Content-Range"] = f"bytes */{file_size}"
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail=range_request.error_message or "Range not satisfiable",
            headers=headers
        )

    # No range - return full content
    if not range_request.ranges:
        headers["Content-Length"] = str(file_size)
        return Response(
            content=data,
            status_code=status.HTTP_200_OK,
            media_type=media_type,
            headers=headers
        )

    # Single range
    if len(range_request.ranges) == 1:
        byte_range = range_request.ranges[0]
        content = data[byte_range.start:byte_range.end + 1]

        headers["Content-Length"] = str(byte_range.length)
        headers["Content-Range"] = byte_range.content_range_header(file_size)

        return Response(
            content=content,
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            media_type=media_type,
            headers=headers
        )

    # Multiple ranges - build multipart response
    boundary = MULTIPART_BOUNDARY.encode()
    parts = []

    for i, byte_range in enumerate(range_request.ranges):
        if i == 0:
            parts.append(b"--" + boundary + b"\r\n")
        else:
            parts.append(b"\r\n--" + boundary + b"\r\n")

        parts.append(f"Content-Type: {media_type}\r\n".encode())
        parts.append(f"Content-Range: {byte_range.content_range_header(file_size)}\r\n".encode())
        parts.append(b"\r\n")
        parts.append(data[byte_range.start:byte_range.end + 1])

    parts.append(b"\r\n--" + boundary + b"--\r\n")

    multipart_content = b"".join(parts)
    multipart_media_type = f"multipart/byteranges; boundary={MULTIPART_BOUNDARY}"

    headers["Content-Length"] = str(len(multipart_content))

    return Response(
        content=multipart_content,
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        media_type=multipart_media_type,
        headers=headers
    )
