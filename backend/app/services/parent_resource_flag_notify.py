# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.email import send_email
from ..models.parent_onboarding import (
    ParentResourceGuideFlag,
    ParentResourceGuideItem,
    ResourceGuideFlagReason,
)
from ..models.user import User

logger = get_logger(__name__)

# Distinct Resend tag for this notification type. See
# feedback_resend_tag_name_uniqueness -- Resend 422s on duplicate tag
# names within a single batch request.
RESEND_TAG = "parent_resource_guide_flag_filed"


# Human-readable labels for reason codes in the email body. UI labels are
# i18n-bundled and rendered client-side; staff email body is English-only
# in v1 because the recipient (the last verifier) is always a staff user
# and we don't have per-user locale on the User model yet.
_REASON_LABELS: dict[str, str] = {
    ResourceGuideFlagReason.disconnected_phone.value: "Phone number is disconnected",
    ResourceGuideFlagReason.wrong_address.value: "Address is wrong or they've moved",
    ResourceGuideFlagReason.eligibility_changed.value: "Eligibility rules have changed",
    ResourceGuideFlagReason.closed_permanently.value: "Office closed permanently",
    ResourceGuideFlagReason.other.value: "Something else",
}


def _reason_label(code: str) -> str:
    return _REASON_LABELS.get(code, code)


async def _resolve_recipient(
    db: AsyncSession,
    item: ParentResourceGuideItem,
    flagged_by_id: Optional[int],
) -> Optional[User]:
    if item.verified_by_id is None:
        return None
    if flagged_by_id is not None and item.verified_by_id == flagged_by_id:
        # Self-flag suppression per spec QO #3 (v1 silent skip).
        return None
    result = await db.execute(select(User).where(User.id == item.verified_by_id))
    return result.scalar_one_or_none()


def _render_html(
    item: ParentResourceGuideItem,
    flag: ParentResourceGuideFlag,
    queue_url: str,
) -> str:
    reason = _reason_label(flag.reason_code)
    comment_block = (
        f"<p><strong>Comment:</strong> {flag.comment}</p>" if flag.comment else ""
    )
    return f"""
<p>A parent or staff member flagged the resource <strong>{item.title}</strong>
as out of date.</p>
<p><strong>Reason:</strong> {reason}</p>
{comment_block}
<p><a href="{queue_url}">Review the flag queue</a> to triage.</p>
<p style="color: #777; font-size: 12px;">
You're receiving this because you most recently verified this resource.
</p>
""".strip()


async def notify_flag_filed(
    db: AsyncSession,
    flag: ParentResourceGuideFlag,
    flagged_by: User,
) -> bool:
    item = flag.item
    if item is None:
        # Defensive: relationship should have been loaded by the route
        # handler. If we got here without it, refuse to fire blind.
        result = await db.execute(
            select(ParentResourceGuideItem).where(
                ParentResourceGuideItem.id == flag.item_id
            )
        )
        item = result.scalar_one_or_none()
    if item is None:
        logger.warning(
            "parent_resource_flag: cannot notify, item not found",
            extra={"flag_id": flag.id, "item_id": flag.item_id},
        )
        return False

    recipient = await _resolve_recipient(db, item, flagged_by.id)
    if recipient is None:
        logger.info(
            "parent_resource_flag: no recipient (no prior verifier or self-flag)",
            extra={"flag_id": flag.id, "item_id": item.id},
        )
        return False
    if not recipient.email:
        logger.info(
            "parent_resource_flag: recipient has no email on file",
            extra={"flag_id": flag.id, "user_id": recipient.id},
        )
        return False

    # Lazy import to avoid a hard config-time dependency in tests that
    # don't exercise the email path -- config import side-effects pull in
    # the Pydantic Settings model and require a DATABASE_URL.
    from ..core.config import get_settings
    settings = get_settings()
    queue_url = f"{settings.frontend_url.rstrip('/')}/staff/parent-onboarding/resource-flags"

    subject = f'Resource flagged for review: "{item.title}"'
    html = _render_html(item, flag, queue_url)

    logger.info(
        "EMAIL_SEND parent_resource_guide_flag_filed user=%s item=%s flag=%s",
        recipient.id,
        item.id,
        flag.id,
    )
    try:
        ok = await send_email(
            to_email=recipient.email,
            subject=subject,
            html_content=html,
            categories=[RESEND_TAG],
            notification_type=RESEND_TAG,
        )
    except Exception:  # pragma: no cover -- best-effort
        logger.exception(
            "parent_resource_flag: send_email raised; swallowing",
            extra={"flag_id": flag.id, "item_id": item.id, "user_id": recipient.id},
        )
        return False

    if not ok:
        logger.warning(
            "parent_resource_flag: send_email returned False "
            "(daily cap, dedup, or transport failure)",
            extra={"flag_id": flag.id, "item_id": item.id, "user_id": recipient.id},
        )
    return bool(ok)
