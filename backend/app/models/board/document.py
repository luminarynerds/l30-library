# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import StrEnum
from ...core.database import Base


class DocumentType(StrEnum):
    MINUTES = "minutes"
    AGENDA = "agenda"
    PACKET = "packet"
    RESOLUTION = "resolution"
    POLICY = "policy"
    FINANCIAL_REPORT = "financial_report"
    PRESENTATION = "presentation"
    OTHER = "other"


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class BoardDocument(Base):
    __tablename__ = "board_documents"

    id = Column(Integer, primary_key=True, index=True)
    committee_id = Column(Integer, ForeignKey("board_committees.id", ondelete="SET NULL"), nullable=True, index=True)
    meeting_id = Column(Integer, ForeignKey("board_meetings.id", ondelete="SET NULL"), nullable=True, index=True)
    document_type = Column(String(30), nullable=False, index=True)

    title = Column(String(500), nullable=False)
    description = Column(Text)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size_bytes = Column(Integer)
    mime_type = Column(String(100))

    version_number = Column(Integer, default=1, nullable=False)
    is_current_version = Column(Boolean, default=True, index=True)
    previous_version_id = Column(Integer, ForeignKey("board_documents.id", ondelete="SET NULL"))

    status = Column(String(30), default="draft", nullable=False, index=True)
    published_date = Column(DateTime(timezone=True))
    published_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    is_public = Column(Boolean, default=True, index=True)
    is_confidential = Column(Boolean, default=False)

    # Keywords for search
    keywords = Column(ARRAY(String), default=list)

    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    committee = relationship("Committee", back_populates="documents")
    meeting = relationship("BoardMeeting", foreign_keys=[meeting_id], back_populates="documents")
    previous_version = relationship("BoardDocument", remote_side=[id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    published_by = relationship("User", foreign_keys=[published_by_id])
    versions = relationship(
        "BoardDocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="BoardDocumentVersion.version_number",
    )
