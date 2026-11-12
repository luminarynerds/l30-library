# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from ..mixins import TimestampMixin
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ...core.database import Base


COI_CATEGORIES = [
    "vendor_relationship",
    "financial_interest",
    "family_member",
    "real_estate",
    "employment",
    "board_membership",
    "other",
]


class BoardCOIDisclosure(Base, TimestampMixin):
    __tablename__ = "board_coi_disclosures"

    id = Column(Integer, primary_key=True, index=True)
    board_member_id = Column(Integer, ForeignKey("board_members.id", ondelete="CASCADE"), nullable=False, index=True)
    fiscal_year = Column(String(10), nullable=False, index=True)

    disclosure_text = Column(Text, nullable=False)
    categories = Column(JSONB, default=list)
    keywords = Column(JSONB, default=list)

    attested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    attestation_statement = Column(String(1000), nullable=False)

    is_current = Column(Boolean, default=True, index=True)
    superseded_by_id = Column(Integer, ForeignKey("board_coi_disclosures.id", ondelete="SET NULL"), nullable=True)
    superseded_at = Column(DateTime(timezone=True), nullable=True)

    board_member = relationship("BoardMember", backref="coi_disclosures")
    superseded_by = relationship("BoardCOIDisclosure", remote_side=[id])
