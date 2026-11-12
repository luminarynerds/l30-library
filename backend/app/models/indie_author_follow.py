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


class IndieAuthorFollow(Base):

    __tablename__ = "indie_author_follows"

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
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # Set to NOW() the first time the digest job processes this follow.
    # NULL means "not seeded yet"; on first run the job records all current
    # books-by-this-author as already-notified, sends nothing, then stamps this.
    seeded_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "indie_author_id", name="uq_indie_author_follow_user_author"
        ),
    )

    user = relationship("User", foreign_keys=[user_id])
    indie_author = relationship("IndieAuthor", foreign_keys=[indie_author_id])
