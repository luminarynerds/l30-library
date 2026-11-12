# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.nudge import Nudge, PatronNudgeState


async def get_active_nudges_for_patron(
    db: AsyncSession,
    patron_id: int,
    page_context: str,
    nudge_frequency: str = "normal",
) -> list[dict[str, Any]]:
    if nudge_frequency == "off":
        return []

    stmt = select(Nudge).where(
        and_(
            Nudge.active == True,
            or_(
                Nudge.delivery_placement == "global",
                Nudge.delivery_placement == page_context,
            ),
        )
    )
    result = await db.execute(stmt)
    candidates = result.scalars().all()

    if not candidates:
        return []

    nudge_ids = [n.id for n in candidates]
    state_stmt = select(PatronNudgeState).where(
        and_(
            PatronNudgeState.patron_id == patron_id,
            PatronNudgeState.nudge_id.in_(nudge_ids),
        )
    )
    state_result = await db.execute(state_stmt)
    states = {s.nudge_id: s for s in state_result.scalars().all()}

    now = datetime.now(timezone.utc)
    eligible = []

    for nudge in candidates:
        state = states.get(nudge.id)
        if state:
            if state.status in ("dismissed", "acted_on"):
                continue
            if state.impressions >= nudge.max_impressions:
                continue
            elapsed = (now - state.last_shown_at).total_seconds()
            if elapsed < nudge.cooldown_seconds:
                continue

        if not _evaluate_conditions(nudge.trigger_conditions, page_context):
            continue

        eligible.append(nudge)

    eligible.sort(key=lambda n: (-n.priority, n.created_at))

    max_results = 1 if nudge_frequency == "minimal" else 3
    eligible = eligible[:max_results]

    return [
        {
            "id": n.id,
            "slug": n.slug,
            "delivery_type": n.delivery_type,
            "delivery_placement": n.delivery_placement,
            "content": {
                "title": n.content_title,
                "body": n.content_body,
                "cta_label": n.content_cta_label,
                "cta_route": n.content_cta_route,
            },
            "priority": n.priority,
        }
        for n in eligible
    ]


async def record_nudge_event(
    db: AsyncSession,
    patron_id: int,
    nudge_id: int,
    action: str,
) -> None:
    now = datetime.now(timezone.utc)

    stmt = select(PatronNudgeState).where(
        and_(
            PatronNudgeState.patron_id == patron_id,
            PatronNudgeState.nudge_id == nudge_id,
        )
    )
    result = await db.execute(stmt)
    state = result.scalar_one_or_none()

    if action == "shown":
        if state:
            state.impressions += 1
            state.last_shown_at = now
        else:
            db.add(PatronNudgeState(
                patron_id=patron_id,
                nudge_id=nudge_id,
                status="shown",
                impressions=1,
                first_shown_at=now,
                last_shown_at=now,
            ))
    elif action in ("dismissed", "acted_on"):
        # Persist the terminal status even if no prior 'shown' row exists.
        # The toast fires 'shown' and 'dismissed' as two racing async requests;
        # if 'dismissed' lands first (or 'shown' never persists), there is no
        # row to update and the dismissal would be silently dropped, so the
        # nudge keeps reappearing. Upsert so the dismissal always sticks.
        dismissed_at = now if action == "dismissed" else None
        if state:
            state.status = action
            state.dismissed_at = dismissed_at
        else:
            stmt = pg_insert(PatronNudgeState).values(
                patron_id=patron_id,
                nudge_id=nudge_id,
                status=action,
                impressions=0,
                first_shown_at=now,
                last_shown_at=now,
                dismissed_at=dismissed_at,
            ).on_conflict_do_update(
                constraint="uq_patron_nudge",
                set_={"status": action, "dismissed_at": dismissed_at},
            )
            await db.execute(stmt)

    await db.commit()


def _evaluate_conditions(conditions: list[dict], page_context: str) -> bool:
    for condition in conditions:
        ctype = condition.get("type")
        if ctype == "page_context":
            route_pattern = condition.get("route_pattern", "")
            if not page_context.startswith(route_pattern.lstrip("/")):
                return False
    return True
