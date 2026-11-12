# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.mixins import TimestampMixin

from ..core.database import Base


class RecentSearch(Base, TimestampMixin):

    __tablename__ = "recent_searches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query = Column(String(500), nullable=False)
    search_type = Column(String(50), nullable=True)  # 'unified', 'patrons', 'items', etc.
    result_count = Column(Integer, default=0, nullable=False)

    # Relationship
    user = relationship("User", backref="recent_searches")
