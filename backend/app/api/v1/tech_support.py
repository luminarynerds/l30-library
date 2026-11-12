# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tech Support API — classes, resources, help options, quick links from database."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.content_i18n import translated
from ...core.database import get_db
from ...models.tech_support import (
    TechHelpResource, TechClass, TechHelpOption, TechQuickLink, TechFacility
)


router = APIRouter(prefix="/tech-support", tags=["tech-support"])


# ---------- Schemas ----------

class HelpOptionOut(BaseModel):
    id: int
    title: str
    description: str
    schedule: str
    location: Optional[str] = None
    phone: Optional[str] = None
    icon: Optional[str] = None

    model_config = {"from_attributes": True}


class TechResourceOut(BaseModel):
    id: int
    title: str
    description: str
    category: str
    format: str
    duration: Optional[str] = None
    href: Optional[str] = None
    difficulty_level: Optional[str] = None

    model_config = {"from_attributes": True}


class TechClassOut(BaseModel):
    id: int
    title: str
    description: str
    date: str
    time: str
    location: str
    level: str
    instructor: Optional[str] = None
    capacity: Optional[int] = None
    enrolled: int = 0

    model_config = {"from_attributes": True}


class QuickLinkOut(BaseModel):
    name: str
    url: str

    model_config = {"from_attributes": True}


class QuickAccessSectionOut(BaseModel):
    title: str
    icon: Optional[str] = None
    links: List[QuickLinkOut]


class TechFacilityOut(BaseModel):
    id: int
    label: str
    value: str

    model_config = {"from_attributes": True}


class TechFacilitySectionOut(BaseModel):
    kind: str
    facilities: List[TechFacilityOut]


# ---------- Endpoints ----------

@router.get("/help-options", response_model=List[HelpOptionOut])
async def get_help_options(
    lang: Optional[str] = Query(None, max_length=10),
    db: AsyncSession = Depends(get_db),
):
    """Get available tech support help options."""
    result = await db.execute(
        select(TechHelpOption)
        .where(TechHelpOption.is_active == True)
        .order_by(TechHelpOption.sort_order)
    )
    options = result.scalars().all()
    return [
        HelpOptionOut(
            id=o.id,
            title=translated(o, "title", lang),
            description=translated(o, "description", lang),
            schedule=translated(o, "schedule", lang),
            location=o.location,
            phone=o.phone,
            icon=o.icon,
        )
        for o in options
    ]


@router.get("/resources", response_model=List[TechResourceOut])
async def get_resources(category: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Get tech support learning resources."""
    query = select(TechHelpResource).where(TechHelpResource.is_active == True)
    if category:
        query = query.where(TechHelpResource.category == category)
    query = query.order_by(TechHelpResource.sort_order)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/classes", response_model=List[TechClassOut])
async def get_classes(db: AsyncSession = Depends(get_db)):
    """Get upcoming tech support classes."""
    result = await db.execute(
        select(TechClass)
        .where(TechClass.is_active == True)
        .where(TechClass.date >= datetime.now())
        .order_by(TechClass.date)
    )
    classes = result.scalars().all()
    out = []
    for cls in classes:
        out.append(TechClassOut(
            id=cls.id,
            title=cls.title,
            description=cls.description,
            date=cls.date.strftime("%b %d, %Y"),
            time=cls.date.strftime("%-I:%M %p"),
            location=cls.location,
            level=cls.level.value,
            instructor=cls.instructor,
            capacity=cls.capacity,
            enrolled=cls.enrolled,
        ))
    return out


@router.get("/quick-links", response_model=List[QuickAccessSectionOut])
async def get_quick_links(db: AsyncSession = Depends(get_db)):
    """Get quick access links grouped by section."""
    result = await db.execute(
        select(TechQuickLink)
        .where(TechQuickLink.is_active == True)
        .order_by(TechQuickLink.section_title, TechQuickLink.sort_order)
    )
    links = result.scalars().all()

    sections: dict = {}
    for link in links:
        if link.section_title not in sections:
            sections[link.section_title] = {
                "title": link.section_title,
                "icon": link.section_icon,
                "links": [],
            }
        sections[link.section_title]["links"].append({
            "name": link.name,
            "url": link.url,
        })
    return list(sections.values())


@router.get("/facilities", response_model=List[TechFacilitySectionOut])
async def get_facilities(db: AsyncSession = Depends(get_db)):
    """Get facility facts (computer-lab stats, printers) grouped by kind."""
    result = await db.execute(
        select(TechFacility)
        .where(TechFacility.is_active == True)
        .order_by(TechFacility.kind, TechFacility.sort_order)
    )
    facilities = result.scalars().all()

    sections: dict = {}
    for facility in facilities:
        kind = facility.kind.value
        if kind not in sections:
            sections[kind] = {"kind": kind, "facilities": []}
        sections[kind]["facilities"].append({
            "id": facility.id,
            "label": facility.label,
            "value": facility.value,
        })
    return list(sections.values())
