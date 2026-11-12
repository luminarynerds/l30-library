# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from ..core.database import Base
from ..core.enum_helpers import EnumColumn
from .mixins import TimestampMixin


class MarcMacroVisibility(StrEnum):
    private = "private"
    shared = "shared"


class MarcMacro(Base, TimestampMixin):
    __tablename__ = "marc_macros"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)

    visibility = EnumColumn(MarcMacroVisibility, nullable=False, index=True)

    # Owner is required for private macros; null for shared macros that are
    # not tied to an individual cataloger. We do NOT cascade-delete macros
    # when a user is removed -- shared knowledge survives departures.
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Ordered list of step dicts. Each step:
    #   {"op": "set"|"clear"|"find_replace"|"append",
    #    "tag": "650", "subfield": "a",
    #    "value": "...", "find": "...", "replace": "..."}
    # Validated by MarcMacroService before run.
    steps = Column(JSONB, nullable=False, default=list)

    owner = relationship("User", foreign_keys=[owner_id])

    __table_args__ = (
        Index("ix_marc_macros_visibility_name", "visibility", "name"),
    )

    def __repr__(self) -> str:
        return f"<MarcMacro(id={self.id}, name={self.name!r}, visibility={self.visibility})>"
