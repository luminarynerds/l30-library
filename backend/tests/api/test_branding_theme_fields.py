# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the theme fields on GET /branding (Task 10):

logo_url, display_font, body_font, secondary_color, surface_color,
ink_color, nav_style.
"""

import pytest

from app.models.library_branding import LibraryBranding


@pytest.mark.asyncio
async def test_branding_returns_theme_fields_when_set(client, test_db):
    row = LibraryBranding(
        id=1,
        library_name="Orange Public Library",
        logo_url="https://example.org/logo.svg",
        display_font="Cormorant Garamond",
        body_font="",
        secondary_color="#0F1F3D",
        surface_color="#FBF7EE",
        ink_color="#26221C",
        nav_style="needs-based",
    )
    test_db.add(row)
    await test_db.commit()

    resp = await client.get("/api/v1/branding")
    assert resp.status_code == 200
    body = resp.json()

    assert body["logo_url"] == "https://example.org/logo.svg"
    assert body["display_font"] == "Cormorant Garamond"
    assert body["body_font"] == ""
    assert body["secondary_color"] == "#0F1F3D"
    assert body["surface_color"] == "#FBF7EE"
    assert body["ink_color"] == "#26221C"
    assert body["nav_style"] == "needs-based"


@pytest.mark.asyncio
async def test_branding_theme_fields_default_when_unset(client):
    """No DB row at all -- must fall back to today's look, not crash."""
    resp = await client.get("/api/v1/branding")
    assert resp.status_code == 200
    body = resp.json()

    assert body["logo_url"] == ""
    assert body["display_font"] == ""
    assert body["body_font"] == ""
    assert body["secondary_color"] == ""
    assert body["surface_color"] == ""
    assert body["ink_color"] == ""
    assert body["nav_style"] == "default"
