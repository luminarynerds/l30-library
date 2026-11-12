# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Floor-view websocket credential extraction.

The staff JWT must ride the ``bearer`` Sec-WebSocket-Protocol subprotocol
(``new WebSocket(url, ['bearer', token])``) so it stays out of nginx access
logs. The legacy ``?token=`` query param is accepted for one deploy cycle with
a server-side deprecation warning.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.api.v1 import computers
from app.api.v1.computers import _floor_ws_credentials


def _ws(headers: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(headers=headers or {})


def test_bearer_subprotocol_preferred_over_query_param():
    ws = _ws({"sec-websocket-protocol": "bearer, aaa.bbb.ccc"})
    assert _floor_ws_credentials(ws, "query-token") == ("aaa.bbb.ccc", "bearer")


def test_bearer_subprotocol_without_spaces():
    ws = _ws({"sec-websocket-protocol": "bearer,aaa.bbb.ccc"})
    assert _floor_ws_credentials(ws, None) == ("aaa.bbb.ccc", "bearer")


def test_legacy_query_param_still_accepted_with_deprecation_warning(monkeypatch):
    warnings: list[tuple] = []
    monkeypatch.setattr(computers.logger, "warning", lambda *a, **k: warnings.append(a))

    assert _floor_ws_credentials(_ws(), "query-token") == ("query-token", None)
    assert len(warnings) == 1
    assert "deprecated" in warnings[0][0]


def test_no_credentials_returns_none():
    assert _floor_ws_credentials(_ws(), None) == (None, None)


def test_unrelated_subprotocol_falls_back_to_query_param():
    ws = _ws({"sec-websocket-protocol": "graphql-ws"})
    assert _floor_ws_credentials(ws, "query-token") == ("query-token", None)


def test_bearer_without_token_falls_back_to_query_param():
    ws = _ws({"sec-websocket-protocol": "bearer"})
    assert _floor_ws_credentials(ws, "query-token") == ("query-token", None)
