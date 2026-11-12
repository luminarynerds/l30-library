# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..core.database import Base
from .mixins import TimestampMixin


class FineWaiverStatus(StrEnum):

    waived = "waived"
    pending_approval = "pending_approval"
    rejected = "rejected"


class FineWaiver(Base, TimestampMixin):

    __tablename__ = "fine_waivers"
    __table_args__ = (
        Index("ix_fine_waivers_fine_id", "fine_id"),
        Index("ix_fine_waivers_status", "status"),
        Index("ix_fine_waivers_waived_by", "waived_by_user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    fine_id = Column(
        Integer, ForeignKey("fines.id", ondelete="CASCADE"), nullable=False
    )
    amount_waived = Column(Numeric(10, 2), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(
        SQLEnum(
            FineWaiverStatus,
            name="finewaiverstatus",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=FineWaiverStatus.pending_approval,
        nullable=False,
    )

    waived_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    waived_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)

    fine = relationship("Fine", foreign_keys=[fine_id])
    waived_by = relationship("User", foreign_keys=[waived_by_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])

    @property
    def is_terminal(self) -> bool:
        return self.status in (FineWaiverStatus.waived, FineWaiverStatus.rejected)

    @property
    def reduces_balance(self) -> bool:
        return self.status == FineWaiverStatus.waived
