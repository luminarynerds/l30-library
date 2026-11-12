# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.bibframe import AuthorityLink, AuthoritySource
from ..models.local_authority import (
    LocalAuthority,
    LocalAuthorityStatus,
    LocalAuthorityType,
)
from ..schemas.local_authority import (
    LocalAuthorityCreate,
    LocalAuthorityLinkRequest,
    LocalAuthorityUpdate,
)


def _normalize(label: str) -> str:
    return " ".join(label.lower().split())


def _to_jsonable(value):
    if value is None:
        return None
    if isinstance(value, list):
        return [v.model_dump() if hasattr(v, "model_dump") else v for v in value]
    return value


class LocalAuthorityService:
    async def create(
        self,
        db: AsyncSession,
        data: LocalAuthorityCreate,
        user_id: Optional[int],
    ) -> LocalAuthority:
        normalized = _normalize(data.label)
        existing = await db.execute(
            select(LocalAuthority).where(
                LocalAuthority.library_system_id == data.library_system_id,
                LocalAuthority.authority_type == data.authority_type,
                LocalAuthority.label_normalized == normalized,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An authority with this heading already exists for this type.",
            )

        if data.use_instead_id is not None:
            await self._require_exists(db, data.use_instead_id)

        record = LocalAuthority(
            library_system_id=data.library_system_id,
            authority_type=data.authority_type,
            status=data.status,
            label=data.label.strip(),
            label_normalized=normalized,
            scope_note=data.scope_note,
            source_notes=data.source_notes,
            variants=data.variants,
            related_authorities=_to_jsonable(data.related_authorities),
            external_links=_to_jsonable(data.external_links),
            use_instead_id=data.use_instead_id,
            created_by_id=user_id,
            updated_by_id=user_id,
        )
        db.add(record)
        await db.flush()
        await db.refresh(record)
        return record

    async def update(
        self,
        db: AsyncSession,
        authority_id: int,
        data: LocalAuthorityUpdate,
        user_id: Optional[int],
    ) -> LocalAuthority:
        record = await self._require_exists(db, authority_id)

        if data.label is not None:
            new_label = data.label.strip()
            new_normalized = _normalize(new_label)
            target_type = data.authority_type or record.authority_type
            conflict = await db.execute(
                select(LocalAuthority).where(
                    LocalAuthority.id != record.id,
                    LocalAuthority.library_system_id == record.library_system_id,
                    LocalAuthority.authority_type == target_type,
                    LocalAuthority.label_normalized == new_normalized,
                )
            )
            if conflict.scalar_one_or_none() is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Another authority with this heading already exists for this type.",
                )
            record.label = new_label
            record.label_normalized = new_normalized

        if data.authority_type is not None:
            record.authority_type = data.authority_type
        if data.status is not None:
            record.status = data.status
        if data.scope_note is not None:
            record.scope_note = data.scope_note
        if data.source_notes is not None:
            record.source_notes = data.source_notes
        if data.variants is not None:
            record.variants = data.variants
        if data.related_authorities is not None:
            record.related_authorities = _to_jsonable(data.related_authorities)
        if data.external_links is not None:
            record.external_links = _to_jsonable(data.external_links)
        if data.use_instead_id is not None:
            if data.use_instead_id == record.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An authority cannot supersede itself.",
                )
            await self._require_exists(db, data.use_instead_id)
            record.use_instead_id = data.use_instead_id

        record.updated_by_id = user_id
        await db.flush()
        await db.refresh(record)
        return record

    async def delete(self, db: AsyncSession, authority_id: int) -> None:
        record = await self._require_exists(db, authority_id)

        link_count = await db.execute(
            select(func.count()).select_from(AuthorityLink).where(
                AuthorityLink.source == AuthoritySource.LOCAL,
                AuthorityLink.authority_id == str(record.id),
            )
        )
        if link_count.scalar_one() > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Authority is referenced by one or more BIBFRAME entities. "
                    "Detach links or mark it deprecated instead."
                ),
            )

        await db.delete(record)
        await db.flush()

    async def get(self, db: AsyncSession, authority_id: int) -> LocalAuthority:
        return await self._require_exists(db, authority_id)

    async def search(
        self,
        db: AsyncSession,
        *,
        q: Optional[str],
        authority_type: Optional[LocalAuthorityType],
        status_filter: Optional[LocalAuthorityStatus],
        library_system_id: Optional[int],
        limit: int,
        offset: int,
    ) -> tuple[int, list[LocalAuthority]]:
        base = select(LocalAuthority)
        if q:
            needle = f"%{_normalize(q)}%"
            base = base.where(
                or_(
                    LocalAuthority.label_normalized.like(needle),
                    func.lower(func.coalesce(LocalAuthority.scope_note, "")).like(needle),
                )
            )
        if authority_type is not None:
            base = base.where(LocalAuthority.authority_type == authority_type)
        if status_filter is not None:
            base = base.where(LocalAuthority.status == status_filter)
        if library_system_id is not None:
            base = base.where(LocalAuthority.library_system_id == library_system_id)

        total = (
            await db.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        rows = (
            await db.execute(
                base.order_by(LocalAuthority.label_normalized).limit(limit).offset(offset)
            )
        ).scalars().all()
        return total, list(rows)

    async def link_to_entity(
        self,
        db: AsyncSession,
        authority_id: int,
        request: LocalAuthorityLinkRequest,
        user_id: Optional[int],
    ) -> AuthorityLink:
        record = await self._require_exists(db, authority_id)

        targets = [
            request.work_id,
            request.instance_id,
            request.item_id,
            request.contributor_id,
            request.subject_id,
        ]
        if sum(1 for t in targets if t is not None) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exactly one of work_id/instance_id/item_id/contributor_id/subject_id is required.",
            )

        link = AuthorityLink(
            source=AuthoritySource.LOCAL,
            authority_id=str(record.id),
            authority_label=record.label,
            link_type=request.link_type,
            verified=True,
            verified_by_id=user_id,
            work_id=request.work_id,
            instance_id=request.instance_id,
            item_id=request.item_id,
            contributor_id=request.contributor_id,
            subject_id=request.subject_id,
        )
        db.add(link)
        await db.flush()
        await db.refresh(link)
        return link

    async def _require_exists(self, db: AsyncSession, authority_id: int) -> LocalAuthority:
        record = await db.get(LocalAuthority, authority_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"LocalAuthority {authority_id} not found.",
            )
        return record


local_authority_service = LocalAuthorityService()
