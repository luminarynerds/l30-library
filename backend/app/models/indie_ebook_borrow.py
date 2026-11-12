# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import enum

from enum import Enum, StrEnum
from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Enum as SQLEnum,
    ForeignKey, Integer, Numeric, String, Text, func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class BorrowStatus(StrEnum):
    active = "active"
    returned = "returned"
    expired = "expired"


class MetisLibSyncState(StrEnum):
    not_required = "not_required"   # local-only title (no metislib_ebook_id)
    synced = "synced"               # MetisLib borrow created / return propagated
    borrow_failed = "borrow_failed" # MetisLib borrow call needed but failed
    return_failed = "return_failed" # MetisLib return call needed but failed


class IndieEbook(Base):
    __tablename__ = "indie_ebooks"

    id = Column(Integer, primary_key=True, index=True)
    metislib_ebook_id = Column(Integer, unique=True, index=True)
    sample_text = Column(Text, nullable=True)

    # --- Owned catalog fields (imported from MetisLib OPDS, Phase 1) ---
    title = Column(String(500), nullable=True)
    author_pen_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    cover_url = Column(String(1024), nullable=True)
    genre = Column(String(255), nullable=True)
    language = Column(String(16), nullable=True)
    publication_year = Column(Integer, nullable=True)
    file_format = Column(String(32), nullable=True, default="epub")
    content_warnings = Column(Text, nullable=True)  # JSON-encoded list[str]
    copies_owned = Column(Integer, nullable=False, server_default="0", default=0)
    copies_available = Column(Integer, nullable=False, server_default="0", default=0)
    price_per_copy = Column(Numeric(10, 2), nullable=True)
    file_path = Column(String(1024), nullable=True)  # local path to the owned EPUB
    source_updated_at = Column(DateTime(timezone=True), nullable=True)  # feed entry <updated>
    imported_at = Column(DateTime(timezone=True), nullable=True)

    # --- Phase 2 gap fields (static metadata captured from MetisLib detail) ---
    subjects = Column(Text, nullable=True)            # JSON-encoded list[str]
    content_rating = Column(String(16), nullable=True)
    word_count = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    isbn = Column(String(32), nullable=True)
    author_id = Column(Integer, nullable=True)        # MetisLib-side author id, denormalized


class IndieEbookBorrow(Base):
    __tablename__ = "indie_ebook_borrows"

    id = Column(Integer, primary_key=True, index=True)
    ebook_id = Column(Integer, ForeignKey("indie_ebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    borrowed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    due_at = Column(DateTime(timezone=True), nullable=False)
    returned_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(
        SQLEnum(BorrowStatus, name="borrowstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=BorrowStatus.active,
        nullable=False,
        index=True,
    )

    metislib_borrow_id = Column(Integer, nullable=True)
    metislib_sync_state = Column(
        SQLEnum(MetisLibSyncState, name="metislibsyncstate", create_type=False,
                values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=MetisLibSyncState.not_required.value,
        default=MetisLibSyncState.not_required,
        index=True,
    )
    access_token = Column(String(64), unique=True, nullable=False, index=True)
    download_count = Column(Integer, default=0, nullable=False)
    max_downloads = Column(Integer, default=5, nullable=False)

    rating = Column(Integer, nullable=True)
    review_text = Column(Text, nullable=True)
    review_submitted_at = Column(DateTime(timezone=True), nullable=True)
    due_soon_notified_at = Column(DateTime(timezone=True), nullable=True)
    renewal_count = Column(Integer, default=0, nullable=False, server_default="0")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("returned_at IS NULL OR returned_at >= borrowed_at", name="ck_borrow_return_after_borrow"),
        CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="ck_indie_ebook_borrow_rating_range"),
        CheckConstraint("download_count >= 0", name="ck_download_count_non_negative"),
        CheckConstraint("max_downloads > 0", name="ck_max_downloads_positive"),
        CheckConstraint("renewal_count >= 0 AND renewal_count <= 1", name="ck_renewal_count_range"),
    )

    ebook = relationship("IndieEbook", foreign_keys=[ebook_id])
    user = relationship("User", foreign_keys=[user_id])


class IndieEbookWaitlist(Base):
    __tablename__ = "indie_ebook_waitlist"

    id = Column(Integer, primary_key=True, index=True)
    ebook_id = Column(Integer, ForeignKey("indie_ebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, nullable=False)
    notified_at = Column(DateTime(timezone=True), nullable=True)
    notification_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ebook = relationship("IndieEbook", foreign_keys=[ebook_id])
    user = relationship("User", foreign_keys=[user_id])
