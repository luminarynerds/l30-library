# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from ..core.database import Base


class BlogEmailSubscription(Base):
    __tablename__ = "blog_email_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # "weekly" or "monthly" -- plain string to dodge alembic enum bulk_insert PG/SQLite mismatch
    frequency = Column(String(20), nullable=False, default="weekly")
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    confirmation_token = Column(String(64), nullable=False, index=True)
    unsubscribe_token = Column(String(64), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "email", "frequency", name="uq_blog_subscription_email_freq"
        ),
    )
