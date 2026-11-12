# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.websocket import redact_websocket_url


def test_redact_websocket_url_redacts_token_query_param():
    url = "ws://localhost:8000/api/v1/ws/patron?token=secret-token&channels=all"

    result = redact_websocket_url(url)

    assert "token=%5BREDACTED%5D" in result
    assert "channels=all" in result
    assert "secret-token" not in result


def test_redact_websocket_url_leaves_non_sensitive_params_unchanged():
    url = "wss://example.com/ws?channels=holds&foo=bar"

    result = redact_websocket_url(url)

    assert result == url


def test_redact_websocket_url_redacts_multiple_sensitive_params_case_insensitive():
    url = "wss://example.com/ws?Token=abc&access_token=def&AUTH=ghi"

    result = redact_websocket_url(url)

    assert "Token=%5BREDACTED%5D" in result
    assert "access_token=%5BREDACTED%5D" in result
    assert "AUTH=%5BREDACTED%5D" in result
    assert "abc" not in result
    assert "def" not in result
    assert "ghi" not in result
