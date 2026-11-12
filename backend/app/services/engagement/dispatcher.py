# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.logging import get_logger
from ...models.engagement import SurveyOutcome, SurveyResponse
from ...models.learning_platform_enhanced import Badge, UserBadge
from ...models.notification import (Notification, NotificationStatus,
                                    NotificationType)
from .branching import Action

logger = get_logger(__name__)


# Action names produced by branching.evaluate_*
ACTION_SET_TRACK = "set_track"
ACTION_JUMP_TO_QUESTION = "jump_to_question"
ACTION_SERVE_REMEDIAL_LESSON = "serve_remedial_lesson"
ACTION_TRIGGER_OUTCOME = "trigger_outcome"
ACTION_AWARD_BADGE = "award_badge"

# Outcome types written to engagement_survey_outcomes
OUTCOME_BADGE_AWARDED = "badge_awarded"
OUTCOME_PEER_TIP = "peer_tip_shown"
OUTCOME_REMEDIAL_QUEUED = "remedial_lesson_queued"
OUTCOME_CIVIC_EMAIL = "civic_email_sent"
OUTCOME_TRACK_ASSIGNED = "track_assigned"


async def _award_badge(
    db: AsyncSession,
    response: SurveyResponse,
    badge_slug: str,
) -> SurveyOutcome:
    if response.user_id is None:
        return _outcome(response, OUTCOME_BADGE_AWARDED, target=badge_slug,
                        status="failed", error="anonymous response")

    badge = (await db.execute(
        select(Badge).where(Badge.name == badge_slug, Badge.is_active.is_(True))
    )).scalar_one_or_none()
    if badge is None:
        return _outcome(response, OUTCOME_BADGE_AWARDED, target=badge_slug,
                        status="failed", error="badge not found")

    already = (await db.execute(
        select(UserBadge.id).where(
            UserBadge.user_id == response.user_id,
            UserBadge.badge_id == badge.id,
        )
    )).scalar_one_or_none()
    if already:
        return _outcome(response, OUTCOME_BADGE_AWARDED, target=badge_slug,
                        status="sent", error=None)

    user_badge = UserBadge(
        user_id=response.user_id,
        badge_id=badge.id,
        earned_for=f"survey response #{response.id}",
        context_data={"survey_id": response.survey_id,
                      "response_id": response.id},
    )
    db.add(user_badge)
    return _outcome(response, OUTCOME_BADGE_AWARDED, target=badge_slug,
                    status="sent")


async def _send_civic_notification(
    db: AsyncSession,
    response: SurveyResponse,
    target_url: str,
) -> SurveyOutcome:
    if response.user_id is None:
        return _outcome(response, OUTCOME_CIVIC_EMAIL, target=target_url,
                        status="failed", error="anonymous response")

    notification = Notification(
        user_id=response.user_id,
        notification_type=NotificationType.TRAINING_NEW_CONTENT,
        status=NotificationStatus.PENDING,
        subject="Your next step: get involved with local AI policy",
        message=(
            "Thanks for completing the engagement survey. Based on your "
            "interest, here is a link to your local AI Task Force or city "
            f"board: {target_url}"
        ),
        context_data={
            "survey_response_id": response.id,
            "survey_id": response.survey_id,
            "civic_link": target_url,
        },
    )
    db.add(notification)
    await db.flush()  # need notification.id for outcome.notification_id

    outcome = _outcome(response, OUTCOME_CIVIC_EMAIL, target=target_url,
                       status="queued")
    outcome.notification_id = notification.id
    return outcome


def _outcome(
    response: SurveyResponse,
    outcome_type: str,
    *,
    target: Optional[str] = None,
    status: str = "queued",
    error: Optional[str] = None,
) -> SurveyOutcome:
    return SurveyOutcome(
        response_id=response.id,
        outcome_type=outcome_type,
        target=target,
        status=status,
        error=error,
    )


async def apply_actions(
    db: AsyncSession,
    response: SurveyResponse,
    actions: List[Action],
) -> List[SurveyOutcome]:
    outcomes: List[SurveyOutcome] = []

    for action in actions:
        if action.action_type == ACTION_SET_TRACK:
            track = action.payload.get("track")
            if track:
                response.derived_track = str(track)[:50]
                outcomes.append(
                    _outcome(response, OUTCOME_TRACK_ASSIGNED, target=track,
                             status="sent")
                )

        elif action.action_type == ACTION_AWARD_BADGE:
            slug = action.payload.get("badge")
            if slug:
                outcomes.append(await _award_badge(db, response, slug))

        elif action.action_type == ACTION_SERVE_REMEDIAL_LESSON:
            lesson_id = action.payload.get("lesson_id")
            if lesson_id is not None:
                outcomes.append(
                    _outcome(response, OUTCOME_REMEDIAL_QUEUED,
                             target=str(lesson_id), status="queued")
                )

        elif action.action_type == ACTION_JUMP_TO_QUESTION:
            qid = action.payload.get("question_id")
            outcomes.append(
                _outcome(response, "jump_to_question",
                         target=str(qid) if qid is not None else None,
                         status="sent")
            )

        elif action.action_type == ACTION_TRIGGER_OUTCOME:
            outcome_type = action.payload.get("outcome_type")
            target = action.payload.get("target")
            if outcome_type == OUTCOME_CIVIC_EMAIL and target:
                outcomes.append(
                    await _send_civic_notification(db, response, target)
                )
            elif outcome_type:
                outcomes.append(
                    _outcome(response, outcome_type, target=target,
                             status="sent")
                )

        else:
            logger.warning(
                "engagement: unknown action_type=%s response_id=%s",
                action.action_type, response.id,
            )

    for outcome in outcomes:
        if outcome.id is None and outcome not in db.new:
            db.add(outcome)
    return outcomes
