# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class HomeShelfQueryKind(StrEnum):

    new_arrivals = "new_arrivals"
    staff_picks = "staff_picks"
    subject = "subject"
    format = "format"
    circulation_top = "circulation_top"
    manual_list = "manual_list"


class HomeHeroPick(Base):
    __tablename__ = "home_hero_picks"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(
        Integer,
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    annotation_md = Column(Text, nullable=False)
    cta_label = Column(String(120), nullable=False)
    cta_href = Column(String(500), nullable=True)
    active_from = Column(DateTime(timezone=True), nullable=False)
    active_to = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    item = relationship("CatalogItem", lazy="select")

    __table_args__ = (
        Index("ix_home_hero_picks_active_from", "active_from"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<HomeHeroPick id={self.id} item_id={self.item_id}>"


class HomeShelf(Base):
    __tablename__ = "home_shelves"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(120), nullable=False, unique=True)
    heading = Column(String(200), nullable=False)
    description = Column(String(500), nullable=False, server_default="")
    query_kind = Column(
        SQLEnum(
            HomeShelfQueryKind,
            name="homeshelfquerykind",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    query_params = Column(JSONB, nullable=False, server_default="{}")
    sort_order = Column(Integer, nullable=False, server_default="0")
    is_active = Column(Boolean, nullable=False, server_default="true")
    max_items = Column(Integer, nullable=False, server_default="6")
    view_all_href = Column(String(500), nullable=True)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_home_shelves_sort_active", "sort_order", "is_active"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<HomeShelf id={self.id} slug={self.slug!r} kind={self.query_kind}>"


class HomePageConfig(Base):
    __tablename__ = "home_page_config"

    id = Column(Integer, primary_key=True, server_default="1")
    eyebrow = Column(String(280), nullable=True)
    hero_visible = Column(Boolean, nullable=False, server_default="true")
    picks_link_label = Column(String(120), nullable=True)
    picks_link_href = Column(String(500), nullable=True)
    empty_state_message = Column(Text, nullable=True)
    updated_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("id = 1", name="ck_home_page_config_singleton"),
    )
