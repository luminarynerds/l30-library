# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for the validated medium/low security batch.

Behavioral tests where cheap (turnstile fail-closed, email autoescape, XML
bomb guard); source guards for the endpoint/flow changes that would otherwise
need heavy DB/UploadFile setup.
"""

import pathlib
from types import SimpleNamespace
from unittest.mock import patch

import pytest

BACKEND = pathlib.Path(__file__).resolve().parents[1]


def _src(rel: str) -> str:
    return (BACKEND / rel).read_text()


# ---- #9 Turnstile fail-closed in production ----

@pytest.mark.asyncio
async def test_turnstile_fails_closed_in_production_when_secret_unset():
    from app.core.turnstile import verify_turnstile
    fake = SimpleNamespace(turnstile_secret_key="", environment="production")
    with patch("app.core.turnstile.get_settings", return_value=fake):
        assert await verify_turnstile("token", None) is False


@pytest.mark.asyncio
async def test_turnstile_fails_open_in_development():
    from app.core.turnstile import verify_turnstile
    fake = SimpleNamespace(turnstile_secret_key="", environment="development")
    with patch("app.core.turnstile.get_settings", return_value=fake):
        assert await verify_turnstile("token", None) is True


# ---- #11 vendor/PO email escaping ----

def test_email_env_autoescapes():
    from app.services.email_templates import _env
    assert _env.from_string("{{ x }}").render(x="<script>") == "&lt;script&gt;"


def test_render_vendor_email_escapes_vendor_name():
    from app.services.email_templates import render_vendor_email
    po = SimpleNamespace(
        vendor=SimpleNamespace(name="<script>alert(1)</script>"),
        po_number="PO-1",
        total_amount=12.5,
    )
    out = render_vendor_email(po)
    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;" in out


# ---- #12 MARCXML XXE / entity-expansion guard ----

def test_reject_xml_bombs_blocks_doctype_and_entity():
    from app.services.catalog_import import _reject_xml_bombs
    with pytest.raises(ValueError):
        _reject_xml_bombs(b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><c/>')
    with pytest.raises(ValueError):
        _reject_xml_bombs(b'<!ENTITY lol "lol">')


def test_reject_xml_bombs_blocks_oversize():
    from app.services.catalog_import import _reject_xml_bombs, _MAX_MARCXML_BYTES
    with pytest.raises(ValueError):
        _reject_xml_bombs(b"x" * (_MAX_MARCXML_BYTES + 1))


def test_reject_xml_bombs_allows_clean_marcxml():
    from app.services.catalog_import import _reject_xml_bombs
    _reject_xml_bombs(b'<?xml version="1.0"?><collection><record/></collection>')


# ---- source guards for the endpoint/flow changes ----

def test_login_uses_lowercase_lockout_attr():
    s = _src("app/api/v1/auth/login.py")
    assert "LOCKOUT_DURATION_MINUTES" not in s
    assert "settings.lockout_duration_minutes" in s


def test_login_runs_compare_before_no_password_raise():
    s = _src("app/api/v1/auth/login.py")
    assert "no_password_account = bool(user and not user.password_hash)" in s
    # old early-raise-before-compare pattern is gone (timing oracle closed)
    assert "if user and not user.password_hash:" not in s


def test_setup_gates_on_complete_and_rejects_svg():
    s = _src("app/api/v1/setup/router.py")
    assert "is_setup_complete(db)" in s
    assert "_LOGO_MIME_EXT" in s
    assert 'file.content_type.startswith("image/")' not in s


def test_panic_alert_docstring_drops_false_csrf_claim():
    s = _src("app/api/v1/panic_alert.py")
    assert "CSRF protection: Requires valid CSRF token" not in s


def test_encryption_pii_decrypt_failure_warns():
    assert 'logger.warning("Failed to decrypt PII' in _src("app/core/encryption.py")


def test_blog_upload_validates_magic_bytes():
    assert "validate_file_type(data[:16]" in _src("app/api/v1/blog.py")


def test_covers_revalidates_host_across_redirects():
    s = _src("app/api/v1/catalog/covers.py")
    assert "follow_redirects=False" in s
    assert "urljoin" in s
    assert "_ALLOWED_UPSTREAM_HOSTS" in s
