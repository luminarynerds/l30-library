# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from ..core.database import Base


class Subject(Base):

    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(300), nullable=False, unique=True, index=True)
    slug = Column(String(300), nullable=False, index=True)
    authority = Column(String(40), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    item_links = relationship(
        "CatalogItemSubject",
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CatalogItemSubject(Base):

    __tablename__ = "catalog_item_subjects"

    catalog_item_id = Column(
        Integer,
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id = Column(
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position = Column(Integer, nullable=False, server_default="0", default=0)

    __table_args__ = (
        PrimaryKeyConstraint(
            "catalog_item_id", "subject_id", name="pk_catalog_item_subjects"
        ),
        # Reverse-direction lookup for facet counts (group by subject_id with
        # an item_id filter from the outer search query).
        Index(
            "ix_catalog_item_subjects_subject_item",
            "subject_id",
            "catalog_item_id",
        ),
    )

    catalog_item = relationship("CatalogItem", back_populates="subject_links")
    subject = relationship("Subject", back_populates="item_links")
