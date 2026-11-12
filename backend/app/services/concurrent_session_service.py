# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
import time
import uuid
from typing import Optional

from ..core.cache import get_redis
from ..core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

DEFAULT_SESSION_TTL_MINUTES = 30

_CHECK_AND_ADD_SCRIPT = """
redis.call("ZREMRANGEBYSCORE", KEYS[1], "-inf", ARGV[1])
local active = redis.call("ZCARD", KEYS[1])
local limit = tonumber(ARGV[4])
if active >= limit then
    return 0
end
redis.call("ZADD", KEYS[1], ARGV[2], ARGV[3])
redis.call("EXPIRE", KEYS[1], tonumber(ARGV[5]))
return 1
"""


async def check_and_acquire_session(
    subscription_id: int,
    simultaneous_users: int,
    session_ttl_minutes: Optional[int] = None,
    user_id: Optional[int] = None,
    ip_hash: Optional[str] = None,
) -> tuple[bool, int]:
    client = await get_redis()
    if client is None:
        logger.warning(
            "Redis unavailable for concurrent session check, failing open",
            extra={"subscription_id": subscription_id},
        )
        return (True, -1)

    ttl = (session_ttl_minutes or DEFAULT_SESSION_TTL_MINUTES) * 60
    now = time.time()
    expiry = now + ttl
    key = f"db_sessions:{subscription_id}"
    member = f"{user_id or ip_hash}:{uuid.uuid4().hex[:8]}"
    key_ttl = ttl + 300  # 5-minute backstop

    try:
        result = await client.eval(
            _CHECK_AND_ADD_SCRIPT,
            1,
            key,
            str(now),
            str(expiry),
            member,
            str(simultaneous_users),
            str(key_ttl),
        )
        admitted = int(result) == 1

        if not admitted:
            active_count = simultaneous_users
        else:
            active_count = await client.zcard(key)

        return (admitted, active_count)

    except Exception as e:  # noqa: BLE001 -- fail-open: Redis outage must not block patron sessions (audit only)
        logger.warning(
            "Redis error during concurrent session check, failing open",
            extra={
                "subscription_id": subscription_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        return (True, -1)


async def get_active_session_count(subscription_id: int) -> Optional[int]:
    client = await get_redis()
    if client is None:
        return None

    try:
        key = f"db_sessions:{subscription_id}"
        now = time.time()
        await client.zremrangebyscore(key, "-inf", str(now))
        return await client.zcard(key)
    except Exception:  # noqa: BLE001 -- fail-open: Redis outage returns None, caller handles
        return None
