# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from ..core.database import Base


class LibraryDocumentType(StrEnum):
    NEWSLETTER = "newsletter"
    ANNUAL_REPORT = "annual_report"
    BOARD_REPORT = "board_report"
    FLYER = "flyer"
    PROGRAM_GUIDE = "program_guide"
    POLICY_DOCUMENT = "policy_document"
    PRESS_RELEASE = "press_release"
    OTHER = "other"


class LibraryDocument(Base):
    __tablename__ = "library_documents"

    id = Column(Integer, primary_key=True, index=True)

    # Metadata
    title = Column(String(500), nullable=False)
    document_type = Column(String(30), nullable=False, index=True)
    description = Column(Text, nullable=True)
    publish_date = Column(DateTime(timezone=True), nullable=True)
    tags = Column(ARRAY(String), default=list)

    # File info (null if text was pasted directly)
    filename = Column(String(500), nullable=True)
    file_path = Column(String(1000), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)

    # Extracted / pasted full text
    full_text = Column(Text, nullable=False)
    page_count = Column(Integer, nullable=True)

    # Chunk tracking
    chunk_count = Column(Integer, nullable=False, default=0)

    # Ownership
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
    chunks = relationship(
        "LibraryDocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="LibraryDocumentChunk.chunk_index",
    )

    __table_args__ = (
        Index("ix_library_documents_type_date", "document_type", "publish_date"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "document_type": self.document_type,
            "description": self.description,
            "publish_date": self.publish_date.isoformat() if self.publish_date else None,
            "tags": self.tags or [],
            "filename": self.filename,
            "file_size_bytes": self.file_size_bytes,
            "page_count": self.page_count,
            "chunk_count": self.chunk_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class LibraryDocumentChunk(Base):
    __tablename__ = "library_document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("library_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Position within the document
    chunk_index = Column(Integer, nullable=False)
    section_title = Column(String(500), nullable=True)
    page_number = Column(Integer, nullable=True)

    # The chunk text content
    chunk_text = Column(Text, nullable=False)
    word_count = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("LibraryDocument", back_populates="chunks")

    __table_args__ = (
        Index("ix_doc_chunks_doc_index", "document_id", "chunk_index"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "section_title": self.section_title,
            "page_number": self.page_number,
            "chunk_text": self.chunk_text[:200] + "..." if len(self.chunk_text) > 200 else self.chunk_text,
            "word_count": self.word_count,
        }
