# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff content-translations editor.

Flat cross-content-type view over the JSONB ``translations`` column on
rooms, tech_help_options, legal_topics, and staff_shelves, so a staff
translator can fill in one language without hopping between admin pages.
"""
from dataclasses import dataclass
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.legal.taxonomy import LegalTopic
from ....models.room import Room
from ....models.staff_shelves import StaffShelf
from ....models.tech_support import TechHelpOption
from ....models.user import User
from ..dependencies import require_staff

router = APIRouter(prefix="/staff/content-translations", tags=["staff-content-translations"])


@dataclass(frozen=True)
class ContentTypeSpec:
    model: type
    fields: tuple[str, ...]
    display_field: str
    label: str
    order_by: tuple[str, ...]


REGISTRY: dict[str, ContentTypeSpec] = {
    "room": ContentTypeSpec(Room, ("name", "description"), "name", "Rooms", ("name",)),
    "tech_help_option": ContentTypeSpec(
        TechHelpOption, ("title", "description", "schedule"), "title",
        "Tech Help Options", ("sort_order", "id"),
    ),
    "legal_topic": ContentTypeSpec(
        LegalTopic, ("name", "description"), "name", "Legal Topics",
        ("display_order", "id"),
    ),
    "discover_shelf": ContentTypeSpec(
        StaffShelf, ("title", "description"), "title", "Discover Shelves",
        ("display_order", "id"),
    ),
}


class TranslationField(BaseModel):
    field: str
    source: Optional[str]
    value: Optional[str]


class TranslationRecord(BaseModel):
    id: int
    display_name: str
    fields: list[TranslationField]


class TranslationGroup(BaseModel):
    content_type: str
    label: str
    records: list[TranslationRecord]


class TranslationsResponse(BaseModel):
    language: str
    groups: list[TranslationGroup]


class TranslationUpdateRequest(BaseModel):
    language: str
    values: dict[str, Optional[str]]


def _record_to_translation(record, spec: ContentTypeSpec, lang: str) -> TranslationRecord:
    entry = (record.translations or {}).get(lang) or {}
    fields = []
    for field in spec.fields:
        value = entry.get(field) if isinstance(entry, dict) else None
        if not (isinstance(value, str) and value.strip()):
            value = None
        fields.append(
            TranslationField(field=field, source=getattr(record, field), value=value)
        )
    return TranslationRecord(
        id=record.id,
        display_name=getattr(record, spec.display_field),
        fields=fields,
    )


@router.get("", response_model=TranslationsResponse)
async def get_content_translations(
    lang: str = Query(..., max_length=10),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List every translatable record across all content types for one language."""
    groups = []
    for content_type, spec in REGISTRY.items():
        order_cols = [getattr(spec.model, col) for col in spec.order_by]
        result = await db.execute(select(spec.model).order_by(*order_cols))
        records = result.scalars().all()
        groups.append(
            TranslationGroup(
                content_type=content_type,
                label=spec.label,
                records=[_record_to_translation(r, spec, lang) for r in records],
            )
        )
    return TranslationsResponse(language=lang, groups=groups)


@router.put("/{content_type}/{record_id}", response_model=TranslationRecord)
async def update_content_translation(
    content_type: str,
    record_id: int,
    payload: TranslationUpdateRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Merge ``values`` into ``translations[language]``; empty/null deletes a field."""
    spec = REGISTRY.get(content_type)
    if spec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown content type")

    unknown = set(payload.values) - set(spec.fields)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown field(s): {', '.join(sorted(unknown))}",
        )

    result = await db.execute(select(spec.model).where(spec.model.id == record_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    translations = dict(record.translations or {})
    lang_entry = dict(translations.get(payload.language) or {})
    for field, value in payload.values.items():
        if value is None or value == "":
            lang_entry.pop(field, None)
        else:
            lang_entry[field] = value
    if lang_entry:
        translations[payload.language] = lang_entry
    else:
        translations.pop(payload.language, None)
    record.translations = translations

    await db.flush()
    await db.refresh(record)

    return _record_to_translation(record, spec, payload.language)
