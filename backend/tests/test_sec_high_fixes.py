# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for the board-security-highs sweep.

F3 (rate-limit client-IP spoofing): the limiter must key on the real client,
never on the client-influenceable leftmost X-Forwarded-For entry. The middleware
now delegates to the shared core.rate_limit.client_ip helper, which prefers
CF-Connecting-IP (the real client), then X-Real-IP, then the socket peer.
(Follow-up: in the two-nginx prod topology X-Real-IP is the docker gateway
constant, so CF-Connecting-IP is what actually identifies the client.)

F4 (2FA refresh tokens stored plaintext): the 2FA verify and recovery
endpoints must persist a HASHED refresh token, matching the normal login
path, so a database read never yields usable session tokens.
"""

import pathlib
from types import SimpleNamespace

from app.middleware.rate_limit_middleware import CategoryRateLimitMiddleware


def _req(headers: dict, client_host):
    return SimpleNamespace(
        headers={k.lower(): v for k, v in headers.items()},
        client=SimpleNamespace(host=client_host) if client_host else None,
    )


class TestRateLimitClientIP:
    """F3: X-Forwarded-For must not be trusted for rate-limit keying."""

    def test_spoofed_xff_is_ignored_in_favour_of_x_real_ip(self):
        req = _req(
            {"X-Forwarded-For": "1.2.3.4", "X-Real-IP": "203.0.113.9"},
            client_host="172.20.0.5",
        )
        # Attacker sets X-Forwarded-For: 1.2.3.4; must NOT become the key.
        assert CategoryRateLimitMiddleware._get_client_ip(req) == "203.0.113.9"

    def test_cf_connecting_ip_wins_over_everything(self):
        req = _req(
            {"CF-Connecting-IP": "198.51.100.1", "X-Real-IP": "203.0.113.9",
             "X-Forwarded-For": "1.2.3.4"},
            client_host="172.20.0.5",
        )
        assert CategoryRateLimitMiddleware._get_client_ip(req) == "198.51.100.1"

    def test_xff_alone_is_not_used(self):
        # No X-Real-IP: fall back to the socket peer, never the spoofable XFF.
        req = _req({"X-Forwarded-For": "1.2.3.4"}, client_host="172.20.0.5")
        assert CategoryRateLimitMiddleware._get_client_ip(req) == "172.20.0.5"

    def test_x_real_ip_used_when_present(self):
        req = _req({"X-Real-IP": "198.51.100.7"}, client_host="172.20.0.5")
        assert CategoryRateLimitMiddleware._get_client_ip(req) == "198.51.100.7"

    def test_falls_back_to_socket_peer_default_when_no_ip_available(self):
        # No CF / X-Real-IP header and no socket client -> the shared helper's
        # get_remote_address fallback returns the loopback default.
        req = _req({}, client_host=None)
        assert CategoryRateLimitMiddleware._get_client_ip(req) == "127.0.0.1"


def test_2fa_refresh_tokens_are_hashed_not_plaintext():
    """F4: neither 2FA issuance site may persist a raw refresh token."""
    src = (
        pathlib.Path(__file__).resolve().parents[1]
        / "app" / "api" / "v1" / "account_security.py"
    )
    text = src.read_text()
    # The plaintext-persistence pattern must never reappear.
    assert "token=refresh_token," not in text, (
        "account_security.py persists a raw refresh token; hash it "
        "(hash_refresh_token) to match the login path."
    )
    # Both issuance sites (2FA verify + recovery) must hash.
    assert text.count("token=hash_refresh_token(refresh_token)") == 2
