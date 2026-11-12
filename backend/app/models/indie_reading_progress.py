# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class IndieReadingProgress(Base):
    __tablename__ = "indie_reading_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ebook_id = Column(Integer, ForeignKey("indie_ebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    percent = Column(Integer, nullable=False, default=0)
    current_position = Column(String(500), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "ebook_id", name="uq_indie_reading_progress_user_ebook"),
    )

    user = relationship("User", foreign_keys=[user_id])
    ebook = relationship("IndieEbook", foreign_keys=[ebook_id])
