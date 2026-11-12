# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

from .catalog import BookBinding, ItemType  # BookBinding re-exported for back-compat
from .user import UserRole


class CirculationPolicy(Base):

    __tablename__ = "circulation_policy"

    id = Column(Integer, primary_key=True)
    library_system_id = Column(
        Integer,
        ForeignKey("library_systems.id", ondelete="CASCADE"),
        nullable=False,
    )

    role = Column(
        SQLEnum(UserRole, name="userrole", values_callable=lambda x: [e.value for e in x], create_type=False),
        nullable=True,
    )
    item_type = Column(
        SQLEnum(ItemType, name="itemtype", values_callable=lambda x: [e.value for e in x], create_type=False),
        nullable=True,
    )
    binding = Column(
        SQLEnum(BookBinding, name="bookbinding", values_callable=lambda x: [e.value for e in x], create_type=False),
        nullable=True,
    )
    collection_id = Column(
        Integer,
        ForeignKey("collection.id", ondelete="CASCADE"),
        nullable=True,
    )

    loan_period_days = Column(Integer, nullable=True)
    max_renewals = Column(Integer, nullable=True)
    overdue_fine_per_day = Column(Numeric(10, 2), nullable=True)
    max_fine = Column(Numeric(10, 2), nullable=True)
    grace_period_days = Column(Integer, nullable=True)
    hold_pickup_days = Column(Integer, nullable=True)
    fine_free = Column(Boolean, nullable=True)

    active = Column(Boolean, nullable=False, default=True, server_default="true")
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    library_system = relationship("LibrarySystem")
    collection = relationship("Collection")

    def __repr__(self) -> str:
        return (
            f"<CirculationPolicy id={self.id} sys={self.library_system_id} "
            f"role={self.role} item_type={self.item_type} "
            f"binding={self.binding} collection={self.collection_id}>"
        )
