# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..core.database import Base
from .mixins import TimestampMixin


class ShelfNoteCategory(StrEnum):
    content_warning = "content_warning"
    recommendation = "recommendation"
    context = "context"
    accessibility = "accessibility"
    other = "other"


class ShelfNote(Base, TimestampMixin):

    __tablename__ = "shelf_notes"

    id = Column(Integer, primary_key=True, index=True)
    catalog_item_id = Column(
        Integer,
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    category = Column(
        SQLEnum(
            ShelfNoteCategory,
            name="shelfnotecategory",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ShelfNoteCategory.other,
    )
    is_approved = Column(Boolean, default=False, nullable=False)

    user = relationship("User", backref="shelf_notes")
    catalog_item = relationship("CatalogItem", backref="shelf_notes")
