# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from app.models.mixins import TimestampMixin

from ..core.database import Base
from ..core.enum_helpers import EnumColumn
from .mixins import TimestampMixin


class TechResourceCategory(StrEnum):
    basics = "basics"
    internet = "internet"
    mobile = "mobile"
    safety = "safety"
    apps = "apps"
    printing = "printing"
    digital = "digital"
    services = "services"


class TechClassLevel(StrEnum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class TechFacilityKind(StrEnum):
    computer_lab = "computer_lab"
    printer = "printer"


class TechHelpResource(TimestampMixin, Base):
    __tablename__ = "tech_help_resources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(SQLEnum(TechResourceCategory, values_callable=lambda x: [e.value for e in x]), nullable=False)
    format = Column(String(50), nullable=False)
    duration = Column(String(20))
    href = Column(String(500))
    difficulty_level = Column(String(20), default="beginner")
    is_active = Column(Boolean, default=True, server_default=text('true'), nullable=False)
    sort_order = Column(Integer, default=0)


class TechClass(TimestampMixin, Base):
    __tablename__ = "tech_classes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    date = Column(DateTime, nullable=False)
    location = Column(String(100), nullable=False)
    level = Column(SQLEnum(TechClassLevel, values_callable=lambda x: [e.value for e in x]), nullable=False, default=TechClassLevel.beginner)
    instructor = Column(String(100))
    capacity = Column(Integer, default=15)
    enrolled = Column(Integer, default=0, server_default=text('0'), nullable=False)
    is_active = Column(Boolean, default=True, server_default=text('true'), nullable=False)


class TechHelpOption(TimestampMixin, Base):
    __tablename__ = "tech_help_options"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    schedule = Column(String(200), nullable=False)
    location = Column(String(100))
    phone = Column(String(20))
    icon = Column(String(50))
    is_active = Column(Boolean, default=True, server_default=text('true'), nullable=False)
    sort_order = Column(Integer, default=0)
    translations = Column(JSONB, nullable=False, server_default=text("'{}'"))


class TechQuickLink(TimestampMixin, Base):
    __tablename__ = "tech_quick_links"

    id = Column(Integer, primary_key=True, index=True)
    section_title = Column(String(100), nullable=False)
    section_icon = Column(String(50))
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, server_default=text('true'), nullable=False)


class TechFacility(TimestampMixin, Base):
    __tablename__ = "tech_facilities"

    id = Column(Integer, primary_key=True, index=True)
    kind = EnumColumn(TechFacilityKind, nullable=False)
    label = Column(String(200), nullable=False)
    value = Column(Text, nullable=False)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, server_default=text('true'), nullable=False)
