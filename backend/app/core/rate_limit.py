# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import get_settings

settings = get_settings()


def client_ip(request: Request) -> str:
    """Best-effort real client IP -- the single source of truth for rate-limit
    keys, audit logging, and device fingerprinting.

    Resolution order, most-trusted first:

    1. CF-Connecting-IP -- set by Cloudflare to the real client. Trustworthy
       because the nginx allowlist restricts ingress to Cloudflare IPs; without
       that allowlist a client could spoof it.
    2. X-Real-IP -- a reverse proxy sets this to the socket peer and overwrites
       any client value, so it is not spoofable (used for non-Cloudflare
       ingress / dev). NB: in the current two-nginx prod topology the inner
       nginx re-sets X-Real-IP to its own peer (the docker gateway), so this
       branch is only a fallback for when CF-Connecting-IP is absent.
    3. The socket peer.

    We deliberately do NOT trust X-Forwarded-For: nginx appends to it
    (proxy_add_x_forwarded_for), so its leftmost entry is attacker-controlled.
    request.client.host is likewise spoofable here (ProxyHeadersMiddleware
    unwinds that same X-Forwarded-For chain), so prefer this helper anywhere the
    value drives a security decision or is written to an audit record.
    """
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return get_remote_address(request)


def _client_identity(request: Request) -> str:
    return client_ip(request)


# Use Redis as the shared storage backend for distributed rate limiting.
# The ``redis://`` URI tells the ``limits`` library (used internally by
# slowapi) to use Redis. Falls back to in-memory if the URI is empty.
_storage_uri = settings.redis_url if settings.redis_url else "memory://"


class ResilientLimiter(Limiter):
    """Limiter that degrades gracefully when Redis is unreachable instead of
    returning HTTP 500 on rate-limited routes (e.g. POST /auth/login during a
    Redis outage or Docker network drift).

    Two slowapi behaviors combine to 500 a request when Redis is down:

    1. ``limiter.hit()`` raises ``redis.ConnectionError``. ``swallow_errors``
       (set on the limiter below) suppresses that, allowing the request
       through (fail-open).
    2. But slowapi's async wrapper then unconditionally reads
       ``request.state.view_rate_limit``, which is only set on the success
       path, so a swallowed error resurfaces as a secondary ``AttributeError``
       and still 500s. Setting the attribute defensively here closes that gap.

    During an outage the per-route slowapi limit fails open; the global
    rate_limit_middleware (which has its own in-memory fallback) keeps
    enforcing limits. When Redis is healthy, behavior (including 429s) is
    unchanged.
    """

    def _check_request_limit(self, request, endpoint_func, in_middleware=True):
        try:
            super()._check_request_limit(request, endpoint_func, in_middleware)
        finally:
            if not hasattr(request.state, "view_rate_limit"):
                request.state.view_rate_limit = None


limiter = ResilientLimiter(
    key_func=_client_identity,
    storage_uri=_storage_uri,
    strategy="fixed-window",
    enabled=settings.rate_limit_enabled,
    # Fail open when Redis is unreachable instead of raising ConnectionError,
    # which otherwise surfaces as a 500 on decorated routes like POST
    # /auth/login. Requires ResilientLimiter (above) to also avoid the
    # secondary view_rate_limit AttributeError. Normal limiting is unaffected
    # when Redis is healthy.
    swallow_errors=True,
)
