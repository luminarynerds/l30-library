# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.branding import branding
from ....core.database import get_db
from ....core.rate_limit import client_ip
from ....models.user import User, UserRole
from .helpers import get_current_user, log_security_event

logger = get_logger(__name__)

router = APIRouter(tags=["card-management"])


def _generate_full_card() -> str:
    import secrets
    import string

    alphabet = string.ascii_uppercase + string.digits
    part1 = ''.join(secrets.choice(alphabet) for _ in range(4))
    part2 = ''.join(secrets.choice(alphabet) for _ in range(4))
    return f"{branding.CARD_PREFIX}-{part1}-{part2}"


@router.post("/staff/upgrade-card/{patron_id}")
async def upgrade_patron_card(
    patron_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upgrade a patron's temporary card to a full library card.

    Requires staff, admin, or director role.
    """
    ip_address = client_ip(request)

    # Authorization: staff+ only
    allowed_roles = {UserRole.STAFF, UserRole.ADMIN, UserRole.DIRECTOR, UserRole.SUPER_ADMIN}
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Card upgrades require a staff account. Please ask a librarian for help.",
        )

    # Load patron
    result = await db.execute(select(User).where(User.id == patron_id))
    patron = result.scalar_one_or_none()

    if not patron:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="We couldn't find a patron with that information. Please check and try again.",
        )

    if patron.card_type == "full":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This patron already has a full library card.",
        )

    # Upgrade
    old_card = patron.library_card
    patron.library_card = _generate_full_card()
    patron.card_type = "full"
    patron.card_trial_expires_at = None
    patron.card_upgraded_at = datetime.now(timezone.utc)
    patron.card_upgraded_by_id = current_user.id

    await db.commit()

    log_security_event(
        "CARD_UPGRADED",
        user_id=patron.id,
        email=patron.email,
        ip_address=ip_address,
        details={
            "old_card": old_card,
            "new_card": patron.library_card,
            "upgraded_by": current_user.id,
        },
    )

    return {
        "message": "Card upgraded successfully.",
        "library_card": patron.library_card,
        "card_type": patron.card_type,
    }
