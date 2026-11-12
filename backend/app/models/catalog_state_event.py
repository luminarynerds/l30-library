# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base
from .catalog import ItemStatus


class CatalogStateEvent(Base):
    __tablename__ = "catalog_state_events"

    id = Column(Integer, primary_key=True, index=True)
    catalog_item_id = Column(
        Integer,
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    old_status = Column(
        SQLEnum(ItemStatus, name="itemstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    new_status = Column(
        SQLEnum(ItemStatus, name="itemstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    reason = Column(Text, nullable=False)
    source_type = Column(String(50), nullable=False)
    source_id = Column(Integer, nullable=True)
    actor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    catalog_item = relationship("CatalogItem")
    actor = relationship("User")

    __table_args__ = (
        Index("ix_catalog_state_events_item_created", "catalog_item_id", "created_at"),
    )
