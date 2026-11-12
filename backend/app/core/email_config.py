# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional, Tuple

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)


def resolve_marketing_email_key(
    db_email_marketing_config: Optional[dict],
) -> Tuple[Optional[str], str]:
    settings = get_settings()
    env_key = (settings.resend_api_key or "").strip()

    db_key = ""
    if db_email_marketing_config:
        # NOTE: "sendgrid_api_key" is a legacy DB field name retained for
        # backward compatibility with existing org configurations. The value
        # it holds is the Resend API key; renaming the field requires a
        # data migration to rewrite stored configs.
        raw = db_email_marketing_config.get("sendgrid_api_key") or ""
        if isinstance(raw, str):
            db_key = raw.strip()

    if env_key:
        if db_key and db_key != env_key:
            logger.warning(
                "marketing.email.config.split",
                extra={"env_len": len(env_key), "db_len": len(db_key)},
            )
        return env_key, "env"

    if db_key:
        return db_key, "db"

    return None, "none"
