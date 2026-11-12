# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for server-side HTML sanitization (defense in depth)."""
from __future__ import annotations

import pytest

from app.core.sanitization import _sanitize_html


class TestSanitizeHtml:
    def test_strips_script_tag(self):
        assert _sanitize_html("<script>alert(1)</script>") == ""

    def test_keeps_p_text_drops_script(self):
        assert _sanitize_html("<script>alert(1)</script><p>ok</p>") == "<p>ok</p>"

    def test_javascript_href_dropped(self):
        out = _sanitize_html('<a href="javascript:alert(1)">x</a>')
        assert "javascript" not in out
        assert "href" not in out
        assert ">x</a>" in out

    def test_https_href_survives(self):
        out = _sanitize_html('<a href="https://example.com">x</a>')
        assert 'href="https://example.com"' in out

    def test_mailto_href_survives(self):
        out = _sanitize_html('<a href="mailto:x@y.com">x</a>')
        assert 'href="mailto:x@y.com"' in out

    def test_relative_href_survives(self):
        out = _sanitize_html('<a href="/relative">x</a>')
        assert 'href="/relative"' in out

    def test_https_img_survives(self):
        out = _sanitize_html('<img src="https://cdn/x.png" alt="x">')
        assert 'src="https://cdn/x.png"' in out
        assert 'alt="x"' in out

    def test_relative_uploads_img_survives(self):
        out = _sanitize_html('<img src="/uploads/blog/abc.webp" alt="x">')
        assert 'src="/uploads/blog/abc.webp"' in out

    def test_javascript_img_src_stripped(self):
        out = _sanitize_html('<img src="javascript:x" alt="x">')
        assert "javascript" not in out
        assert "src=" not in out
        # img tag itself + alt should survive
        assert "<img" in out
        assert 'alt="x"' in out

    def test_img_onerror_dropped_but_tag_survives(self):
        out = _sanitize_html('<img onerror="x" src="https://cdn/x.png">')
        assert "onerror" not in out
        assert 'src="https://cdn/x.png"' in out

    def test_callout_div_survives(self):
        out = _sanitize_html('<div data-callout-type="warning" class="callout">x</div>')
        assert 'data-callout-type="warning"' in out
        assert 'class="callout"' in out

    def test_style_attribute_dropped(self):
        out = _sanitize_html('<p style="color:red">x</p>')
        assert "style" not in out
        assert "color:red" not in out
        assert out == "<p>x</p>"

    def test_h1_is_dropped(self):
        # h1 is reserved for the page <h1> (post title). The tag is
        # removed but its text content is preserved.
        out = _sanitize_html("<h1>x</h1><h2>ok</h2>")
        assert "<h1>" not in out
        assert "</h1>" not in out
        assert "<h2>ok</h2>" in out

    def test_h2_h3_h4_survive(self):
        out = _sanitize_html("<h2>a</h2><h3>b</h3><h4>c</h4>")
        assert "<h2>a</h2>" in out
        assert "<h3>b</h3>" in out
        assert "<h4>c</h4>" in out

    def test_none_returns_none(self):
        assert _sanitize_html(None) is None

    def test_empty_string_returns_empty(self):
        assert _sanitize_html("") == ""

    def test_non_string_passes_through(self):
        # Pydantic should still surface a type error downstream rather
        # than us silently coercing.
        assert _sanitize_html(123) == 123  # type: ignore[arg-type]

    def test_event_handler_attribute_dropped(self):
        out = _sanitize_html('<p onclick="alert(1)">x</p>')
        assert "onclick" not in out
        assert out == "<p>x</p>"

    def test_iframe_dropped(self):
        out = _sanitize_html('<iframe src="https://evil"></iframe><p>ok</p>')
        assert "iframe" not in out
        assert "<p>ok</p>" in out

    def test_object_tag_dropped(self):
        out = _sanitize_html('<object data="evil"></object>')
        assert "object" not in out

    def test_data_url_in_img_dropped(self):
        out = _sanitize_html('<img src="data:text/html,<script>x</script>" alt="y">')
        assert "data:" not in out
        assert "script" not in out

    def test_basic_formatting_survives(self):
        out = _sanitize_html("<p><strong>bold</strong> and <em>italic</em></p>")
        assert "<strong>bold</strong>" in out
        assert "<em>italic</em>" in out

    def test_strike_survives(self):
        # StarterKit ships Strike by default; markdown shortcut works
        # even without a toolbar button, so <s> must round-trip.
        out = _sanitize_html("<s>strike</s>")
        assert out == "<s>strike</s>"

    def test_lists_survive(self):
        out = _sanitize_html("<ul><li>a</li><li>b</li></ul>")
        assert out == "<ul><li>a</li><li>b</li></ul>"

    def test_code_block_survives(self):
        out = _sanitize_html("<pre><code>foo</code></pre>")
        assert "<pre>" in out
        assert "<code>foo</code>" in out

    def test_link_rel_target_survive(self):
        out = _sanitize_html(
            '<a href="https://e.com" target="_blank" rel="noopener">x</a>'
        )
        assert 'target="_blank"' in out
        assert 'rel="noopener"' in out


@pytest.fixture
def sample_callout() -> str:
    return '<div data-callout-type="info" class="callout"><p>tip</p></div>'


def test_callout_with_nested_block(sample_callout: str) -> None:
    out = _sanitize_html(sample_callout)
    assert 'data-callout-type="info"' in out
    assert "<p>tip</p>" in out
