# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import nh3

# Tags the rich-text editor can emit. h1 is intentionally excluded because
# the page <h1> is reserved for the post title.
_ALLOWED_TAGS: frozenset[str] = frozenset({
    "h2", "h3", "h4",
    "p", "ul", "ol", "li", "blockquote",
    "code", "pre", "hr", "strong", "em", "s",
    "a", "img", "br",
    "div", "span",
})

# Per-tag attribute allowlist. Anything not listed is dropped, which
# implicitly handles ``style`` and ``on*`` handlers.
_ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    "a": {"href", "target", "rel", "title"},
    "img": {"src", "alt", "title", "width", "height"},
    # Callout extension: <div data-callout-type="..." class="callout">
    "div": {"data-callout-type", "class"},
    "span": {"class"},
    # TipTap CodeBlock may emit <code class="language-X"> inside <pre>.
    "code": {"class"},
}

# URL schemes permitted on ``a[href]``. Relative URLs (no scheme) are
# always permitted by nh3; ``javascript:``, ``data:``, ``vbscript:``,
# etc. are stripped because they are not listed.
_ALLOWED_URL_SCHEMES: frozenset[str] = frozenset({"http", "https", "mailto"})


def _sanitize_html(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        # Let Pydantic's own type coercion/validation handle non-strings
        # downstream; don't silently coerce here.
        return value
    if not value:
        return value
    return nh3.clean(
        value,
        tags=set(_ALLOWED_TAGS),
        attributes={k: set(v) for k, v in _ALLOWED_ATTRIBUTES.items()},
        url_schemes=set(_ALLOWED_URL_SCHEMES),
        # Pass link_rel=None so the caller's ``rel`` attribute survives;
        # nh3's default ("noopener noreferrer") would otherwise reject
        # any explicit rel value.
        link_rel=None,
    )
