# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse


@dataclass
class ParsedStanza:
    title: str
    url: str
    hosts: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    line_number: int = 0
    raw_lines: list[str] = field(default_factory=list)


@dataclass
class ParseWarning:
    line_number: int
    directive: str
    content: str
    reason: str


@dataclass
class ParseResult:
    stanzas: list[ParsedStanza] = field(default_factory=list)
    warnings: list[ParseWarning] = field(default_factory=list)
    total_lines: int = 0
    skipped_lines: int = 0


# Directives that generate warnings
_WARN_DIRECTIVES = frozenset({
    "includefile", "option", "group", "neverproxy",
    "httpheader", "anonymousurl", "proxy", "find",
    "replace", "cookie", "encoding",
})

# Compiled regexes
_TITLE_RE = re.compile(r"^Title\s+(.+)$", re.IGNORECASE)
_URL_RE = re.compile(r"^(?:URL|U)\s+(\S+)$", re.IGNORECASE)
_HOST_RE = re.compile(r"^(?:Host|HostJavaScript|H|HJ)\s+(\S+)$", re.IGNORECASE)
_DOMAIN_RE = re.compile(r"^(?:Domain|DJ|D)\s+(\S+)$", re.IGNORECASE)


def parse_stanza_file(content: str) -> ParseResult:
    result = ParseResult()
    lines = content.splitlines()
    result.total_lines = len(lines)

    current_stanza: Optional[ParsedStanza] = None

    for line_num, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        # Title starts a new stanza
        title_match = _TITLE_RE.match(line)
        if title_match:
            _finish_stanza(current_stanza, result)
            current_stanza = ParsedStanza(
                title=title_match.group(1).strip(),
                url="",
                line_number=line_num,
            )
            current_stanza.raw_lines.append(raw_line)
            continue

        # URL directive
        url_match = _URL_RE.match(line)
        if url_match:
            if current_stanza:
                if not current_stanza.url:
                    current_stanza.url = url_match.group(1)
                current_stanza.raw_lines.append(raw_line)
            else:
                url = url_match.group(1)
                current_stanza = ParsedStanza(
                    title=_extract_domain_name(url),
                    url=url,
                    line_number=line_num,
                )
                current_stanza.raw_lines.append(raw_line)
            continue

        # Host directive
        host_match = _HOST_RE.match(line)
        if host_match:
            if current_stanza:
                current_stanza.hosts.append(host_match.group(1))
                current_stanza.raw_lines.append(raw_line)
            continue

        # Domain directive
        domain_match = _DOMAIN_RE.match(line)
        if domain_match:
            if current_stanza:
                current_stanza.domains.append(domain_match.group(1))
                current_stanza.raw_lines.append(raw_line)
            continue

        # Warning directives
        first_word = line.split()[0].lower() if line.split() else ""
        if first_word in _WARN_DIRECTIVES:
            result.warnings.append(ParseWarning(
                line_number=line_num,
                directive=first_word,
                content=line,
                reason=f"Directive '{first_word}' not supported by importer",
            ))
            result.skipped_lines += 1
            if current_stanza:
                current_stanza.raw_lines.append(raw_line)
            continue

        # Unknown line -- skip
        result.skipped_lines += 1

    # Final stanza
    _finish_stanza(current_stanza, result)

    return result


def _finish_stanza(stanza: Optional[ParsedStanza], result: ParseResult) -> None:
    if stanza is None:
        return
    if stanza.url:
        result.stanzas.append(stanza)
    else:
        result.warnings.append(ParseWarning(
            line_number=stanza.line_number,
            directive="Title",
            content=stanza.title,
            reason="Stanza has no URL directive",
        ))


def _extract_domain_name(url: str) -> str:
    try:
        parsed = urlparse(url)
        domain = parsed.hostname or url
        for prefix in ("www.", "search.", "login.", "proxy."):
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
        return domain.split(".")[0].replace("-", " ").title()
    except (ValueError, AttributeError):
        return url[:50]
