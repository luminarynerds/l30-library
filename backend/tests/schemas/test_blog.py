# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for BlogPost schemas — server-side HTML sanitization integration."""
from __future__ import annotations

from app.schemas.blog import BlogPostCreate, BlogPostUpdate


class TestBlogPostCreateSanitization:
    def test_script_stripped_from_body(self):
        post = BlogPostCreate(body="<script>x</script><p>ok</p>", title="t")
        assert post.body == "<p>ok</p>"

    def test_script_stripped_from_tldr(self):
        post = BlogPostCreate(
            body="<p>body</p>",
            tldr="<script>x</script><p>summary</p>",
            title="t",
        )
        assert post.tldr == "<p>summary</p>"

    def test_clean_html_passes_through(self):
        body = "<p>hello <strong>world</strong></p>"
        post = BlogPostCreate(body=body, title="t")
        assert post.body == body

    def test_javascript_href_dropped_from_body(self):
        post = BlogPostCreate(
            body='<a href="javascript:alert(1)">x</a>', title="t"
        )
        assert "javascript" not in post.body
        assert "href" not in post.body

    def test_h1_dropped_h2_kept_in_body(self):
        post = BlogPostCreate(body="<h1>title</h1><h2>section</h2>", title="t")
        assert "<h1>" not in post.body
        assert "<h2>section</h2>" in post.body

    def test_callout_div_preserved(self):
        body = '<div data-callout-type="warning" class="callout"><p>note</p></div>'
        post = BlogPostCreate(body=body, title="t")
        assert 'data-callout-type="warning"' in post.body
        assert "<p>note</p>" in post.body

    def test_style_attribute_dropped(self):
        post = BlogPostCreate(body='<p style="color:red">x</p>', title="t")
        assert post.body == "<p>x</p>"

    def test_image_relative_upload_preserved(self):
        post = BlogPostCreate(
            body='<img src="/uploads/blog/x.webp" alt="cover">', title="t"
        )
        assert 'src="/uploads/blog/x.webp"' in post.body

    def test_tldr_none_stays_none(self):
        post = BlogPostCreate(body="<p>x</p>", title="t", tldr=None)
        assert post.tldr is None

    def test_empty_body_default(self):
        post = BlogPostCreate(title="t")
        assert post.body == ""


class TestBlogPostUpdateSanitization:
    def test_script_stripped_from_body(self):
        upd = BlogPostUpdate(body="<script>x</script><p>edited</p>")
        assert upd.body == "<p>edited</p>"

    def test_script_stripped_from_tldr(self):
        upd = BlogPostUpdate(tldr="<script>x</script><p>summary</p>")
        assert upd.tldr == "<p>summary</p>"

    def test_body_none_preserves_none(self):
        upd = BlogPostUpdate(title="renamed")
        assert upd.body is None

    def test_event_handler_dropped(self):
        upd = BlogPostUpdate(body='<p onclick="x">y</p>')
        assert "onclick" not in upd.body
