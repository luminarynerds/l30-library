"""RFC 5545 formatting primitives shared by event calendar endpoints."""

from datetime import datetime, timezone


def escape_ical(text: str | None) -> str:
    if not text:
        return ""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def fold_ical(line: str) -> str:
    encoded = line.encode("utf-8")
    if len(encoded) <= 75:
        return line

    parts: list[bytes] = []
    remaining = encoded
    first = True
    while remaining:
        chunk_size = 75 if first else 74
        chunk = remaining[:chunk_size]
        while chunk:
            try:
                chunk.decode("utf-8")
                break
            except UnicodeDecodeError:
                chunk = chunk[:-1]
        if not chunk:
            chunk = remaining[:1]
        parts.append((b"\r\n " if not first else b"") + chunk)
        remaining = remaining[len(chunk) :]
        first = False
    return b"".join(parts).decode("utf-8")


def format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.strftime("%Y%m%dT%H%M%SZ")
