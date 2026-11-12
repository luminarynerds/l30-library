# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import (
    Column, BigInteger, Integer, String, DateTime, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from ..core.database import Base


class EbookCheckoutLog(Base):
    __tablename__ = "ebook_checkout_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    source = Column(String(20), nullable=False)        # metislib, indie, vault
    source_ref_id = Column(Integer, nullable=True)      # provider-specific ID
    ebook_title = Column(String(500), nullable=False)
    ebook_author = Column(String(300), nullable=False, server_default="")
    action = Column(String(20), nullable=False)         # borrow, return, hold, download, purchase
    recorded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    metadata_ = Column("metadata", JSONB, nullable=True)

    __table_args__ = (
        Index("ix_ebook_log_user_recorded", "user_id", recorded_at.desc()),
        Index("ix_ebook_log_source_action_recorded", "source", "action", recorded_at.desc()),
    )
