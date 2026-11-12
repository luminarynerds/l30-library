# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func

from ..core.database import Base


class OfflineSyncSession(Base):

    __tablename__ = "offline_sync_sessions"
    __table_args__ = (
        Index("ix_offline_sync_branch_status", "branch_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, default="preparing")
    departed_at = Column(DateTime(timezone=True), nullable=True)
    returned_at = Column(DateTime(timezone=True), nullable=True)
    synced_at = Column(DateTime(timezone=True), nullable=True)
    items_cached = Column(Integer, default=0)
    patrons_cached = Column(Integer, default=0)
    operations_queued = Column(Integer, default=0)
    operations_synced = Column(Integer, default=0)
    operations_conflicted = Column(Integer, default=0)
    offline_session_token = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProcessedOfflineOp(Base):

    __tablename__ = "processed_offline_ops"

    client_op_id = Column(String(50), primary_key=True)
    session_id = Column(Integer, ForeignKey("offline_sync_sessions.id", ondelete="CASCADE"), nullable=False)
    result_status = Column(String(20), nullable=False)
    result_detail = Column(String(500), nullable=True)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
