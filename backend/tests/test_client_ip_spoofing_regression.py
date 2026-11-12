# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Security regression: security-sensitive client IP comes from CF-Connecting-IP,
not the spoofable request.client.host / X-Forwarded-For chain.

Finding #3: ProxyHeadersMiddleware(trusted_hosts=["*"]) makes
request.client.host reflect the client-appended X-Forwarded-For chain (nginx
uses proxy_add_x_forwarded_for, which appends), so a caller can forge it. The
auth audit log and the 2FA trusted-device hash (app/api/v1/auth/login.py) read
that value. They now use core.rate_limit.client_ip, which prefers
CF-Connecting-IP (nginx restricts ingress to Cloudflare, so it is trustworthy),
matching the enforcing slowapi rate limiter's key source.
"""

from starlette.requests import Request

from app.core.rate_limit import client_ip
from app.core.totp import compute_device_hash


def _req(headers: dict, client=("172.20.0.1", 5432)) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw, "client": client})


def test_cf_connecting_ip_wins_over_spoofed_xff():
    r = _req({"cf-connecting-ip": "203.0.113.7", "x-forwarded-for": "6.6.6.6, 172.20.0.1"})
    assert client_ip(r) == "203.0.113.7"


def test_uses_x_real_ip_and_never_spoofable_xff_when_no_cf():
    # No Cloudflare header: X-Real-IP is used and the (spoofable) leftmost
    # X-Forwarded-For entry is ignored entirely.
    r = _req({"x-real-ip": "198.51.100.7", "x-forwarded-for": "6.6.6.6, 172.20.0.1"})
    assert client_ip(r) == "198.51.100.7"


def test_xff_is_never_trusted():
    # Only X-Forwarded-For present -> fall through to the socket peer, NOT the
    # attacker-controlled XFF value.
    r = _req({"x-forwarded-for": "6.6.6.6, 172.20.0.1"}, client=("172.20.0.1", 5432))
    assert client_ip(r) == "172.20.0.1"


def test_falls_back_to_socket_peer_when_no_headers():
    r = _req({}, client=("192.0.2.5", 9999))
    assert client_ip(r) == "192.0.2.5"


def test_device_hash_stable_under_xff_spoof_when_cf_present():
    """The 2FA trusted-device hash must not change when an attacker forges
    X-Forwarded-For, so a stolen device hash can't be replayed from another IP
    by header injection and a victim's real device stays keyed to CF-Connecting-IP."""
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    honest = _req({"cf-connecting-ip": "203.0.113.7"})
    spoofed = _req({"cf-connecting-ip": "203.0.113.7", "x-forwarded-for": "6.6.6.6"})
    assert compute_device_hash(ua, client_ip(honest)) == compute_device_hash(ua, client_ip(spoofed))


def test_client_ip_identity_helper_delegates():
    """_client_identity (rate-limit key) and client_ip share one source of truth."""
    from app.core.rate_limit import _client_identity
    r = _req({"cf-connecting-ip": "203.0.113.7"})
    assert _client_identity(r) == client_ip(r) == "203.0.113.7"
