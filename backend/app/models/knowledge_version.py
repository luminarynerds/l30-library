# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class KnowledgeVersion(Base):
    __tablename__ = "knowledge_versions"

    id = Column(Integer, primary_key=True, index=True)
    knowledge_entry_id = Column(Integer, ForeignKey("knowledge_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    persona_domain = Column(String(50), nullable=True)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    changed_by_name = Column(String(255), nullable=True)
    change_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    previous_content = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
