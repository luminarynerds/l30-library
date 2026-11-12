# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from fastapi import APIRouter

from . import login, password, profile, registration, sessions, card_upgrade

router = APIRouter(prefix="/auth", tags=["auth"])
router.include_router(registration.router)
router.include_router(login.router)
router.include_router(password.router)
router.include_router(sessions.router)
router.include_router(profile.router)
router.include_router(card_upgrade.router)

# CRITICAL: Re-export auth dependencies used by dozens of other modules.
# These names are imported via `from ..auth import get_current_user` etc.
from .helpers import (
    get_current_user,
    get_optional_user,
    get_current_user_optional,
    set_refresh_token_cookie,
    generate_library_card,
    _invalidate_known_device_cache,
    log_security_event,
    add_deprecated_get_headers,
    REFRESH_TOKEN_COOKIE_NAME,
)

__all__ = [
    "router",
    "get_current_user",
    "get_optional_user",
    "get_current_user_optional",
    "set_refresh_token_cookie",
    "generate_library_card",
    "_invalidate_known_device_cache",
    "log_security_event",
    "add_deprecated_get_headers",
    "REFRESH_TOKEN_COOKIE_NAME",
]
