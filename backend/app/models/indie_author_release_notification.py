# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class IndieAuthorReleaseNotification(Base):

    __tablename__ = "indie_author_release_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    indie_author_id = Column(
        Integer,
        ForeignKey("indie_authors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # External (MetisLib) ebook id; we don't have an L30-side ebooks PK for every catalog row.
    metislib_ebook_id = Column(Integer, nullable=False, index=True)
    sent_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "metislib_ebook_id",
            name="uq_indie_release_notif_user_ebook",
        ),
    )

    user = relationship("User", foreign_keys=[user_id])
    indie_author = relationship("IndieAuthor", foreign_keys=[indie_author_id])
