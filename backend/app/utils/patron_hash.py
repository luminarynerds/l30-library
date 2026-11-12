# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import hashlib
import hmac

from app.core.config import get_settings


def generate_patron_hash(user_id: int | str) -> str:
    settings = get_settings()
    key = settings.secret_key.encode()
    msg = str(user_id).encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()[:16]
