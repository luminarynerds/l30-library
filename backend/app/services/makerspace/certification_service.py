# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.makerspace import (
    MakerspaceCertificationType, MakerspaceCertification,
    CertificationStatus,
)
from .base_service import BaseMakerspaceService

logger = get_logger(__name__)

QUIZ_MAX_ATTEMPTS = 3


class CertificationService(BaseMakerspaceService[MakerspaceCertification]):

    model = MakerspaceCertification

    @staticmethod
    async def get_certification_types(
        db: AsyncSession,
        is_active: bool = True
    ) -> list[MakerspaceCertificationType]:
        result = await db.execute(
            select(MakerspaceCertificationType)
            .where(MakerspaceCertificationType.is_active == is_active)
            .order_by(MakerspaceCertificationType.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_certification_type_by_id(
        db: AsyncSession,
        cert_type_id: int
    ) -> MakerspaceCertificationType | None:
        result = await db.execute(
            select(MakerspaceCertificationType)
            .where(MakerspaceCertificationType.id == cert_type_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_certification_type(
        db: AsyncSession,
        data: dict
    ) -> MakerspaceCertificationType:
        cert_type = MakerspaceCertificationType(**data)
        db.add(cert_type)
        await db.commit()
        await db.refresh(cert_type)
        return cert_type

    @staticmethod
    async def get_user_certifications(
        db: AsyncSession,
        user_id: int,
        status: CertificationStatus | None = None
    ) -> list[MakerspaceCertification]:
        query = select(MakerspaceCertification).where(
            MakerspaceCertification.user_id == user_id
        )
        if status:
            query = query.where(MakerspaceCertification.status == status)

        result = await db.execute(
            query.options(selectinload(MakerspaceCertification.certification_type))
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_certification(
        db: AsyncSession,
        certification_id: int
    ) -> MakerspaceCertification | None:
        result = await db.execute(
            select(MakerspaceCertification)
            .options(selectinload(MakerspaceCertification.certification_type))
            .where(MakerspaceCertification.id == certification_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def check_user_certified(
        db: AsyncSession,
        user_id: int,
        certification_type_id: int
    ) -> bool:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(MakerspaceCertification)
            .where(MakerspaceCertification.user_id == user_id)
            .where(MakerspaceCertification.certification_type_id == certification_type_id)
            .where(MakerspaceCertification.status == CertificationStatus.active)
            .where(
                or_(
                    MakerspaceCertification.expires_at.is_(None),
                    MakerspaceCertification.expires_at > now
                )
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def start_certification(
        db: AsyncSession,
        user_id: int,
        certification_type_id: int
    ) -> MakerspaceCertification:
        # Check for existing pending/active certification
        existing = await db.execute(
            select(MakerspaceCertification)
            .where(MakerspaceCertification.user_id == user_id)
            .where(MakerspaceCertification.certification_type_id == certification_type_id)
            .where(MakerspaceCertification.status.in_([
                CertificationStatus.pending,
                CertificationStatus.active
            ]))
        )
        if existing.scalar_one_or_none():
            raise ValueError("User already has a pending or active certification")

        certification = MakerspaceCertification(
            user_id=user_id,
            certification_type_id=certification_type_id,
            status=CertificationStatus.pending
        )
        db.add(certification)
        await db.commit()
        await db.refresh(certification)
        return certification

    @staticmethod
    async def complete_training(
        db: AsyncSession,
        certification: MakerspaceCertification
    ) -> MakerspaceCertification:
        certification.training_completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(certification)
        return certification

    @staticmethod
    async def submit_quiz(
        db: AsyncSession,
        certification: MakerspaceCertification,
        score: int
    ) -> tuple[MakerspaceCertification, bool]:
        cert_type = await CertificationService.get_certification_type_by_id(
            db, certification.certification_type_id
        )

        certification.quiz_score = score
        certification.quiz_attempts += 1

        passed = score >= (cert_type.passing_score if cert_type else 80)

        if passed:
            certification.status = CertificationStatus.active
            certification.certified_at = datetime.now(timezone.utc)

            # Set expiration if applicable
            if cert_type and cert_type.validity_months > 0:
                certification.expires_at = datetime.now(timezone.utc) + timedelta(
                    days=cert_type.validity_months * 30
                )
        elif certification.quiz_attempts >= QUIZ_MAX_ATTEMPTS:
            certification.status = CertificationStatus.expired
            logger.warning(
                "Patron exhausted quiz attempts",
                extra={"certification_id": certification.id, "attempts": certification.quiz_attempts},
            )

        await db.commit()
        await db.refresh(certification)
        return certification, passed

    @staticmethod
    async def certify_user(
        db: AsyncSession,
        certification: MakerspaceCertification,
        certified_by_id: int,
        notes: str | None = None
    ) -> MakerspaceCertification:
        cert_type = await CertificationService.get_certification_type_by_id(
            db, certification.certification_type_id
        )

        certification.status = CertificationStatus.active
        certification.certified_at = datetime.now(timezone.utc)
        certification.certified_by_id = certified_by_id
        certification.training_completed_at = datetime.now(timezone.utc)

        if notes:
            certification.notes = notes

        if cert_type and cert_type.validity_months > 0:
            certification.expires_at = datetime.now(timezone.utc) + timedelta(
                days=cert_type.validity_months * 30
            )

        await db.commit()
        await db.refresh(certification)
        return certification

    @staticmethod
    async def suspend_certification(
        db: AsyncSession,
        certification: MakerspaceCertification,
        suspended_by_id: int,
        reason: str
    ) -> MakerspaceCertification:
        certification.status = CertificationStatus.suspended
        certification.suspended_at = datetime.now(timezone.utc)
        certification.suspended_by_id = suspended_by_id
        certification.suspended_reason = reason
        await db.commit()
        await db.refresh(certification)
        return certification

    @staticmethod
    async def reinstate_certification(
        db: AsyncSession,
        certification: MakerspaceCertification,
        notes: str | None = None
    ) -> MakerspaceCertification:
        certification.status = CertificationStatus.active
        certification.suspended_at = None
        certification.suspended_reason = None
        if notes:
            certification.notes = (certification.notes or "") + f"\nReinstated: {notes}"
        await db.commit()
        await db.refresh(certification)
        return certification

    @staticmethod
    async def check_expiring_certifications(
        db: AsyncSession,
        days_before: int = 30
    ) -> list[MakerspaceCertification]:
        deadline = datetime.now(timezone.utc) + timedelta(days=days_before)
        result = await db.execute(
            select(MakerspaceCertification)
            .options(
                selectinload(MakerspaceCertification.user),
                selectinload(MakerspaceCertification.certification_type)
            )
            .where(MakerspaceCertification.status == CertificationStatus.active)
            .where(MakerspaceCertification.expires_at.isnot(None))
            .where(MakerspaceCertification.expires_at <= deadline)
            .where(MakerspaceCertification.expires_at > datetime.now(timezone.utc))
        )
        return list(result.scalars().all())
