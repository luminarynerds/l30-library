# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.ebook_checkout_log import EbookCheckoutLog

logger = get_logger(__name__)


async def log_ebook_event(
    db: AsyncSession,
    user_id: int,
    source: str,
    action: str,
    ebook_title: str,
    ebook_author: str = "",
    source_ref_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    entry = EbookCheckoutLog(
        user_id=user_id,
        source=source,
        action=action,
        ebook_title=ebook_title,
        ebook_author=ebook_author,
        source_ref_id=source_ref_id,
        metadata_=metadata,
    )
    db.add(entry)
    logger.debug("ebook_log: user=%s source=%s action=%s title=%s", user_id, source, action, ebook_title)
