# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.mixins import TimestampMixin

from ..core.database import Base


class SearchQueryLog(Base, TimestampMixin):

    __tablename__ = "search_query_log"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(500), nullable=False)
    normalized_query = Column(String(500), nullable=False, index=True)
    result_count = Column(Integer, nullable=False, default=0)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_search_query_log_normalized_created", "normalized_query", "created_at"),
        Index("ix_search_query_log_zero_results", "normalized_query", postgresql_where=Column("result_count") == 0),
    )


class SearchClickLog(Base, TimestampMixin):

    __tablename__ = "search_click_log"

    id = Column(Integer, primary_key=True, index=True)
    normalized_query = Column(String(500), nullable=False, index=True)
    result_id = Column(String(120), nullable=False)
    entity_type = Column(String(40), nullable=False, index=True)
    position = Column(Integer, nullable=False, default=0)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_search_click_log_query_result", "normalized_query", "result_id"),
    )
