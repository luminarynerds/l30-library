# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Drift-detection + structural-injection tests for the SSR helper.

_inject_meta matches head tags by SHAPE (attribute key), not by their current
content, and inserts missing tags before </head> — so a forked deployment
editing frontend/index.html copy cannot silently break SSR injection. The
drift validator only guards the structural anchors injection depends on
(<title>, </head>, <div id="root">) and logs ERROR when one is missing.
"""
import logging

import pytest

import app.api.v1.seo_meta as seo_meta


def _good_template() -> str:
    """A shell containing every structural anchor plus typical head tags."""
    return "\n".join([
        "<!DOCTYPE html><html><head>",
        "<title>Library</title>",
        '<meta property="og:title" content="L30. A complete library system. Free, open-source, yours.">',
        '<meta property="og:description" content="Tour a full working demo library. The community is fictional. The software is real.">',
        '<meta name="twitter:title" content="L30. A complete library system. Free, open-source, yours.">',
        '<meta name="twitter:description" content="Tour a full working demo library. The community is fictional. The software is real.">',
        '<meta name="description" content="L30 Library - Search the catalog, reserve a room, check your holds, find events." />',
        '<meta property="og:url" content="https://l30.org/">',
        '<meta property="og:type" content="website">',
        '<link rel="canonical" href="https://l30.org/" />',
        '<meta name="robots" content="index, follow" />',
        '<meta property="og:image" content="https://l30.org/og-image.png">',
        '<meta name="twitter:image" content="https://l30.org/og-image.png">',
        '</head><body><div id="root"></div></body></html>',
    ])


def _forked_template() -> str:
    """A tenant-customized shell: same tag shapes, entirely different copy.

    This is the shell a fork ships after editing index.html for their own
    library — the exact case the old exact-string .replace() silently broke.
    """
    return "\n".join([
        "<!DOCTYPE html><html><head>",
        "<title>Maple Falls Public Library</title>",
        '<meta property="og:title" content="Maple Falls Public Library">',
        '<meta property="og:description" content="Your community library.">',
        '<meta name="twitter:title" content="Maple Falls Public Library">',
        '<meta name="twitter:description" content="Your community library.">',
        '<meta name="description" content="Maple Falls Public Library" />',
        '<meta property="og:url" content="https://library.maplefalls.example/">',
        '<meta property="og:type" content="website">',
        '<link rel="canonical" href="https://library.maplefalls.example/" />',
        '<meta name="robots" content="index, follow" />',
        '</head><body><div id="root"></div></body></html>',
    ])


@pytest.fixture
def _stub_shell(monkeypatch):
    """Point _get_index_html at a given template string."""
    def _apply(template: str):
        async def _stubbed() -> str:
            return template
        monkeypatch.setattr(seo_meta, "_get_index_html", _stubbed)
        monkeypatch.setattr(seo_meta, "_INDEX_HTML", None)
    return _apply


# ---------------------------------------------------------------------------
# Drift validator: structural anchors only
# ---------------------------------------------------------------------------


def test_validate_passes_silently_on_good_template(caplog):
    caplog.set_level(logging.ERROR, logger="app.api.v1.seo_meta")
    seo_meta._validate_template_placeholders(_good_template())
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert errors == [], f"Unexpected error logs: {[r.getMessage() for r in errors]}"


def test_validate_passes_on_tenant_customized_copy(caplog):
    """Changed tag CONTENT (fork editing index.html) is not drift."""
    caplog.set_level(logging.ERROR, logger="app.api.v1.seo_meta")
    seo_meta._validate_template_placeholders(_forked_template())
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert errors == [], f"Unexpected error logs: {[r.getMessage() for r in errors]}"


def test_validate_logs_error_when_title_tag_missing(caplog):
    bad = _good_template().replace("<title>Library</title>", "")
    caplog.set_level(logging.ERROR, logger="app.api.v1.seo_meta")
    seo_meta._validate_template_placeholders(bad)
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) == 1
    msg = errors[0].getMessage()
    assert "SSR template drift" in msg
    assert "<title>" in msg


def test_validate_combines_all_missing_into_one_log_line(caplog):
    bad = _good_template()
    bad = bad.replace("<title>Library</title>", "")
    bad = bad.replace('<div id="root">', "<div>")
    caplog.set_level(logging.ERROR, logger="app.api.v1.seo_meta")
    seo_meta._validate_template_placeholders(bad)
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) == 1
    msg = errors[0].getMessage()
    assert "2 expected placeholder string(s) not found" in msg


def test_validate_does_not_raise_on_missing_placeholder(caplog):
    """Missing anchors must not raise — degraded SSR is acceptable, hard fail is not."""
    bad = "<html><head></head><body></body></html>"
    caplog.set_level(logging.ERROR, logger="app.api.v1.seo_meta")
    seo_meta._validate_template_placeholders(bad)
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) == 1


# ---------------------------------------------------------------------------
# Structural injection: content-independent replace + insert-if-missing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_inject_replaces_tags_regardless_of_shell_copy(_stub_shell):
    """The fork scenario: customized index.html copy still gets per-page meta."""
    _stub_shell(_forked_template())
    html = await seo_meta._inject_meta(
        "Storytime | Maple Falls",
        "Weekly storytime for ages 3-5.",
        canonical_url="https://library.maplefalls.example/events/detail/7",
        og_type="article",
    )
    assert "<title>Storytime | Maple Falls</title>" in html
    assert 'og:title" content="Storytime | Maple Falls"' in html
    assert 'og:description" content="Weekly storytime for ages 3-5."' in html
    assert 'twitter:title" content="Storytime | Maple Falls"' in html
    assert 'og:url" content="https://library.maplefalls.example/events/detail/7"' in html
    assert 'canonical" href="https://library.maplefalls.example/events/detail/7"' in html
    assert 'og:type" content="article"' in html
    # The shell's own static values are gone, not duplicated
    assert 'content="Maple Falls Public Library"' not in html
    assert 'href="https://library.maplefalls.example/" />' not in html


@pytest.mark.asyncio
async def test_inject_inserts_missing_tags_before_head_close(_stub_shell):
    """A minimal shell with no og/twitter tags gets them inserted, not dropped."""
    _stub_shell(
        "<!DOCTYPE html><html><head><title>x</title></head>"
        '<body><div id="root"></div></body></html>'
    )
    html = await seo_meta._inject_meta(
        "Inserted Title",
        "Inserted description.",
        canonical_url="https://example.org/page",
        og_type="website",
        robots="noindex,follow",
        image="https://example.org/img.png",
    )
    assert "<title>Inserted Title</title>" in html
    for expected in (
        '<meta property="og:title" content="Inserted Title" />',
        '<meta property="og:description" content="Inserted description." />',
        '<meta name="twitter:title" content="Inserted Title" />',
        '<meta name="description" content="Inserted description." />',
        '<meta property="og:url" content="https://example.org/page" />',
        '<meta property="og:type" content="website" />',
        '<link rel="canonical" href="https://example.org/page" />',
        '<meta name="robots" content="noindex,follow" />',
        '<meta property="og:image" content="https://example.org/img.png" />',
        '<meta name="twitter:image" content="https://example.org/img.png" />',
    ):
        assert expected in html, f"missing inserted tag: {expected}"
        assert html.index(expected) < html.index("</head>")


@pytest.mark.asyncio
async def test_inject_escapes_content_and_handles_regex_specials(_stub_shell):
    """Quotes/angle brackets in titles are escaped; backslashes in content
    don't corrupt output via re.sub replacement-escape rules."""
    _stub_shell(_good_template())
    html = await seo_meta._inject_meta(
        'Back\\slash & "Quotes" <Tag>',
        "desc",
        canonical_url="https://example.org/",
    )
    assert (
        "<title>Back\\slash &amp; &quot;Quotes&quot; &lt;Tag&gt;</title>" in html
    )


@pytest.mark.asyncio
async def test_inject_matches_single_quoted_and_reversed_attr_order(_stub_shell):
    """Tag-shape matching tolerates single quotes and content-first order."""
    _stub_shell(
        "<!DOCTYPE html><html><head><title>x</title>"
        "<meta property='og:title' content='old'>"
        '<meta content="old" name="twitter:title">'
        '</head><body><div id="root"></div></body></html>'
    )
    html = await seo_meta._inject_meta(
        "New", "desc", canonical_url="https://example.org/"
    )
    assert "content='old'" not in html
    assert 'content="old"' not in html
    assert 'og:title" content="New"' in html
    assert 'twitter:title" content="New"' in html
