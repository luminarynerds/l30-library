# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Patron waiting-list signups.

Patron self-serve registration is currently invite-only; the public
``/register`` page collects emails here instead of creating accounts, so
patrons can be onboarded in manageable batches.
"""
from sqlalchemy import Column, Integer, String, DateTime, func, Index

from ..core.database import Base


class WaitlistSignup(Base):
    __tablename__ = "waitlist_signups"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)
    # Where the signup came from (e.g. 'register'); kept for parity with the
    # MetisLib waitlist so future surfaces can be told apart.
    source = Column(String(50), nullable=False, server_default="register")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_l30_waitlist_signups_email_lower", func.lower(email), unique=True),
    )
