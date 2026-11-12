# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.household import HouseholdLink, HouseholdLinkStatus
from ..models.parent_onboarding import ParentOnboardingSession
from ..models.patron_consent import PatronConsent
from ..models.program_family import ProgramFamilyGroup, ProgramFamilyMember
from ..models.user import User
from ..schemas.family_snapshot import (
    FamilySnapshotMember,
    FamilySnapshotResponse,
    PatronConsentRead,
    PatronConsentStatusResponse,
)

logger = get_logger(__name__)

CONSENT_TYPE_FAMILY_SNAPSHOT = "family_snapshot"

# Map BCP-47-ish code -> language autonym for display. Kept small + in
# code (not DB) so adding a language is a one-line PR. Falls back to the
# raw code when missing.
LANGUAGE_LABELS = {
    "en": "English",
    "es": "Español",
    "vi": "Tiếng Việt",
    "zh": "中文",
    "ar": "العربية",
    "fr": "Français",
    "ko": "한국어",
    "ru": "Русский",
    "so": "Soomaali",
    "fa": "فارسی",
}

# Notes longer than this get a "..." tail in the redacted view so a
# screenshot of the snapshot does not surface sensitive household
# context. The reveal payload returns the full string.
NOTES_REDACTED_MAX = 60


def _language_label(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    return LANGUAGE_LABELS.get(code, code)


def _redact_first_name(name: str) -> str:
    if not name:
        return "?."
    return f"{name[0].upper()}."


def _redact_notes(notes: Optional[str]) -> Optional[str]:
    if not notes:
        return None
    s = notes.strip()
    if len(s) <= NOTES_REDACTED_MAX:
        return s
    # Cut on a word boundary near the cap so the truncation reads cleanly.
    cut = s[:NOTES_REDACTED_MAX].rsplit(" ", 1)[0]
    if not cut:
        cut = s[:NOTES_REDACTED_MAX]
    return f"{cut}…"


async def get_active_consent(
    db: AsyncSession,
    patron_id: int,
    consent_type: str = CONSENT_TYPE_FAMILY_SNAPSHOT,
) -> Optional[PatronConsent]:
    stmt = (
        select(PatronConsent)
        .where(
            and_(
                PatronConsent.patron_id == patron_id,
                PatronConsent.consent_type == consent_type,
                PatronConsent.revoked_at.is_(None),
            )
        )
        .order_by(PatronConsent.recorded_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_consent_status(
    db: AsyncSession,
    patron_id: int,
    consent_type: str = CONSENT_TYPE_FAMILY_SNAPSHOT,
) -> PatronConsentStatusResponse:
    active = await get_active_consent(db, patron_id, consent_type)
    if active is not None and active.granted:
        return PatronConsentStatusResponse(
            patron_id=patron_id,
            consent_status="granted",
            consent_recorded_at=active.recorded_at,
            recorded_by_staff_id=active.recorded_by_staff_id,
        )

    # No active row: check whether the patron ever had one (revoked).
    revoked_stmt = (
        select(PatronConsent)
        .where(
            and_(
                PatronConsent.patron_id == patron_id,
                PatronConsent.consent_type == consent_type,
                PatronConsent.revoked_at.is_not(None),
            )
        )
        .order_by(PatronConsent.revoked_at.desc())
        .limit(1)
    )
    revoked = (await db.execute(revoked_stmt)).scalar_one_or_none()
    if revoked is not None:
        return PatronConsentStatusResponse(
            patron_id=patron_id,
            consent_status="revoked",
            consent_recorded_at=revoked.recorded_at,
            recorded_by_staff_id=revoked.recorded_by_staff_id,
        )

    return PatronConsentStatusResponse(
        patron_id=patron_id,
        consent_status="not_requested",
    )


async def record_consent(
    db: AsyncSession,
    *,
    patron_id: int,
    granted: bool,
    recorded_by_staff_id: int,
    notes: Optional[str] = None,
    consent_type: str = CONSENT_TYPE_FAMILY_SNAPSHOT,
) -> PatronConsent:
    now = datetime.now(timezone.utc)

    existing = await get_active_consent(db, patron_id, consent_type)
    if existing is not None:
        existing.revoked_at = now

    row = PatronConsent(
        patron_id=patron_id,
        consent_type=consent_type,
        granted=granted,
        recorded_by_staff_id=recorded_by_staff_id,
        recorded_at=now,
        revoked_at=now if not granted else None,
        notes=notes,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def _load_patron_with_family(
    db: AsyncSession,
    patron_id: int,
) -> Optional[Tuple[User, Optional[ProgramFamilyGroup], List[HouseholdLink]]]:
    patron_stmt = select(User).where(User.id == patron_id)
    patron = (await db.execute(patron_stmt)).scalar_one_or_none()
    if patron is None:
        return None

    fg_stmt = (
        select(ProgramFamilyGroup)
        .where(ProgramFamilyGroup.parent_user_id == patron_id)
        .options(selectinload(ProgramFamilyGroup.members))
    )
    family_group = (await db.execute(fg_stmt)).scalar_one_or_none()

    hh_stmt = select(HouseholdLink).where(
        and_(
            HouseholdLink.target_parent_id == patron_id,
            HouseholdLink.status == HouseholdLinkStatus.APPROVED,
        )
    )
    household_links = list((await db.execute(hh_stmt)).scalars().all())

    return patron, family_group, household_links


def _build_member_rows(
    family_group: Optional[ProgramFamilyGroup],
    reveal: bool,
) -> Tuple[List[FamilySnapshotMember], int]:
    if family_group is None:
        return [], 0
    members = sorted(
        family_group.members,
        key=lambda m: (m.is_parent, m.age_range, m.first_name),
    )
    rows: List[FamilySnapshotMember] = []
    child_count = 0
    for m in members:
        if m.is_parent:
            # The spec only surfaces children in the UI list, but parents
            # in the family group count toward household size.
            continue
        child_count += 1
        rows.append(
            FamilySnapshotMember(
                first_name_revealed=m.first_name if reveal else _redact_first_name(m.first_name),
                age_range=m.age_range,
                is_parent=False,
            )
        )
    return rows, child_count


def _household_size(
    family_group: Optional[ProgramFamilyGroup],
    household_link_count: int,
) -> int:
    fg_size = 0
    if family_group is not None:
        fg_rows = len(family_group.members)
        # If the patron isn't already represented as is_parent=True, add 1.
        patron_in_group = any(m.is_parent for m in family_group.members)
        fg_size = fg_rows + (0 if patron_in_group else 1)

    link_size = household_link_count + 1 if household_link_count else 0
    return max(fg_size, link_size, 1)


async def build_family_snapshot(
    db: AsyncSession,
    *,
    session: ParentOnboardingSession,
    reveal: bool = False,
) -> FamilySnapshotResponse:
    patron_id = session.patron_id
    loaded = await _load_patron_with_family(db, patron_id)
    if loaded is None:
        # Patron row was deleted between session creation and this read.
        # Treat as consent-missing so the UI still renders something
        # sensible rather than 500ing.
        return FamilySnapshotResponse(
            patron_id=patron_id,
            consent_status="not_requested",
            sensitive_fields_hidden=True,
        )
    patron, family_group, household_links = loaded

    consent = await get_consent_status(db, patron_id)

    base_payload = {
        "patron_id": patron_id,
        "consent_status": consent.consent_status,
        "consent_recorded_at": consent.consent_recorded_at,
        "language_preference": patron.language_preference,
        "language_preference_label": _language_label(patron.language_preference),
    }

    if consent.consent_status != "granted":
        # Language preference travels regardless; everything else stays
        # hidden so a screenshot of the card can't leak minor data.
        return FamilySnapshotResponse(
            **base_payload,
            household_size=None,
            household_members=[],
            household_notes_summary=None,
            baby_age_months=None,
            sensitive_fields_hidden=True,
        )

    member_rows, _ = _build_member_rows(family_group, reveal=reveal)
    notes_source = session.family_situation_notes
    notes_for_payload = (
        notes_source if reveal else _redact_notes(notes_source)
    )

    return FamilySnapshotResponse(
        **base_payload,
        household_size=_household_size(family_group, len(household_links)),
        household_members=member_rows,
        household_notes_summary=notes_for_payload,
        baby_age_months=session.baby_age_months,
        sensitive_fields_hidden=not reveal,
    )


def to_consent_read(row: PatronConsent) -> PatronConsentRead:
    return PatronConsentRead.model_validate(row)
