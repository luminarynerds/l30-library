"""Shared helpers for event API route modules."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.logging import get_logger
from ...services.notifications.email_sender import EmailSenderService
from ...services.notifications.types import NotificationType

logger = get_logger(__name__)


def normalize_email(email: str) -> str:
    return email.lower().strip()


def ensure_aware_start(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


async def send_event_email(
    notification_type: NotificationType,
    recipient_email: str | None,
    context_data: dict,
    db: AsyncSession,
) -> None:
    if not recipient_email:
        return
    try:
        await EmailSenderService().send_templated(
            notification_type=notification_type,
            recipient_email=recipient_email,
            context_data=context_data,
            db=db,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to send event email %s: %s", notification_type, exc)


async def branch_names_by_id(db: AsyncSession, branch_ids: set[int | None]) -> dict[int, str]:
    """Resolve branch names without triggering async relationship loading."""
    wanted = {branch_id for branch_id in branch_ids if branch_id is not None}
    if not wanted:
        return {}

    from ...models.multi_branch import Branch

    result = await db.execute(select(Branch.id, Branch.name).where(Branch.id.in_(wanted)))
    return dict(result.all())
