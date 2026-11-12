# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import CheckConstraint, Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.enum_helpers import EnumColumn
from app.models.mixins import TimestampMixin


class MultiPartSetType(StrEnum):
    multivolume = "multivolume"
    monographic_series = "monographic_series"
    numbered_set = "numbered_set"


class MultiPartSet(Base, TimestampMixin):
    __tablename__ = "multipart_sets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    set_type = EnumColumn(
        MultiPartSetType,
        nullable=False,
        index=True,
        default=MultiPartSetType.multivolume,
    )
    total_parts = Column(Integer, nullable=True)
    publisher = Column(String(255), nullable=True)
    editor = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    items = relationship(
        "CatalogItem",
        back_populates="multipart_set",
        order_by="CatalogItem.sequence_in_set",
    )

    __table_args__ = (
        CheckConstraint(
            "total_parts IS NULL OR total_parts > 0",
            name="ck_multipart_set_total_parts_positive",
        ),
    )
