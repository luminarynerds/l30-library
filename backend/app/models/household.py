# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class HouseholdLinkStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


class HouseholdLink(Base):
    __tablename__ = "household_links"

    id = Column(Integer, primary_key=True, index=True)

    # The user requesting the link (usually a child)
    requester_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # The parent user being linked to
    target_parent_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Status of the link (pending approval, approved, or declined)
    status = Column(
        SQLEnum(HouseholdLinkStatus, name="householdlinkstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=HouseholdLinkStatus.PENDING,
        nullable=False,
        index=True
    )

    # Optional reason for declining the link
    decline_reason = Column(String(500), nullable=True)

    # Optional message from requester
    message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    requester = relationship(
        "User",
        foreign_keys=[requester_id],
        back_populates="household_link_requests",
        lazy="select"
    )
    target_parent = relationship(
        "User",
        foreign_keys=[target_parent_id],
        back_populates="household_link_targets",
        lazy="select"
    )
