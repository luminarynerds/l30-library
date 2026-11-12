# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import enum

from enum import Enum, StrEnum
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.mixins import TimestampMixin


class ShelfAudience(StrEnum):

    kids = "kids"
    teens = "teens"
    adults = "adults"
    all = "all"


class StaffShelf(Base, TimestampMixin):

    __tablename__ = "staff_shelves"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(80), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    item_ids = Column(JSON, nullable=False, default=list)
    audience = Column(
        Enum(ShelfAudience, name="shelfaudience"),
        nullable=True,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    translations = Column(JSONB, nullable=False, server_default=text("'{}'"))
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_by = relationship("User", foreign_keys=[created_by_id])
